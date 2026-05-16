# coding=utf-8
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
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
from common.file_utils import FileUtils, FindFiles
from common.logger import *
from common.minimal_monitor import MinimalMonitor
from common.monitor import Monitor
from common.phrases import Phrase
from backends.settings.service_types import (QualityType, ServiceID,
                                             ServiceKey)
from common.settings import Settings

MY_LOGGER = BasicLogger.get_logger(__name__)

"""
    Most TTS engines support specific voices. PiperTTS provides models which 
    produce a group of closely related voices (although they sound significantly
    different). Each model file defines a Voice Group. A Voice Group can have 
    one or even a thousand Voices. There is overhead initializing the TTS engine
    whenever a model is changed, therefore when multiple voices are needed, it 
    is advantageous if they come from the same model.
    
    TThe naming convention of the model identifies the locale, name and quality,
    An example: en_US-lessac-medium. The format is:
       <language_code>_<territory_code>-<voice_group_name>-<quality>. Individual
    voices and other information comes from a model's .json file. In particular,
    the supported voices (or speakers) are listed.

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
"""


# PiperSpeakerTuple contains the information from parsing the model's json files
# in order create data structures used by Kodi TTS.


class PiperModel:
    """
    Describes a Model in a form more convenient for our use
    """
    current_locale: str = LangUtils.kodi_locale
    current_language: str = LangUtils.kodi_lang
    current_ietf_tag: str = current_language.replace('_', '-').lower()
    kodi_lang: langcodes.Language = langcodes.Language.get(current_ietf_tag)

    def __init__(self, model_name: str, model_data: dict[str, Any]) -> None:
        clz = type(self)
        # model_name: en_US-libritts-high
        fields: List[str] = model_name.split('-')
        ietf_tag: str = fields[0].replace('_', '-').lower()
        model_path: Path = (Constants.PIPER_DATA_PATH / model_name).with_suffix('.onnx')
        try:
            if model_path.exists() and model_path.is_file():
                self._model_present = True
            else:
                self._model_present = False
        except Exception:
            MY_LOGGER.exception()
            self._model_present = False

        self._model_name: str = model_name
        self._language: langcodes.Language = langcodes.Language.get(ietf_tag)
        MY_LOGGER.debug(f'vg_id: {model_name} label: {fields[1]}')
        self._vg_id: str = model_name
        self._vg_label: str = fields[1]
        self._voice_id_map: dict[str, int] = {}
        self._quality: QualityType = QualityType(fields[2])
        self._locale_distance: int = langcodes.tag_distance(desired=clz.current_ietf_tag,
                                                            supported=ietf_tag)
        if model_data is not None:
            tmp = model_data.get('speaker_id_map',
                                 None)  # Is empty or None for single voice groups
            tmp: dict[str, int]
            if tmp is None or len(tmp) == 0:  # Add Voice 0, which is named same as the voice group.
                tmp = {self._vg_label: 0}
            self._voice_id_map = tmp

    @property
    def language(self) -> langcodes.Language:
        return self._language

    @property
    def model_present(self) -> bool:
        """
        Currently, Piper is the only engine that has downloadable voice models.
        The Configuration code and UI use this to 1) avoid using a model that is
        not present 2) trigger a download of the model 3) inform the UI so that
        user can choose whether to download or not
        """
        return self._model_present

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def vg_id(self) -> str:
        return self._vg_id

    @property
    def vg_label(self) -> str:
        return self._vg_label

    @property
    def voice_id_map(self) -> dict[str, int]:
        return self._voice_id_map

    @property
    def quality(self) -> QualityType:
        return self._quality

    @property
    def locale_distance(self) -> int:
        return self._locale_distance

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            if self._locale_distance > other._locale_distance:
                return True
            if self._locale_distance == other._locale_distance:
                return self._quality <= other._quality
            return False
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            if self._locale_distance > other._locale_distance:
                return True
            if self._locale_distance == other._locale_distance:
                return self._quality < other._quality
            return False
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            if self._locale_distance < other._locale_distance:
                return True
            if self._locale_distance == other._locale_distance:
                return self._quality >= other._quality
            return False
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            if self._locale_distance < other._locale_distance:
                return True
            if self._locale_distance == other._locale_distance:
                return self._quality > other._quality
            return False
        return NotImplemented


