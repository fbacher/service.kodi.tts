# coding=utf-8
from __future__ import annotations  # For union operator |

from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, StringValidator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import AudioType, Backends, Players
from common.settings_low_level import SettingProp
from common.system_queries import SystemQueries

module_logger = BasicLogger.get_logger(__name__)


class PiperSettings(BaseServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.PIPER_ID
    engine_id = Backends.PIPER_ID
    engine_id = Backends.PIPER_ID
    service_id: str = Services.PIPER_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    displayName = 'Piper_TTS'
    # player_handler_class: Type[BasePlayerHandler] = WavAudioPlayerHandler

    """
    In an attempt to bring some consistency between the various players, engines and 
    converters, standard "TTS" constraints are defined which every engine, player_key,
    converter, etc. is to convert to/from. Hopefully this will help these settings
    to remain sane regardless of the combination of services used. 
    
    So, if an engine does not produce volume that matches the db-scale based
    ttsVolumeConstraints, then the engine needs to create a customer converter. 
    
    In the case of Experimental engine, it's volume (it might be configureable) 
    appears to be equivalent to be about 8db (as compared to TTS). Since we
    have to use a different player_key AND since
    it is almost guaranteed that the voiced text is cached, just set volume
    to fixed 8db and let player_key handle make the necessary adjustments to the volume.
    
    In other words, create a custom validator which always returns a volume of 1
    (or just don't use the validator and such and hard code it inline).
    
    """

    _supported_input_formats: List[AudioType] = []
    _supported_output_formats: List[AudioType] = [AudioType.WAV]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    SoundCapabilities.add_service(service_id, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _logger: BasicLogger = None

    # Every setting from settings.xml must be listed here
    # SettingName, default value
    initialized: bool = False

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(clz.service_id, *args, **kwargs)
        BaseEngineSettings(clz.service_id)
        if PiperSettings.initialized:
            return
        PiperSettings.initialized = True
        if clz._logger is None:
            clz._logger = module_logger
        PiperSettings.init_settings()
        installed: bool = clz.isInstalled()
        SettingsMap.set_is_available(clz.service_id, Reason.AVAILABLE)

    @classmethod
    def init_settings(cls):
        service_properties: Dict[str, Any]
        service_properties = {'name'                     : cls.displayName,
                              Constants.MAX_PHRASE_LENGTH: 400,
                              Constants.CACHE_SUFFIX     : 'piper'}
        SettingsMap.define_service_properties(ServiceType.ENGINE, cls.engine_id,
                                              service_properties)
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        speed_validator: NumericValidator
        speed_validator = NumericValidator(SettingProp.SPEED,
                                           cls.service_id,
                                           minimum=.25, maximum=5,
                                           default=1,
                                           is_decibels=False,
                                           is_integer=False)
        SettingsMap.define_setting(cls.service_id,
                                   SettingProp.SPEED,
                                   speed_validator)

        pitch_validator: NumericValidator
        pitch_validator = NumericValidator(SettingProp.PITCH,
                                           cls.service_id,
                                           minimum=0, maximum=99, default=50,
                                           is_decibels=False, is_integer=True)
        SettingsMap.define_setting(cls.service_id, SettingProp.PITCH,
                                   pitch_validator)

        volume_validator: NumericValidator
        volume_validator = NumericValidator(SettingProp.VOLUME,
                                            cls.service_id,
                                            minimum=5, maximum=400,
                                            default=100, is_decibels=False,
                                            is_integer=False)
        SettingsMap.define_setting(cls.service_id,
                                   SettingProp.VOLUME,
                                   volume_validator)
        language_validator: StringValidator
        language_validator = StringValidator(SettingProp.LANGUAGE, cls.engine_id,
                                             allowed_values=[], min_length=2,
                                             max_length=5)
        voice_validator: StringValidator
        voice_validator = StringValidator(SettingProp.VOICE, cls.engine_id,
                                          allowed_values=[], min_length=1, max_length=10)
        voice_path_validator: StringValidator
        voice_path_validator = StringValidator(SettingProp.VOICE_PATH,
                                               cls.engine_id,
                                               allowed_values=[], min_length=1,
                                               max_length=1024)
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingProp.PIPE, cls.engine_id,
                                       default=False)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingProp.CACHE_SPEECH, cls.engine_id,
                                        default=True)

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        valid_players: List[str] = [Players.MPV, Players.MPLAYER, Players.SFX,
                                    Players.WINDOWS, Players.APLAY,
                                    Players.PAPLAY, Players.AFPLAY, Players.SOX,
                                    Players.MPG321, Players.MPG123,
                                    Players.MPG321_OE_PI, Players.INTERNAL]
        player_validator: StringValidator
        player_validator = StringValidator(SettingProp.PLAYER, cls.engine_id,
                                           allowed_values=valid_players,
                                           default=Players.MPLAYER)

        SettingsMap.define_setting(cls.service_id, SettingProp.LANGUAGE,
                                   language_validator)
        SettingsMap.define_setting(cls.service_id,
                                   SettingProp.VOICE_PATH,
                                   voice_path_validator)
        SettingsMap.define_setting(cls.service_id, SettingProp.VOICE,
                                   voice_validator)
        SettingsMap.define_setting(cls.service_id, SettingProp.PIPE,
                                   pipe_validator)
        SettingsMap.define_setting(cls.service_id, SettingProp.PLAYER,
                                   player_validator)
        SettingsMap.define_setting(cls.service_id, SettingProp.CACHE_SPEECH,
                                   cache_validator)

    @classmethod
    def isSupportedOnPlatform(cls) -> bool:
        return SystemQueries.isLinux()

    @classmethod
    def isInstalled(cls) -> bool:
        installed: bool = False
        if cls.isSupportedOnPlatform():
            installed = True
        return installed

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        return SettingsMap.is_valid_setting(cls.service_id, setting)

    '''
    @classmethod
    def getSettingNames(cls) -> List[str]:
        settingNames: List[str] = []
        for settingName in cls.settings.keys():
            settingNames.append(settingName)
    
        return settingNames
    '''

    @classmethod
    def available(cls) -> bool:
        engine_output_formats: List[str]
        engine_output_formats = SoundCapabilities.get_output_formats(
                cls.service_id)
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[AudioType.MP3],
                producer_formats=[])
        if len(candidates) > 0:
            return True
