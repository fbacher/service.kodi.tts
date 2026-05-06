# coding=utf-8
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
from collections import namedtuple
from pathlib import Path

import xbmc

import langcodes
from backends.engines.idownloader import IDownloader, OutputType
from backends.engines.utils.igenerator_deps import ITTSData
from backends.settings.engine_voice import EngineVoice
from backends.settings.engine_voice_group import EngineVoiceGroup
from backends.settings.engine_voice_manager import EngineVoiceManager
from backends.settings.i_engine_voice_group import IEngineVoiceGroup
from backends.settings.lang_utils import LangUtils
from common import *
from common.constants import Constants
from common.logger import *
from common.message_ids import MessageId
from common.monitor import Monitor
from common.phrases import Phrase
from backends.settings.service_types import (LabeledType, QualityType, ServiceID,
                                             ServiceKey)

MY_LOGGER = BasicLogger.get_logger(__name__)

PiperSpeakerTuple = namedtuple('PiperSpeakerTuple',
                               'lang_territory_code, '
                               'vg_name, '
                               'voice_id, '
                               'speaker_name, '
                               'speaker_id, '
                               'quality')
"""
    PiperTTS supplies voices for a good number of languages. They are organized
    in a manner similar to GoogleTTS. A group of closely related voices are
    defined by a pair of files. The file name prefix identifies the language_id,
    the Territory id,
    the name and quality of the group. An example being: en_US-lessac-medium.
    Most voice files describe a single voice, while some have a dozen or more.
    The advantage to a group of similar voice is that the voices share
    the same basic parameters, allowing the speakers to be changed without
    any performance penalty of reconfiguring the engine. This is useful
    if using different speakers in the same "conversation" is helpful. Perhaps
    female for voicing the type of control and male for the text.

    Available english voice groups:
      en_GB-alan-low
      en_GB-alan-medium
      en_GB-alba-medium
      en_GB-aru-medium
      en_GB-cori-high
      en_GB-cori-medium
      en_GB-jenny_dioco-medium
      en_GB-northern_english_male-medium
      en_GB-semaine-medium
      en_GB-southern_english_female-low
      en_GB-vctk-medium
      en_US-amy-low
      en_US-amy-medium
      en_US-arctic-medium
      en_US-bryce-medium
      en_US-danny-low
      en_US-hfc_male-medium
      en_US-joe-medium
      en_US-john-medium
      en_US-kathleen-low
      en_US-kristin-medium
      en_US-kusal-medium
      en_US-l2arctic-medium
      en_US-lessac-high
      en_US-lessac-low
      en_US-lessac-medium
      en_US-libritts-high
      en_US-libritts_r-medium
      en_US-ljspeech-high
      en_US-ljspeech-medium
      en_US-norman-medium
      en_US-reza_ibrahim-medium
      en_US-ryan-high
      en_US-ryan-low
      en_US-ryan-medium
      en_US-sam-medium

      The format is <language_code>_<territory_code>-<voice_group_name>-<quality>
      If you add the speakers within a group the full identification of
      a voice is: 
         <language_code>_<territory_code>-<voice_group_name>-<quality>-<voice>
         en_US-libritts_r-medium-5
         
      Speaker info comes from *.onnx.json:
      
       "num_symbols": 256,
  "num_speakers": 904,
  "speaker_id_map": {
    "3922": 0,  # Here voice is 3922, frequently it is a name. Speaker id is 0
    "8699": 1,
    "4535": 2,
    "6701": 3,
     ...
"""


class PiperApiType(LabeledType):
    ANY_API = 'any_api', 4, MessageId.ANY_PIPER_API
    COMPILED_API = 'compiled_api', 3, MessageId.COMPILED_PIPER_API
    PYTHON_API = 'python_api', 2, MessageId.PYTHON_PIPER_API
    HTTP_API = 'http_api', 1, MessageId.HTTP_PIPER_API


