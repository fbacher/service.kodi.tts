# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.settings.i_validators import IStringValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import Services, ServiceType, TTS_Type
from backends.settings.settings_map import Reason, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          GenderValidator, IntValidator, NumericValidator,
                                          SimpleIntValidator, SimpleStringValidator,
                                          StringValidator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import AudioType, Backends, Genders, PlayerMode, Players
from common.settings import Settings
from common.settings_low_level import SettingProp
from backends.settings.service_types import ServiceID

MY_LOGGER = BasicLogger.get_logger(__name__)

'''
class PlayerModeValidator(StringValidator):
    """
        Custom Validator to check for conflicts between the current Player and
        PLAYER_MODE choices presented to the user.
    """

    def get_allowed_values(self) -> List[Tuple[str, bool]] | None:
        """
        Determine which values are allowed and which normally allowed values
        are disabled, due to other settings. Example, a chosen player_key may not
        support PLAYER_MODE SLAVE_FILE.

        :return: A list of Tuple[<setting>, <enabled | disabled> for every
                 supported value. Those settings which are in conflict with
                 a current setting will be marked disabled (False)
        """
        player_id: str = Settings.get_player_key()
        player_key = BaseServices.get_service(player_id)
        allowed: List[Tuple[str, bool]] = []
        for setting in self.allowed_values:
            if setting not in player_key.allowed_player_modes():
                allowed.append((setting, False))
            else:
                allowed.append((setting, True))
        return allowed
'''


