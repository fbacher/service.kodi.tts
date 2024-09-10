# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |
import io
import os
import pathlib
import subprocess
import sys
import tempfile
from datetime import timedelta
from enum import Enum
from time import time

import xbmc
import xbmcvfs

import simplejson
from backends.ispeech_generator import ISpeechGenerator
from common.kodi_player_monitor import KodiPlayerMonitor
from common.piper_pipe_command import PiperPipeCommand

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
from backends.settings.validators import (ConstraintsValidator, NumericValidator,
                                          StringValidator)
from cache.voicecache import VoiceCache
from common.constants import Constants, ReturnCode
from common.exceptions import ExpiredException
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList, PhraseUtils
from common.setting_constants import Backends, Genders, Mode
from common.settings import Settings
from common.simple_run_command import SimpleRunCommand
from utils.util import runInThread

module_logger = BasicLogger.get_module_logger(module_path=__file__)
DEFAULT_MODEL: Final[str] = 'en_US-ryan-medium.onnx'
#  'en_US-lessac-medium.onnx'

'''
usage: piper [-h] -m MODEL [-c CONFIG] [-f OUTPUT_FILE] [-d OUTPUT_DIR]
             [--output-raw] [-s SPEAKER] [--length-scale LENGTH_SCALE]
             [--noise-scale NOISE_SCALE] [--noise-w NOISE_W] [--cuda]
             [--sentence-silence SENTENCE_SILENCE] [--data-dir DATA_DIR]
             [--download-dir DOWNLOAD_DIR] [--update-voices] [--debug]

options:
  -h, --help            show this help message and exit
  -m MODEL, --model MODEL
                        Path to Onnx model file
  -c CONFIG, --config CONFIG
                        Path to model config file
  -f OUTPUT_FILE, --output-file OUTPUT_FILE, --output_file OUTPUT_FILE
                        Path to output WAV file (default: stdout)
  -d OUTPUT_DIR, --output-dir OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Path to output directory (default: cwd)
  --output-raw, --output_raw
                        Stream raw audio to stdout
  -s SPEAKER, --speaker SPEAKER
                        Id of speaker (default: 0)
  --length-scale LENGTH_SCALE, --length_scale LENGTH_SCALE
                        Phoneme length
  --noise-scale NOISE_SCALE, --noise_scale NOISE_SCALE
                        Generator noise
  --noise-w NOISE_W, --noise_w NOISE_W
                        Phoneme width noise
  --cuda                Use GPU
  --sentence-silence SENTENCE_SILENCE, --sentence_silence SENTENCE_SILENCE
                        Seconds of silence after each sentence
  --data-dir DATA_DIR, --data_dir DATA_DIR
                        Data directory to check for downloaded models
                        (default: current directory)
  --download-dir DOWNLOAD_DIR, --download_dir DOWNLOAD_DIR
                        Directory to download voices into (default: first data
                        dir)
  --update-voices       Download latest voices.json during startup
  --debug               Print DEBUG messages to console
  
  { "text": "First speaker.", "speaker_id": 0, "output_file": "/tmp/speaker_0.wav" }
{ "text": "Second speaker.", "speaker_id": 1, "output_file": "/tmp/speaker_1.wav" }
'''

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
        clz = type(self)
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