class PiperApi:
    """

    """
    #  REPLACE WITH SETTINGS

    PIPER_TTS_MAX_CHARS = 10000

    DEFAULT_HTTP_VG: str = 'en_US-libritts-high'
    PIPER_HTTP_SERVER_DEFAULT_VG_ARG: str = DEFAULT_HTTP_VG

    piper_api_type: PiperApiType | None = None
    default_piper_api: PiperApiType = PiperApiType.ANY_API
    default_piper_get_voice_api: PiperApiType = PiperApiType.ANY_API

    http_server_lock: threading.RLock = threading.RLock()
    http_server_run_state: int = 0

    HTTP_SERVER_NOT_STARTED: Final[int] = 0
    HTTP_SERVER_STARTING: Final[int] = 1
    HTTP_SERVER_RUNNING: Final[int] = 2
    HTTP_SERVER_READY: Final[int] = 3
    HTTP_SERVER_BROKEN: Final[int] = 4

    HTTP_RETRY_DELAY_SECONDS: Final[float] = 0.2
    HTTP_RETRY_LIMIT_SECONDS: Final[float] = 5.0
    HTTP_RETRY_LIMIT: Final[int] = int(
        HTTP_RETRY_LIMIT_SECONDS / HTTP_RETRY_DELAY_SECONDS) + 1

    _http_process: subprocess.Popen | None = None

    @classmethod
    def tts_langs(cls,
                  current_language: str) -> List[PiperSpeakerTuple] | None:
        """
        Discover Piper's supported voices and speakers for the current language.

        Piper language info is in the form of a Tuple with two types of entries:
          A voice entry
          A voice of a voice entry
          :param current_language: Only include voices that are the same language ('en')
          :return: List of PiperSpeakerTuple which contains simple string
                   values (voice name, etc.) needed to define Voice and VoiceGroup
                   objects.
        """
        MY_LOGGER.debug(f'In tts_langs')
        result: Tuple[int, List[str]]
        Constants.PIPER_DATA_PATH.mkdir(mode=0o775, parents=True, exist_ok=True)
        result = cls.get_vg_names()
        if result[0] != 0:
            return None

        """
        Voices are specified by files named:
            <language_code>_<territory_code>-<voice_group_name>-<quality>.onnx.json
            ex: en_US-kathleen-low.onnx.json
        These files usually describe only one voice, however they can also descibe
        additinal speakers of that voice which are simple variants of the original,
        but sound significantly different. The primary advantage of a family, is 
        that the TTS engine does not have to reload the data defining the voice when
        the voice changes. This makes it faster to have multiple speakers voice text
        than to completely switch voices.
        
        For each voice file that applies to the current Kodi language is found, 
        then an entry is returned ommiting any voice information

        If a voice file also lists speakers, then additional entries are returned
        listing the group and voice information.          
        """
        speakers: List[PiperSpeakerTuple] = []
        voices: List[str] = result[1]
        for voice in voices:
            voice: str
            if len(voice) == 0:
                continue
            MY_LOGGER.debug(f'voice: {voice} split: {voice.split("-")}')
            fields: List[str] = voice.split('-')
            lang_territory_code: str = fields[0]
            MY_LOGGER.debug(f'lang_territory_code: {lang_territory_code}')
            voice_locale: str = langcodes.Language.get(lang_territory_code).to_tag()
            voice_language: str = langcodes.Language.get(voice_locale).language
            MY_LOGGER.debug(f'voice_locale: {voice_locale} '
                            f'current_language: {current_language}')
            if voice_language != current_language:
                continue
            voice_name: str = fields[1]
            quality: QualityType = QualityType.UNKNOWN
            if len(fields) >= 3:
                try:
                    quality = QualityType(fields[2])
                except KeyError:
                    MY_LOGGER.debug(f'Invalid QualityType: {fields[2]}')

            # Determine if there are multiple speakers for this voice, or
            # just the single voice.

            speaker: str | None = None
            result_entry: PiperSpeakerTuple | None = None

            json_data: Dict[str, Any]
            json_data = cls.get_voice_data(voice,
                                           keep_definition=True)
            # The default voice is 0, which is also the voice id to use
            # when there is a single voice.

            vg_label: str = f'{voice_name}'
            speaker_id: str = '0'
            # Describe the voice file
            MY_LOGGER.debug(f'lang_territory_code: {lang_territory_code}\n'
                            f'voice: {voice}\n'
                            f'voice_name: {voice_name}\n'
                            f'vg_label: {vg_label}\n'
                            f'quality: {quality}')
            single_voice_entry = PiperSpeakerTuple(
                lang_territory_code=lang_territory_code,
                vg_name=vg_label,
                voice_id=voice,
                speaker_name=voice_name,
                speaker_id=speaker_id,
                quality=quality)
            speakers_in_vg: int = 0
            MY_LOGGER.debug(f'speaker_id: {speaker_id} type: {type(speaker_id)}')

            # MY_LOGGER.debug(f'json_data: {json_data} voice: {voice}')
            # No 'speaker_id_map' is needed when there is only the default
            # voice.
            vg_name: str = ''
            if json_data.get('dataset'):
                vg_name = json_data.get('dataset')
            if json_data.get('speaker_id_map'):
                # Convert int speaker_ids to str to make consistent with
                # vg_id.

                speaker_id_map: Dict[str, int] = json_data.get('speaker_id_map')
                for speaker_name, speaker_id in speaker_id_map.items():
                    speaker_name: str
                    speaker_id: str = str(speaker_id)
                    if MY_LOGGER.isEnabledFor(DEBUG_XV):
                        MY_LOGGER.debug_xv(f'lang_territory_code: {lang_territory_code}\n'
                                           f'speaker_name: {speaker_name}\n'
                                           f'voice_group: {voice}\n'
                                           f'vg_label: {vg_label}\n'
                                           f'speaker_id: {speaker_id}\n'
                                           f'quality: {quality}')

                    result_entry = PiperSpeakerTuple(
                        lang_territory_code=lang_territory_code,
                        vg_name=vg_label,
                        voice_id=voice,
                        speaker_name=speaker_name,
                        speaker_id=speaker_id,
                        quality=quality)
                    speakers_in_vg += 1
                    speakers.append(result_entry)
            if speakers_in_vg == 0:
                MY_LOGGER.debug(f'Appending single voice entry vg: {vg_label} '
                                f'speaker: {speaker_id} ')
                speakers.append(single_voice_entry)
        MY_LOGGER.debug(f'Found {len(speakers)} speakers')
        return speakers

    @classmethod
    def get_voice_groups(cls,
                         onnx_model_config_file: str,
                         keep_definition: bool = True) -> Dict[str, str]:
        """
        Reads given onnx_model_config_file (downloading as necessary) and returns
        the voices defined in the .json file. When downloaded, file(s) will be
        saved in Kodi TTS userdata space.

        :param onnx_model_config_file: base name of the onnx_model_config_file to download
        :param keep_definition: Keep the much larger voice definition file (.onnx)

        :return Tuple[<map of any speakers defined in onnx_model_config_file>],
                      Path to onnx_model_config_file, Path to onnx_model_file]
                      If path does not exist, then None is returned.

        To help reduce disk space, the definition (.onnx) are deleted, unless
        keep_definition is specified. Note: After the definition file has been
        downloaded, keep_definition will have no effect.

        TODO: Need mechanism to detect when file changes and needs updating.
        """
        MY_LOGGER.debug(
            f'get_voice_groups onnx_model_config_file: {onnx_model_config_file}')

        onnx_model_config: Dict[str, str]
        onnx_model_config = cls.get_voice_data(onnx_model_config_file,
                                               keep_definition=keep_definition)
        return onnx_model_config

    @classmethod
    def get_onnx_model(cls, onnx_model_file: str) -> Path | None:
        """
        Reads given onnx_model_config_file (downloading as necessary) and returns
        the voices defined in the .json file. When downloaded, file(s) will be
        saved in Kodi TTS userdata space.

        :param onnx_model_file: base name of the onnx_model_file to download

        :return Path to onnx_model_file if successful, None, otherwise

        To help reduce disk space, the definition (.onnx) are deleted, unless
        keep_definition is specified. Note: After the definition file has been
        downloaded, keep_definition will have no effect.

        TODO: Need mechanism to detect when file changes and needs updating.
        """
        MY_LOGGER.debug(f'get_onnx_model: {onnx_model_file}')

        onnx_model_config_file: str = f'{onnx_model_file}.json'
        onnx_model_config: Dict[str, Any]
        onnx_model_config = cls.get_voice_data(onnx_model_file,
                                               keep_definition=True)
        download_dir: Path = Path(f'{Constants.PIPER_DATA_PATH}')
        onnx_model_path: Path = download_dir / onnx_model_file
        if onnx_model_path.exists():
            return onnx_model_path
        return None

    @classmethod
    def get_voice_data(cls, voice_file_name: str,
                       keep_definition: bool = False) -> Dict[str, Any] | None:
        """
        Downloads the onnx_model_config_file (*.onnx.json) and onnx_model_file (*.onnx)
        files, as needed. Note that there is currently no way to download
        the .json or .onnx file alone.

        :param voice_file_name: base name of the voice files
        :param keep_definition: When True, keep the .onnx (and .onnx.json) files after
        downloading. (It doesn't make much sense to throw away the .onnx.json file.)

        :return: the contents of the onnx_model_file file (.onnx.json) as a Dictionary
        """
        MY_LOGGER.debug(f'get_voice_data voice_file_name: {voice_file_name}')
        results: Dict[str, Any] | None = None
        download_dir: Path = Path(f'{Constants.PIPER_DATA_PATH}')
        onnx_model_file: Path = download_dir / f'{voice_file_name}.onnx'
        onnx_model_config_file: Path = download_dir / f'{voice_file_name}.onnx.json'
        MY_LOGGER.debug(f'onnx_model_file: {onnx_model_file}\n'
                        f'onnx_model_config_file: {onnx_model_config_file}')
        MY_LOGGER.debug(f'onnx_model_config_file_exists:'
                        f' {onnx_model_config_file.exists()}\n'
                        f'keep_definition: {keep_definition}\n'
                        f'onnx_model_file_exists: {onnx_model_file.exists()}')

        if (not onnx_model_config_file.exists() or
                (keep_definition and not onnx_model_file.exists())):
            env = cls.get_basic_env()
            args: list[str] = cls.get_basic_args()
            args.extend(['-m',
                         Constants.PIPER_DOWNLOAD_VOICES, f'{voice_file_name}',
                         '--data-dir', f'{Constants.PIPER_DATA_PATH}'])
            MY_LOGGER.debug(f'About to run args: {args}')
            rc = PiperApi.run_command(args, env)
            MY_LOGGER.debug(f'rc: {rc}')
            if not (onnx_model_file.exists() or onnx_model_config_file.exists()):
                MY_LOGGER.debug(f'Download failed for : {onnx_model_file} and '
                                f'{onnx_model_config_file}')
                return None
        try:
            with onnx_model_config_file.open(mode='r') as vcf:
                results = json.load(vcf)

        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
        # Always keep the.json file
        if not keep_definition and onnx_model_file.exists():
            onnx_model_file.unlink(missing_ok=True)

        return results

    @classmethod
    def get_vg_names(cls) -> Tuple[int, List[str]]:
        """
        Queries the piper engine for list of supported voice names.

        :return: Tuple[rc, list of supported voice names]
        """
        result: Tuple[int, List[str]] = -1, []
        piper_api = cls.default_piper_get_voice_api
        MY_LOGGER.debug(f'get_vg_data')
        try:
            if piper_api == PiperApiType.ANY_API:
                result = cls.get_vg_names_by_http()
                if result[0] == 0:
                    return result
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
        result = cls.get_vg_names_by_python_command()
        return result

    @classmethod
    def get_voice_data_by_http(cls) -> Tuple[int, Dict[str, Any]]:
        cls.start_builtin_http_server()
        return cls._get_voice_data_by_http()

    @classmethod
    def _get_voice_data_by_http(cls) -> Tuple[int, Dict[str, Any]]:
        """
        Queries http server about installed voices.

        Called both during the startup of http server and after startup.
        """
        rc: int = -1
        data: Dict[str, Any] = {}
        try:

            args: List[str] = [str(Constants.CURL_PATH),
                               f'{Constants.PIPER_HTTP_SERVER_HOST}:'
                               f'{Constants.PIPER_HTTP_SERVER_PORT}/voices']
            env = cls.get_basic_env()
            json_str: str
            rc, json_str = cls.run_command(args, env)
            data: dict[str, Any] = {}
            # MY_LOGGER.debug(f'http json_strs: |{json_strs}|END|')
            # json_strs = f'{json_strs}\n'
            data = json.loads(json_str)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            return -1, {}
        return rc, data

    @classmethod
    def get_vg_names_by_http(cls) -> Tuple[int, List[str]]:
        voice_data: Dict[str, Any]
        rc, voice_data = cls.get_voice_data_by_http()
        vg_names: List[str] = list(voice_data.keys())
        return rc, vg_names

    @classmethod
    def get_vg_names_by_python_command(cls) -> Tuple[int, List[str]]:
        """
        Queries the piper engine for list of supported voices.

        Note that Piper supports multiple ways to query:
          1) Fastest is via http (avoids startup overhead of command)
          2) Slowest is Python only
        Compiled code + Python DOES NOT support query

        Each of the above means to query Piper will be tried, in order, until
        success.

        The user can install Piper wherever they wish, using whatever http server
        and port that they like. Particular care is needed to provide user with
        configuration/discovery tools.

        usage: __main__.py [-h] -m MODEL [-c CONFIG] [-i INPUT_FILE] [-f OUTPUT_FILE] [
        -d OUTPUT_DIR]
                   [--output-raw] [-s SPEAKER] [--length-scale LENGTH_SCALE]
                   [--noise-scale NOISE_SCALE] [--noise-w-scale NOISE_W_SCALE] [--cuda]
                   [--sentence-silence SENTENCE_SILENCE] [--volume VOLUME] [
                   --no-normalize]
                   [--data-dir DATA_DIR] [--debug]

        options:
          -h, --help            show this help message and exit
          -m MODEL, --model MODEL
                                Path to Onnx model file
          -c CONFIG, --download CONFIG
                                Path to model download file
          -i INPUT_FILE, --input-file INPUT_FILE, --input_file INPUT_FILE
                                Paths to input text files
          -f OUTPUT_FILE, --output-file OUTPUT_FILE, --output_file OUTPUT_FILE
                                Path to output WAV file (default: stdout)
          -d OUTPUT_DIR, --output-dir OUTPUT_DIR, --output_dir OUTPUT_DIR
                                Path to output directory (default: cwd)
          --output-raw, --output_raw
                                Stream raw audio to stdout
          -s SPEAKER, --voice SPEAKER
                                Id of voice (default: 0)
          --length-scale LENGTH_SCALE, --length_scale LENGTH_SCALE
                                Phoneme length
          --noise-scale NOISE_SCALE, --noise_scale NOISE_SCALE
                                Generator noise
          --noise-w-scale NOISE_W_SCALE, --noise_w_scale NOISE_W_SCALE, --noise-w
          NOISE_W_SCALE, --noise_w NOISE_W_SCALE
                                Phoneme width noise
          --cuda                Use GPU
          --sentence-silence SENTENCE_SILENCE, --sentence_silence SENTENCE_SILENCE
                                Seconds of silence after each sentence
          --volume VOLUME       Volume multiplier (default: 1.0)
          --no-normalize        Don't normalize audio
          --data-dir DATA_DIR, --data-dir DATA_DIR
                                Data directory to check for voice models (default:
                                current directory)
          --debug               Print DEBUG messages to console

        """
        env = cls.get_basic_env()
        args = cls.get_basic_args()
        args: list[str]
        args.extend(['-m',
                     Constants.PIPER_DOWNLOAD_VOICES])
        process: subprocess.CompletedProcess | None = None
        '''
         Returns a list of voice names:
         ar_JO-kareem-medium
         bg_BG-dimitar-medium
         ca_ES-upc_ona-medium
        '''
        voice_names: List[str]
        rc, voice_names = cls.run_command(args, env)
        return rc, voice_names

    @classmethod
    def start_builtin_http_server(cls) -> None:
        """
        Starts the builtin http server to provide services using cached data
        rather than just constantly reinitializing the TTS engine, etc. on every
        voicing.

        Basically, the server is started by:

             python3 -m piper.http_server -m en_US-lessac-medium

        Of course things get more complicated if things are not in default locations:

        /home/fbacher/Source/venvs/TTS/bin/python3 -m piper.http_server \
            -m en_US-libritts-high \
            --data-dir /home/fbacher/.kodi_data/userdata/addon_data/service.kodi.tts
            /piper/data

        """
        # Already started?
        with (cls.http_server_lock):
            # Is it running?
            try:
                Constants.PIPER_HTTP_SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                MY_LOGGER.debug(f'Could not create directory path for '
                                f'{Constants.PIPER_HTTP_SERVER_LOG}')
            if Constants.PIPER_HTTP_SERVER_PID.exists():
                with Constants.PIPER_HTTP_SERVER_PID.open('rt') as f:
                    pid: str = f.readline()
                    try:
                        pid_int = int(pid)
                        try:
                            if pid_int > 0:
                                os.kill(pid_int, signal.SIGTERM)
                        except OSError:
                            MY_LOGGER.warning(
                                f'Can not kill old Piper http server with pid: '
                                f'{pid_int}')
                    except ValueError:
                        MY_LOGGER.warning(
                            f'Can not read pid for Piper http server: {pid}')
            try:
                Constants.PIPER_HTTP_SERVER_PID.unlink(missing_ok=True)
            except Exception:
                MY_LOGGER.info(F'Could not delete {Constants.PIPER_HTTP_SERVER_PID}')

            if cls.http_server_run_state == cls.HTTP_SERVER_READY:
                return
            if cls.http_server_run_state == cls.HTTP_SERVER_NOT_STARTED:
                cls.http_server_run_state = cls.HTTP_SERVER_STARTING
            elif cls.http_server_run_state != cls.HTTP_SERVER_NOT_STARTED:
                raise RuntimeError(f'Should not get here http_state:'
                                   f' {cls.http_server_run_state}')
            retries: int = 0
            try:
                MY_LOGGER.debug(f'Starting http_server Log: {Constants.PIPER_HTTP_SERVER_LOG}')
                http_server_log = Constants.PIPER_HTTP_SERVER_LOG.open('tw')

                cls._start_builtin_http_server(http_server_log)
                cls.http_server_run_state = cls.HTTP_SERVER_RUNNING
                while retries <= cls.HTTP_RETRY_LIMIT:
                    Monitor.wait_for_abort(0.2)
                    result = cls._get_voice_data_by_http()
                    if result[0] == 0:
                        MY_LOGGER.debug(f'Started http_server after: {retries} retries')
                        cls.http_server_run_state = cls.HTTP_SERVER_READY
                        return
                    retries += 1
                # http_server_log.flush()
                MY_LOGGER.debug(f'FAILED Retries to start http_server: {retries}')
            except AbortException:
                reraise(*sys.exc_info())
            except Exception as e:
                MY_LOGGER.exception('')
                cls.http_server_run_state = cls.HTTP_SERVER_BROKEN
            finally:
                pass

    @classmethod
    def _start_builtin_http_server(cls, http_server_log) -> None:
        """
        Starts the builtin http server to provide services using cached data
        rather than just constantly reinitializing the TTS engine, etc. on every
        voicing.

        Basically, the server is started by:

             python3 -m piper.http_server -m en_US-lessac-medium

        Of course things get more complicated if things are not in default locations:

        /home/fbacher/Source/venvs/TTS/bin/python3 -m piper.http_server \
            -m en_US-libritts-high \
            ---/home/fbacher/.kodi_data/userdata/addon_data/service.kodi.tts
            /piper/data
        """
        env = cls.get_basic_env()
        args: list[str] = cls.get_basic_args()
        args.extend(['-m',
                     Constants.PIPER_HTTP_SERVER_ARG, '-m',
                     Constants.PIPER_HTTP_SERVER_DEFAULT_VG_ARG,
                     '--host', Constants.PIPER_HTTP_SERVER_HOST,
                     '--port', Constants.PIPER_HTTP_SERVER_PORT,
                     '--data-dir', str(Constants.PIPER_DATA_PATH),
                     '--download-dir', str(Constants.PIPER_DATA_PATH)])
        MY_LOGGER.debug(f'args: {args}')
        MY_LOGGER.debug(f'PATH: {env["PATH"]}')
        if Constants.PYTHON_USE_VENV:
            MY_LOGGER.debug(f'VIRTUAL_ENV: {env["VIRTUAL_ENV"]}')
        try:
            platform: str = 'Linux'
            if Constants.PLATFORM_WINDOWS:
                platform = 'Windows'
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'Running command: {platform}: {args}')
            if Constants.PLATFORM_WINDOWS:
                cls._http_process = subprocess.Popen(args,
                                                     stdin=None,
                                                     stdout=subprocess.PIPE,
                                                     stderr=http_server_log,
                                                     shell=False,
                                                     text=True,
                                                     encoding='utf-8', env=env,
                                                     close_fds=True,
                                                     creationflags=subprocess.DETACHED_PROCESS)
            else:
                cls._http_process = subprocess.Popen(args,
                                                     stdin=None,
                                                     stdout=subprocess.PIPE,
                                                     stderr=http_server_log,
                                                     shell=False,
                                                     text=True,
                                                     encoding='utf-8', env=env,
                                                     close_fds=True)
            try:
                MY_LOGGER.debug(f'http server started')
            except AbortException:
                reraise(*sys.exc_info())
            except Exception:
                MY_LOGGER.exception('')
                return
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
            return

    @classmethod
    def run_command(cls, args: List[str],
                    env, cmd_input: str = '',
                    out_file: Path = None) -> Tuple[int, str | List[str]]:
        try:
            output: str = ''
            platform: str = 'Linux'
            if Constants.PLATFORM_WINDOWS:
                platform = 'Windows'
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'Running command: {platform}: {args}\n '
                                  f'cmd_input: {cmd_input}')
            if Constants.PLATFORM_WINDOWS:
                process = subprocess.run(args,
                                         input=cmd_input,
                                         capture_output=True,
                                         shell=False,
                                         text=True,
                                         encoding='utf-8', env=env,
                                         close_fds=True,
                                         creationflags=subprocess.DETACHED_PROCESS)
            else:
                process = subprocess.run(args,
                                         input=cmd_input,
                                         capture_output=True,
                                         shell=False,
                                         text=True,
                                         encoding='utf-8', env=env,
                                         close_fds=True)
            rc: int = -1
            try:
                rc = process.returncode
                if rc != 0:
                    MY_LOGGER.debug(f'piper failed with RC: {process.returncode}')
                else:
                    output = process.stdout
                    MY_LOGGER.debug(f'RC: {process.returncode} ')
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        if out_file is not None and out_file.exists():
                            #  Python 9 hates
                            #  MY_LOGGER.debug_v(f'\noutput: {"\n".join(output)}')
                            x = "\n".join(output)
                            MY_LOGGER.debug_v(f'\noutput: {x}')
            except AbortException:
                reraise(*sys.exc_info())
            except Exception:
                MY_LOGGER.exception('')
                return -2, []
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
            return -2, []
        lines: List[str]
        lines = output.split('\n')
        return rc, output

    @classmethod
    def get_basic_env(cls) -> Dict[str, str]:
        env = os.environ.copy()
        # for key, value in env.items():
        #     MY_LOGGER.debug(f'env: {key} value: {value}\n')
        if Constants.PYTHON_USE_VENV:
            env['PATH'] = (f'{Constants.PYTHON_VENV_ENV["PATH"]}'
                           f'{Constants.ENV_PATH_DELIM}'
                           f'{env["PATH"]}')
            env['VIRTUAL_ENV'] = Constants.PYTHON_VENV_ENV['VIRTUAL_ENV']
        return env

    @classmethod
    def get_basic_args(cls) -> List[str]:
        if Constants.PYTHON_USE_VENV:
            pass
        # args = [f'{Constants.PYTHON_VENV_COMMAND_PATH}']
        args = [f'{Constants.PYTHON_COMMAND_PATH}']
        return args

    @classmethod
    def abort_listener(cls) -> None:
        xbmc.log('About to kill Piper http server. process None: '
                 f'{cls._http_process is None}', xbmc.LOGDEBUG)

        if cls._http_process is not None:
            try:
                xbmc.log('Killing Piper http server', xbmc.LOGDEBUG)
                cls._http_process.kill()
            except Exception:
                xbmc.log(f'Failed to kill Piper http server', xbmc.LOGWARNING)
            cls.http_process = None


