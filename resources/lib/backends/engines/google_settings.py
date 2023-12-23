from backends.audio.sound_capabilties import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.i_validators import ValueType
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, StringValidator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Backends, Genders, Players
from common.settings_low_level import SettingsProperties
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class GoogleSettings(BaseServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.GOOGLE_ID
    backend_id = Backends.GOOGLE_ID
    engine_id = Backends.GOOGLE_ID
    service_ID: str = Services.GOOGLE_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    displayName = 'GoogleTTS'

    # Maximum phrase length that a remote engine can convert to speech at a time
    # None indicates that the engine does not download from a remote server
    MAXIMUM_PHRASE_LENGTH: int | None = 100

    """
    In an attempt to bring some consistency between the various players, engines and 
    converters, standard "TTS" constraints are defined which every engine, player,
    converter, etc. is to convert to/from. Hopefully this will help these settings
    to remain sane regardless of the combination of services used. 
    
    So, if an engine does not produce volume that matches the db-scale based
    ttsVolumeConstraints, then the engine needs to create a customer converter. 
    
    In the case of Experimental engine, it's volume (it might be configureable) 
    appears to be equivalent to be about 8db (as compared to TTS). Since we
    have to use a different player AND since
    it is almost guaranteed that the voiced text is cached, just set volume
    to fixed 8db and let player handle make the necessary adjustments to the volume.
    
    In other words, create a custom validator which always returns a volume of 1
    (or just don't use the validator and such and hard code it inline).

    
        volume = cls.volumeConstraints.translate_value(
                                        cls.volumeConversionConstraints, volumeDb)
    
    """

    class VolumeConstraintsValidator(ConstraintsValidator):

        # This engine
        def __init__(self, setting_id: str, service_id: str,
                     constraints: Constraints) -> None:
            super().__init__(setting_id, service_id, constraints)

        def set_tts_value(self, value: int | float | str,
                          value_type: ValueType = ValueType.VALUE) -> None:
            """
            Keep value fixed at 5 db
            :param value:
            :param value_type:
            """
            constraints: Constraints = self.constraints
            constraints.setSetting(5, self.service_id)

        def get_tts_value(self, default_value: int | float | str = None,
                          setting_service_id: str = None) -> int | float | str:
            """
            Keep value fixed at 5
            kodi volume
            :return:
            """
            clz = type(self)

            return 5

        def setUIValue(self, ui_value: str) -> None:
            pass

        def getUIValue(self) -> str:
            value, _, _, _ = self.get_tts_value()
            return str(value)

    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = [SoundCapabilities.MP3]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _logger: BasicLogger = None

    # Every setting from settings.xml must be listed here
    # SettingName, default value
    initialized: bool = False

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(clz.service_ID, *args, **kwargs)
        BaseEngineSettings(clz.service_ID)
        if GoogleSettings.initialized:
            return
        GoogleSettings.initialized = True
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        GoogleSettings.init_settings()
        installed: bool = clz.isInstalled()
        SettingsMap.set_is_available(clz.service_ID, Reason.AVAILABLE)

    @classmethod
    def init_settings(cls):
        # Maximum phrase length that a remote engine can convert to speech at a time
        # None indicates that the engine does not download from a remote server
        service_properties: Dict[str, Any]
        service_properties = {'name'                     : cls.displayName,
                              Constants.MAX_PHRASE_LENGTH: 100,
                              Constants.CACHE_SUFFIX     : 'goo'}
        SettingsMap.define_service(ServiceType.ENGINE, cls.engine_id,
                                   service_properties)
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        speedConstraints: Constraints = Constraints(25, 100, 400, False, False, 0.01,
                                                    SettingsProperties.SPEED, 125, 0.25)
        speed_constraints_validator = ConstraintsValidator(SettingsProperties.SPEED,
                                                           cls.engine_id,
                                                           speedConstraints)
        '''
        engine_volume_constraints_validator = cls.VolumeConstraintsValidator(
            SettingsProperties.VOLUME,
            cls.engine_id,
            cls.ttsVolumeConstraints)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOLUME,
                                   engine_volume_constraints_validator)
        '''

        volume_constraints_validator = ConstraintsValidator(
                SettingsProperties.VOLUME,
                cls.engine_id,
                cls.ttsVolumeConstraints)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOLUME,
                                   volume_constraints_validator)

        language_validator: StringValidator
        language_validator = StringValidator(SettingsProperties.LANGUAGE, cls.engine_id,
                                             allowed_values=[], min_length=2,
                                             max_length=5)
        # voice_validator: StringValidator
        # voice_validator = StringValidator(SettingsProperties.VOICE, cls.engine_id,
        #                                   allowed_values=[], min_length=1,
        #                                   max_length=10)
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingsProperties.PIPE, cls.engine_id,
                                       default=False)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, cls.engine_id,
                                        default=True)

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        valid_players: List[str] = [Players.MPLAYER, Players.SFX, Players.WINDOWS,
                                    Players.APLAY,
                                    Players.PAPLAY, Players.AFPLAY, Players.SOX,
                                    Players.MPG321, Players.MPG123,
                                    Players.MPG321_OE_PI, Players.INTERNAL]
        player_validator: StringValidator
        player_validator = StringValidator(SettingsProperties.PLAYER, cls.engine_id,
                                           allowed_values=valid_players,
                                           default=Players.MPLAYER)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.LANGUAGE,
                                   language_validator)
        # SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOICE,
        #                            voice_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PIPE,
                                   pipe_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.SPEED,
                                   speed_constraints_validator)

        pitch_constraints: Constraints = Constraints(50, 50, 50, True, False, 1.0,
                                                     SettingsProperties.PITCH)
        pitch_constraints_validator = ConstraintsValidator(SettingsProperties.PITCH,
                                                           cls.engine_id,
                                                           pitch_constraints)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PITCH,
                                   pitch_constraints_validator)
        # can't change gender

        #  gender_validator = GenderValidator(SettingsProperties.GENDER, cls.engine_id,
        #                                     min_value=Genders.UNKNOWN,
        #                                     max_value=Genders.UNKNOWN,
        #                                     default=Genders.UNKNOWN)
        # gender_validator.set_tts_value(Genders.UNKNOWN)
        SettingsMap.define_setting(cls.engine_id, SettingsProperties.GENDER,
                                   None)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER,
                                   player_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.CACHE_SPEECH,
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
                cls.service_ID)
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[SoundCapabilities.MP3],
                producer_formats=[])
        if len(candidates) > 0:
            return True
