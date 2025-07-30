# coding=utf-8

"""
Provides the ability to have a settings cache which is backed by settings.xml

Reasons for this include:
  - Can have a stack of settings, with the top being the current settings and
    the deeper stack entries representing different generations of changes. For
    practical purposes there are only two stack levels. Normally only level 0 exists
    and used. However, during configuration there can be two levels. If the user
    decides to save and commit the settings, they are copied to level 0. Otherwise,
    level 1 is discarded and all settings instantly revert back to where they were
    prior to configuration.
"""

from __future__ import annotations  # For union operator |

import copy
import threading
import time

import xbmcaddon

from backends.settings.setting_properties import SettingProp, SettingType
from common import *

from backends.settings.service_types import (ServiceKey, Services, ServiceType,
                                             ServiceID, TTS_Type)
from common.constants import Constants
from common.critical_settings import CriticalSettings
from common.logger import *

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
    """
    Contains and manages the settings stack.
    """

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
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'frame: {frame} setting:'
                                        f' {setting_id} != {value}')
                    '''
                    Don't record as a change since this is loading from settings.xml.
                    A change indicates that results need to be saved to settings.xml
                    '''
                    cls._settings_stack[frame].settings[setting_id] = value
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        loaded: bool
                        loaded = setting_id in cls._settings_stack[frame].settings.keys()
                        MY_LOGGER.debug_v(f'{setting_id} in setting_stack[{frame}] = '
                                          f'{loaded}')
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
            in_stack: bool = setting_id in cls._settings_stack[-1].settings.keys()
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                if not in_stack:
                    for i in range(len(cls._settings_stack)):
                        MY_LOGGER.debug_v(f'idx: {i} '
                                          f'{cls._settings_stack[i].settings.keys()} \n')
            return in_stack

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
            value = default_value
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            if setting_id == 'converter':
                    MY_LOGGER.dump_stack('Converter problem')
            MY_LOGGER.debug_v(f'get_previous_setting setting_id: {setting_id}'
                              f' value: {value}')
        return value

    @classmethod
    def is_empty(cls) -> bool:
        with cls._settings_lock:
            return not cls._settings_stack[-1].settings


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


