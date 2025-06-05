# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import copy
import threading
import time
from contextlib import AbstractContextManager

import xbmcaddon

from common import *

from backends.settings.service_types import (ServiceKey, Services, ServiceType,
                                             ServiceID)
from backends.settings.setting_properties import SettingProp, SettingType
from backends.settings.settings_map import SettingsMap
from common.constants import Constants
from common.critical_settings import CriticalSettings
from common.logger import *
from common.monitor import Monitor
from common.setting_constants import Backends, Players
from common.kodiaddon import Addon

MY_LOGGER = BasicLogger.get_logger(__name__)


class CachedSettings:
    settings: Dict[str, Union[Any, None]] = {}
    settings_changed: bool = False
    settings_update_begin: float = None

    def __init__(self, settings_to_copy: Dict[str, int | bool | str | None]) -> None:
        self.settings = copy.deepcopy(settings_to_copy)
        self.settings_changed = True
        if self.settings_update_begin is None:
            self.settings_update_begin = time.time()

    def __str__(self):
        return (f'settings_changed: {self.settings_changed}\n'
                f'update_begin: {self.settings_update_begin}\n'
                f'settings: {self.settings}')


class SettingsManager:

    # Initialize with one frame

    _settings_lock: threading.RLock = threading.RLock()
    _settings_stack: List[CachedSettings] = [CachedSettings(settings_to_copy={})]

    @classmethod
    def get_lock(cls) -> threading.RLock:
        """
        Should NOT be generally used. Meant to be used in SettingsDialog while
        configuring settings. Typically used when multiple settings changes occur
        within a short time and would prefer for them to all appear to be changed
        atomically.

        :return:
        """
        return cls._settings_lock

    @classmethod
    def set_setting(cls, setting_id: str,
                    value: int | bool | str | None = None) -> bool:
        """
        Backup a single setting to the top frome of save settings
        :param setting_id: full setting name ex. speed.google
        :param value: value of the setting
        :return:
        """
        with cls._settings_lock:
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'setting_id: {setting_id} value: {value}')
            changed: bool = False
            if cls._settings_stack[-1].settings.get(setting_id) != value:
                changed = True
                cls._settings_stack[-1].settings_changed = True
                if cls._settings_stack[-1].settings_update_begin is None:
                    cls._settings_stack[-1].settings_update_begin = time.time()
                cls._settings_stack[-1].settings[setting_id] = value
            return changed

    @classmethod
    def load_setting_to_all_frames(cls, setting_id: str,
                                   value: int | bool | str | None = None) -> bool:
        """
        Ideally all settings are loaded at startup, but this is not so easy to
        do sometimes. This allows settings which are NOT in the cache to be loaded
        into all frames, providing a consistent view of the value.
        :param setting_id: full setting name ex. speed.google
        :param value: value of the setting
        :return:
        """
        with cls._settings_lock:
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'setting_id: {setting_id} value: {value} depth: '
                                   f'{cls.get_stack_depth()}')
            changed: bool = False
            for frame in range(0, cls.get_stack_depth()):
                if cls._settings_stack[frame].settings.get(setting_id) != value:
                    changed = True
                    MY_LOGGER.debug(f'frame: {frame} setting: {setting_id} != {value}')
                    '''
                    Don't record as a change since this is loading from settings.xml.
                    A change indicates that results need to be saved to settings.xml
                    
                    cls._settings_stack[frame].settings_changed = True
                    if cls._settings_stack[frame].settings_update_begin is None:
                        cls._settings_stack[frame].settings_update_begin = time.time()
                    '''
                    cls._settings_stack[frame].settings[setting_id] = value
                    MY_LOGGER.debug(f'{setting_id} in setting_stack[{frame}] = '
                                    f'{setting_id in cls._settings_stack[frame].settings.keys()}')
            return changed

    @classmethod
    def set_settings(cls,
                     settings_to_update: Dict[ServiceID, int | str | bool | None]) -> None:
        for service_key, value in settings_to_update.items():
            cls.set_setting(service_key.short_key, value)

    @classmethod
    def load_settings(cls,
                      settings_to_backup: Dict[str, int | str | bool | None]) -> None:
        """
        Creates a new CachedSettings 'frame' from the given settings. The copy
        becomes the new top frame

        :param settings_to_backup: deep_copy is used to copy
        :return:
        """

        new_frame: CachedSettings = CachedSettings(settings_to_backup)
        with cls._settings_lock:
            cls._settings_stack.append(new_frame)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(
                    f'settings_to_backup len: {len(settings_to_backup)}'
                    f' current_settings len: {len(cls._settings_stack[-1].settings)}')

    @classmethod
    def clear_settings(cls) -> None:
        with cls._settings_lock:
            del cls._settings_stack[0:-1]

    @classmethod
    def push_settings(cls) -> int:
        """
         Creates a new CachedSettings 'frame' from the current top frame. This
         saves the previous version of settings so that it can be restored if
         needed.

         :return:
         """
        with cls._settings_lock:
            current_settings: Dict[str, int | str | bool | None]
            current_settings = cls._settings_stack[-1].settings
            new_frame: CachedSettings = CachedSettings(current_settings)
            cls._settings_stack.append(new_frame)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(
                    f'push_settings settings_to_backup len: {len(current_settings)}'
                    f' current_settings len: {len(cls._settings_stack[-1].settings)}')
        return len(cls._settings_stack)

    @classmethod
    def restore_settings(cls, stack_depth: int = None,
                         settings_changes: Dict[ServiceID, int | str | bool | None] | None = None) -> None:
        """
        Restore the Settings Stack by poping one or more frames.

        :param stack_depth: Specifies what the final stack depth should be.
                            Defaults to poping one frame
        :param settings_changes: If not None, then apply these changes
                                 to stack_top
        """
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'restore_settings stack_depth: {stack_depth} '
                              f'len(_settings_stack): {cls.get_stack_depth()}')
        old_top_frame: CachedSettings
        with cls._settings_lock:
            if stack_depth is not None:
                while stack_depth < cls.get_stack_depth():
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'poping stack_depth: {stack_depth} depth: '
                                          f'{cls.get_stack_depth()}')
                    cls._settings_stack.pop()
            else:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'pop one')
                cls._settings_stack.pop()
            if settings_changes is not None:
                cls.set_settings(settings_changes)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'leaving with stack_depth: {cls.get_stack_depth()}')

    @classmethod
    def get_stack_depth(cls) -> int:
        with cls._settings_lock:
            return len(cls._settings_stack)

    @classmethod
    def get_settings(cls, depth: int = -1) -> Dict[str, Any]:
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'get_settings')
        with cls._settings_lock:
            return copy.deepcopy(cls._settings_stack[-1].settings)

    @classmethod
    def is_in_cache(cls, setting_id: str) -> bool:
        with cls._settings_lock:
            '''
            MY_LOGGER.debug(f'setting_id: {setting_id} '
                            f'{setting_id in cls._settings_stack[-1].settings.keys()} \n'
                            f'depth: {len(cls._settings_stack)}\n keys: '
                            f'{cls._settings_stack[-1].settings.keys()}')
            '''
            return setting_id in cls._settings_stack[-1].settings.keys()

    @classmethod
    def get_setting(cls, setting_id: str, default_value: Any) -> Any:
        """
        throws KeyError
        """
        with cls._settings_lock:
            value = cls._settings_stack[-1].settings.get(setting_id)
            if value is None:
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'setting_id: {setting_id} cls._settings_stack[-1]'
                                       f' {cls._settings_stack[-1]} ')
        if value is None or (isinstance(value, str) and value == ''):
            # MY_LOGGER.debug(f'Using default value {setting_id} {default}')
            value = default_value
            if setting_id == 'converter':
                MY_LOGGER.dump_stack('Converter problem')
        # MY_LOGGER.debug(f'setting_id: {setting_id} value: {value}')

        return value

    @classmethod
    def get_previous_setting(cls, setting_id: str, default_value: Any) -> Any:
        """
        throws KeyError
        """
        with cls._settings_lock:
            if len(cls._settings_stack) < 2:
                return None
            value = cls._settings_stack[-2].settings.get(setting_id)
        if value is None or (isinstance(value, str) and value == ''):
            # MY_LOGGER.debug(f'Using default value {setting_id} {default}')
            value = default_value
            if setting_id == 'converter':
                MY_LOGGER.dump_stack('Converter problem')
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'get_previous_setting setting_id: {setting_id}'
                              f' value: {value}')
        return value

    @classmethod
    def is_empty(cls) -> bool:
        with cls._settings_lock:
            return not cls._settings_stack[-1].settings


