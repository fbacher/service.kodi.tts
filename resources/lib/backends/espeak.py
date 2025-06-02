# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import ctypes.util
import os
import subprocess
import sys

import xbmc

import langcodes

from pathlib import Path

from backends.espeak_settings import ESpeakSettings
from backends.players.iplayer import IPlayer
from backends.settings.language_info import LanguageInfo
from backends.settings.settings_helper import SettingsHelper
from backends.settings.validators import NumericValidator
from backends.transcoders.trans import TransCode
from cache.cache_file_state import CacheFileState
from cache.voicecache import VoiceCache
from cache.common_types import CacheEntryInfo
from common import *

from backends.audio.sound_capabilities import ServiceType
from backends.base import BaseEngineService, SimpleTTSBackend
from backends.settings.i_validators import AllowedValue, INumericValidator, IValidator
from backends.settings.service_types import ServiceKey, Services, ServiceID
from backends.settings.settings_map import Status, SettingsMap
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import *
from common.message_ids import MessageId
from common.monitor import Monitor
from common.phrases import Phrase
from common.setting_constants import (AudioType, Backends, Genders, Mode, PlayerMode,
                                      Players)
from common.settings import Settings
from common.settings_low_level import SettingProp
from langcodes import LanguageTagError
from windowNavigation.choice import Choice

MY_LOGGER = BasicLogger.get_logger(__name__)


class VoiceData:

    def __init__(self, lang_id: str,  langcodes_lang: langcodes.Language,
                 voice_name: str, voice_id: str, gender: Genders,
                 available: bool = False) -> None:
        self._lang_id: str = lang_id
        self._langcodes_lang: langcodes.Language = langcodes_lang
        self._voice_name: str = voice_name
        self._voice_id: str = voice_id
        self._gender: Genders = gender
        self._available: bool = available

    @property
    def lang_id(self) -> str:
        return self._lang_id

    @property
    def langcodes_lang(self) -> langcodes.Language:
        return self._langcodes_lang

    @property
    def voice_name(self) -> str:
        return self._voice_name

    @property
    def voice_id(self) -> str:
        return self._voice_id

    @property
    def gender(self) -> Genders:
        return self._gender

    @property
    def available(self) -> bool:
        return self._available

    @available.setter
    def available(self, available: bool) -> None:
        self._available = available

    def __str__(self) -> str:
        return (f'lang: {self.lang_id} voice_name: {self.voice_name} '
                f'voice_id: {self.voice_id} gender: {self.gender} avail: {self.available}')

