from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.base_engine_service_settings import BaseEngineServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, IntValidator, StringValidator,
                                          Validator)
from common.base_services import BaseServices
from common.setting_constants import Backends
from common.typing import *

class BasePlayerSettings(BaseEngineServiceSettings):

    broken = False

    # Define TTS native scales for volume, speed, etc
    #
    # Min, Default, Max, Integer_Only (no float)
    ttsPitchConstraints: Constraints = Constraints(0, 50, 99, True, False, 1.0,
                                                   SettingsProperties.PITCH, 50, 1.0)
    ttsVolumeConstraints: Constraints = Constraints(minimum=-12, default=0, maximum=12,
                                                    integer=True, decibels=True,
                                                    scale=1.0,
                                                    property_name=SettingsProperties.VOLUME,
                                                    midpoint=0, increment=1.0)
    ttsSpeedConstraints: Constraints = Constraints(25, 100, 400, False, False, 0.01,
                                                   SettingsProperties.SPEED, 100, 0.25)

    # TODO: move to default settings map
    TTSConstraints: Dict[str, Constraints] = {
        SettingsProperties.SPEED : ttsSpeedConstraints,
        SettingsProperties.PITCH : ttsPitchConstraints,
        SettingsProperties.VOLUME: ttsVolumeConstraints
    }
    # TODO: eliminate these
    pitchConstraints: Constraints = ttsPitchConstraints
    volumeConstraints: Constraints = ttsVolumeConstraints
    speedConstraints: Constraints = ttsSpeedConstraints
    # Volume scale as presented to the user

    # volumeExternalEndpoints = (-12, 12)
    # volumeStep = 1
    # volumeSuffix = 'dB'
    # speedInt = True
    # _loadedSettings = {}
    #  currentSettings = []
    settings: Dict[str, Validator] = {}
    constraints: Dict[str, Constraints] = {}

    initialized_settings: bool = False

    # _supported_input_formats: List[str] = []
    # _supported_output_formats: List[str] = []
    # _provides_services: List[ServiceType] = [ServiceType.ENGINE]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz.initialized_settings:
            return

        if not clz.initialized_settings:
            clz.initialized_settings = True

        allowed_engine_ids: List[str] = [

        ]
        engine_id_validator = StringValidator(SettingsProperties.ENGINE, '',
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way to big
                                              max_length=32,
                                              default_value=Backends.ESPEAK_ID)
        SettingsMap.define_setting(SettingsProperties.ENGINE, Services.TTS_SERVICE,
                                   engine_id_validator)

        auto_item_extra_validator: BoolValidator
        auto_item_extra_validator = BoolValidator(SettingsProperties.AUTO_ITEM_EXTRA, '',
                                                  default=False)
        SettingsMap.define_setting(Services.TTS_SERVICE, SettingsProperties.AUTO_ITEM_EXTRA,
                                   auto_item_extra_validator)
        auto_item_extra_delay_validator: IntValidator
        auto_item_extra_delay_validator = IntValidator(
                SettingsProperties.AUTO_ITEM_EXTRA_DELAY, '',
                min_value=0, max_value=3, default_value=0,
                step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.AUTO_ITEM_EXTRA_DELAY,
                                   auto_item_extra_delay_validator)
        background_progress_validator: IntValidator
        background_progress_validator = IntValidator(
                SettingsProperties.BACKGROUND_PROGRESS_INTERVAL, '',
                min_value=0, max_value=60, default_value=5,
                step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.BACKGROUND_PROGRESS_INTERVAL,
                                   background_progress_validator)
        disable_broken_services: BoolValidator
        disable_broken_services = BoolValidator(
                SettingsProperties.DISABLE_BROKEN_SERVICES, '',
                default=True)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.DISABLE_BROKEN_SERVICES,
                                   disable_broken_services)
        speak_background_progress: BoolValidator
        speak_background_progress = BoolValidator(
                SettingsProperties.SPEAK_BACKGROUND_PROGRESS, '',
                default=False)
        SettingsMap.define_setting(Services.TTS_SERVICE,
                                   SettingsProperties.SPEAK_BACKGROUND_PROGRESS,
                                   speak_background_progress)

        '''
        CONVERTER?,
        GENDER_VISIBLE,
        GUI,
        SPEECH_DISPATCHER,
        OUTPUT_VIA,
        OUTPUT_VISIBLE,
        SETTINGS_BEING_CONFIGURED,
        SETTINGS_DIGEST,
        SPEAK_VIA_KODI,
        TTSD_HOST,
        TTSD_PORT,
        VOICE_VISIBLE,
        VOLUME_VISIBLE
        '''

    @classmethod
    def register(cls, what: Type[ITTSBackendBase]) -> None:
        BaseServices.register(what)