class SettingsContext(AbstractContextManager):

    def __init__(self):
        self.ks: xbmcaddon.Settings | None = None

    def __enter__(self) -> ForwardRef('SettingsContext'):
        self.ks = xbmcaddon.Addon(Constants.ADDON_ID).getSettings()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            del self.ks
            self.ks = None
            pass
        except Exception as e:
            # MY_LOGGER.exception('')
            pass

        if exc_type is not None:
            return False
        else:
            return True


class SettingsWrapper:
    """
    Reads settings from settings.xml via the old api
    """
    old_api: xbmcaddon.Addon = CriticalSettings.ADDON

    def __init__(self):
        pass

    def getBool(self, setting_path: str) -> bool:
        """
        Returns the value of a setting as a boolean.

        :param setting_path: string - id of the setting that the module needs to access.
        :return: bool - Setting as a boolean

        @python_v20 New function added.

        Example::

            ..
            enabled = settings.getBool('enabled')
            ..
        """
        clz = type(self)
        try:
            value = clz.old_api.getSettingBool(setting_path)
        except TypeError:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Error getting {setting_path}')
            value = None
        except Exception:
            MY_LOGGER.exception('')
            value = None

        if isinstance(value, str):
            value = value.lower() == 'true'

        return value

    def getInt(self, setting_path: str) -> int:
        """
        Returns the value of a setting as an integer.

        :param setting_path: string - id of the setting that the module needs to access.
        :return: integer - Setting as an integer

        @python_v20 New function added.

        Example::

            ..
            max = settings.getInt('max')
            ..
        """
        clz = type(self)
        value: int | None = None
        try:
            value = clz.old_api.getSettingInt(setting_path)
        except TypeError as e:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Error getting {setting_path}')
            value = None
        return value

    def getNumber(self, setting_path: str) -> float:
        """
        Returns the value of a setting as a floating point number.

        :param setting_path: string - id of the setting that the module needs to access.
        :return: float - Setting as a floating point number

        @python_v20 New function added.

        Example::

            ..
            max = settings.getNumber('max')
            ..
        """
        clz = type(self)
        value: float | None = None
        try:
            value: float = clz.old_api.getSettingNumber(setting_path)
        except TypeError:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.error(f'Setting {setting_path} is not a float. '
                                f'Setting to None')
            value = None
        return value

    def getString(self, setting_path: str) -> str:
        """
        Returns the value of a setting as a string.

        :param setting_path: - id of the setting that the module needs to access.
        :return: string - Setting as a string

        @python_v20 New function added.

        Example::
            apikey = settings.getString('apikey')
        """
        clz = type(self)
        value: str | None = None
        try:
            value = clz.old_api.getSettingString(setting_path)
            #  MY_LOGGER.debug(f'value: {value} id: {short_key}')
        except TypeError as e:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Error getting {setting_path}')
            value = None
        return value

    def getBoolList(self, setting_path: str) -> List[bool]:
        """
        Returns the value of a setting as a list of booleans.

        :param setting_path: - id of the setting that the module needs to access.
        :return: list - Setting as a list of booleans

        @python_v20 New function added.

        Example::

            ...
            enabled = settings.getBoolList('enabled')
            ...
        """
        raise NotImplementedError()

    def getIntList(self, setting_path: str) -> List[int]:
        """
        Returns the value of a setting as a list of integers.

        :param setting_path: string - id of the setting that the module needs to access.
        :return: list - Setting as a list of integers

        @python_v20 New function added.

        Example::

            ..
            ids = settings.getIntList('ids')
            ..
        """
        raise NotImplementedError()

    def getNumberList(self, setting_path: str) -> List[float]:
        """
        Returns the value of a setting as a list of floating point numbers.

        :param setting_path: string - id of the setting that the module needs to access.
        :return: list - Setting as a list of floating point numbers

        @python_v20 New function added.

        Example::

            ..
            max = settings.getNumberList('max')
            ..
        """
        raise NotImplementedError()

    def getStringList(self, setting_path: str) -> List[str]:
        """
        Returns the value of a setting as a list of unicode strings.

        :param setting_path: string - id of the setting that the module needs to access.
        :return: list - Setting as a list of unicode strings

        @python_v20 New function added.

        Example::

            ..
            views = settings.getStringList('views')
            ..
        """
        raise NotImplementedError()

    def setBool(self, setting_path: str, value: bool) -> None:
        """
        Sets the value of a setting.

        :param setting_path: string - id of the setting that the module needs to access.
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
        #  MY_LOGGER.debug(f'Saving {short_key} value {type(value)} {value}')
        value = clz.old_api.setSettingBool(setting_path, value)

    def setInt(self, setting_path: str, value: int) -> None:
        """
        Sets the value of a setting.

        :param setting_path: string - id of the setting that the module needs to access.
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
        clz.old_api.setSettingInt(setting_path, value)

    def setNumber(self, setting_path: str, value: float) -> None:
        """
        Sets the value of a setting.

        :param setting_path: string - id of the setting that the module needs to access.
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
        clz.old_api.setSettingNumber(setting_path, value)

    def setString(self, setting_path: str, value: str) -> None:
        """
        Sets the value of a setting.

        :param setting_path: string - id of the setting that the module needs to access.
        :param value: string - value of the setting.
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
        if not isinstance(value, str):
            raise ValueError(f'Value is not a str {value} {type(value)}')
        clz.old_api.setSettingString(setting_path, value)

    def setBoolList(self, setting_path: str, values: List[bool]) -> None:
        """
        Sets the boolean values of a list setting.

        :param setting_path: string - id of the setting that the module needs to access.
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

    def setIntList(self, setting_path: str, values: List[int]) -> None:
        """
        Sets the integer values of a list setting.

        :param setting_path: string - id of the setting that the module needs to access.
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

    def setNumberList(self, setting_path: str, values: List[float]) -> None:
        """
        Sets the floating point values of a list setting.

        :param setting_path: string - id of the setting that the module needs to access.
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

    def setStringList(self, setting_path: str, values: List[str]) -> None:
        """
        Sets the string values of a list setting.

        :param setting_path: string - id of the setting that the module needs to access.
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
    # _current_engine: str = None
    # _alternate_engine: str = None
    settings_wrapper = SettingsWrapper()
    addon = xbmcaddon.Addon(Constants.ADDON_ID)
    all_settings: xbmcaddon.Settings = addon.getSettings()
    # settings_wrapper = all_settings

    _initialized: bool = False
    _loading: threading.Event = threading.Event()
    _loading.set()  # Enable

    @classmethod
    def init(cls):
        if not cls._initialized:
            cls._initialized = True
            # SettingsLowLevel._current_engine = None

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
        pass

    @classmethod
    def save_settings(cls) -> int:
        """

        :return:
        """
        try:
            return SettingsManager.push_settings()
            #  MY_LOGGER.debug('Backed up settings')
        except Exception:
            MY_LOGGER.exception("")

    @classmethod
    def restore_settings(cls, stack_depth: int = None) -> None:
        # get lock
        # set SETTINGS_BEING_CONFIGURED, SETTINGS_LAST_CHANGED
        #
        SettingsManager.restore_settings(stack_depth)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('TRACE Cancel changes')

    @staticmethod
    def get_changed_settings(settings_to_check: List[str]) -> List[str]:
        """

        :param settings_to_check:
        :return:
        """
        changed_settings = []
        for setting_id in settings_to_check:
            previous_value = SettingsManager.get_previous_setting(setting_id, None)
            try:
                current_value = SettingsLowLevel.get_addon().setting(setting_id)
            except Exception:
                current_value = previous_value

            if previous_value != current_value:
                changed = True
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'setting changed: {setting_id} '
                                    f'previous_value: {previous_value} '
                                    f'current_value: {current_value}')
            else:
                changed = False

            if changed:
                changed_settings.append(setting_id)

        return changed_settings

    @classmethod
    def type_and_validate_settings(cls, full_setting_id: str | ServiceID,
                                   value: Any | None) -> Tuple[bool, Type]:
        """
        Performs minimal validation of settings: Verifies that the property is
        expected and that the value conforms to the expected type. This is NOT the
        same as validating the values using Validators.
        """
        setting_id: str | None = None
        # engine_id: str | None = None
        type_error: bool = False
        expected_type: str = ''
        service_key: ServiceID | None = None
        if isinstance(full_setting_id, str):
            # Will have ServiceType.UNKNOWN
            service_key = ServiceID.from_full_setting_id(full_setting_id)
        else:
            service_key = full_setting_id
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'service_key: {service_key} value: {value}')
        if not SettingsMap.is_valid_setting(service_key):
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(
                    f'TRACE Setting NOT supported for {service_key}')

        PROTO_LIST_BOOLS: List[bool] = [True, False]
        PROTO_LIST_FLOATS: List[float] = [0.7, 8.2]
        PROTO_LIST_INTEGERS: List[int] = [1, 57]
        PROTO_LIST_STRINGS: List[str] = ['a', 'b']
        try:
            try:
                try:
                    setting_type = SettingsMap.get_setting_type(service_key)
                except ValueError:
                    setting_type = SettingProp.SettingTypes[service_key.setting_id]
                if setting_type == SettingType.BOOLEAN_TYPE:
                    expected_type = 'bool'
                    if not isinstance(value, bool):
                        type_error = True
                elif setting_type == SettingType.BOOLEAN_LIST_TYPE:
                    expected_type = 'List[bool]'
                    if not isinstance(value, type(PROTO_LIST_BOOLS)):
                        type_error = True
                elif setting_type == SettingType.FLOAT_TYPE:
                    expected_type = 'float'
                    if not isinstance(value, float):
                        type_error = True
                elif setting_type == SettingType.FLOAT_LIST_TYPE:
                    expected_type = 'List[float]'
                    if not isinstance(value, type(PROTO_LIST_FLOATS)):
                        type_error = True
                elif setting_type == SettingType.INTEGER_TYPE:
                    expected_type = 'int'
                    if not isinstance(value, int):
                        type_error = True
                elif setting_type == SettingType.INTEGER_LIST_TYPE:
                    expected_type = 'List[int]'
                    if not isinstance(value, type(PROTO_LIST_INTEGERS)):
                        type_error = True
                elif setting_type == SettingType.STRING_TYPE:
                    expected_type = 'str'
                    if not isinstance(value, str):
                        type_error = True
                elif setting_type == SettingType.STRING_LIST_TYPE:
                    expected_type = 'List[str]'
                    if not isinstance(value, type(PROTO_LIST_STRINGS)):
                        type_error = True
            finally:
                pass
        except TypeError:
            MY_LOGGER.exception(
                    f'TRACE: failed to find type of setting: {full_setting_id}. '
                    f'Probably not defined in resources/settings.xml')
        except Exception:
            MY_LOGGER.exception(
                    f'TRACE: Bad full_setting_id: {full_setting_id}')
        if type_error:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'TRACE: incorrect type for setting: {full_setting_id} '
                                f'Expected {expected_type} got {str(type(value))}')
        return type_error, type(value)

    all_engines_loaded: bool = False

    @classmethod
    def load_settings(cls, service_key: ServiceID) -> None:
        """
        Load ALL settings for the given ServiceType (engine, tts, etc).
        Settings not supported by a Service are not read and not put into
        the cache. The settings.xml can have orphaned settings as long as
        kodi allows it, based on the rules in the addon's settings.xml definition
        file.

        Ignore any other changes to settings until finished
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'TRACE load_settings service_key: {service_key}')
        blocked: bool = False
        while not SettingsLowLevel._loading.is_set():
            # If some other thread is loading, wait until finished, then exit.
            # The assumption is that a reload after a reload is not needed.
            # Besides, the code will still load from settings.xml when needed.

            blocked = True
            Monitor.exception_on_abort(timeout=0.01)

        services_to_add: List[str] = []
        new_settings: Dict[ServiceID, str] = {}
        if service_key.service_type == ServiceType.ENGINE and not cls.all_engines_loaded:
            engine_id: str
            cls.all_engines_loaded = True
            full_setting_id, engine_id = cls.load_setting(ServiceKey.CURRENT_ENGINE_KEY)
            #  if engine_id == Backends.AUTO_ID:
            #      engine_id = Backends.DEFAULT_ENGINE_ID
            new_settings[full_setting_id] = engine_id
            #  services_to_add.append(engine_id)  # Do the requested one first
            services_to_add.extend(Backends.ALL_ENGINE_IDS)
            #  try:
            #     services_to_add.remove(Services.AUTO_ENGINE_ID)
            # except ValueError:
            #     MY_LOGGER.exception('')
        # elif service_key.service_type == ServiceType.PLAYER:
        #     pass
            #  MY_LOGGER.debug(f'Loading PLAYER services')
            #  services_to_add.extend(Players.ALL_PLAYER_IDS)
        elif service_key.service_type == ServiceType.TTS:
            #  MY_LOGGER.debug(f'Loading TTS services')
            #  services_to_add.append(SettingProp.TTS_SERVICE)
            services_to_add.extend(SettingProp.TTS_SETTINGS)
        try:
            SettingsLowLevel._loading.clear()
            if blocked:
                return
            setting_id: str
            for setting_id in services_to_add:
                cls._load_settings(new_settings, service_key, setting_id)

            # validate new_settings
            SettingsManager.set_settings(new_settings)
            # release lock
            # Notify
        finally:
            SettingsLowLevel._loading.set()

    # Ignore Settings in this dict
    ignore: Dict[str, str] = {
        'addons_MD5.eSpeak': '',
        'addons_MD5.google': '',
        # 'addons_MD5.tts': '',
        'addons_MD5.powershell': '',
        # 'api_key.Cepstral': '',
        'api_key.google': '',
        'api_key.eSpeak': '',
        'api_key.powershell': '',
        # 'api_key.ResponsiveVoice': '',setting_id
        'api_key.tts': '',
        'auto_item_extra_delay.eSpeak': '',
        #  'auto_item_extra_delay.tts': '',
        'auto_item_extra_delay.google': '',
        'auto_item_extra_delay.powershell': '',
        'auto_item_extra.eSpeak': '',
        'auto_item_extra.google': '',
        'auto_item_extra.powershell': '',
        #  'auto_item_extra.tts': '',
        'background_progress_interval.eSpeak': '',
        'background_progress_interval.google': '',
        'background_progress_interval.powershell': '',
        #  'background_progress_interval.tts': '',
        'cache_expiration_days.eSpeak': '',
        #  'cache_expiration_days.tts': '',
        # 'cache_path.eSpeak': '',
        # 'cache_path.google': '',
        # 'cache_path.powershell': '',
        #  'cache_path.tts': '',
        # 'cache_speech.eSpeak': '',
        # 'cache_speech.experimental': '',
        # 'cache_speech.google': '',
        # 'cache_speech.piper': '',
        # 'cache_speech.ResponsiveVoice': '',
        # 'cache_speech.sapi': '',
        'cache_speech.tts': '',
        'capital_recognition.eSpeak': '',
        'capital_recognition.google': '',
        'capital_recognition.powershell': '',
        # 'capital_recognition.Speech-Dispatcher': '',
        'capital_recognition.tts': '',
        'channels.eSpeak': '',
        'channels.google': '',
        'channels.powershell': '',
        'channels.tts': '',
        #  'converter.eSpeak': '',
        #  'converter.powershell': '',
        # 'converter.experimental': '',
        # 'converter.google': '',
        # 'converter.piper': '',
        # 'converter.ResponsiveVoice': '',
        # 'converter.sapi': '',
        'converter.tts': '',
        'core_version': '',
        'debug_log_level.eSpeak': '',
        'debug_log_level.google': '',
        'debug_log_level.powershell': '',
        # 'debug_log_level.tts': '',
        'delay_voicing.eSpeak': '',
        # 'delay_voicing.experimental': '',
        'delay_voicing.google': '',
        'delay_voicing.powershell': '',
        # 'delay_voicing.piper': '',
        # 'delay_voicing.sapi': '',
        'delay_voicing.tts': '',
        'disable_broken_services.eSpeak': '',
        'disable_broken_services.google': '',
        'disable_broken_services.powershell': '',
        # 'disable_broken_services.tts': '',
        ' fr .tts': '',
        'engine.google': '',
        'engine.no_engine': '',
        'engine.powershell': '',
        'engine.eSpeak': '',
        'tts.tts': '',
        # 'gender.Cepstral': '',
        # 'gender.eSpeak': '',
        # 'gender.experimental': '',
        # 'gender.Flite': '',
        # 'gender.google': '',
        # 'gender.no_engine': '',
        # 'gender.powershell': '',
        # 'gender.OSXSay': '',
        # 'gender.pico2wave': '',
        # 'gender.piper': '',
        # 'gender.ResponsiveVoice': '',
        # 'gender.sapi': '',
        # 'gender.Speech-Dispatcher': '',
        'gender.tts': '',
        # 'gender_visible.eSpeak': '',
        # 'gender_visible.google': '',
        # 'gender_visible.powershell': '',
        'gender_visible.tts': '',
        'gui.eSpeak': '',
        'gui.google': '',
        'gui.powershell': '',
        'gui.tts': '',
        #  'id.eSpeak': '',
        'id.eSpeak': '',
        'id.google': '',
        'id.powershell': '',
        'id.tts': '',
        'language': '',
        # 'language.Cepstral': '',
        # 'language.eSpeak': '',
        # 'language.experimental': '',
        # 'language.Festival': '',
        # 'language.Flite': '',
        # 'language.google': '',
        # 'language.powershell': '',
        # 'language.OSXSay': '',
        # 'language.pico2wave': '',
        # 'language.piper': '',
        # 'language.ResponsiveVoice': '',
        # 'language.sapi': '',
        # 'language.Speech-Dispatcher': '',
        'language.tts': '',
        # 'lastnotified_stable': '',
        # 'lastnotified_version': '',
        'module.eSpeak': '',
        'module.google': '',
        'module.powershell': '',
        'module.Speech-Dispatcher': '',
        'module.tts': '',
        'output_via.eSpeak': '',
        'output_via.google': '',
        'output_via.powershell': '',
        'output_via.tts': '',
        'output_visible.eSpeak': '',
        'output_visible.google': '',
        'output_visible.powershell': '',
        'output_visible.tts': '',
        'override_poll_interval.eSpeak': '',
        'override_poll_interval.google': '',
        'override_poll_interval.powershell': '',
        # 'override_poll_interval.tts': '',
        # 'pipe.Cepstral': '',
        'pipe.eSpeak': '',
        'pipe.powershell': '',
        'pipe.google': '',
        # 'pipe.experimental': '',
        # 'pipe.Festival': '',
        # 'pipe.Flite': '',
        # 'pipe.OSXSay': '',
        # 'pipe.pico2wave': '',
        # 'pipe.piper': '',
        # 'pipe.ResponsiveVoice': '',
        # 'pipe.sapi': '',
        # 'pipe.Speech-Dispatcher': '',
        'pipe.tts': '',
        # 'pitch.Cepstral': '',
        # 'pitch.eSpeak': '',  # Supports pitch
        # 'pitch.experimental': '',
        # 'pitch.Festival': '',
        # 'pitch.Flite': '',
        # 'pitch.OSXSay': '',
        # 'pitch.pico2wave': '',
        # 'pitch.piper': '',
        # 'pitch.ResponsiveVoice': '',
        # 'pitch.sapi': '',
        # 'pitch.Speech-Dispatcher': '',
        'pitch.tts': '',
        'pitch.google': '',
        'pitch.powershell': '',
        # 'player_key.Cepstral': '',
        # 'player_key.eSpeak': '',
        # 'player_key.experimental': '',
        # 'player_key.Festival': '',
        # 'player_key.Flite': '',
        # 'player_key.google': '',
        # 'player_mode.google': '',
        # 'player_mode.powershell': '',
        # 'player_mode.eSpeak',
        'player_mode.tts': '',
        # 'player_key.OSXSay': '',
        # 'player_key.pico2wave': '',
        # 'player_key.piper': '',
        'player_pitch.eSpeak': '',
        'player_pitch.google': '',
        'player_pitch.powershell': '',
        # 'player_pitch.experimental': '',
        # 'player_pitch.ResponsiveVoice': '',
        'player_pitch.tts': '',
        # 'player_key.ResponsiveVoice': '',
        # 'player_key.sapi': '',
        # 'player_key.Speech-Dispatcher': '',
        'player_speed.eSpeak': '',
        'player_speed.google': '',
        'player_speed.powershell': '',
        # 'player_speed.ResponsiveVoice': '',
        'player_speed.tts': '',
        'player_key.tts': '',
        'player_volume.eSpeak': '',
        'player_volume.google': '',
        'player_volume.powershell': '',
        'player_volume.tts': '',
        'poll_interval.eSpeak': '',
        'poll_interval.google': '',
        'poll_interval.tts': '',
        'poll_internal.powershell': '',
        'punctuation.eSpeak': '',
        'punctuation.google': '',
        'punctuation.powershell': '',
        # 'punctuation.Speech-Dispatcher': '',
        'punctuation.tts': '',
        'reader_on.eSpeak': '',
        'reader_on.google': '',
        'reader_on.powershell': '',
        #  'reader_on.tts': '',
        'remote_pitch.eSpeak': '',
        'remote_pitch.experimental': '',
        'remote_pitch.google': '',
        'remote_pitch.powershell': '',
        'remote_pitch.ResponsiveVoice': '',
        'remote_pitch.tts': '',
        'remote_server.Speech-Dispatcher': '',
        'remote_speed.eSpeak': '',
        'remote_speed.google': '',
        'remote_speed.powershell': '',
        'remote_speed.tts': '',
        'remote_volume.eSpeak': '',
        'remote_volume.google': '',
        'remote_volume.powershell': '',
        'remote_volume.tts': '',
        'settings_digest.eSpeak': '',
        'settings_digest.google': '',
        'settings_digest.powershell': '',
        #  'settings_digest.tts': '',
        'settings_last_changed.eSpeak': '',
        'settings_last_changed.google': '',
        'settings_last_changed.powershell': '',
        'settings_last_changed.tts': '',
        'speak_background_progress_during_media.eSpeak': '',
        #  'speak_background_progress_during_media.tts': '',
        'speak_background_progress.eSpeak': '',
        'speak_background_progress.powershell': '',
        #  'speak_background_progress.tts': '',
        'speak_list_count.eSpeak': '',
        'speak_list_count.powershell': '',
        #  'speak_list_count.tts': '',
        'speak_on_server.eSpeak': '',
        'speak_on_server.experimental': '',
        'speak_on_server.google': '',
        'speak_on_server.powershell': '',
        'speak_on_server.ResponsiveVoice': '',
        'speak_on_server.tts': '',
        'speak_via_kodi': '',
        'speak_via_kodi.eSpeak': '',
        'speak_via_kodi.google': '',
        'speak_via_kodi.powershell': '',
        'speak_via_kodi.tts': '',
        'Speech-Dispatcher.eSpeak': '',
        'Speech-Dispatcher.google': '',
        'Speech-Dispatcher.powershell': '',
        # 'Speech-Dispatcher-module': '',
        'Speech-Dispatcher.tts': '',
        'speed_enabled.eSpeak': '',
        # 'speed_enabled.experimental': '',
        'speed_enabled.google': '',
        'speed_enabled.powershell': '',
        # 'speed_enabled.piper': '',
        # 'speed_enabled.ResponsiveVoice': '',
        # 'speed_enabled.sapi': '',
        'speed_enabled.tts': '',
        'speed.eSpeak': '',
        'speed.google': '',
        'speed.powershell': '',
        'speed_visible.eSpeak': '',
        'speed_visible.google': '',
        'speed_visible.powershell': '',
        'speed_visible.tts': '',
        'spelling.eSpeak': '',
        'spelling.google': '',
        'spelling.powershell': '',
        # 'spelling.Speech-Dispatcher': '',
        'spelling.tts': '',
        'ttsd_host.eSpeak': '',
        'ttsd_host.google': '',
        'ttsd_host.tts': '',
        'ttsd_port.eSpeak': '',
        'ttsd_port.google': '',
        'ttsd_port.powershell': '',
        'ttsd_port.tts': '',
        'use_aoss.eSpeak': '',
        'use_aoss.google': '',
        'use_aoss.powershell': '',
        # 'use_aoss.experimental': '',
        # 'use_aoss.ResponsiveVoice': '',
        'use_aoss.tts': '',
        # 'use_temp_settings.tts': '',
        'use_tmpfs.eSpeak': '',
        'use_tmpfs.tts': '',
        'version.eSpeak': '',
        #  'version.tts': '',
        'voice.Cepstral': '',
        # 'voice.eSpeak': '',
        'voice.experimental': '',
        'voice.Festival': '',
        'voice.Flite': '',
        # 'voice.google': '',
        'voice.OSXSay': '',
        'voice_path.eSpeak': '',
        'voice_path.piper': '',
        'voice_path.tts': '',
        'voice_path.google': '',
        'voice_path.powershell': '',
        'voice.pico2wave': '',
        'voice.piper': '',
        'voice.ResponsiveVoice': '',
        'voice.sapi': '',
        'voice.Speech-Dispatcher': '',
        'voice.tts': '',
        'voice_visible.eSpeak': '',
        'voice_visible.google': '',
        'voice_visible.powershell': '',
        'voice_visible.tts': '',
        'volume.eSpeak': '',
        # 'volume.tts': '',
        # 'volume_visible.tts'
    }

    @classmethod
    def _load_settings(cls, new_settings: Dict[ServiceID, Any],
                       service_key: ServiceID,
                       setting_id: str) -> None:
        """
        Load ALL settings for the given service_id.
        Settings from multiple backends can be in the cache simultaneously
        Settings not supported by a backend are not read and not put into
        the cache. The settings.xml can have orphaned settings as long as
        kodi allows it, based on the rules in the addon's settings.xml definition
        file.

        Ignore any other changes to settings until finished

        :param new_settings: Any settings found are returned with their values
                            via this dict
        :param service_key: Identifies the service to load
        :param setting_id: load this setting, if found.
                           ex. service_type = Engine, service_id = google
                           will return a value. But service_type = PLAYER and
                           service_id == google, will not
        """

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'TRACE load_settings service: {service_key} '
                            f'service_id: {service_key.service_id} '
                            f'setting_id: {setting_id}')
        # Get Lock
        force_load: bool = False
        settings: Dict[str, None]
        settings = SettingProp.SETTINGS_BY_SERVICE_TYPE[service_key.service_type]
        #  MY_LOGGER.debug(f'service_key: {service_key} properties: {settings.keys()}')
        for setting_id in settings.keys():
            value: Any | None
            full_path: str = f'{setting_id}.{service_key.service_id}'
            if full_path in cls.ignore:
                MY_LOGGER.debug(f'full_path: {full_path} ignored')
                continue
            else:
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'key: {full_path} not in cls.ignore')

            # if setting_id in SettingProp.TOP_LEVEL_SETTINGS:
            #     continue
            # if setting_id in SettingProp.TTS_SETTINGS:
            #     setting_id = Services.TTS_SERVICE
            service_key: ServiceID
            service_key = ServiceID(service_type=service_key.service_type,
                                    service_id=service_key.service_id,
                                    setting_id=setting_id)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'property\'s service_key: {service_key} path: '
                                  f'{service_key.short_key}')
            if SettingsMap.is_valid_setting(service_key):
                value = cls.load_setting(service_key)
            elif force_load:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'FORCED load of property: {setting_id}')
                value = cls.load_setting(service_key)
            else:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Not loading: {service_key} '
                                    f'NOT defined via SettingsMap.define_setting')
                continue
            if value is not None:
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'Adding {service_key} value: {value} '
                                       f'to settings cache')
                new_settings[service_key] = value
            else:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'FAILED to add {service_key} value: {value}')

    @classmethod
    def load_setting(cls, service_key: ServiceID) -> Any | None:
        """
        loads setting into the current settings cache frame from settings.xml

        :param service_key: Identifies the setting to load
        :return: Any value found for the setting
        """
        found: bool = True
        force_load: bool = False
        if service_key == ServiceKey.CURRENT_ENGINE_KEY:
            found = True
        if not force_load and not SettingsMap.is_valid_setting(service_key):
            found = False
            MY_LOGGER.debug(f'valid_setting: {service_key} {service_key.short_key} '
                            f'{SettingsMap.is_valid_setting(service_key)}')
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'Setting {service_key.setting_id} supported: {found} for '
                              f'{service_key.service_id}')
        setting_path: str = service_key.short_key
        MY_LOGGER.debug(f'is_in_cache: {cls.is_in_cache(service_key)}')
        if setting_path in cls.ignore:
            MY_LOGGER.debug(f'IGNORE {setting_path}')
            return None
        # MY_LOGGER.debug(f'key: {key}')
        # A few values are constant (such as some engines can't play audio,
        # or adjust volume)
        const_value: Any = SettingsMap.get_const_value(service_key)
        value: Any | None = None
        try:
            '''
            match SettingProp.SettingTypes[setting_id]:
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
            '''
            setting_type = SettingProp.SettingTypes[service_key.setting_id]
            if setting_type == SettingType.BOOLEAN_TYPE:
                value = cls.settings_wrapper.getBool(setting_path)
            elif setting_type == SettingType.BOOLEAN_LIST_TYPE:
                value = cls.settings_wrapper.getBoolList(setting_path)
            elif setting_type == SettingType.FLOAT_TYPE:
                value = cls.settings_wrapper.getNumber(setting_path)
            elif setting_type == SettingType.FLOAT_LIST_TYPE:
                value = cls.settings_wrapper.getNumberList(setting_path)
            elif setting_type == SettingType.INTEGER_TYPE:
                value = cls.settings_wrapper.getInt(setting_path)
            elif setting_type == SettingType.INTEGER_LIST_TYPE:
                value = cls.settings_wrapper.getIntList(setting_path)
            elif setting_type == SettingType.STRING_TYPE:
                value = cls.settings_wrapper.getString(setting_path)
            elif setting_type == SettingType.STRING_LIST_TYPE:
                value = cls.settings_wrapper.getStringList(setting_path)
            if const_value is not None:
                value = const_value
            # MY_LOGGER.debug(f'found key: {key} value: {value}')
        except KeyError:
            MY_LOGGER.exception(
                    f'failed to find service_key: {service_key}. '
                    f'Probably not defined in resources/settings.xml')
        except TypeError:
            MY_LOGGER.exception(f'failed to get type of service: {service_key}')
            if force_load:
                try:
                    value_str: str
                    value_str = xbmcaddon.Addon(Constants.ADDON_ID).getSetting(setting_path)
                    if value_str is None:
                        value = None
                    else:
                        """
                        match SettingProp.SettingTypes[setting_id]:
                            case SettingType.BOOLEAN_TYPE:
                                value = bool(value_str)
                            case SettingType.FLOAT_TYPE:
                                value = float(value_str)
                            case SettingType.INTEGER_TYPE:
                                value = int(value_str)
                            case SettingType.STRING_TYPE:
                                value = value_str
                        """
                        setting_type = SettingProp.SettingTypes[service_key.setting_id]
                        if setting_type == SettingType.BOOLEAN_TYPE:
                            value = bool(value_str)
                        elif setting_type == SettingType.FLOAT_TYPE:
                            value = float(value_str)
                        elif setting_type == SettingType.INTEGER_TYPE:
                            value = int(value_str)
                        elif setting_type == SettingType.STRING_TYPE:
                            value = value_str
                except Exception as e:
                    MY_LOGGER.exception(
                        f'Second attempt to read setting'
                        f' {service_key.short_key} failed')
        #  if value is not None:
        #     MY_LOGGER.debug(f'Loaded {service_key.short_key}')
        if value is None:
            try:
                value = SettingsMap.get_default_value(service_key)
            except Exception as e:
                MY_LOGGER.exception(f'Can not set default for '
                                    f'{setting_path}')
        # if value and MY_LOGGER.isEnabledFor(DEBUG):
            #  MY_LOGGER.debug(f'Read {key} value: {value}')
        #  MY_LOGGER.debug(f'Read {key} value: {value}')
        return value

    @classmethod
    def configuring_settings(cls):
        #  MY_LOGGER.debug('configuring_settings hardcoded to false')
        return False

    @classmethod
    def getExpandedSettingId(cls, setting_id: str, service_id: str) -> str:
        tmp_id: List[str] = setting_id.split(sep=".", maxsplit=2)
        real_key: str

        if len(tmp_id) > 1:
            #     MY_LOGGER.debug(f'already expanded: {setting_id}')
            real_key = setting_id
        else:
            suffix: str = ''
            if service_id is None:
                if setting_id not in SettingProp.TOP_LEVEL_SETTINGS:
                    #  setting_id = SettingsLowLevel._current_engine
                    engine_id: ServiceID = SettingsLowLevel.get_engine_id_ll()
                    service_id = engine_id.service_id

            if service_id:
                suffix = "." + service_id

            real_key: str = setting_id + suffix
        # MY_LOGGER.debug(
        #         f'in: {setting_id} out: {real_key} len(tmp_id): {len(tmp_id)}')
        return real_key

    @classmethod
    def splitSettingId(cls, expanded_setting: str) -> Tuple[str | None, str | None]:
        tmp_id: List[str] = expanded_setting.split(sep=".", maxsplit=2)
        if len(tmp_id) == 1:
            return tmp_id[0], None
        if len(tmp_id) == 2:
            return tmp_id[1], tmp_id[0]
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Malformed setting id: {expanded_setting}')
        return None, None

    @classmethod
    def getSettingIdPrefix(cls, setting_id: str) -> str:
        #
        tmp_id: List[str] = setting_id.split(sep=".", maxsplit=1)
        prefix: str
        prefix = tmp_id[0]
        return prefix

    @classmethod
    def getRealSetting(cls, setting_id: str, engine_id: str | None,
                       default_value: Any | None) -> Any | None:
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'TRACE getRealSetting NOT from cache id: {setting_id}'
                            f' backend: {engine_id}')
        if engine_id is None or len(engine_id) == 0:
            # engine_id = SettingsLowLevel._current_engine
            engine_src_id: ServiceID = SettingsLowLevel.get_engine_id_ll(
                ignore_cache=True)
            if engine_src_id is None:
                MY_LOGGER.error("TRACE Failed to get current engine_id")
            engine_id = engine_src_id.service_id
        real_key = cls.getExpandedSettingId(setting_id, engine_id)
        try:
            """
            match SettingProp.SettingTypes[setting_id]:
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
            """
            setting_type = SettingProp.SettingTypes[setting_id]
            if setting_type == SettingType.BOOLEAN_TYPE:
                return cls.settings_wrapper.getBool(real_key)
            elif setting_type == SettingType.BOOLEAN_LIST_TYPE:
                return cls.settings_wrapper.getBoolList(real_key)
            elif setting_type == SettingType.FLOAT_TYPE:
                return cls.settings_wrapper.getNumber(real_key)
            elif setting_type == SettingType.FLOAT_LIST_TYPE:
                return cls.settings_wrapper.getNumberList(real_key)
            elif setting_type == SettingType.INTEGER_TYPE:
                return cls.settings_wrapper.getInt(real_key)
            elif setting_type == SettingType.INTEGER_LIST_TYPE:
                return cls.settings_wrapper.getIntList(real_key)
            elif setting_type == SettingType.STRING_TYPE:
                return cls.settings_wrapper.getString(real_key)
            elif setting_type == SettingType.STRING_LIST_TYPE:
                return cls.settings_wrapper.getStringList(real_key)
        except Exception as e:
            MY_LOGGER.exception('')

    @classmethod
    def commit_settings(cls) -> None:
        """
        In one operation, protected by RLocks:
            1) commit the top-frame of settngs to settings.xml
            2) Purge all other frames from SettingsStack, leaving only one frame
        :return:

        Note that final_stack_depth and save_from_top are used during settings
        configuration. These options allow temporary settings values to be tried
        by the user and then committed once the user is satisfied.
        """
        #  MY_LOGGER.debug('TRACE commit_settings')
        addon: xbmcaddon = xbmcaddon.Addon(Constants.ADDON_ID)

        with SettingsManager._settings_lock:
            # Copy the settings from stack_frame at final_stack_depth to
            # a map.
            # Apply settings_changes to the copied settings from previous step
            # Remove all stack frames.
            # Create final_stack_depth copies of the merged changes and add to
            # stack.
            top_frame: Dict[str, str | int | bool | float | None]
            top_frame = SettingsManager.get_settings()
            failed: bool = False
            # Persist the new-frame to settings.xml
            for full_setting_id, value in top_frame.items():
                full_setting_id: str
                value: Any
                value_type: SettingType | None = None
                str_value: str = ''
                try:
                    str_value = str(value)
                    if full_setting_id == SettingProp.ENGINE:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'TRACE Commiting ENGINE value: {str_value}')

                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'id: {full_setting_id} '
                                        f'value: {str_value} type: {type(value)}')
                    prefix: str = cls.getSettingIdPrefix(full_setting_id)
                    value_type = SettingProp.SettingTypes.get(prefix, None)
                    if value == 'NO_VALUE':
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Expected setting not found {prefix}')
                        continue
                    """
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
                    """
                    if value_type == SettingType.BOOLEAN_TYPE:
                        cls.settings_wrapper.setBool(full_setting_id, value)
                    if value_type == SettingType.BOOLEAN_LIST_TYPE:
                        cls.settings_wrapper.setBoolList(full_setting_id, value)
                    if value_type == SettingType.FLOAT_TYPE:
                        cls.settings_wrapper.setNumber(full_setting_id, value)
                    if value_type == SettingType.FLOAT_LIST_TYPE:
                        cls.settings_wrapper.setNumberList(full_setting_id, value)
                    if value_type == SettingType.INTEGER_TYPE:
                        cls.settings_wrapper.setInt(full_setting_id, value)
                    if value_type == SettingType.INTEGER_LIST_TYPE:
                        cls.settings_wrapper.setIntList(full_setting_id, value)
                    if value_type == SettingType.STRING_TYPE:
                        # MY_LOGGER.debug(f'full_setting_id: {full_setting_id} '
                        #                 f'type: {type(full_setting_id)} '
                        #                 f'value: {value} '
                        #                 f'value type: {type(value)}')
                        cls.settings_wrapper.setString(full_setting_id, value)
                    if value_type == SettingType.STRING_LIST_TYPE:
                        cls.settings_wrapper.setStringList(full_setting_id, value)
                except Exception as e:
                    failed = True
                    MY_LOGGER.exception(f'Error saving setting: {full_setting_id} '
                                        f'value: {value} type: {type(value)} as '
                                        f'{value_type.name}')
            if not failed:
                # top frame is cloned and saved
                # Clear the settings stack
                # Reload the settings stack with copies of top frame until
                # the stack depth is the same  as before the commit.
                # After we return, the stack will likely be popped when SettingsDialog
                # exits and pops the frame that it created on entering

                final_stack_depth: int = SettingsManager.get_stack_depth()
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'stack_depth: {final_stack_depth}')
                SettingsManager.clear_settings()
                for idx in range(1, final_stack_depth):
                    SettingsManager.load_settings(top_frame)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'final stack_depth: {SettingsManager.get_stack_depth()}')

    @classmethod
    def get_engine_id_ll(cls, default: str = None,
                         ignore_cache: bool = False) -> ServiceID:
        """
        Gets the engine_id from either the settings cache, or directly from
        settings.xml

        :param default: If the setting_id value is not found, then use the
                        value specified by default
        :param ignore_cache: Used during the bootstrap process to get the
                          engine setting directly, bypassing any cached
                          value. After startup, the cached value is almost
                          always the right value to use.
        :return: The found engine_id
        """
        # MY_LOGGER.debug(f'default: {default} boostrap {ignore_cache} current: '
        #                                f'{SettingsLowLevel._current_engine}')
        engine_id: str | None
        engine_id = cls.get_setting_str(service_key=ServiceKey.CURRENT_ENGINE_KEY,
                                        ignore_cache=ignore_cache,
                                        default=default)
        #  MY_LOGGER.debug_xv(f'TRACE engine: {engine_id} ignore_cache: {ignore_cache}')
        return ServiceID(ServiceType.ENGINE, service_id=engine_id)

    @classmethod
    def set_engine(cls, engine_key: ServiceID) -> None:
        # MY_LOGGER.debug(f'TRACE set_engine: {engine_key.service_id}'
        #                 f' type: {type(engine_key.service_id)}')
        service_key = ServiceKey.CURRENT_ENGINE_KEY
        success: bool = cls.set_setting_str(service_key, engine_key.service_id)

    @classmethod
    def setSetting(cls, setting_id: str, value: Any,
                   engine_id: str) -> bool:

        real_key = cls.getExpandedSettingId(setting_id, engine_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        try:
            success: bool = SettingsManager.set_setting(real_key, value)
            return success
        except:
            MY_LOGGER.exception('')
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'TRACE: type mismatch')

    @classmethod
    def check_reload(cls):
        if SettingsManager.is_empty():
            cls.load_settings(ServiceKey.CURRENT_ENGINE_KEY)
            cls.load_settings(ServiceKey.TTS_KEY)
            cls.load_settings(ServiceKey.PLAYER_KEY)

    @classmethod
    def get_service_setting(cls, service_key: ServiceID, default: Any = None) -> Any:
        cls.check_reload()
        value: Any = SettingsManager.get_setting(service_key.short_key,
                                                 default_value=default)
        return value

    @classmethod
    def set_service_setting(cls, service_key: ServiceID, value: Any) -> None:
        cls.check_reload()
        SettingsManager.set_setting(service_key.short_key, value)

    @classmethod
    def getSetting(cls, service_key: ServiceID,
                   default_value: Any | None = None) -> Any:
        if service_key.setting_id == SettingProp.ENGINE:
            return cls.get_engine_id_ll()  # Returns ServiceID

        value: Any = cls._getSetting(service_key, default_value)
        return value

    @classmethod
    def _getSetting(cls, service_key: ServiceID,
                    default_value: Any | None = None,
                    load_on_demand: bool = False) -> Any:
        """
        Gets the VALUE of the setting identified by service_key
        :param service_key:
        :param default_value:
        :param load_on_demand: If True, then if the setting is not found in the cache
                  it attempts to load it from settings.xml. Any loaded value is placed
                  into the cache.
        :return:

        :raises KeyError:
        """
        value: Any = None

        MY_LOGGER.debug(f'{service_key} is_in_cache: {cls.is_in_cache(service_key)}')
        cls.check_reload()
        MY_LOGGER.debug(f'{service_key} is_in_cache: {cls.is_in_cache(service_key)}')
        if load_on_demand and not cls.is_in_cache(service_key):
            # value is NOT stored in settings cache. Need to manually push it to
            # all stack frames of cache (yuk).
            value = cls.load_setting(service_key)
            MY_LOGGER.debug(f'loading {service_key.short_key} value: {value}')
            SettingsManager.load_setting_to_all_frames(service_key.short_key, value)
            value = SettingsManager.get_setting(service_key.short_key,
                                                default_value)
            MY_LOGGER.debug(f'Getting from cache: {service_key.short_key} '
                            f'value: {value} is_in_cache: '
                            f'{cls.is_in_cache(service_key)}')
        else:
            value = SettingsManager.get_setting(service_key.short_key,
                                                default_value)
            MY_LOGGER.debug(f'Getting from cache: {service_key.short_key} '
                            f'value: {value} is_in_cache: '
                            f'{cls.is_in_cache(service_key)}')
        # MY_LOGGER.debug(f'full_setting_id: {full_setting_id} '
        #                   f'default: {default} value: {value}')
        return value

    @classmethod
    def is_in_cache(cls, service_key: ServiceID) -> bool:
        #  cls.check_reload()
        return SettingsManager.is_in_cache(service_key.short_key)

    @classmethod
    def set_setting_str(cls, service_key: ServiceID, value: str) -> bool:
        if service_key.service_type == ServiceType.ENGINE:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'TRACE service_key: {service_key} '
                                f'value: {value} value_type: {type(value)}')
        success, found_type = cls.type_and_validate_settings(service_key, value)
        passed: bool = SettingsManager.set_setting(service_key.short_key, value)
        return passed

    @classmethod
    def get_setting_str(cls, service_key: ServiceID,
                        ignore_cache: bool = False,
                        load_on_demand: bool = False,
                        default: str = None) -> str:
        """
        Gets the value of the given setting from the cache, or from settings.xml

        :param service_key: Identifies the setting to read
        :param ignore_cache: When True, reads directly from settings.xml. Does NOT
                             save value in cache
        :param load_on_demand:  When True, if setting not found in the cache,
                                reads from settings.xml and stores result in cache
        :param default: Value to use if no value (or setting) found.
        :return:
        """
        force_load: bool = False
        # MY_LOGGER.debug(f'ignore_cache: {ignore_cache} service_key: {service_key} '
        #                 f'setting_id: {service_key.setting_id}'
        #                 f' short_key: {service_key.short_key}')
        if ignore_cache and (service_key.setting_id == SettingProp.ENGINE):
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(
                    f'TRACE IGNORING CACHE id: {service_key}')
        if ignore_cache:
            try:
                value: str = cls.settings_wrapper.getString(service_key.short_key)
                return value.strip()
            except Exception as e:
                MY_LOGGER.exception(f'None value for {service_key.short_key}')
                return default
        # MY_LOGGER.debug(f'setting_id: {service_key.setting_id} service_id: '
        #                 f'{service_key.service_id}')
        value = cls._getSetting(service_key, default, load_on_demand)
        # MY_LOGGER.debug(f'value: {value}')
        return value

    @classmethod
    def get_setting_bool(cls, service_key: ServiceID,
                         ignore_cache: bool = False,
                         default: bool = None) -> bool:
        """

        :return:
        """
        value: bool | None = None
        if ignore_cache:
            try:
                value = cls.settings_wrapper.getBool(service_key.short_key)
                return value
            except Exception as e:
                MY_LOGGER.exception('')
        value = cls._getSetting(service_key, default)
        return value

    @classmethod
    def set_setting_bool(cls, service_key: ServiceID, value: bool) -> bool:
        """

        :return:
        """
        success, found_type = cls.type_and_validate_settings(service_key, value)
        return_value = SettingsManager.set_setting(service_key.short_key, value)
        return return_value

    @classmethod
    def get_setting_float(cls, service_key: ServiceID,
                          default_value: float = 0.0) -> float:
        """

        :return:
        """
        return SettingsLowLevel._getSetting(service_key, default_value)

    @classmethod
    def get_setting_int(cls, service_key: ServiceID,
                        default_value: int = 0) -> int:
        """

        :return:
        """
        cls.check_reload()
        value: int = SettingsManager.get_setting(service_key.short_key, default_value)
        # MY_LOGGER.debug(f'real_key: {real_key} value: {value}')
        return value

    @classmethod
    def set_setting_int(cls, service_key: ServiceID, value: int) -> bool:
        """

        :return:
        """
        success, found_type = cls.type_and_validate_settings(service_key, value)
        return SettingsManager.set_setting(service_key.short_key, value)

    @classmethod
    def update_cached_setting(cls, service_key: ServiceID, value: Any) -> None:
        SettingsManager.set_setting(service_key.short_key, value)

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
