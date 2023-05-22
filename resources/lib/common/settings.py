# -*- coding: utf-8 -*-
import traceback

from backends.i_tts_backend_base import ITTSBackendBase
from backends.backend_info_bridge import BackendInfoBridge
import copy
import time
from enum import Enum
import xbmcaddon
from xbmcaddon import Settings as KodiSettings

from common.critical_settings import CriticalSettings
from common.constants import Constants
from common.exceptions import NotReadyException
from kutils.kodiaddon import Addon
from common.logger import *
from common.settings_bridge import ISettings, SettingsBridge
from typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SettingType(Enum):
    BOOLEAN_TYPE = 'BOOLEAN_TYPE'
    BOOLEAN_LIST_TYPE = 'BOOLEAN_LIST_TYPE'
    FLOAT_TYPE = 'FLOAT_TYPE'
    FLOAT_LIST_TYPE = 'FLOAT_LIST_TYPE'
    INTEGER_TYPE = 'INTEGER_TYPE'
    INTEGER_LIST_TYPE = 'INTEGER_LIST_TYPE'
    STRING_TYPE = 'STRING_TYPE'
    STRING_LIST_TYPE = 'STRING_LIST_TYPE'


class CurrentCachedSettings:
    _current_settings: Dict[str, Union[Any, None]] = {}
    _current_settings_changed: bool = False
    _current_settings_update_begin: float = None
    _logger: BasicLogger
    _logger = module_logger.getChild("CurrentCachedSettings")

    @classmethod
    def set_setting(cls, setting_id: str, value: Any = None) -> bool:
        changed: bool = False
        if cls._current_settings.get(setting_id) != value:
            changed = True
            cls._current_settings_changed = True
            if cls._current_settings_update_begin is None:
                cls._current_settings_update_begin = time.time()
            cls._current_settings[setting_id] = value

        return changed

    @classmethod
    def set_settings(cls, settings_to_backup: Dict[str, Any]) -> None:
        cls._current_settings = copy.deepcopy(settings_to_backup)
        cls._logger.debug(f'settings_to_backup len: {len(settings_to_backup)}'
                          f' current_settings len: {len(cls._current_settings)}')
        cls._current_settings_changed = True
        if cls._current_settings_update_begin is None:
            cls._current_settings_update_begin = time.time()

    @classmethod
    def backup(cls) -> None:
        PreviousCachedSettings.backup(cls._current_settings,
                                      cls._current_settings_changed,
                                      cls._current_settings_update_begin)

    @classmethod
    def restore_settings(cls) -> None:
        previous_settings: Dict[str, Any]
        previous_settings_changed: bool
        previous_settings_update_begin: float
        previous_settings, previous_settings_changed, previous_settings_update_begin = \
            PreviousCachedSettings.get_settings()
        cls._current_settings = copy.deepcopy(previous_settings)
        cls._logger.debug(f'previous_settings len: {len(previous_settings)}'
                          f' current_settings len: {len(cls._current_settings)}')
        cls._current_settings_changed = previous_settings_changed
        cls._current_settings_update_begin = previous_settings_update_begin

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        return cls._current_settings

    @classmethod
    def get_setting(cls, setting_id: str, default_value: Any) -> Any:
        '''
        throws KeyError
        '''
        value = cls._current_settings[setting_id]
        if value is None:
            value = default_value
        #  cls._logger.debug(f'setting_id: {setting_id} value: {value}')
        return value

    @classmethod
    def is_empty(cls) -> bool:
        return not cls._current_settings


class PreviousCachedSettings:
    # Backup copy of settings while _current_settings is being changed

    _previous_settings: Dict[str, Union[Any, None]] = {}
    _previous_settings_changed: bool = False
    _previous_settings_update_begin: float | None = None

    @classmethod
    def backup(cls, settings_to_backup: Dict[str, Any],
               settings_changed: bool,
               settings_update_begin: float) -> None:
        cls.clear()
        cls._previous_settings = copy.deepcopy(settings_to_backup)
        cls._previous_settings_update_begin = settings_update_begin
        cls._previous_settings_changed = settings_changed

    @classmethod
    def clear(cls) -> None:
        cls._previous_settings.clear()
        cls._previous_settings_changed: bool = False
        cls._previous_settings_update_begin = None

    @classmethod
    def get_settings(cls) -> Tuple[Dict[str, Any], bool, float]:
        return (cls._previous_settings, cls._previous_settings_changed,
                cls._previous_settings_update_begin)

    @classmethod
    def get_setting(cls, setting_id: str, default_value: Any) -> Any:
        return cls._previous_settings.get(setting_id, default_value)


