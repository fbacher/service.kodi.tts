# from backends.i_tts_backend_base import ITTSBackendBase
# from backends.settings.service_types import Services
import sys

from backends.settings.setting_properties import SettingsProperties
# from backends.settings.settings_map import SettingsMap
# from backends.settings.validators import StringValidator
from backends.settings.settings_map import Reason, SettingsMap
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
        Backends.GOOGLE_ID,
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
            cls.determine_available_engines()
            cls.load_current_backend()
            # Load all settings for current backend
            # Can be called multiple times
            Settings.load_settings()
            util.runInThread(cls.load_other_engines, name='load_other_engines')

    @classmethod
    def load_base(cls):
        from backends.settings.base_service_settings import BaseServiceSettings
        BaseServiceSettings()

    @classmethod
    def determine_available_engines(cls):
        try:
            from backends.espeak_settings import ESpeakSettings
            espeak_settings: ESpeakSettings = ESpeakSettings()
            is_available: bool = espeak_settings.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.ESPEAK_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.ESPEAK_ID, Reason.NOT_AVAILABLE)

        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
            SettingsMap.set_is_available(Backends.ESPEAK_ID, Reason.BROKEN)

        try:
            from backends.engines.festival_settings import FestivalSettings
            festival: FestivalSettings = FestivalSettings()
            is_available: bool = festival.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.FESTIVAL_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.FESTIVAL_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
            SettingsMap.set_is_available(Backends.FESTIVAL_ID, Reason.BROKEN)

        try:
            from backends.engines.FliteSettings import FliteSettings
            flite: FliteSettings = FliteSettings()
            is_available: bool = flite.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.FLITE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.FLITE_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
            SettingsMap.set_is_available(Backends.FLITE_ID, Reason.BROKEN)

        try:
            from backends.engines.google_settings import GoogleSettings
            google_settings: GoogleSettings = GoogleSettings()
            is_available: bool = google_settings.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.GOOGLE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.GOOGLE_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
            SettingsMap.set_is_available(Backends.GOOGLE_ID, Reason.BROKEN)

        try:
            from backends.settings.Pico2WaveSettings import Pico2WaveSettings
            pico2Wave: Pico2WaveSettings = Pico2WaveSettings()
            is_available: bool = pico2Wave.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.PICO_TO_WAVE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.PICO_TO_WAVE_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
            SettingsMap.set_is_available(Backends.PICO_TO_WAVE_ID, Reason.BROKEN)

        try:
            from backends.engines.responsive_voice_settings import ResponsiveVoiceSettings
            responsive_settings: ResponsiveVoiceSettings = ResponsiveVoiceSettings()
            is_available: bool = responsive_settings.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.RESPONSIVE_VOICE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.RESPONSIVE_VOICE_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
            SettingsMap.set_is_available(Backends.RESPONSIVE_VOICE_ID, Reason.BROKEN)

        try:
            from backends.engines.experimental_engine_settings import ExperimentalSettings
            experimental: ExperimentalSettings = ExperimentalSettings()
            is_available: bool = experimental.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.EXPERIMENTAL_ENGINE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.EXPERIMENTAL_ENGINE_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
            SettingsMap.set_is_available(Backends.EXPERIMENTAL_ENGINE_ID, Reason.BROKEN)

        try:
            from backends.engines.speech_dispatcher_settings import \
                SpeechDispatcherSettings
            spd: SpeechDispatcherSettings = SpeechDispatcherSettings()
            is_available: bool = spd.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.SPEECH_DISPATCHER_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.SPEECH_DISPATCHER_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
            SettingsMap.set_is_available(Backends.SPEECH_DISPATCHER_ID, Reason.BROKEN)

    @classmethod
    def load_current_backend(cls) -> str:
        """
        engine_id_validator = StringValidator(SettingsProperties.ENGINE, '',
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way too big
                                              max_length=32,
                                              default=Backends.ESPEAK_ID)
        SettingsMap.define_setting(SettingsProperties.ENGINE, Services.TTS_SERVICE,
                                   engine_id_validator)
        """
        engine_id: str = SettingsLowLevel.get_engine_id(bootstrap=True,
                                                        default=None)
        if engine_id is None:
            engine_id = SettingsProperties.ENGINE_DEFAULT
        Settings.set_engine_id(engine_id)
        engine_id = BootstrapEngines.load_engine(engine_id)

    @classmethod
    def load_engine(cls, engine_id: str) -> None:
        try:
            if not SettingsMap.is_available(engine_id):
                return

            #  cls._logger.debug(f'Loading engine_id: {engine_id}')
            if engine_id in (Backends.AUTO_ID, Backends.ESPEAK_ID):
                from backends.espeak import ESpeakTTSBackend
                engine_id = ESpeakTTSBackend().service_ID
            elif engine_id == Backends.FESTIVAL_ID:
                from backends.festival import FestivalTTSBackend
                engine_id = FestivalTTSBackend().service_ID
            elif engine_id == Backends.FLITE_ID:
                from backends.flite import FliteTTSBackend
                engine_id = FliteTTSBackend().service_ID
            elif engine_id == Backends.PICO_TO_WAVE_ID:
                from backends.pico2wave import Pico2WaveTTSBackend
                engine_id = Pico2WaveTTSBackend().service_ID
            # elif engine_id == Backends.RECITE_ID:
            elif engine_id == Backends.RESPONSIVE_VOICE_ID:
                from backends.responsive_voice import ResponsiveVoiceTTSBackend
                engine_id = ResponsiveVoiceTTSBackend().service_ID
            elif engine_id == Backends.EXPERIMENTAL_ENGINE_ID:
                from backends.engines.experimental_engine import ExperimentalTTSBackend
                engine_id = ExperimentalTTSBackend().service_ID
            elif engine_id == Backends.SPEECH_DISPATCHER_ID:
                from backends.speechdispatcher import SpeechDispatcherTTSBackend
                engine_id = SpeechDispatcherTTSBackend().service_ID
            elif engine_id == Backends.GOOGLE_ID:
                from backends.google import GoogleTTSEngine
                engine_id = GoogleTTSEngine().service_ID
            else:  # Catch all default
                # engine_id = ESpeakSettings().service_ID
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

        # Include settings for other engines
        Settings.load_settings()


BootstrapEngines.init()
