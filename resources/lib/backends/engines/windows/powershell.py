# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import ctypes.util
import os
import subprocess
import sys
import tempfile

import xbmc

import langcodes

from pathlib import Path

from backends.engines.windows.powershell_settings import PowerShellTTSSettings
from backends.players.iplayer import IPlayer
from backends.settings.language_info import LanguageInfo
from backends.settings.settings_helper import SettingsHelper
from backends.settings.validators import NumericValidator
from backends.transcoders.trans import TransCode
from cache.voicecache import VoiceCache
from cache.cache_file_state import CacheFileState
from cache.common_types import CacheEntryInfo
from common import *

from backends.audio.builtin_player import BuiltInPlayer
# from backends.audio.player_handler import BasePlayerHandler, WavAudioPlayerHandler
from backends.audio.sound_capabilities import ServiceType
from backends.base import BaseEngineService, SimpleTTSBackend
from backends.settings.i_validators import AllowedValue, INumericValidator, IValidator
from backends.settings.service_types import ServiceID, ServiceKey, Services
from backends.settings.settings_map import Reason, SettingsMap
from common import utils
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import *
from common.message_ids import MessageId
from common.messages import Messages
from common.monitor import Monitor
from common.phrases import Phrase
from common.setting_constants import (AudioType, Backends, Genders, Mode, PlayerMode,
                                      Players)
from common.settings import Settings
from common.settings_low_level import SettingProp
from langcodes import LanguageTagError
from windowNavigation.choice import Choice

MY_LOGGER = BasicLogger.get_logger(__name__)


