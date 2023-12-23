from backends.audio.sound_capabilties import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.i_validators import ValueType
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          StringValidator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Backends, Players
from common.settings_low_level import SettingsProperties
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ResponsiveVoiceSettings(BaseServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.RESPONSIVE_VOICE_ID
    engine_id: str = Backends.RESPONSIVE_VOICE_ID
    service_ID: str = Services.RESPONSIVE_VOICE_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS

    logger: BasicLogger = None
    displayName = 'ResponsiveVoice'

    """
    In an attempt to bring some consistency between the various players, engines and 
    converters, standard "TTS" constraints are defined which every engine, player,
    converter, etc. is to convert to/from. Hopefully this will help these settings
    to remain sane regardless of the combination of services used. 
    
    So, if an engine does not produce volume that matches the db-scale based
    ttsVolumeConstraints, then the engine needs to create a customer converter. 
    
    In the case of Responsive Voice, it's maximum volume (1.0) appears to be
    equivalent to about 0db. Since we have to use a different player AND since
    it is almost guaranteed that the voiced text is cached, just set volume
    to fixed 1.0 and let player handle volume.
    
    In other words, create a custom validator which always returns a volume of 1
    (or just don't use the validator and such and hard code it inline).

    
        volume = self.volumeConstraints.translate_value(
                                        self.volumeConversionConstraints, volumeDb)
    
    """

    class VolumeConstraintsValidator(ConstraintsValidator):

        def __init__(self, setting_id: str, service_id: str,
                     constraints: Constraints) -> None:
            super().__init__(setting_id, service_id, constraints)
            clz = type(self)

        def set_tts_value(self, value: int | float | str,
                          value_type: ValueType = ValueType.VALUE) -> None:
            """
            Keep value fixed at 1
            :param value:
            :param value_type:
            """
            constraints: Constraints = self.constraints
            constraints.setSetting(1, self.service_id)

        def get_tts_value(self,
                          value_type: ValueType = ValueType.VALUE) -> int | float | str:
            """
            Keep value fixed at 1
            :return:
            """
            return 1

        def setUIValue(self, ui_value: str) -> None:
            pass

        def getUIValue(self) -> str:
            value, _, _, _ = self.get_tts_values()
            return str(value)

    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _logger: BasicLogger = None

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(*args, **kwargs)

        BaseEngineSettings(clz.service_ID)
        self.initialized: bool = False
        if self.initialized:
            return
        self.initialized = True
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.init_settings()
        installed: bool = clz.isInstalled()
        SettingsMap.set_is_available(clz.service_ID, Reason.AVAILABLE)

    def init_settings(self):
        service_properties = {'name'                     : self.displayName,
                              Constants.MAX_PHRASE_LENGTH: 200,
                              Constants.CACHE_SUFFIX     : 'rv'}
        SettingsMap.define_service(ServiceType.ENGINE, self.service_ID,
                                   service_properties)
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        speed_constraints_val = ConstraintsValidator(SettingsProperties.SPEED,
                                                     self.engine_id,
                                                     BaseServiceSettings.ttsSpeedConstraints)

        pitch_constraints: Constraints = Constraints(0, 50, 99, True, False, 1.0,
                                                     SettingsProperties.PITCH)
        pitch_constraints_validator = ConstraintsValidator(SettingsProperties.PITCH,
                                                           self.engine_id,
                                                           pitch_constraints)

        volumeConversionConstraints: Constraints
        volumeConversionConstraints = Constraints(minimum=0.1, default=1.0,
                                                  maximum=2.0, integer=False,
                                                  decibels=False, scale=1.0,
                                                  property_name=SettingsProperties.VOLUME,
                                                  midpoint=0.8, increment=0.1)
        engine_id_constraints_validator = self.VolumeConstraintsValidator(
                SettingsProperties.VOLUME, self.engine_id, volumeConversionConstraints)

        SettingsMap.define_setting(self.service_ID, SettingsProperties.VOLUME,
                                   engine_id_constraints_validator)
        '''
        volume_constraints_validator = self.VolumeConstraintsValidator(
                SettingsProperties.VOLUME,
                self.engine_id,
                self.ttsVolumeConstraints)

        SettingsMap.define_setting(self.service_ID, SettingsProperties.VOLUME,
                                   volume_constraints_validator)
        '''

        audio_validator: StringValidator
        audio_converter_validator = StringValidator(SettingsProperties.CONVERTER,
                                                    self.engine_id,
                                                    allowed_values=[Services.LAME_ID])

        SettingsMap.define_setting(self.service_ID, SettingsProperties.CONVERTER,
                                   audio_converter_validator)

        api_key_validator = StringValidator(SettingsProperties.API_KEY, self.engine_id,
                                            allowed_values=[], min_length=0,
                                            max_length=1024)
        language_validator: StringValidator
        language_validator = StringValidator(SettingsProperties.LANGUAGE, self.engine_id,
                                             allowed_values=[], min_length=2,
                                             max_length=5)
        voice_validator: StringValidator
        voice_validator = StringValidator(SettingsProperties.VOICE, self.engine_id,
                                          allowed_values=[], min_length=1, max_length=10)
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingsProperties.PIPE, self.engine_id,
                                       default=False)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, self.engine_id,
                                        default=True)

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        valid_players: List[str] = [Players.SFX, Players.WINDOWS, Players.APLAY,
                                    Players.PAPLAY, Players.AFPLAY, Players.SOX,
                                    Players.MPLAYER, Players.MPG321, Players.MPG123,
                                    Players.MPG321_OE_PI]
        player_validator: StringValidator
        player_validator = StringValidator(SettingsProperties.PLAYER, self.engine_id,
                                           allowed_values=valid_players,
                                           default=Players.MPLAYER)

        SettingsMap.define_setting(service_id=self.service_ID,
                                   property_id=SettingsProperties.API_KEY,
                                   validator=api_key_validator)
        SettingsMap.define_setting(self.service_ID, SettingsProperties.LANGUAGE,
                                   language_validator)
        SettingsMap.define_setting(self.service_ID, SettingsProperties.VOICE,
                                   voice_validator)
        SettingsMap.define_setting(self.service_ID, SettingsProperties.PIPE,
                                   pipe_validator)
        SettingsMap.define_setting(self.service_ID, SettingsProperties.SPEED,
                                   speed_constraints_val)
        SettingsMap.define_setting(self.service_ID, SettingsProperties.PITCH,
                                   pitch_constraints_validator)
        SettingsMap.define_setting(self.service_ID, SettingsProperties.PLAYER,
                                   player_validator)
        SettingsMap.define_setting(self.service_ID, SettingsProperties.CACHE_SPEECH,
                                   cache_validator)

    @classmethod
    def isSupportedOnPlatform(cls) -> bool:
        return (SystemQueries.isLinux() or SystemQueries.isWindows()
                or SystemQueries.isOSX())

    @classmethod
    def isInstalled(cls) -> bool:
        installed: bool = False
        if cls.isSupportedOnPlatform():
            installed = True
        return installed

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        return SettingsMap.is_valid_property(cls.service_ID, setting)
