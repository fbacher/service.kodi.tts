# -*- coding: utf-8 -*-
import locale
import os
import sys

from backends.audio.sound_capabilties import ServiceType, SoundCapabilities
from backends.base import ThreadedTTSBackend
from backends.settings.constraints import Constraints
from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator
from backends.speechd import Speaker, SSIPCommunicationError
from common.constants import Constants
from common.logger import *
from common.messages import Messages
from common.base_services import BaseServices
from common.setting_constants import Backends
from common.settings import Settings
from common.settings_low_level import SettingsProperties
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)

'''
    Speech Dispatcher is a Linux TTS abstraction layer. It allows for programs
    to interact with a speech engine using a consistent interface. It also allows
    the user to conveniently change which speech engine that they want to use system
    wide without having to go modify settings everywhere.
    
    Speech Dispatcher is long in the tooth, but still useful.
'''

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)
else:
    module_logger = BasicLogger.get_module_logger()


def getSpeechDSpeaker(test=False) -> Speaker:
    try:
        return Speaker('kodi', 'kodi')
    except AbortException:
        reraise(*sys.exc_info())
    except:
        try:
            socket_path = os.path.expanduser('~/.speech-dispatcher/speechd.sock')
            so = Speaker('kodi', 'kodi', socket_path=socket_path)
            try:
                so.set_language(locale.getdefaultlocale()[0][:2])
            except (KeyError, IndexError):
                pass
            return so
        except AbortException:
            reraise(*sys.exc_info())
        except:
            if not test:
                module_logger.error('Speech-Dispatcher: failed to create Speaker')
    return None