class PowerShellTTS(SimpleTTSBackend):
    """
        Use Windows built-in TTS via powershell script
    """
    ID = Backends.POWERSHELL_ID
    service_id: str = Services.POWERSHELL_ID
    service_key: ServiceID
    service_type: ServiceType = ServiceType.ENGINE
    engine_id: str = Backends.POWERSHELL_ID
    service_key = ServiceID(service_type, service_id)
    OUTPUT_FILE_TYPE: str = '.wav'
    displayName: str = MessageId.ENGINE_POWERSHELL.get_msg()
    UTF_8: Final[str] = '1'

    POWERSHELL_PATH = "powershell.exe"  # POWERSHELL EXE PATH
    #  ps_script_path = "C:\\PowershellScripts\\FTP_UPLOAD.PS1"
    script_dir: Path = Constants.PYTHON_ROOT_PATH / 'backends/engines/windows'
    ps_script = 'voice.ps1'
    script_path: Path = script_dir / ps_script
    voice_args = [POWERSHELL_PATH, '-ExecutionPolicy', 'Unrestricted',
                  script_path]
    voice_map: Dict[str, List[Tuple[str, str, Genders]]] = None
    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        self.process: subprocess.Popen | None = None
        self.voice_cache: VoiceCache = VoiceCache(clz.service_key)

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

    @classmethod
    def get_backend_id(cls) -> str:
        return cls.service_id

    @classmethod
    def init_voices(cls):
        if cls.voice_map is not None:
            return

        david: Tuple[str, str, Genders] = ('David', 'en', Genders.MALE)
        zira: Tuple[str, str, Genders] = ('Zira', 'en', Genders.FEMALE)
        voices: List[Tuple[str, str, Genders]] = [david, zira]
        for voice in voices:
            v_name: str = voice[0]
            v_lang: str = voice[1]
            v_gender: Genders = voice[2]
            lang: langcodes.Language | None = None
            try:
                lang = langcodes.Language.get(v_lang)
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'language: {lang.language} '
                                       f'display: '
                                       f'{lang.display_name(lang.language)}')
            except LanguageTagError:
                MY_LOGGER.exception('')

            LanguageInfo.add_language(engine_id=PowerShellTTS.engine_id,
                                      language_id=lang.language,
                                      country_id=lang.territory,
                                      ietf=lang,
                                      region_id='',
                                      gender=v_gender,
                                      voice=v_name,
                                      engine_lang_id=v_lang,
                                      engine_voice_id=v_name,
                                      engine_name_msg_id=MessageId.ENGINE_POWERSHELL,
                                      engine_quality=3,
                                      voice_quality=-1)
        cls.initialized_static = True

    def addCommonArgs(self, args, phrase: Phrase | None = None):
        clz = type(self)
        voice_id = Settings.get_voice(clz.service_key)
        if voice_id is None or voice_id in ('unknown', ''):
            voice_id = ''

        speed = self.get_speed()
        volume = self.getVolume()
        pitch = self.get_pitch()
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
        Return cached file if present, otherwise, generate speech, place in cache
        and return cached speech.

        Very similar to runCommand, except that the cached files are expected
        to be sent to a slave player_key, or some other player_key that can play a sound
        file.
        :param phrase: Contains the text to be voiced as wll as the path that it
                       is or will be located.
        :param generate_voice: If true, then wait a bit to generate the speech
                               file.
        :return: True if the voice file was handed to a player_key, otherwise False
        """
        clz = type(self)
        MY_LOGGER.debug(f'phrase: {phrase.get_text()} {phrase.get_debug_info()} '
                        f'cache_path: {phrase.get_cache_path()} use_cache: '
                        f'{Settings.is_use_cache()}')
        self.get_voice_cache().get_path_to_voice_file(phrase,
                                                      use_cache=Settings.is_use_cache())
        MY_LOGGER.debug(f'cache_exists: {phrase.cache_file_state()} '
                        f'cache_path: {phrase.get_cache_path()}')
        # Wave files only added to cache when SFX is used.

        # This Only checks if a .wav file exists. That is good enough, the
        # player_key should check for existence of what it wants and to transcode
        # if needed.
        player_key: ServiceID = Settings.get_player_key()
        sfx_player: bool = player_key == Players.SFX
        if sfx_player and phrase.cache_file_state() == CacheFileState.OK:
            return True

        # If audio in cache is suitable for player_key, then we are done.

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
            mp3_file = result.current_audio_path
            trans_id: str | None = Settings.get_converter(clz.service_key)
            MY_LOGGER.debug(f'service_id: {self.engine_id} trans_id: {trans_id}')
            success = TransCode.transcode(trans_id=trans_id,
                                          input_path=wave_file,
                                          output_path=mp3_file,
                                          remove_input=True)
            if success:
                phrase.text_exists(check_expired=False)
            MY_LOGGER.debug(f'success: {success} wave_file: {wave_file} mp3: {mp3_file}')
        return success

    def runCommand(self, phrase: Phrase) -> Path | None:
        """
        Run command to generate speech and save voice to a file (mp3 or wave).
        A player_key will then be scheduled to play the file. Note that there is
        delay in starting speech generator, speech generation, starting player_key
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
            - to player_key
            - to cache, then player_key
            - to mp3 converter, to cache, then player_key
            Player prefers wave (since that is native to eSpeak), but can be 
            mp3
            Cache strongly prefers .mp3 (space), but can do wave (useful for
            fail-safe, when there is no mp3 player_key configured)).

        Assumptions:
            any cache has been checked to see if already voiced
        """
        use_cache: bool = Settings.is_use_cache()
        # The SFX player_key is used when NO player_key is available. SFX is Kodi's
        # internal player_key with limited functionality. Requires Wave.
        sfx_player: bool = Settings.get_player_key() == Players.SFX
        espeak_out_file: Path | None = None
        exists: bool = False
        if not sfx_player:
            tmp = tempfile.NamedTemporaryFile()
            espeak_out_file = Path(tmp.name)
            #  espeak_out_file = clz.tmp_file(clz.OUTPUT_FILE_TYPE)
        else:
            result: CacheEntryInfo
            result = self.voice_cache.get_path_to_voice_file(phrase, use_cache=True)
            exists = result.audio_exists
            espeak_out_file = result.current_audio_path
        if exists:
            return espeak_out_file

        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'espeak.runCommand cache: {use_cache} '
                              f'espeak_out_file: {espeak_out_file.name}\n'
                              f'text: {phrase.text}')
        # if out_file.stem == '.mp3':
        #     self.runCommandAndPipe(phrase)
        #     return

        env = os.environ.copy()
        args = clz.voice_args.copy()
        self.addCommonArgs(args)
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
                               creationflags=subprocess.DETACHED_PROCESS)
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

            MY_LOGGER.debug(f'args: {args}')
        except subprocess.CalledProcessError as e:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.exception('')
                return None
        return espeak_out_file  # Wave file

    def runCommandAndSpeak(self, phrase: Phrase):
        clz = type(self)
        env = os.environ.copy()
        args: List[str] = clz.voice_args.copy()
        self.addCommonArgs(args, phrase)
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
                MY_LOGGER.exception('')

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
        cls.init_voices()

    @classmethod
    def settingList(cls, setting, *args) -> Tuple[List[Choice], str]:
        choices: List[Choice] = []
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
            for voice_name, voice_id, gender_id in voice_list:
                # TODO: verify
                # Voice_name is from command and not translatable?

                # Unlike voices and languages, we just return gender ids
                # translation is handled by SettingsDialog

                genders.append(Choice(value=gender_id))
            return genders, ''
        elif setting == SettingProp.PLAYER:
            # Get list of player_key ids. Id is same as is stored in settings.xml
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
        # Conversions to/from the engine's or player_key's scale are done using
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
        # Conversions to/from the engine's or player_key's scale are done using
        # Constraints
        clz = type(self)
        if self.get_player_mode != PlayerMode.ENGINE_SPEAK:
            pitch_val: INumericValidator = SettingsMap.get_validator(
                    clz.service_id, SettingProp.PITCH)
            pitch_val: NumericValidator
            pitch: int = pitch_val.get_value()
            return pitch
        else:
            # volume = Settings.get_volume(clz.setting_id)
            pitch_val: INumericValidator = SettingsMap.get_validator(
                    clz.service_id, SettingProp.PITCH)
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
        # Conversions to/from the engine's or player_key's scale are done using
        # Constraints
        clz = type(self)
        if self.get_player_mode != PlayerMode.ENGINE_SPEAK:
            # Let player_key decide speed
            speed = 176  # Default espeak speed of 176 words per minute.
            return speed
        else:
            speed_val: INumericValidator = SettingsMap.get_validator(
                    clz.service_id, SettingProp.SPEED)
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
            phrase.set_territory_dir(ietf_lang.territory.lower())
        return

    @classmethod
    def check_availability(cls) -> Reason:
        return PowerShellTTSSettings.check_availability()
