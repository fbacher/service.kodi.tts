# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import copy
import threading
import time
from contextlib import AbstractContextManager

import xbmcaddon

from common import *

from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties, SettingType
from backends.settings.settings_map import SettingsMap
from common.constants import Constants
from common.critical_settings import CriticalSettings
from common.logger import *
from common.monitor import Monitor
from common.setting_constants import Backends
from kutils.kodiaddon import Addon

module_logger = BasicLogger.get_logger(__name__)


class CachedSettings:
    settings: Dict[str, Union[Any, None]] = {}
    settings_changed: bool = False
    settings_update_begin: float = None

    def __init__(self, settings_to_copy: Dict[str, int | bool | str | None]) -> None:
        self.settings = copy.deepcopy(settings_to_copy)
        self.settings_changed = True
        if self.settings_update_begin is None:
            self.settings_update_begin = time.time()


class SettingsManager:

    # Initialize with one frame

    _settings_stack: List[CachedSettings] = [CachedSettings(settings_to_copy={})]

    @classmethod
    def set_setting(cls, setting_id: str,
                    value: int | bool | str | None = None) -> bool:
        """
        Backup a single setting to the top frome of save settings
        :param setting_id: full setting name ex. speed.google
        :param value: value of the setting
        :return:
        """
        changed: bool = False
        if cls._settings_stack[-1].settings.get(setting_id) != value:
            changed = True
            cls._settings_stack[-1].settings_changed = True
            if cls._settings_stack[-1].settings_update_begin is None:
                cls._settings_stack[-1].settings_update_begin = time.time()
            cls._settings_stack[-1].settings[setting_id] = value
        return changed

    @classmethod
    def load_settings(cls,
                      settings_to_backup: Dict[str, int | str | bool | None]) -> None:
        """
        Creates a new CachedSettings 'frame' from the given settings. The copy
        becomes the new top frame

        :param settings_to_backup: deep_copy is used to copy
        :return:
        """
        tts_logger: BasicLogger = BasicLogger.get_addon_logger()

        tts_logger.setLevel(INFO)
        tts_logger.info('tts_logger info')
        tts_logger.debug(f'tts_logger debug')
        module_logger.info('module_logger info')
        module_logger.debug(f'module_logger debug')

        new_frame: CachedSettings = CachedSettings(settings_to_backup)
        cls._settings_stack.append(new_frame)
        if SettingsLowLevel._logger.isEnabledFor(DEBUG):
            SettingsLowLevel._logger.debug(
                f'settings_to_backup len: {len(settings_to_backup)}'
                f' current_settings len: {len(cls._settings_stack[-1].settings)}')

    @classmethod
    def push_settings(cls) -> None:
        """
         Creates a new CachedSettings 'frame' from the current top frame. This
         saves the previous version of settings so that it can be restored if
         needed.

         :return:
         """
        current_settings: Dict[str, int | str | bool | None]
        current_settings = cls._settings_stack[-1].settings
        new_frame: CachedSettings = CachedSettings(current_settings)
        cls._settings_stack.append(new_frame)
        if SettingsLowLevel._logger.isEnabledFor(DEBUG):
            SettingsLowLevel._logger.debug(
                    f'settings_to_backup len: {len(current_settings)}'
                    f' current_settings len: {len(cls._settings_stack[-1].settings)}')
    @classmethod
    def restore_settings(cls) -> None:
        cls._settings_stack.pop()

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        return cls._settings_stack[-1].settings

    @classmethod
    def get_setting(cls, setting_id: str, default_value: Any) -> Any:
        """
        throws KeyError
        """
        value = cls._settings_stack[-1].settings.get(setting_id)
        if value is None or (isinstance(value, str) and value == ''):
            # cls._logger.debug(f'Using default value {setting_id} {default_value}')
            value = default_value
            if setting_id == 'converter':
                SettingsLowLevel._logger.dump_stack('Converter problem')
        #  SettingsLowLevel._logger.debug(f'setting_id: {setting_id} value: {value}')
        return value


    @classmethod
    def get_previous_setting(cls, setting_id: str, default_value: Any) -> Any:
        """
        throws KeyError
        """
        if len(cls._settings_stack) < 2:
            return None
        value = cls._settings_stack[-2].settings.get(setting_id)
        if value is None or (isinstance(value, str) and value == ''):
            # cls._logger.debug(f'Using default value {setting_id} {default_value}')
            value = default_value
            if setting_id == 'converter':
                SettingsLowLevel._logger.dump_stack('Converter problem')
        #  SettingsLowLevel._logger.debug(f'setting_id: {setting_id} value: {value}')
        return value

    @classmethod
    def is_empty(cls) -> bool:
        return not cls._settings_stack[-1].settings


