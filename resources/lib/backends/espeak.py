# -*- coding: utf-8 -*-

import ctypes
import ctypes.util
import os
import subprocess
import sys

from backends import base
from backends.audio.builtin_audio_player import BuiltInAudioPlayer
# from backends.audio.player_handler import BasePlayerHandler, WavAudioPlayerHandler
from backends.audio.sound_capabilties import ServiceType, SoundCapabilities
from backends.base import Constraints, SimpleTTSBackend
from backends.espeak_settings import ESpeakSettings
from backends.i_tts_backend_base import ITTSBackendBase
from backends.players.iplayer import IPlayer
from backends.settings.service_types import Services
from backends.settings.validators import ConstraintsValidator
from common import utils
from common.constants import Constants
from common.logger import *
from common.base_services import BaseServices
from common.setting_constants import Backends, Genders, Mode, Players
from common.settings import Settings
from common.settings_low_level import SettingsProperties
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ESpeakTTSBackend(SimpleTTSBackend):
    """

    """
    ID = Backends.ESPEAK_ID
    service_ID: str = Services.ESPEAK_ID
    initialized: bool = False
    backend_id = Backends.ESPEAK_ID
    displayName = 'eSpeak'

    voice_map = dict()
    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(type(self)._class_name)
        if not clz._initialized:
            clz._initialized = True
            BaseServices.register(self)

    def init(self):
        super().init()
        clz = type(self)
        self.initialized = False
        self.process: subprocess.Popen = None
        self.update()

    '''
    @classmethod
    def register_me(cls, what: Type[ITTSBackendBase]) -> None:
        cls._logger.debug(f'Registering {repr(what)}')
        BaseServices.register(service=what)
    '''

    @classmethod
    def get_backend_id(cls) -> str:
        return Backends.ESPEAK_ID

    @classmethod
    def init_voices(cls):
        if cls.initialized_static:
            return

        cmd_path = 'espeak'
        args = [cmd_path, '--voices']
        voices = []
        try:
            process = subprocess.run(args, stdin=None, stdout=subprocess.PIPE,
                                     universal_newlines=True,
                                     stderr=None, shell=False)
            for line in process.stdout.split('\n'):
                if len(line) > 0:
                    voices.append(line)

            del voices[0]
        except ProcessLookupError:
            rc = -1

        # Read lines of voices, ignoring header

        for voice in voices:
            fields = voice.split()
            lang = fields[1]
            gender = fields[2].split('/')[1]
            if gender == 'M':
                gender = Genders.MALE
            elif gender == 'F':
                gender = Genders.FEMALE
            else:
                gender = Genders.UNKNOWN

            voice_name = fields[3]
            voice_id = fields[4]
            entries = cls.voice_map.get(lang, None)
            if entries is None:
                entries = []
                cls.voice_map[lang] = entries
            entries.append((voice_name, voice_id, gender))
            cls.initialized_static = True

    def getVoice(self) -> str:
        clz = type(self)
        voice = clz.getSetting(SettingsProperties.VOICE, '')
        return voice

    def addCommonArgs(self, args, text):
        clz = type(self)
        voice_id = self.getVoice()
        speed = self.getSpeed()
        mode = self.getMode()
        if mode == Mode.ENGINESPEAK:
            # Scale 0 - 200 Default 100
            volume = self.scale_db_to_percent(
                self.getVolume(), upper_bound=200)
        else:
            volume = self.getEngineVolume()

        pitch = self.getPitch()
        if voice_id:
            args.extend(
                ('-v', voice_id))
        if speed:
            args.extend(('-s', str(speed)))
        if pitch:
            args.extend(('-p', str(pitch)))

        args.extend(('-a', str(volume)))
        args.append(text)

    def update(self) -> None:
        self.setMode(self.getMode())

    def getMode(self):
        clz = type(self)
        player_id: str = Settings.get_player_id(clz.service_ID)
        if player_id == BuiltInAudioPlayer.ID:
            return Mode.ENGINESPEAK
        elif type(self).getSetting(SettingsProperties.PIPE):
            return Mode.PIPE
        else:
            return Mode.FILEOUT

    def runCommand(self, text, outFile):
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'espeak.runCommand outFile: {outFile}')
        args = ['espeak', '-w', outFile]
        self.addCommonArgs(args, text)
        try:
            completed: subprocess.CompletedProcess = subprocess.run(args, check=True,
                                                                    shell=False)
            clz._logger.debug(f'args: {completed.args}')
        except subprocess.CalledProcessError as e:
            if type(self)._logger.isEnabledFor(DEBUG):
                type(self)._logger.debug('espeak.runCommand Exception: ' + str(e))
        return True

    def runCommandAndSpeak(self, text):
        clz = type(self)
        args = ['espeak']
        self.addCommonArgs(args, text)
        try:
            self.process = subprocess.Popen(args, universal_newlines=True)
            while self.process is not None and self.process.poll() is None and self.active:
                utils.sleep(10)
            clz._logger.debug(f'args: {args}')
        except subprocess.SubprocessError as e:
            if type(self)._logger.isEnabledFor(DEBUG):
                type(self)._logger.debug('espeak.runCommand Exception: ' + str(e))

    def runCommandAndPipe(self, text):
        args = ['espeak', '--stdout']
        self.addCommonArgs(args, text)
        self.process = subprocess.Popen(args, stdout=subprocess.PIPE)
        return self.process.stdout

    def stop(self):
        clz = type(self)
        if not self.process:
            return
        try:
            self.process.terminate()
        except AbortException:
            reraise(*sys.exc_info())
        except:
            clz._logger.exception("")

    @classmethod
    def settingList(cls, setting, *args):
        if setting == SettingsProperties.LANGUAGE:
            # Returns list of languages and index to closest match to current
            # locale

            cls.init_voices()
            langs = cls.voice_map.keys()  # Not locales

            # Get current process' language_code i.e. en-us
            default_locale = Constants.LOCALE.lower().replace('_', '-')

            longest_match = -1
            default_lang = default_locale[0:2]
            default_lang_country = ''
            if len(default_locale) >= 5:
                default_lang_country = default_locale[0:5]

            idx = 0
            languages = []
            for lang in sorted(langs):
                lower_lang = lang.lower()
                if longest_match == -1:
                    if lower_lang.startswith(default_lang):
                        longest_match = idx
                elif lower_lang.startswith(default_lang_country):
                    longest_match = idx
                elif lower_lang.startswith(default_locale):
                    longest_match = idx

                entry = (lang, lang)  # Display value, setting_value
                languages.append(entry)
                idx += 1

            # Now, convert index to default_setting

            default_setting = ''
            if longest_match > 0:
                default_setting = languages[longest_match][1]

            return languages, default_setting

        if setting == SettingsProperties.VOICE:
            cls.init_voices()
            current_lang = cls.getLanguage()
            current_lang = current_lang[0:2]
            langs = cls.voice_map.keys()  # Not locales
            voices = []
            for lang in langs:
                if lang.startswith(current_lang):
                    voice_list = cls.voice_map.get(lang, [])
                    for voice_name, voice_id, gender_id in voice_list:
                        # TODO: verify
                        # Voice_name is from command and not translatable?

                        # display_value, setting_value
                        voices.append((voice_name, voice_id))

            return voices

        elif setting == SettingsProperties.GENDER:
            cls.init_voices()
            current_lang = cls.getLanguage()
            voice_list = cls.voice_map.get(current_lang, [])
            genders = []
            for voice_name, voice_id, gender_id in voice_list:
                # TODO: verify
                # Voice_name is from command and not translatable?

                # Unlike voices and languages, we just return gender ids
                # translation is handled by SettingsDialog

                genders.append(gender_id)

            return genders

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml
            default_player: str = cls.get_setting_default(SettingsProperties.PLAYER)
            player_ids: List[str] = cls.get_player_ids(include_builtin=True)
            return player_ids, default_player

        return None

    @classmethod
    def get_default_language(cls) -> str:
        languages: List[str]
        default_lang: str
        languages, default_lang = cls.settingList(SettingsProperties.LANGUAGE)
        return default_lang

    @classmethod
    def get_voice_id_for_name(cls, name):
        if len(cls.voice_map) == 0:
            cls.settingList(SettingsProperties.VOICE)
        return cls.voice_map[name]

    def getEngineVolume(self) -> int:
        clz = type(self)
        volume_validator: ConstraintsValidator
        volume_validator = clz.get_validator(clz.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume: float = volume_validator.getValue()
        return volume

    @classmethod
    def negotiate_engine_config(cls, backend_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        """
        Player is informing engine what it is capable of controlling
        Engine replies what it is allowing engine to control
        """
        # if using cache
        # return True, True, True

        return False, False, False


class espeak_VOICE(ctypes.Structure):
    _fields_ = [
        ('name', ctypes.c_char_p),
        ('languages', ctypes.c_char_p),
        ('identifier', ctypes.c_char_p),
        ('gender', ctypes.c_byte),
        ('age', ctypes.c_byte),
        ('variant', ctypes.c_byte),
        ('xx1', ctypes.c_byte),
        ('score', ctypes.c_int),
        ('spare', ctypes.c_void_p),
    ]


######### BROKEN ctypes method ############
class ESpeakCtypesTTSBackend(base.BaseEngineService):
    backend_id = 'eSpeak-ctypes'
    displayName = 'eSpeak (ctypes)'
    settings = {SettingsProperties.VOICE: ''}
    broken = True
    _eSpeak = None

    @property
    def eSpeak(self):
        if ESpeakCtypesTTSBackend._eSpeak:
            return ESpeakCtypesTTSBackend._eSpeak
        libname = ctypes.util.find_library('espeak')
        ESpeakCtypesTTSBackend._eSpeak = ctypes.cdll.LoadLibrary(libname)
        ESpeakCtypesTTSBackend._eSpeak.espeak_Initialize(0, 0, None, 0)
        return ESpeakCtypesTTSBackend._eSpeak

    def __init__(self):
        super().__init__()
        pass

    def init(self):
        super().init()
        self.update()

    @staticmethod
    def isSupportedOnPlatform():
        return SystemQueries.isLinux() or SystemQueries.isWindows()

    @staticmethod
    def isInstalled():
        return ESpeakCtypesTTSBackend.isSupportedOnPlatform()

    def say(self, text, interrupt=False, preload_cache=False):
        if not self.eSpeak:
            return
        if self.voice:
            self.eSpeak.espeak_SetVoiceByName(self.voice)
        if interrupt:
            self.eSpeak.espeak_Cancel()
        sb_text = ctypes.create_string_buffer(text)
        size = ctypes.sizeof(sb_text)
        self.eSpeak.espeak_Synth(sb_text, size, 0, 0, 0, 0x1000, None, None)

    def update(self):
        self.voice = type(self).getSetting(SettingsProperties.VOICE)

    def stop(self):
        if not self.eSpeak:
            return
        self.eSpeak.espeak_Cancel()

    def close(self):
        if not self.eSpeak:
            return
        # self.eSpeak.espeak_Terminate() #TODO: Removed because broke, uncomment if fixed
        # ctypes.cdll.LoadLibrary('libdl.so').dlclose(self.eSpeak._handle)
        # del self.eSpeak #TODO: Removed because broke, uncomment if fixed
        # self.eSpeak = None #TODO: Removed because broke, uncomment if fixed

    @staticmethod
    def available():
        return bool(ctypes.util.find_library('espeak'))

    @classmethod
    def settingList(cls, setting, *args):
        return None
        if setting == SettingsProperties.VOICE:
            if not ESpeakCtypesTTSBackend._eSpeak:
                return None
            voices = ESpeakCtypesTTSBackend._eSpeak.espeak_ListVoices(None)
            aespeak_VOICE = ctypes.POINTER(ctypes.POINTER(espeak_VOICE))
            pvoices = ctypes.cast(voices, aespeak_VOICE)
            voiceList = []
            index = 0
            while pvoices[index]:
                voiceList.append(os.path.basename(
                    pvoices[index].contents.identifier))
                index += 1
            return voiceList
        return None
