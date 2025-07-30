# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import json
import os
import subprocess
import sys
from io import StringIO

import langcodes

from pathlib import Path, WindowsPath

from backends.ispeech_generator import ISpeechGenerator
from backends.settings.language_info import LanguageInfo
from backends.settings.validators import NumericValidator
from backends.transcoders.trans import TransCode
from cache.voicecache import VoiceCache
from cache.cache_file_state import CacheFileState
from cache.common_types import CacheEntryInfo
from common.typing import *

from backends.audio.sound_capabilities import ServiceType
from backends.base import BaseEngineService, SimpleTTSBackend
from backends.settings.i_validators import AllowedValue, INumericValidator
from backends.settings.service_types import LabeledType, ServiceID, ServiceKey, Services
from backends.settings.settings_map import SettingsMap
from common.base_services import BaseServices
from common.constants import Constants, ReturnCode
from common.exceptions import ExpiredException
from common.logger import *
from common.message_ids import MessageId
from common.phrases import Phrase, PhraseList
from common.setting_constants import (Backends, Genders, PlayerMode,
                                      Players)
from common.settings import Settings
from common.settings_low_level import SettingProp
from langcodes import LanguageTagError
from windowNavigation.choice import Choice

MY_LOGGER = BasicLogger.get_logger(__name__)


class Results:
    """
        Contains results of background thread/process
        Provides ability for caller to get status/results
        Also allows caller to abandon results, but allow task to continue
        quietly. This is useful for downloading/generating speech which may
        get canceled before finished, but results can be cached for later use
    """

    def __init__(self):
        self.rc: ReturnCode = ReturnCode.NOT_SET
        # self.download: io.BytesIO = io.BytesIO(initial_bytes=b'')
        self.finished: bool = False
        self.phrase: Phrase | None = None

    def get_rc(self) -> ReturnCode:
        return self.rc

    # def get_download_bytes(self) -> memoryview:
    #     return self.download.getbuffer()

    # def get_download_stream(self) -> io.BytesIO:
    #     return self.download

    def is_finished(self) -> bool:
        return self.finished

    def get_phrase(self) -> Phrase:
        return self.phrase

    def set_finished(self, finished: bool) -> None:
        self.finished = finished

    # def set_download(self, data: bytes | io.BytesIO | None) -> None:
    #     self.download = data

    def set_rc(self, rc: ReturnCode) -> None:
        self.rc = rc

    def set_phrase(self, phrase: Phrase) -> None:
        self.phrase = phrase


class SpeechGenerator(ISpeechGenerator):

    def __init__(self, generator: ISpeechGenerator, engine: SimpleTTSBackend) -> None:
        self.download_results: Results = Results()
        self.engine: SimpleTTSBackend = engine
        self.voice_cache: VoiceCache = VoiceCache(engine.service_key)

    def set_rc(self, rc: ReturnCode) -> None:
        self.download_results.set_rc(rc)

    def get_rc(self) -> ReturnCode:
        return self.download_results.get_rc()

    def set_phrase(self, phrase: Phrase) -> None:
        self.download_results.set_phrase(phrase)

    # def get_download_bytes(self) -> memoryview:
    #     return self.download_results.get_download_bytes()

    def set_finished(self) -> None:
        self.download_results.set_finished(True)

    def is_finished(self) -> bool:
        return self.download_results.is_finished()


