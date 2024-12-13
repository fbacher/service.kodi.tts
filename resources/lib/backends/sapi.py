# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys
from io import BytesIO
from pathlib import Path

# from pyttsx4 import engine
# import backends.pyttsx4_proxy.proxy as pyttsx4_proxy
# import backends.pyttsx4_run_daemon as pyttsx4_run_daemon
# import backends.pyttsx4_proxy.proxy_impl.engine as engine_proxy
# from backends.pyttsx4_proxy.proxy import Pyttsx4Proxy
# from backends.pyttsx4_proxy.proxy_impl.voice import Voice
from pyttsx4.voice import Voice
import pyttsx4
from backends.settings.constraints import Constraints
from backends.settings.validators import NumericValidator
from common import *

# from backends.audio.player_handler import BasePlayerHandler, WavAudioPlayerHandler
from backends.audio.sound_capabilities import ServiceType
from backends.base import SimpleTTSBackend
from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services
from backends.settings.settings_map import SettingsMap
from common.base_services import BaseServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.logger import *
from common.phrases import Phrase
from common.setting_constants import Backends, Genders, Mode
from common.settings import Settings
from common.settings_low_level import SettingsProperties

module_logger = BasicLogger.get_logger(__name__)


class SAPIBackend(SimpleTTSBackend):
    ID = Backends.SAPI_ID
    service_ID: str = Services.SAPI_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    engine_id: str = Backends.SAPI_ID
    engine_id: str = Backends.SAPI_ID
    displayName: str = 'SAPI'
    PYTTSX_SAPI_NAME: Final[str] = 'sapi5'
    UTF_8: Final[str] = '1'

    voice_map: Dict[str, Voice] = None
    lang_map: Dict[str, List[Voice]] = None
    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False
    displayName = 'SAPI (Windows Internal)'

    canStreamWav = True
    volumeExternalEndpoints = (0, 100)
    volumeStep = 5
    volumeSuffix = '%'
    baseSSML = '''<?xml version="1.0"?>
    phrase: Phrase = None
    
    '''

    pytts_engine: pyttsx4.engine = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger
        clz._logger.debug(f'In init args: {args}')

        '''
        local_site_modules = pathlib.Path(os.environ['SYSTEM_PYTHON'])
        clz._logger.debug(f'SYSTEM_PYTHON: {local_site_modules}')
        sys.path.append(str(local_site_modules))
        sys.path.append(f'{local_site_modules / "win32"}')
        sys.path.append(f'{local_site_modules / "win32" / "lib"}')
        clz._logger.debug(f'SYSTEM_PYTHON: {sys.path}')

        os.add_dll_directory(str(local_site_modules))
        os.add_dll_directory(f'{local_site_modules / "win32"}')
        os.add_dll_directory(f'{local_site_modules / "win32" / "lib"}')
        '''
        if not clz._initialized:
            clz._initialized = True
            BaseServices.register(self)

    def init(self):
        super().init()
        clz = type(self)
        self.update()
        try:
            clz._logger.debug(f'About to init pyttsx4')
            clz.phrase = None
            # clz.proxy = pyttsx4  # Pyttsx4Proxy()
            # clz.pytts_engine = clz.proxy.init(SAPIBackend.PYTTSX_SAPI_NAME, debug=True)
            # clz._logger.debug(f'About to speak')
            # clz.pytts_engine.say('You are a disgusting pig.')
            # clz.pytts_engine.runAndWait()
            # clz.pytts_engine.setProperty('speed', 300)
            # Speak => say + runAndWait
            # clz.proxy.speak('You suck, you old dog.')
            # voices: List[Voice] = clz.pytts_engine.getProperty('voices')
            # for voice in voices:
            #     clz._logger.debug(f'voice: {voice}')

            #  clz.pytts_engine.connect('started-utterance', clz.onStart)
            #  clz.pytts_engine.connect('started-word', clz.onWord)
            #  clz.pytts_engine.connect('finished-utterance', clz.onEnd)
        except ImportError as e:
            clz._logger.exception('')
        except RuntimeError as e:
            clz._logger.exception('')
        clz._logger.debug(f'pytts_engine: {clz.pytts_engine}')

    @classmethod
    def init_pytts(cls) -> None:
        if cls.pytts_engine is None:
            cls.pytts_engine = pyttsx4.init(SAPIBackend.PYTTSX_SAPI_NAME, debug=True)

    @classmethod
    def onStart(cls, name):
        cls._logger.debug('starting', name)

    @classmethod
    def onWord(cls, name, location, length):
        cls._logger.debug('word', name, location, length)

    @classmethod
    def onEnd(cls, name, completed):
        cls._logger.debug('finishing', name, completed)


    '''
    @classmethod
    def register_me(cls, what: Type[ITTSBackendBase]) -> None:
        cls._logger.debug(f'Registering {repr(what)}')
        BaseServices.register(service=what)
    '''

    @classmethod
    def get_backend_id(cls) -> str:
        return cls.service_ID

    @classmethod
    def init_voices(cls):
        if cls.voice_map is not None:
            return

        cls.voice_map: Dict[str, Voice] = {}
        cls.lang_map: Dict[str, List[Voice]] = {}
        voices: List[Voice] = cls.pytts_engine.getProperty('voices')
        for voice in voices:
            cls._logger.debug(f'Setting voice: {voice.id}')
            cls.voice_map[voice.id] = voice
            for lang in voice.languages:
                cls._logger.debug(f'Setting lang: {lang}')
                lang_voices: List[Voice] = cls.lang_map.get(lang)
                if not lang_voices:
                    lang_voices = []
                    cls.lang_map[lang] = lang_voices
                lang_voices.append(lang)
        cls.initialized_static = True

    def addCommonArgs(self, args, phrase: Phrase | None = None):
        clz = type(self)
        clz.phrase = phrase
        voice_id = Settings.get_voice(clz.service_ID)
        if voice_id is None or voice_id in ('unknown', ''):
            voice_id = None

        speed = self.get_speed()
        volume = self.getVolume()
        pitch = self.get_pitch()
        if voice_id:
            args.extend(
                    ('-v', voice_id))
        if speed:
            args.extend(('-s', str(speed)))
        if pitch:
            args.extend(('-p', str(pitch)))

        args.extend(('-a', str(volume)))
        if phrase:
            args.append(phrase.get_text())

    def update(self) -> None:
        self._logger.debug(f'In update')
        self.setMode(self.getMode())

    def getMode(self):
        clz = type(self)
        clz._logger.debug(f' In SAPI getMode')
        return Mode.ENGINESPEAK
    '''
        clz = type(self)
        player_id: str = Settings.get_player_id(clz.service_ID)
        if player_id == BuiltInAudioPlayer.ID:
            return Mode.ENGINESPEAK
        elif Settings.get_pipe(clz.service_ID):
            return Mode.PIPE
        else:
            return Mode.FILEOUT
     '''

    def runCommand(self, phrase: Phrase):
        clz = type(self)
        try:
            clz.phrase = phrase
            self.init_pytts()
            self.current_phrase = phrase
            if phrase.get_interrupt():
                self.stop_current_phrases()
            out_file: Path = phrase.get_cache_path()
            if clz._logger.isEnabledFor(DEBUG_V):
                clz._logger.debug_v(f'sapi.runCommand outFile: {out_file}\n'
                                          f'text: {phrase.text}')
            clz.pytts_engine.save_to_file(phrase.text, out_file)
            clz.pytts_engine.runAndWait()
        except ExpiredException as e:
            self.stop_current_phrases()
            clz._logger.debug(f'EXPIRED: {phrase.text}')
        except Exception as e:
            clz._logger.exception('')
        return True

    def runCommandAndSpeak(self, phrase: Phrase):
        clz = type(self)
        try:
            clz.phrase = phrase
            self.init_pytts()
            if phrase.get_interrupt():
                self.stop_current_phrases()
            clz._logger.debug(f'about to say {phrase.text}')
            clz.pytts_engine.say(phrase.get_text())
            clz._logger.debug(f'about to runAndWait')
            clz.pytts_engine.runAndWait()
            clz._logger.debug(f'returned from runAndWait')
        except ExpiredException as e:
            self.stop_current_phrases()
            clz._logger.debug(f'EXPIRED: {phrase.text}')
        except Exception as e:
            clz._logger.exception('')

    def runCommandAndPipe(self, phrase: Phrase) -> BytesIO:
        clz = type(self)
        try:
            clz.phrase = phrase
            self.init_pytts()
            if phrase.get_interrupt():
                self.stop_current_phrases()
            clz._logger.debug(f'runCommandAndPipe phrase: {phrase.get_text()}')
            byte_stream = BytesIO()
            clz.pytts_engine.save_to_file(phrase.get_text(), byte_stream)
            clz.pytts_engine.runAndWait()
            # the bs is raw data of the audio.
            bs = byte_stream.getvalue()
            # add a wav file format header
            b = bytes(b'RIFF') + (len(bs) + 38).to_bytes(4,
                                                         byteorder='little') + b'WAVEfmt\x20\x12\x00\x00' \
                                                                               b'\x00\x01\x00\x01\x00' \
                                                                               b'\x22\x56\x00\x00\x44\xac\x00\x00' + \
                b'\x02\x00\x10\x00\x00\x00data' + (len(bs)).to_bytes(4,
                                                                     byteorder='little') + bs
            # changed to BytesIO
            b = BytesIO(b)
            return
        except ExpiredException as e:
            self.stop_current_phrases()
            clz._logger.debug(f'EXPIRED: {phrase.text}')
        except Exception as e:
            clz._logger.exception('')
        return None

    def stop(self):
        clz = type(self)
        if clz.pytts_engine is not None:
            try:
                self.stop_current_phrases()
            except AbortException:
                reraise(*sys.exc_info())
            except:
                clz._logger.exception("")
        clz.pytts_engine = None

    def stop_current_phrases(self):
        clz = type(self)
        if clz.pytts_engine is not None:
            clz._logger.debug(f'INTERRUPT stopping speech {clz.phrase.debug_data()}')
            clz.pytts_engine.stop()

    @classmethod
    def settingList(cls, setting, *args):
        if setting == SettingsProperties.LANGUAGE:
            # Returns list of languages and index to closest match to current
            # locale
            # Get current process' language_code i.e. en-us
            default_locale = Constants.LOCALE.lower().replace('_', '-')

            longest_match = -1
            default_lang = default_locale[0:2]
            default_lang_country = ''
            if len(default_locale) >= 5:
                default_lang_country = default_locale[0:5]

            idx = 0
            languages = []
            for lang in sorted(cls.lang_map.keys()):
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
            voices = []
            for lang, voice_list in cls.lang_map.keys():
                if lang.startswith(current_lang):
                    for voice in  voice_list:
                        # TODO: verify
                        # Voice_name is from command and not translatable?

                        # display_value, setting_value
                        voices.append((voice.name, voice.id))

            return voices

        elif setting == SettingsProperties.GENDER:
            cls.init_voices()
            genders: List[str] = []
            current_lang = cls.getLanguage()
            current_lang = current_lang[0:2]
            voices = []
            for lang, voice_list in cls.lang_map.keys():
                if lang.startswith(current_lang):
                    for voice in voice_list:
                        # Voice_name is from command and not translatable?

                        # Unlike voices and languages, we just return gender ids
                        # translation is handled by SettingsDialog

                        genders.append(voice.gender)

            return genders

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml
            default_player: str = cls.get_setting_default(SettingsProperties.PLAYER)
            player_ids: List[str]
            player_ids = SettingsMap.get_allowed_values(cls.service_ID,
                                                        SettingsProperties.PLAYER)
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

    @classmethod
    def getVolume(cls) -> int:
        volume_validator: NumericValidator
        volume_validator = cls.get_validator(cls.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume: int = volume_validator.get_value()
        return volume

    def get_pitch(self) -> int:
        # All pitches in settings use a common TTS scale.
        # Conversions to/from the engine's or player's scale are done using
        # Constraints
        clz = type(self)
        if self.mode != Mode.ENGINESPEAK:
            pitch_val: IValidator = SettingsMap.get_validator(
                    clz.service_ID, SettingsProperties.PITCH)
            pitch: int = pitch_val.tts_line_value
            return pitch
        else:
            # volume = Settings.get_volume(clz.service_ID)
            pitch_val: IValidator = SettingsMap.get_validator(
                    clz.service_ID, SettingsProperties.PITCH)
            # volume: int = volume_val.get_tts_value()
            pitch: int = pitch_val.get_impl_value(clz.service_ID)

        return pitch

    @classmethod
    def get_speed(cls) -> float:
        speed_validator: NumericValidator
        speed_validator = cls.get_validator(cls.service_ID,
                                            property_id=SettingsProperties.SPEED)
        speed: float
        speed = speed_validator.get_value()
        return speed
