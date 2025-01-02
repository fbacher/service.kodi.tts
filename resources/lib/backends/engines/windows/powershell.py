# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import ctypes.util
import os
import subprocess
import sys
import tempfile

import langcodes

from pathlib import Path

from backends.players.iplayer import IPlayer
from backends.settings.language_info import LanguageInfo
from backends.settings.settings_helper import SettingsHelper
from backends.settings.validators import NumericValidator
from backends.transcoders.trans import TransCode
from cache.voicecache import VoiceCache
from cache.common_types import CacheEntryInfo
from common import *

from backends.audio.builtin_audio_player import BuiltInPlayer
# from backends.audio.player_handler import BasePlayerHandler, WavAudioPlayerHandler
from backends.audio.sound_capabilities import ServiceType
from backends.base import BaseEngineService, SimpleTTSBackend
from backends.settings.i_validators import AllowedValue, INumericValidator, IValidator
from backends.settings.service_types import Services
from backends.settings.settings_map import SettingsMap
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
from common.settings_low_level import SettingsProperties
from langcodes import LanguageTagError
from windowNavigation.choice import Choice

MY_LOGGER = BasicLogger.get_logger(__name__)


class PowerShellTTS(SimpleTTSBackend):
    """

    """
    ID = Backends.POWERSHELL_ID
    service_ID: str = Services.POWERSHELL_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    engine_id: str = Backends.POWERSHELL_ID
    engine_id: str = Backends.POWERSHELL_ID
    OUTPUT_FILE_TYPE: str = '.mp3'
    displayName: str = MessageId.ENGINE_POWERSHELL.get_msg()
    UTF_8: Final[str] = '1'

    voice_map: Dict[str, List[Tuple[str, str, Genders]]] = None
    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        self.process: subprocess.Popen | None = None
        self.voice_cache: VoiceCache = VoiceCache(clz.service_ID)

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
        return cls.service_ID

    @classmethod
    def init_voices(cls):
        if cls.voice_map is not None:
            return
        return
    '''
        cls._voice_map = {}
        for voice in voices:
            
            lang: langcodes.Language = None
            try:
                lang = langcodes.Language.get(lang_str)
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'orig: {lang_str} '
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
            entries: List[Tuple[str, str, Genders]] | None
            entries = cls.voice_map.get(lang.language, None)
            if entries is None:
                entries = []
                cls.voice_map[lang.language] = entries
            entries.append((voice_name, voice_id, gender))
            LanguageInfo.add_language(engine_id=PowerShellTTS.engine_id,
                                      language_id=lang.language,
                                      country_id=lang.territory,
                                      ietf=lang,
                                      region_id='',
                                      gender=Genders.UNKNOWN,
                                      voice=voice_name,
                                      engine_lang_id=lang_str,
                                      engine_voice_id=voice_id,
                                      engine_name_msg_id=MessageId.ENGINE_POWERSHELL,
                                      engine_quality=3,
                                      voice_quality=-1)
        cls.initialized_static = True
    '''
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
        MY_LOGGER.debug(f'phrase: {phrase.get_text()} {phrase.get_debug_info()} '
                        f'cache_path: {phrase.get_cache_path()} use_cache: '
                        f'{Settings.is_use_cache()}')
        self.get_voice_cache().get_path_to_voice_file(phrase,
                                                      use_cache=Settings.is_use_cache())
        MY_LOGGER.debug(f'cache_exists: {phrase.cache_path_exists()} '
                        f'cache_path: {phrase.get_cache_path()}')
        # Wave files only added to cache when SFX is used.

        # This Only checks if a .wav file exists. That is good enough, the
        # player should check for existence of what it wants and to transcode
        # if needed.
        player_id: str = Settings.get_player_id()
        sfx_player: bool = player_id == Players.SFX
        if sfx_player and phrase.cache_path_exists():
            return True

        # If audio in cache is suitable for player, then we are done.
        player_voice_cache: VoiceCache = self.get_player_voice_cache(self.player_id)
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
            trans_id: str | None = Settings.get_converter(self.engine_id)
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
        use_cache: bool = Settings.is_use_cache()
        # The SFX player is used when NO player is available. SFX is Kodi's
        # internal player with limited functionality. Requires Wave.
        sfx_player: bool = Settings.get_player_id() == Players.SFX
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
        args = ['espeak-ng', '-b', clz.UTF_8, '-w', str(espeak_out_file), '--stdin']
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

            MY_LOGGER.debug(f'args: {args}')
        except subprocess.CalledProcessError as e:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.exception('')
                return None
        return espeak_out_file  # Wave file

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
            MY_LOGGER.debug(f'args: {args}')
        except subprocess.SubprocessError as e:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('espeak.runCommandAndSpeak Exception: ' + str(e))

    '''
    def runCommandAndPipe(self, phrase: Phrase):
        clz = type(self)
        args = ['espeak-ng', '-b', clz.UTF_8, '--stdin', '--stdout']

        self.addCommonArgs(args, phrase)
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
        self.process = subprocess.Popen(args, stdout=subprocess.PIPE)
        return self.process.stdout
    '''

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
        if setting == SettingsProperties.LANGUAGE:
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
                player_label = Players.get_msg(player.value)
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

    @staticmethod
    def available() -> bool:
        available: bool = True
        try:
            cmd_path = 'espeak-ng'
            args = [cmd_path, '--version']
            try:
                completed: subprocess.CompletedProcess
                completed = subprocess.run(args, stdin=None, capture_output=True,
                                           text=True, encoding='utf-8',
                                           shell=False, check=True)

                found: bool = False
                for line in completed.stdout.split('\n'):
                    if len(line) > 0:
                        if line.find('eSpeak NG text_to_speech'):
                            found = True
                            break
                if not found:
                    available = False
            except ProcessLookupError:
                MY_LOGGER.exception('')
                available = False
        except Exception:
            MY_LOGGER.exception('')
            available = False

        # eSpeak has built-in player
        return available