class PiperSpeechGenerator(ISpeechGenerator):
    MAXIMUM_PHRASE_LENGTH: Final[int] = 10000
    piper_cmd: PiperPipeCommand = None

    _logger: BasicLogger = None

    def __init__(self) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.download_results: Results = Results()

        if clz.piper_cmd is None:
            clz.piper_cmd = PiperPipeCommand()

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

    '''
    def generate_speech(self, phrase: Phrase, timeout=1.0) -> Results:
        # Disable expiration checks. We are doing this in background. Results
        # are cached for next time

        clz = type(self)
        Monitor.exception_on_abort(timeout=0.0)
        max_phrase_length: int | None
        max_phrase_length = PiperSpeechGenerator.MAXIMUM_PHRASE_LENGTH
        self.set_phrase(phrase)
        phrase_chunks: PhraseList = PhraseUtils.split_into_chunks(phrase,
                                                                  max_phrase_length)
        unchecked_phrase_chunks: PhraseList = phrase_chunks.clone(check_expired=False)
        runInThread(self._generate_speech, name='generate_speech', delay=0.0,
                    phrase_chunks=unchecked_phrase_chunks, original_phrase=phrase,
                    timeout=timeout)
        max_wait: int = int(timeout / 0.1)
        while max_wait > 0:
            Monitor.exception_on_abort(timeout=0.1)
            max_wait -= 1
            if phrase.exists():  # Background process started elsewhere may finish
                break
            if (self.get_rc() <= ReturnCode.MINOR_SAVE_FAIL or
                    KodiPlayerMonitor.instance().isPlaying()):
                clz._logger.debug(f'generate_speech exit rc: {self.get_rc().name}  '
                                  f'stop: {KodiPlayerMonitor.instance().isPlaying()}')
                break
        return self.download_results

    def _generate_speech(self, **kwargs) -> None:
        # Break long texts into chunks so that they can be downloaded.
        # Concatenate returned binary voice files together and return
        clz = type(self)
        self.set_rc(ReturnCode.OK)
        text_file_path: pathlib.Path = None
        phrase_chunks: PhraseList | None = None
        original_phrase: Phrase = None
        try:
            # The passed in phrase_chunks, are actually chunks of a phrase. Therefor
            # we concatenate the voiced text from each chunk to produce one
            # sound file. This phrase list has expiration disabled.

            phrase_chunks = kwargs.get('phrase_chunks', None)
            if phrase_chunks is None or len(phrase_chunks) == 0:
                self.set_rc(ReturnCode.NO_PHRASES)
                self.set_finished()
                return

            original_phrase = kwargs.get('original_phrase', None)
            Monitor.exception_on_abort()
            if original_phrase.exists():
                self.set_rc(ReturnCode.OK)
                self.set_finished()
                return  # Nothing to do

        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            self.set_finished()
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
            self.set_rc(ReturnCode.CALL_FAILED)
            self.set_finished()
            return

        cache_path: pathlib.Path | None = None
        try:
            cache_path = original_phrase.get_cache_path()
            rc2: int
            rc2, _ = VoiceCache.create_sound_file(cache_path,
                                                  create_dir_only=True)
            if rc2 != 0:
                if clz._logger.isEnabledFor(ERROR):
                    clz._logger.error(f'Failed to create cache directory '
                                      f'{cache_path.parent}')
                self.set_rc(ReturnCode.CALL_FAILED)
                self.set_finished()
                return

            # with tempfile.NamedTemporaryFile(mode='w+b', buffering=-1,
            #                                  suffix=cache_path.suffix,
            #                                  prefix=cache_path.stem,
            #                                  dir=cache_path.parent,
            #                                  delete=False) as sound_file:
            # each 'phrase' is a chunk from one, longer phrase. The chunks
            # are small enough for gTTS to handle. We concatenate the results
            # from the phrase_chunks to the same file.
            phrase_chunk: Phrase = None
            for phrase_chunk in phrase_chunks:
                try:
                    Monitor.exception_on_abort()
                    if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                        clz._logger.debug_verbose(f'phrase: '
                                                  f'{phrase_chunk.get_text()}')

                    failed = clz.piper_cmd.say(phrase_chunk, model=DEFAULT_MODEL)
                    if failed:
                        clz._logger.debug(f'failed')
                        return  #  ReturnCode.CALL_FAILED
                    self.tts_generate(phrase_chunk)
                    #  my_gtts: MyGTTS = MyGTTS(phrase_chunk, lang=language)
                    # gtts.save(phrase.get_cache_path())
                    #     gTTSError – When there’s an error with the API request.
                    # gtts.stream() # Streams bytes
                    clz._logger.debug(f'Wrote cache_file fragment')
                except AbortException:
                    self.set_rc(ReturnCode.ABORT)
                    self.set_finished()
                    reraise(*sys.exc_info())
                except TypeError as e:
                    clz._logger.exception('')
                    self.set_rc(ReturnCode.DOWNLOAD)
                    self.set_finished()
                except ExpiredException:
                    clz._logger.exception('')
                    self.set_rc(ReturnCode.DOWNLOAD)
                    self.set_finished()
                except IOError as e:
                    clz._logger.exception(f'Error processing phrase: '
                                          f'{phrase_chunk.get_text()}')
                    # clz._logger.error(f'Error writing to temp file:'
                    #                   f' {str(temp_file)}')
                    self.set_rc(ReturnCode.DOWNLOAD)
                    self.set_finished()
                except Exception as e:
                    clz._logger.exception('')
                    self.set_rc(ReturnCode.DOWNLOAD)
                    self.set_finished()
            # clz._logger.debug(f'Finished with loop writing temp file: '
            #                   f'{str(temp_file)}')
            ' ''
            if self.get_rc() == ReturnCode.OK:
               #  try:
                    # if temp_file.exists() and temp_file.stat().st_size > 0:
                    #     temp_file.rename(cache_path)
                    #     original_phrase.set_exists(True)
                    #     clz._logger.debug(f'cache_file is: {str(cache_path)}')
                    # else:
                    #     self.set_rc(ReturnCode.DOWNLOAD)
                    #     self.set_finished()
                except Exception as e:
                    clz._logger.exception('')
            else:
                if temp_file.exists():
                    temp_file.unlink(True)
                self.set_rc(ReturnCode.DOWNLOAD)
                self.set_finished()
            ' ''
        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            self.set_finished()
            reraise(*sys.exc_info())
        except ExpiredException:
            clz._logger.exception('')
            self.set_finished()
            self.set_rc(ReturnCode.DOWNLOAD)
        except Exception as e:
            clz._logger.exception('')
            if clz._logger.isEnabledFor(ERROR):
                clz._logger.error('Failed to download voice: {}'.format(str(e)))
            self.set_finished()
            self.set_rc(ReturnCode.DOWNLOAD)
        clz._logger.debug(f'exit download_speech')
        self.set_finished()
        return None
    '''
    def tts_generate(self, phrase: Phrase, sound_file = None) -> ReturnCode:
        clz = type(self)
        clz._logger.debug(f'About to convert .wav to .mp3')

        failed = clz.piper_cmd.say(phrase)
        clz._logger.debug(f'piper_cmd.say completed failed: {failed}')
        if failed:
            return ReturnCode.CALL_FAILED

        voice_file_path: pathlib.Path = phrase.get_cache_path()
        transcoder: WaveToMpg3Encoder = WaveToMpg3Encoder.LAME
        if not failed:
            match transcoder:
                case  WaveToMpg3Encoder.MPLAYER:
                    try:
                        wave_path: pathlib.Path = voice_file_path.with_suffix('.wav')

                        subprocess.run(['mencoder', '-really_quiet',
                                        '-af', 'volume=-10', '-i', f'{wave_path}',
                                        '-o', 'output_file',
                                        f'{voice_file_path}'], shell=False, text=True,
                                       check=True)
                    except subprocess.CalledProcessError:
                        clz._logger.exception('')
                        failed = True
                case WaveToMpg3Encoder.FFMPEG:
                    try:
                        subprocess.run(['ffmpeg', '-loglevel', 'error', '-i',
                                        '/tmp/tst.wav', '-filter:a', 'speechnorm',
                                        '-acodec', 'libmp3lame',
                                        f'{voice_file_path}'], shell=False,
                                       text=True, check=True)
                    except subprocess.CalledProcessError:
                        clz._logger.exception('')
                        failed = True
                case WaveToMpg3Encoder.LAME:
                    try:
                        # --scale 0.40 reduces volume by 40%
                        wave_path: pathlib.Path = phrase.get_cache_path().with_suffix(
                                '.wav')
                        subprocess.run(['lame', '--scale', '0.40',
                                        '--replaygain-accurate', f'{wave_path}',
                                        f'{phrase.get_cache_path()}'], shell=False,
                                       text=True, check=True)
                    except subprocess.CalledProcessError:
                        clz._logger.exception('')
                        reason = 'lame failed'
                        failed = True
        if failed:
            self.set_rc(ReturnCode.CALL_FAILED)
            clz._logger.debug(f'Failed to convert {phrase} to .mpg')
        else:
            clz._logger.debug(f'Converted {phrase} to .mp3')
            phrase.set_exists(True)
        return self.get_rc()