class SpeechDispatcherTTSBackend(ThreadedTTSBackend):
    """Supports The speech-dispatcher on linux"""
    ID = Backends.SPEECH_DISPATCHER_ID
    backend_id = Backends.SPEECH_DISPATCHER_ID
    service_ID: str = Services.SPEECH_DISPATCHER_ID
    service_TYPE: str = ServiceType.ENGINE
    displayName = 'Speech Dispatcher'

    # pitchConstraints: Constraints = Constraints(0, 0, 100, True, 1.0, SettingsProperties.PITCH)
    pitchConstraints: Constraints = Constraints(0, 50, 99, True, False, 1.0,
                                                SettingsProperties.PITCH, None)
    # volumeConstraints: Constraints = Constraints(-12, 8, 12, True, 1.0, SettingsProperties.VOLUME)

    SpeechDispatcherVolumeConstraints: Constraints = Constraints(-100, 0, 75,
                                                                 True, False,
                                                                 1.0,
                                                                 SettingsProperties.VOLUME,
                                                                 10)
    SpeechDispatcherSpeedConstraints: Constraints = Constraints(-100, 0, 100, True, False, 1.0,
                                                                 SettingsProperties.SPEED, 0, 10)
    # Pitch -- integer value within the range from -100 to 100, with 0
    #    corresponding to the default pitch of the current speech synthesis
    #    output module, lower values meaning lower pitch and higher values
    #    meaning higher pitch.
    SpeechDispatcherPitchConstraints: Constraints = Constraints(-100, 0, 100,
                                                                True, False,
                                                                1.0,
                                                                SettingsProperties.PITCH,
                                                                0, 10)
    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.ENGINE, ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    NONE: str = 'none'
    _class_name: str = None
    _logger: BasicLogger = None
    volumeExternalEndpoints = (SpeechDispatcherVolumeConstraints.minimum,
                               SpeechDispatcherVolumeConstraints.maximum)
    volumeStep = SpeechDispatcherVolumeConstraints.increment
    volumeSuffix = '%'

    settings = {
        SettingsProperties.MODULE: None  # More defined in init
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)
            clz.register(self)

        self.process = None
        self.stop_processing = False
        self.speechdObject: Speaker | None = None
        self.updateMessage: str | None = None
        self.previous_module: str | None = None
        self.previous_voice: str | None = None

        clz.settings[SettingsProperties.GENDER] = 'female',
        clz.settings[SettingsProperties.LANGUAGE] = 'en-US',
        clz.settings[SettingsProperties.VOICE] = None,
        clz.settings[SettingsProperties.PIPE] = False,
        clz.settings[SettingsProperties.SPEED] = clz.SpeechDispatcherSpeedConstraints.default
        clz.settings[SettingsProperties.PITCH] = clz.SpeechDispatcherPitchConstraints.default
        clz.settings[SettingsProperties.VOLUME] = clz.SpeechDispatcherVolumeConstraints.default

    def init(self):
        super().init()
        self.updateMessage = None
        self.connect()
        self.update()

    @staticmethod
    def isSupportedOnPlatform():
        return SystemQueries.isLinux()

    @staticmethod
    def isInstalled():
        installed = False
        if SpeechDispatcherTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def connect(self) -> None:
        self.speechdObject = getSpeechDSpeaker()
        if not self.speechdObject:
            return
        self.update()

    def threadedSay(self, text, interrupt=False):
        clz = type(self)
        if not self.speechdObject:
            return
        module: str = None
        voice: str = None
        vol: int = -1234
        rate: int = None
        pitch: int = None

        try:
            module = self.setting('module')
            if module and module != self.previous_module:
                self.speechdObject.set_output_module(module)
                self.previous_module = module
            voice = self.setting(SettingsProperties.VOICE)
            if voice and voice != self.previous_voice:
                self.speechdObject.set_language(self.getVoiceLanguage(voice))
                self.speechdObject.set_synthesis_voice(voice)
                self.previous_voice = voice
            rate = clz.getEngineSpeed()
            self.speechdObject.set_rate(rate)
            pitch = clz.getEnginePitch()
            self.speechdObject.set_pitch(pitch)
            vol: int = int(clz.getEngineVolume())
            self.speechdObject.set_volume(vol)
            clz._logger.debug_verbose(f'module: {module} voice: {voice} volume: {vol} '
                                      f'speed: {rate} pitch: {pitch}')
        except SSIPCommunicationError:
            self._logger.exception('SpeechDispatcher')
        try:
            self.speechdObject.speak(text)
        except SSIPCommunicationError:
            self.reconnect()
        except AttributeError:  # Happens on shutdown
            pass

    def stop(self):
        try:
            self.speechdObject.cancel()
        except SSIPCommunicationError:
            self.reconnect()
        except AttributeError:  # Happens on shutdown
            pass

    def reconnect(self):
        self.close()
        if self.active:
            self._logger.debug('Speech-Dispatcher reconnecting...')
            self.connect()

    def volumeUp(self) -> None:
        # Override because returning the message (which causes speech) causes the
        # backend to hang, not sure why... threading issue?
        self.updateMessage = ThreadedTTSBackend.volumeUp(self)

    def volumeDown(self) -> None:
        # Override because returning the message (which causes speech) causes the
        # backend to hang, not sure why... threading issue?
        self.updateMessage = ThreadedTTSBackend.volumeDown(self)

    @classmethod
    def getVolumeDb(cls) -> float | None:
        volume_validator: ConstraintsValidator | IValidator
        volume_validator = SettingsMap.get_validator(cls.service_ID,
                                                     property_id=SettingsProperties.VOLUME)
        volume = volume_validator.get_tts_value()

        return volume

    @classmethod
    def getEngineVolume(cls) -> float:
        """
        Get the configured volume in our standard  -12db .. +12db scale converted
        to the native scale of the API (0.1 .. 1.0). The maximum volume (1.0) is equivalent
        to 0db. Since we have to use a different player AND since it almost guaranteed
        that the voiced text is cached, just set volume to fixed 1.0 and let player
        handle volume).
        """
        volume_validator: ConstraintsValidator
        volume_validator = cls.get_validator(cls.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume, _, _, _ = volume_validator.get_tts_values()
        return volume

    @classmethod
    def getEngineSpeed(cls) -> int:
        """
        """
        speed: float = cls.getSpeed()
        engineSpeed: int = cls.speedConstraints.translate_value(
                cls.SpeechDispatcherSpeedConstraints,
                speed)
        return engineSpeed

    @classmethod
    def getEnginePitch(cls) -> int:
        """
        """
        pitch: float = cls.getPitch()
        enginePitch: int
        enginePitch = cls.pitchConstraints.translate_value(
            cls.SpeechDispatcherPitchConstraints,
            pitch)
        return enginePitch

    @classmethod
    def negotiate_engine_config(cls, backend_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        """
        Player is informing engine what it is capable of controlling
        Engine replies what it is allowing engine to control
        """
        return False, False, False

    def getUpdateMessage(self):
        msg = self.updateMessage
        self.updateMessage = None
        return msg

    def update(self):
        clz = type(self)
        try:
            module = self.setting('module')
            if module:
                self.speechdObject.set_output_module(module)
            voice = self.setting(SettingsProperties.VOICE)
            if voice:
                self.speechdObject.set_language(self.getVoiceLanguage(voice))
                self.speechdObject.set_synthesis_voice(voice)
            self.speechdObject.set_rate(clz.getEngineSpeed())
            self.speechdObject.set_pitch(clz.getEnginePitch())
            vol: int = int(clz.getEngineVolume())
            self.speechdObject.set_volume(vol)
        except SSIPCommunicationError:
            self._logger.error('SpeechDispatcherTTSBackend.update()')
        msg = self.getUpdateMessage()
        if msg:
            self.say(msg, interrupt=True)

    def getVoiceLanguage(self, voice):
        res = None
        voices = self.speechdObject.list_synthesis_voices()
        # Returns a tuple of triplets (name, language, variant).
        # 'name' is a string, 'language' is an ISO 639-1 Alpha-2/3 language code
        # and 'variant' is a string.  Language and variant may be None.
        for v in voices:
            if voice == v[0]:
                res = v[1]
                break
        return res

    @classmethod
    def getCurrentLanguage(cls) -> str:
        so = getSpeechDSpeaker()
        lang = so.get_language()
        return lang

    @classmethod
    def getLanguages(cls) -> Tuple[List[Tuple[str, str]], str]:
        so = getSpeechDSpeaker()
        module: str = cls.setting(SettingsProperties.MODULE)
        if module:
            so.set_output_module(module)
        current_lang = cls.getCurrentLanguage()
        default_lang: str = ''
        voices: List[Tuple[str, str, str]] = so.list_synthesis_voices()
        result: List[Tuple[str, str]] = []
        for (voice, lang, variant) in voices:
            voice: str
            lang: str
            variant: str
            if lang is not None and len(lang) > 0:
                if lang == current_lang:
                    default_lang = current_lang
                result.append((lang, lang))

        final_result: Tuple[List[Tuple[str, str]], str] = (result, default_lang)
        if len(final_result) > 0:
            return final_result
        else:
            return None

    @classmethod
    def getVoices(cls, include_default: bool) -> Tuple[List[Tuple[str, str]], str] | List[
        Tuple[str, str]]:
        so = getSpeechDSpeaker()
        module: str = cls.setting(SettingsProperties.MODULE)
        if module:
            so.set_output_module(module)
        voices: List[Tuple[str, str, str]] = so.list_synthesis_voices()
        current_lang = cls.getCurrentLanguage()
        result: List[Tuple[str, str]] = []
        for (voice, lang, variant) in voices:
            voice: str
            lang: str
            variant: str
            if lang[0:2] == current_lang[0:2]:
                displayName: str = ''
                if variant is not None and len(variant) > 0 and variant != cls.NONE:
                    displayName = f'/{variant}'
                if lang is not None and len(lang) > 0 and lang != cls.NONE:
                    displayName = f'/{lang}{displayName}'
                displayName = f'{voice}{displayName}'
                result.append((displayName, displayName))
        if not include_default:
            return result

        final_result: Tuple[List[Tuple[str, str]], str] = (result, result[0][1])
        if len(final_result) > 0:
            return final_result
        else:
            return None

    @classmethod
    def settingList(cls, setting, *args) -> Tuple[List[Tuple[str, str]], str] | List[
        str] | List[int] | None:
        so = getSpeechDSpeaker()
        if setting == SettingsProperties.LANGUAGE:  # originally VOICE
            voices: Tuple[List[Tuple[str, str]], str] = cls.getLanguages()
            #  voice_name/language/variant , name/language/variant
            return voices
        elif setting == SettingsProperties.MODULE:
            # Return names of all active output modules as a tuple of strings.
            # Tuple[List[xbmcgui.ListItem], int]:
            choices: Tuple[List[Tuple[str, str]], int]
            module_list: List[Tuple[str, str]]
            module_list = [(m, m) for m in so.list_output_modules()]
            default_module_idx = 0
            choices = module_list, default_module_idx
            return choices
        elif setting == SettingsProperties.VOICE:
            voices: Tuple[List[Tuple[str, str]], str] = cls.getVoices(
                include_default=False)

            #  voice_name/language/variant , name/language/variant
            return voices
        elif setting == SettingsProperties.GENDER:  # Only supported with generic voice names
            # See client 'set_synthesis_voice'
            return [Messages.GENDER_UNKNOWN.get_msg_id()]
        else:
            return [('nuthin', 'much')], 'nuthin'

    def close(self):
        if self.speechdObject:
            self.speechdObject.close()
        del self.speechdObject
        self.speechdObject = None
