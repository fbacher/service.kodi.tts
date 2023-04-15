# -*- coding: utf-8 -*-

import binascii
import copy
import time
from enum import Enum
import xbmc
import xbmcaddon

from common.constants import Constants
from kutils.kodiaddon import Addon
from common.logger import *
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
    def set_setting(cls, setting_id: str, value: Any = None) -> None:
        cls._current_settings_changed = True
        if cls._current_settings_update_begin is None:
            cls._current_settings_update_begin = time.time()
        cls._current_settings[setting_id] = value

    @classmethod
    def set_settings(cls, settings_to_backup: Dict[str, Any]) -> None:
        cls._current_settings = copy.deepcopy (settings_to_backup)
        cls._logger.debug(f'settings_to_backup len: {len(settings_to_backup)}'
                          f' current_settings len: {len(cls._current_settings)}')
        cls._current_settings_changed = True
        if cls._current_settings_update_begin is None:
            cls._current_settings_update_begin = time.time()

    @classmethod
    def backup_settings(cls) -> None:
        PreviousCachedSettings.backup_settings(cls._current_settings,
                                               cls._current_settings_changed,
                                               cls._current_settings_update_begin)

    @classmethod
    def restore_settings(cls) -> None:
        saved_settings: Dict[str, Any]
        saved_settings_changed: bool
        saved_settings_update_begin: float
        saved_settings, saved_settings_changed, saved_settings_update_begin = \
            PreviousCachedSettings.get_saved_settings()
        cls._current_settings = copy.deepcopy(saved_settings)
        cls._logger.debug(f'saved_settings len: {len(saved_settings)}'
                          f' current_settings len: {len(cls._current_settings)}')
        cls._current_settings_changed = saved_settings_changed
        cls._current_settings_update_begin = saved_settings_update_begin

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        return cls._current_settings

    @classmethod
    def get_setting(cls, setting_id: str, default_value: Any) -> Any:
        value = cls._current_settings.get(setting_id, default_value)
        cls._logger.debug(f'setting_id: {setting_id} value: {value}')
        return value

    @classmethod
    def is_empty(cls) -> bool:
        return not cls._current_settings


class PreviousCachedSettings:

    # Backup copy of settings while _current_settings is being changed

    _saved_settings: Dict[str, Union[Any, None]] = {}
    _saved_settings_changed: bool = False
    _saved_settings_update_begin: float = None

    @classmethod
    def backup_settings(cls, settings_to_backup: Dict[str, Any],
                        settings_changed: bool,
                        settings_update_begin: float) -> None:
        cls.clear_saved_settings()
        cls._previous_settings = copy.deepcopy (settings_to_backup)
        cls._previous_settings_update_begin = settings_update_begin
        cls._saved_settings_changed = settings_changed

    @classmethod
    def clear_saved_settings(cls) -> None:
        cls._saved_settings.clear()
        cls._saved_settings_changed: bool = False
        cls._saved_settings_update_begin = None

    @classmethod
    def get_saved_settings(cls) -> (Union[Dict[str, Any]], bool, float):
        return (cls._saved_settings, cls._saved_settings_changed,
                cls._saved_settings_update_begin)

    @classmethod
    def get_setting(cls, setting_id: str, default_value: Any) -> Any:
        return cls._saved_settings.get(setting_id, default_value)


