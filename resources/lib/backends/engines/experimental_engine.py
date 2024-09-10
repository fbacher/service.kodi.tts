# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import io
import os
import pathlib
import subprocess
import sys
from datetime import timedelta
from enum import Enum
from time import time

try:
    import regex
except ImportError:
    import re as regex

from common import *

from backends.audio.sound_capabilties import ServiceType
from backends.base import SimpleTTSBackend
from backends.players.iplayer import IPlayer
from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator
from cache.voicecache import VoiceCache
from common.constants import ReturnCode
from common.exceptions import ExpiredException
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import Backends, Genders, Mode
from common.settings import Settings
from common.simple_run_command import SimpleRunCommand
from utils.util import runInThread

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class WaveToMpg3Encoder(Enum):
    FFMPEG = 0
    MPLAYER = 1
    LAME = 2


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
        self.download: bytes = None
        self.finished: bool = False
        self.phrase: Phrase = None

    def get_rc(self) -> ReturnCode:
        return self.rc

    def get_download(self) -> bytes | None:
        return self.download

    def is_finished(self) -> bool:
        return self.finished

    def get_phrase(self) -> Phrase:
        return self.phrase

    def set_finished(self, finished: bool) -> None:
        self.finished = finished

    def set_download(self, data: bytes | None) -> None:
        self.download = data

    def set_rc(self, rc: ReturnCode) -> None:
        self.rc = rc

    def set_phrase(self, phrase: Phrase) -> None:
        self.phrase = phrase