class PiperData(ITTSData):

    """
    Simply to pass data from TTS engine to speech_generator or Downloader.

    For Piper, Settings.get_vg returns a string containing each part of the voice:

    vg_id[0] == <language_code>_<territory_code>
    vg_id[1] = <voice_group_name>
    vg_id[2] = <quality>
    vg_id[3] = <vg_id> (only present when there is more than one voice
                   for the voice_group, a string containing an integer)

    The format is
        <language_code>_<territory_code>-<voice_group_name>-<quality>-<voice>
         example: en_US-libritts_r-medium-5

    """

    def __init__(self,
                 speaker_name: str | None = None,
                 ietf_language_code: str | None = None,
                 ietf_territory_code: str | None = None,
                 voice_group_name: str | None = None,
                 voice_quality: str | None = None,
                 speaker_id: str | None = None) -> None:
        super().__init__()

        self._speaker_name: str | None = speaker_name
        self._ietf_language_code: str | None = ietf_language_code  # ex 'en'
        self._ietf_territory_code: str | None = ietf_territory_code  # ex 'us'
        self._voice_group_name: str | None = voice_group_name
        self._voice_quality: int | None = voice_quality
        self._speaker_id: str | None = str(speaker_id)

    @property
    def speaker_name(self) -> str:
        return self._speaker_name

    @property
    def ietf_language_code(self) -> str:
        return self._ietf_language_code

    @property
    def ietf_territory_code(self) -> str:
        return self._ietf_territory_code

    @property
    def voice_group_name(self) -> str:
        return self._voice_group_name

    @property
    def onnx_model_file(self) -> str:
        return f'{self.piper_vg_id}.onnx'

    @property
    def onnx_model_config_file(self) -> str:
        return f'{self.piper_vg_id}.onnx.json'

    @property
    def voice_quality(self) -> str | None:
        return self._voice_quality

    @property
    def speaker_id(self) -> str:
        return str(self._speaker_id)

    @property
    def piper_vg_id(self) -> str:
        """
        Gives the file prefix (without the .onnx or .onnx.json suffix) of
        the piper data files describing this voice & speakers
        """
        piper_vg_id: str = (f'{self._ietf_language_code}_{self._ietf_territory_code}-'
                               f'{self._voice_group_name}-{self._voice_quality}')
        # piper_vg_id: str = self._voice_group_name
        MY_LOGGER.debug(f'piper_vg_id: {piper_vg_id}')
        MY_LOGGER.debug(f'ietf_language_code: {self._ietf_language_code} \n'
                        f'ietf_territory_code: {self._ietf_territory_code} \n'
                        f'voice_group_name: {self._voice_group_name} \n'
                        f'voice_quality: {self._voice_quality}')
        return piper_vg_id

    def __repr__(self) -> str:
        result: str = ''
        result = f'{result} speaker_name: {self._speaker_name}\n'
        result = f'{result} ietf_language_code: {self._ietf_language_code}\n'
        result = f'{result} ietf_territory_code: {self._ietf_territory_code}\n'
        result = f'{result} voice_group_name: {self._voice_group_name}\n'
        result = f'{result} voice_quality = {self._voice_quality}\n'
        result = f'{result} speaker_id: {self._speaker_id}'
        return result


