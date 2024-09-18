# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import ctypes.util
import os
import subprocess
import sys
import langcodes

from pathlib import Path

from backends.players.iplayer import IPlayer
from backends.settings.language_info import LanguageInfo
from backends.settings.validators import NumericValidator
from cache.voicecache import VoiceCache
from common import *

from backends.audio.builtin_audio_player import BuiltInAudioPlayer
# from backends.audio.player_handler import BasePlayerHandler, WavAudioPlayerHandler
from backends.audio.sound_capabilties import ServiceType
from backends.base import BaseEngineService, SimpleTTSBackend
from backends.settings.i_validators import AllowedValue, INumericValidator, IValidator
from backends.settings.service_types import Services
from backends.settings.settings_map import SettingsMap
from common import utils
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import *
from common.message_ids import MessageUtils
from common.messages import Messages
from common.monitor import Monitor
from common.phrases import Phrase
from common.setting_constants import Backends, Genders, Mode, PlayerMode
from common.settings import Settings
from common.settings_low_level import SettingsProperties
from langcodes import LanguageTagError
from windowNavigation.choice import Choice

module_logger = BasicLogger.get_logger(__name__)


class ESpeakTTSBackend(SimpleTTSBackend):
    """

    """
    ID = Backends.ESPEAK_ID
    service_ID: str = Services.ESPEAK_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    backend_id: str = Backends.ESPEAK_ID
    engine_id: str = Backends.ESPEAK_ID
    displayName: str = 'eSpeak'
    UTF_8: Final[str] = '1'

    voice_map: Dict[str, List[Tuple[str, str, Genders]]] = None
    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False

    class LangInfo:
        _logger: BasicLogger = None

        lang_info_map: Dict[str, ForwardRef('LangInfo')] = {}
        initialized: bool = False

        def __init__(self, locale_id: str, language_code: str, country_code: str,
                     language_name: str, country_name: str, google_tld: str) -> None:
            clz = type(self)
            self.locale_id: str = locale_id
            self.language_code: str = language_code
            self.country_code: str = country_code
            self.language_name: str = language_name
            self.country_name: str = country_name
            self.google_tld: str = google_tld
            clz.lang_info_map[locale_id] = self

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger
        self.process: subprocess.Popen = None
        self.voice_cache: VoiceCache = VoiceCache()

        if not clz._initialized:
            clz._initialized = True
            BaseServices.register(self)

    def init(self):
        super().init()
        clz = type(self)
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
        if cls.voice_map is not None:
            return

        cls.voice_map = {}
        cmd_path = 'espeak-ng'
        args = [cmd_path, '--voices']
        voices = []
        try:
            process = subprocess.run(args, stdin=None, stdout=subprocess.PIPE,
                                     universal_newlines=True,
                                     stderr=None, shell=False, check=True)
            """
             Sample output:
             Pty Language       Age/Gender VoiceName          File                 Other Languages
             5  af              --/M      Afrikaans          gmw/af               
             5  am              --/M      Amharic            sem/am                       
             5  bpy             --/M      Bishnupriya_Manipuri inc/bpy                
             5  chr-US-Qaaa-x-west --/M      Cherokee_          iro/chr              
             5  cmn             --/M      Chinese_(Mandarin,_latin_as_English) sit/cmn              (zh-cmn 5)(zh 5)
             5  cmn-latn-pinyin --/M      Chinese_(Mandarin,_latin_as_Pinyin) sit/cmn-Latn-pinyin  (zh-cmn 5)(zh 5)

            Each line is of the form:
            <priority: int> <language> <age/gender> <voicename> <file> <other_langs>...
            spaces are seperaators. Language tags are based upon BCP-47. In particular,
            iso639-1 and 639-3 are used (among others).
            
            These language tags are used to specify the language, such as:

                fr (French) -- The ISO 639-1 2-letter language code for the language.
            
                NOTE: BCP 47 uses ISO 639-1 codes for languages that are allocated 
                2-letter codes (e.g. using en instead of eng).
            
                yue (Cantonese) -- The ISO 639-3 3-letter language codes for the language.
            
                ta-Arab (Tamil written in the Arabic alphabet) -- The ISO 15924
                 4-letter script code.
            
                NOTE: Where the script is the primary script for the language, the 
                script tag should be omitted.
            
            Language Family
            
                The languages are grouped by the closest language family the language 
                belongs. These language families are defined in ISO 639-5. See also
                 Wikipedia's List of language families for more details.
                
                For example, the Celtic languages (Welsh, Irish Gaelic, Scottish Gaelic,
                 etc.) are listed under the cel language family code.
                Accent (optional)
                
                If necessary, the language tags are also used to specify the accent or 
                dialect of a language, such as:
                
                    es-419 (Spanish (Latin America)) -- The UN M.49 3-number region codes.
                
                    fr-CA (French (Canada)) -- Using the ISO 3166-2 2-letter region codes.
                
                    en-GB-scotland (English (Scotland)) -- This is using the BCP 47
                     variant tags.
                
                 en-GB-x-rp (English (Received Pronunciation)) -- This is using the
                  bcp47-extensions language tags for accents that cannot be described 
                  using the available BCP 47 language tags.
            """
            for line in process.stdout.split('\n'):
                if len(line) > 0:
                    voices.append(line)

            del voices[0]
        except ProcessLookupError:
            rc = -1

        # Read lines of voices, ignoring header

        for voice in voices:
            fields = voice.split(maxsplit=5)
            priority_str: str = fields[0]
            priority: int = int(priority_str)

            lang_str: str = fields[1]
            if lang_str == 'chr-US-Qaaa-x-west':  # IETF will not parse
                lang_str = 'chr-Qaaa-x-west'
            if lang_str == 'en-us-nyc':
                lang_str = 'en-us'
            # locale: str = langcodes.standardize_tag(lang_str)
            lang: langcodes.Language = None
            try:
                lang = langcodes.Language.get(lang_str)
                if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    cls._logger.debug_extra_verbose(f'orig: {lang_str} '
                                                    f'language: {lang.language} '
                                                    f'script: {lang.script} '
                                                    f'territory: {lang.territory} '
                                                    f'extlangs: {lang.extlangs} '
                                                    f'variants: {lang.variants} '
                                                    f'extensions: {lang.extensions} '
                                                    f'private: {lang.private} '
                                                    f'display: '
                                                    f'{lang.display_name(lang.language)}')
            except LanguageTagError:
                cls._logger.exception('')

            age, gender = fields[2].split('/')
            if gender == 'M':
                gender = Genders.MALE
            elif gender == 'F':
                gender = Genders.FEMALE
            else:
                gender = Genders.UNKNOWN

            voice_name = fields[3]
            voice_id = fields[4]  # File
            other_langs: str = ''
            if len(fields) > 5:
                other_langs = fields[5]  # Fields 5 -> eol
            entries: List[Tuple[str, str, Genders]] | None
            entries = cls.voice_map.get(lang.language, None)
            if entries is None:
                entries = []
                cls.voice_map[lang.language] = entries
            entries.append((voice_name, voice_id, gender))
            LanguageInfo.add_language(engine_id=ESpeakTTSBackend.engine_id,
                                      language_id=lang.language,
                                      country_id=lang.territory,
                                      ietf=lang,
                                      region_id='',
                                      gender=Genders.UNKNOWN,
                                      voice=voice_name,
                                      engine_lang_id=lang_str,
                                      engine_voice_id=voice_id,
                                      engine_name_msg_id=Messages.BACKEND_ESPEAK.get_msg_id(),
                                      engine_quality=3,
                                      voice_quality=-1)
        cls.initialized_static = True

    def addCommonArgs(self, args, phrase: Phrase | None = None):
        clz = type(self)
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

    def get_player_mode(self) -> PlayerMode:
        clz = type(self)
        player: IPlayer = self.get_player(self.service_ID)
        player_mode: PlayerMode = Settings.get_player_mode(clz.service_ID)
        return player_mode

    def runCommand(self, phrase: Phrase):
        """
        Run command to generate speech and save voice to a file (mp3 or wave).
        A player will then be scheduled to play the file. Note that there is
        delay in starting speech generator, speech generation, starting player
        up and playing. Consider using caching of speech files as well as
        using PlayerMode.SLAVE_FILE.
        :param phrase:
        :return:
        """
        clz = type(self)
        out_file: Path = phrase.get_cache_path()
        if out_file is None:
            out_file, exists = self.voice_cache.get_path_to_voice_file(phrase)
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'espeak.runCommand outFile: {out_file}\n'
                                      f'text: {phrase.text}')
        clz._logger.debug(f'espeak.runCommand outFile: {out_file}\n'
                          f'text: {phrase.text}')
        env = os.environ.copy()
        args = ['espeak-ng', '-b', clz.UTF_8, '-w', out_file, '--stdin']
        self.addCommonArgs(args)
        try:
            if Constants.PLATFORM_WINDOWS:
                subprocess.run(args,
                               input=f'{phrase.text} ',
                               text=True,
                               shell=False,
                               encoding='utf-8',
                               close_fds=True,
                               env=env,
                               check=True,
                               creationflags=subprocess.DETACHED_PROCESS)
            else:
                subprocess.run(args,
                               input=f'{phrase.text} ',
                               text=True,
                               shell=False,
                               encoding='utf-8',
                               close_fds=True,
                               env=env,
                               check=True)

            clz._logger.debug(f'args: {args}')
        except subprocess.CalledProcessError as e:
            if clz._logger.isEnabledFor(DEBUG):
                clz._logger.exception('')
        return True

    def runCommandAndSpeak(self, phrase: Phrase):
        clz = type(self)
        args = ['espeak', '-b', clz.UTF_8, '--stdin']
        self.addCommonArgs(args, phrase)
        try:
            self.process = subprocess.Popen(args, universal_newlines=True,
                                            encoding='utf-8',
                                            stdin=subprocess.PIPE)
            while (self.process is not None and self.process.poll() is None and
                    BaseEngineService.is_active_engine(engine=clz)):
                Monitor.exception_on_abort(timeout=0.1)
            clz._logger.debug(f'args: {args}')
        except subprocess.SubprocessError as e:
            if clz._logger.isEnabledFor(DEBUG):
                clz._logger.debug('espeak.runCommandAndSpeak Exception: ' + str(e))

    def runCommandAndPipe(self, phrase: Phrase):
        clz = type(self)
        args = ['espeak', '-b', clz.UTF_8, '--stdin', '--stdout']

        self.addCommonArgs(args, phrase)
        self.process = subprocess.Popen(args, stdout=subprocess.PIPE,
                                        encoding='utf-8')
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
    def settingList(cls, setting, *args) -> Tuple[List[Choice], str]:
        if setting == SettingsProperties.LANGUAGE:
            # Returns list of languages and index to the closest match to current
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

            idx: int = 0
            languages: List[Choice]
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

                choice: Choice = Choice(lang, lang, choice_index=idx)
                languages.append(choice)
                idx += 1

            # Now, convert index to default_setting

            default_setting = ''
            if longest_match > 0:
                default_setting = languages[longest_match].value

            return languages, default_setting

        if setting == SettingsProperties.VOICE:
            cls.init_voices()
            current_lang = BaseEngineService.getLanguage()
            current_lang = current_lang[0:2]
            langs = cls.voice_map.keys()  # Not locales
            voices: List[Choice] = []
            idx: int = 0
            for lang in langs:
                if lang.startswith(current_lang):
                    voice_list = cls.voice_map.get(lang, [])
                    for voice_name, voice_id, gender_id in voice_list:
                        # TODO: verify
                        # Voice_name is from command and not translatable?

                        # display_value, setting_value
                        voices.append(Choice(voice_name, voice_id, choice_index=idx))
                        idx += 1
            return voices, ''

        elif setting == SettingsProperties.GENDER:
            # Currently does not meet the needs of the GUI and is
            # probably not that useful at this stage.
            # The main issue, is that this returns language as either
            # the 2-3 char IETF lang code, or as the traditional
            # locale (2-3 char lang and 2-3 char territory + extra).
            # This can be fixed, but not until it proves useful and then
            # figure out what format is preferred.
            cls.init_voices()
            current_lang = Settings.get_language(cls.service_ID)
            voice_list = cls.voice_map.get(current_lang, [])
            genders: List[Choice] = []
            for voice_name, voice_id, gender_id in voice_list:
                # TODO: verify
                # Voice_name is from command and not translatable?

                # Unlike voices and languages, we just return gender ids
                # translation is handled by SettingsDialog

                genders.append(Choice(value=gender_id))

            return genders, ''

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml
            supported_players: List[AllowedValue]
            supported_players = SettingsMap.get_allowed_values(cls.engine_id,
                                                               SettingsProperties.PLAYER)
            choices: List[Choice] = []
            for player in supported_players:
                player: AllowedValue
                player_label = MessageUtils.get_msg(player.value)
                choices.append(Choice(label=player_label, value=player.value,
                                      choice_index=-1, enabled=player.enabled))

            choices = sorted(choices, key=lambda entry: entry.label)
            idx: int = 0
            for choice in choices:
                choice.choice_index = idx
                idx += 1

            default_player: str
            default_player = SettingsMap.get_default_value(cls.engine_id,
                                                           SettingsProperties.PLAYER)
            return choices, default_player
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

    def getVolume(self) -> int:
        # All volumes in settings use a common TTS db scale.
        # Conversions to/from the engine's or player's scale are done using
        # Constraints
        clz = type(self)
        if self.get_player_mode() != PlayerMode.ENGINE_SPEAK:
            volume_val: INumericValidator = SettingsMap.get_validator(
                    clz.service_ID, SettingsProperties.VOLUME)
            volume_val: NumericValidator
            volume: int = volume_val.get_value()
            return volume
        else:
            # volume = Settings.get_volume(clz.service_ID)
            volume_val: INumericValidator = SettingsMap.get_validator(
                    clz.service_ID, SettingsProperties.VOLUME)
            volume_val: NumericValidator
            # volume: int = volume_val.get_tts_value()
            volume: int = volume_val.get_value()

        return volume

    def get_pitch(self) -> int:
        # All pitches in settings use a common TTS scale.
        # Conversions to/from the engine's or player's scale are done using
        # Constraints
        clz = type(self)
        if self.get_player_mode != PlayerMode.ENGINE_SPEAK:
            pitch_val: INumericValidator = SettingsMap.get_validator(
                    clz.service_ID, SettingsProperties.PITCH)
            pitch_val: NumericValidator
            pitch: int = pitch_val.get_value()
            return pitch
        else:
            # volume = Settings.get_volume(clz.service_ID)
            pitch_val: INumericValidator = SettingsMap.get_validator(
                    clz.service_ID, SettingsProperties.PITCH)
            pitch_val: NumericValidator
            # volume: int = volume_val.get_tts_value()
            pitch: int = pitch_val.get_value()

        return pitch

    def get_speed(self) -> int:
        """
            espeak's speed is measured in 'words/minute' with a default
            of 175. Limits not specified, appears to be about min=60 with no
            max. Linear

            By contrast, mplayer linearly adjusts the 'speed' of play with
            0.25 playing at 1/4th speed (or 4x the time)
        :return:
        """
        # All settings use a common TTS scale.
        # Conversions to/from the engine's or player's scale are done using
        # Constraints
        clz = type(self)
        if self.get_player_mode != PlayerMode.ENGINE_SPEAK:
            # Let player decide speed
            speed = 176  # Default espeak speed of 176 words per minute.
            return speed
        else:
            speed_val: INumericValidator = SettingsMap.get_validator(
                    clz.service_ID, SettingsProperties.SPEED)
            speed_val: NumericValidator
            speed: int = speed_val.get_value()
        return speed

    @staticmethod
    def available() -> bool:
        available: bool = True
        try:
            cmd_path = 'espeak-ng'
            args = [cmd_path, '--version']
            try:
                process = subprocess.run(args, stdin=None, stdout=subprocess.PIPE,
                                         universal_newlines=True,
                                         stderr=None, shell=False, check=True)

                found: bool = False
                for line in process.stdout.split('\n'):
                    if len(line) > 0:
                        if line.find('eSpeak NG text_to_speech'):
                            found = True
                            break
                if not found:
                    available = False
            except ProcessLookupError:
                available = False
        except Exception:
            available = False

        # eSpeak has built-in player
        return available

'''
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
        self.initialized = True

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
        clz = type(self)
        self.voice = clz.getSetting(SettingsProperties.VOICE)

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
'''