class SettingsIO:

    #   TODO: Eliminate this by declaring all settings in SettingsMap.
    # Ignore Settings in this dict
    ignore: Dict[str, str] = {
        'addons_MD5.eSpeak'                            : '',
        'addons_MD5.google'                            : '',
        # 'addons_MD5.tts': '',
        'addons_MD5.powershell'                        : '',
        # 'api_key.Cepstral': '',
        'api_key.google'                               : '',
        'api_key.eSpeak'                               : '',
        'api_key.powershell'                           : '',
        # 'api_key.ResponsiveVoice': '',setting_id
        'api_key.tts'                                  : '',
        'auto_item_extra_delay.eSpeak'                 : '',
        #  'auto_item_extra_delay.tts': '',
        'auto_item_extra_delay.google'                 : '',
        'auto_item_extra_delay.powershell'             : '',
        'auto_item_extra.eSpeak'                       : '',
        'auto_item_extra.google'                       : '',
        'auto_item_extra.powershell'                   : '',
        #  'auto_item_extra.tts': '',
        'background_progress_interval.eSpeak'          : '',
        'background_progress_interval.google'          : '',
        'background_progress_interval.powershell'      : '',
        #  'background_progress_interval.tts': '',
        'cache_expiration_days.eSpeak'                 : '',
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
        'cache_speech.tts'                             : '',
        'capital_recognition.eSpeak'                   : '',
        'capital_recognition.google'                   : '',
        'capital_recognition.powershell'               : '',
        # 'capital_recognition.Speech-Dispatcher': '',
        'capital_recognition.tts'                      : '',
        'channels.eSpeak'                              : '',
        'channels.google'                              : '',
        'channels.powershell'                          : '',
        #  'converter.eSpeak': '',
        #  'converter.powershell': '',
        # 'converter.experimental': '',
        # 'converter.google': '',
        # 'converter.piper': '',
        # 'converter.ResponsiveVoice': '',
        # 'converter.sapi': '',
        'converter.tts'                                : '',
        'core_version'                                 : '',
        'debug_log_level.eSpeak'                       : '',
        'debug_log_level.google'                       : '',
        'debug_log_level.powershell'                   : '',
        # 'debug_log_level.tts': '',
        'delay_voicing.eSpeak'                         : '',
        # 'delay_voicing.experimental': '',
        'delay_voicing.google'                         : '',
        'delay_voicing.powershell'                     : '',
        # 'delay_voicing.piper': '',
        # 'delay_voicing.sapi': '',
        'delay_voicing.tts'                            : '',
        'disable_broken_services.eSpeak'               : '',
        'disable_broken_services.google'               : '',
        'disable_broken_services.powershell'           : '',
        # 'disable_broken_services.tts': '',
        ' fr .tts'                                     : '',
        'engine.google'                                : '',
        'engine.no_engine'                             : '',
        'engine.powershell'                            : '',
        'engine.eSpeak'                                : '',
        'tts.tts'                                      : '',
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
        'gender.tts'                                   : '',
        # 'gender_visible.eSpeak': '',
        # 'gender_visible.google': '',
        # 'gender_visible.powershell': '',
        'gender_visible.tts'                           : '',
        'gui.eSpeak'                                   : '',
        'gui.google'                                   : '',
        'gui.powershell'                               : '',
        'gui.tts'                                      : '',
        #  'id.eSpeak': '',
        'id.eSpeak'                                    : '',
        'id.google'                                    : '',
        'id.powershell'                                : '',
        'id.tts'                                       : '',
        'language'                                     : '',
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
        'language.tts'                                 : '',
        # 'lastnotified_stable': '',
        # 'lastnotified_version': '',
        'module.eSpeak'                                : '',
        'module.google'                                : '',
        'module.powershell'                            : '',
        'module.Speech-Dispatcher'                     : '',
        'module.tts'                                   : '',
        'output_via.eSpeak'                            : '',
        'output_via.google'                            : '',
        'output_via.powershell'                        : '',
        'output_via.tts'                               : '',
        'output_visible.eSpeak'                        : '',
        'output_visible.google'                        : '',
        'output_visible.powershell'                    : '',
        'output_visible.tts'                           : '',
        'override_poll_interval.eSpeak'                : '',
        'override_poll_interval.google'                : '',
        'override_poll_interval.powershell'            : '',
        # 'override_poll_interval.tts': '',
        # 'pipe.Cepstral': '',
        'pipe.eSpeak'                                  : '',
        'pipe.powershell'                              : '',
        'pipe.google'                                  : '',
        # 'pipe.experimental': '',
        # 'pipe.Festival': '',
        # 'pipe.Flite': '',
        # 'pipe.OSXSay': '',
        # 'pipe.pico2wave': '',
        # 'pipe.piper': '',
        # 'pipe.ResponsiveVoice': '',
        # 'pipe.sapi': '',
        # 'pipe.Speech-Dispatcher': '',
        'pipe.tts'                                     : '',
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
        'pitch.tts'                                    : '',
        'pitch.google'                                 : '',
        'pitch.powershell'                             : '',
        # 'player_key.Cepstral': '',
        # 'player_key.eSpeak': '',
        # 'player_key.experimental': '',
        # 'player_key.Festival': '',
        # 'player_key.Flite': '',
        # 'player_key.google': '',
        # 'player_mode.google': '',
        # 'player_mode.powershell': '',
        # 'player_mode.eSpeak',
        'player_mode.tts'                              : '',
        # 'player_key.OSXSay': '',
        # 'player_key.pico2wave': '',
        # 'player_key.piper': '',
        'player_pitch.eSpeak'                          : '',
        'player_pitch.google'                          : '',
        'player_pitch.powershell'                      : '',
        # 'player_pitch.experimental': '',
        # 'player_pitch.ResponsiveVoice': '',
        'player_pitch.tts'                             : '',
        # 'player_key.ResponsiveVoice': '',
        # 'player_key.sapi': '',
        # 'player_key.Speech-Dispatcher': '',
        'player_speed.eSpeak'                          : '',
        'player_speed.google'                          : '',
        'player_speed.powershell'                      : '',
        # 'player_speed.ResponsiveVoice': '',
        'player_speed.tts'                             : '',
        'player_key.tts'                               : '',
        'player_volume.eSpeak'                         : '',
        'player_volume.google'                         : '',
        'player_volume.powershell'                     : '',
        'player_volume.tts'                            : '',
        'poll_interval.eSpeak'                         : '',
        'poll_interval.google'                         : '',
        # 'poll_interval.tts'                            : '',
        'poll_internal.powershell'                     : '',
        'punctuation.eSpeak'                           : '',
        'punctuation.google'                           : '',
        'punctuation.powershell'                       : '',
        # 'punctuation.Speech-Dispatcher': '',
        'punctuation.tts'                              : '',
        'reader_on.eSpeak'                             : '',
        'reader_on.google'                             : '',
        'reader_on.powershell'                         : '',
        #  'reader_on.tts': '',
        'remote_pitch.eSpeak'                          : '',
        'remote_pitch.experimental'                    : '',
        'remote_pitch.google'                          : '',
        'remote_pitch.powershell'                      : '',
        'remote_pitch.ResponsiveVoice'                 : '',
        'remote_pitch.tts'                             : '',
        'remote_server.Speech-Dispatcher'              : '',
        'remote_speed.eSpeak'                          : '',
        'remote_speed.google'                          : '',
        'remote_speed.powershell'                      : '',
        'remote_speed.tts'                             : '',
        'remote_volume.eSpeak'                         : '',
        'remote_volume.google'                         : '',
        'remote_volume.powershell'                     : '',
        'remote_volume.tts'                            : '',
        'settings_digest.eSpeak'                       : '',
        'settings_digest.google'                       : '',
        'settings_digest.powershell'                   : '',
        #  'settings_digest.tts': '',
        'settings_last_changed.eSpeak'                 : '',
        'settings_last_changed.google'                 : '',
        'settings_last_changed.powershell'             : '',
        'settings_last_changed.tts'                    : '',
        'speak_background_progress_during_media.eSpeak': '',
        #  'speak_background_progress_during_media.tts': '',
        'speak_background_progress.eSpeak'             : '',
        'speak_background_progress.powershell'         : '',
        #  'speak_background_progress.tts': '',
        'speak_list_count.eSpeak'                      : '',
        'speak_list_count.powershell'                  : '',
        #  'speak_list_count.tts': '',
        'speak_on_server.eSpeak'                       : '',
        'speak_on_server.experimental'                 : '',
        'speak_on_server.google'                       : '',
        'speak_on_server.powershell'                   : '',
        'speak_on_server.ResponsiveVoice'              : '',
        'speak_on_server.tts'                          : '',
        # 'speak_via_kodi'                               : '',
        # 'speak_via_kodi.eSpeak'                        : '',
        # 'speak_via_kodi.google'                        : '',
        # 'speak_via_kodi.powershell'                    : '',
        # 'speak_via_kodi.tts'                           : '',
        'Speech-Dispatcher.eSpeak'                     : '',
        'Speech-Dispatcher.google'                     : '',
        'Speech-Dispatcher.powershell'                 : '',
        # 'Speech-Dispatcher-module': '',
        'Speech-Dispatcher.tts'                        : '',
        'speed_enabled.eSpeak'                         : '',
        # 'speed_enabled.experimental': '',
        'speed_enabled.google'                         : '',
        'speed_enabled.powershell'                     : '',
        # 'speed_enabled.piper': '',
        # 'speed_enabled.ResponsiveVoice': '',
        # 'speed_enabled.sapi': '',
        'speed_enabled.tts'                            : '',
        'speed.eSpeak'                                 : '',
        'speed.google'                                 : '',
        'speed.powershell'                             : '',
        'speed_visible.eSpeak'                         : '',
        'speed_visible.google'                         : '',
        'speed_visible.powershell'                     : '',
        'speed_visible.tts'                            : '',
        'spelling.eSpeak'                              : '',
        'spelling.google'                              : '',
        'spelling.powershell'                          : '',
        # 'spelling.Speech-Dispatcher': '',
        'spelling.tts'                                 : '',
        'ttsd_host.eSpeak'                             : '',
        'ttsd_host.google'                             : '',
        'ttsd_host.tts'                                : '',
        'ttsd_port.eSpeak'                             : '',
        'ttsd_port.google'                             : '',
        'ttsd_port.powershell'                         : '',
        'ttsd_port.tts'                                : '',
        'use_aoss.eSpeak'                              : '',
        'use_aoss.google'                              : '',
        'use_aoss.powershell'                          : '',
        # 'use_aoss.experimental': '',
        # 'use_aoss.ResponsiveVoice': '',
        'use_aoss.tts'                                 : '',
        # 'use_temp_settings.tts': '',
        # 'use_tmpfs.eSpeak'                             : '',
        # 'use_tmpfs.tts'                                : '',
        'version.eSpeak'                               : '',
        #  'version.tts': '',
        'voice.Cepstral'                               : '',
        # 'voice.eSpeak': '',
        'voice.experimental'                           : '',
        'voice.Festival'                               : '',
        'voice.Flite'                                  : '',
        # 'voice.google': '',
        'voice.OSXSay'                                 : '',
        'voice_path.eSpeak'                            : '',
        'voice_path.piper'                             : '',
        'voice_path.tts'                               : '',
        'voice_path.google'                            : '',
        'voice_path.powershell'                        : '',
        'voice.pico2wave'                              : '',
        'voice.piper'                                  : '',
        'voice.ResponsiveVoice'                        : '',
        'voice.sapi'                                   : '',
        'voice.Speech-Dispatcher'                      : '',
        'voice.tts'                                    : '',
        'voice_visible.eSpeak'                         : '',
        'voice_visible.google'                         : '',
        'voice_visible.powershell'                     : '',
        'voice_visible.tts'                            : '',
        'volume.eSpeak'                                : '',
        # 'volume.tts': '',
        # 'volume_visible.tts'
    }

    settings_wrapper = SettingsWrapper()

    @classmethod
    def load_setting(cls, service_key: ServiceID, persist: bool,
                     default_value: [int | float | str | bool | None],
                     const_value:  [int | float | str | bool]) -> Any | None:
        """
        loads setting into the current settings cache frame from settings.xml

        :param service_key: Identifies the setting to load
        :param persist: if True, then this setting is persisted in settings.xml
        :param default_value: A non-null value acts as a  default value for the setting
        :param const_value: A non-null value indicates that the setting is a constant
                            value of const_value.
        :return: Any value found for the setting
        """

        found: bool = True
        force_load: bool = False
        if service_key == ServiceKey.CURRENT_ENGINE_KEY:
            force_load = True
        if not force_load:
            found = False
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'Setting {service_key.setting_id} supported: {found} for '
                              f'{service_key.service_id} persist: {persist}')
        if not persist:
            return None
        setting_path: str = service_key.short_key
        if setting_path in cls.ignore:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'IGNORE {setting_path}')
            return None
        # A few values are constant (such as some engines can't play audio,
        # or adjust volume)
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
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'found key: {service_key} value: {value} const_value: '
                                   f'{const_value} '
                                   f'setting_type: {setting_type}')
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
                value = default_value
            except Exception as e:
                MY_LOGGER.exception(f'Can not set default for '
                                    f'{setting_path}')
        # if value and MY_LOGGER.isEnabledFor(DEBUG):
            #  MY_LOGGER.debug(f'Read {key} value: {value}')
        #  MY_LOGGER.debug(f'Read {key} value: {value}')
        SettingsManager.set_setting(service_key.short_key, value)

        return value