class Settings(ISettings):
    # TOP LEVEL SETTINGS
    _addon_singleton: Addon = None
    KODI_SETTINGS: xbmcaddon.Addon = None
    kodi_settings: KodiSettings = None

    ADDONS_MD5: Final[str] = 'addons_MD5'
    API_KEY: Final[str] = 'api_key'
    AUTO_ITEM_EXTRA: Final[str] = 'auto_item_extra'

    # int seconds Time to wait before saying something extra in seconds

    AUTO_ITEM_EXTRA_DELAY: Final[str] = 'auto_item_extra_delay'
    BACKEND: Final[str] = 'backend'
    # BACKEND_DEFAULT: Final[str] = ISettings.BACKEND_DEFAULT
    BACKGROUND_PROGRESS_INTERVAL: Final[str] = 'background_progress_interval'
    CACHE_PATH: Final[str] = 'cache_path'
    CACHE_EXPIRATION_DAYS: Final[str] = 'cache_expiration_days'
    CACHE_SPEECH: Final[str] = 'cache_speech'
    CAPITAL_RECOGNITION: Final[str] = 'capital_recognition'
    # DEBUG_LOGGING: Final[str] = 'debug_logging'
    DEBUG_LOG_LEVEL: Final[str] = 'log_level'
    DISABLE_BROKEN_BACKENDS: Final[str] = 'disable_broken_backends'
    # TODO: Change settings like output_via_espeak to be output <string value>
    # ENGINE_SPEAKS: Final[str] = 'engine_speak'  # Voicing engine also speaks
    EXTERNAL_COMMAND: Final[str] = 'EXTERNAL_COMMAND'
    GENDER: Final[str] = 'gender'
    GENDER_VISIBLE: Final[str] = 'gender_visible'
    GUI: Final[str] = 'gui'
    LANGUAGE: Final[str] = 'language'
    MODULE: Final[str] = 'module'
    OUTPUT_VIA: Final[str] = 'output_via'
    OUTPUT_VISIBLE: Final[str] = 'output_visible'
    OVERRIDE_POLL_INTERVAL: Final[str] = 'override_poll_interval'
    PIPE: Final[str] = 'pipe'  # Engine to pipe speech to a player
    PITCH: Final[str] = 'pitch'
    PLAYER: Final[str] = 'player'  # Specifies the player
    PLAYER_VOLUME: Final[str] = 'player_volume'
    PLAYER_PITCH: Final[str] = 'player_pitch'
    PLAYER_SPEED: Final[str] = 'player_speed'
    POLL_INTERVAL: Final[str] = 'poll_interval'
    PUNCTUATION: Final[str] = 'punctuation'
    READER_OFF: Final[str] = 'reader_off'
    REMOTE_PITCH: Final[str] = 'remote_pitch'
    REMOTE_SERVER: Final[str] = 'remote_server'
    REMOTE_SPEED: Final[str] = 'remote_speed'
    REMOTE_VOLUME: Final[str] = 'remote_volume'
    SETTINGS_BEING_CONFIGURED: Final[str] = 'settings_being_configured'
    SETTINGS_DIGEST: Final[str] = 'settings_digest'
    SETTINGS_LAST_CHANGED: Final[str] = 'settings_last_changed'
    SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: Final[
        str] = 'speak_background_progress_during_media'
    SPEAK_BACKGROUND_PROGRESS: Final[str] = 'speak_background_progress'
    SPEAK_LIST_COUNT: Final[str] = 'speak_list_count'
    SPEAK_ON_SERVER: Final[str] = 'speak_on_server'
    SPEAK_VIA_KODI: Final[str] = 'speak_via_kodi'
    SPEECH_DISPATCHER: Final[str] = 'Speech-Dispatcher'
    SPEED: Final[str] = 'speed'
    SPEED_ENABLED: Final[str] = 'speed_enabled'
    SPEED_VISIBLE: Final[str] = 'speed_visible'
    SPELLING: Final[str] = 'spelling'
    TTSD_HOST: Final[str] = 'ttsd_host'
    TTSD_PORT: Final[str] = 'ttsd_port'
    USE_AOSS: Final[str] = 'use_aoss'
    USE_TEMPFS: Final[str] = 'use_tmpfs'
    VERSION: Final[str] = 'version'
    VOICE: Final[str] = 'voice'
    VOICE_TTSD: Final[str] = 'voice_ttsd'
    VOICE_VISIBLE: Final[str] = 'voice_visible'
    VOLUME: Final[str] = 'volume'
    VOLUME_VISIBLE: Final[str] = 'volume_visible'

    API_KEY_DEFAULT: Final[str] = ''
    CACHE_EXPIRATION_DEFAULT: Final[int] = 365
    CACHE_SPEECH_DEFAULT: Final[bool] = False
    ENGINE_SPEEK_DEFAULT = None
    GENDER_DEFAULT: Final[str] = 'none'
    LANGUAGE_DEFAULT: Final[str] = 'none'
    PIPE_DEFAULT = None
    PITCH_DEFAULT = None
    SPEED_DEFAULT = None
    VOICE_DEFAULT: Final[str] = 'none'
    VOLUME_DEFAULT = None

    TOP_LEVEL_SETTINGS: List[str] = [
        AUTO_ITEM_EXTRA,
        AUTO_ITEM_EXTRA_DELAY,
        BACKEND,
        BACKGROUND_PROGRESS_INTERVAL,
        DISABLE_BROKEN_BACKENDS,
        SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
        SPEAK_BACKGROUND_PROGRESS,
        CACHE_PATH,
        CACHE_EXPIRATION_DAYS,
        ADDONS_MD5,
        EXTERNAL_COMMAND,
        # DEBUG_LOGGING,  # Boolean needed to toggle visibility
        DEBUG_LOG_LEVEL,  # Merge into Logging, get rid of verbose_logging, etc
        GENDER,
        GENDER_VISIBLE,
        GUI,
        SPEECH_DISPATCHER,
        OUTPUT_VIA,
        OUTPUT_VISIBLE,
        OVERRIDE_POLL_INTERVAL,
        POLL_INTERVAL,
        READER_OFF,
        SETTINGS_BEING_CONFIGURED,
        SETTINGS_DIGEST,
        SETTINGS_LAST_CHANGED,
        SPEAK_LIST_COUNT,
        SPEAK_VIA_KODI,
        TTSD_HOST,
        TTSD_PORT,
        USE_TEMPFS,
        VERSION,
        VOICE_VISIBLE,
        VOLUME_VISIBLE
    ]

    # Logically, ENGINE_SPEAK and PIPE should be combined into an enum of
    # three values instructing the engine what to do with speech that it produces:
    #   WRITE_TO_FILE, SPEAK (engine itself speaks), PIPE (to some other player).
    #
    # However, we have two settings: ENGINE_SPEAK and PIPE. ENGINE_SPEAK takes
    # precedence. If PIPE is set to 'pipe', then it is considered True, else
    # the engine is to write to file.

    UNKNOWN_VALUE = 'unknown'

    # Most settings are associated with a player or a voice engine. Such
    # settings have the player or engine name appended to the setting name.
    #
    # Some settings are not associated with a player or engine. The setting
    # names are not modified. Such settings are referred to here as
    # 'top_level_settings'

    ALL_SETTINGS: List[str] = [
        BACKEND,   # Leave this as the FIRST setting
        ADDONS_MD5,
        API_KEY,
        AUTO_ITEM_EXTRA,
        # int seconds Time to wait before saying something extra in seconds
        AUTO_ITEM_EXTRA_DELAY,
        BACKGROUND_PROGRESS_INTERVAL,
        CACHE_PATH,
        CACHE_EXPIRATION_DAYS,
        CACHE_SPEECH,
        CAPITAL_RECOGNITION,
        # DEBUG_LOGGING,
        DEBUG_LOG_LEVEL,
        DISABLE_BROKEN_BACKENDS,
        EXTERNAL_COMMAND,
        GENDER,
        GENDER_VISIBLE,
        GUI,
        LANGUAGE,
        MODULE,
        OUTPUT_VIA,
        OUTPUT_VISIBLE,
        OVERRIDE_POLL_INTERVAL,
        PIPE,
        PITCH,
        PLAYER,
        PLAYER_VOLUME,
        PLAYER_PITCH,
        PLAYER_SPEED,
        POLL_INTERVAL,
        PUNCTUATION,
        READER_OFF,
        REMOTE_PITCH,
        REMOTE_SPEED,
        REMOTE_VOLUME,
        SETTINGS_DIGEST,
        SETTINGS_BEING_CONFIGURED,
        SETTINGS_LAST_CHANGED,
        SPEECH_DISPATCHER,
        SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
        SPEAK_BACKGROUND_PROGRESS,
        SPEAK_LIST_COUNT,
        SPEAK_ON_SERVER,
        SPEAK_VIA_KODI,
        SPEED,
        SPEED_ENABLED,
        SPEED_VISIBLE,
        SPELLING,
        TTSD_HOST,
        TTSD_PORT,
        USE_AOSS,
        USE_TEMPFS,
        VERSION,
        VOICE,
        VOICE_VISIBLE,
        VOLUME
    ]

    _settings_types: Dict[str, SettingType] = {}

    # The built-in Kodi settings configuration does not work well with this
    # add-on because the kodi config gui is unable to:
    #  - Adjusting the audio to reflect the changes as they occur
    #  - The UI and it's voicing does not work well with some of the
    #    complex interactions between settings
    #
    # Therefore we have our own settings gui. To support this, this settings
    # module provides the ability to make changes to a local copy of settings
    # providing the ability to roll-back or commit them atomically when the user
    # is happy with the changes.
    #
    # Each backend validates changes to settings before any changes are made here

    # working copy of settings. Changes must be validated before changes allowed
    # here

    _current_backend: str  # = BACKEND_DEFAULT
    _logger: BasicLogger = None

    @staticmethod
    def get_addon() -> Addon:
        '''

        :return:
        '''

        if Settings._addon_singleton is None:
            # Protect against case where Random Trailers is partially
            # installed, such that script.video.randomtrailers doesn't
            # exist
            try:
                Settings._addon_singleton = Addon(Constants.ADDON_ID)
            except Exception:
                pass

        return Settings._addon_singleton

    @staticmethod
    def on_settings_changed() -> None:
        '''

        :return:
        '''
        # Settings.load_settings()

    @classmethod
    def save_settings(cls) -> None:
        '''

        :return:
        '''
        try:
            CurrentCachedSettings.backup()
            cls._logger.debug('Backed up settings')
        except Exception:
            cls._logger.exception("")

    @classmethod
    def cancel_changes(cls) -> None:
        # get lock
        # set SETTINGS_BEING_CONFIGURED, SETTINGS_LAST_CHANGED
        #
        CurrentCachedSettings.restore_settings()
        cls._logger.debug('TRACE Cancel changes')

    @staticmethod
    def get_changed_settings(settings_to_check: List[str]) -> List[str]:
        '''

        :param settings_to_check:
        :return:
        '''
        Settings._logger.debug('entered')
        changed_settings = []
        for setting_id in settings_to_check:
            previous_value = PreviousCachedSettings.get_setting(setting_id, None)
            try:
                current_value = Settings.get_addon().setting(setting_id)
            except Exception:
                current_value = previous_value

            if previous_value != current_value:
                changed = True
                if module_logger.isEnabledFor(DEBUG):
                    Settings._logger.debug(f'setting changed: {setting_id} '
                                           f'previous_value: {previous_value} '
                                           f'current_value: {current_value}')
            else:
                changed = False

            if changed:
                changed_settings.append(setting_id)

        return changed_settings

    @classmethod
    def type_and_validate_settings(cls, full_setting_id: str, value: Any | None) -> Tuple[
        bool, Type]:
        '''

        '''
        setting_id: str = ""
        backend_id: str = None
        type_error: bool = False
        engine: ITTSBackendBase = None
        expected_type: str = ''
        if full_setting_id not in cls.TOP_LEVEL_SETTINGS:
            backend_id, setting_id = cls.splitSettingId(full_setting_id)
            engine = BackendInfoBridge.getBackend(backend_id)
        else:
            setting_id = full_setting_id

        if engine is not None:
            if not engine.isSettingSupported(setting_id):
                cls._logger.debug(
                        f'TRACE Setting {setting_id} NOT supported for {backend_id}')
        PROTO_LIST_BOOLS: List[bool] = [True, False]
        PROTO_LIST_FLOATS: List[float] = [0.7, 8.2]
        PROTO_LIST_INTEGERS: List[int] = [1, 57]
        PROTO_LIST_STRINGS: List[str] = ['a', 'b']
        try:
            match cls._settings_types[setting_id]:
                case SettingType.BOOLEAN_TYPE:
                    expected_type = 'bool'
                    if not isinstance(value, bool):
                        type_error = True
                case SettingType.BOOLEAN_LIST_TYPE:
                    expected_type = 'List[bool]'
                    if not isinstance(value, type(PROTO_LIST_BOOLS)):
                        type_error = True
                case SettingType.FLOAT_TYPE:
                    expected_type = 'float'
                    if not isinstance(value, float):
                        type_error = True
                case SettingType.FLOAT_LIST_TYPE:
                    expected_type = 'List[float]'
                    if not isinstance(value, type(PROTO_LIST_FLOATS)):
                        type_error = True
                case SettingType.INTEGER_TYPE:
                    expected_type = 'int'
                    if not isinstance(value, int):
                        type_error = True
                case SettingType.INTEGER_LIST_TYPE:
                    expected_type = 'List[int]'
                    if not isinstance(value, type(PROTO_LIST_INTEGERS)):
                        type_error = True
                case SettingType.STRING_TYPE:
                    expected_type = 'str'
                    if not isinstance(value, str):
                        type_error = True
                case SettingType.STRING_LIST_TYPE:
                    expected_type = 'List[str'
                    if not isinstance(value, type(PROTO_LIST_STRINGS)):
                        type_error = True
        except TypeError:
            cls._logger.exception(
                    f'TRACE: failed to find type of setting: {full_setting_id}. '
                    f'Probably not defined in resources/settings.xml')
        except Exception:
            cls._logger.exception(
                    f'TRACE: Bad setting_id: {setting_id}')
        if type_error:
            cls._logger.debug(f'TRACE: incorrect type for setting: {full_setting_id} '
                              f'Expected {expected_type} got {str(type(value))}')
        return type_error, type(value)

    @classmethod
    def load_settings(cls) -> None:
        '''
        Load ALL of the settings for the current backend.
        Settings from multiple backends can be in the cache simultaneously
        Settings not supported by a backend are not read and not put into
        the cache. The settings.xml can have orphaned settings as long as
        kodi allows it, based on the rules in the addon's settings.xml definition
        file.

        Ignore any other changes to settings until finished
        '''

        cls._logger.debug('TRACE load_settings')
        new_settings: Dict[str, Any] = {}
        cls.kodi_settings = xbmcaddon.Addon("service.kodi.tts").getSettings()
        # Get Lock
        backend_id: str = cls.load_setting(Settings.BACKEND)
        if backend_id is None:
            backend_id = Settings.BACKEND_DEFAULT

        for setting_id in cls.ALL_SETTINGS:
            key: str = setting_id
            value: Any | None
            if setting_id not in cls.TOP_LEVEL_SETTINGS:
                value = cls.load_setting(setting_id, backend_id)
            else:
                value = cls.load_setting(setting_id)
            if value is not None:
                new_settings[key] = value

        cls._current_backend = backend_id

        # validate_settings new_settings
        CurrentCachedSettings.set_settings(new_settings)
        # release lock
        # Notify

    @classmethod
    def load_setting(cls, setting_id: str, backend_id: str = None) -> Any | None:
        key: str = setting_id
        engine: ITTSBackendBase | None = None
        if backend_id is not None:
            key = setting_id + '.' + backend_id
            try:
                engine = BackendInfoBridge.getBackend(backend_id)
                if engine is None:
                    backend_id = cls._current_backend
                    engine = BackendInfoBridge.getBackend(backend_id)

                if not engine.isSettingSupported(setting_id):
                    cls._logger.debug(
                            f'Setting {setting_id} NOT supported for {backend_id}')
                    return None
            except NotReadyException:
                engine = None
                cls._logger.debug(f'NotReady to validate engine setting. Omitting '
                                  f'{setting_id} for now')
        value: Any | None = None
        try:
            match cls._settings_types[setting_id]:
                case SettingType.BOOLEAN_TYPE:
                    value = cls.kodi_settings.getBool(key)
                case SettingType.BOOLEAN_LIST_TYPE:
                    value = cls.kodi_settings.getBoolList(key)
                case SettingType.FLOAT_TYPE:
                    value = cls.kodi_settings.getNumber(key)
                case SettingType.FLOAT_LIST_TYPE:
                    value = cls.kodi_settings.getNumberList(key)
                case SettingType.INTEGER_TYPE:
                    value = cls.kodi_settings.getInt(key)
                case SettingType.INTEGER_LIST_TYPE:
                    value = cls.kodi_settings.getIntList(key)
                case SettingType.STRING_TYPE:
                    value = cls.kodi_settings.getString(key)
                case SettingType.STRING_LIST_TYPE:
                    value = cls.kodi_settings.getStringList(key)
            cls._logger.debug(
                    f'found key: {key} value: {value}')
        except KeyError:
            cls._logger.exception(
                    f'failed to find setting key: {key}. '
                    f'Probably not defined in resources/settings.xml')
        except TypeError:
            cls._logger.exception(f'failed to get type of setting: {key} ')

        if value is None:
            if engine is None:
                cls._logger.debug(f'Will get default value later key: {key}')
            else:
                value = engine.get_setting_default(setting_id)
        return value

    @classmethod
    def get_backend_id(cls) -> str:
        backend: str = Settings.get_setting_str(Settings.BACKEND, backend_id=None,
                                                ignore_cache=False,
                                                default_value=Settings.BACKEND_DEFAULT)
        cls._logger.debug(f'TRACE get_backend_id: {backend}')
        cls._current_backend = backend
        return backend

    @classmethod
    def set_backend_id(cls, backend_id: str) -> None:
        cls._logger.debug(f'TRACE set backend_id: {backend_id}')
        if backend_id is None or len(backend_id) == 0:
            cls._logger.debug(f'invalid backend_id Not saving')
            return

        Settings.set_setting_str(Settings.BACKEND, backend_id)
        cls._current_backend = backend_id

    @classmethod
    def get_addons_md5(cls) -> str:
        addon_md5: str = Settings.get_setting_str(Settings.ADDONS_MD5, backend_id=None,
                                                  ignore_cache=False, default_value=None)
        cls._logger.debug(f'addons MD5: {Settings.ADDONS_MD5}')
        return addon_md5

    @classmethod
    def set_addons_md5(cls, addon_md5: str) -> None:
        cls._logger.debug(f'setting addons md5: {addon_md5}')
        Settings.set_setting_str(Settings.ADDONS_MD5, addon_md5)
        return

    @classmethod
    def get_api_key(cls, api_key: str) -> None:
        cls._logger.debug(f'getting api_key: {api_key}')
        Settings.get_setting_str(Settings.API_KEY, backend_id=None,
                                 ignore_cache=False, default_value=None)
        return

    @classmethod
    def set_api_key(cls, api_key: str) -> None:
        cls._logger.debug(f'setting api_key: {api_key}')
        Settings.set_setting_str(Settings.API_KEY, api_key, backend_id=None)
        return

    @classmethod
    def get_auto_item_extra(cls, default_value: bool = None) -> bool:
        value: bool = Settings.get_setting_bool(
                Settings.AUTO_ITEM_EXTRA, backend_id=None,
                default_value=default_value)
        cls._logger.debug(f'{Settings.AUTO_ITEM_EXTRA}: {value}')
        return value

    @classmethod
    def set_auto_item_extra(cls, value: bool) -> None:
        cls._logger.debug(f'setting {Settings.AUTO_ITEM_EXTRA}: {value}')
        Settings.set_setting_bool(Settings.AUTO_ITEM_EXTRA, value)
        return

    @classmethod
    def get_auto_item_extra_delay(cls, default_value: int = None) -> int:
        value: int = Settings.get_setting_int(
                Settings.AUTO_ITEM_EXTRA_DELAY, default_value)
        cls._logger.debug(f'{Settings.AUTO_ITEM_EXTRA_DELAY}: {value}')
        return value

    @classmethod
    def set_auto_item_extra_delay(cls, value: int) -> None:
        cls._logger.debug(f'setting {Settings.AUTO_ITEM_EXTRA_DELAY}: {value}')
        Settings.set_setting_int(Settings.AUTO_ITEM_EXTRA_DELAY, value)
        return

    @classmethod
    def get_reader_off(cls, default_value: bool = None) -> bool:
        value: bool = Settings.get_setting_bool(
                Settings.READER_OFF, default_value)
        cls._logger.debug(f'{Settings.READER_OFF}: {value}')
        return value

    @classmethod
    def set_reader_off(cls, value: bool) -> None:
        cls._logger.debug(f'setting {Settings.READER_OFF}: {value}')
        Settings.set_setting_bool(Settings.READER_OFF, value)
        return

    @classmethod
    def get_speak_list_count(cls, default_value: bool = None) -> bool:
        value: bool = Settings.get_setting_bool(
                Settings.SPEAK_LIST_COUNT, backend_id=None,
                default_value=default_value)

        cls._logger.debug(f'{Settings.SPEAK_LIST_COUNT}: {value}')
        return value

    @classmethod
    def set_speak_list_count(cls, value: bool) -> None:
        cls._logger.debug(f'setting {Settings.SPEAK_LIST_COUNT}: {value}')
        Settings.set_setting_bool(Settings.SPEAK_LIST_COUNT, value)
        return

    @classmethod
    def get_player(cls, default_value: str | None, backend_id: str = None) -> str:
        value: str = Settings.get_setting_str(Settings.PLAYER, backend_id=backend_id,
                                              ignore_cache=False,
                                              default_value=default_value)
        cls._logger.debug(f'player.{backend_id} = {value}')
        return value

    @classmethod
    def set_player(cls, value: str, backend_id: str = None) -> bool:
        cls._logger.debug(f'setting {Settings.PLAYER}: {value}')
        return Settings.set_setting_str(Settings.PLAYER, value, backend_id=backend_id)

    @classmethod
    def init(cls):
        SettingsBridge.set_settings_ref(cls)

        cls._logger = module_logger.getChild(cls.__name__)
        cls._current_backend = cls.BACKEND_DEFAULT
        cls.kodi_settings = xbmcaddon.Addon("service.kodi.tts").getSettings()
        cls._settings_types = {
            cls.ADDONS_MD5                            : SettingType.STRING_TYPE,
            cls.API_KEY                               : SettingType.STRING_TYPE,
            cls.AUTO_ITEM_EXTRA                       : SettingType.BOOLEAN_TYPE,
            cls.AUTO_ITEM_EXTRA_DELAY                 : SettingType.INTEGER_TYPE,
            cls.BACKEND                               : SettingType.STRING_TYPE,
            cls.BACKGROUND_PROGRESS_INTERVAL          : SettingType.INTEGER_TYPE,
            cls.CACHE_PATH                            : SettingType.STRING_TYPE,
            cls.CACHE_EXPIRATION_DAYS                 : SettingType.INTEGER_TYPE,
            cls.CACHE_SPEECH                          : SettingType.BOOLEAN_TYPE,
            cls.CAPITAL_RECOGNITION                   : SettingType.STRING_TYPE,
            # cls.DEBUG_LOGGING: SettingType.BOOLEAN_TYPE,
            cls.DEBUG_LOG_LEVEL                       : SettingType.INTEGER_TYPE,
            cls.DISABLE_BROKEN_BACKENDS               : SettingType.BOOLEAN_TYPE,
            cls.EXTERNAL_COMMAND                      : SettingType.STRING_TYPE,
            cls.GENDER                                : SettingType.INTEGER_TYPE,
            cls.GENDER_VISIBLE                        : SettingType.BOOLEAN_TYPE,
            cls.GUI                                   : SettingType.BOOLEAN_TYPE,
            cls.LANGUAGE                              : SettingType.STRING_TYPE,
            cls.MODULE                                : SettingType.STRING_TYPE,
            cls.OUTPUT_VIA                            : SettingType.STRING_TYPE,
            cls.OUTPUT_VISIBLE                        : SettingType.BOOLEAN_TYPE,
            cls.OVERRIDE_POLL_INTERVAL                : SettingType.BOOLEAN_TYPE,
            cls.PIPE                                  : SettingType.BOOLEAN_TYPE,
            cls.PITCH                                 : SettingType.INTEGER_TYPE,
            cls.PLAYER                                : SettingType.STRING_TYPE,
            cls.PLAYER_VOLUME                         : SettingType.INTEGER_TYPE,
            cls.PLAYER_PITCH                          : SettingType.INTEGER_TYPE,
            cls.PLAYER_SPEED                          : SettingType.INTEGER_TYPE,
            cls.POLL_INTERVAL                         : SettingType.INTEGER_TYPE,
            cls.READER_OFF                            : SettingType.BOOLEAN_TYPE,
            cls.REMOTE_PITCH                          : SettingType.INTEGER_TYPE,
            # Replaces engine.ttsd, etc.
            cls.REMOTE_SERVER                         : SettingType.STRING_TYPE,
            cls.REMOTE_SPEED                          : SettingType.INTEGER_TYPE,
            cls.REMOTE_VOLUME                         : SettingType.INTEGER_TYPE,
            cls.SETTINGS_BEING_CONFIGURED             : SettingType.BOOLEAN_TYPE,
            cls.SETTINGS_DIGEST                       : SettingType.STRING_TYPE,
            cls.SETTINGS_LAST_CHANGED                 : SettingType.INTEGER_TYPE,
            cls.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: SettingType.BOOLEAN_TYPE,
            cls.SPEAK_BACKGROUND_PROGRESS             : SettingType.BOOLEAN_TYPE,
            cls.SPEAK_LIST_COUNT                      : SettingType.BOOLEAN_TYPE,
            cls.SPEAK_ON_SERVER                       : SettingType.BOOLEAN_TYPE,
            cls.SPEAK_VIA_KODI                        : SettingType.BOOLEAN_TYPE,
            cls.SPEECH_DISPATCHER                     : SettingType.STRING_TYPE,
            cls.SPEED                                 : SettingType.INTEGER_TYPE,
            cls.SPEED_ENABLED                         : SettingType.BOOLEAN_TYPE,
            cls.SPEED_VISIBLE                         : SettingType.BOOLEAN_TYPE,
            cls.TTSD_HOST                             : SettingType.STRING_TYPE,
            cls.TTSD_PORT                             : SettingType.INTEGER_TYPE,
            cls.USE_AOSS                              : SettingType.BOOLEAN_TYPE,
            cls.USE_TEMPFS                            : SettingType.BOOLEAN_TYPE,
            cls.VERSION                               : SettingType.STRING_TYPE,
            cls.VOICE                                 : SettingType.STRING_TYPE,
            cls.VOICE_VISIBLE                         : SettingType.BOOLEAN_TYPE,
            cls.VOLUME                                : SettingType.INTEGER_TYPE,
            cls.VOLUME_VISIBLE                        : SettingType.STRING_TYPE
        }
        cls.load_settings()

    @classmethod
    def configuring_settings(cls):
        cls._logger.debug('configuring_settings hardcoded to false')
        return False

    @classmethod
    def getExpandedSettingId(cls, setting_id: str, backend: str) -> str:
        tmp_id: List[str] = setting_id.split(sep=".", maxsplit=2)
        real_key: str
        if len(tmp_id) > 1:
            cls._logger.debug(f'already expanded: {setting_id}')
            real_key = setting_id
        else:
            suffix: str = ''
            if setting_id not in cls.TOP_LEVEL_SETTINGS:
                suffix = "." + backend

            real_key: str = setting_id + suffix
        cls._logger.debug(
                f'in: {setting_id} out: {real_key} len(tmp_id): {len(tmp_id)}')
        return real_key

    @classmethod
    def splitSettingId(cls, expanded_setting: str) -> Tuple[str | None, str | None]:
        tmp_id: List[str] = expanded_setting.split(sep=".", maxsplit=2)
        if len(tmp_id) == 1:
            return tmp_id[0], None
        if len(tmp_id) == 2:
            return tmp_id[1], tmp_id[0]

        cls._logger.debug(f'Malformed setting id: {expanded_setting}')
        return None, None

    @classmethod
    def getSettingIdPrefix(cls, setting_id: str) -> str:
        #
        tmp_id: List[str] = setting_id.split(sep=".", maxsplit=1)
        prefix: str
        prefix = tmp_id[0]
        return prefix

    @classmethod
    def getRealSetting(cls, setting_id: str, backend_id: str | None,
                       default_value: Any | None) -> Any | None:
        cls._logger.debug(
            f'TRACE getRealSetting NOT from cache id: {setting_id} backend: {backend_id}')
        if backend_id is None or len(backend_id) == 0:
            backend_id = cls._current_backend
            if backend_id is None or len(backend_id) == 0:
                cls._logger.error("TRACE null or empty backend")
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        try:
            match cls._settings_types[setting_id]:
                case SettingType.BOOLEAN_TYPE:
                    return cls.kodi_settings.getBool(real_key)
                case SettingType.BOOLEAN_LIST_TYPE:
                    return cls.kodi_settings.getBoolList(real_key)
                case SettingType.FLOAT_TYPE:
                    return cls.kodi_settings.getNumber(real_key)
                case SettingType.FLOAT_LIST_TYPE:
                    return cls.kodi_settings.getNumberList(real_key)
                case SettingType.INTEGER_TYPE:
                    return cls.kodi_settings.getInt(real_key)
                case SettingType.INTEGER_LIST_TYPE:
                    return cls.kodi_settings.getIntList(real_key)
                case SettingType.STRING_TYPE:
                    return cls.kodi_settings.getString(real_key)
                case SettingType.STRING_LIST_TYPE:
                    return cls.kodi_settings.getStringList(real_key)
        except TypeError:
            cls._logger.debug(f'Setting {real_key} not found')

    @classmethod
    def commit_settings(cls):
        cls._logger.debug('TRACE commit_settings')
        cls.kodi_settings = xbmcaddon.Addon('service.kodi.tts').getSettings()
        addon: xbmcaddon.Addon = xbmcaddon.Addon('service.kodi.tts')

        for full_setting_id, value in CurrentCachedSettings.get_settings().items():
            full_setting_id: str
            value: Any
            value_type: SettingType | None = None
            str_value: str = ''
            try:
                str_value = str(value)
                if full_setting_id == Settings.BACKEND:
                    cls._logger.debug(f'TRACE Commiting BACKEND value: {str_value}')

                cls._logger.debug(f'id: {full_setting_id} value: {str_value}')
                prefix: str = cls.getSettingIdPrefix(full_setting_id)
                value_type = cls._settings_types.get(prefix, None)
                if value == 'NO_VALUE':
                    cls._logger.debug(f'Expected setting not found {prefix}')
                    continue
                # tmp: Any = 'bogus'
                # cls.kodi_settings = xbmcaddon.Addon('service.kodi.tts').getSettings()
                # addon: xbmcaddon.Addon = xbmcaddon.Addon('service.kodi.tts')
                match value_type:
                    case SettingType.BOOLEAN_TYPE:
                        # cls.kodi_settings.setBool(full_setting_id, value)
                        addon.setSettingBool(full_setting_id, value)
                        # tmp: bool = cls.kodi_settings.getBool(full_setting_id)
                    case SettingType.BOOLEAN_LIST_TYPE:
                        cls.kodi_settings.setBoolList(full_setting_id, value)
                        # addon.setSettingBool(full_setting_id, value)
                    case SettingType.FLOAT_TYPE:
                        # cls.kodi_settings.setNumber(full_setting_id, value)
                        addon.setSettingNumber(full_setting_id, value)
                        # tmp: float = cls.kodi_settings.getNumber(full_setting_id)
                    case SettingType.FLOAT_LIST_TYPE:
                        cls.kodi_settings.setNumberList(full_setting_id, value)
                    case SettingType.INTEGER_TYPE:
                        # cls.kodi_settings.setInt(full_setting_id, value)
                        addon.setSettingInt(full_setting_id, value)
                        # tmp: int = cls.kodi_settings.getInt(full_setting_id)
                    case SettingType.INTEGER_LIST_TYPE:
                        cls.kodi_settings.setIntList(full_setting_id, value)
                    case SettingType.STRING_TYPE:
                        # cls.kodi_settings.setString(full_setting_id, value)
                        addon.setSetting(full_setting_id, value)
                        # tmp: str = cls.kodi_settings.getString(full_setting_id)
                    case SettingType.STRING_LIST_TYPE:
                        cls.kodi_settings.setStringList(full_setting_id, value)
                # if tmp != value:
                #    saved_value: str = str(tmp)
                #    cls._logger.error(
                #        f'TRACE ERROR Saved value of {full_setting_id} != Read value {str_value}, '
                #        f'saved value: {saved_value}')
            except Exception as e:
                cls._logger.exception(f'Error saving setting: {full_setting_id} '
                                      f'value: {str_value} as '
                                      f'{value_type.name}')

    @classmethod
    def getSetting(cls, setting_id: str, backend_id: str | None,
                   default_value: Any | None = None) -> Any:
        if backend_id is None:
            backend_id = cls._current_backend
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        if CurrentCachedSettings.is_empty():
            cls.load_settings()

        value: Any = Settings._getSetting(setting_id, backend_id, default_value)
        cls._logger.debug(f'setting_id: {real_key} value: {value}')
        return value

    @classmethod
    def _getSetting(cls, setting_id: str, backend_id: str | None,
                    default_value: Any | None = None) -> Any:
        value: Any = None
        full_setting_id = cls.getExpandedSettingId(setting_id, backend_id)
        try:
            value: Any = CurrentCachedSettings.get_setting(full_setting_id, default_value)
        except KeyError:
            value = Settings.getRealSetting(setting_id, backend_id, default_value)
            CurrentCachedSettings.set_setting(full_setting_id, value)
        # cls._logger.debug(f'setting_id: {full_setting_id} value: {value}')
        return value

    @classmethod
    def setSetting(cls, setting_id: str, value: Any,
                   backend_id: str) -> bool:

        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        try:
            success: bool = CurrentCachedSettings.set_setting(real_key, value)
            return success
        except:
            cls._logger.debug(f'TRACE: type mismatch')

    @classmethod
    def get_setting_str(cls, setting_id: str, backend_id: str = None,
                        ignore_cache: bool = False,
                        default_value: str = None) -> str:
        if ignore_cache and setting_id == Settings.BACKEND:
            cls._logger.debug(f'TRACE get_backend_id IGNORING CACHE id: {setting_id}')
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        if ignore_cache:
            return cls.kodi_settings.getString(real_key)

        return Settings._getSetting(setting_id, backend_id, default_value)

    @classmethod
    def set_setting_str(cls, setting_id: str, value: str, backend_id: str = None) -> bool:
        if setting_id == Settings.BACKEND:
            cls._logger.debug(f'TRACE set_backend_id: {value}')
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        passed: bool = CurrentCachedSettings.set_setting(real_key, value)
        return passed

    @classmethod
    def get_setting_bool(cls, setting_id: str, backend_id: str = None,
                         default_value: bool = None) -> bool:
        """

        :return:
        """
        return Settings._getSetting(setting_id, backend_id, default_value)

    @classmethod
    def set_setting_bool(cls, setting_id: str, value: bool,
                         backend_id: str = None) -> bool:
        """
        :setting:
        :value:
        :return:
        """
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        return CurrentCachedSettings.set_setting(real_key, value)

    @classmethod
    def get_setting_float(cls, setting_id: str, backend_id: str = None,
                          default_value: float = 0.0) -> float:
        """

        :return:
        """
        return Settings._getSetting(setting_id, backend_id, default_value)

    @classmethod
    def set_setting_float(cls, setting_id: str, value: float,
                          backend_id: str = None) -> bool:
        """

        :return:
        """
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        return CurrentCachedSettings.set_setting(real_key, value)

    @classmethod
    def get_setting_int(cls, setting_id: str, backend_id: str = None,
                        default_value: int = 0) -> int:
        """

        :return:
        """
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        return CurrentCachedSettings.get_setting(real_key, default_value)

    @classmethod
    def set_setting_int(cls, setting_id: str, value: int, backend_id: str = None) -> bool:
        """

        :return:
        """
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        return CurrentCachedSettings.set_setting(real_key, value)

    @classmethod
    def update_cached_setting(cls, setting_id: str, value: Any,
                              backend_id: str = None) -> None:
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        CurrentCachedSettings.set_setting(real_key, value)

    '''
    def getBoolList(self, id: str) -> List[bool]:
    def getIntList(self, id: str) -> List[int]:
    def getNumberList(self, id: str) -> List[float]:
    def getStringList(self, id: str) -> List[str]:
    
    def setBoolList(self, id: str, values: List[bool]) -> None:
    def setIntList(self, id: str, values: List[int]) -> None:
    def setNumberList(self, id: str, values: List[float]) -> None:
    def setStringList(self, id: str, values: List[str]) -> None:
    '''


Settings.init()