class GoogleSettings:
    # Only returns .mp3 files
    ID: str = Backends.GOOGLE_ID
    engine_id = Backends.GOOGLE_ID
    service_id: str = Services.GOOGLE_ID
    service_type: ServiceType = ServiceType.ENGINE
    service_key: ServiceID = ServiceID(service_type, service_id)
    GOOGLE_KEY: ServiceID = ServiceID(service_type, service_id)
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    MAX_PHRASE_KEY: ServiceID = service_key.with_prop(SettingProp.MAX_PHRASE_LENGTH)
    displayName = 'GoogleTTS'

    # Maximum phrase length that a remote engine can convert to speech at a time
    # None indicates that the engine does not download from a remote server
    MAXIMUM_PHRASE_LENGTH: int | None = 10000

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
    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False

    @classmethod
    def config_settings(cls, *args, **kwargs):
        # Define each engine's default settings here, afterward, they can be
        # overridden by this class.
        if GoogleSettings.initialized:
            return
        GoogleSettings.initialized = True
        BaseEngineSettings.config_settings(GoogleSettings.service_key)

        name_validator: StringValidator
        name_validator = StringValidator(service_key=cls.NAME_KEY,
                                         allowed_values=[cls.displayName],
                                         allow_default=False,
                                         const=True
                                         )

        SettingsMap.define_setting(cls.NAME_KEY, name_validator)

        max_phrase_val: SimpleIntValidator
        max_phrase_val = SimpleIntValidator(service_key=cls.MAX_PHRASE_KEY,
                                            value=cls.MAXIMUM_PHRASE_LENGTH,
                                            const=True)
        SettingsMap.define_setting(cls.MAX_PHRASE_KEY, max_phrase_val)

        cls._config()
        available: Reason = GoogleSettings.check_availability()
        SettingsMap.set_is_available(GoogleSettings.service_key, available)

    @classmethod
    def _config(cls):
        # Maximum phrase length that a remote engine can convert to speech at a time
        # None indicates that the engine does not download from a remote server
        #  service_properties: Dict[str, Any]
        #  service_properties = {Constants.NAME             : GoogleSettings.displayName,
        #                        Constants.MAX_PHRASE_LENGTH: 100}
        #  SettingsMap.define_service_properties(GoogleSettings.service_key,
        #                                        service_properties)

        # Can't adjust Pitch except via a player_key that supports it. Not bothering
        # with at this time.

        # Uses default volume_validator defined in base_engine_settings

        # Defines a very loose language validator. Basically it will accept
        # almost any strings. The real work is done by LanguageInfo and
        # SettingsHelper. Should revisit this validator

        lang_svc_key: ServiceID
        lang_svc_key = cls.service_key.with_prop(SettingProp.LANGUAGE)
        language_validator: StringValidator
        language_validator = StringValidator(lang_svc_key,
                                             allowed_values=[], min_length=2,
                                             max_length=10)
        SettingsMap.define_setting(language_validator.service_key,
                                   language_validator)

        # The free GoogleTTS only supplies basic voices which are determined
        # by language and country code. In short, the voice choices are
        # essentially the locale (en-us, en-gb, etc.).Not all combinations are
        # supported.
        #
        # For the most part, google_tts uses the 'top level domain' of the url
        # for the google tts service to imply any dialect on a language. The
        # default is "com". Since each country tends to have its own tld the
        # system works fairly well. Google doesn't document this nor does it
        # work in all situations.

        voice_validator: StringValidator
        voice_validator = StringValidator(cls.service_key.with_prop(SettingProp.VOICE),
                                          allowed_values=[], min_length=1,
                                          max_length=8, default='com')

        SettingsMap.define_setting(voice_validator.service_key,
                                   voice_validator)

        # Can't support PlayerMode.PIPE: 1) Google does download mp3, but the
        # response time would be awful. 2) You could simulate pipe mode for the
        # cached files, but it would add extra cpu. 3) Not worth it

        allowed_player_modes: List[str] = [
            PlayerMode.SLAVE_FILE.value,
            PlayerMode.FILE.value
        ]
        tmp_key: ServiceID
        tmp_key = cls.service_key.with_prop(SettingProp.PLAYER_MODE)

        MY_LOGGER.debug(f'player_mode key: {tmp_key}')
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(tmp_key,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.SLAVE_FILE.value)
        SettingsMap.define_setting(player_mode_validator.service_key,
                                   player_mode_validator)
        Settings.set_current_output_format(GoogleSettings.service_key, AudioType.MP3)
        SoundCapabilities.add_service(GoogleSettings.service_key,
                                      service_types=[ServiceType.ENGINE],
                                      supported_input_formats=[],
                                      supported_output_formats=[AudioType.MP3])

        consumer_formats: List[AudioType] = [AudioType.MP3]
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER,
                consumer_formats=consumer_formats,
                producer_formats=[])

        e_pm_val: IStringValidator
        e_pm_val = SettingsMap.get_validator(cls.service_key.with_prop(
                SettingProp.PLAYER_MODE))
        MY_LOGGER.debug(f'player_val_key: {e_pm_val}')
        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        players: List[str] = [Players.MPV, Players.MPLAYER,
                              Players.SFX, Players.WINDOWS, Players.APLAY,
                              Players.PAPLAY, Players.AFPLAY, Players.SOX,
                              Players.MPG321, Players.MPG123,
                              Players.MPG321_OE_PI]

        MY_LOGGER.debug(f'candidates: {candidates}')
        valid_players: List[str] = []
        for player_id in candidates:
            player_id: str
            player_key: ServiceID
            player_key = ServiceID(ServiceType.PLAYER, player_id)
            if player_id in players and SettingsMap.is_available(player_key):
                valid_players.append(player_id)

        MY_LOGGER.debug(f'valid_players: {valid_players}')
        player_validator: StringValidator
        player_validator = StringValidator(cls.service_key.with_prop(SettingProp.PLAYER),
                                           allowed_values=valid_players,
                                           default=Players.MPV)
        SettingsMap.define_setting(player_validator.service_key,
                                   player_validator)

        cache_validator: BoolValidator
        cache_validator = BoolValidator(
            cls.service_key.with_prop(SettingProp.CACHE_SPEECH),
            default=True, const=True)

        SettingsMap.define_setting(cache_validator.service_key,
                                   cache_validator)

        cache_service_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_PATH)
        cache_path_val: SimpleStringValidator
        cache_path_val = SimpleStringValidator(cache_service_key,
                                               value=SettingProp.CACHE_PATH_DEFAULT)
        SettingsMap.define_setting(cache_path_val.service_key,
                                   cache_path_val)

        cache_suffix_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix: str = Backends.ENGINE_CACHE_CODE[Backends.GOOGLE_ID]

        cache_suffix_val: SimpleStringValidator
        cache_suffix_val = SimpleStringValidator(cache_suffix_key,
                                                 value=cache_suffix)
        SettingsMap.define_setting(cache_suffix_val.service_key,
                                   cache_suffix_val)

        '''
        gender_validator = GenderValidator(SettingProp.GENDER,
                                           GoogleSettings.setting_id,
                                           min_value=Genders.FEMALE,
                                           max_value=Genders.UNKNOWN,
                                           default=Genders.UNKNOWN)
        SettingsMap.define_setting(GoogleSettings.setting_id, SettingProp.GENDER,
                                   gender_validator)
        gender_visible: BoolValidator
        gender_visible = BoolValidator(
                SettingProp.GENDER_VISIBLE, GoogleSettings.setting_id,
                default=True)
        SettingsMap.define_setting(GoogleSettings.setting_id,
                                   SettingProp.GENDER_VISIBLE,
                                   gender_visible)
        '''

    @classmethod
    def check_availability(cls) -> Reason:
        availability: Reason = Reason.AVAILABLE
        if not cls.isSupportedOnPlatform():
            availability = Reason.NOT_SUPPORTED
        if not cls.isInstalled():
            availability = Reason.NOT_AVAILABLE
        elif not cls.is_available():
            availability = Reason.BROKEN
        SettingsMap.set_is_available(GoogleSettings.service_key, availability)
        return availability

    @staticmethod
    def isSupportedOnPlatform() -> bool:
        return True

    @staticmethod
    def isInstalled() -> bool:
        installed: bool = False
        if GoogleSettings.isSupportedOnPlatform():
            installed = True
        return installed

    @staticmethod
    def is_available() -> bool:
        return True