class ESpeakTTSBackend(SimpleTTSBackend):
    """

    """
    ID = Backends.ESPEAK_ID
    service_id: str = Services.ESPEAK_ID
    service_type: ServiceType = ServiceType.ENGINE
    engine_id: str = Backends.ESPEAK_ID
    service_key: ServiceID = ServiceKey.ESPEAK_KEY
    OUTPUT_FILE_TYPE: str = '.wav'
    displayName: str = 'eSpeak'
    UTF_8: Final[str] = '1'

    voice_map: Dict[str, List[VoiceData]] = None
    FILE_DIR_TO_REAL_DIR: Dict[str, str] = {'mb': 'mbrola'}
    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False
    _available: bool | None = None
    player_key: ServiceID = service_key.with_prop(SettingProp.PLAYER)
    volume_key: ServiceID = service_key.with_prop(SettingProp.VOLUME)
    pitch_key: ServiceID = service_key.with_prop(SettingProp.PITCH)
    speed_key: ServiceID = service_key.with_prop(SettingProp.SPEED)
    cmd_path: Path = Constants.ESPEAK_PATH / 'espeak-ng'
    data_path: Path = Constants.ESPEAK_DATA_PATH
    if Constants.PLATFORM_WINDOWS:
        cmd_path = Constants.ESPEAK_PATH_WINDOWS / 'espeak-ng'
        data_path = Constants.ESPEAK_DATA_PATH_WINDOWS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        self.process: subprocess.Popen | None = None
        MY_LOGGER.debug(f'eSpeak service_key: {ESpeakTTSBackend.service_key}')
        self.voice_cache: VoiceCache = VoiceCache(ESpeakTTSBackend.service_key)

        if not clz._initialized:
            clz._initialized = True
            BaseServices.register(self)

    def init(self):
        super().init()
        clz = type(self)
        self.process: subprocess.Popen | None = None
        self.update()

    def get_voice_cache(self) -> VoiceCache:
        return self.voice_cache

    '''
    @classmethod
    def register_me(cls, what: Type[ITTSBackendBase]) -> None:
        MY_LOGGER.debug(f'Registering {repr(what)}')
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
        env = os.environ.copy()
        args = [str(cls.cmd_path), '-b', cls.UTF_8, '--voices',
                f'--path={str(cls.data_path)}']
        voices = []
        try:
            completed: subprocess.CompletedProcess | None = None
            if Constants.PLATFORM_WINDOWS:
                MY_LOGGER.info(f'Running command: Windows: {args}')
                completed = subprocess.run(args, stdin=None, capture_output=True,
                                           text=True, env=env, close_fds=True,
                                           encoding='utf-8', shell=False, check=True,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                MY_LOGGER.info(f'Running command: Linux args: {args}')
                completed = subprocess.run(args, stdin=None, capture_output=True,
                                           text=True, env=env, close_fds=True,
                                           encoding='utf-8', shell=False, check=True)

            """
             Sample output:
             Pty Language       Age/Gender VoiceName          File                 
             Other Languages
             5  af              --/M      Afrikaans          gmw/af               
             5  am              --/M      Amharic            sem/am                       
             5  bpy             --/M      Bishnupriya_Manipuri inc/bpy                
             5  chr-US-Qaaa-x-west --/M      Cherokee_          iro/chr              
             5  cmn             --/M      Chinese_(Mandarin,_latin_as_English) sit/cmn  
                         (zh-cmn 5)(zh 5)
             5  cmn-latn-pinyin --/M      Chinese_(Mandarin,_latin_as_Pinyin) 
             sit/cmn-Latn-pinyin  (zh-cmn 5)(zh 5)

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
            for line in completed.stdout.split('\n'):
                MY_LOGGER.debug(f'line: {line}')
                if len(line) > 0:
                    voices.append(line)

            del voices[0]
        except ProcessLookupError:
            MY_LOGGER.exception('')
            rc = -1

        # Read lines of voices, ignoring header
        for voice in voices:
            fields = voice.split(maxsplit=5)
            MY_LOGGER.debug(f'fields: {fields}')
            priority_str: str = fields[0]  # Higher is better
            priority: int = int(priority_str)

            lang_id: str = fields[1]
            if lang_id == 'chr-US-Qaaa-x-west':  # IETF will not parse
                lang_id = 'chr-Qaaa-x-west'
            if lang_id == 'en-us-nyc':
                lang_id = 'en-us'
            # locale: str = langcodes.standardize_tag(lang_id)
            langcodes_lang: langcodes.Language | None = None
            try:
                langcodes_lang = langcodes.Language.get(lang_id)
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'orig: {lang_id} '
                                       f'language: {langcodes_lang.language} '
                                       f'script: {langcodes_lang.script} '
                                       f'territory: {langcodes_lang.territory} '
                                       f'extlangs: {langcodes_lang.extlangs} '
                                       f'variants: {langcodes_lang.variants} '
                                       f'extensions: {langcodes_lang.extensions} '
                                       f'private: {langcodes_lang.private} '
                                       f'display: '
                                       f'{langcodes_lang.display_name(langcodes_lang.language)}')
            except LanguageTagError:
                MY_LOGGER.exception('')

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
            entries: List[VoiceData] | None
            entries = cls.voice_map.setdefault(langcodes_lang.language, [])
            entries.append(VoiceData(lang_id, langcodes_lang, voice_name, voice_id,
                                     gender))

        # Discover the directories of voice files referenced by the list of voices
        voice_files_by_directory: Dict[str, Dict[str, None]] = {}
        for lang, entries in cls.voice_map.items():
            MY_LOGGER.debug(f'lang: {lang} entries: {entries}')
            for entry in entries:
                entry: VoiceData
                MY_LOGGER.debug(f'entry: {entry}')
                voice_file_path: Path = Path(entry.voice_id)
                subdir_name: str = str(voice_file_path.parent)
                MY_LOGGER.debug(f'subdir_name: {subdir_name}')
                subdir_name = cls.FILE_DIR_TO_REAL_DIR.get(subdir_name)
                if subdir_name is not None:
                    voices_in_subdir: Dict[str, None]  # used as a set
                    voices_in_subdir = voice_files_by_directory.setdefault(subdir_name, {})
                    # Only need to scan a subdir once to capture all voices in it
                    if len(voices_in_subdir) == 0:
                        for voice_file in cls.get_installed_voice_files(subdir_name):
                            voices_in_subdir[voice_file] = None
                    # Mark any entry that has its voice_file in the subdir
                    voice_file: str = str(voice_file_path.name)
                    if voice_file in voices_in_subdir:
                        entry.available = True
                else:
                    entry.available = True

                if entry.available:
                    # NOTE: Omitting voices that are NOT installed

                    langcodes_lang: langcodes.Language = entry.langcodes_lang
                    LanguageInfo.add_language(engine_key=ESpeakTTSBackend.service_key,
                                              language_id=langcodes_lang.language,
                                              country_id=langcodes_lang.territory,
                                              ietf=langcodes_lang,
                                              region_id='',
                                              gender=Genders.UNKNOWN,
                                              voice=entry.voice_name,
                                              engine_lang_id=entry.lang_id,
                                              engine_voice_id=entry.voice_id,
                                              engine_name_msg_id=MessageId.ENGINE_ESPEAK,
                                              engine_quality=3,
                                              voice_quality=priority)

        cls.initialized_static = True

    @classmethod
    def get_installed_voice_files(cls, subdir: str) -> List[str]:
        """
        Supplements the info that espeak-ng -voices gives by checking to see
        what voice files are installed for a given lang.

        Espeak-ng --voices=<lang> can
        return voices which are defined, but NOT installed. Mbrola voices are
        a case in point. The voice files are typically stored in subdirectories
        of the data-directory. Mbrola files are in the 'mb' subdirectory. The
        subdirectory name comes from the --voices command.

        LIMITATIONS: ONLY looks for data files stored in the default data-directory.

        :param subdir: data-directory subdir to look for voice files
        :return List[str]: A list of voice file names found from the given subdir
        """
        voice_files: List[str] = []
        try:
            subdir_path: Path = cls.data_path / subdir
            for voice_file in subdir_path.glob('*'):
                voice_file: Path
                voice_files.append(str(voice_file))
        except Exception:
            MY_LOGGER.exception('')
        MY_LOGGER.debug(f'voice_files: {voice_files}')
        return voice_files

    def addCommonArgs(self, args, phrase: Phrase | None = None):
        clz = type(self)
        voice_id = Settings.get_voice(clz.service_key)
        #  voice_id = 'gmw/en-US'
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
        player: IPlayer = self.get_player(self.service_key)
        player_mode: PlayerMode = Settings.get_player_mode(clz.service_key)
        MY_LOGGER.debug(f'player_mode: {player_mode}')
        return player_mode

    def get_cached_voice_file(self, phrase: Phrase,
                              generate_voice: bool = True) -> bool:
        """
        Return cached file if present, otherwise, generate speech, place in cache
        and return cached speech.

        Very similar to runCommand, except that the cached files are expected
        to be sent to a slave player, or some other player that can play a sound
        file.
        :param phrase: Contains the text to be voiced as wll as the path that it
                       is or will be located.
        :param generate_voice: If true, then wait a bit to generate the speech
                               file.
        :return: True if the voice file was handed to a player, otherwise False
        """
        clz = type(self)
        player_key: ServiceID = Settings.get_player_key()
        MY_LOGGER.debug(f'phrase: {phrase.get_text()} {phrase.get_debug_info()} '
                        f'cache_path: {phrase.get_cache_path()} use_cache: '
                        f'{Settings.is_use_cache()}')
        cache_info: CacheEntryInfo
        cache_info = self.get_voice_cache().get_path_to_voice_file(phrase,
                                                      use_cache=Settings.is_use_cache())
        MY_LOGGER.debug(f'cache_info: {cache_info} player_key: {player_key}')
        MY_LOGGER.debug(f'cache_file_state: {phrase.cache_file_state()} '
                        f'cache_path: {phrase.get_cache_path()} '
                        f'temp_path: {cache_info.temp_voice_path}')
        # Wave files only added to cache when SFX is used.

        # This Only checks if a .wav file exists. That is good enough, the
        # player should check for existence of what it wants and to transcode
        # if needed.
        is_sfx_player: bool = player_key.service_id == Players.SFX
        if is_sfx_player and phrase.cache_file_state() == CacheFileState.OK:
            return True

        # If audio in cache is suitable for player, then we are done.
        result: CacheEntryInfo
        result = self.voice_cache.get_path_to_voice_file(phrase, use_cache=True)
        if result.audio_exists:
            return True

        success: bool = False
        wave_file: Path = self.runCommand(phrase)
        if wave_file is not None:
            result: CacheEntryInfo
            result = self.voice_cache.get_path_to_voice_file(phrase, use_cache=True)
            mp3_file = result.final_audio_path
            trans_id: str = Settings.get_transcoder(clz.service_key)
            MY_LOGGER.debug(f'service_id: {self.engine_id} trans_id: {trans_id}')
            success = TransCode.transcode(trans_id=trans_id,
                                          input_path=wave_file,
                                          output_path=mp3_file,
                                          remove_input=True)
            if success:
                phrase.text_exists(check_expired=False, active_engine=self)
            MY_LOGGER.debug(f'success: {success} wave_file: {wave_file} mp3: {mp3_file}')
        return success

    def runCommand(self, phrase: Phrase) -> Path | None:
        """
        Run command to generate speech and save voice to a file (mp3 or wave).
        A player will then be scheduled to play the file. Note that there is
        delay in starting speech generator, speech generation, starting player
        up and playing. Consider using caching of speech files as well as
        using PlayerMode.SLAVE_FILE.
        :param phrase:
        :return: If Successful, path of the wave file (may not have a suffix!)
                 Otherwise, None
        """
        clz = type(self)
        """
        Output file choices:
            eSpeak can:
            - Only output wave format
            - Can write to file, or pipe, or directly voice
            - Here we only care about writing to file.
            Destination:
            - to player
            - to cache, then player
            - to mp3 converter, to cache, then player
            Player prefers wave (since that is native to eSpeak), but can be 
            mp3
            Cache strongly prefers .mp3 (space), but can do wave (useful for
            fail-safe, when there is no mp3 player configured)).
            
        Assumptions:
            any cache has been checked to see if already voiced
        """
        sfx_player: bool = Settings.get_player_key().setting_id == Players.SFX
        use_cache: bool = Settings.is_use_cache() or sfx_player
        # The SFX player is used when NO player is available. SFX is Kodi's
        # internal player with limited functionality. Requires Wave.
        audio_exists: bool = False
        result: CacheEntryInfo | None = None
        # For SFX, save eSpeak .wav directly into the cache
        result = self.voice_cache.get_path_to_voice_file(phrase, use_cache=use_cache)
        audio_exists = result.audio_exists
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'espeak.runCommand '
                            f'result: {result} '
                            f'text: {phrase.text}')
        if audio_exists:
            return result.final_audio_path
        env = os.environ.copy()
        args = [str(clz.cmd_path), '-b', clz.UTF_8, '-w',
                str(result.temp_voice_path), '--stdin',
                f'--path={str(clz.data_path)}']
        self.addCommonArgs(args)
        try:
            if Constants.PLATFORM_WINDOWS:
                MY_LOGGER.info(f'Running command: WINDOWS args: {args}')
                subprocess.run(args,
                               input=f'{phrase.text} ',
                               text=True,
                               shell=False,
                               encoding='utf-8',
                               close_fds=True,
                               env=env,
                               check=True,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                MY_LOGGER.info(f'Running command: LINUX: args {args}')
                subprocess.run(args,
                               input=f'{phrase.text} ',
                               text=True,
                               shell=False,
                               encoding='utf-8',
                               close_fds=True,
                               env=env,
                               check=True)

            if not result.temp_voice_path.exists():
                MY_LOGGER.info(f'voice file not created: {result.temp_voice_path}')
                return None
            if result.temp_voice_path.stat().st_size <= 1000:
                MY_LOGGER.info(f'voice file too small. Deleting: '
                               f'{result.temp_voice_path}')
                try:
                    result.temp_voice_path.unlink(missing_ok=True)
                except:
                    MY_LOGGER.exception('')
                return None
            try:
                result.temp_voice_path.rename(result.final_audio_path)
                phrase.set_cache_path(cache_path=result.final_audio_path,
                                      text_exists=phrase.text_exists(check_expired=False,
                                                                     active_engine=self),
                                      temp=not result.use_cache)
            except Exception:
                MY_LOGGER.exception(f'Could not rename {result.temp_voice_path} '
                                    f'to {result.final_audio_path}')
                try:
                    result.temp_voice_path.unlink(missing_ok=True)
                except:
                    MY_LOGGER.exception(f'Can not delete {result.temp_voice_path}')
                return None
        except subprocess.CalledProcessError as e:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.exception('')
                return None
        return result.final_audio_path  # Wave file

    def runCommandAndSpeak(self, phrase: Phrase):
        clz = type(self)
        env = os.environ.copy()
        args = [str(clz.cmd_path), '-b', clz.UTF_8, '--stdin',
                str(clz.data_path)]
        self.addCommonArgs(args)
        MY_LOGGER.debug(f'args: {args}')
        try:
            if Constants.PLATFORM_WINDOWS:
                MY_LOGGER.info(f'Running command: Windows')
                subprocess.run(args,
                               input=f'{phrase.text} ',
                               text=True,
                               shell=False,
                               encoding='utf-8',
                               close_fds=True,
                               env=env,
                               check=True,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                MY_LOGGER.info(f'Running command: Linux')
                subprocess.run(args,
                               input=f'{phrase.text} ',
                               text=True,
                               shell=False,
                               encoding='utf-8',
                               close_fds=True,
                               env=env,
                               check=True)
        except subprocess.SubprocessError as e:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('espeak.runCommandAndSpeak Exception: ' + str(e))

    def runCommandAndPipe(self, phrase: Phrase):
        clz = type(self)
        env = os.environ.copy()
        args = [str(clz.cmd_path), '-b', clz.UTF_8, '--stdin', '--stdout',
                f'--path={str(clz.data_path)}']
        self.addCommonArgs(args)
        MY_LOGGER.debug(f'args: {args}')
        try:
            # Process will block until reader for PIPE opens
            # Be sure to close self.process.stdout AFTER second process starts
            # ex:
            # p1 = Popen(["dmesg"], stdout=PIPE)
            # p2 = Popen(["grep", "hda"], stdin=p1.stdout, stdout=PIPE)
            # p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
            # output = p2.communicate()[0]
            #
            # The p1.stdout.close() call after starting the p2 is important in order
            # for p1 to receive a SIGPIPE if p2 exits before p1.
            if Constants.PLATFORM_WINDOWS:
                MY_LOGGER.info(f'Running command: Windows')
                self.process = subprocess.run(args,
                                              input=f'{phrase.text} ',
                                              stdout=subprocess.PIPE,
                                              text=True,
                                              shell=False,
                                              encoding='utf-8',
                                              close_fds=True,
                                              env=env,
                                              check=True,
                                              creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                MY_LOGGER.info(f'Running command: Linux')
                self.process = subprocess.run(args,
                                              input=f'{phrase.text} ',
                                              stdout=subprocess.PIPE,
                                              text=True,
                                              shell=False,
                                              encoding='utf-8',
                                              close_fds=True,
                                              env=env,
                                              check=True)
        except subprocess.SubprocessError as e:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('espeak.runCommandAndPipe Exception: ' + str(e))
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
            MY_LOGGER.exception("")

    @classmethod
    def load_languages(cls):
        """
        Discover eSpeak's supported languages and report results to
        LanguageInfo.
        :return:
        """
        MY_LOGGER.debug(f'In load_languages')
        cls.init_voices()

    '''
    @classmethod
    def settingList(cls, setting, *args) -> Tuple[List[Choice], str]:
        if setting == SettingProp.LANGUAGE:
            # Returns list of languages and index to the closest match to current
            # locale
            MY_LOGGER.debug(f'In LANGUAGE')
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

        if setting == SettingProp.VOICE:
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

        elif setting == SettingProp.GENDER:
            # Currently does not meet the needs of the GUI and is
            # probably not that useful at this stage.
            # The main issue, is that this returns language as either
            # the 2-3 char IETF lang code, or as the traditional
            # locale (2-3 char lang and 2-3 char territory + extra).
            # This can be fixed, but not until it proves useful and then
            # figure out what format is preferred.
            cls.init_voices()
            current_lang = Settings.get_language(cls.service_key)
            voice_list = cls.voice_map.get(current_lang, [])
            genders: List[Choice] = []
            idx: int = 0
            for voice_name, voice_id, gender_id in voice_list:
                # TODO: verify
                # Voice_name is from command and not translatable?

                # Unlike voices and languages, we just return gender ids.
                # Translation is handled by SettingsDialog. Label and
                # choice_index are ignored
                genders.append(Choice(label='', value=gender_id, choice_index=idx))
                idx += 1
            return genders, ''

        
        elif setting == SettingProp.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml
            supported_players: List[AllowedValue]
            supported_players = SettingsMap.get_allowed_values(cls.player_key)
            choices: List[Choice] = []
            for player in supported_players:
                player: AllowedValue
                player_label = Players.get_msg(player.value)
                choices.append(Choice(label=player_label, value=player.value,
                                      choice_index=-1, enabled=player.enabled))

            choices = sorted(choices, key=lambda entry: entry.label)
            idx: int = 0
            for choice in choices:
                choice.choice_index = idx
                idx += 1

            default_player: str
            default_player = SettingsMap.get_default_value(cls.runCommand)
            return choices, default_player
        
        return None
    '''

    '''
    @classmethod
    def get_default_language(cls) -> str:
        languages: List[str]
        default_lang: str
        languages, default_lang = cls.settingList(SettingProp.LANGUAGE)
        return default_lang
    '''

    '''
    @classmethod
    def get_voice_id_for_name(cls, name):
        if len(cls.voice_map) == 0:
            cls.settingList(SettingProp.VOICE)
        return cls.voice_map[name]
    '''

    def getVolume(self) -> int:
        # All volumes in settings use a common TTS db scale.
        # Conversions to/from the engine's or player's scale are done using
        # Constraints
        clz = type(self)
        if self.get_player_mode() != PlayerMode.ENGINE_SPEAK:
            volume_val: INumericValidator = SettingsMap.get_validator(clz.volume_key)
            volume_val: NumericValidator
            volume: int = volume_val.get_value()
            return volume
        else:
            # volume = Settings.get_volume(clz.setting_id)
            # volume_val: INumericValidator = SettingsMap.get_validator(
            #         SettingProp.TTS_SERVICE, SettingProp.VOLUME)
            # volume_val: NumericValidator
            # volume: int = volume_val.get_tts_value()
            # volume: int = volume_val.get_value()
            volume: int = 100  # Default
        return volume

    def get_pitch(self) -> int:
        # All pitches in settings use a common TTS scale.
        # Conversions to/from the engine's or player's scale are done using
        # Constraints
        clz = type(self)
        if self.get_player_mode != PlayerMode.ENGINE_SPEAK:
            pitch_val: INumericValidator = SettingsMap.get_validator(clz.pitch_key)
            pitch_val: NumericValidator
            pitch: int = pitch_val.get_value()
            return pitch
        else:
            # volume = Settings.get_volume(clz.setting_id)
            pitch_val: INumericValidator = SettingsMap.get_validator(clz.pitch_key)
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
            speed_val: INumericValidator = SettingsMap.get_validator(clz.speed_key)
            speed_val: NumericValidator
            speed: int = speed_val.get_value()
        return speed

    @classmethod
    def update_voice_path(cls, phrase: Phrase) -> None:
        """
        If a language is specified for this phrase, then modify any
        cache path to reflect the chosen language and territory.
        :param phrase:
        :return:
        """

        if Settings.is_use_cache() and not phrase.is_lang_territory_set():
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'lang: {phrase.language} \n'
                                   f'voice: {phrase.voice}\n'
                                   f'lang_dir: {phrase.lang_dir}\n'
                                   f'')
            locale: str = phrase.language  # IETF format
            _, kodi_locale, _, ietf_lang = LanguageInfo.get_kodi_locale_info()
            # MY_LOGGER.debug(f'orig Phrase locale: {locale}')
            if locale is None:
                locale = kodi_locale
            ietf_lang: langcodes.Language = langcodes.get(locale)
            # MY_LOGGER.debug(f'locale: {locale}')
            phrase.set_lang_dir(ietf_lang.language)
            territory: str = '-'
            if ietf_lang.territory is not None:
                territory = ietf_lang.territory.lower()
            phrase.set_territory_dir(territory)
        return
