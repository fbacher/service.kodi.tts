from __future__ import annotations  # For union operator |

from common import *

from backends.audio.sound_capabilties import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, NumericValidator,
                                          StringValidator)
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Backends, Genders, PlayerMode, Players
from common.settings import Settings
from common.settings_low_level import SettingsProperties
from common.system_queries import SystemQueries

module_logger = BasicLogger.get_module_logger(module_path=__file__)

'''
class PlayerModeValidator(StringValidator):
    """
        Custom Validator to check for conflicts between the current Player and
        PLAYER_MODE choices presented to the user.
    """

    def get_allowed_values(self) -> List[Tuple[str, bool]] | None:
        """
        Determine which values are allowed and which normally allowed values
        are disabled, due to other settings. Example, a chosen player may not
        support PLAYER_MODE SLAVE_FILE.

        :return: A list of Tuple[<setting>, <enabled | disabled> for every
                 supported value. Those settings which are in conflict with
                 a current setting will be marked disabled (False)
        """
        player_id: str = Settings.get_player_id()
        player = BaseServices.getService(player_id)
        allowed: List[Tuple[str, bool]] = []
        for setting in self.allowed_values:
            if setting not in player.allowed_player_modes():
                allowed.append((setting, False))
            else:
                allowed.append((setting, True))
        return allowed
'''


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

    
    """
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
        super().__init__(GoogleSettings.service_ID, *args, **kwargs)
        BaseEngineSettings(GoogleSettings.service_ID)
        if GoogleSettings.initialized:
            return
        GoogleSettings.initialized = True
        if GoogleSettings._logger is None:
            GoogleSettings._logger = module_logger.getChild(GoogleSettings.__name__)
        GoogleSettings.init_settings()
        installed: bool = GoogleSettings.isInstalled()
        SettingsMap.set_is_available(GoogleSettings.service_ID, Reason.AVAILABLE)

    @classmethod
    def init_settings(cls):
        # Maximum phrase length that a remote engine can convert to speech at a time
        # None indicates that the engine does not download from a remote server
        service_properties: Dict[str, Any]
        service_properties = {Constants.NAME             : cls.displayName,
                              Constants.MAX_PHRASE_LENGTH: 100,
                              Constants.CACHE_SUFFIX     : 'goo'}
        SettingsMap.define_service(ServiceType.ENGINE, cls.service_ID,
                                   service_properties)

        language_validator: StringValidator
        language_validator = StringValidator(SettingsProperties.LANGUAGE, cls.service_ID,
                                             allowed_values=[], min_length=2,
                                             max_length=10)
        # For the most part, google_tts uses the 'top level domain' of the url
        # for the google tts service to imply any dialect on a language. The
        # default is "com". Since each country tends to have its own tld the
        # system works fairly well. Google doesn't document this nor does it
        # work in all situations.
        voice_validator: StringValidator
        voice_validator = StringValidator(SettingsProperties.VOICE, cls.engine_id,
                                          allowed_values=[], min_length=1,
                                          max_length=8, default='com')
        # pipe_validator: BoolValidator
        # pipe_validator = BoolValidator(SettingsProperties.PIPE, cls.service_ID,
        #                                default=True, const=True)
        # cls._logger.debug(f'Boolvalidator value: {pipe_validator.get_tts_value()} '
        #                   f'const: {pipe_validator.is_const()}')
        allowed_player_modes: List[str] = [
            PlayerMode.SLAVE_FILE.value,
            PlayerMode.FILE.value
        ]
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(SettingsProperties.PLAYER_MODE,
                                                cls.service_ID,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.SLAVE_FILE.value)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER_MODE,
                                   player_mode_validator)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, cls.service_ID,
                                        default=True, const=True)

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        players: List[str] = [Players.MPV, Players.MPLAYER,
                              Players.SFX, Players.WINDOWS, Players.APLAY,
                              Players.PAPLAY, Players.AFPLAY, Players.SOX,
                              Players.MPG321, Players.MPG123,
                              Players.MPG321_OE_PI]

        SoundCapabilities.add_service(cls.service_ID, service_types=[ServiceType.ENGINE],
                                      supported_input_formats=[],
                                      supported_output_formats=[SoundCapabilities.MP3])

        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[SoundCapabilities.MP3],
                producer_formats=[])

        cls._logger.debug(f'candidates: {candidates}')
        valid_players: List[str] = []
        for player_id in candidates:
            player_id: str
            if player_id in players and SettingsMap.is_available(player_id):
                valid_players.append(player_id)

        cls._logger.debug(f'valid_players: {valid_players}')

        player_validator: StringValidator
        player_validator = StringValidator(SettingsProperties.PLAYER, cls.service_ID,
                                           allowed_values=valid_players,
                                           default=Players.MPV)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.LANGUAGE,
                                   language_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOICE,
                                   voice_validator)
        # REMOVE gender validator created by BaseServiceSettings
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

    @classmethod
    def available(cls) -> bool:
        engine_output_formats: List[str]
        engine_output_formats = SoundCapabilities.get_output_formats(
                cls.service_ID)
        cls._logger.debug(f'engine_output_formats: {engine_output_formats}')
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=[SoundCapabilities.MP3],
                producer_formats=[])
        cls._logger.debug(f'mp3 player candidates: {candidates}')
        if len(candidates) > 0:
            return True
        return False