class Voice:
    _logger: BasicLogger = None
    voices: List[Voice] = []

    """
     Index is lang or lang_country name
     ex: en_us voice1 would have two entries:
       "en" -> voice1
       "en_US" -> voice1
    """
    voices_by_lang_country: Dict[str, List[Voice]] = {}
    known_male_voices: List[str] = [
        'alan',
        'danny',
        'northern_english_male',
        'ryan',
        'joe',
        'hfc_male',
        'kusal'
    ]
    known_female_voices: List[str] = [
        'amy',
        'jenny',
        'hfc_female',
        'libritts',
        'libritts_r',
        'kathleen',
        'southern_english_female'
    ]

    def __init__(self, lang: str, country: str, name: str, quality: str):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.lang: str = lang
        self.country: str = country
        self.name: str = name
        self.quality: str = quality
        if name in clz.known_male_voices:
            self.gender = Genders.MALE
        elif name in clz.known_female_voices:
            self.gender = Genders.FEMALE
        else:
            self.gender = Genders.UNKNOWN
        clz._logger.debug(f'lang: {lang} country: {country} name: {name} '
                          f'quality: {quality} gender: {self.gender}')

    @staticmethod
    def parse(voice_spec: str) -> Voice:
        clz = Voice
        tokens: List[str] = voice_spec.split('-')
        clz._logger.debug(f'tokens: {tokens}')
        lang_country: str = tokens[0]
        lang: str
        country: str
        lang, country = lang_country.split('_')
        name: str = tokens[1]
        quality: str = tokens[2]
        voice: Voice = Voice(lang, country, name, quality)
        lang_entries = Voice.voices_by_lang_country.get(lang, [])
        lang_entries.append(voice)
        if len(country) > 0:
            lang_country_entries = Voice.voices_by_lang_country.get(f'{lang}_{country}', [])
            lang_country_entries.append(voice)
        return voice

    @classmethod
    def get_voices_by_lang_country(cls, lang: str, country: str = '') -> List[Voice] | None:
        return cls.voices_by_lang_country.get(f'{lang}_{country}', None)

    @classmethod
    def load_voices(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)
        voices_path_validator: StringValidator
        voices_path_validator = PiperTTSBackend.get_validator(PiperTTSBackend.service_ID,
                                                  property_id=SettingsProperties.VOICE_PATH)
        voices_dir: str = voices_path_validator.get_tts_value()
        cls._logger.debug(f'voices_dir: {voices_dir}')
        voices_dir = xbmcvfs.translatePath(voices_dir)
        voices_path: pathlib.Path = pathlib.Path(voices_dir)
        glob_pattern: str = '*.onnx'

        for path in voices_path.glob(glob_pattern):
            if not (path.is_file() and path.exists()):
                continue
            Voice.parse(path.stem)