class Settings:
    '''
    # Digest of the settings for quick detection of changes
    'addons_MD5'>c1ca8f807fe0e3857bef2e42554a9f67

    'api_key.Cepstral' default='true'

    # api key for current backend
    'api_key' default='true'>1f3KHpbc

    # api key for specific engine

    'api_key.ResponsiveVoice'>1f3KHpbc
    'auto_item_extra_delay' default='true'>2
    'auto_item_extra'>true
    'backend'>ResponsiveVoice
    'background_progress_interval' default='true'>5
    'cache_expiration_days'>720
    'cache_path'>special://userdata/addon_data/service.kodi.tts/cache/
    'cache_speech.ResponsiveVoice'>true
    'cache_voice_files' default='true'>true
    'debug_logging'>true
    'disable_broken_backends' default='true'>true
    'do_debug' default='true'>true
    'engine.ttsd' default='true'
    'EXTERNAL_COMMAND' default='true'
    'gender.Cepstral' default='true'
    'gender' default='true'>unknown
    'gender.eSpeak' default='true'
    'gender.Flite' default='true'
    'gender.Google' default='true'
    'gender.OSXSay' default='true'
    'gender.pico2wave' default='true'
    'gender.ResponsiveVoice'>unknown
    'gender.SAPI' default='true'
    'gender.Speech-Dispatcher' default='true'
    'gender_visible' default='true'>true
    'gui' default='true'
    'host.ttsd' default='true'>127.0.0.1
    'language.Cepstral' default='true'
    'language' default='true'>en-US
    'language.eSpeak' default='true'
    'language.Festival' default='true'
    'language.Flite' default='true'
    'language.Google'>en
    'language.OSXSay' default='true'
    'language.pico2wave'>en-US
    'language.ResponsiveVoice'>en-US
    'language.SAPI' default='true'
    'language.Speech-Dispatcher' default='true'
    'language_visible' default='true'>true
    'log_level'>5
    'module.Speech-Dispatcher' default='true'
    'output' default='true'>false
    'output_via_espeak.eSpeak' default='true'>false
    'output_via_flite.Flite' default='true'>false
    'output_visible' default='true'>false
    'override_poll_interval' default='true'>false
    'perl_server.ttsd' default='true'>true
    'pipe.Cepstral' default='true'>false
    'pipe' default='true'>false
    'pipe.eSpeak' default='true'>false
    'pipe.Festival' default='true'>false
    'pipe.Flite' default='true'>false
    'pipe.Google'>true
    'pipe.OSXSay' default='true'>false
    'pipe.pico2wave' default='true'>false
    'pipe.ResponsiveVoice'>true
    'pipe.SAPI' default='true'>false
    'pipe.Speech-Dispatcher' default='true'>false
    'pipe.ttsd'>true
    'pipe_visible' default='true'>true
    'pitch.Cepstral'>0
    'pitch' default='true'>50
    'pitch.eSpeak'>50
    'pitch.Festival'>500
    'pitch.Flite' default='true'>5
    'pitch.Google' default='true'>5
    'pitch.OSXSay' default='true'>5
    'pitch.pico2wave' default='true'>5
    'pitch.ResponsiveVoice'>47
    'pitch.SAPI'>0
    'pitch.Speech-Dispatcher'>0
    'pitch_visible' default='true'>true
    'player.Cepstral' default='true'
    'player' default='true'>sox
    'player_enabled' default='true'>true
    'player.eSpeak' default='true'
    'player.Festival' default='true'
    'player.Flite'>sox
    'player.Google'>mplayer
    'player.OSXSay' default='true'
    'player.pico2wave'>PlaySFX
    'player.ResponsiveVoice'>mplayer
    'player.SAPI' default='true'
    'player.Speech-Dispatcher' default='true'
    'player_speed.ttsd' default='true'>100
    'player.ttsd' default='true'
    'player_visible' default='true'>true
    'player_volume.ttsd'>10
    'poll_interval' default='true'>100
    'port.ttsd' default='true'>8256
    'reader_off' default='true'>false
    'remote_pitch.ttsd' default='true'>0
    'remote_speed.ttsd' default='true'>0
    'remote_volume.ttsd' default='true'>0
    'speak_background_progress' default='true'>false
    'speak_background_progress_during_media' default='true'>false
    'speak_list_count' default='true'>true
    'speak_on_server.ttsd' default='true'>false
    'speak_via_kodi.SAPI' default='true'>false
    'speed.Cepstral'>170
    'speed' default='true'>50
    'speed_enabled' default='true'>true
    'speed.eSpeak'>175
    'speed.Festival'>12
    'speed.Flite'>100
    'speed.Google' default='true'>5
    'speed.OSXSay'>200
    'speed.pico2wave'>100
    'speed.ResponsiveVoice'>60
    'speed.SAPI'>0
    'speed.Speech-Dispatcher'>0
    'speed_visible' default='true'>true
    'temp.addons_MD5' default='true'
    'temp.api_key.ResponsiveVoice' default='true'
    'use_aoss.Cepstral' default='true'>false
    'use_temp_settings'>true
    'use_tmpfs' default='true'>true
    'verbose_logging'>true
    'version'>2.0.0
    'voice.Cepstral' default='true'
    'voice.Cepstral.ttsd' default='true'
    'voice' default='true'
    'voice.eSpeak-ctypes' default='true'
    'voice.eSpeak'>English_(America)
    'voice.eSpeak.ttsd' default='true'
    'voice.Festival'>en1_mbrola
    'voice.Festival.ttsd' default='true'
    'voice.Flite'>slt
    'voice.Flite.ttsd' default='true'
    'voice.Google' default='true'
    'voice.OSXSay' default='true'
    'voice.OSXSay.ttsd' default='true'
    'voice.pico2wave' default='true'
    'voice.ResponsiveVoice'>g1
    'voice.SAPI' default='true'
    'voice.SAPI.ttsd' default='true'
    'voice.Speech-Dispatcher' default='true'
    'voice.ttsd' default='true'
    'voice_visible' default='true'>true
    'volume.Cepstral'>0
    'volume' default='true'>-10
    'volume.eSpeak'>0
    'volume.Festival'>12
    'volume.Flite'>0
    'volume.Google'>0
    'volume.OSXSay'>100
    'volume.pico2wave'>0
    'volume.ResponsiveVoice'>-10
    'volume.SAPI'>50
    'volume.Speech-Dispatcher'>50
    'volume_visible' default='true'>true
    '''
    # TOP LEVEL SETTINGS

    # bool whether to wait extra time before saying something extra

    _addon_singleton: Addon = None
    KODI_SETTINGS: xbmcaddon.Settings = None

    ADDONS_MD5: Final[str] = 'addons_MD5'
    API_KEY: Final[str] = 'api_key'
    AUTO_ITEM_EXTRA: Final[str] = 'auto_item_extra'

    # int seconds Time to wait before saying something extra in seconds

    AUTO_ITEM_EXTRA_DELAY: Final[str] = 'auto_item_extra_delay'

    BACKEND: Final[str] = 'backend'
    BACKEND_DEFAULT: Final[str] = 'auto'
    BACKGROUND_PROGRESS_INTERVAL: Final[str] = 'background_progress_interval'
    CACHE_PATH: Final[str] = 'cache_path'
    CACHE_EXPIRATION_DAYS: Final[str] = 'cache_expiration_days'
    CACHE_SPEECH: Final[str] = 'cache_speech'
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
    OUTPUT_VIA: Final[str] = 'output_via'
    OUTPUT_VISIBLE: Final[str] = 'output_visible'
    OVERRIDE_POLL_INTERVAL: Final[str] = 'override_poll_interval'
    PIPE: Final[str] = 'pipe'  # Engine to pipe speech to a player
    PITCH: Final[str] = 'pitch'
    PLAYER: Final[str] = 'player'  # Specifies the player
    PLAYER_VOLUME: Final[str] = 'player_volume'
    POLL_INTERVAL: Final[str] = 'poll_interval'
    READER_OFF: Final[str] = 'reader_off'
    REMOTE_PITCH: Final[str] = 'remote_pitch'
    REMOTE_SERVER: Final[str] = 'remote_server'
    REMOTE_SPEED: Final[str] = 'remote_speed'
    REMOTE_VOLUME: Final[str] = 'remote_volume'
    SETTINGS_BEING_CONFIGURED: Final[str] = 'settings_being_configured'
    SETTINGS_DIGEST: Final[str] = 'settings_digest'
    SETTINGS_LAST_CHANGED: Final[str] = 'settings_last_changed'
    SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: Final[str] = 'speak_background_progress_during_media'
    SPEAK_BACKGROUND_PROGRESS: Final[str] = 'speak_background_progress'
    SPEAK_LIST_COUNT: Final[str] = 'speak_list_count'
    SPEAK_ON_SERVER: Final[str] = 'speak_on_server'
    SPEAK_VIA_KODI: Final[str] = 'speak_via_kodi'
    SPEECH_DISPATCHER_MODULE: Final[str] = 'Speech-Dispatcher-module'
    SPEED: Final[str] = 'speed'
    SPEED_ENABLED: Final[str] = 'speed_enabled'
    SPEED_VISIBLE: Final[str] = 'speed_visible'
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
        DEBUG_LOG_LEVEL, # Merge into Logging, get rid of verbose_logging, etc
        GENDER,
        GENDER_VISIBLE,
        GUI,
        SPEECH_DISPATCHER_MODULE,
        OUTPUT_VIA,
        OUTPUT_VISIBLE,
        OVERRIDE_POLL_INTERVAL,
        PIPE,
        POLL_INTERVAL,
        READER_OFF,
        SETTINGS_BEING_CONFIGURED,
        SETTINGS_DIGEST,
        SETTINGS_LAST_CHANGED,
        SPEAK_LIST_COUNT,
        SPEAK_VIA_KODI,
        SPEED_ENABLED,
        SPEED_VISIBLE,
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
        ADDONS_MD5,
        API_KEY,
        AUTO_ITEM_EXTRA,
        AUTO_ITEM_EXTRA_DELAY,  # int seconds Time to wait before saying something extra in seconds
        BACKEND,
        BACKGROUND_PROGRESS_INTERVAL,
        CACHE_PATH,
        CACHE_EXPIRATION_DAYS,
        CACHE_SPEECH,
        # DEBUG_LOGGING,
        DEBUG_LOG_LEVEL,
        DISABLE_BROKEN_BACKENDS,
        EXTERNAL_COMMAND,
        GENDER,
        GENDER_VISIBLE,
        GUI,
        LANGUAGE,
        SPEECH_DISPATCHER_MODULE,
        OUTPUT_VIA,
        OUTPUT_VISIBLE,
        OVERRIDE_POLL_INTERVAL,
        PIPE,
        PITCH,
        PLAYER,
        POLL_INTERVAL,
        READER_OFF,
        REMOTE_PITCH,
        REMOTE_SPEED,
        REMOTE_VOLUME,
        SETTINGS_DIGEST,
        SETTINGS_BEING_CONFIGURED,
        SETTINGS_LAST_CHANGED,
        SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
        SPEAK_BACKGROUND_PROGRESS,
        SPEAK_LIST_COUNT,
        SPEAK_ON_SERVER,
        SPEAK_VIA_KODI,
        SPEED,
        SPEED_ENABLED,
        SPEED_VISIBLE,
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

    _current_backend: str = None
    temp_shadow_settings = {}
    use_temp_settings = False
    _logger = None

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
        Settings.save_settings()
        Settings.reload_settings()

    @classmethod
    def reload_settings(cls) -> None:
        '''

        :return:
        '''
        Settings._addon_singleton = None
        backend_id: str = cls.get_backend_id(ignore_cache=True)
        cls._current_backend = backend_id
        cls.load_backend(backend_id)
        Settings.get_addon()

    @staticmethod
    def save_settings() -> None:
        '''

        :return:
        '''
        try:
            CurrentCachedSettings.backup_settings()

        except Exception:
            pass

    @staticmethod
    def cancel_changes() -> None:
        # get lock
        # set SETTINGS_BEING_CONFIGURED, SETTINGS_LAST_CHANGED
        #
        CurrentCachedSettings.restore_settings()

    @staticmethod
    def get_changed_settings(settings_to_check: List[str]) -> List[str]:
        '''

        :param settings_to_check:
        :return:
        '''

        Settings._logger.debug('entered')
        changed_settings = []
        for setting_id in settings_to_check:
            previous_value = PreviousCachedSettings.get(setting_id, None)
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
    def load_backend(cls, backend: str) -> None:
        '''
        Load ALL of the settings for this backend

        Ignore any other changes to settings until finished
        '''

        new_settings: Dict[str, Any] = {}

        if backend is None or len(backend) == 0:
            backend = cls.get_backend_id(ignore_cache=True)

        cls._logger.debug(f'backend: {backend}')
        # Get Lock

        for key in cls.ALL_SETTINGS:
            suffix: str = ''
            cls._logger.debug_extra_verbose(f'key: {key}')
            if key not in cls.TOP_LEVEL_SETTINGS:
                suffix = "." + backend
                cls._logger.debug_extra_verbose(f'key2: {key} suffix: {suffix}')

            cls._logger.debug_extra_verbose(f'key: {key} suffix: {suffix}')
            real_key: str = key
            real_key += suffix
            try:
                match cls._settings_types[key]:
                    case SettingType.BOOLEAN_TYPE:
                        new_settings[real_key] = cls.KODI_SETTINGS.getBool(real_key)
                    case SettingType.BOOLEAN_LIST_TYPE:
                        new_settings[real_key] = cls.KODI_SETTINGS.getBoolList(real_key)
                    case SettingType.FLOAT_TYPE:
                        new_settings[real_key] = cls.KODI_SETTINGS.getNumber(real_key)
                    case SettingType.FLOAT_LIST_TYPE:
                        new_settings[real_key] = cls.KODI_SETTINGS.getNumberList(real_key)
                    case SettingType.INTEGER_TYPE:
                        new_settings[real_key] = cls.KODI_SETTINGS.getInt(real_key)
                    case SettingType.INTEGER_LIST_TYPE:
                        new_settings[real_key] = cls.KODI_SETTINGS.getIntList(real_key)
                    case SettingType.STRING_TYPE:
                        new_settings[real_key] = cls.KODI_SETTINGS.getString(real_key)
                    case SettingType.STRING_LIST_TYPE:
                        new_settings[real_key] = cls.KODI_SETTINGS.getStringList(real_key)
                cls._logger.debug(f'found key: {real_key} value: {new_settings[real_key]}')
            except TypeError:
                cls._logger.exception(f'failed to find setting key: {real_key}')

        # validate_settings new_settings
        CurrentCachedSettings.set_settings(new_settings)
        # release lock
        # Notify

    @staticmethod
    def save_backend_id(backend_id: str) -> None:
        '''
        Save ALL of the settings for this backend

        Ignore any other changes to settings until finished
        '''
        Settings.set_setting_str(Settings.BACKEND, backend_id)
        return

    @classmethod
    def get_backend_id(cls, ignore_cache: bool = True) -> str:
        backend: str = Settings.get_setting_str(Settings.BACKEND, ignore_cache)
        cls._logger.debug(f'backend: {backend}')
        cls._current_backend = backend
        return backend

    @classmethod
    def set_backend_id(cls, backend_id: str) -> None:
        cls._logger.debug(f'setting backend_id: {backend_id}')
        Settings.set_setting_str(Settings.BACKEND, backend_id)
        return

    @classmethod
    def get_addons_md5(cls) -> str:
        addon_md5: str = Settings.get_setting_str(Settings.ADDONS_MD5)
        cls._logger.debug(f'addons MD5: {Settings.ADDONS_MD5}')
        return addon_md5

    @classmethod
    def set_addons_md5(cls, addon_md5: str) -> None:
        cls._logger.debug(f'setting addons md5: {addon_md5}')
        Settings.set_setting_str(Settings.ADDONS_MD5, addon_md5)
        return

    @classmethod
    def get_auto_item_extra(cls, default_value: bool = None) -> bool:
        value: bool = Settings.get_setting_bool(Settings.AUTO_ITEM_EXTRA, default_value)
        cls._logger.debug(f'{Settings.AUTO_ITEM_EXTRA}: {value}')
        return value

    @classmethod
    def set_auto_item_extra(cls, value: bool) -> None:
        cls._logger.debug(f'setting {Settings.AUTO_ITEM_EXTRA}: {value}')
        Settings.set_setting_bool(Settings.AUTO_ITEM_EXTRA, value)
        return

    @classmethod
    def get_auto_item_extra_delay(cls, default_value: int = None) -> int:
        value: int = Settings.get_setting_int(Settings.AUTO_ITEM_EXTRA_DELAY, default_value)
        cls._logger.debug(f'{Settings.AUTO_ITEM_EXTRA_DELAY}: {value}')
        return value

    @classmethod
    def set_auto_item_extra_delay(cls, value: int) -> None:
        cls._logger.debug(f'setting {Settings.AUTO_ITEM_EXTRA_DELAY}: {value}')
        Settings.set_setting_int(Settings.AUTO_ITEM_EXTRA_DELAY, value)
        return

    @classmethod
    def get_reader_off(cls, default_value: bool = None) -> bool:
        value: bool = Settings.get_setting_bool(Settings.READER_OFF, default_value)
        cls._logger.debug(f'{Settings.READER_OFF}: {value}')
        return value

    @classmethod
    def set_reader_off(cls, value: bool) -> None:
        cls._logger.debug(f'setting {Settings.READER_OFF}: {value}')
        Settings.set_setting_bool(Settings.READER_OFF, value)
        return

    @classmethod
    def get_speak_list_count(cls, default_value: bool = None) -> bool:
        value: bool = Settings.get_setting_bool(Settings.SPEAK_LIST_COUNT, default_value)
        cls._logger.debug(f'{Settings.SPEAK_LIST_COUNT}: {value}')
        return value

    @classmethod
    def set_speak_list_count(cls, value: bool) -> None:
        cls._logger.debug(f'setting {Settings.SPEAK_LIST_COUNT}: {value}')
        Settings.set_setting_bool(Settings.SPEAK_LIST_COUNT, value)
        return


    '''
    @staticmethod
    def get_adjust_volume() -> bool:
        ' ' '

        :return:
        ' ' '
        return Settings.get_setting_bool(Settings.VOLUME)
    '''

    @classmethod
    def init(cls):
        cls._logger = module_logger.getChild(cls.__name__)
        cls.KODI_SETTINGS = xbmcaddon.Addon(Constants.ADDON_ID).getSettings()
        cls._settings_types = {
            cls.ADDONS_MD5: SettingType.STRING_TYPE,
            cls.API_KEY: SettingType.STRING_TYPE,
            cls.AUTO_ITEM_EXTRA: SettingType.BOOLEAN_TYPE,
            cls.AUTO_ITEM_EXTRA_DELAY: SettingType.INTEGER_TYPE,
            cls.BACKEND: SettingType.STRING_TYPE,
            cls.BACKGROUND_PROGRESS_INTERVAL: SettingType.INTEGER_TYPE,
            cls.CACHE_PATH: SettingType.STRING_TYPE,
            cls.CACHE_EXPIRATION_DAYS: SettingType.INTEGER_TYPE,
            cls.CACHE_SPEECH: SettingType.BOOLEAN_TYPE,
            # cls.DEBUG_LOGGING: SettingType.BOOLEAN_TYPE,
            cls.DEBUG_LOG_LEVEL: SettingType.INTEGER_TYPE,
            cls.DISABLE_BROKEN_BACKENDS: SettingType.BOOLEAN_TYPE,
            cls.EXTERNAL_COMMAND: SettingType.STRING_TYPE,
            cls.GENDER: SettingType.STRING_TYPE,
            cls.GENDER_VISIBLE: SettingType.BOOLEAN_TYPE,
            cls.GUI: SettingType.BOOLEAN_TYPE,
            cls.LANGUAGE: SettingType.STRING_TYPE,
            cls.OUTPUT_VIA: SettingType.STRING_TYPE,
            cls.OUTPUT_VISIBLE: SettingType.BOOLEAN_TYPE,
            cls.OVERRIDE_POLL_INTERVAL: SettingType.BOOLEAN_TYPE,
            cls.PIPE: SettingType.BOOLEAN_TYPE,
            cls.PITCH: SettingType.INTEGER_TYPE,
            cls.PLAYER: SettingType.STRING_TYPE,
            cls.POLL_INTERVAL: SettingType.INTEGER_TYPE,
            cls.READER_OFF: SettingType.BOOLEAN_TYPE,
            cls.REMOTE_PITCH: SettingType.INTEGER_TYPE,
            cls.REMOTE_SERVER: SettingType.STRING_TYPE, # Replaces engine.ttsd, etc.
            cls.REMOTE_SPEED: SettingType.INTEGER_TYPE,
            cls.REMOTE_VOLUME: SettingType.INTEGER_TYPE,
            cls.SETTINGS_BEING_CONFIGURED: SettingType.BOOLEAN_TYPE,
            cls.SETTINGS_DIGEST: SettingType.STRING_TYPE,
            cls.SETTINGS_LAST_CHANGED: SettingType.INTEGER_TYPE,
            cls.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA: SettingType.BOOLEAN_TYPE,
            cls.SPEAK_BACKGROUND_PROGRESS: SettingType.BOOLEAN_TYPE,
            cls.SPEAK_LIST_COUNT: SettingType.BOOLEAN_TYPE,
            cls.SPEAK_ON_SERVER: SettingType.BOOLEAN_TYPE,
            cls.SPEAK_VIA_KODI: SettingType.BOOLEAN_TYPE,
            cls.SPEECH_DISPATCHER_MODULE: SettingType.STRING_TYPE,
            cls.SPEED: SettingType.INTEGER_TYPE,
            cls.SPEED_ENABLED: SettingType.BOOLEAN_TYPE,
            cls.SPEED_VISIBLE: SettingType.BOOLEAN_TYPE,
            cls.TTSD_HOST: SettingType.STRING_TYPE,
            cls.TTSD_PORT: SettingType.INTEGER_TYPE,
            cls.USE_AOSS: SettingType.BOOLEAN_TYPE,
            cls.USE_TEMPFS: SettingType.BOOLEAN_TYPE,
            cls.VERSION: SettingType.STRING_TYPE,
            cls.VOICE: SettingType.STRING_TYPE,
            cls.VOICE_VISIBLE: SettingType.BOOLEAN_TYPE,
            cls.VOLUME: SettingType.INTEGER_TYPE,
            cls.VOLUME_VISIBLE: SettingType.STRING_TYPE
        }
    '''
    @classmethod
    def getSetting(cls, key: str, default: Union[str, None] = None,
               setting_type: Union[Type, None] = None):

        if key.startswith('None'):
            cls._logger.debug_verbose(f'Found key with none:{key}')
            return None

        setting: Any = cls._current_settings.get(key, None)
        if setting is None:
            cls._logger.debug_verbose(f'Found key value None: {key}')
        return setting
    '''
    '''
    @classmethod
    def getSetting(cls, key: str, default: Union[str, None] = None,
                   setting_type: Union[Type, None] = None):
        if key.startswith('None'):
            cls._logger.debug_verbose('Found key with none:{}'.format(key))

        cls.check_key(key)

        setting = None
        if cls.configuring_settings():
            temp_key = '{}.{}'.format('temp', key)
            if temp_key in cls.temp_shadow_settings:
                setting = cls.temp_shadow_settings.get(temp_key)
            else:
                setting = xbmcaddon.Addon().getSetting(key)
                cls.temp_shadow_settings[temp_key] = setting
        else:
            setting = cls._get_setting(key, default)

        cls._logger.debug_verbose('key: {} value: {}'
                                  .format(key, str(setting)))
        return cls._processSetting(setting, default, setting_type=setting_type)

    '''

    '''
    @classmethod
    def _get_setting(cls, key: str, default: Union[str, None] = None):
        setting = cls._current_settings.get(key, None)
        if setting is None:
            setting = xbmcaddon.Addon().getSetting(key)
            cls._logger.debug_extra_verbose('key: {} value: {} default: {}'
                                            .format(key, setting, default))
            if setting is None:
                setting = default
            cls.cached_settings[key] = setting
        return setting
    '''

    '''
    @classmethod
    def _processSetting(cls, setting, default, setting_type: Union[Type, None] = None):
        return_value = setting
        if setting is None:
            return_value = default

        if return_value is None:
            return return_value

        return_type = setting_type
        if return_type is None and default is not None:
            return_type = type(default)

        if return_type is None:
            return return_value

        if isinstance(return_value, return_type):
            return return_value
        elif issubclass(return_type, bool):
            return return_value.lower() == 'true'
        elif issubclass(return_type, float):
            return float(return_value)
        elif issubclass(return_type, int):
            return int(float(return_value or 0))
        elif issubclass(return_value, list):
            return binascii.unhexlify(return_value).split('\0')
        return return_value
    '''

    '''
    @classmethod
    def setSetting(cls, key, value):
        value = cls._processSettingForWrite(value)
        cls._logger.debug_verbose(
            'key:', key, ' value:', value)
        cls.check_key(key)

        if cls.configuring_settings():
            key = '{}.{}'.format('temp', key)
            cls.temp_shadow_settings[key] = value
        else:
            cls._set_setting(key, value)

        #  if key.startswith('backend'):
        #      cls._set_setting(key, value)
    '''

    '''
    @classmethod
    def _set_setting(cls, key: str, value: Any):
        cls._logger.debug_extra_verbose('key: {} value: {}'
                                        .format(key, value))
        cls.cached_settings[key] = value
        xbmcaddon.Addon().setSetting(key, value)
        return

    @classmethod
    def _processSettingForWrite(cls, value):
        if isinstance(value, list):
            value = binascii.hexlify('\0'.join(value))
        elif isinstance(value, bool):
            value = value and 'true' or 'false'
        return str(value)
    '''

    '''
    @classmethod
    def check_key(cls, key):
        if key.startswith('backend.'):
            cls._logger.debug_verbose(
                'key starts with backend. {}'.format(key))

        if key.startswith('temp'):
            cls._logger.debug_verbose(
                'key starts with temp {}'.format(key))
        tokens = key.split('.')
        if tokens[0] in cls.TOP_LEVEL_SETTINGS:
            if len(tokens) != 1:
                cls._logger.error('TOP_LEVEL_SETTING used as engine-specific: {}'
                                  .format(key))
        elif len(tokens) == 1:
            cls._logger.error('Unregistered TOP_LEVEL_SETTING: {}'
                              .format(key))
        elif len(tokens) == 1:
            cls._logger.error('Engine not specified {}'
                              .format(key))
    '''


    @classmethod
    def configuring_settings(cls):
        #if cls.use_temp_settings:
        #    cls._logger.debug_verbose('using temp settings')
        return False

    '''
    @classmethod
    def begin_configuring_settings(cls):
        pass  # cls.backend_changed()

    @classmethod
    def backend_changed(cls, new_provider):

        cls._logger.debug_verbose(
            'backend_changed: {}'.format(new_provider.provider))
        cls._logger.debug_verbose('setting use_temp_settings')
        cls.use_temp_settings = True

        return

        key_suffix = new_provider.provider
        setting_keys = new_provider.getSettingNames()
        setting_map = dict()
        for key in setting_keys:
            setting_name = '{}.{}'.format(key, key_suffix)
            try:
                setting = xbmcaddon.Addon().getSetting(setting_name)
                # ADDON.getSetting(setting_name)
            except Exception as e:
                setting = 'No Setting'

            if setting == 'No Setting':
                setting_name = key
                try:
                    setting = xbmcaddon.Addon().getSetting(setting_name)
                except Exception as e:
                    setting = 'No Setting'

            if setting != 'No Setting':
                setting_map[setting_name] = setting

        # Does not have provider suffix
        setting = Settings.getSetting('backend')
        setting_map[Settings.BACKEND] = setting

        #setSetting('use_temp_settings', True)
        cls._logger.debug_verbose('setting use_temp_settings')
        cls.use_temp_settings = True

        for key, value in setting_map.items():
            cls._logger.debug_verbose('backend_changed saving: {} value: {}'
                                      .format(key, value))
            Settings.setSetting(key, value)
    '''
    @classmethod
    def getExpandedSettingId(cls, setting_id: str) -> str:
        #
        # Make sure that we haven't already been expanded
        tmp_id: List[str] = setting_id.split(sep=".", maxsplit=2)
        real_key: str
        if len(tmp_id) > 1:
            cls._logger.debug(f'already expanded: {setting_id}')
            real_key = setting_id
        else:
            suffix: str = ''
            if setting_id not in cls.TOP_LEVEL_SETTINGS:
                suffix = "." + cls._current_backend

            real_key: str = setting_id + suffix
        cls._logger.debug(f'in: {setting_id} out: {real_key} len(tmp_id): {len(tmp_id)}')
        return real_key

    @classmethod
    def getRealSetting(cls, setting_id: str, default_value: Any) -> Any:
        real_key = cls.getExpandedSettingId(setting_id)
        match cls._settings_types[setting_id]:
            case SettingType.BOOLEAN_TYPE:
                return cls.KODI_SETTINGS.getBool(real_key, default_value)
            case SettingType.BOOLEAN_LIST_TYPE:
                return cls.KODI_SETTINGS.getBoolList(real_key, default_value)
            case SettingType.FLOAT_TYPE:
                return cls.KODI_SETTINGS.getNumber(real_key, default_value)
            case SettingType.FLOAT_LIST_TYPE:
                return cls.KODI_SETTINGS.getNumberList(real_key, default_value)
            case SettingType.INTEGER_TYPE:
                return cls.KODI_SETTINGS.getInt(real_key, default_value)
            case SettingType.INTEGER_LIST_TYPE:
                return cls.KODI_SETTINGS.getIntList(real_key, default_value)
            case SettingType.STRING_TYPE:
                return cls.KODI_SETTINGS.getString(real_key, default_value)
            case SettingType.STRING_LIST_TYPE:
                return cls.KODI_SETTINGS.getStringList(real_key, default_value)

    '''
    @classmethod
    def setSetting(cls, setting_id: str, value: Any) -> None:
        suffix: str = ''
        if setting_id not in cls.TOP_LEVEL_SETTINGS:
            suffix = "." + cls._current_backend

        real_key: str = setting_id + suffix
        match cls._settings_types[setting_id]:
            case SettingType.BOOLEAN_TYPE:
                cls.KODI_SETTINGS.setBool(real_key, value)
            case SettingType.BOOLEAN_LIST_TYPE:
                cls.KODI_SETTINGS.setBoolList(real_key, value)
            case SettingType.FLOAT_TYPE:
                cls.KODI_SETTINGS.setNumber(real_key, value)
            case SettingType.FLOAT_LIST_TYPE:
                cls.KODI_SETTINGS.setNumberList(real_key, value)
            case SettingType.INTEGER_TYPE:
                cls.KODI_SETTINGS.setInt(real_key, value)
            case SettingType.INTEGER_LIST_TYPE:
                cls.KODI_SETTINGS.setIntList(real_key, value)
            case SettingType.STRING_TYPE:
                cls.KODI_SETTINGS.setString(real_key, value)
            case SettingType.STRING_LIST_TYPE:
                cls.KODI_SETTINGS.setStringList(real_key, value)
    '''

    @classmethod
    def commit_settings(cls):
        for key, value in CurrentCachedSettings.get_settings().items():
            key: str
            value: Any
            match cls._settings_types[key]:
                case SettingType.BOOLEAN_TYPE:
                    cls.KODI_SETTINGS.setBool(key, value)
                case SettingType.BOOLEAN_LIST_TYPE:
                    cls.KODI_SETTINGS.setBoolList(key, value)
                case SettingType.FLOAT_TYPE:
                    cls.KODI_SETTINGS.setNumber(key, value)
                case SettingType.FLOAT_LIST_TYPE:
                    cls.KODI_SETTINGS.setNumberList(key, value)
                case SettingType.INTEGER_TYPE:
                    cls.KODI_SETTINGS.setInt(key, value)
                case SettingType.INTEGER_LIST_TYPE:
                    cls.KODI_SETTINGS.setIntList(key, value)
                case SettingType.STRING_TYPE:
                    cls.KODI_SETTINGS.setString(key, value)
                case SettingType.STRING_LIST_TYPE:
                    cls.KODI_SETTINGS.setStringList(key, value)

    @classmethod
    def getSetting(cls, setting_id: str, default_value: Any | None = None) -> Any:
        real_key = cls.getExpandedSettingId(setting_id)
        if CurrentCachedSettings.is_empty():
            backend_id: str = cls.get_backend_id(ignore_cache=True)
            cls.reload_settings()

        value: Any = CurrentCachedSettings.get_setting(real_key, default_value)
        cls._logger.debug(f'setting_id: {real_key} value: {value}')
        return value

    @classmethod
    def setSetting(cls, setting_id: str, value: Any) -> None:
        real_key = cls.getExpandedSettingId(setting_id)
        CurrentCachedSettings.set_setting(real_key, value)

    @classmethod
    def get_setting_str(cls, setting_id: str, ignore_cache: bool = False,
                        default_value: str = None) -> str:
        real_key = cls.getExpandedSettingId(setting_id)
        if ignore_cache:
            return cls.KODI_SETTINGS.getString(real_key)

        return CurrentCachedSettings.get_setting(real_key, default_value)

    @classmethod
    def set_setting_str(cls, setting_id: str, value: str) -> None:
        real_key = cls.getExpandedSettingId(setting_id)
        CurrentCachedSettings.set_setting(real_key, value)
        # return cls.KODI_SETTINGS.setString(setting_name, value)

    @classmethod
    def get_setting_bool(cls, setting_id: str, default_value: bool = None) -> bool:
        """

        :return:
        """
        real_key = cls.getExpandedSettingId(setting_id)
        return CurrentCachedSettings.get_setting(real_key, default_value)

    @classmethod
    def set_setting_bool(cls, setting_id: str, value: bool) -> None:
        """
        :setting:
        :value:
        :return:
        """
        #
        # Make sure that we haven't already been expanded
        real_key = cls.getExpandedSettingId(setting_id)
        CurrentCachedSettings.set_setting(real_key, value)
        # return Settings.KODI_SETTINGS.setBool(setting_name, value)

    @classmethod
    def get_setting_float(cls, setting_id: str, default_value: float = 0.0) -> float:
        """

        :return:
        """
        real_key = cls.getExpandedSettingId(setting_id)
        return CurrentCachedSettings.get_setting(real_key, default_value)

    @classmethod
    def set_setting_float(cls, setting_id: str, value: float) -> None:
        """

        :return:
        """
        # try:
        #     return Settings.KODI_SETTINGS.setNumber(setting_name, value)
        # except:
        #     Settings._logger.error(f'Exception Setting: {setting_name}')
        real_key = cls.getExpandedSettingId(setting_id)
        CurrentCachedSettings.set_setting(real_key, value)

    @classmethod
    def get_setting_int(cls, setting_id: str, default_value: int = 0) -> int:
        """

        :return:
        """
        #
        # Make sure that we haven't already been expanded
        real_key = cls.getExpandedSettingId(setting_id)
        return CurrentCachedSettings.get_setting(real_key, default_value)

    @classmethod
    def set_setting_int(cls, setting_id: str, value: int) -> None:
        """

        :return:
        """
        # try:
        #     return Settings.KODI_SETTINGS.setInt(setting_name, int)
        # except Exception as e:
        #     Settings._logger.error(f'Exception Setting: {setting_name}.')
        real_key = cls.getExpandedSettingId(setting_id)
        CurrentCachedSettings.set_setting(real_key, value)

    @classmethod
    def update_cached_setting(cls, setting_id: str, value: Any) -> None:
        real_key = cls.getExpandedSettingId(setting_id)
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