class PiperDownloader(IDownloader):

    service_key: ServiceID = ServiceKey.PIPER_KEY

    def __init__(self,
                 output_type: OutputType = OutputType.USE_FILE,
                 **kwargs) -> None:
        """
        :param lang_code:  2-char language code
        :param country_code:  country code
        :param voice: Name of a voice (engine dependent)
        :param output_type:  How the downloader should handle output
        :param kwargs: Any engine specific arguments
        :return: An integer. Only 0 is success.
        """
        super().__init__()
        self._phrase: Phrase | None = None
        self._tmp_path: Path | None = None
        self._piper_data: PiperData | None = None
        self._fp = None
        self._use_fp_for_tmp: bool = False

    # @property
    # def output_type(self) -> OutputType:
    #     return self._output_type

    @property
    def piper_data(self) -> PiperData:
        return self._piper_data

    def download(self, phrase: Phrase | None = None,
                 **kwargs) -> int:
        """
        Download the given phrase. Note that piper can handle very long phrases, so
        chunking is not used.

        Piper is capable of:
            Downloading from http to a file
            Downloading using python to a file
            Downloading using a 3rd party binary to either a file or a pipe

        :param phrase:
        :param kwargs: For additional arguments specific to binary Piper. Only ONE can
            be specified.
            kwargs['tmp_path']: Download to this file
            kwargs['pipe'] = "copy": Create pipe for generated wave file.
                                     Use write_to_fp to write the contents of the
                                     pipe to another file pointer.
            kwargs['pipe'] = "write": Create pipe for generated wave file. The
                                      caller must call get_pipe to get the handle
                                      to the pipe before piper will close it.
        :return: int return code. Only 0 is success.

        Raises:
        AssertionError – When text is None or empty; when there’s nothing left to speak
        after pre-precessing, tokenizing and cleaning.
        ValueError – When lang_check is True and lang is not supported.
        RuntimeError – When lang_check is True but there is an error loading the
        languages dictionary.
        """
        self._phrase = phrase
        self._tmp_path = kwargs.get('tmp_path', None)
        self._fp = kwargs.get('pipe', None)  # Write to a stream/pipe
        self._use_fp_for_tmp: bool = kwargs.get('use_fp_for_tmp', False)

        locale_id: str = phrase.language  # IETF format
        if phrase.language is None:
            locale_id = LangUtils.kodi_locale
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'orig Phrase locale_id: {locale_id}')
        ietf_lang: langcodes.Language = langcodes.get(locale_id)
        e_voice: EngineVoice = EngineVoiceManager.get_e_voice(PiperDownloader.service_key)
        e_vg: IEngineVoiceGroup | EngineVoiceGroup
        e_vg = EngineVoiceManager.get_vg(e_voice.engine_vg_id,
                                         PiperDownloader.service_key)

        MY_LOGGER.debug(f'Setting PiperData voice_group_name to {e_vg.vg_name}')
        tts_data: PiperData
        tts_data = PiperData(speaker_name='',
                             ietf_language_code=ietf_lang.language,
                             ietf_territory_code=ietf_lang.territory,
                             voice_group_name=e_vg.vg_name,
                             voice_quality=str(e_voice.voice_quality),
                             speaker_id=e_voice.e_voice_id)
        MY_LOGGER.debug(f'piper_data: {tts_data}')
        self._piper_data = tts_data
        MY_LOGGER.debug(f'tmp_path: {self._tmp_path} phrase: {phrase.short_text()}')
        if self._output_type == OutputType.USE_FILE:
            return self.tts(phrase, self._tmp_path)
        return 1  # Not set up for anything but returning a file

    def tts(self, phrase, voiced_path: Path) -> int:
        """
        Calls the third-party Piper TTS engine that runs in a separate Python
        environment to voice text.
        """
        clz = type(self)
        rc: int = -1
        # Ex command:
        # python3 -m piper -m en_US-lessac-medium -f test.wav -- 'This is a test.'
        self._phrase = phrase
        speaker_id: str = self.piper_data.speaker_id
        MY_LOGGER.debug(f'speaker_id: {speaker_id} type: {type(speaker_id)}')
        volume: float = 1.0
        voice_file_name: str = self.piper_data.piper_vg_id
        MY_LOGGER.debug(f'voiced_path: {voiced_path}')
        onnx_model_path: Path = (Constants.PIPER_DATA_PATH /
                                 self.piper_data.onnx_model_file)
        if not onnx_model_path.exists():
            MY_LOGGER.debug(f'onnx_model_path: {onnx_model_path} does NOT exist')
            path: Path
            path = PiperApi.get_onnx_model(self.piper_data.piper_vg_id)
            MY_LOGGER.debug(f'path: {path}')
            if path is None:
                MY_LOGGER.debug(f'Could not download {self.piper_data.onnx_model_file}')

        if PiperApi.default_piper_api == PiperApiType.ANY_API:
            rc = self.tts_by_http(phrase, voice_file_name,
                                  speaker_id, volume, self._tmp_path)
            if rc != 0:
                PiperApi.default_piper_api = PiperApiType.COMPILED_API
        if PiperApi.default_piper_api == PiperApiType.COMPILED_API:
            rc = self.tts_by_native_command(phrase, voice_file_name,
                                            speaker_id, volume,
                                            self._tmp_path)
        if rc != 0:
            PiperApi.default_piper_api = PiperApiType.PYTHON_API
        if PiperApi.default_piper_api == PiperApiType.PYTHON_API:
            rc = self.tts_by_python(phrase, voice_file_name,
                                    speaker_id, volume, self._tmp_path)
        return rc

    def tts_by_http(self, phrase: Phrase, voice_file_name: str,
                    speaker_id: str, volume: float = 1.0,
                    voiced_path: Path = None) -> int:
        """
            :param phrase: Phrase to be voiced
            :param voice_file_name: name of the voice file, or 'model'
            :param speaker_id optional voice id within the model
            :param volume: float volume multiplier
            :param voiced_path: path to output voiced phrase
            :return rc with rc == 0 == success
        """

        """
        The JSON data fields area:
        
            text (required) - text to synthesize
            voice (optional) - name of voice to use; defaults to -m <VOICE>
            voice (optional) - name of voice for multi-voice voices
            vg_id (optional) - id of voice for multi-voice voices; overrides voice
            length_scale (optional) - speaking speed; defaults to 1
            noise_scale (optional) - speaking variability
            noise_w_scale (optional) - phoneme width variability
        """
        if PiperApi.http_server_run_state == PiperApi.HTTP_SERVER_READY:
            MY_LOGGER.debug(f'tts_by_http already running')
        else:
            PiperApi.start_builtin_http_server()
        json_str: str = ('{ '
                         f'"text": "{phrase.text}", '  # No expired check
                         f'"voice": "{voice_file_name}", '
                         f'"speaker_id": {speaker_id} '
                         '}')
        #  'length_scale': Speed, default 1 # Not yet used
        # 'noise_scale':  speaking variability # Not yet used
        # 'noise_w_scale': phoneme width variability # Not yet used

        # curl -X POST -H 'Content-Type: application/json' -d '{ "text": "This is a
        # test." }' -o test.wav localhost:5000

        env = PiperApi.get_basic_env()
        args = [str(Constants.CURL_PATH),
                '-X',
                'POST',
                '-H',
                'Content-Type: application/json',
                '-d',
                f'{json_str}',
                '-o',
                f'{voiced_path}',
                f'{Constants.PIPER_HTTP_SERVER_HOST}:'
                f'{Constants.PIPER_HTTP_SERVER_PORT}'
                ]
        MY_LOGGER.debug(f'Generating voice for {phrase.text} voice_path: {voiced_path}')
        self.delete_path_if_exists(voiced_path, "before generating from http")
        rc, _ = PiperApi.run_command(args, env)
        if rc != 0:
            self.delete_path_if_exists(voiced_path, "after http generation failed")
        else:
            MY_LOGGER.debug(f'Voice generation by http success')
        return rc

    def delete_path_if_exists(self, path: Path, msg: str) -> None:
        try:
            if path.exists():
                MY_LOGGER.debug(f'{path} exists {msg}, deleting')
                path.unlink(missing_ok=True)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception(f'Could not delete {path}.')

    def tts_by_native_command(self, phrase: Phrase, voice_file_name: str,
                              speaker_id: str, volume: float = 1.0,
                              voiced_path: Path = None) -> int:
        """
           Calls the third-party Piper TTS engine that runs in a separate Python
           environment to voice text.

           This engine is faster than the http server engine but faster than the
           pure-python based engine.

           :param phrase: Phrase to be voiced
           :param voice_file_name: name of the voice file, or 'model'
           :param speaker_id: optional vg_id within model
           :param volume: float volume multiplier
           :param voiced_path: path to output voiced phrase
           """
        """
        Command options:
        -h        --help              show this message and exit
        -m  FILE  --model       FILE  path to onnx model file
        -c  FILE  --download      FILE  path to model download file (default: model 
        path + .json)
        -f  FILE  --output_file FILE  path to output WAV file ('-' for stdout)
        -d  DIR   --output_dir  DIR   path to output directory (default: cwd)
        --output_raw                  output raw audio to stdout as it becomes available
        -s  NUM   --voice     NUM   id of voice (default: 0)
        --noise_scale           NUM   generator noise (default: 0.667)
        --length_scale          NUM   phoneme length (default: 1.0)
        --noise_w               NUM   phoneme width noise (default: 0.8)
        --sentence_silence      NUM   seconds of silence after each sentence (default: 
        0.2)
        --espeak_data           DIR   path to espeak-ng data directory
        --tashkeel_model        FILE  path to libtashkeel onnx model (arabic)
        --json-input                  stdin input is lines of JSON instead of plain text
        --debug                       print DEBUG messages to the console

The following example writes two sentences with different speakers to different files:

READ FROM STDIN, not cmd line arg!!!
{ "text": "First voice.", "vg_id": 0, "output_file": "/tmp/speaker_0.wav" }
{ "text": "Second voice.", "vg_id": 1, "output_file": "/tmp/speaker_1.wav" }

        """
        onnx_model_path: Path = (Constants.PIPER_DATA_PATH /
                                 self.piper_data.onnx_model_file)
        onnx_model_config_path: Path = (Constants.PIPER_DATA_PATH /
                                        self.piper_data.onnx_model_config_file)
        MY_LOGGER.debug(f'tts_by_native_command voiced_path: {voiced_path}')
        env = PiperApi.get_basic_env()
        json_str: str = (f'{{ "text": "{phrase.text}", "vg_id": {speaker_id}, '
                         f' "output_file": "{voiced_path}" }}')
        args: list[str] = PiperApi.get_basic_args()
        args.extend([str(Constants.PIPER_BINARY_PATH),
                     '--model',
                     f'{onnx_model_path}',  # .onnx
                     '--download',
                     f'{onnx_model_config_path}',  # .onnx.json
                     '--json-input'
                   ])
        MY_LOGGER.debug(f'Generating voice for {phrase.text}')
        self.delete_path_if_exists(voiced_path, "before native generation")
        rc, _ = PiperApi.run_command(args, env, cmd_input=json_str)
        if rc != 0:
            self.delete_path_if_exists(voiced_path, "after native generation failed")
        MY_LOGGER.debug(f'{voiced_path} exists: {voiced_path.exists()}')
        return rc

    def tts_by_python(self, phrase: Phrase, voice_file_name: str, speaker_id: str,
                      volume: float = 1.0, voiced_path: Path = None) -> int:
        """
        Calls the third-party Piper TTS engine that runs in a separate Python
        environment to voice text.

        This engine is slower than the native engine as well as the engine that
        uses http.

        :param phrase: Phrase to be voiced
        :param voice_file_name: name of the voice file, or 'model'
        :param speaker_id: optional voice id within the model
        :param volume: float volume multiplier
        :param voiced_path: path to output voiced phrase
        """
        """
        -h, --help            show this help message and exit
      -m MODEL, --model MODEL
                            Path to Onnx model file
      -c CONFIG, --download CONFIG
                            Path to model download file
      -i INPUT_FILE, --input-file INPUT_FILE, --input_file INPUT_FILE
                            Paths to input text files
      -f OUTPUT_FILE, --output-file OUTPUT_FILE, --output_file OUTPUT_FILE
                            Path to output WAV file (default: stdout)
      -d OUTPUT_DIR, --output-dir OUTPUT_DIR, --output_dir OUTPUT_DIR
                            Path to output directory (default: cwd)
      --output-raw, --output_raw
                            Stream raw audio to stdout
      -s SPEAKER, --voice SPEAKER
                            Id of voice (default: 0)
      --length-scale LENGTH_SCALE, --length_scale LENGTH_SCALE
                            Phoneme length
      --noise-scale NOISE_SCALE, --noise_scale NOISE_SCALE
                            Generator noise
      --noise-w-scale NOISE_W_SCALE, --noise_w_scale NOISE_W_SCALE, --noise-w 
      NOISE_W_SCALE, --noise_w NOISE_W_SCALE
                            Phoneme width noise
      --cuda                Use GPU
      --sentence-silence SENTENCE_SILENCE, --sentence_silence SENTENCE_SILENCE
                            Seconds of silence after each sentence
      --volume VOLUME       Volume multiplier (default: 1.0)
      --no-normalize        Don't normalize audio
      --data-dir DATA_DIR, --data-dir DATA_DIR
                            Data directory to check for voice models (default:
                            current directory)
      --debug               Print DEBUG messages to console
    """
        env = PiperApi.get_basic_env()
        args: list[str] = PiperApi.get_basic_args()
        args = [
            '-m',
            'piper',
            '-m',
            f'{voice_file_name}',
            '--voice',
            f'{speaker_id}',
            '--output-file',
            f'{voiced_path}',
            '--volume',
            f'{volume}',
            '--data-dir',
            f'{Constants.PIPER_DATA_PATH}',
            '--',
            f'{phrase.text}'
        ]
        # TODO: Revisit the wisdom of passing text by argument instead of file.
        #       text files currently only saved for cached files. No provision
        #       for using them with non-cached nor with chunked cached files.
        #       Risk is that command line buffer could get overwhelmed, or that
        #       special characters in string could screw things up.

        process: subprocess.CompletedProcess | None = None
        MY_LOGGER.debug(f'Generating voice for {phrase.text}')
        self.delete_path_if_exists(voiced_path, "before generating from python")
        rc, _ = PiperApi.run_command(args, env)
        if rc != 0:
            self.delete_path_if_exists(voiced_path, "after python generation failed")
        MY_LOGGER.debug(f'tts_by_python rc: {rc}')
        return rc

    def write_to_fp(self, fp):
        """
        Causes gtts to write downloaded data to the given file
        :param fp:
        :return:
        """
        pass

    @property
    def supports_chunks(self) -> bool:
        return False

    @property
    def creates_tmp(self) -> bool:
        return True


Monitor.register_abort_listener(listener = PiperApi.abort_listener,
                                name='piper_abort_listener', thread=None)