class SpeechGenerator:
    RESPONSIVE_VOICE_URL: Final[
        str] = "http://responsivevoice.org/responsivevoice/getvoice.php"
    MAXIMUM_PHRASE_LENGTH: Final[int] = 200

    _logger: BasicLogger = None

    def __init__(self) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.generate_results: Results = Results()
        self.simple_cmd: SimpleRunCommand

    def set_rc(self, rc: ReturnCode) -> None:
        self.generate_results.set_rc(rc)

    def get_rc(self) -> ReturnCode:
        return self.generate_results.get_rc()

    def set_phrase(self, phrase: Phrase) -> None:
        self.generate_results.set_phrase(phrase)

    def set_download(self, download: bytes) -> None:
        self.generate_results.set_download(download)

    def set_finished(self) -> None:
        self.generate_results.set_finished(True)

    def is_finished(self) -> bool:
        return self.generate_results.is_finished()

    def get_results(self) -> Results:
        if self.get_rc() == ReturnCode.OK:
            phrase: Phrase = self.generate_results.get_phrase()
            phrase.set_exists(True)
        return self.generate_results

    def generate_speech(self, caller: Callable,
                        phrase: Phrase, timeout: float = 30.0) -> Results:
        # Disable expiration checks. We are doing this in background. Results
        # are cached for next time

        unchecked_phrase: Phrase = phrase.clone(check_expired=False)
        self.set_phrase(unchecked_phrase)
        runInThread(self._generate_speech, name='download_speech', delay=0.0,
                    phrase=unchecked_phrase)
        max_wait: int = int(timeout / 0.1)
        while Monitor.exception_on_abort(timeout=0.1):
            max_wait -= 1
            if (self.get_rc() == ReturnCode.OK or caller.stop_processing or
                    max_wait <= 0):
                break
        return self.generate_results

    def _generate_speech(self, phrase: Phrase) -> ReturnCode:
        # Break long texts into 250 char chunks so that they can be downloaded.
        # Concatenate returned binary voice files together and return
        clz = type(self)
        self.set_rc(ReturnCode.OK)
        text_file_path: pathlib.Path = None
        try:
            clz._logger.debug_extra_verbose(f'Text len: {len(phrase.get_text())} '
                                            f'{phrase.get_text()}')
            Monitor.exception_on_abort()
            save_copy_of_text: bool = True
            save_to_file: bool = phrase.get_cache_path() is not None

            cache_file: IO[io.BufferedWriter] = None
            if save_to_file:
                rc2: int
                rc2, cache_file = VoiceCache.create_sound_file(phrase.get_cache_path(),
                                                               create_dir_only=False)
                if rc2 != 0 or cache_file is None:
                    if clz._logger.isEnabledFor(ERROR):
                        clz._logger.error(f'Failed to create cache file {cache_file}')
                    self.set_rc(ReturnCode.CALL_FAILED)
                    return self.get_rc()
            try:
                # Should only get here if voiced file (.wav, .mp3, etc.) was NOT
                # found. We might see a pre-existing .txt file which means that
                # the download failed. To prevent multiple downloads, wait a day
                # before retrying the download.

                failing_voice_text_file: pathlib.Path | None = None
                if save_to_file:
                    failing_voice_text_file = phrase.get_cache_path().with_suffix(
                            '.txt')
                    if (failing_voice_text_file.is_file() and
                            failing_voice_text_file.exists()):
                        expiration_time: float = time() - timedelta(
                                hours=24).total_seconds()
                        if (
                                os.stat(failing_voice_text_file).st_mtime <
                                expiration_time):
                            clz._logger.debug(f'voice_file_path.unlink(')
                        else:
                            clz._logger.debug_extra_verbose(
                                    'Previous attempt to get speech failed. '
                                    'Skipping.')
                            self.set_rc(ReturnCode.MINOR)
                            return self.get_rc()

                    if save_copy_of_text:
                        path: str
                        file_type: str
                        text_file_path = failing_voice_text_file
                        text_file_path = text_file_path.with_suffix('.txt')
                        try:
                            text_file_path.unlink(missing_ok=True)

                            with text_file_path.open('wt', encoding='utf-8') as f:
                                f.write(phrase.get_text())
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(f'Failed to save voiced text file: '
                                                  f'{text_file_path} Exception: '
                                                  f'{str(e)}')

                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose(f'phrase len: '
                                              f'{len(phrase.get_text())}')

                # Pass means for results to be communicated back. Caller can
                # choose to ignore/abandon results, but download will still
                # occur and cached for later use.
                self.generate_results: Results = Results()

                runInThread(self.tts_generate, name='tts_generate', delay=0.0,
                            phrase=phrase)
                thirty_seconds: int = int(30 / 0.1)
                while Monitor.exception_on_abort(timeout=0.1):
                    thirty_seconds -= 1
                    if (
                            self.generate_results.get_rc() == ReturnCode.OK or
                            thirty_seconds <= 0):
                        break

                if self.get_rc() != ReturnCode.OK:
                    text_file_path.unlink(missing_ok=True)

            except AbortException:
                text_file_path.unlink(missing_ok=True)
                self.set_rc(ReturnCode.ABORT)
                reraise(*sys.exc_info())
            except Exception:
                clz._logger.exception('')
                self.set_rc(ReturnCode.CALL_FAILED)
        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            reraise(*sys.exc_info())
        except Exception:
            clz._logger.exception('')
            self.set_rc(ReturnCode.CALL_FAILED)
            return self.get_rc()
        return self.get_rc()

    def tts_generate(self, phrase: Phrase) -> ReturnCode:
        clz = type(self)
        failed: bool = False
        if Settings.get_setting_bool(SettingsProperties.DELAY_VOICING,
                                     ExperimentalTTSBackend.service_ID,
                                     ignore_cache=False,
                                     default=True):
            clz._logger.debug(f'Generation of voice files disabled by settings')
            self.set_rc(ReturnCode.MINOR_SAVE_FAIL)
            return self.get_rc()
        text_file: str
        text_to_voice: str = phrase.get_text()
        voice_file_path: pathlib.Path = phrase.get_cache_path()
        output_dir: pathlib.Path
        output: pathlib.Path
        self.set_rc(ReturnCode.OK)
        model = 'tts_models/en/ljspeech/tacotron2-DDC_ph'
        vocoder = 'vocoder_models/en/ljspeech/univnet'
        try:
            self.simple_cmd = SimpleRunCommand(['tts', '--text', f'{text_to_voice}',
                                                '--model_name', model,
                                                '--vocoder_name', vocoder,
                                                '--out_path', '/tmp/tst.wav'])
            self.simple_cmd.run_cmd()
            self.simple_cmd = None
            phrase.set_exists(True)
        except subprocess.CalledProcessError as e:
            clz._logger.exception('')
            failed = True
        except ExpiredException:
            clz._logger.debug(f'EXPIRED generating voice')
            self.set_rc(ReturnCode.EXPIRED)
        transcoder: WaveToMpg3Encoder = WaveToMpg3Encoder.LAME

        if not failed:
            if transcoder == WaveToMpg3Encoder.MPLAYER:
                try:
                    subprocess.run(['mencoder', '-really_quiet',
                                    '-af', 'volume=-10', '-i', '/tmp/tst.wav',
                                    '-o', 'output_file',
                                    f'{voice_file_path}'], shell=False, text=True,
                                   check=True)
                except subprocess.CalledProcessError:
                    clz._logger.exception('')
                    self.set_rc(ReturnCode.CALL_FAILED)
            elif transcoder == WaveToMpg3Encoder.FFMPEG:
                try:
                    subprocess.run(['ffmpeg', '-loglevel', 'error', '-i',
                                    '/tmp/tst.wav', '-filter:a', 'speechnorm',
                                    '-acodec', 'libmp3lame',
                                    f'{voice_file_path}'], shell=False,
                                   text=True, check=True)
                except subprocess.CalledProcessError:
                    clz._logger.exception('')
                    failed = True
                    self.set_rc(ReturnCode.CALL_FAILED)
            elif transcoder == WaveToMpg3Encoder.LAME:
                try:
                    # --scale 0.40 reduces volume by 40%
                    subprocess.run(['lame', '--scale', '0.40',
                                    '--replaygain-accurate', '/tmp/tst.wav',
                                    f'{voice_file_path}'], shell=False,
                                   text=True, check=True)
                except subprocess.CalledProcessError:
                    clz._logger.exception('')
                    reason = 'lame failed'
                    failed = True
                    self.set_rc(ReturnCode.CALL_FAILED)
        return self.get_rc()