class PiperTTSBackend(SimpleTTSBackend):

    ID: str = Backends.PIPER_ID
    backend_id = Backends.PIPER_ID
    engine_id = Backends.PIPER_ID
    service_ID: str = Services.PIPER_ID
    service_TYPE: str = ServiceType.ENGINE

    _logger: BasicLogger = None
    _initialized: bool = False
    generator: PiperSpeechGenerator = None

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
        clz.generator = PiperSpeechGenerator()
        Voice.load_voices()

    def getMode(self) -> Mode:
        clz = type(self)
        player: IPlayer = self.get_player(clz.service_ID)
        if clz.getSetting(SettingsProperties.PIPE):
            return Mode.PIPE
        else:
            return Mode.FILEOUT

    def runCommand(self, phrase: Phrase) -> bool:
        clz = type(self)
        #  clz._logger.debug(f'In runCommand')
        # If caching disabled, then exists is always false. file_path
        # always contains path to cached file, or path where to download to
        if self.stop_processing:
            if clz._logger.isEnabledFor(DEBUG):
                clz._logger.debug('stop_processing')
            return False

        exists: bool
        voiced_text: bytes
        try:
            #  clz._logger.debug(f'phrase path: {str(phrase.get_cache_path)} '
            #                    f'exists: {phrase.exists()}')
            if phrase.get_cache_path() is None:
                VoiceCache.get_path_to_voice_file(phrase,
                                                  use_cache=Settings.is_use_cache())
            if not phrase.exists():
                clz._logger.debug(f'phrase does NOT exist, calling generate')

                results: ReturnCode = clz.generator.tts_generate(phrase)
                if results == ReturnCode.OK:
                    phrase.set_exists(True)
        except ExpiredException:
            clz._logger.debug(f'EXPIRED at engine')
            return False
        #  clz._logger.debug(f'Returning from runCommand exists: {phrase.exists()}')
        return phrase.exists()

    def runCommandAndPipe(self, phrase: Phrase):
        clz = type(self)
        #  clz._logger.debug(f'In runCommandAnd Pipe')

        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        audio_pipe = None
        voice_file: str | None
        exists: bool
        byte_stream: BinaryIO = None
        rc: int = -2
        try:
            if not phrase.exists():
                rc: ReturnCode = clz.generator.tts_generate(phrase)

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
        xbmc.sleep(5000)
        clz = type(self)
        #  clz._logger.debug(f'In seed_text_cache')
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

    def generate_speech(self, phrase: Phrase, timeout: float = 0.0) -> ReturnCode:
        # If voice_file_path is None, then don't save voiced text to it,
        # just return the voiced text as bytes

        clz = type(self)
        clz._logger.debug(f'phrase: {Phrase}')
        return clz.generator.tts_generate(phrase)

    def update(self):
        clz = type(self)
        if self.stop_processing:
            clz._logger.debug(f'reset stop_processing')
        self.process = None
        self.stop_processing = False

    def close(self):
        # self._close()
        pass

    def _close(self):
        # self.stop()
        # super()._close()
        pass

    '''
    def stop(self):
        # Review this. google does not use stop. Doesn't seem to restart
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
    '''

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
            # List [(Display value, setting_value)], default_locale-index
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
    '''
    '''
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
    '''

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
        pitch_validator: NumericValidator
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

    @classmethod
    def has_speech_generator(cls) -> bool:
        return False

    @classmethod
    def get_speech_generator(cls) -> ISpeechGenerator:
        return PiperSpeechGenerator()
