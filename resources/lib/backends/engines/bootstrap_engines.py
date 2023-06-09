# from backends.i_tts_backend_base import ITTSBackendBase
# from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
# from backends.settings.settings_map import SettingsMap
# from backends.settings.validators import StringValidator
from common import *
from common.setting_constants import Backends
from common.settings import Settings


# from speechutil import SpeechUtilComTTSBackend


# from voiceover import VoiceOverBackend #Can't test
from common.settings_low_level import SettingsLowLevel


class BootstrapEngines:
    # Instances of ITTSBackendBase
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
        #   SpeechUtilComTTSBackend(),
        # ESpeakCtypesTTSBackend(),
        Backends.LOG_ONLY_ID
    ]
    _initialized: bool = False

    @classmethod
    def init(cls) -> None:
        if not cls._initialized:
            cls.initialized = True
            cls.load_current_backend()

    @classmethod
    def load_current_backend(cls):
        '''
        engine_id_validator = StringValidator(SettingsProperties.ENGINE, '',
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way too big
                                              max_length=32,
                                              default_value=Backends.ESPEAK_ID)
        SettingsMap.define_setting(SettingsProperties.ENGINE, Services.TTS_SERVICE,
                                   engine_id_validator)
        '''
        engine_id: str = SettingsLowLevel.get_engine_id(bootstrap=True)
        if engine_id is None:
            engine_id = SettingsProperties.ENGINE_DEFAULT
        BootstrapEngines.load_engine(engine_id)

    @classmethod
    def load_engine(cls, engine_id: str) -> None:
        if engine_id in (Backends.AUTO_ID, Backends.ESPEAK_ID):
            from backends.espeak_settings import ESpeakSettings
            ESpeakSettings()
        elif engine_id == Backends.FESTIVAL_ID:
            from backends.engines.festival_settings import FestivalSettings
            FestivalSettings()
        elif engine_id == Backends.FLITE_ID:
            from backends.engines.FliteSettings import FliteSettings
            FliteSettings()
        elif engine_id == Backends.PICO_TO_WAVE_ID:
            from backends.settings.Pico2WaveSettings import Pico2WaveSettings
            Pico2WaveSettings()
        # elif engine_id == Backends.RECITE_ID:
        elif engine_id == Backends.RESPONSIVE_VOICE_ID:
            # from backends.engines.responsive_voice_settings import ResponsiveVoiceSettings
            # ResponsiveVoiceSettings()
            from backends.responsive_voice import ResponsiveVoiceTTSBackend
            ResponsiveVoiceTTSBackend()
        elif engine_id == Backends.SPEECH_DISPATCHER_ID:
            from backends.engines.speech_dispatcher_settings import \
                SpeechDispatcherSettings
            SpeechDispatcherSettings()

    @classmethod
    def load_other_engines(cls) -> None:
        from common.base_services import BaseServices
        for engine_id in cls.engine_ids_by_priority:
            engine_id: str
            if BaseServices.getService(engine_id) is None:
                cls.load_engine(engine_id)


BootstrapEngines.init()