class ExperimentalTTSBackend(SimpleTTSBackend):

    ID: str = Backends.EXPERIMENTAL_ENGINE_ID
    backend_id = Backends.EXPERIMENTAL_ENGINE_ID
    engine_id = Backends.EXPERIMENTAL_ENGINE_ID
    service_ID: str = Services.EXPERIMENTAL_ENGINE_ID
    service_TYPE: str = ServiceType.ENGINE

    MAXIMUM_PHRASE_LENGTH: Final[int] = 200
    _logger: BasicLogger = None
    _initialized: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)

        self.process = None
        self.stop_processing = False
        self.simple_cmd: SimpleRunCommand = None
        self.stop_urgent: bool = False
        if not clz._initialized:
            clz.register(self)
            clz._initialized = True

    def init(self) -> None:
        clz = type(self)
        if self.initialized:
            return
        super().init()
        self.update()

    def getMode(self) -> Mode:
        clz = type(self)
        player: IPlayer = self.get_player(clz.service_ID)
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
            if not phrase.exists():
                generator: SpeechGenerator = SpeechGenerator()
                results: Results = generator.generate_speech(self, phrase)
                if results.get_rc() == ReturnCode.OK:
                    phrase.set_exists(True)
        except ExpiredException:
            clz._logger.debug(f'EXPIRED at engine')
            return False
        return phrase.exists()

    def runCommandAndPipe(self, phrase: Phrase):
        clz = type(self)

        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        audio_pipe = None
        voice_file: str | None
        exists: bool
        byte_stream: io.BinaryIO = None
        rc: int = -2
        try:
            if not phrase.exists():
                rc = self.generate_speech(phrase)

            if self.stop_processing:
                if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    clz._logger.debug_extra_verbose('stop_processing')
                return False

            try:
                byte_stream = io.open(phrase.get_cache_path(), 'rb')
            except ExpiredException:
                clz._logger.debug('EXPIRED in engine')
            except Exception:
                rc = 1
                clz._logger.exception('')
                byte_stream = None
        except ExpiredException:
            clz._logger.debug('EXPIRED in engine')

        return byte_stream

    def seed_text_cache(self, phrases: PhraseList) -> None:
        # For engine that are expensive, it can be beneficial to cache the voice
        # files. In addition, by saving text to the cache that is not yet
        # voiced, then a background process can generate speech so the cache
        # gets built more quickly

        clz = type(self)
        try:
            # We don't care whether it is too late to say this text.

            phrases = phrases.clone(check_expired=False)
            for phrase in phrases:
                if Settings.is_use_cache():
                    VoiceCache.get_path_to_voice_file(phrase, use_cache=True)
                    if not phrase.exists():
                        text_to_voice: str = phrase.get_text()
                        voice_file_path: pathlib.Path = phrase.get_cache_path()
                        clz._logger.debug_extra_verbose(f'PHRASE Text {text_to_voice}')
                        rc: int = 0
                        try:
                            # Should only get here if voiced file (.wav, .mp3,
                            # etc.) was NOT
                            # found. We might see a pre-existing .txt file which means
                            # that
                            # the download failed. To prevent multiple downloads,
                            # wait a day
                            # before retrying the download.

                            voice_text_file: pathlib.Path | None = None
                            voice_text_file = voice_file_path.with_suffix('.txt')
                            try:
                                if os.path.isfile(voice_text_file):
                                    os.unlink(voice_text_file)

                                with open(voice_text_file, 'wt', encoding='utf-8') as f:
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

    def generate_speech(self, phrase: Phrase) -> ReturnCode:
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
            return ReturnCode.EXPIRED

        failed: bool = False
        save_copy_of_text: bool = True
        save_to_file: bool = voice_file_path is not None
        rc: ReturnCode = ReturnCode.OK
        voiced_buffer: IO[io.BufferedWriter] = None
        if save_to_file:
            # This engine only writes to file it creates
            rc, _ = VoiceCache.create_sound_file(voice_file_path,
                                                 create_dir_only=True)
            if rc != ReturnCode.OK:
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

                failing_voice_text_file: pathlib.Path | None = None  # None when
                # save_to_file False
                if save_to_file:
                    failing_voice_text_file = voice_file_path.with_suffix('.txt')
                    if (failing_voice_text_file.is_file() and
                            failing_voice_text_file.exists()):
                        expiration_time: float = time() - timedelta(
                            hours=24).total_seconds()
                        if (os.stat(failing_voice_text_file).st_mtime <
                                expiration_time):
                            clz._logger.debug(f'voice_file_path.unlink(missing_ok=True)')
                        else:
                            clz._logger.debug_extra_verbose(
                                    'Previous attempt to get speech failed. Skipping.')
                            rc = ReturnCode.MINOR
                            return rc

                    if save_copy_of_text:
                        path: str
                        file_type: str
                        copy_text_file_path: pathlib.Path
                        copy_text_file_path = voice_file_path.with_suffix('.txt')
                        try:
                            if (copy_text_file_path.is_file() and
                                    copy_text_file_path.exists()):
                                copy_text_file_path.unlink()

                            with copy_text_file_path.open('wt', encoding='utf-8') as f:
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
                    rc = ReturnCode.MINOR_SAVE_FAIL
                    return rc
                text_file: str
                output_dir: pathlib.Path
                output: pathlib.Path
                rc: int = ReturnCode.OK
                reason: str = ''
                model = 'tts_models/en/ljspeech/tacotron2-DDC_ph'
                vocoder = 'vocoder_models/en/ljspeech/univnet'
                try:
                    self.simple_cmd = SimpleRunCommand(
                            ['tts', '--text', f'{text_to_voice}',
                             '--model_name', model,
                             '--vocoder_name', vocoder,
                             '--out_path', '/tmp/tst.wav'])
                    if self.stop_processing:
                        rc = ReturnCode.STOP
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
                    rc = ReturnCode.EXPIRED
                transcoder: WaveToMpg3Encoder = WaveToMpg3Encoder.LAME

                if not failed:
                    if transcoder == WaveToMpg3Encoder.MPLAYER:
                        try:
                            subprocess.run(['mencoder', '-really_quiet',
                                            '-af', 'volume=-10', '-i', '/tmp/tst.wav',
                                            '-o', 'output_file',
                                            f'{voice_file_path}'], shell=False, text=True,
                                           check=True)
                        except subprocess.CalledProcessError:
                            clz._logger.exception('')
                            reason = 'mplayer failed'
                            failed = True
                    if transcoder == WaveToMpg3Encoder.FFMPEG:
                        try:
                            subprocess.run(['ffmpeg', '-loglevel', 'error', '-i',
                                            '/tmp/tst.wav', '-filter:a', 'speechnorm',
                                            '-acodec', 'libmp3lame',
                                            f'{voice_file_path}'], shell=False,
                                           text=True, check=True)
                        except subprocess.CalledProcessError:
                            clz._logger.exception('')
                            reason = 'ffmpeg failed'
                            failed = True
                    if transcoder == WaveToMpg3Encoder.LAME:
                        try:
                            # --scale 0.40 reduces volume by 40%
                            subprocess.run(['lame', '--scale', '0.40',
                                            '--replaygain-accurate', '/tmp/tst.wav',
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

                            with open(failing_voice_text_file, 'wt', encoding='utf-8') as f:
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
        return rc

    def update(self):
        self.process = None
        self.stop_processing = False

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
            -> List[str] | List[Tuple[str, str]] | Tuple[List[str], str] | Tuple[
                List[Tuple[str, str]], str]:
        """
        Gets the possible specified setting values in same representation
        as stored in settings.xml (not translate). Sorting/translating done
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
        # Get the converter from TTS volume scale to the Engine's Scale
        # Get the Engine validator/converter

        # Since the audio for this engine is expensive, it is cached and reused many times
        # It only makes sense to save everything in the cache at a fixed 'optimal'
        # volume and leave it to the player to adjust.

        volume_validator: ConstraintsValidator | IValidator
        volume_validator = SettingsMap.get_validator(cls.service_ID,
                                                     property_id=SettingsProperties.VOLUME)
        # volume is hardcoded to a fixed value
        volume, _, _, _ = volume_validator.get_tts_values()
        return volume  # Find out if used

    @classmethod
    def getEngineVolume(cls) -> float:
        """
        The Engine's job is to make sure that it's output volume is equal to
        the TTS standard volume. Get the TTS volume from Settings
        service_id=Services.TTS, setting_id='volume'. Then use the validators
        and converters to adjust the engine's volume to match what TTS has
        in the settings.

        The same is true for every stage: engine, player, converter, etc.
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
        language: str = language_validator.get_tts_value()
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
            pitch, _, _, _ = pitch_validator.get_tts_values()
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
        # This speed is represented as a setting as an integer by multiplying
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
