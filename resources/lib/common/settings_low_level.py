# -*- coding: utf-8 -*-
import sys
from contextlib import AbstractContextManager
import copy
import threading
import time

from common.typing import *

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
        value = cls._current_settings.get(setting_id)
        if value is None:
            value = default_value
            if setting_id == 'converter':
                cls._logger.dump_stack('Converter problem')
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


class SettingsContext(AbstractContextManager):
    # module_logger = BasicLogger.get_module_logger(module_path=__file__)
    # _logger: BasicLogger = None

    def __init__(self):
        clz = type(self)
        # clz._logger = module_logger.getChild(clz.__name__)
        self.ks: xbmcaddon.Settings = None

    def __enter__(self) -> ForwardRef('SettingsContext'):
        self.ks = xbmcaddon.Addon("service.kodi.tts").getSettings()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        clz = type(self)
        try:
            del self.ks
            self.ks = None
            pass
        except Exception as e:
            # clz._logger.exception('')
            pass

        if exc_type is not None:
            return False
        else:
            return True


class SettingsWrapper:

    # new_api = xbmcaddon.Addon("service.kodi.tts").getSettings()
    old_api = xbmcaddon.Addon()
    _logger : BasicLogger = None

    def __init__(self):
        clz = type(self)
        #  clz._logger = module_logger.getChild(clz.__name__)

    def getBool(self, id: str) -> bool:
        """
        Returns the value of a setting as a boolean.

        :param id: string - id of the setting that the module needs to access.
        :return: bool - Setting as a boolean

        @python_v20 New function added.

        Example::

            ..
            enabled = settings.getBool('enabled')
            ..
        """
        clz = type(self)
        try:
            value = clz.old_api.getSettingBool(id)
        except TypeError:
            value = None

        if isinstance(value, str):
            value = value.lower() == 'true'

        return value

    def getInt(self, id: str) -> int:
        """
        Returns the value of a setting as an integer.

        :param id: string - id of the setting that the module needs to access.
        :return: integer - Setting as an integer

        @python_v20 New function added.

        Example::

            ..
            max = settings.getInt('max')
            ..
        """
        clz = type(self)
        value: int = None
        try:
            value = clz.old_api.getSettingInt(id)
        except TypeError as e:
            value = None
        return value


    def getNumber(self, id: str) -> float:
        """
        Returns the value of a setting as a floating point number.

        :param id: string - id of the setting that the module needs to access.
        :return: float - Setting as a floating point number

        @python_v20 New function added.

        Example::

            ..
            max = settings.getNumber('max')
            ..
        """
        clz = type(self)
        value: float | None = 0.0
        try:
            value: float =  clz.old_api.getSettingNumber(id)
        except TypeError:
            clz._logger.error(f'Setting {id} is not a float. Setting to None/default')
            value = None
        return value

    def getString(self, id: str) -> str:
        """
        Returns the value of a setting as a unicode string.

        :param id: string - id of the setting that the module needs to access.
        :return: string - Setting as a unicode string

        @python_v20 New function added.

        Example::

            ..
            apikey = settings.getString('apikey')
            ..
        """
        clz = type(self)
        value: str | None = None
        try:
            value = clz.old_api.getSettingString(id)
        except TypeError as e:
            value = None
        return value

    def getBoolList(self, id: str) -> List[bool]:
        """
        Returns the value of a setting as a list of booleans.

        :param id: string - id of the setting that the module needs to access.
        :return: list - Setting as a list of booleans

        @python_v20 New function added.

        Example::

            ..
            enabled = settings.getBoolList('enabled')
            ..
        """
        raise NotImplementedError()

    def getIntList(self, id: str) -> List[int]:
        """
        Returns the value of a setting as a list of integers.

        :param id: string - id of the setting that the module needs to access.
        :return: list - Setting as a list of integers

        @python_v20 New function added.

        Example::

            ..
            ids = settings.getIntList('ids')
            ..
        """
        raise NotImplementedError()

    def getNumberList(self, id: str) -> List[float]:
        """
        Returns the value of a setting as a list of floating point numbers.

        :param id: string - id of the setting that the module needs to access.
        :return: list - Setting as a list of floating point numbers

        @python_v20 New function added.

        Example::

            ..
            max = settings.getNumberList('max')
            ..
        """
        raise NotImplementedError()

    def getStringList(self, id: str) -> List[str]:
        """
        Returns the value of a setting as a list of unicode strings.

        :param id: string - id of the setting that the module needs to access.
        :return: list - Setting as a list of unicode strings

        @python_v20 New function added.

        Example::

            ..
            views = settings.getStringList('views')
            ..
        """
        raise NotImplementedError()

    def setBool(self, id: str, value: bool) -> None:
        """
        Sets the value of a setting.

        :param id: string - id of the setting that the module needs to access.
        :param value: bool - value of the setting.
        :return: bool - True if the value of the setting was set, false otherwise

        .. note::
            You can use the above as keywords for arguments.

        @python_v20 New function added.

        Example::

            ..
            settings.setBool(id='enabled', value=True)
            ..
        """
        clz = type(self)
        value = clz.old_api.setSettingBool(id, value)


    def setInt(self, id: str, value: int) -> None:
        """
        Sets the value of a setting.

        :param id: string - id of the setting that the module needs to access.
        :param value: integer - value of the setting.
        :return: bool - True if the value of the setting was set, false otherwise

        .. note::
            You can use the above as keywords for arguments.

        @python_v20 New function added.

        Example::

            ..
            settings.setInt(id='max', value=5)
            ..
        """
        clz = type(self)
        clz.old_api.setSettingInt(id, value)

    def setNumber(self, id: str, value: float) -> None:
        """
        Sets the value of a setting.

        :param id: string - id of the setting that the module needs to access.
        :param value: float - value of the setting.
        :return: bool - True if the value of the setting was set, false otherwise

        .. note::
            You can use the above as keywords for arguments.

        @python_v20 New function added.

        Example::

            ..
            settings.setNumber(id='max', value=5.5)
            ..
        """
        clz = type(self)
        clz.old_api.setSettingNumber(id, value)

    def setString(self, id: str, value: str) -> None:
        """
        Sets the value of a setting.

        :param id: string - id of the setting that the module needs to access.
        :param value: string or unicode - value of the setting.
        :return: bool - True if the value of the setting was set, false otherwise

        .. note::
            You can use the above as keywords for arguments.

        @python_v20 New function added.

        Example::

            ..
            settings.setString(id='username', value='teamkodi')
            ..
        """
        clz = type(self)
        clz.old_api.setSettingString(id, value)

    def setBoolList(self, id: str, values: List[bool]) -> None:
        """
        Sets the boolean values of a list setting.

        :param id: string - id of the setting that the module needs to access.
        :param values: list of boolean - values of the setting.
        :return: bool - True if the values of the setting were set, false otherwise

        .. note::
            You can use the above as keywords for arguments.

        @python_v20 New function added.

        Example::

            ..
            settings.setBoolList(id='enabled', values=[ True, False ])
            ..
        """
        pass

    def setIntList(self, id: str, values: List[int]) -> None:
        """
        Sets the integer values of a list setting.

        :param id: string - id of the setting that the module needs to access.
        :param values: list of int - values of the setting.
        :return: bool - True if the values of the setting were set, false otherwise

        .. note::
            You can use the above as keywords for arguments.

        @python_v20 New function added.

        Example::

            ..
            settings.setIntList(id='max', values=[ 5, 23 ])
            ..
        """
        pass

    def setNumberList(self, id: str, values: List[float]) -> None:
        """
        Sets the floating point values of a list setting.

        :param id: string - id of the setting that the module needs to access.
        :param values: list of float - values of the setting.
        :return: bool - True if the values of the setting were set, false otherwise

        .. note::
            You can use the above as keywords for arguments.

        @python_v20 New function added.

        Example::

            ..
            settings.setNumberList(id='max', values=[ 5.5, 5.8 ])
            ..
        """
        pass

    def setStringList(self, id: str, values: List[str]) -> None:
        """
        Sets the string values of a list setting.

        :param id: string - id of the setting that the module needs to access.
        :param values: list of string or unicode - values of the setting.
        :return: bool - True if the values of the setting were set, false otherwise

        .. note::
            You can use the above as keywords for arguments.

        @python_v20 New function added.

        Example::

            ..
            settings.setStringList(id='username', values=[ 'team', 'kodi' ])
            ..
        """
        pass


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
    settings_wrapper = SettingsWrapper()

    _initialized: bool = False
    _loading: threading.Event = threading.Event()
    _loading.set() # Enable

    @classmethod
    def init(cls):
        if not cls._initialized:
            cls._initialized = True
            cls._logger = module_logger.getChild(cls.__name__)
            cls._current_engine = None

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
            #  cls._logger.debug('Backed up settings')
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
        # SettingsLowLevel._logger.debug('entered')
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
            # Get Lock
            engine_id: str = cls.load_setting(SettingsProperties.ENGINE)
            force_load: bool = False
            for setting_id in SettingsProperties.ALL_SETTINGS:
                value: Any | None
                service_id: str = engine_id
                key: str = cls.getExpandedSettingId(setting_id, engine_id)
                if setting_id not in SettingsProperties.TOP_LEVEL_SETTINGS:
                    if SettingsMap.is_valid_property(service_id, setting_id):
                        value = cls.load_setting(setting_id, engine_id)
                    elif force_load:
                        cls._logger.debug(f'FORCED load of property: {setting_id}')
                        value = cls.load_setting(setting_id, engine_id)
                    else:
                        cls._logger.debug(f'Skipping load of property: {setting_id} '
                                          f'for service_id: {service_id}')
                        continue
                else:
                    if SettingsMap.is_valid_property(Services.TTS_SERVICE, setting_id):
                        value = cls.load_setting(setting_id)
                    elif force_load:
                        cls._logger.debug(f'FORCED load of property: {setting_id}')
                        value = cls.load_setting(setting_id)
                    else:
                        cls._logger.debug(f'Skipping load of top-level (.tts) property: '
                                          f'{setting_id}')
                    continue
                if value is not None:
                    new_settings[key] = value

            cls._current_engine = engine_id

            # validate_settings new_settings
            CurrentCachedSettings.set_settings(new_settings)
            # release lock
            # Notify
        finally:
            cls._loading.set()

    @classmethod
    def load_setting(cls, setting_id: str,
                     engine_id: str = None) -> Any | None:
        if engine_id is None:
            engine_id = Services.TTS_SERVICE

        found: bool = True
        force_load: bool = False
        if not force_load and not SettingsMap.is_valid_property(engine_id, setting_id):
            found = False
            cls._logger.debug(f'Setting {setting_id} NOT supported for {engine_id}')
        key: str = cls.getExpandedSettingId(setting_id, engine_id)
        value: Any | None = None
        try:
            match SettingsProperties.SettingTypes[setting_id]:
                case SettingType.BOOLEAN_TYPE:
                    value = cls.settings_wrapper.getBool(key)
                case SettingType.BOOLEAN_LIST_TYPE:
                    value = cls.settings_wrapper.getBoolList(key)
                case SettingType.FLOAT_TYPE:
                    value = cls.settings_wrapper.getNumber(key)
                case SettingType.FLOAT_LIST_TYPE:
                    value = cls.settings_wrapper.getNumberList(key)
                case SettingType.INTEGER_TYPE:
                    value = cls.settings_wrapper.getInt(key)
                case SettingType.INTEGER_LIST_TYPE:
                    value = cls.settings_wrapper.getIntList(key)
                case SettingType.STRING_TYPE:
                    value = cls.settings_wrapper.getString(key)
                case SettingType.STRING_LIST_TYPE:
                    value = cls.settings_wrapper.getStringList(key)
            # cls._logger.debug(f'found key: {key} value: {value}')
        except KeyError:
            cls._logger.exception(
                    f'failed to find setting key: {key}. '
                    f'Probably not defined in resources/settings.xml')
        except TypeError:
            cls._logger.exception(f'failed to get type of setting: {key}.{engine_id} ')
            if force_load:
                try:
                    value_str: str = xbmcaddon.Addon("service.kodi.tts").getSetting(key)
                    if value_str is None:
                        value = None
                    else:
                        match SettingsProperties.SettingTypes[setting_id]:
                            case SettingType.BOOLEAN_TYPE:
                                value = bool(value_str)
                            case SettingType.FLOAT_TYPE:
                                value = float(value_str)
                            case SettingType.INTEGER_TYPE:
                                value = int(value_str)
                            case SettingType.STRING_TYPE:
                                value = value_str
                except Exception as e:
                    cls._logger.debug(f'Second attempt to read setting {setting_id} failed')
        if value is None:
            value = SettingsMap.get_default_value(engine_id, setting_id)
        return value

    @classmethod
    def configuring_settings(cls):
        #  cls._logger.debug('configuring_settings hardcoded to false')
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
                if backend is None:
                    backend = cls._current_engine
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
                    return cls.settings_wrapper.getBool(real_key)
                case SettingType.BOOLEAN_LIST_TYPE:
                    return cls.settings_wrapper.getBoolList(real_key)
                case SettingType.FLOAT_TYPE:
                    return cls.settings_wrapper.getNumber(real_key)
                case SettingType.FLOAT_LIST_TYPE:
                    return cls.settings_wrapper.getNumberList(real_key)
                case SettingType.INTEGER_TYPE:
                    return cls.settings_wrapper.getInt(real_key)
                case SettingType.INTEGER_LIST_TYPE:
                    return cls.settings_wrapper.getIntList(real_key)
                case SettingType.STRING_TYPE:
                    return cls.settings_wrapper.getString(real_key)
                case SettingType.STRING_LIST_TYPE:
                    return cls.settings_wrapper.getStringList(real_key)
        except Exception as e:
            cls._logger.exception('')

    @classmethod
    def commit_settings(cls):
        #  cls._logger.debug('TRACE commit_settings')
        addon: xbmcaddon.Addon = xbmcaddon.Addon('service.kodi.tts')

        for full_setting_id, value in CurrentCachedSettings.get_settings().items():
            full_setting_id: str
            value: Any
            value_type: SettingType | None = None
            str_value: str = ''
            try:
                str_value = str(value)
                if full_setting_id == SettingsProperties.ENGINE:
                    cls._logger.debug(f'TRACE Commiting ENGINE value: {str_value}')

                cls._logger.debug(f'id: {full_setting_id} value: {str_value}')
                prefix: str = cls.getSettingIdPrefix(full_setting_id)
                value_type = SettingsProperties.SettingTypes.get(prefix, None)
                if value == 'NO_VALUE':
                    cls._logger.debug(f'Expected setting not found {prefix}')
                    continue

                match value_type:
                    case SettingType.BOOLEAN_TYPE:
                         cls.settings_wrapper.setBool(full_setting_id, value)
                    case SettingType.BOOLEAN_LIST_TYPE:
                        cls.settings_wrapper.setBoolList(full_setting_id, value)
                    case SettingType.FLOAT_TYPE:
                        cls.settings_wrapper.setNumber(full_setting_id, value)
                    case SettingType.FLOAT_LIST_TYPE:
                        cls.settings_wrapper.setNumberList(full_setting_id, value)
                    case SettingType.INTEGER_TYPE:
                        cls.settings_wrapper.setInt(full_setting_id, value)
                    case SettingType.INTEGER_LIST_TYPE:
                        cls.settings_wrapper.setIntList(full_setting_id, value)
                    case SettingType.STRING_TYPE:
                        cls.settings_wrapper.setString(full_setting_id, value)
                    case SettingType.STRING_LIST_TYPE:
                        cls.settings_wrapper.setStringList(full_setting_id, value)
            except Exception as e:
                cls._logger.exception('')
                cls._logger.exception(f'Error saving setting: {full_setting_id} '
                                      f'value: {str_value} as '
                                      f'{value_type.name}')

    @classmethod
    def get_engine_id(cls, default: str = None,
                      bootstrap: bool = False) -> str:
        """
        :return:
        """
        ignore_cache = True
        engine_id: str = None
        if bootstrap:
            ignore_cache = True
        elif cls._current_engine is not None:
            engine_id = cls._current_engine
        if engine_id is None:
            engine_id = cls.get_setting_str(SettingsProperties.ENGINE, engine_id=None,
                                             ignore_cache=ignore_cache,
                                             default=default)
        #  cls._logger.debug(f'TRACE get_engine_id: {engine_id}')
        cls._current_engine = engine_id
        return engine_id

    @classmethod
    def set_backend_id(cls, backend_id: str) -> None:
        #  cls._logger.debug(f'TRACE set backend_id: {backend_id}')
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
            cls._logger.exception('')
            cls._logger.debug(f'TRACE: type mismatch')

    @classmethod
    def check_reload(cls):
        if CurrentCachedSettings.is_empty():
            cls.load_settings()

    @classmethod
    def getSetting(cls, setting_id: str, backend_id: str | None,
                   default_value: Any | None = None) -> Any:
        if setting_id == SettingsProperties.ENGINE:
            return cls.get_engine_id()
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        cls.check_reload()

        value: Any = cls._getSetting(setting_id, backend_id, default_value)
        cls._logger.debug(f'setting_id: {real_key} value: {value}')
        return value

    @classmethod
    def _getSetting(cls, setting_id: str, backend_id: str | None,
                    default_value: Any | None = None) -> Any:
        value: Any = None
        full_setting_id = cls.getExpandedSettingId(setting_id, backend_id)
        try:
            cls.check_reload()
            value: Any = CurrentCachedSettings.get_setting(full_setting_id, default_value)
        except KeyError:
            value = SettingsLowLevel.getRealSetting(setting_id, backend_id, default_value)
            CurrentCachedSettings.set_setting(full_setting_id, value)
        # cls._logger.debug(f'setting_id: {full_setting_id} value: {value}')
        return value

    @classmethod
    def set_setting_str(cls, setting_id: str, value: str, engine_id: str = None) -> bool:
        if setting_id == SettingsProperties.ENGINE:
            cls._logger.debug(f'TRACE engine_id: {value}')
        real_key = cls.getExpandedSettingId(setting_id, engine_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        passed: bool = CurrentCachedSettings.set_setting(real_key, value)
        return passed

    @classmethod
    def get_setting_str(cls, setting_id: str, engine_id: str = None,
                        ignore_cache: bool = False,
                        default: str = None) -> str:
        force_load: bool = False
        if ignore_cache and setting_id == SettingsProperties.ENGINE:
            cls._logger.debug(f'TRACE get_setting_str IGNORING CACHE id: {setting_id}')
        real_key = cls.getExpandedSettingId(setting_id, engine_id)
        if ignore_cache:
            try:
                value: str = cls.settings_wrapper.getString(real_key)
                return value
            except Exception as e:
                cls._logger.exception('')
                return default
        return cls._getSetting(setting_id, engine_id, default)

    @classmethod
    def get_setting_bool(cls, setting_id: str, engine_id: str = None,
                         ignore_cache: bool = False,
                         default: bool = None) -> bool:
        """

        :return:
        """
        if ignore_cache and setting_id == SettingsProperties.ENGINE:
            cls._logger.debug(f'TRACE get_setting_str IGNORING CACHE id: {setting_id}')
        real_key = cls.getExpandedSettingId(setting_id, engine_id)
        if ignore_cache:
            try:
                return cls.settings_wrapper.getBool(real_key)
            except Exception as e:
                cls._logger.exception('')
        return cls._getSetting(setting_id, engine_id, default)

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
        cls.check_reload()
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