class PiperApi:
    """
    Provides functions for integrating Piper into Kodi TTS by utilizing Piper's API.
    These function identify the models, voice groups and voices that are available
    for installation, as well as the ability to install, remove produce TTS.
    """
    #  REPLACE WITH SETTINGS

    PIPER_TTS_MAX_CHARS = 10000
    DOWNLOAD_MISSING_MODEL: bool = True
    http_server_lock: threading.RLock = threading.RLock()

    HTTP_SERVER_NOT_STARTED: Final[int] = 0
    HTTP_SERVER_STARTING: Final[int] = 1
    HTTP_SERVER_READY: Final[int] = 2
    HTTP_SERVER_BROKEN: Final[int] = 3

    http_server_state: int = HTTP_SERVER_NOT_STARTED
    _use_native_piper_command: bool = True
    _use_python_piper_command: bool = True

    HTTP_RETRY_DELAY_SECONDS: Final[float] = 0.2
    HTTP_RETRY_LIMIT_SECONDS: Final[float] = 5.0
    HTTP_RETRY_LIMIT: Final[int] = int(
        HTTP_RETRY_LIMIT_SECONDS / HTTP_RETRY_DELAY_SECONDS) + 1

    _http_process: subprocess.Popen | None = None
    _initialized: bool = False
    _native_piper_cmd_initialized: bool = False
    _piper_data_checked: bool = False
    _best_model: str = None

    @classmethod
    def get_tts_voice_details(cls,
                              current_language: str,
                              include_uninstalled: bool,
                              keep_definitions: bool) -> List[PiperModel]:
        """
        Discover Piper's Voice Groups and Voices for the current language. For
        known models which are not downloaded, only the model's name is returned
        along with an empty Dictionary instead of any speaker or voice information.
        This is enough information to let the user know about the model. The user can
        later choose to download it, see the details and hear the voice.

        :param current_language: Only include models that are the same language as Kodi's
                                ('en')
        :param include_uninstalled: If True, then include information about any
                                    uninstalled models.
        :return: List of PiperModel which describes each Voice Group and Voice
        """
        MY_LOGGER.debug(f'In get_tts_voice_details')
        # Get information about all models, possibly including uninstalled models.
        # The returned dictionary is indexed by the name of the model.
        # The values are from each model's .json (.onnx.json) file, or empty if
        # the model is not installed.

        rc: int
        model_data: dict[str, Any]
        rc, model_data = cls.get_model_info(models=[],  # All models
                                            include_uninstalled=include_uninstalled)
        MY_LOGGER.debug(f'rc: {rc} keys: {list(model_data.keys())}')
        if rc != 0:
            return []

        piper_models: List[PiperModel] = []
        for model_name, model_details in model_data.items():
            model_name: str
            model_details: dict[str, Any]
            MY_LOGGER.debug(f'model: {model_name}')
            if len(model_name) == 0:
                continue
            json_data: Dict[str, Any]
            json_data = cls.download_model(model_name,
                                           keep_definition=keep_definitions)
            piper_models.append(PiperModel(model_name=model_name,
                                           model_data=json_data))
        return piper_models

    @classmethod
    def get_model_info(cls,
                       models: List[str],
                       include_uninstalled: bool = False) -> (
                                                Tuple[int, dict[str, dict[str, Any]]]):
        """
        For each model, returns the contents of model.onnx.json, or an
        empty dict, if the model is not in Constants.PIPER_DATA_PATH.

        :param models: Models to process. If empty, then all models for the
                       current language are returned including those not
                       downloaded.
        :param include_uninstalled: if True, then list the names of models that have not
                                    been downloaded
        :return: dict[model, dict_from_models_json]
        """
        rc: int = 0
        result_info: dict[str, dict[str, Any]] = {}
        use_http: bool = cls.use_http()

        if len(models) == 0:
            models: List[str] = cls.list_all_models()
        if use_http:
            # Verify that http server started.

            # start http server with a model that has both .json and .onnx files

            # Returns info for all downloaded models at once
            rc, result_info = cls._get_local_model_info_by_http()
            if include_uninstalled:
                # Add dummy entries for uninstalled models.
                for model in models:
                    if result_info.get(model) is None:
                        result_info[model] = {}
        else:
            for model in models:
                model: str
                json_data: Dict[str, Any]
                json_data = cls.get_local_model_info(model)
                result_info[model] = json_data
                #  MY_LOGGER.debug(f'model: {model} json_data: {json_data}')
        return rc, result_info

    @classmethod
    def get_local_model_info(cls, model: str) -> Dict[str, str]:
        """
        Gets the model information by processing the model as a json file.

        :param model: model to process
        :return: model information, or, if file not found, an empty dict.
        """
        json_file: Path = Constants.PIPER_DATA_PATH / f'{model}.onnx.json'
        json_data: Dict[str, Any] = {}
        try:
            if json_file.is_file():
                with open(json_file) as f:
                    json_data: Dict[str, Any] = json.load(f)
        except Exception:
            MY_LOGGER.exception()
        return json_data

    @classmethod
    def get_onnx_model(cls, model_name: str) -> Path | None:
        """
        Reads given model_name.onnx.json (downloading as necessary) and returns
        the path to it. When downloaded, the model_name.onnx.json file will be
        saved in Kodi TTS userdata space. However, any downloaded model_name.onnx
        file will be deleted.

        :param model_name: base name of the model_name.onnx.json file to download

        :return Path to onnx_model_file if successful, None, otherwise

        TODO: Need mechanism to detect when file changes and needs updating.
        """
        MY_LOGGER.debug(f'get_onnx_model: {model_name}')

        _ = cls.download_model(model_name, keep_definition=False)
        download_dir: Path = Path(f'{Constants.PIPER_DATA_PATH}')
        onnx_model_path: Path = download_dir / f'{model_name}.onnx.json'
        if onnx_model_path.exists():
            return onnx_model_path
        return None

    @classmethod
    def list_all_models(cls) -> List[str]:
        """
        List all models for Kodi's current language from piper's central model repository.

        Uses the piper command, since the piper http_server can only give information
        for local models.

        :return: The names of the models for the current language. An empty list
                 is a sign of an error.
        """
        all_models: List[str] = []
        found_models: List[str] = []
        try:
            env = cls.get_basic_env()
            args: list[str] = cls.get_basic_args()
            args.extend(['-m',
                         Constants.PIPER_DOWNLOAD_VOICES,
                         '--data-dir', f'{Constants.PIPER_DATA_PATH}'])
            MY_LOGGER.debug(f'About to run args: {args}')
            models_str: str
            rc, models_str = PiperApi.run_command(args, env)
            all_models = models_str.split('\n')
            if all_models[-1] == '':
                del all_models[-1]
            #  MY_LOGGER.debug(f'all_models: # {len(all_models)} {"\n".join(all_models)}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')

        try:
            current_locale: str = LangUtils.kodi_locale
            current_language: str = LangUtils.kodi_lang
            current_ietf_tag: str = current_language.replace('_', '-').lower()
            kodi_lang: langcodes.Language = langcodes.Language.get(current_ietf_tag)
            # MY_LOGGER.debug(f'current_ietf_tag: {current_ietf_tag} kodi_lang: {kodi_lang}')
            for model in all_models:
                fields: List[str] = model.split('-')
                lang_territory_code: str = fields[0]
                model_locale: str = langcodes.Language.get(lang_territory_code).to_tag()
                model_language: str = langcodes.Language.get(model_locale).language
                #  MY_LOGGER.debug(
                #     f'kodi_language: {current_language} model_langauge: {model_language}')
                if model_language == current_language:
                    #  MY_LOGGER.debug(f'Adding to found_models: {model_language} {model}')
                    found_models.append(model)
                # else:
                #     MY_LOGGER.debug(f'model: {model} field: {fields[0]} model_locale: {model_locale} '
                #                     f'model_lang: {langcodes.Language.get(model_locale).language}')

        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
        return found_models

    @classmethod
    def download_model(cls, model: str,
                       keep_definition: bool = False) -> Dict[str, Any]:
        """
        Downloads the model_json (*.onnx.json) and model_name (*.onnx)
        files, as needed. Note that there is currently no way to download
        the .json or .onnx file alone.

        :param model: model to get
        :param keep_definition: When True, keep the .onnx files after
                                downloading, otherwise, just keeps the .onnx.json files.

        :return: the contents of the model_json file (.onnx.json) as a Dictionary
        """
        MY_LOGGER.debug(f'model: {model}')
        results: Dict[str, Any] = {}
        download_dir: Path = Path(f'{Constants.PIPER_DATA_PATH}')
        model_data: Path = download_dir / f'{model}.onnx'
        model_json: Path = download_dir / f'{model}.onnx.json'
        MY_LOGGER.debug(f'model: {model_data}\n'
                        f'model_json: {model_json}')
        MY_LOGGER.debug(f'model_json exists:'
                        f' {model_json.exists()}\n'
                        f'keep_definition: {keep_definition}\n'
                        f'model_data exists: {model_data.exists()}')
        model_json_exists_on_entry: bool = model_json.exists()
        model_data_exists_on_entry: bool = model_data.exists()
        if (not model_json.exists() or
                (keep_definition and not model_data.exists())):
            env = cls.get_basic_env()
            args: list[str] = cls.get_basic_args()
            args.extend(['-m',
                         Constants.PIPER_DOWNLOAD_VOICES, f'{model}',
                         '--data-dir', f'{Constants.PIPER_DATA_PATH}'])
            MY_LOGGER.debug(f'About to run args: {args}')
            rc, _ = PiperApi.run_command(args, env)
            MY_LOGGER.debug(f'rc: {rc}')
            if not (model_data.exists() or model_json.exists()):
                MY_LOGGER.debug(f'Download failed for : {model_data} and '
                                f'{model_json}')
                return {}
        try:
            with model_json.open(mode='r') as f:
                results = json.load(f)

        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
        # Always keep the.json file
        if not (model_data_exists_on_entry or keep_definition) and model_data.exists():
            model_data.unlink(missing_ok=True)

        return results

    @classmethod
    def get_vg_names(cls) -> Tuple[int, List[str]]:
        """
        Queries the piper engine for list of supported voice names.

        :return: Tuple[rc, list of supported voice names]
        """
        result: Tuple[int, List[str]] = -1, []
        try:
            rc, tmp = cls.get_model_info(models=[])
            #  MY_LOGGER.debug(f'rc: {rc} #vg_names: {len(tmp)}\n tmp: {tmp}')
            if rc == 0:
                vg_names: List[str] = list(tmp.keys())
                return rc, vg_names
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
        return result

    @classmethod
    def use_http(cls) -> bool:
        with (cls.http_server_lock):
            if not cls._initialized:
                cls.init_piper_data()
                model: str = cls.minimally_populate_piper_data()
                MY_LOGGER.debug(f'Calling start_builtin_http_server')
                cls.start_builtin_http_server(model=model)
        return cls.http_server_state == cls.HTTP_SERVER_READY

    @classmethod
    def tts_by_native_command(cls, text: str, model: str,
                              voice_id: str,
                              voiced_path: Path = None,
                              volume: float = 1.0) -> int:
        """
           Runs the native Piper command to voice speech. The command is significantly
           faster than the pure python version. The http piper essentially runs
           this native Piper command, but is faster since the process is long-lived
           and the cost of reinitializing the model is avoided.

           :param text: Text to be voiced
           :param model: name of the voice file, or 'model'
           :param voice_id: optional vg_id within model
           :param voiced_path: path to output voiced text. CAN BE NONE OR os.devnull
           :param volume: float volume multiplier
           """
        """
        Command options:
   -h        --help              show this message and exit
   -m  FILE  --model       FILE  path to onnx model file
   -c  FILE  --config      FILE  path to model config file (default: model path + .json)
   -f  FILE  --output_file FILE  path to output WAV file ('-' for stdout)
   -d  DIR   --output_dir  DIR   path to output directory (default: cwd)
   --output_raw                  output raw audio to stdout as it becomes available
   -s  NUM   --speaker     NUM   id of speaker (default: 0)
   --noise_scale           NUM   generator noise (default: 0.667)
   --length_scale          NUM   phoneme length (default: 1.0)
   --noise_w               NUM   phoneme width noise (default: 0.8)
   --sentence_silence      NUM   seconds of silence after each sentence (default: 0.2)
   --espeak_data           DIR   path to espeak-ng data directory
   --tashkeel_model        FILE  path to libtashkeel onnx model (arabic)
   --json-input                  stdin input is lines of JSON instead of plain text
   --debug                       print DEBUG messages to the console


The following example writes two sentences with different speakers to different files:

READ FROM STDIN, not cmd line arg!!!
{ "text": "First voice.", "vg_id": 0, "output_file": "/tmp/speaker_0.wav" }
{ "text": "Second voice.", "vg_id": 1, "output_file": "/tmp/speaker_1.wav" }

        """
        if voiced_path is None:
            raise ValueError('Missing voice_path')
        MY_LOGGER.debug(f'tts_by_native_command voiced_path: {voiced_path}')
        model_path: Path = cls.get_model_path(model)
        config_path: Path = model_path.with_suffix('.onnx.json')

        env = PiperApi.get_basic_env()
        args: list[str] = [
                     str(Constants.PIPER_BINARY_PATH),
                     '--model',
                     f'{model_path}',  # .onnx
                     '--config',
                     f'{config_path}',
                     '--data-dir',
                     f'{Constants.PIPER_DATA_PATH}',
                     '--speaker',
                     f'{voice_id}',
                     '--output-file',
                     f'{voiced_path}',
                     '--debug'
                     ]
        MY_LOGGER.debug(f'Generating voice for {text}')
        FileUtils.delete_path_if_exists(voiced_path, "before native generation")
        rc, _ = PiperApi.run_command(args, env, cmd_input=text)
        if rc != 0:
            FileUtils.delete_path_if_exists(voiced_path, "after native generation failed")
        MY_LOGGER.debug(f'{voiced_path} exists: {voiced_path.exists()}')
        return rc

    @classmethod
    def tts_by_python(cls, text: str, model: str, voice_id: str,
                      voiced_path: Path, volume: float = 1.0) -> int:
        """
        Calls the Piper TTS engine that runs in a separate Python
        environment to voice text.

        This engine is slower than the native engine as well as the engine that
        uses http.

        :param text: Text to be voiced
        :param model: base name of model
        :param voice_id: optional voice id within the model
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
        args.extend([
            '-m',
            'piper',
            '-m',
            f'{model}',
            '--speaker',
            f'{voice_id}',
            '--output-file',
            f'{voiced_path}',
            '--volume',
            f'{volume}',
            '--data-dir',
            f'{Constants.PIPER_DATA_PATH}',
            f'--debug',
            '--',
            f'{text}'
        ])
        # TODO: Revisit the wisdom of passing text by argument instead of file.
        #       text files currently only saved for cached files. No provision
        #       for using them with non-cached nor with chunked cached files.
        #       Risk is that command line buffer could get overwhelmed, or that
        #       special characters in string could screw things up.

        process: subprocess.CompletedProcess | None = None
        MY_LOGGER.debug(f'Generating voice for {text}')
        FileUtils.delete_path_if_exists(voiced_path, "before generating from python")
        rc, _ = PiperApi.run_command(args, env)
        if rc != 0:
            FileUtils.delete_path_if_exists(voiced_path, "after python generation failed")
        MY_LOGGER.debug(f'tts_by_python rc: {rc}')
        return rc

    @classmethod
    def tts(cls, text: str, voiced_path: Path, model: str, voice_id: str) -> int:
        """
        Calls the Piper TTS engine that runs in a separate Python environment to
        voice text.

        :param text: Text to voice
        :param voiced_path: Output path for voiced text
        :param model: base name of model
        :param voice_id: id of Voice to use
        """
        rc: int = -1
        # Ex command:
        # python3 -m piper -m en_US-lessac-medium -f test.wav -- 'This is a test.'
        MY_LOGGER.debug(f'model: {model}')
        volume: float = 1.0
        if cls.use_http():
            rc = cls.tts_by_http(text, model, voice_id, voiced_path, volume)
            if rc == 0:
                return rc
        if cls.use_native_piper_command():
            rc = cls.tts_by_native_command(text, model, voice_id, voiced_path, volume)
            if rc == 0:
                return rc
        rc = cls.tts_by_python(text, model, voice_id, voiced_path, volume)
        return rc

    @classmethod
    def tts_by_http(cls, text: str, model: str, voice_id: str, voiced_path: Path,
                    volume: float = 1.0) -> int:
        """
        Uses the built-in http_server to generate speech. Faster due to the
        Voice Model being persistent in memory until changed.

            :param text: Text to be voiced
            :param model: base name of model
            :param voice_id optional voice id within the model
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
        if PiperApi.http_server_state == PiperApi.HTTP_SERVER_READY:
            MY_LOGGER.debug(f'tts_by_http already running')
        elif PiperApi.http_server_state == PiperApi.HTTP_SERVER_BROKEN:
            MY_LOGGER.debug(f'tts_by_http broken')
            return -1
        else:
            if PiperApi.http_server_state == PiperApi.HTTP_SERVER_BROKEN:
                MY_LOGGER.debug(f'tts_by_http broken')
                return -1
        json_str: str = ('{ '
                         f'"text": "{text}", '  # No expired check
                         f'"voice": "{model}", '
                         f'"speaker_id": {voice_id} '  # or "speaker"
                         '}')
        #  'length_scale': Speed, default 1 # Not yet used
        # 'noise_scale':  speaking variability # Not yet used
        # 'noise_w_scale': phoneme width variability # Not yet used

        # curl -X POST -H 'Content-Type: application/json' -d '{ "text": "This is a
        # test.", "voice": "model_name"}' -o test.wav localhost:5000

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
        MY_LOGGER.debug(f'Generating voice for {text} voice_path: {voiced_path}')
        FileUtils.delete_path_if_exists(voiced_path, "before generating from http")
        rc, _ = PiperApi.run_command(args, env)
        if rc != 0:
            FileUtils.delete_path_if_exists(voiced_path, "after http generation failed")
        else:
            MY_LOGGER.debug(f'Voice generation by http success')
        return rc

    @classmethod
    def use_native_piper_command(cls) -> bool:
        model: str = ''
        if not cls._initialized:
            cls.init_piper_data()

        if not cls._native_piper_cmd_initialized:
            model: str = cls.minimally_populate_piper_data()
            cls._use_native_piper_command = cls.test_native_tts(model=model)
            MY_LOGGER.debug(f'native tts piper command enabled: '
                            f'{cls._use_native_piper_command}')
            cls._native_piper_cmd_initialized = True
        return cls._use_native_piper_command

    @classmethod
    def test_http_server(cls) -> bool:
        """
        Verifies whether the http server is working. Since the server runs in a
        separate process, it is possible that it is alive between Kodi restarts.

        :return: True if the server is functioning, otherwise, False.
        """
        rc: int
        rc, _ = cls._get_local_model_info_by_http()
        return rc == 0

    @classmethod
    def test_native_tts(cls, model: str) -> bool:
        rc: int = cls.tts_by_native_command('Test', model=model, voice_id='0',
                                            voiced_path=Path(os.devnull))
        return rc == 0

    @classmethod
    def init_piper_data(cls) -> None:
        """
        Remove any corrupted voice data
        Make sure there is at least one onnx voice data file so that Piper TTS
        will work. User can choose more voices later.

        NOTE: Can not be run prior to initialzation performed by PiperSettings.
        """

        MY_LOGGER.debug(f'In init_piper_data state: {cls.http_server_state}')
        if cls._initialized:
            return

        cls._intialized = True
        with cls.http_server_lock:
            if cls.http_server_state in (  # PiperApi.HTTP_SERVER_NOT_STARTED,
                    # PiperApi.HTTP_SERVER_STARTING,
                    PiperApi.HTTP_SERVER_BROKEN,
                    PiperApi.HTTP_SERVER_READY):
                MY_LOGGER.debug(f'http_server_state: {cls.http_server_state}')
                return
            MY_LOGGER.debug(f'Calling create_piper_data_as_needed')
            cls.create_piper_data_as_needed()
            MY_LOGGER.debug(f'Exiting init_piper_data')

    @classmethod
    def get_model_path(cls, model: str) -> Path:
        model_path: Path = (Constants.PIPER_DATA_PATH / model).with_suffix('.onnx')
        if cls.DOWNLOAD_MISSING_MODEL and not model_path.exists():
            MY_LOGGER.debug(f'Downloading: {model_path}')
            if model_path is None:
                raise ValueError(f'Could not download {model_path}')
        return model_path

    @classmethod
    def create_piper_data_as_needed(cls):
        """
        Simply makes sure that the Constants.PIPER_DATA_PATH exist, creating it,
        as needed.

        """
        download_dir: Path = Path(f'{Constants.PIPER_DATA_PATH}')
        if not download_dir.exists():
            MY_LOGGER.debug(f'Creating {download_dir} directory')
            download_dir.mkdir(exist_ok=True, parents=True)

    @classmethod
    def minimally_populate_piper_data(cls) -> str:
        """
        Called after creating and/or removing voice models from piper's model directory.
        Need to make sure that there is at least one model present for Kodi's current
        language, downloading if needed.

        Also, in the case where a model is/has been freshly downloaded, then it is
        very likely that the model/voice_id has not yet been committed to settings.xml
        (long story). For this reason, when the model name can not be found in Settings,
        the model name from the model directory is returned here so that the http_server
        can get started. The model can change in the future, but settings will be able
        to find it then.

        :return: The name of model chosen

        """
        if cls._piper_data_checked:
            return cls._best_model

        MY_LOGGER.debug(f'In minimally_populate_piper_data')
        valid_onnx_path: Path
        files_to_replace: list[Path]
        models_present: list[str]
        current_language: str = LangUtils.kodi_lang
        current_ietf_tag: str = current_language.replace('_', '-').lower()
        kodi_lang: langcodes.Language = langcodes.Language.get(current_ietf_tag)
        result = cls.check_piper_data(current_language)
        valid_onnx_path, files_to_replace, models_present = result
        MY_LOGGER.debug(f'valid_onnx_path: {valid_onnx_path} '
                        f'files_to_replace: {files_to_replace} '
                        f'models_present: {models_present}')
        current_voice_id: str | None = Settings.get_voice_id(
            engine_key=ServiceKey.PIPER_KEY)
        MY_LOGGER.debug(f'current_voice_id: {current_voice_id}')
        current_model: str | None = None
        download_required: bool = False
        if current_voice_id is not None:
            current_model = current_voice_id.split('|')[1]

        models: list[str]
        best_model: str = ''

        MY_LOGGER.debug(f'current_model: {current_model}'
                        f' models_present: {models_present}')
        try:
            if current_model is None and valid_onnx_path is None:
                # Pick the first onnx file for this language
                # Can NOT use the http version since it must refer to an onnx file in
                # the data directory. Use the command version instead.

                download_required = True
                models = cls.list_all_models()
                MY_LOGGER.debug(f'models: {models}')
                if len(models) == 0:
                    MY_LOGGER.debug(f'No models found in {current_language}')
            else:
                models = models_present
                if current_model is not None and current_model in models_present:
                    MY_LOGGER.debug(f'Found current_model: {current_model}')
                    return current_model

                best_quality: QualityType = QualityType.UNKNOWN
                closest_match: int = 10000

                # This finds the model that's locale is the closest match to
                # Kodi's locale.
                # Of the closest locale match, the best quality voice is found.
                # HINT- this ain't perfect, but probably good 'nuf
                closest_models: List[str] = []
                for model in models:
                    fields: List[str] = model.split('-')
                    MY_LOGGER.debug(f'model: {model} fields: {fields}')
                    ietf_tag: str = fields[0].replace('_', '-').lower()
                    lang: langcodes.Language = langcodes.Language.get(ietf_tag)
                    # Major language ('en') must match
                    if lang.language != kodi_lang.language:
                        continue

                    current_match: int
                    current_match = langcodes.tag_distance(desired=current_ietf_tag,
                                                           supported=ietf_tag)
                    if current_match < closest_match:
                        closest_match = current_match
                        closest_models.clear()
                    if current_match == closest_match:
                        closest_models.append(model)

                # Quality based on piper's ranking: x_low - High
                MY_LOGGER.debug(f'closest_models: {closest_models}')
                for model in closest_models:
                    MY_LOGGER.debug(f'model: {model}')
                    fields: List[str] = model.split('-')
                    quality: QualityType = QualityType(fields[2])
                    if quality < best_quality:
                        best_quality = quality
                        best_model = model

                # Download the 'best' voice file so that Piper can work
                if download_required and best_model != '':
                    cls.download_model(best_model,
                                       keep_definition=True)
                MY_LOGGER.debug(f'best_model: {best_model}')
                Settings.set_voice_id(f'engine.piper.id|{best_model}|0',
                                      engine_key=ServiceKey.PIPER_KEY)
        finally:
            cls._initialized = True
            cls._piper_data_checked = True
            cls._best_model = best_model
        return best_model

    @classmethod
    def check_piper_data(cls, current_language: str) -> \
            (Tuple[Path | None, List[Path], List[str]]):
        """
        Verifies that voice files exists in PIPER_DATA_PATH. If not, some default
        voice files for the current Kodi locale will need to be downloaded before
        this engine can be used. Only reports on voice files that apply to the
        current_language.

        Note that it attempts to detect all bad .onnx files, but only checks the
        .json files which have .onnx files. Could add a separate search, if needed.

        :param: current_language: 2-char language code for kodi's current language
        :return: Tuple indicating 1) if there are no valid entries.
                                  2) List of any onnx_model_files that need to
                                     be replaced/downloaded.
                                  3) List of remaining models
        """
        MY_LOGGER.debug(f'check_piper_data')
        files_to_replace: List[Path] = []
        models_kept: List[str] = []
        download_dir: Path = Path(f'{Constants.PIPER_DATA_PATH}')
        valid_path: Path | None = None
        if not download_dir.exists():
            MY_LOGGER.debug(f'Creating {download_dir} directory')
            download_dir.mkdir(exist_ok=True, parents=True)
            return None, files_to_replace, models_kept

        # onnx file names begin with the locale of the voice: ex: en_US

        onnx_finder: FindFiles = FindFiles(top=Constants.PIPER_DATA_PATH,
                                           glob_pattern='*.onnx')
        for onnx_file in onnx_finder:
            onnx_file: Path
            delete: bool = False
            ignore: bool = False
            delete_json: bool = False
            missing_json: bool = False
            missing_onnx: bool = False
            MY_LOGGER.debug(f'onnx_file: {onnx_file} exists: {onnx_file.exists()} '
                            f'onnx_jason: {onnx_file.with_suffix(".onnx.json")} '
                            f'exists: {onnx_file.exists()}')
            if not onnx_file.is_file():
                MY_LOGGER.debug(f'{onnx_file} is not a file, deleting.')
                delete = True
                missing_onnx = True
            # .onnx files should be at least 65M, so just check for ~25M
            elif onnx_file.stat().st_size < 25000000:
                MY_LOGGER.inf(f'The data file {onnx_file} looks too small and probably'
                              f'corrupt.')
                delete = True
            elif not onnx_file.name.startswith(current_language):
                MY_LOGGER.debug(f'{onnx_file} does not apply to kodi\'s current'
                                f'language. Ignored.')
                ignore = True
            json_file: Path = onnx_file.with_suffix('.onnx.json')
            if not json_file.exists():
                missing_json = True
            elif not json_file.is_file():
                delete_json = True
                MY_LOGGER.debug(f'{json_file} is not a file, deleting.')
            elif json_file.stat().st_size < 2000:
                MY_LOGGER.debug(f'{json_file} looks too small and probably corrupt,'
                                f'deleting.')
                delete_json = True
            if delete_json:
                if not delete:
                    files_to_replace.append(json_file)
            MY_LOGGER.debug(f'json: {json_file}: missing: {missing_json}')
            MY_LOGGER.debug(f'data: {onnx_file}: missing: {missing_onnx}')

            if delete or delete_json:
                cls.delete_onnx_files(onnx_file)
            valid_entry_found = not (ignore or delete or delete_json or missing_json
                                     or missing_onnx)
            if valid_entry_found:
                valid_path = json_file
                models_kept.append(onnx_file.stem)
        MY_LOGGER.debug(f'valid_path: {valid_path} files_to_replace: {files_to_replace}\n'
                        f'models_kept: {models_kept}')
        return valid_path, files_to_replace, models_kept

    @classmethod
    def delete_onnx_files(cls, onnx_file: Path) -> None:
        """
        Deletes the onnx_file (.onxx) as well as it's .json counterpart.

        :param onnx_file: path to the onnx file to delete (with suffix .onnx)

        :return: None
        """
        json_file: Path = onnx_file.with_suffix('.onnx.json')
        for file in onnx_file, json_file:
            try:
                file.unlink(missing_ok=True)
            except Exception:
                MY_LOGGER.exception(f'Could not delete {file}.')

    @classmethod
    def _get_local_model_info_by_http(cls) -> Tuple[int, Dict[str, Dict[str, Any]]]:
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
            # MY_LOGGER.debug(f'http json_strs: |{json_str}|END|')
            # json_strs = f'{json_strs}\n'
            if rc == 0:
                data = json.loads(json_str)
            else:
                MY_LOGGER.debug(f'Failed to get voice data rc: {rc}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
            return -1, {}
        return rc, data

    @classmethod
    def start_builtin_http_server(cls, model: str) -> bool:
        """
        Tracks the state of piper's private http-server and attempts to start it,
        as needed. The http-server is more efficient because it avoids the cost
        of re-initializing the engine on each request.

        :return: True if the http_server is started, otherwise False
        """
        # Already started, or broken?
        MY_LOGGER.debug(f'http_server_state: {cls.http_server_state}')
        if cls.http_server_state == cls.HTTP_SERVER_BROKEN:
            raise ValueError('damn http server is broken')

        with (cls.http_server_lock):
            # It is possible that the http server is running as an orphaned
            # process. If so, restart it, or reuse it.
            if cls.http_server_state != cls.HTTP_SERVER_READY:
                okay: bool = cls.test_http_server()
                if okay:
                    MY_LOGGER.debug(f'http_server is running')
                    cls.http_server_state = cls.HTTP_SERVER_READY
                    return True
                else:
                    MY_LOGGER.debug(f'http_server is not running')
            # Try to kill any prior running server
            if Constants.PIPER_HTTP_SERVER_PID.exists():
                with Constants.PIPER_HTTP_SERVER_PID.open('rt') as f:
                    pid: str = f.readline()
                    try:
                        pid_int = int(pid)
                        try:
                            if pid_int > 0:
                                pass  #  os.kill(pid_int, signal.SIGTERM)
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

            MY_LOGGER.debug(f'http_server_state: {cls.http_server_state}')
            if cls.http_server_state == cls.HTTP_SERVER_READY:
                return True
            elif cls.http_server_state == cls.HTTP_SERVER_BROKEN:
                return False
            if cls.http_server_state == cls.HTTP_SERVER_NOT_STARTED:
                cls.http_server_state = cls.HTTP_SERVER_STARTING
            elif cls.http_server_state != cls.HTTP_SERVER_STARTING:
                raise RuntimeError(f'Should not get here http_state:'
                                   f' {cls.http_server_state}')
            retries: int = 0
            try:
                MY_LOGGER.debug(f'Starting http_server Log: '
                                f'{Constants.PIPER_HTTP_SERVER_LOG}')
                http_server_log = Constants.PIPER_HTTP_SERVER_LOG.open('tw')

                cls._start_builtin_http_server(model, http_server_log)
                cls.http_server_state = cls.HTTP_SERVER_STARTING
                while retries <= cls.HTTP_RETRY_LIMIT:
                    Monitor.wait_for_abort(cls.HTTP_RETRY_DELAY_SECONDS)
                    result = cls._get_local_model_info_by_http()
                    if result[0] == 0:
                        MY_LOGGER.debug(f'Started http_server after: {retries} retries')
                        cls.http_server_state = cls.HTTP_SERVER_READY
                        return True
                    retries += 1
                # http_server_log.flush()
                MY_LOGGER.debug(f'FAILED Retries to start http_server: {retries}')
                cls.http_server_state = cls.HTTP_SERVER_BROKEN
            except AbortException:
                reraise(*sys.exc_info())
            except Exception as e:
                MY_LOGGER.exception('')

        MY_LOGGER.debug(f'broken: {cls.http_server_state}')
        cls.http_server_state = cls.HTTP_SERVER_BROKEN
        return False

    @classmethod
    def _start_builtin_http_server(cls, model: str,  http_server_log) -> None:
        """
        Starts the builtin http server to provide services using cached data
        rather than just constantly reinitializing the TTS engine, etc. on every
        voicing.

        There MUST be at least one pair of onnx files (voice files) in the data
        directory AND PIPER_HTTP_SERVER_DEFAULT_VG_ARG MUST refer to a vaild file
        in that directory.

        Basically, the server is started by:

             python3 -m piper.http_server -m en_US-lessac-medium

        Of course things get more complicated if things are not in default locations:

        /home/fbacher/Source/venvs/TTS/bin/python3 -m piper.http_server \
            -m en_US-libritts-high \
            ---/home/fbacher/.kodi_data/userdata/addon_data/service.kodi.tts
            /piper/data
        """
        current_voice_id: str = Settings.get_voice_id(engine_key=ServiceKey.PIPER_KEY)
        if model is not None:
            current_model = model
        else:
            current_model: str = current_voice_id.split('|')[1]
        env = cls.get_basic_env()
        args: list[str] = cls.get_basic_args()
        args.extend(['-m',
                     Constants.PIPER_HTTP_SERVER_ARG, '-m',
                     current_model,
                     '--host', Constants.PIPER_HTTP_SERVER_HOST,
                     '--port', Constants.PIPER_HTTP_SERVER_PORT,
                     '--data-dir', str(Constants.PIPER_DATA_PATH),
                     '--download-dir', str(Constants.PIPER_DATA_PATH),
                     '--debug'])
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
                cls._http_process: subprocess.Popen
            else:
                cls._http_process = subprocess.Popen(args,
                                                     stdin=None,
                                                     stdout=subprocess.PIPE,
                                                     stderr=http_server_log,
                                                     shell=False,
                                                     text=True,
                                                     encoding='utf-8', env=env,
                                                     close_fds=True)
                cls._http_process: subprocess.Popen
            try:
                MinimalMonitor.exception_on_abort(timeout=1.50)
                if cls._http_process.poll() is None:
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
                    env: dict[str, str],
                    cmd_input: str = '',
                    out_file: Path = None) -> Tuple[int, str]:
        """
        Runs the given command, returning stdout as a string.

        :parameter args: Arguments to pass to command
        :parameter env: Environment variables
        :parameter cmd_input: Sent to command as stdin
        :parameter out_file: if specified, then write output to the file
        :return: Tuple[rc, List[str]]
        """
        rc: int = -1
        output: str = ''
        try:
            platform: str = 'Linux'
            if Constants.PLATFORM_WINDOWS:
                platform = 'Windows'
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
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'Running command: {platform}:\n'
                                  f'args: {args}\n '
                                  f'cmd_input: {cmd_input}')
            try:
                rc = process.returncode
                if rc != 0:
                    MY_LOGGER.debug(f'piper failed with RC: {process.returncode}')
                else:
                    output = process.stdout
                    if MY_LOGGER.isEnabledFor(DEBUG_XV):
                        #  Python 9 hates
                        #  MY_LOGGER.debug_v(f'\noutput: {"\n".join(output)}')
                        x = output.split('\n')
                        MY_LOGGER.debug_xv(f'cmd output: {x}')
            except AbortException:
                reraise(*sys.exc_info())
            except Exception:
                MY_LOGGER.exception('')
                return -2, ''
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
            return -2, ''
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
                 quality: str | None = None,
                 speaker_id: str | None = None) -> None:
        super().__init__()

        self._speaker_name: str | None = speaker_name
        self._ietf_language_code: str | None = ietf_language_code  # ex 'en'
        self._ietf_territory_code: str | None = ietf_territory_code  # ex 'us'
        self._voice_group_name: str | None = voice_group_name
        self._voice_quality: str | None = quality
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
    def quality(self) -> str | None:
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
                        f'quality: {self._voice_quality}')
        return piper_vg_id

    def __repr__(self) -> str:
        result: str = ''
        result = f'{result} speaker_name: {self._speaker_name}\n'
        result = f'{result} ietf_language_code: {self._ietf_language_code}\n'
        result = f'{result} ietf_territory_code: {self._ietf_territory_code}\n'
        result = f'{result} voice_group_name: {self._voice_group_name}\n'
        result = f'{result} quality = {self._voice_quality}\n'
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
        if self._piper_data is None:
            raise ValueError('piper_data not initialized')
        return self._piper_data

    def download(self, phrase: Phrase,
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
        e_vg = EngineVoiceManager.get_vg(e_voice.e_vg_id,
                                         PiperDownloader.service_key)

        MY_LOGGER.debug(f'Setting PiperData voice_group_name to {e_vg.vg_name}')
        tts_data: PiperData
        tts_data = PiperData(speaker_name='',
                             ietf_language_code=ietf_lang.language,
                             ietf_territory_code=ietf_lang.territory,
                             voice_group_name=e_vg.vg_name,
                             quality=str(e_voice.voice_quality),
                             speaker_id=e_voice.e_voice_id)
        MY_LOGGER.debug(f'piper_data: {tts_data}')
        self._piper_data = tts_data
        MY_LOGGER.debug(f'tmp_path: {self._tmp_path} phrase: {phrase.short_text()}')
        if self._output_type == OutputType.USE_FILE:
            return PiperApi.tts(phrase.text, voiced_path=self._tmp_path,
                                model=e_vg.e_vg_id,
                                voice_id=e_voice.e_voice_id)
        return 1  # Not set up for anything but returning a file

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


Monitor.register_abort_listener(listener=PiperApi.abort_listener,
                                name='piper_abort_listener', thread=None)