class SettingsContext(AbstractContextManager):

    # module_logger = BasicLogger.get_logger(__name__)
    _logger: BasicLogger = module_logger

    def __init__(self):
        clz = type(self)
        # clz._logger = module_logger
        self.ks: xbmcaddon.Settings = None

    def __enter__(self) -> ForwardRef('SettingsContext'):
        self.ks = xbmcaddon.Addon(Constants.ADDON_ID).getSettings()
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

    _logger: BasicLogger = module_logger
    old_api: xbmcaddon.Addon = CriticalSettings.ADDON

    def __init__(self):
        clz = type(self)
        # clz._logger = module_logger

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
            value: float = clz.old_api.getSettingNumber(id)
        except TypeError:
            clz._logger.error(f'Setting {id} is not a float. Setting to None/default')
            value = None
        return value

    def getString(self, id: str) -> str:
        """
        Returns the value of a setting as a tring.

        :param id: string - id of the setting that the module needs to access.
        :return: string - Setting as a string

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
            clz._logger.debug(f'value: {value} id: {id}')
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
    _alternate_engine: str = None
    _logger: BasicLogger = module_logger
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
            #  SettingsLowLevel._logger = module_logger
            SettingsLowLevel._current_engine = None

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
            SettingsManager.push_settings()
            #  SettingsLowLevel._logger.debug('Backed up settings')
        except Exception:
            SettingsLowLevel._logger.exception("")

    @classmethod
    def restore_settings(cls) -> None:
        # get lock
        # set SETTINGS_BEING_CONFIGURED, SETTINGS_LAST_CHANGED
        #
        SettingsManager.restore_settings()
        SettingsLowLevel._logger.debug('TRACE Cancel changes')

    @staticmethod
    def get_changed_settings(settings_to_check: List[str]) -> List[str]:
        """

        :param settings_to_check:
        :return:
        """
        # SettingsLowLevel._logger.debug('entered')
        changed_settings = []
        for setting_id in settings_to_check:
            previous_value = SettingsManager.get_previous_setting(setting_id, None)
            try:
                current_value = SettingsLowLevel.get_addon().setting(setting_id)
            except Exception:
                current_value = previous_value

            if previous_value != current_value:
                changed = True
                if module_logger.isEnabledFor(DEBUG_VERBOSE):
                    SettingsLowLevel._logger.debug_verbose(f'setting changed: {setting_id} '
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
        if SettingsLowLevel._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            SettingsLowLevel._logger.debug_extra_verbose(f'full_setting_id:'
                                                         f' {full_setting_id} '
                                                         f'value: {value}')
        engine_id, setting_id = cls.splitSettingId(full_setting_id)
        if full_setting_id in SettingsProperties.TTS_SETTINGS:
            engine_id = Services.TTS_SERVICE

        if SettingsLowLevel._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            SettingsLowLevel._logger.debug_extra_verbose(f'setting_id: {setting_id}'
                                                         f' engine_id: {engine_id}')
        if not SettingsMap.is_valid_property(engine_id, setting_id):
            if SettingsLowLevel._logger.isEnabledFor(DEBUG_VERBOSE):
                SettingsLowLevel._logger.debug_verbose(
                    f'TRACE Setting {setting_id} NOT supported for {engine_id}')
        if setting_id is None or len(setting_id) == 0:
            setting_id = engine_id

        PROTO_LIST_BOOLS: List[bool] = [True, False]
        PROTO_LIST_FLOATS: List[float] = [0.7, 8.2]
        PROTO_LIST_INTEGERS: List[int] = [1, 57]
        PROTO_LIST_STRINGS: List[str] = ['a', 'b']
        try:
            try:
                setting_type = SettingsProperties.SettingTypes[setting_id]
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
                    expected_type = 'List[str'
                    if not isinstance(value, type(PROTO_LIST_STRINGS)):
                        type_error = True
            finally:
                pass
        except TypeError:
            SettingsLowLevel._logger.exception(
                    f'TRACE: failed to find type of setting: {full_setting_id}. '
                    f'Probably not defined in resources/settings.xml')
        except Exception:
            SettingsLowLevel._logger.exception(
                    f'TRACE: Bad setting_id: {setting_id}')
        if type_error:
            SettingsLowLevel._logger.debug(f'TRACE: incorrect type for setting: {full_setting_id} '
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
        if SettingsLowLevel._logger.isEnabledFor(DEBUG_VERBOSE):
            SettingsLowLevel._logger.debug_verbose('Tload_settingsRACE load_settings')
        blocked: bool = False
        while not SettingsLowLevel._loading.is_set():
            # If some other thread is loading, wait until finished, then exit.
            # The assumption is that a reload after a reload is not needed.
            # Besides, the code will still load from settings.xml when needed.

            blocked = True
            Monitor.exception_on_abort(timeout=0.10)

        try:
            SettingsLowLevel._loading.clear()
            if blocked:
                return
            new_settings: Dict[str, Any] = {}
            cls._load_settings(new_settings, Services.TTS_SERVICE)
            engine_id: str
            _, engine_id = cls.load_setting(SettingsProperties.ENGINE)
            if engine_id == Backends.AUTO_ID:
                engine_id = Backends.DEFAULT_ENGINE_ID
            cls._load_settings(new_settings, engine_id)

            SettingsLowLevel._current_engine = engine_id

            # validate new_settings
            SettingsManager.load_settings(new_settings)
            # release lock
            # Notify
        finally:
            SettingsLowLevel._loading.set()

    ignore: Dict[str, str] = {
        'addons_MD5.eSpeak': '',
        'addons_MD5.google': '',
        'addons_MD5.tts': '',
        # 'api_key.Cepstral': '',
        'api_key.google': '',
        'api_key.eSpeak': '',
        # 'api_key.ResponsiveVoice': '',
        'api_key.tts': '',
        'auto_item_extra_delay.eSpeak': '',
        'auto_item_extra_delay.tts': '',
        'auto_item_extra_delay.google': '',
        'auto_item_extra.eSpeak': '',
        'auto_item_extra.google': '',
        'auto_item_extra.tts': '',
        'background_progress_interval.eSpeak': '',
        'background_progress_interval.google': '',
        'background_progress_interval.tts': '',
        'cache_expiration_days.eSpeak': '',
        'cache_expiration_days.tts': '',
        'cache_path.eSpeak': '',
        'cache_path.google': '',
        'cache_path.tts': '',
        # 'cache_speech.eSpeak': '',
        # 'cache_speech.experimental': '',
        # 'cache_speech.google': '',
        # 'cache_speech.piper': '',
        # 'cache_speech.ResponsiveVoice': '',
        # 'cache_speech.sapi': '',
        # 'cache_speech.tts': '',
        'cache_speech.tts': '',
        'capital_recognition.eSpeak': '',
        'capital_recognition.google': '',
        # 'capital_recognition.Speech-Dispatcher': '',
        'capital_recognition.tts': '',
        'channels.eSpeak': '',
        'channels.google': '',
        'channels.tts': '',
        'converter.eSpeak': '',
        'converter.google': '',
        # 'converter.experimental': '',
        # 'converter.google': '',
        # 'converter.piper': '',
        # 'converter.ResponsiveVoice': '',
        # 'converter.sapi': '',
        'converter.tts': '',
        'core_version': '',
        'debug_log_level.eSpeak': '',
        'debug_log_level.google': '',
        # 'debug_log_level.tts': '',
        'delay_voicing.eSpeak': '',
        # 'delay_voicing.experimental': '',
        'delay_voicing.google': '',
        # 'delay_voicing.piper': '',
        # 'delay_voicing.sapi': '',
        'delay_voicing.tts': '',
        'disable_broken_services.eSpeak': '',
        'disable_broken_services.google': '',
        'disable_broken_services.tts': '',
        'engine.tts': '',
        'engine.google': '',
        'engine.eSpeak': '',
        'tts.tts': '',
        # 'gender.Cepstral': '',
        'gender.eSpeak': '',
        # 'gender.experimental': '',
        # 'gender.Flite': '',
        'gender.google': '',
        # 'gender.OSXSay': '',
        # 'gender.pico2wave': '',
        # 'gender.piper': '',
        # 'gender.ResponsiveVoice': '',
        # 'gender.sapi': '',
        # 'gender.Speech-Dispatcher': '',
        # 'gender.tts': '',
        'gender.tts': '',
        'gender_visible.eSpeak': '',
        'gender_visible.google': '',
        'gender_visible.tts': '',
        'gui.eSpeak': '',
        'gui.google': '',
        'gui.tts': '',
        #  'id.eSpeak': '',
        'id.eSpeak': '',
        'id.google': '',
        'id.tts': '',
        'language': '',
        # 'language.Cepstral': '',
        # 'language.eSpeak': '',
        # 'language.experimental': '',
        # 'language.Festival': '',
        # 'language.Flite': '',
        # 'language.google': '',
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
        'module.Speech-Dispatcher': '',
        'module.tts': '',
        'output_via.eSpeak': '',
        'output_via.google': '',
        'output_via.tts': '',
        'output_visible.eSpeak': '',
        'output_visible.google': '',
        'output_visible.tts': '',
        'override_poll_interval.eSpeak': '',
        'override_poll_interval.google': '',
        'override_poll_interval.tts': '',
        # 'pipe.Cepstral': '',
        'pipe.eSpeak': '',
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
        # 'pitch.google': '',
        # 'pitch.OSXSay': '',
        # 'pitch.pico2wave': '',
        # 'pitch.piper': '',
        # 'pitch.ResponsiveVoice': '',
        # 'pitch.sapi': '',
        # 'pitch.Speech-Dispatcher': '',
        'pitch.tts': '',
        'pitch.google': '',
        # 'player.Cepstral': '',
        # 'player.eSpeak': '',
        # 'player.experimental': '',
        # 'player.Festival': '',
        # 'player.Flite': '',
        # 'player.google': '',
        # 'player_mode.google': '',
        'player_mode.tts': '',
        # 'player.OSXSay': '',
        # 'player.pico2wave': '',
        # 'player.piper': '',
        'player_pitch.eSpeak': '',
        'player_pitch.google': '',
        # 'player_pitch.experimental': '',
        # 'player_pitch.ResponsiveVoice': '',
        'player_pitch.tts': '',
        # 'player.ResponsiveVoice': '',
        # 'player.sapi': '',
        # 'player.Speech-Dispatcher': '',
        'player_speed.eSpeak': '',
        'player_speed.google': '',
        # 'player_speed.ResponsiveVoice': '',
        'player_speed.tts': '',
        'player.tts': '',
        'player_volume.eSpeak': '',
        'player_volume.google': '',
        'player_volume.tts': '',
        'poll_interval.eSpeak': '',
        'poll_interval.google': '',
        'poll_interval.tts': '',
        'punctuation.eSpeak': '',
        'punctuation.google': '',
        # 'punctuation.Speech-Dispatcher': '',
        'punctuation.tts': '',
        'reader_on.eSpeak': '',
        'reader_on.google': '',
        'reader_on.tts': '',
        'remote_pitch.eSpeak': '',
        'remote_pitch.experimental': '',
        'remote_pitch.google': '',
        'remote_pitch.ResponsiveVoice': '',
        'remote_pitch.tts': '',
        'remote_server.Speech-Dispatcher': '',
        'remote_speed.eSpeak': '',
        'remote_speed.google': '',
        'remote_speed.tts': '',
        'remote_volume.eSpeak': '',
        'remote_volume.google': '',
        'remote_volume.tts': '',
        'settings_being_configured.eSpeak': '',
        'settings_being_configured.google': '',
        'settings_being_configured.tts': '',
        'settings_digest.eSpeak': '',
        'settings_digest.google': '',
        'settings_digest.tts': '',
        'settings_last_changed.eSpeak': '',
        'settings_last-changed.google': '',
        'settings_last_changed.tts': '',
        'speak_background_progress_during_media.eSpeak': '',
        'speak_background_progress_during_media.tts': '',
        'speak_background_progress.eSpeak': '',
        'speak_background_progress.tts': '',
        'speak_list_count.eSpeak': '',
        'speak_list_count.tts': '',
        'speak_on_server.eSpeak': '',
        'speak_on_server.experimental': '',
        'speak_on_server.google': '',
        'speak_on_server.ResponsiveVoice': '',
        'speak_on_server.tts': '',
        'speak_via_kodi': '',
        'speak_via_kodi.eSpeak': '',
        'speak_via_kodi.google': '',
        'speak_via_kodi.tts': '',
        'Speech-Dispatcher.eSpeak': '',
        'Speech-Dispatcher.google': '',
        # 'Speech-Dispatcher-module': '',
        'Speech-Dispatcher.tts': '',
        'speed_enabled.eSpeak': '',
        # 'speed_enabled.experimental': '',
        'speed_enabled.google': '',
        # 'speed_enabled.piper': '',
        # 'speed_enabled.ResponsiveVoice': '',
        # 'speed_enabled.sapi': '',
        'speed_enabled.tts': '',
        'speed.eSpeak': '',
        'speed.google': '',
        'speed_visible.eSpeak': '',
        'speed_visible.google': '',
        'speed_visible.tts': '',
        'spelling.eSpeak': '',
        'spelling.google': '',
        # 'spelling.Speech-Dispatcher': '',
        'spelling.tts': '',
        'ttsd_host.eSpeak': '',
        'ttsd_host.google': '',
        'ttsd_host.tts': '',
        'ttsd_port.eSpeak': '',
        'ttsd_port.google': '',
        'ttsd_port.tts': '',
        'use_aoss.eSpeak': '',
        'use_aoss.google': '',
        # 'use_aoss.experimental': '',
        # 'use_aoss.ResponsiveVoice': '',
        'use_aoss.tts': '',
        # 'use_temp_settings.tts': '',
        'use_tmpfs.eSpeak': '',
        'use_tmpfs.tts': '',
        'version.eSpeak': '',
        'version.tts': '',
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
        'voice.pico2wave': '',
        'voice.piper': '',
        'voice.ResponsiveVoice': '',
        'voice.sapi': '',
        'voice.Speech-Dispatcher': '',
        'voice.tts': '',
        'voice_visible.eSpeak': '',
        'voice_visible.google': '',
        'voice_visible.tts': '',
        'volume.eSpeak': '',
        'volume.tts': '',
        # 'volume_visible.tts'
    }

    @classmethod
    def _load_settings(cls, new_settings: Dict[str, Any], engine_id: str) -> None:
        """
        Load ALL of the settings for the current backend.
        Settings from multiple backends can be in the cache simultaneously
        Settings not supported by a backend are not read and not put into
        the cache. The settings.xml can have orphaned settings as long as
        kodi allows it, based on the rules in the addon's settings.xml definition
        file.

        Ignore any other changes to settings until finished
        """

        if SettingsLowLevel._logger.isEnabledFor(DEBUG_VERBOSE):
            SettingsLowLevel._logger.debug_verbose('TRACE load_settings')
        # Get Lock
        force_load: bool = False
        for setting_id in SettingsProperties.ALL_SETTINGS:
            value: Any | None
            service_id: str = engine_id
            key: str = cls.getExpandedSettingId(setting_id, engine_id)
            if key in cls.ignore:
               continue
            else:
                if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    cls._logger.debug_extra_verbose(f'key: {key} not in cls.ignore')

            if setting_id in SettingsProperties.TOP_LEVEL_SETTINGS:
                continue
            if setting_id in SettingsProperties.TTS_SETTINGS:
                service_id = Services.TTS_SERVICE
            if SettingsMap.is_valid_property(service_id, setting_id):
                key, value = cls.load_setting(setting_id, service_id)
            elif force_load:
                SettingsLowLevel._logger.debug(f'FORCED load of property: {setting_id}')
                key, value = cls.load_setting(setting_id, service_id)
            else:
                SettingsLowLevel._logger.debug_extra_verbose(f'Skipping load of property: {setting_id} '
                                  f'for service_id: {service_id} key: {key}')
                continue
            if value is not None:
                if SettingsLowLevel._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    SettingsLowLevel._logger.debug_extra_verbose(f'Adding {key} '
                                                                 f'value: {value} '
                                                                 f'to settings cache')
                new_settings[key] = value

    @classmethod
    def load_setting(cls, setting_id: str,
                     engine_id: str = None) -> Tuple[str, Any | None]:
        if setting_id in SettingsProperties.TTS_SETTINGS:
            engine_id = Services.TTS_SERVICE

        found: bool = True
        force_load: bool = False
        if not force_load and not SettingsMap.is_valid_property(engine_id, setting_id):
            found = False
            if SettingsLowLevel._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                SettingsLowLevel._logger.debug_extra_verbose(f'Setting {setting_id} '
                                                             f'NOT supported for '
                                                             f'{engine_id}')
        key: str = cls.getExpandedSettingId(setting_id, engine_id)
        if key in cls.ignore:
            return key, None
        # cls._logger.debug(f'key: {key}')
        # A few values are constant (such as some engines can't play audio,
        # or adjust volume)
        const_value: Any = SettingsMap.get_const_value(engine_id, setting_id)
        value: Any | None = None
        try:
            '''
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
            '''
            setting_type = SettingsProperties.SettingTypes[setting_id]
            if setting_type == SettingType.BOOLEAN_TYPE:
                value = cls.settings_wrapper.getBool(key)
            elif setting_type == SettingType.BOOLEAN_LIST_TYPE:
                value = cls.settings_wrapper.getBoolList(key)
            elif setting_type == SettingType.FLOAT_TYPE:
                value = cls.settings_wrapper.getNumber(key)
            elif setting_type == SettingType.FLOAT_LIST_TYPE:
                value = cls.settings_wrapper.getNumberList(key)
            elif setting_type == SettingType.INTEGER_TYPE:
                value = cls.settings_wrapper.getInt(key)
            elif setting_type == SettingType.INTEGER_LIST_TYPE:
                value = cls.settings_wrapper.getIntList(key)
            elif setting_type == SettingType.STRING_TYPE:
                value = cls.settings_wrapper.getString(key)
            elif setting_type == SettingType.STRING_LIST_TYPE:
                value = cls.settings_wrapper.getStringList(key)
            if const_value is not None:
                value = const_value
            # SettingsLowLevel._logger.debug(f'found key: {key} value: {value}')
        except KeyError:
            SettingsLowLevel._logger.exception(
                    f'failed to find setting key: {key}. '
                    f'Probably not defined in resources/settings.xml')
        except TypeError:
            SettingsLowLevel._logger.exception(f'failed to get type of setting: '
                                               f'{key}.{engine_id} ')
            if force_load:
                try:
                    value_str: str = xbmcaddon.Addon(Constants.ADDON_ID).getSetting(key)
                    if value_str is None:
                        value = None
                    else:
                        """
                        match SettingsProperties.SettingTypes[setting_id]:
                            case SettingType.BOOLEAN_TYPE:
                                value = bool(value_str)
                            case SettingType.FLOAT_TYPE:
                                value = float(value_str)
                            case SettingType.INTEGER_TYPE:
                                value = int(value_str)
                            case SettingType.STRING_TYPE:
                                value = value_str
                        """
                        setting_type = SettingsProperties.SettingTypes[setting_id]
                        if setting_type == SettingType.BOOLEAN_TYPE:
                            value = bool(value_str)
                        elif setting_type == SettingType.FLOAT_TYPE:
                            value = float(value_str)
                        elif setting_type == SettingType.INTEGER_TYPE:
                            value = int(value_str)
                        elif setting_type == SettingType.STRING_TYPE:
                            value = value_str
                except Exception as e:
                    SettingsLowLevel._logger.exception(
                        f'Second attempt to read setting {setting_id} failed')
        if value is None:
            try:
                value = SettingsMap.get_default_value(engine_id, setting_id)
            except Exception as e:
                SettingsLowLevel._logger.exception(f'Can not set default for '
                                      f'{setting_id} {engine_id}')
        if value and SettingsLowLevel._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            SettingsLowLevel._logger.debug_extra_verbose(f'Read {key} value: {value}')
        #  SettingsLowLevel._logger.debug(f'Read {key} value: {value}')
        return key, value

    @classmethod
    def configuring_settings(cls):
        #  SettingsLowLevel._logger.debug('configuring_settings hardcoded to false')
        return False

    @classmethod
    def getExpandedSettingId(cls, setting_id: str, service_id: str) -> str:
        tmp_id: List[str] = setting_id.split(sep=".", maxsplit=2)
        real_key: str

        if len(tmp_id) > 1:
            #     SettingsLowLevel._logger.debug(f'already expanded: {setting_id}')
            real_key = setting_id
        else:
            suffix: str = ''
            if service_id is None:
                if setting_id not in SettingsProperties.TOP_LEVEL_SETTINGS:
                    service_id = SettingsLowLevel._current_engine

            if service_id:
                suffix = "." + service_id

            real_key: str = setting_id + suffix
        # SettingsLowLevel._logger.debug(
        #         f'in: {setting_id} out: {real_key} len(tmp_id): {len(tmp_id)}')
        return real_key

    @classmethod
    def splitSettingId(cls, expanded_setting: str) -> Tuple[str | None, str | None]:
        tmp_id: List[str] = expanded_setting.split(sep=".", maxsplit=2)
        if len(tmp_id) == 1:
            return tmp_id[0], None
        if len(tmp_id) == 2:
            return tmp_id[1], tmp_id[0]

        SettingsLowLevel._logger.debug(f'Malformed setting id: {expanded_setting}')
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
        SettingsLowLevel._logger.debug(
                f'TRACE getRealSetting NOT from cache id: {setting_id} backend: '
                f'{backend_id}')
        if backend_id is None or len(backend_id) == 0:
            backend_id = SettingsLowLevel._current_engine
            if backend_id is None or len(backend_id) == 0:
                SettingsLowLevel._logger.error("TRACE null or empty backend")
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        try:
            """
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
            """
            setting_type = SettingsProperties.SettingTypes[setting_id]
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
            SettingsLowLevel._logger.exception('')

    @classmethod
    def commit_settings(cls):
        """
        Persist all settings from the top frame SettingsManager to settings.xml.

        All settings in Settings and SettingsLowLevel are stored in this top frame.
        Therefore, the most up-to-date version of the settings is persisted
        to settings.xml

        :return:
        """
        #  SettingsLowLevel._logger.debug('TRACE commit_settings')
        addon: xbmcaddon = xbmcaddon.Addon(Constants.ADDON_ID)

        for full_setting_id, value in SettingsManager.get_settings().items():
            full_setting_id: str
            value: Any
            value_type: SettingType | None = None
            str_value: str = ''
            try:
                str_value = str(value)
                if full_setting_id == SettingsProperties.ENGINE:
                    if SettingsLowLevel._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                        SettingsLowLevel._logger.debug_extra_verbose(f'TRACE Commiting ENGINE value: {str_value}')

                if SettingsLowLevel._logger.isEnabledFor(DEBUG_VERBOSE):
                    SettingsLowLevel._logger.debug_verbose(f'id: {full_setting_id} '
                                                           f'value: {str_value}')
                prefix: str = cls.getSettingIdPrefix(full_setting_id)
                value_type = SettingsProperties.SettingTypes.get(prefix, None)
                if value == 'NO_VALUE':
                    SettingsLowLevel._logger.debug(f'Expected setting not found {prefix}')
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
                    cls.settings_wrapper.setString(full_setting_id, value)
                if value_type == SettingType.STRING_LIST_TYPE:
                    cls.settings_wrapper.setStringList(full_setting_id, value)
            except Exception as e:
                SettingsLowLevel._logger.exception('')
                SettingsLowLevel._logger.exception(f'Error saving setting: {full_setting_id} '
                                      f'value: {str_value} as '
                                      f'{value_type.name}')
        engine = addon.getSettingString('engine')
        #  addon.setSettingString('engine', engine)

        #  del SettingsLowLevel.all_settings
        #  SettingsLowLevel.all_settings = addon.getSettings()
        #  SettingsLowLevel.settings_wrapper = SettingsLowLevel.all_settings

    @classmethod
    def get_engine_id_ll(cls, default: str = None,
                      bootstrap: bool = False) -> str:
        """
        :return:
        """
        # SettingsLowLevel._logger.debug(f'default: {default} boostrap {bootstrap} current: '
        #                                f'{SettingsLowLevel._current_engine}')
        ignore_cache = True
        engine_id: str = None
        if bootstrap:
            ignore_cache = True
        elif SettingsLowLevel._current_engine is not None:
            engine_id = SettingsLowLevel._current_engine
        if engine_id is None:
            engine_id = cls.get_setting_str(SettingsProperties.ENGINE, engine_id=None,
                                            ignore_cache=ignore_cache,
                                            default=default)
        #  SettingsLowLevel._logger.debug(f'TRACE get_engine_id_ll: {engine_id}')
        SettingsLowLevel._current_engine = engine_id
        return engine_id

    @classmethod
    def set_backend_id(cls, backend_id: str) -> None:
        #  SettingsLowLevel._logger.debug(f'TRACE set backend_id: {backend_id}')
        if backend_id is None or len(backend_id) == 0:
            SettingsLowLevel._logger.debug(f'invalid backend_id Not saving')
            return

        success: bool = cls.set_setting_str(SettingsProperties.ENGINE, backend_id)
        SettingsLowLevel._current_engine = backend_id

    @classmethod
    def setSetting(cls, setting_id: str, value: Any,
                   engine_id: str) -> bool:

        real_key = cls.getExpandedSettingId(setting_id, engine_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        try:
            success: bool = SettingsManager.set_setting(real_key, value)
            return success
        except:
            SettingsLowLevel._logger.exception('')
            SettingsLowLevel._logger.debug(f'TRACE: type mismatch')

    @classmethod
    def check_reload(cls):
        if SettingsManager.is_empty():
            cls.load_settings()

    @classmethod
    def getSetting(cls, setting_id: str, service_id: str | None,
                   default_value: Any | None = None) -> Any:
        if setting_id == SettingsProperties.ENGINE:
            return cls.get_engine_id_ll()
        real_key = cls.getExpandedSettingId(setting_id, service_id)
        cls.check_reload()

        value: Any = cls._getSetting(setting_id, service_id, default_value)
        return value

    @classmethod
    def _getSetting(cls, setting_id: str, service_id: str | None,
                    default_value: Any | None = None) -> Any:
        value: Any = None
        full_setting_id = cls.getExpandedSettingId(setting_id, service_id)
        try:
            cls.check_reload()
            value: Any = SettingsManager.get_setting(full_setting_id, default_value)
            # cls._logger.debug(f'full_setting_id: {full_setting_id} '
            #                   f'default: {default_value} value: {value}')
        except KeyError:
            cls._logger.debug(f'KeyError with {full_setting_id} {setting_id}'
                              f' {service_id} {default_value}')
            value = SettingsLowLevel.getRealSetting(setting_id, service_id, default_value)
            cls._logger.debug(f'value: {value}')
            SettingsManager.set_setting(full_setting_id, value)
        # SettingsLowLevel._logger.debug(f'setting_id: {full_setting_id} value: {value}')
        return value

    @classmethod
    def set_setting_str(cls, setting_id: str, value: str, engine_id: str = None) -> bool:
        real_key = cls.getExpandedSettingId(setting_id, engine_id)
        if setting_id == SettingsProperties.ENGINE:
            if SettingsLowLevel._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                SettingsLowLevel._logger.debug_extra_verbose(f'TRACE engine_id: '
                                                             f'{value} real_key: '
                                                             f'{real_key} '
                                                             f'value: {value}')
        success, found_type = cls.type_and_validate_settings(real_key, value)
        passed: bool = SettingsManager.set_setting(real_key, value)
        return passed

    @classmethod
    def get_setting_str(cls, setting_id: str, engine_id: str = None,
                        ignore_cache: bool = False,
                        default: str = None) -> str:
        force_load: bool = False
        real_key = cls.getExpandedSettingId(setting_id, engine_id)
        if ignore_cache and setting_id == SettingsProperties.ENGINE:
            if SettingsLowLevel._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                SettingsLowLevel._logger.debug_extra_verbose(
                    f'TRACE get_setting_str IGNORING CACHE id: {setting_id}'
                    f' {engine_id} -> {real_key}')
        if ignore_cache:
            try:
                value: str = cls.settings_wrapper.getString(real_key)
                return value.strip()
            except Exception as e:
                SettingsLowLevel._logger.exception('')
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
            if SettingsLowLevel._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                SettingsLowLevel._logger.debug_extra_verbose(
                        f'TRACE get_setting_str IGNORING CACHE id: {setting_id}')
        real_key = cls.getExpandedSettingId(setting_id, engine_id)
        value: bool = None
        if ignore_cache:
            try:
                value = cls.settings_wrapper.getBool(real_key)
            except Exception as e:
                SettingsLowLevel._logger.exception('')
        value = cls._getSetting(setting_id, engine_id, default)
        return value

    @classmethod
    def set_setting_bool(cls, setting_id: str, value: bool,
                         backend_id: str = None) -> bool:
        """

        :return:
        """
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        return_value = SettingsManager.set_setting(real_key, value)
        current_value: bool = cls.get_setting_bool(setting_id, backend_id)
        return return_value

    @classmethod
    def get_setting_float(cls, setting_id: str, backend_id: str = None,
                          default_value: float = 0.0) -> float:
        """

        :return:
        """
        return SettingsLowLevel._getSetting(setting_id, backend_id, default_value)

    @classmethod
    def get_setting_int(cls, setting_id: str, service_id: str = None,
                        default_value: int = 0) -> int:
        """

        :return:
        """
        cls.check_reload()
        real_key = cls.getExpandedSettingId(setting_id, service_id)
        value: int = SettingsManager.get_setting(real_key, default_value)
        # cls._logger.debug(f'real_key: {real_key} value: {value}')
        return value

    @classmethod
    def set_setting_int(cls, setting_id: str, value: int, backend_id: str = None) -> bool:
        """

        :return:
        """
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        success, found_type = cls.type_and_validate_settings(real_key, value)
        return SettingsManager.set_setting(real_key, value)

    @classmethod
    def update_cached_setting(cls, setting_id: str, value: Any,
                              backend_id: str = None) -> None:
        real_key = cls.getExpandedSettingId(setting_id, backend_id)
        SettingsManager.set_setting(real_key, value)

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
