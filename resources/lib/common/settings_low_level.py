# -*- coding: utf-8 -*-

import copy
import threading
import time
from typing import *

import xbmcaddon

from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties, SettingType
from backends.settings.settings_map import SettingsMap
from common.monitor import Monitor
from common.constants import Constants
from common.logger import *
from kutils.kodiaddon import Addon

module_logger = BasicLogger.get_module_logger(module_path=__file__)


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
        """
        throws KeyError
        """
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


class SettingsLowLevel:
    """
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
    """
    _current_engine: str = None
    _logger: BasicLogger = None
    kodi_settings: xbmcaddon.Settings = xbmcaddon.Addon("service.kodi.tts").getSettings()

    _initialized: bool = False
    _loading: threading.Event = threading.Event()
    _loading.set() # Enable

    @classmethod
    def init(cls):
        if not cls._initialized:
            cls._initialized = True
            cls._logger = module_logger.getChild(cls.__name__)
            cls._current_engine = None
            kodi_settings = xbmcaddon.Addon("service.kodi.tts").getSettings()
            # cls.load_settings()

    @staticmethod
    def get_addon() -> Addon:
        """

        :return:
        """

        if SettingsLowLevel._addon_singleton is None:
            try:
                SettingsLowLevel._addon_singleton = Addon(Constants.ADDON_ID)
            except Exception:
                pass

        return SettingsLowLevel._addon_singleton

    @staticmethod
    def on_settings_changed() -> None:
        """

        :return:
        """
        # SettingsLowLevel.load_settings()

    @classmethod
    def save_settings(cls) -> None:
        """

        :return:
        """
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
        """

        :param settings_to_check:
        :return:
        """
        SettingsLowLevel._logger.debug('entered')
        changed_settings = []
        for setting_id in settings_to_check:
            previous_value = PreviousCachedSettings.get_setting(setting_id, None)
            try:
                current_value = SettingsLowLevel.get_addon().setting(setting_id)
            except Exception:
                current_value = previous_value

            if previous_value != current_value:
                changed = True
                if module_logger.isEnabledFor(DEBUG):
                    SettingsLowLevel._logger.debug(f'setting changed: {setting_id} '
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
        """

        """
        setting_id: str = ""
        engine_id: str = None
        type_error: bool = False
        expected_type: str = ''
        if full_setting_id not in SettingsProperties.TOP_LEVEL_SETTINGS:
            engine_id, setting_id = cls.splitSettingId(full_setting_id)
        else:
            setting_id = full_setting_id

        if engine_id is None:
            engine_id = Services.TTS_SERVICE

        if not SettingsMap.is_valid_property(engine_id, setting_id):
            cls._logger.debug(
                f'TRACE Setting {setting_id} NOT supported for {engine_id}')
        PROTO_LIST_BOOLS: List[bool] = [True, False]
        PROTO_LIST_FLOATS: List[float] = [0.7, 8.2]
        PROTO_LIST_INTEGERS: List[int] = [1, 57]
        PROTO_LIST_STRINGS: List[str] = ['a', 'b']
        try:
            match SettingsProperties.SettingTypes[setting_id]:
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
        """
        Load ALL of the settings for the current backend.
        Settings from multiple backends can be in the cache simultaneously
        Settings not supported by a backend are not read and not put into
        the cache. The settings.xml can have orphaned settings as long as
        kodi allows it, based on the rules in the addon's settings.xml definition
        file.

        Ignore any other changes to settings until finished
        """

        cls._logger.debug('TRACE load_settings')
        blocked: bool = False
        while not cls._loading.is_set():
            # If some other thread is loading, wait until finished, then exit.
            # The assumption is that a reload after a reload is not needed.
            # Besides, the code will still load from settings.xml when needed.

            blocked = True
            Monitor.wait_for_abort(timeout=0.10)

        try:
            cls._loading.clear()
            if blocked:
                return
            new_settings: Dict[str, Any] = {}
            cls.kodi_settings = xbmcaddon.Addon("service.kodi.tts").getSettings()
            # Get Lock
            backend_id: str = cls.load_setting(SettingsProperties.ENGINE)

            for setting_id in SettingsProperties.ALL_SETTINGS:
                key: str = setting_id
                value: Any | None
                service_id: str = backend_id
                if setting_id not in SettingsProperties.TOP_LEVEL_SETTINGS:
                    if SettingsMap.is_valid_property(service_id, setting_id):
                        value = cls.load_setting(setting_id, backend_id)
                    else:
                        cls._logger.debug(f'Skipping load of property: {setting_id} '
                                          f'for service_id: {service_id}')
                        continue
                else:
                    if SettingsMap.is_valid_property(Services.TTS_SERVICE, setting_id):
                        value = cls.load_setting(setting_id)
                    else:
                        cls._logger.debug(f'Skipping load of top-level property: '
                                          f'{setting_id}')
                        continue
                if value is not None:
                    new_settings[key] = value

            cls._current_engine = backend_id

            # validate_settings new_settings
            CurrentCachedSettings.set_settings(new_settings)
            # release lock
            # Notify
        finally:
            cls._loading.set()

    @classmethod
    def load_setting(cls, setting_id: str, engine_id: str = None) -> Any | None:
        key: str = setting_id
        if engine_id is None:
            engine_id = Services.TTS_SERVICE

        found: bool = True
        if not SettingsMap.is_valid_property(engine_id, setting_id):
            found = False
            cls._logger.debug(f'Setting {setting_id} NOT supported for {engine_id}')

        value: Any | None = None
        try:
            match SettingsProperties.SettingTypes[setting_id]:
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
            value = SettingsMap.get_default_value(engine_id, setting_id)
        return value

    @classmethod
    def configuring_settings(cls):
        cls._logger.debug('configuring_settings hardcoded to false')
        return False

    @classmethod
    def getExpandedSettingId(cls, setting_id: str, backend: str) -> str:
        tmp_id: List[str] = setting_id.split(sep=".", maxsplit=2)
        real_key: str
        if len(tmp_id) > 1:
        #     cls._logger.debug(f'already expanded: {setting_id}')
            real_key = setting_id
        else:
            suffix: str = ''
            if setting_id not in SettingsProperties.TOP_LEVEL_SETTINGS:
                suffix = "." + backend

            real_key: str = setting_id + suffix
        # cls._logger.debug(
        #         f'in: {setting_id} out: {real_key} len(tmp_id): {len(tmp_id)}')
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
            backend_id = cls._current_engine
            if backend_id is None or len(backend_id) == 0:
                cls._logger.error("TRACE null or empty backend")
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        try:
            match SettingsProperties.SettingTypes[setting_id]:
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
                if full_setting_id == SettingsProperties.ENGINE:
                    cls._logger.debug(f'TRACE Commiting BACKEND value: {str_value}')

                cls._logger.debug(f'id: {full_setting_id} value: {str_value}')
                prefix: str = cls.getSettingIdPrefix(full_setting_id)
                value_type = SettingsProperties.SettingTypes.get(prefix, None)
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
    def get_engine_id(cls, bootstrap: bool = False) -> str:
        """
        :return:
        """
        engine_id: str = cls.get_setting_str(SettingsProperties.ENGINE, engine_id=None,
                                             ignore_cache=False,
                                             default_value=None)
        cls._logger.debug(f'TRACE get_engine_id: {engine_id}')
        cls._current_engine = engine_id
        return engine_id

    @classmethod
    def set_backend_id(cls, backend_id: str) -> None:
        cls._logger.debug(f'TRACE set backend_id: {backend_id}')
        if backend_id is None or len(backend_id) == 0:
            cls._logger.debug(f'invalid backend_id Not saving')
            return

        cls.set_setting_str(SettingsProperties.ENGINE, backend_id)
        cls._current_engine = backend_id

    @classmethod
    def setSetting(cls, setting_id: str, value: Any,
                   engine_id_id: str) -> bool:

        real_key = cls.getExpandedSettingId(setting_id, engine_id_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        try:
            success: bool = CurrentCachedSettings.set_setting(real_key, value)
            return success
        except:
            cls._logger.debug(f'TRACE: type mismatch')

    @classmethod
    def getSetting(cls, setting_id: str, backend_id: str | None,
                   default_value: Any | None = None) -> Any:
        if backend_id is None:
            backend_id = cls._current_engine
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        if CurrentCachedSettings.is_empty():
            cls.load_settings()

        value: Any = cls._getSetting(setting_id, backend_id, default_value)
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
            value = SettingsLowLevel.getRealSetting(setting_id, backend_id, default_value)
            CurrentCachedSettings.set_setting(full_setting_id, value)
        # cls._logger.debug(f'setting_id: {full_setting_id} value: {value}')
        return value

    @classmethod
    def set_setting_str(cls, setting_id: str, value: str, backend_id: str = None) -> bool:
        if setting_id == SettingsProperties.ENGINE:
            cls._logger.debug(f'TRACE set_backend_id: {value}')
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        passed: bool = CurrentCachedSettings.set_setting(real_key, value)
        return passed

    @classmethod
    def get_setting_str(cls, setting_id: str, engine_id: str = None,
                        ignore_cache: bool = False,
                        default_value: str = None) -> str:
        if ignore_cache and setting_id == SettingsProperties.ENGINE:
            cls._logger.debug(f'TRACE get_setting_str IGNORING CACHE id: {setting_id}')
        real_key = cls.getExpandedSettingId(setting_id, engine_id)
        if ignore_cache:
            return cls.kodi_settings.getString(real_key)

        return cls._getSetting(setting_id, engine_id, default_value)

    @classmethod
    def get_setting_bool(cls, setting_id: str, backend_id: str = None,
                         default_value: bool = None) -> bool:
        """

        :return:
        """
        return cls._getSetting(setting_id, backend_id, default_value)

    @classmethod
    def set_setting_bool(cls, setting_id: str, value: bool, backend_id: str = None) -> bool:
        """

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
        return SettingsLowLevel._getSetting(setting_id, backend_id, default_value)

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


SettingsLowLevel.init()