class PowerShellTTS(SimpleTTSBackend):
    """
        Use Windows built-in TTS via powershell script
    """
    ID = Backends.POWERSHELL_ID
    service_id: str = Services.POWERSHELL_ID
    service_key: ServiceID
    service_type: ServiceType = ServiceType.ENGINE
    service_key = ServiceID(service_type, service_id)
    OUTPUT_FILE_TYPE: str = '.wav'
    displayName: str = MessageId.ENGINE_POWERSHELL.get_msg()
    UTF_8: Final[str] = '1'

    POWERSHELL_PATH = "powershell.exe"  # POWERSHELL EXE PATH
    #  ps_script_path = "C:\\PowershellScripts\\FTP_UPLOAD.PS1"
    script_dir: Path = Constants.SHELL_SCRIPTS_PATH
    ps_script = 'voice_sapi.ps1'
    script_path: Path = script_dir / ps_script
    voice: str = 'Zira'
    voice_map: Dict[str, List[Tuple[str, str, Genders]]] = None
    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False
    _voices_initialized: bool = False
    suffix: int = 0

    # Maps a voice_id to the directory_name for cache entries sharing this voice_id
    _voice_dir_for_id: Dict[str, str] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        self.process: subprocess.Popen | None = None
        self.completed_process: subprocess.CompletedProcess | None = None
        self.voice_cache: VoiceCache = VoiceCache(clz.service_key)

        if not clz._initialized:
            clz._initialized = True
            BaseServices.register(self)

    def init(self):
        super().init()
        clz = type(self)
        self.init_process()
        self.update()

    def init_process(self) -> None:
        if self.process is not None:
            try:
                if self.process.poll() is None:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Killing process')
                    self.process.kill()
            except Exception:
                MY_LOGGER.exception('previous process not None')
        self.process: subprocess.Popen | None = None

    def get_voice_cache(self) -> VoiceCache:
        return self.voice_cache

    @classmethod
    def get_backend_id(cls) -> str:
        return cls.service_id

    @classmethod
    def init_voices(cls):
        if cls._voices_initialized:
            return
        cls.init_sapi_voices()
        # cls.init_one_core_voices()
        cls._voices_initialized = True

    @classmethod
    def get_cache_id(cls, voice_id: str) -> str:
        """
        Given an official SAPI MS Name of the form: "Microsoft David Desktop"
        While a OneCore voice is of the form: "Microsoft David"

        Strip off the redundant "Microsoft"
        Reduce 'Desktop" to 'DT'
        The cache_file directory becomes 'David_DT'

        :param voice_id: Name of voice from application
        :return: Tuple[
        """
        cache_id: str = voice_id
        segments: List[str] = voice_id.split(' ')
        if len(segments) == 0:
            MY_LOGGER.warning('SAPI voice id incorrect format: {voice_id}')
        else:
            cache_id = segments[1]
            if len(segments) == 3:
                name = f'{cache_id}_DT'
        MY_LOGGER.info(f'cache_id: {cache_id}')
        cls._voice_dir_for_id[voice_id] = cache_id
        return cache_id

    @classmethod
    def get_sapi_json(cls) -> List[Dict[str, str | List[Dict[str, Any]]]] | None:
        env = os.environ.copy()
        win_path: WindowsPath
        win_path = WindowsPath(Constants.CONFIG_SCRIPTS_DIR_WINDOWS / 'sapi_voices.ps1')
        MY_LOGGER.debug(f'{win_path} exists: {win_path.exists()}')
        cmd_args: List[str] = ['powershell.exe', str(win_path)]
        MY_LOGGER.debug(f'Running command: Windows args: {cmd_args}')
        rc: int = -1
        json_str: str | None = None
        try:
            completed: subprocess.CompletedProcess
            completed = subprocess.run(cmd_args, stdin=None, capture_output=True,
                                       text=True, env=env, close_fds=True,
                                       encoding='utf-8', shell=False, check=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            rc = completed.returncode
            if rc != 0:
                MY_LOGGER.debug(f'config output: {completed.stdout}')
            else:
                json_str = completed.stdout
        except subprocess.CalledProcessError:
            MY_LOGGER.exception('')
        except OSError:
            MY_LOGGER.exception('')
        except Exception:
            MY_LOGGER.exception('')

        voice_data: List[Dict[str, str | List[Dict[str, Any]]]] | None = None
        try:
            if json_str is None:
                MY_LOGGER.debug(f'No SAPI voices returned')
                return None
            voice_data = json.loads(json_str)
        except Exception:
            MY_LOGGER.exception('')
        return voice_data

    @classmethod
    def init_sapi_voices(cls):
        try:
            voice_data: List[Dict[str, str | List[Dict[str, Any]]]] | None
            voice_data = cls.get_sapi_json()
            if voice_data is None:
                return
            voice_data: List[Dict[str, str | Dict[str, str]]]
            for voice_entry in voice_data:
                voice_entry: Dict[str, str | Dict[str, str]]
                """
                   SAPI Voice Json Format:
                   List[Dict[prop, value]]
                 {
        "Gender":  1,
        "Age":  30,
        "Name":  "Microsoft David Desktop",
        "Culture":  {
                        "Parent":  "en",
                        "LCID":  1033,
                        "KeyboardLayoutId":  1033,
                        "Name":  "en-US",
                        "IetfLanguageTag":  "en-US",
                        "DisplayName":  "English (United States)",
                        "NativeName":  "English (United States)",
                        "EnglishName":  "English (United States)",
                        "TwoLetterISOLanguageName":  "en",
                        "ThreeLetterISOLanguageName":  "eng",
                        "ThreeLetterWindowsLanguageName":  "ENU",
                        "CompareInfo":  "CompareInfo - en-US",
                        "TextInfo":  "TextInfo - en-US",
                        "IsNeutralCulture":  false,
                        "CultureTypes":  70,
                        "NumberFormat":  "System.Globalization.NumberFormatInfo",
                        "DateTimeFormat":  "System.Globalization.DateTimeFormatInfo",
                        "Calendar":  "System.Globalization.GregorianCalendar",
                        "OptionalCalendars":  "System.Globalization.GregorianCalendar System.Globalization.GregorianCalendar",
                        "UseUserOverride":  false,
                        "IsReadOnly":  false
                    },
        "Id":  "TTS_MS_EN-US_DAVID_11.0",
        "Description":  "Microsoft David Desktop - English (United States)",
        "SupportedAudioFormats":  [

                                  ],
        "AdditionalInfo":  {
                               "Age":  "Adult",
                               "Gender":  "Male",
                               "Language":  "409",
                               "Name":  "Microsoft David Desktop",
                               "SharedPronunciation":  "",
                               "SpLexicon":  "{0655E396-25D0-11D3-9C26-00C04F8EF87C}",
                               "Vendor":  "Microsoft",
                               "Version":  "11.0"
                           }
    },
                   """
                #  v_description: str = voice_entry.get('Description')
                v_name: str = voice_entry.get('Name')
                v_id: str = v_name
                _: str = cls.get_cache_id(v_name)
                v_culture: Dict[str, str]
                v_culture = voice_entry.get('Culture')
                v_additional_info: Dict[str, str]
                v_additional_info = voice_entry.get('AdditionalInfo')
                v_ietf: str = v_culture.get('IetfLanguageTag')
                gend_code: int = int(voice_entry.get('Gender'))
                v_gender: Genders
                if gend_code == 1:
                    v_gender = Genders.MALE
                else:
                    v_gender = Genders.FEMALE
                v_lang: langcodes.Language = None
                try:
                    v_lang = langcodes.Language.get(v_ietf)
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'language: {v_lang.language} '
                                        f'display: '
                                        f'{v_lang.display_name(v_lang.language)} '
                                        f'territory: {v_lang.territory}')
                except LanguageTagError:
                    MY_LOGGER.exception('')

                LanguageInfo.add_language(engine_key=PowerShellTTS.service_key,
                                          language_id=v_lang.language,
                                          country_id=v_lang.territory,
                                          ietf=v_lang,
                                          region_id='',
                                          gender=v_gender,
                                          voice=v_name,
                                          engine_lang_id=v_lang.language,
                                          engine_voice_id=v_name,
                                          engine_name_msg_id=MessageId.ENGINE_POWERSHELL,
                                          engine_quality=2,
                                          voice_quality=-1)
        except Exception:
            MY_LOGGER.exception('')
        return

    @classmethod
    def get_one_core_json(cls) -> List[Dict[str, str | List[Dict[str, Any]]]] | None:
        env = os.environ.copy()
        win_path: WindowsPath
        win_path = WindowsPath(Constants.CONFIG_SCRIPTS_DIR_WINDOWS /
                               'one_core_voices.ps1')
        MY_LOGGER.debug(f'{win_path} exists: {win_path.exists()}')

        cmd_args: List[str] = ['powershell.exe', str(win_path)]
        MY_LOGGER.debug(f'Running command: Windows args: {cmd_args}')
        rc: int = -1
        json_str: str | None = None
        try:
            completed: subprocess.CompletedProcess
            completed = subprocess.run(cmd_args, stdin=None, capture_output=True,
                                       text=True, env=env, close_fds=True,
                                       encoding='utf-8', shell=False, check=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            rc = completed.returncode
            if rc != 0:
                MY_LOGGER.debug(f'config output: {completed.stdout}')
            else:
                json_str = completed.stdout
        except subprocess.CalledProcessError:
            MY_LOGGER.exception('')
        except OSError:
            MY_LOGGER.exception('')
        except Exception:
            MY_LOGGER.exception('')

        voice_data: List[Dict[str, str]] | None = None
        try:
            if json_str is None:
                MY_LOGGER.debug(f'No one_core voices returned')
                return None
            voice_data = json.loads(json_str)
        except Exception:
            MY_LOGGER.exception('')
        return voice_data

    @classmethod
    def init_one_core_voices(cls):
        try:
            voice_data: List[Dict[str, str]] | None
            voice_data = cls.get_one_core_json()
            if voice_data is None:
                return
            '''
            [
                {
                    "Description":  "Microsoft David - English (United States)",
                    "DisplayName":  "Microsoft David",
                    "Gender":  0,
                    "Id":  "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech_OneCore\\Voices\\Tokens\\MSTTS_V110_enUS_DavidM",
                    "Language":  "en-US"
                },
            ]
            '''
            for voice_entry in voice_data:
                voice_entry: Dict[str, str | Dict[str, str]]
                #  "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech_OneCore\\Voices\\Tokens\\MSTTS_V110_enUS_DavidM",
                _ = cls.get_cache_id(voice_entry.get('Id'))
                #  v_description: str = voice_entry.get('Description')
                v_name: str = voice_entry.get('DisplayName')
                v_ietf: str = voice_entry.get('Language')
                gend_code: int = int(voice_entry.get('Gender', 0))
                v_gender: Genders
                if gend_code == 0:
                    v_gender = Genders.MALE
                else:
                    v_gender = Genders.FEMALE
                lang: langcodes.Language = None
                try:
                    lang = langcodes.Language.get(v_ietf)
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'language: {lang.language} '
                                        f'display: '
                                        f'{lang.display_name(lang.language)} '
                                        f'territory: {lang.territory}')
                except LanguageTagError:
                    MY_LOGGER.exception('')

                LanguageInfo.add_language(engine_key=PowerShellTTS.service_key,
                                          language_id=lang.language,
                                          country_id=lang.territory,
                                          ietf=lang,
                                          region_id='',
                                          gender=v_gender,
                                          voice=v_name,
                                          engine_lang_id=v_ietf,
                                          engine_voice_id=v_name,  # Probably can use v_id
                                          engine_name_msg_id=MessageId.ENGINE_POWERSHELL,
                                          engine_quality=2,
                                          voice_quality=-1)
        except Exception:
            MY_LOGGER.exception('')
        return

    @classmethod
    def get_voice_dir(cls, voice_id: str) -> str:
        return cls._voice_dir_for_id.get(voice_id)

    def addCommonArgs(self, args, phrase: Phrase | None = None):
        clz = type(self)
        voice_id = Settings.get_voice(clz.service_key)
        if voice_id is None or voice_id in ('unknown', ''):
            voice_id = ''

        speed = self.get_speed()
        volume = self.getVolume()
        #  pitch = self.get_pitch()
        if phrase:
            args.append(phrase.get_text())
        if voice_id:
            args.extend(voice_id)
        # if speed:
        #     args.extend(('-s', str(speed)))
        # if pitch:
        #     args.extend(('-p', str(pitch)))

        # args.extend(('-a', str(volume)))

    def get_player_mode(self) -> PlayerMode:
        clz = type(self)
        player_mode: PlayerMode = Settings.get_player_mode(clz.service_key)
        return player_mode

    def get_cached_voice_file(self, phrase: Phrase,
                              generate_voice: bool = True) -> bool:
        """
        Return cached file if present. Optionally creates the cache file.

        Very similar to runCommand, except that the cached files are expected
        to be sent to a slave player, or some other player that can play a sound
        file.
        :param phrase: Contains the text to be voiced as wll as the path that it
                       is or will be located.
        :param generate_voice: If true, generate the speech file, as needed,
        :return: True if the voice file was handed to a player, otherwise False
        """
        clz = type(self)
        clz.update_voice_path(phrase)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'phrase: {phrase.get_text()} {phrase.get_debug_info()} '
                              f'cache_path: {phrase.get_cache_path()} use_cache: '
                              f'{Settings.is_use_cache()}')
        self.get_voice_cache().get_path_to_voice_file(phrase,
                                                      use_cache=Settings.is_use_cache(),
                                                      delete_tmp=False)
        # Wave files only added to cache when SFX is used.

        # This Only checks if a .wav file exists. That is good enough, the
        # player should check for existence of what it wants and to transcode
        # if needed.
        player_key: ServiceID = Settings.get_player()
        sfx_player: bool = player_key == Players.SFX
        if sfx_player and phrase.cache_file_state() == CacheFileState.OK:
            return True

        # If audio in cache is suitable for player, then we are done.

        player_voice_cache: VoiceCache = self.voice_cache
        player_result: CacheEntryInfo
        player_result = player_voice_cache.get_path_to_voice_file(phrase, use_cache=True)
        if player_result.audio_exists:
            return True

        success: bool = False
        wave_file: Path = self.runCommand(phrase)
        if wave_file is not None:
            result: CacheEntryInfo
            result = self.voice_cache.get_path_to_voice_file(phrase, use_cache=True)
            mp3_file = result.final_audio_path
            trans_id: str | None = Settings.get_transcoder(clz.service_key)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'service_id: {self.service_key} trans_id: {trans_id}')
            success = TransCode.transcode(trans_id=trans_id,
                                          input_path=wave_file,
                                          output_path=mp3_file,
                                          remove_input=True)
            if success:
                phrase.text_exists(check_expired=False, active_engine=self)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'success: {success} wave_file: {wave_file} mp3: '
                                f'{mp3_file}')
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
            PowerShell can:
            - Only output wave format
            - Can write to file, or pipe, or directly voice
            - Here we only care about writing to file.
            Destination:
            - to player
            - to cache, then player
            - to mp3 converter, to cache, then player
            Player prefers wave (since that is native to PowerShell), but can be 
            mp3
            Cache strongly prefers .mp3 (space), but can do wave (useful for
            fail-safe, when there is no mp3 player configured)).

        Assumptions:
            any cache has been checked to see if already voiced
        """
        clz.update_voice_path(phrase)
        sfx_player: bool = Settings.get_player().setting_id == Players.SFX
        use_cache: bool = Settings.is_use_cache() or sfx_player
        # Get path to audio-temp file, or cache location for audio
        cache_entry_info: CacheEntryInfo | None = None
        cache_entry_info = self.get_voice_cache().get_path_to_voice_file(phrase,
                                                                         use_cache=use_cache,
                                                                         delete_tmp=False)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'phrase: {phrase.get_text()} {phrase.get_debug_info()} '
                              f'cache_path: {phrase.get_cache_path()} ')
        audio_exists: bool = cache_entry_info.audio_exists  # True ONLY if using cache
        if audio_exists:
            return cache_entry_info.final_audio_path

        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'PowerShell.runCommand cache: {use_cache} '
                              f'PowerShell_out_file: {cache_entry_info.temp_voice_path.name}\n'
                              f'text: {phrase.text}')
        env = os.environ.copy()
        args: List[str] = self.get_args(cache_entry_info.temp_voice_path)
        text: str = phrase.text
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'temp_voice_path type: {type(cache_entry_info.temp_voice_path)}')
        try:
            completed: subprocess.CompletedProcess | None = None
            if Constants.PLATFORM_WINDOWS:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Phrase: {phrase.text}')
                    MY_LOGGER.debug(f'Running command: Windows: {args}')

                completed = subprocess.run(args, input=text,
                                           capture_output=True,
                                           timeout=10.0,  # 10 seconds is a lot of time
                                           shell=False,
                                           text=True,
                                           encoding='utf-8',
                                           env=env,
                                           close_fds=True,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                # DO NOT USE subprocess.DETACHED_PROCESS. It won't create voice files
                try:
                    if completed is None:
                        MY_LOGGER.DEBUG(f'command failed, completed is None')
                        return None
                    completed.check_returncode()
                except subprocess.TimeoutExpired:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.info(f'Command could not complete in 10'
                                       f' seconds')
                    return None
                if completed is not None:
                    rc: int = completed.returncode
                    if rc != 0:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Failed RC: {rc}')
        except (OSError, ValueError, subprocess.CalledProcessError) as e:
            MY_LOGGER.exception('')
            return None
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'COMMAND FINISHED phrase: {phrase.text}')
        if not cache_entry_info.temp_voice_path.exists():
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'voice file not created: {cache_entry_info.temp_voice_path}')
            return None
        if cache_entry_info.temp_voice_path.stat().st_size <= 1000:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debig(f'voice file too small. Deleting: '
                                f'{cache_entry_info.temp_voice_path}')
            try:
                cache_entry_info.temp_voice_path.unlink(missing_ok=True)
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'unlink {cache_entry_info.temp_voice_path}')
            except:
                MY_LOGGER.exception('')
            return None
        try:
            cache_entry_info.temp_voice_path.rename(cache_entry_info.final_audio_path)
            phrase.set_cache_path(cache_path=cache_entry_info.final_audio_path,
                                  text_exists=phrase.text_exists(active_engine=self,
                                                                 check_expired=False),
                                  temp=not cache_entry_info.use_cache)
        except ExpiredException:
            try:
                cache_entry_info.temp_voice_path.unlink(missing_ok=True)
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'EXPIRED: unlink {cache_entry_info.temp_voice_path}')
            except:
                MY_LOGGER.exception(f'Can not delete {cache_entry_info.temp_voice_path}')
            return None
        except Exception:
            MY_LOGGER.exception(f'Could not rename {cache_entry_info.temp_voice_path} '
                                f'to {cache_entry_info.final_audio_path}')
            try:
                cache_entry_info.temp_voice_path.unlink(missing_ok=True)
            except:
                MY_LOGGER.exception(f'Can not delete {cache_entry_info.temp_voice_path}')
            return None
        return cache_entry_info.final_audio_path  # Wave file

    def runCommandAndSpeak(self, phrase: Phrase) -> None:
        clz = type(self)
        clz.update_voice_path(phrase)
        env = os.environ.copy()
        args: List[str] = self.get_args()
        text: str = phrase.text
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'args: {args}')

        try:
            completed: subprocess.CompletedProcess | None = None
            if Constants.PLATFORM_WINDOWS:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Phrase: {phrase.text}')
                    MY_LOGGER.debug(f'Running command: Windows: {args}')

                completed = subprocess.run(args, input=text,
                                           capture_output=True,
                                           timeout=10.0,  # 10 seconds is a lot of time
                                           shell=False,
                                           text=True,
                                           encoding='utf-8',
                                           env=env,
                                           close_fds=True,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                # DO NOT USE subprocess.DETACHED_PROCESS. It won't create voice files
                try:
                    if completed is None:
                        MY_LOGGER.DEBUG(f'command failed, completed is None')
                        return None
                    completed.check_returncode()
                except subprocess.TimeoutExpired:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.info(f'Command could not complete in 10'
                                       f' seconds')
                    return None
                if completed is not None:
                    rc: int = completed.returncode
                    if rc != 0:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Failed RC: {rc}')
        except (OSError, ValueError, subprocess.CalledProcessError) as e:
            MY_LOGGER.exception('')
            return None
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'COMMAND FINISHED phrase: {phrase.text}')

    def seed_text_cache(self, phrases: PhraseList) -> None:
        """
        Provides means to generate voice files before actually needed. Currently
        called by worker_thread to get a bit of a head-start on the normal path.

        :param phrases:
        :return:
        """

        clz = type(self)
        self.get_voice_cache().seed_text_cache(phrases)

    '''
    @classmethod
    def get_speech_generator(cls) -> SpeechGenerator:
        return SpeechGenerator(None, engine=)
    '''

    @classmethod
    def has_speech_generator(cls) -> bool:
        """
        TODO: This is needed, but also a lie. SpeechGenerator exists, but is not
            used. Instead get_cached_voice_file is doing the work.
        """
        return True

    def stop_player(self, purge: bool = True,
                    keep_silent: bool = False,
                    kill: bool = False):
        """
        Stop player_key (most likely because current text is expired)
        Players may wish to override this method, particularly when
        the player_key is built-in.

        :param purge: if True, then purge any queued vocings
                      if False, then only stop playing current phrase
        :param keep_silent: if True, ignore any new phrases until restarted
                            by resume_player.
                            If False, then play any new content
        :param kill: If True, kill any player_key processes. Implies purge and
                     keep_silent.
                     If False, then the player_key will remain ready to play new
                     content, depending upon keep_silent
        :return:
        """
        self.stop()

    def stop(self):
        clz = type(self)
        self.init_process()

    @classmethod
    def load_languages(cls):
        """
        Discover PowerShell's supported languages and report results to
        LanguageInfo.
        :return:
        """
        cls.init_voices()

    @classmethod
    def settingList(cls, setting, *args) -> Tuple[List[Choice], str]:
        choices: List[Choice] = []
        if setting == SettingProp.LANGUAGE:
            # Returns list of languages and index to the closest match to current
            # locale
            if MY_LOGGER.isEnabledFor(DEBUG):
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
            for voice_name, voice_id, gender_id in voice_list:
                # TODO: verify
                # Voice_name is from command and not translatable?

                # Unlike voices and languages, we just return gender ids
                # translation is handled by SettingsDialog

                genders.append(Choice(value=gender_id))
            return genders, ''
        elif setting == SettingProp.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml
            supported_players: List[AllowedValue]
            supported_players = SettingsMap.get_allowed_values(ServiceKey.PLAYER_KEY)
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

            t_key: ServiceID
            t_key = cls.service_key.with_prop(SettingProp.PLAYER)
            default_player: str
            default_player = SettingsMap.get_default_value(t_key)
            return choices, default_player
        return choices, ''

    def get_args(self, wave_output: Path | None = None) -> List[str]:
        clz = type(self)

        voice_id = Settings.get_voice(clz.service_key)
        if voice_id is None or voice_id in ('unknown', ''):
            voice_id = ''
        else:
            voice_id = f'-Voice "{voice_id}"'

        clz.suffix += 1
        t_file: str = f'temp_{clz.suffix}'
        windows_path: str = ''
        if wave_output is not None:
            windows_path = f'-AudioPath \'{str(wave_output)}\''

        # speed = self.get_speed()
        # volume = self.getVolume()
        args = [clz.POWERSHELL_PATH,
                f'& {{. \'{clz.script_path}\';  Voice-Sapi '
                f'{voice_id} '
                f'{windows_path}'
                f'}}']
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'args: {args}')
        return args

    @classmethod
    def get_default_language(cls) -> str:
        languages: List[str]
        default_lang: str
        languages, default_lang = cls.settingList(SettingProp.LANGUAGE)
        return default_lang

    @classmethod
    def get_voice_id_for_name(cls, name):
        if len(cls.voice_map) == 0:
            cls.settingList(SettingProp.VOICE)
        return cls.voice_map[name]

    def getVolume(self) -> int:
        # All volumes in settings use a common TTS db scale.
        # Conversions to/from the engine's or player's scale are done using
        # Constraints
        clz = type(self)
        t_service_id: ServiceID
        t_service_id = clz.service_key.with_prop(SettingProp.VOLUME)
        if self.get_player_mode() != PlayerMode.ENGINE_SPEAK:
            volume_val: INumericValidator = SettingsMap.get_validator(t_service_id)
            volume_val: NumericValidator
            volume: int = volume_val.get_value()
            return volume
        else:
            volume_val: INumericValidator = SettingsMap.get_validator(t_service_id)
            volume_val: NumericValidator
            # volume: int = volume_val.get_tts_value()
            volume: int = volume_val.get_value()

        return volume

    def get_pitch(self) -> int:
        # All pitches in settings use a common TTS scale.
        # Conversions to/from the engine's or player's scale are done using
        # Constraints
        clz = type(self)
        pitch_key: ServiceID = clz.service_key.with_prop(SettingProp.PITCH)
        if self.get_player_mode != PlayerMode.ENGINE_SPEAK:
            pitch_val: INumericValidator = SettingsMap.get_validator(pitch_key)
            pitch_val: NumericValidator
            pitch: int = pitch_val.get_value()
            return pitch
        else:
            # volume = Settings.get_volume(clz.setting_id)
            pitch_val: INumericValidator = SettingsMap.get_validator(pitch_key)
            pitch_val: NumericValidator
            # volume: int = volume_val.get_tts_value()
            pitch: int = pitch_val.get_value()

        return pitch

    def get_speed(self) -> int:
        """
            PowerShell's speed is measured in 'words/minute' with a default
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
        speed_key: ServiceID = clz.service_key.with_prop(SettingProp.SPEED)
        if self.get_player_mode != PlayerMode.ENGINE_SPEAK:
            # Let player decide speed
            speed = 176  # Default PowerShell speed of 176 words per minute.
            return speed
        else:
            speed_val: INumericValidator = SettingsMap.get_validator(speed_key)
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
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'lang: {phrase.language} \n'
                                  f'voice: {phrase.voice}\n'
                                  f'lang_dir: {phrase.lang_dir}')
            locale: str = phrase.language  # IETF format
            voice_id: str = Settings.get_voice(cls.service_key)
            kodi_lang, kodi_locale, _, ietf_lang = LanguageInfo.get_kodi_locale_info()
            if voice_id is None or voice_id == '':
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug('Fix Settings.get_voice to use kodi_locale by '
                                    'default')
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'locale: {locale} kodi_lang: {kodi_lang} '
                                  f'kodi_locale: {kodi_locale} '
                                  f'ietf_lang: {ietf_lang}')
            # MY_LOGGER.debug(f'orig Phrase locale: {locale}')
            if locale is None:
                locale = kodi_locale
            ietf_lang: langcodes.Language = langcodes.get(locale)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'locale: {locale} ietf_lang: {ietf_lang.language} '
                                  f'{ietf_lang.territory}')
            phrase.set_lang_dir(ietf_lang.language)
            phrase.set_voice(voice_id)
            phrase.set_voice_dir(cls._voice_dir_for_id.get(voice_id))
            # Horrible, crude, hack due to kodi xbmc.getLanguage bug
            if ietf_lang.territory is not None:
                phrase.set_territory_dir(ietf_lang.territory.lower())
            else:
                phrase.set_territory_dir('us')
        return
