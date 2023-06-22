# from backends.i_tts_backend_base import ITTSBackendBase
# from backends.settings.service_types import Services
import sys

from backends.settings.setting_properties import SettingsProperties
# from backends.settings.settings_map import SettingsMap
# from backends.settings.validators import StringValidator
from common import *
from common.logger import BasicLogger
from common.setting_constants import Backends
from common.settings import Settings


# from speechutil import SpeechUtilComTTSBackend


# from voiceover import VoiceOverBackend #Can't test
from common.settings_low_level import SettingsLowLevel
from utils import util

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class BootstrapEngines:
    # Instances of ITTSBackendBase
    _logger: BasicLogger = None
    engine_ids_by_priority: List[str] = [  # SAPITTSBackend(),
        # OSXSayTTSBackend(),
        Backends.ESPEAK_ID,
        # JAWSTTSBackend(),
        # NVDATTSBackend(),
        Backends.FLITE_ID,
        Backends.PICO_TO_WAVE_ID,
        Backends.FESTIVAL_ID,
        # CepstralTTSBackend(),
        #            CepstralTTSOEBackend(),
        Backends.SPEECH_DISPATCHER_ID,
        #            VoiceOverBackend(),
        # SpeechServerBackend(),
        # ReciteTTSBackend(),
        # GoogleTTSBackend(),
        Backends.RESPONSIVE_VOICE_ID,
        Backends.EXPERIMENTAL_ENGINE_ID,
        #   SpeechUtilComTTSBackend(),
        # ESpeakCtypesTTSBackend(),
        Backends.LOG_ONLY_ID
    ]
    _initialized: bool = False

    @classmethod
    def init(cls) -> None:
        if not cls._initialized:
            cls._initialized = True
            cls._logger = module_logger.getChild(cls.__class__.__name__)
            cls.load_base()
            cls.load_current_backend()
            util.runInThread(cls.load_other_engines, name='load_other_engines')

    @classmethod
    def load_base(cls):
        from backends.settings.base_service_settings import BaseServiceSettings
        BaseServiceSettings()

    @classmethod
    def load_current_backend(cls) -> str:
        '''
        engine_id_validator = StringValidator(SettingsProperties.ENGINE, '',
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way too big
                                              max_length=32,
                                              default_value=Backends.ESPEAK_ID)
        SettingsMap.define_setting(SettingsProperties.ENGINE, Services.TTS_SERVICE,
                                   engine_id_validator)
        '''
        engine_id: str = SettingsLowLevel.get_engine_id(bootstrap=True,
                                                        default=None)
        if engine_id is None:
            engine_id = SettingsProperties.ENGINE_DEFAULT
        Settings.set_engine_id(engine_id)
        engine_id = BootstrapEngines.load_engine(engine_id)

    @classmethod
    def load_engine(cls, engine_id: str) -> None:
        try:
            cls._logger.debug(f'Loading engine_id: {engine_id}')
            if engine_id in (Backends.AUTO_ID, Backends.ESPEAK_ID):
                from backends.espeak_settings import ESpeakSettings
                from backends.espeak import ESpeakTTSBackend
                engine_id = ESpeakSettings().service_ID
                engine_id = ESpeakTTSBackend().service_ID
            elif engine_id == Backends.FESTIVAL_ID:
                from backends.engines.festival_settings import FestivalSettings
                from backends.festival import FestivalTTSBackend
                engine_id = FestivalSettings().service_ID
                engine_id = FestivalTTSBackend().service_ID
            elif engine_id == Backends.FLITE_ID:
                from backends.engines.FliteSettings import FliteSettings
                from backends.flite import FliteTTSBackend
                engine_id = FliteSettings().service_ID
                engine_id = FliteTTSBackend().service_ID
            elif engine_id == Backends.PICO_TO_WAVE_ID:
                from backends.settings.Pico2WaveSettings import Pico2WaveSettings
                from backends.pico2wave import Pico2WaveTTSBackend
                engine_id = Pico2WaveSettings().service_ID
                engine_id = Pico2WaveTTSBackend().service_ID
            # elif engine_id == Backends.RECITE_ID:
            elif engine_id == Backends.RESPONSIVE_VOICE_ID:
                from backends.engines.responsive_voice_settings import ResponsiveVoiceSettings
                ResponsiveVoiceSettings()
                from backends.responsive_voice import ResponsiveVoiceTTSBackend
                engine_id = ResponsiveVoiceTTSBackend().service_ID
            elif engine_id == Backends.EXPERIMENTAL_ENGINE_ID:
                from backends.engines.experimental_engine_settings import ExperimentalSettings
                ExperimentalSettings()
                from backends.engines.experimental_engine import ExperimentalTTSBackend
                engine_id = ExperimentalTTSBackend().service_ID
            elif engine_id == Backends.SPEECH_DISPATCHER_ID:
                from backends.engines.speech_dispatcher_settings import \
                    SpeechDispatcherSettings
                from backends.speechdispatcher import SpeechDispatcherTTSBackend
                engine_id = SpeechDispatcherSettings().service_ID
                engine_id = SpeechDispatcherTTSBackend().service_ID
            else:  # Catch all default
                # from backends.espeak_settings import ESpeakSettings
                # engine_id = ESpeakSettings().service_ID
                from backends.engines.responsive_voice_settings import ResponsiveVoiceSettings
                ResponsiveVoiceSettings()
                from backends.responsive_voice import ResponsiveVoiceTTSBackend
                engine_id = ResponsiveVoiceTTSBackend().service_ID
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
        return

    @classmethod
    def load_other_engines(cls) -> None:
        from common.base_services import BaseServices
        for engine_id in cls.engine_ids_by_priority:
            engine_id: str
            if BaseServices.getService(engine_id) is None:
                cls.load_engine(engine_id)


BootstrapEngines.init()
