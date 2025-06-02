# coding=utf-8
from __future__ import annotations  # For union operator |

from io import BytesIO

from backends.settings.setting_properties import SettingType
from gtts import gTTS

from backends.engines.google_downloader import MyGTTS
from backends.settings.i_validators import IStringValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import (BaseEngineSettings)
from backends.settings.service_types import (PlayerType, ServiceKey, Services,
                                             ServiceType,
                                             TTS_Type)
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (BoolValidator,
                                          SimpleIntValidator, SimpleStringValidator,
                                          StringValidator)
from common.config_exception import UnusableServiceException
from common.constants import Constants
from common.logger import *
from common.message_ids import MessageId
from common.service_status import Progress, ServiceStatus, StatusType
from common.setting_constants import AudioType, Backends, Genders, PlayerMode, Players
from common.settings import Settings
from common.settings_low_level import SettingProp
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class GoogleSettings:
    # Only returns .mp3 files
    ID: str = Backends.GOOGLE_ID
    engine_id = Backends.GOOGLE_ID
    service_id: str = Services.GOOGLE_ID
    service_type: ServiceType = ServiceType.ENGINE
    service_key: ServiceID = ServiceKey.GOOGLE_KEY
    GOOGLE_KEY: ServiceID = service_key
    NAME_KEY: ServiceID = service_key.with_prop(SettingProp.SERVICE_NAME)
    MAX_PHRASE_KEY: ServiceID = service_key.with_prop(SettingProp.MAX_PHRASE_LENGTH)
    displayName: str = MessageId.ENGINE_GOOGLE.get_msg()

    # Maximum phrase length that a remote engine can convert to speech at a time
    # None indicates that the engine does not download from a remote server
    MAXIMUM_PHRASE_LENGTH: int | None = 100

    """
    In an attempt to bring some consistency between the various players, engines and 
    transcoders, standard "TTS" constraints are defined which every engine, player,
    transcoder, etc. is to convert to/from. Hopefully this will help these settings
    to remain sane regardless of the combination of services used. 
    
    So, if an engine does not produce volume that matches the db-scale based
    ttsVolumeConstraints, then the engine needs to create a customer transcoder. 
    
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
    _service_status: ServiceStatus = ServiceStatus()

    @classmethod
    def config_settings(cls, *args, **kwargs):
        # Define each engine's default settings here, afterward, they can be
        # overridden by this class.
        if GoogleSettings.initialized:
            return

        # Basic checks that don't depend on config
        cls.check_is_supported_on_platform()
        cls.check_is_installed()
        if cls._service_status.status != Status.OK:
            raise UnusableServiceException(cls.service_key,
                                           cls._service_status,
                                           msg='')
        cls.check_is_available()
        cls.check_is_usable()
        cls.is_usable()
        GoogleSettings.initialized = True
        BaseEngineSettings.config_settings(cls.service_key,
                                           settings=[])

        name_validator: SimpleStringValidator
        name_validator = SimpleStringValidator(service_key=cls.NAME_KEY,
                                               value=cls.displayName,
                                               const=True,
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=True)

        max_phrase_val: SimpleIntValidator
        max_phrase_val = SimpleIntValidator(service_key=cls.MAX_PHRASE_KEY,
                                            value=cls.MAXIMUM_PHRASE_LENGTH,
                                            const=True,
                                            define_setting=True,
                                            service_status=StatusType.OK,
                                            persist=True)
        cls._config()

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
                                             max_length=10,
                                             define_setting=True,
                                             service_status=StatusType.OK,
                                             persist=True)

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
                                          max_length=8, default='com',
                                          define_setting=True,
                                          service_status=StatusType.OK,
                                          persist=True)

        # Can't support PlayerMode.PIPE: 1) Google does download mp3, but the
        # response time would be awful. 2) You could simulate pipe mode for the
        # cached files, but it would add extra cpu. 3) Not worth it

        allowed_player_modes: List[str] = [
            PlayerMode.SLAVE_FILE.value,
            PlayerMode.FILE.value
        ]
        tmp_key: ServiceID
        tmp_key = cls.service_key.with_prop(SettingProp.PLAYER_MODE)

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'player_mode key: {tmp_key}')
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(tmp_key,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.SLAVE_FILE.value,
                                                define_setting=True,
                                                service_status=StatusType.OK,
                                                persist=True)

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
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'candidates: {candidates}')

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        players: List[str] = [Players.MPV, Players.MPLAYER,
                              Players.SFX, Players.WINDOWS, Players.APLAY,
                              Players.PAPLAY, Players.AFPLAY, Players.SOX,
                              Players.MPG321, Players.MPG123,
                              Players.MPG321_OE_PI]

        valid_players: List[str] = []
        for player_id in candidates:
            player_id: str
            player_key: ServiceID
            player_key = ServiceID(ServiceType.PLAYER, player_id, SettingProp.SERVICE_ID)
            if player_id in players and SettingsMap.is_available(player_key):
                valid_players.append(player_id)

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'valid_players: {valid_players}')
        player_validator: StringValidator
        player_validator = StringValidator(cls.service_key.with_prop(SettingProp.PLAYER),
                                           allowed_values=valid_players,
                                           default=Players.MPV,
                                           define_setting=True,
                                           service_status=StatusType.OK,
                                           persist=True)
        val: IStringValidator
        val = SettingsMap.get_validator(cls.service_key.with_prop(SettingProp.PLAYER))
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'enabled allowed_values: '
                            f'{val.get_allowed_values(enabled=True)}'
                            f' default player: {val.default}')

        cache_speech_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SPEECH)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(cache_speech_key,
                                        default=True, const=True,
                                        define_setting=True,
                                        service_status=StatusType.OK,
                                        persist=True)

        cache_service_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_PATH)
        cache_path_val: SimpleStringValidator
        cache_path_val = SimpleStringValidator(cache_service_key,
                                               value=SettingProp.CACHE_PATH_DEFAULT,
                                               define_setting=True,
                                               service_status=StatusType.OK,
                                               persist=True)

        cache_suffix_key: ServiceID = cls.service_key.with_prop(SettingProp.CACHE_SUFFIX)
        cache_suffix: str = Backends.ENGINE_CACHE_CODE[Backends.GOOGLE_ID]

        cache_suffix_val: SimpleStringValidator
        cache_suffix_val = SimpleStringValidator(cache_suffix_key,
                                                 value=cache_suffix,
                                                 define_setting=True,
                                                 service_status=StatusType.OK,
                                                 persist=True)

    @classmethod
    def check_is_supported_on_platform(cls) -> None:
        if cls._service_status.progress == Progress.START:
            supported: bool = (SystemQueries.isLinux() or SystemQueries.isWindows()
                               or SystemQueries.isOSX())
            cls._service_status.progress = Progress.SUPPORTED
            if not supported:
                cls._service_status.status = Status.FAILED
                cls._service_status.status_summary = StatusType.NOT_ON_PLATFORM
                SettingsMap.define_setting(cls.service_key,
                                           setting_type=SettingType.STRING_TYPE,
                                           service_status=StatusType.NOT_ON_PLATFORM,
                                           validator=None)

    @classmethod
    def check_is_installed(cls) -> None:
        # Don't have a test for installed, just move on to available
        if cls._service_status.progress == Progress.SUPPORTED:
            if cls._service_status.status == Status.OK:
                cls._service_status.progress = Progress.INSTALLED
            else:
                cls._service_status.status_summary = StatusType.NOT_FOUND
                SettingsMap.define_setting(cls.service_key,
                                           setting_type=SettingType.STRING_TYPE,
                                           service_status=StatusType.NOT_FOUND,
                                           validator=None)

    @classmethod
    def check_is_available(cls) -> None:
        """
        Determines if the engine is functional. The test is only run once and
        remembered.

        :return:
        """
        if (cls._service_status.progress == Progress.INSTALLED
                and cls._service_status.status == Status.OK):
            # Test requires actually using Google TTS. Delay until on first
            # use. Add code to mark as BROKEN in engine.
            cls._service_status.progress = Progress.AVAILABLE
        else:
            cls._service_status.status = Status.FAILED
            cls._service_status.status_summary = StatusType.BROKEN
            SettingsMap.define_setting(cls.service_key,
                                       setting_type=SettingType.STRING_TYPE,
                                       service_status=StatusType.BROKEN,
                                       validator=None)

    @classmethod
    def check_is_usable(cls) -> None:
        """
        Determine if the engine is usable in this environment. Perhaps there is
        no player that can work with this engine available.
        :return None:
        """
        # Google TTS only produces .mpg files. If no player is available, we
        # are dead.
        if cls._service_status.progress == Progress.AVAILABLE:
            success: Status = cls._service_status.status
            if success == Status.OK:
                byte_stream: BinaryIO | None = None
                byte_buffer: BytesIO = BytesIO()
                status: StatusType = StatusType.BROKEN
                try:
                    my_gTTS = gTTS('test',
                                   lang='en',
                                   slow=False,
                                   lang_check=False,
                                   tld='com',
                                   timeout=5.0
                                   #  pre_processor_funcs=[
                                   #     pre_processors.tone_marks,
                                   #     pre_processors.end_of_line,
                                   #     pre_processors.abbreviations,
                                   #     pre_processors.word_sub,
                                   # ],
                                   # tokenizer_func=Tokenizer(
                                   #         [
                                   #             tokenizer_cases.tone_marks,
                                   #             tokenizer_cases.period_comma,
                                   #             tokenizer_cases.colon,
                                   #             tokenizer_cases.other_punctuation,
                                   #         ]
                                   # ).run,
                                   )
                    my_gTTS.write_to_fp(byte_buffer)
                    x = byte_buffer.getvalue()
                    MY_LOGGER.debug(f'Size of test: {len(x)} bytes')
                    if len(x) > 4000:
                        status = StatusType.OK
                except Exception:
                    MY_LOGGER.exception('Blew up in gtts')
                    status = StatusType.BROKEN
                SettingsMap.define_setting(cls.service_key,
                                           setting_type=SettingType.STRING_TYPE,
                                           service_status=status,
                                           validator=None)

    @classmethod
    def is_usable(cls) -> bool:
        """
        Determines if there are any known reasons that this service is not
        functional. Runs the check_ methods to determine the result.

        :return True IFF functional:
        :raises UnusableServiceException: when this service is not functional
        :raises ValueError: when called before this module fully initialized.
        """
        return SettingsMap.is_available(cls.service_key)
