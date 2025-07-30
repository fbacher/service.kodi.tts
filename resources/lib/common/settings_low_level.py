# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import copy
import threading
import time
from contextlib import AbstractContextManager

import xbmcaddon

from common import *

from backends.settings.service_types import (ServiceKey, Services, ServiceType,
                                             ServiceID, TTS_Type)
from backends.settings.setting_properties import SettingProp, SettingType
from backends.settings.settings_map import SettingsMap
from common.constants import Constants
from common.critical_settings import CriticalSettings
from common.logger import *
from common.monitor import Monitor
from common.setting_constants import Backends, Players
from common.kodiaddon import Addon
from common.settings_cache import SettingsIO, SettingsManager, SettingsWrapper

MY_LOGGER = BasicLogger.get_logger(__name__)



'''
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
'''


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
                MY_LOGGER.debug(f'TRACE Setting NOT supported for {service_key}')

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
        services_to_add: List[str] = []
        new_settings: Dict[ServiceID, str] = {}
        if service_key.service_type == ServiceType.ENGINE and not cls.all_engines_loaded:
            engine_id: str
            cls.all_engines_loaded = True
            #  full_setting_id, engine_id = cls.load_setting(ServiceKey.CURRENT_ENGINE_KEY)
            value = SettingsMap.load_setting(ServiceKey.CURRENT_ENGINE_KEY)
        '''
            #  if engine_id == Backends.AUTO_ID:
            #      engine_id = Backends.DEFAULT_ENGINE_ID
            #  new_settings[full_setting_id] = engine_id
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
        '''

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
            MY_LOGGER.debug(f'TRACE _load_settings service: {service_key} '
                            f'setting_id: {setting_id}'
                            f'service_id: {service_key.service_id} '
                            f'setting_id: {setting_id} '
                            f'key: {service_key.key} '
                            f'short_key: {service_key.short_key}')
        # Get Lock
        force_load: bool = False
        settings: Dict[str, None]
        settings = SettingProp.SETTINGS_BY_SERVICE_TYPE[service_key.service_type]
        #  MY_LOGGER.debug(f'service_key: {service_key} properties: {settings.keys()}')
        for setting_id in settings.keys():
            value: Any | None
            full_path: str = f'{setting_id}.{service_key.service_id}'
            if full_path in SettingsIO.ignore:
                if MY_LOGGER.isEnabledFor(DEBUG):
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
                value = SettingsMap.load_setting(service_key)
            elif force_load:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'FORCED load of property: {setting_id}')
                value = SettingsMap.load_setting(service_key)
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

                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'id: {full_setting_id} '
                                         f'value: {str_value} type: {type(value)}')
                    prefix: str = cls.getSettingIdPrefix(full_setting_id)
                    value_type = SettingProp.SettingTypes.get(prefix, None)
                    if value is None:
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
        return ServiceID(ServiceType.ENGINE, service_id=engine_id,
                         setting_id=TTS_Type.SERVICE_ID)

    @classmethod
    def set_engine(cls, engine_key: ServiceID) -> None:
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
        if service_key.service_type == SettingProp.ENGINE:
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

        cls.check_reload()
        load_on_demand = True
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'{service_key} is_in_cache: {cls.is_in_cache(service_key)}')
        if load_on_demand and not cls.is_in_cache(service_key):
            # value is NOT stored in settings cache. Need to manually push it to
            # all stack frames of cache (yuk).
            value = SettingsMap.load_setting(service_key)
            SettingsManager.load_setting_to_all_frames(service_key.short_key, value)
            value = SettingsManager.get_setting(service_key.short_key,
                                                default_value)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'Getting from cache: {service_key.short_key} '
                                  f'value: {value} setting_in_cache: '
                                  f'{cls.is_in_cache(service_key)}')
        else:
            value = SettingsManager.get_setting(service_key.short_key,
                                                default_value)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'Getting from cache: {service_key.short_key} '
                                  f'value: {value} setting_in_cache: '
                                  f'{cls.is_in_cache(service_key)}')
        return value

    @classmethod
    def is_in_cache(cls, service_key: ServiceID) -> bool:
        return SettingsManager.is_in_cache(service_key.short_key)

    @classmethod
    def set_setting_str(cls, service_key: ServiceID, value: str) -> bool:
        if service_key.service_type == ServiceType.ENGINE:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'TRACE service_key: {service_key} '
                                f'value: {value}')
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
        value = cls._getSetting(service_key, default, load_on_demand)
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
        value = cls._getSetting(service_key, default, load_on_demand=True)
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
