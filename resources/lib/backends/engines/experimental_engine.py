# -*- coding: utf-8 -*-
import io
import os
import re
import sys
from datetime import timedelta
from enum import Enum
from time import time
import pathlib
import subprocess

from typing.io import IO

from backends.audio.sound_capabilties import ServiceType, SoundCapabilities
from backends.base import SimpleTTSBackend
from backends.engines.experimental_engine_settings import ExperimentalSettings
from backends.players.iplayer import IPlayer
from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator
from cache.voicecache import VoiceCache
from common.base_services import BaseServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.logger import *
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from common.setting_constants import Backends, Genders, Languages, Mode
from common.settings import Settings
from common.simple_run_command import SimpleRunCommand
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)
PUNCTUATION_PATTERN = re.compile(r'([.,:])', re.DOTALL)


class WaveToMpg3Encoder(Enum):
    FFMPEG = 0
    MPLAYER = 1
    LAME = 2


class ExperimentalTTSBackend(SimpleTTSBackend):

    ID: str = Backends.EXPERIMENTAL_ENGINE_ID
    backend_id = Backends.EXPERIMENTAL_ENGINE_ID
    engine_id = Backends.EXPERIMENTAL_ENGINE_ID
    service_ID: str = Services.EXPERIMENTAL_ENGINE_ID
    service_TYPE: str = ServiceType.ENGINE

    MAXIMUM_PHRASE_LENGTH: Final[int] = 200
    _logger: BasicLogger = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)

        self.process = None
        self.stop_processing = False
        self.simple_cmd: SimpleRunCommand = None
        self.stop_urgent: bool = False
        BaseServices().register(self)

    def init(self) -> None:
        clz = type(self)
        if self.initialized:
            return
        super().init()
        self.update()

    def getMode(self) -> Mode:
        clz = type(self)
        player: IPlayer = self.get_player()
        if clz.getSetting(SettingsProperties.PIPE):
            return Mode.PIPE
        else:
            return Mode.FILEOUT

    def runCommand(self, phrase: Phrase) -> bool:
        clz = type(self)
        # If caching disabled, then exists is always false. file_path
        # always contains path to cached file, or path where to download to
        if self.stop_processing:
            if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                clz._logger.debug_extra_verbose('stop_processing')
            return False

        exists: bool
        voiced_text: bytes
        try:
            if phrase.get_cache_path() is None:
                VoiceCache.get_path_to_voice_file(phrase,
                                                  use_cache=Settings.is_use_cache())
            voice_file: pathlib.Path = phrase.get_cache_path()
            exists: bool = phrase.is_exists()
            self._logger.debug(f'PHRASE: {phrase.get_text()} file_path: {voice_file}'
                               f' exists: {exists}')

            if self.stop_processing:
                if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    clz._logger.debug_extra_verbose('stop_processing')
                return False

            if not exists:
                self.generate_speech(phrase)
        except ExpiredException:
            clz._logger.debug(f'EXPIRED at engine')
            return False
        return exists

    def runCommandAndPipe(self, phrase: Phrase):
        clz = type(self)

        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        if self.stop_processing:
            if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                clz._logger.debug_extra_verbose('stop_processing')
            return False

        audio_pipe = None
        voice_file: str | None
        exists: bool
        byte_stream: io.BinaryIO = None
        rc: int = -2
        try:
            if not phrase.is_exists():
                rc = self.generate_speech(phrase)

            if self.stop_processing:
                if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    clz._logger.debug_extra_verbose('stop_processing')
                return False

            try:
                byte_stream = io.open(phrase.get_cache_path(), 'rb')
            except Exception:
                rc = 1
                clz._logger.exception('')
                byte_stream = None
        except ExpiredException:
            clz._logger.debug('EXPIRED in engine')

        return byte_stream

    def seed_text_cache(self, phrases: PhraseList) -> None:
        # If voice_file_path is None, then don't save voiced text to it,
        # just return the voiced text as bytes
        clz = type(self)
        try:
            # We don't care whether it is too late to say this text.

            phrases = phrases.clone(check_expired=False)
            for phrase in phrases:
                if Settings.is_use_cache():
                    VoiceCache.get_path_to_voice_file(phrase, use_cache=True)
                    if not phrase.is_exists():
                        text_to_voice: str = phrase.get_text()
                        voice_file_path: pathlib.Path = phrase.get_cache_path()
                        clz._logger.debug_extra_verbose(f'PHRASE Text {text_to_voice}')
                        rc: int = 0
                        # This engine only writes to file it creates
                        # rc, _ = VoiceCache.create_sound_file(voice_file_path,
                        #                                     create_dir_only=True)
                        # if rc != 0:
                        #     if clz._logger.isEnabledFor(ERROR):
                        #         clz._logger.error(f'Failed to create cache file {voice_file_path}')
                        #     return rc
                        try:
                            # Should only get here if voiced file (.wav, .mp3, etc.) was NOT
                            # found. We might see a pre-existing .txt file which means that
                            # the download failed. To prevent multiple downloads, wait a day
                            # before retrying the download.

                            voice_text_file: pathlib.Path | None = None  # None when save_to_file False
                            voice_text_file = voice_file_path.with_suffix('.txt')

                            try:
                                if os.path.isfile(voice_text_file):
                                    os.unlink(voice_text_file)

                                with open(voice_text_file, 'wt') as f:
                                    f.write(text_to_voice)
                            except Exception as e:
                                if clz._logger.isEnabledFor(ERROR):
                                    clz._logger.error(
                                            f'Failed to save voiced text file: '
                                            f'{voice_text_file} Exception: {str(e)}')
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                        'Failed to download voice: {}'.format(str(e)))
        except Exception as e:
            clz._logger.exception('')

    def generate_speech(self, phrase: Phrase) -> int:
        # If voice_file_path is None, then don't save voiced text to it,
        # just return the voiced text as bytes

        clz = type(self)
        # if len(text_to_voice) > 250:
        #    clz._logger.error('Text longer than 250. len:', len(text_to_voice),
        #                             text_to_voice)
        #    return None, None
        voice_file_path: pathlib.Path = None
        try:
            text_to_voice: str = phrase.get_text()
            voice_file_path = phrase.get_cache_path()
            clz._logger.debug_extra_verbose(f'PHRASE Text {text_to_voice}')
        except ExpiredException:
            return 10

        failed: bool = False
        save_copy_of_text: bool = True
        save_to_file: bool = voice_file_path is not None
        '''
        key:str  = clz.getAPIKey()
        lang: str = clz.getLanguage()
        gender: str = clz.getGender()
        pitch: str = clz.getPitch_str()    # hard coded. Let player decide
        speed: str = clz.getApiSpeed()     # Also hard coded value for 1x speed
        volume: str = clz.getEngineVolume_str()
        service: str = clz.getVoice()
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(
                    f'text: {text_to_voice} lang: {lang} gender: {gender} pitch {pitch} '
                    f'speed: {speed} volume: {volume} service: {service}')
        api_volume: str = volume  # volume
        api_speed = speed
        api_pitch: str = pitch
        params: Dict[str, str] = {
            "key": key,
            # "t": text_to_voice,
            "tl": lang,
            "pitch": api_pitch,
            "rate": api_speed,
            "vol": api_volume,
            "sv": service,
            "vn": '',
            "gender": gender
        }
        '''
        rc: int = 0
        voiced_buffer: IO[io.BufferedWriter] = None
        if save_to_file:
            # This engine only writes to file it creates
            rc, _ = VoiceCache.create_sound_file(voice_file_path,
                                                 create_dir_only=True)
            if rc != 0:
                if clz._logger.isEnabledFor(ERROR):
                    clz._logger.error(f'Failed to create cache file {voice_file_path}')
                return rc

        aggregate_voiced_bytes: bytes = b''
        if not self.stop_processing:
            try:
                # Should only get here if voiced file (.wav, .mp3, etc.) was NOT
                # found. We might see a pre-existing .txt file which means that
                # the download failed. To prevent multiple downloads, wait a day
                # before retrying the download.

                failing_voice_text_file: pathlib.Path | None = None  # None when save_to_file False
                if save_to_file:
                    failing_voice_text_file = voice_file_path / '.txt'
                    if os.path.isfile(failing_voice_text_file):
                        expiration_time: float = time() - timedelta(hours=24).total_seconds()
                        if (os.stat(failing_voice_text_file).st_mtime <
                                expiration_time):
                            clz._logger.debug(f'os.remove(voice_file_path)')
                        else:
                            clz._logger.debug_extra_verbose(
                                    'Previous attempt to get speech failed. Skipping.')
                            rc = 2
                            return rc

                    if save_copy_of_text:
                        path: str
                        file_type: str
                        copy_text_file_path, file_type = os.path.splitext(voice_file_path)
                        copy_text_file_path = f'{copy_text_file_path}.txt'
                        try:
                            if os.path.isfile(copy_text_file_path):
                                os.unlink(copy_text_file_path)

                            with open(copy_text_file_path, 'wt') as f:
                                f.write(text_to_voice)
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                        f'Failed to save voiced text file: '
                                        f'{copy_text_file_path} Exception: {str(e)}')
                if Settings.get_setting_bool(SettingsProperties.DELAY_VOICING,
                                             clz.service_ID, ignore_cache=False,
                                             default=True):
                    clz._logger.debug(f'Generation of voice files disabled by settings')
                    rc = 3
                    return rc
                text_file: str
                output_dir: pathlib.Path
                output: pathlib.Path
                rc: int = 0
                reason: str = ''
                model = 'tts_models/en/ljspeech/tacotron2-DDC_ph'
                vocoder = 'vocoder_models/en/ljspeech/univnet'
                try:
                    self.simple_cmd = SimpleRunCommand(['tts', '--text', f'{text_to_voice}',
                                                   '--model_name', model,
                                                   '--vocoder_name', vocoder,
                                                   '--out_path', '/tmp/tst.wav'])
                    if self.stop_processing:
                        rc = 5
                        return rc
                    self.simple_cmd.run_cmd()
                    self.simple_cmd = None
                    phrase.set_exists(True)
                except subprocess.CalledProcessError as e:
                    clz._logger.exception('')
                    reason = 'tts failed'
                    failed = True
                except ExpiredException:
                    clz._logger.debug(f'EXPIRED generating voice')

                transcoder: WaveToMpg3Encoder = WaveToMpg3Encoder.LAME

                if not failed:
                    if transcoder == WaveToMpg3Encoder.MPLAYER:
                        try:
                            subprocess.run(['mplayer', '-i', '/tmp/tst.wav', '-f', 'mp3',
                                            f'{voice_file_path}'], shell=False, text=True, check=True)
                        except subprocess.CalledProcessError:
                            clz._logger.exception('')
                            reason = 'mplayer failed'
                            failed = True
                    if transcoder == WaveToMpg3Encoder.FFMPEG:
                        try:
                            subprocess.run(['ffmpeg', '-loglevel', 'error', '-i',
                                            '/tmp/tst.wav', '-acodec', 'libmp3lame',
                                            f'{voice_file_path}'], shell=False,
                                           text=True, check=True)
                        except subprocess.CalledProcessError:
                            clz._logger.exception('')
                            reason = 'ffmpeg failed'
                            failed = True
                    if transcoder == WaveToMpg3Encoder.LAME:
                        try:
                            subprocess.run(['lame', '/tmp/tst.wav',
                                            f'{voice_file_path}'], shell=False,
                                           text=True, check=True)
                        except subprocess.CalledProcessError:
                            clz._logger.exception('')
                            reason = 'lame failed'
                            failed = True
                if failed and save_to_file:
                    if clz._logger.isEnabledFor(ERROR):
                        clz._logger.error(
                                f'Failed to download voice for {text_to_voice} '
                                f'reason {reason}')
                    if text_to_voice is not None and voice_file_path is not None:
                        try:
                            if os.path.isfile(failing_voice_text_file):
                                os.unlink(failing_voice_text_file)

                            with open(failing_voice_text_file, 'wt') as f:
                                f.write(text_to_voice)
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                        f'Failed to save sample text to voice file: '
                                        f'{str(e)}')
                            try:
                                os.remove(failing_voice_text_file)
                            except Exception as e2:
                                pass
            except Exception as e:
                if clz._logger.isEnabledFor(ERROR):
                    clz._logger.error(
                            'Failed to download voice: {}'.format(str(e)))
                voice_file_path = None
                aggregate_voiced_bytes = b''
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'aggregate_voiced_bytes:'
                                      f' {len(aggregate_voiced_bytes)}')
        rc = 0
        return rc

    def create_cmdline(self, phrase: Phrase) -> int:
        clz = type(self)
        text_file: str
        output_dir: pathlib.Path
        output_path: pathlib.Path = None
        rc: int = 0

        try:
            model = 'tts_models/en/ljspeech/tacotron2-DDC_ph'
            vocoder = 'vocoder_models/en/ljspeech/univnet'
            output_path = phrase.get_cache_path()
            output_dir = output_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(['tts', f'{phrase.get_text()}', '--model_name', model, '--vocoder_name',
                            vocoder, '--out_path', '/tmp/tst.wav'], shell=True, text=True,
                           check=True)
        except subprocess.CalledProcessError:
            clz._logger.exception('')
            rc = 1
        except ExpiredException:
            rc = 10
        if rc == 0:
            try:
                subprocess.run(['mplayer', '-benchmark', '-vo', 'null', '-vc', 'null',
                                '-ao', f'pcm:fast:file={output_path}', '/tmp/tst.wav'],
                               shell=False, text=True, check=True)
            except subprocess.CalledProcessError:
                clz._logger.exception('')
                rc = 2
        return rc

    def update(self):
        self.process = None
        self.stop_processing = False

    def notify(self, msg: str, now: bool = False):
        self.stop_urgent = now
        self.stop()

    def close(self):
        # self._close()
        pass

    def _close(self):
        # self.stop()
        # super()._close()
        pass

    def stop(self):
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose('stop')
        super().stop()
        self.stop_processing = True
        try:
            if self.process is not None:
                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose('terminate')
                if self.stop_urgent:
                    self.process.kill()
                else:
                    self.process.terminate()
            if self.simple_cmd is not None:
                if self.stop_urgent:
                    self.simple_cmd.process.kill()
                else:
                    self.simple_cmd.process.terminate()

        except AbortException:
            reraise(*sys.exc_info())
        except:
            pass

    @classmethod
    def settingList(cls, setting, *args) \
            -> List[str] | List[Tuple[str, str]] | Tuple[List[str], str] | Tuple[List[Tuple[str, str]], str]:
        """
        Gets the possible specified setting values in same representation
        as stored in settings.xml (not translated). Sorting/translating done
        in UI.

        :param setting:
        :param args:
        :return:
        """
        if setting == SettingsProperties.LANGUAGE:
            # Returns list of languages and value of closest match to current
            #
            # (Display value, setting_value), default_locale-index
            return [('US-English', 'en-US')], 'en-US'

        elif setting == SettingsProperties.GENDER:
            return [Genders.FEMALE.value]

        elif setting == SettingsProperties.VOICE:
            return [('fancy', 'only')]

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            default_player: str = cls.get_setting_default(SettingsProperties.PLAYER)
            player_ids: List[str] = []
            # for player in cls.player_handler_class().getAvailablePlayers():
            #     player_ids.append(player.ID)
            return player_ids, default_player

    # Intercept simply for testing purposes: to disable bypass
    # of voicecache during config to avoid hammering remote
    # vender service.
    #
    # TODO: Remove on ship
    '''
    @classmethod
    def setSetting(cls, key, value):
        changed = super().setSetting(key, value)
        VoiceCache.for_debug_setting_changed()
        return changed
    '''

    @classmethod
    def negotiate_engine_config(cls, engine_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        """
        Player is informing engine what it is capable of controlling
        Engine replies what it is allowing engine to control
        """
        if Settings.is_use_cache():
            return True, True, True

        return False, False, False

    @classmethod
    def getVolumeDb(cls) -> float | None:
        volume_validator: ConstraintsValidator | IValidator
        volume_validator = SettingsMap.get_validator(cls.service_ID,
                                                     property_id=SettingsProperties.VOLUME)
        # volume is hardcoded to a fixed value
        volume: float = volume_validator.getValue()
        return volume  # Find out if used

    @classmethod
    def getEngineVolume(cls) -> float:
        """
        Get the configured volume in TTS standard  -12db .. +12db scale converted
        to the native volume of this engine, which happens to be the same as TTS.
        However the value is fixed. All adjustment is done by player
        """

        return cls.getVolumeDb()

    @classmethod
    def getEngineVolume_str(cls) -> str:
        volume_validator: ConstraintsValidator
        volume_validator = cls.get_validator(cls.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume: str = volume_validator.getUIValue()
        return volume

    @classmethod
    def getVoice(cls) -> str:
        voice = cls.getSetting(SettingsProperties.VOICE)
        if voice is None:
            lang = cls.voices_by_locale_map.get(cls.getLanguage())
            if lang is not None:
                voice = lang[0][1]
        voice = 'g2'
        return voice

    @classmethod
    def getLanguage(cls) -> str:
        language_validator: ConstraintsValidator
        language_validator = cls.get_validator(cls.service_ID,
                                               property_id=SettingsProperties.LANGUAGE)
        language: str = language_validator.getValue()
        language = 'en-US'
        return language

    @classmethod
    def getPitch(cls) -> float:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        pitch_validator: ConstraintsValidator
        pitch_validator = cls.get_validator(cls.service_ID,
                                            property_id=SettingsProperties.PITCH)
        if Settings.is_use_cache():
            pitch = pitch_validator.default_value
        else:
            pitch: float = pitch_validator.getValue()
        return pitch

    @classmethod
    def getPitch_str(cls) -> str:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        # TODO: Solve this differently!!!!

        pitch: float = cls.getPitch()
        return '{:.2f}'.format(pitch)

    @classmethod
    def getSpeed(cls) -> float:
        # Native ResponsiveVoice speed is 1 .. 100, with default of 50,
        # Since Responsive voice always requires a player, and caching is
        # a practical necessity, a fixed setting of 50 is used with Responsive Voice
        # and leave it to the player to adjust speed.
        #
        # Kodi TTS uses a speed of +0.25 .. 1 .. +4.0
        # 0.25 is 1/4 speed and 4.0 is 4x speed
        #
        # This speed is represented as a setting as in integer by multiplying
        # by 100.
        #
        return 0.75

    @classmethod
    def getApiSpeed(cls) -> str:
        speed: float = cls.getSpeed()
        # Leave it to the player to adjust speed
        return "50"

    @classmethod
    def getGender(cls) -> str:
        gender = 'female'
        return gender

    @classmethod
    def getAPIKey(cls) -> str:
        return ''

    # All voices are empty strings
    # def setVoice(self, voice):
    #    self.voice = voice
