# -*- coding: utf-8 -*-

import binascii

import xbmc
import xbmcaddon

from common.constants import Constants
from common.logger import LazyLogger
from typing import Type, Any, Callable, Union, List

module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)


class Settings:
    # TOP LEVEL SETTINGS
    AUTO_ITEM_EXTRA = 'auto_item_extra'
    AUTO_ITEM_EXTRA_DELAY = 'auto_item_extra_delay'
    BACKEND = 'backend'
    BACKEND_DEFAULT = 'auto'
    BACKGROUND_PROGRESS_INTERVAL = 'background_progress_interval'
    SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA = 'speak_background_progress_during_media'
    SPEAK_BACKGROUND_PROGRESS = 'speak_background_progress'
    CACHE_PATH = 'cache_path'
    CACHE_EXPIRATION_DAYS = 'cache_expiration_days'
    CACHE_EXPIRATION_DEFAULT = 365
    ADDONS_MD5 = 'addons_MD5'
    DISABLE_BROKEN_BACKENDS = 'disable_broken_backends'
    EXTERNAL_COMMAND = 'EXTERNAL_COMMAND'
    DEBUG_LOGGING = 'debug_logging'
    OVERRIDE_POLL_INTERVAL = 'override_poll_interval'
    POLL_INTERVAL = 'poll_interval'
    READER_OFF = 'reader_off'
    SETTINGS_DIGEST = 'settings_digest'
    SPEAK_LIST_COUNT = 'speak_list_count'
    USE_TEMPFS = 'use_tmpfs'
    VERSION = 'version'

    TOP_LEVEL_SETTINGS = (
        AUTO_ITEM_EXTRA,
        AUTO_ITEM_EXTRA_DELAY,
        BACKEND,
        BACKEND_DEFAULT,
        BACKGROUND_PROGRESS_INTERVAL,
        DISABLE_BROKEN_BACKENDS,
        SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
        SPEAK_BACKGROUND_PROGRESS,
        CACHE_PATH,
        CACHE_EXPIRATION_DAYS,
        ADDONS_MD5,
        EXTERNAL_COMMAND,
        DEBUG_LOGGING,
        OVERRIDE_POLL_INTERVAL,
        POLL_INTERVAL,
        READER_OFF,
        SETTINGS_DIGEST,
        SPEAK_LIST_COUNT,
        USE_TEMPFS,
        VERSION
    )

    API_KEY = 'api_key'
    API_KEY_DEFAULT = ''
    CACHE_SPEECH = 'cache_speech'
    CACHE_SPEECH_DEFAULT = False
    GENDER = 'gender'
    GENDER_DEFAULT = 'none'
    LANGUAGE = 'language'
    LANGUAGE_DEFAULT = 'none'
    PITCH = 'pitch'
    PITCH_DEFAULT = None
    SPEED = 'speed'
    SPEED_DEFAULT = None
    VOICE = 'voice'
    VOICE_DEFAULT = 'none'
    VOLUME = 'volume'
    VOLUME_DEFAULT = None

    # Logically, ENGINE_SPEAK and PIPE should be combined into an enum of
    # three values instructing the engine what to do with speech that it produces:
    #   WRITE_TO_FILE, SPEAK (engine itself speaks), PIPE (to some other player).
    #
    # However, we have two settings: ENGINE_SPEAK and PIPE. ENGINE_SPEAK takes
    # precedence. If PIPE is set to 'pipe', then it is considered True, else
    # the engine is to write to file.

    ENGINE_SPEAK = 'engine_speak'  # Voicing engine also speaks
    ENGINE_SPEEK_DEFAULT = None
    PIPE = 'pipe'  # Engine to pipe speech to a player
    PIPE_DEFAULT = None
    PLAYER = 'player'  # Specifies the player

    UNKNOWN_VALUE = 'unknown'

    # Most settings are associated with a player or a voice engine. Such
    # settings have the player or engine name appended to the setting name.
    #
    # Some settings are not associated with a player or engine. The setting
    # names are not modified. Such settings are referred to here as
    # 'top_level_settings'

    top_level_settings = (
        BACKEND,
        ADDONS_MD5,
        CACHE_PATH,
        DEBUG_LOGGING,
        EXTERNAL_COMMAND,
        VERSION
    )

    temp_shadow_settings = {}
    use_temp_settings = False
    cached_settings = {}
    _logger = None

    @classmethod
    def init(cls):
        cls._logger = module_logger.getChild(cls.__name__)

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

    @classmethod
    def _get_setting(cls, key: str, default: Union[str, None] = None):
        setting = cls.cached_settings.get(key, None)
        if setting is None:
            setting = xbmcaddon.Addon().getSetting(key)
            cls._logger.debug_extra_verbose('key: {} value: {} default: {}'
                                            .format(key, setting, default))
            if setting is None:
                setting = default
            cls.cached_settings[key] = setting
        return setting

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

    @classmethod
    def configuring_settings(cls):
        if cls.use_temp_settings:
            cls._logger.debug_verbose('using temp settings')

        return cls.use_temp_settings

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

    @classmethod
    def commit_settings(cls):
        cls.use_temp_settings = False

        for temp_key, value in cls.temp_shadow_settings.items():
            temp_key: str
            key = temp_key.replace('temp.', '', 1)
            cls._set_setting(key, value)

        cls.temp_shadow_settings.clear()


Settings.init()
