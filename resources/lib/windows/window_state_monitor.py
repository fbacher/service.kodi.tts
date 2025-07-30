# coding=utf-8
from __future__ import annotations

import copy
import sys
import threading
from collections import namedtuple, OrderedDict

from common.constants import Constants
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from typing import (Callable, Dict, Final, ForwardRef, List,
                    OrderedDict as OrderedDict_type, Tuple)

import xbmc
import xbmcgui

from common import AbortException, reraise
from common.logger import *
from common.monitor import Monitor
from utils import util

MY_LOGGER = BasicLogger.get_logger(__name__)


class WinDialog(StrEnum):
    WINDOW = 'window'
    DIALOG = 'dialog'


WindowChanges = namedtuple(typename='WindowChanges',
                           field_names='focus_changed, focus_change')

ListenerInfo = namedtuple(typename='ListenerInfo',
                          field_names='listener, require_focus_change, '
                                      'window_id_filter, focus_id_filter')


class WindowMonitor(xbmcgui.Window):
    """

    """
    _logger: BasicLogger = None

    def __init__(self, existingWindowId: int = -1) -> None:
        super().__init__(existingWindowId=existingWindowId)

        self.window_id: int = existingWindowId
        self.start_focus: int = -1
        self.start_visible: bool = False
        self.focus_changed: bool = False
        self.current_focus: int = -1
        self.current_visible: bool = False
        return

    def getFocusId(self) -> int:
        focus_id: int
        focus_id = super().getFocusId()
        focus_id = abs(focus_id)
        self.current_focus = focus_id
        return focus_id

    def isVisible(self) -> bool:
        visible: bool = xbmc.getCondVisibility(f'Control.IsVisible('
                                               f'{self.current_focus})')
        self.current_visible = visible
        return visible

    def get_changed(self) -> WindowChanges:
        clz = WindowMonitor
        current_focus: int = -1

        focus_changed: bool = self.focus_changed
        if focus_changed:
            current_focus = self.current_focus
            # clz._logger.debug(f'focus_changed current_focus: {current_focus}')

        changes: WindowChanges = WindowChanges(focus_changed=focus_changed,
                                               focus_change=current_focus)
        self.start_focus = self.current_focus
        self.focus_changed = False
        return changes


class WinDialogState:
    # Change to attributes with WindowStateMonitor._window_state_lock

    """
    current_windialog: WinDialog = WinDialog.WINDOW
    current_window_id: int = -1
    current_dialog_id: int = -1
    current_window_instance: xbmcgui.Window | None = None
    current_window_focus_id: int = 0    # Dialogs appearing as windows can
                                        # have focus (groan).
    current_window_focus_visible: bool = False
    current_dialog_instance: xbmcgui.WindowDialog | None = None
    current_dialog_focus_id: int = 0  # Windows don't have focus
    current_dialog_focus_visible: bool = False
    """

    def __init__(self, windialog: WinDialog = WinDialog.WINDOW,
                 window_id: int = 0,
                 window_instance: WindowMonitor = None,
                 window_focus_id: int = 0,
                 is_control_visible: bool = False,
                 changed: int = 0) -> None:
        self._windialog: WinDialog = windialog
        self._window_id: int = window_id
        self._window_instance: WindowMonitor = window_instance
        self._window_focus_id: int = window_focus_id
        self._is_control_visible: bool = is_control_visible
        self._changed: int = changed
        self._revoice: bool = False  # User triggered revoicing current context

        # Detect some actions that don't necessarily change the focus.
        # For example, when using a SliderControl you use left/right up/down
        # to change the value, even though the focus does not change. This
        # needs to be detected since we don't normally do much when the focus
        # does not change.

        changes: WindowChanges | None = None
        # if self.window_instance is not None:
            # changes = self.window_instance.get_changed()
        # self._focus_changed_action: bool = False
        # self._clicked: bool = False
        # self._cursor_moved_right: bool = False
        # self._cursor_moved_left: bool = False
        # if changes is not None:
        #     self._focus_changed_action = changes.focus_changed
        #     self._clicked = changes.clicked
        #     self._cursor_moved_right = changes.cursor_right
        #     self._cursor_moved_left = changes.cursor_left

    def copy(self) -> ForwardRef('WinDialogState'):
        my_copy: ForwardRef('WinDialogState')
        my_copy = WinDialogState(window_id=self.window_id,
                                 window_instance=self.window_instance,
                                 window_focus_id=self.focus_id,
                                 is_control_visible=self.is_control_visible,
                                 changed=self.changed)
        return my_copy

    @property
    def changed(self) -> int:
        return self._changed

    def set_changed(self, changed: int) -> None:
        """
        Did not make a setter to make it more awkard to set. Only
        WindowStateMonitor should be doing that.

        :param changed:
        :return:
        """
        self._changed = changed

    @property
    def control_focus_changed(self) -> bool:
        if self.is_bad_window:
            return False
        return (self._changed & WindowStateMonitor.WINDOW_FOCUS_CHANGED) != 0

    @property
    def focus_changed(self) -> bool:
        """
        Reports when either window or control focus has changed.

        :return: True if control_fucus_changed or window_changed
        """
        if self.is_bad_window:
            return False
        return self.control_focus_changed or self.window_changed

    '''
    @property
    def value_changed(self) -> bool:
        return (self._changed & WindowStateMonitor.FOCUS_VALUE_CHANGED) != 0
    '''

    @property
    def potential_change(self) -> bool:
        """
        This is useful for detecting changes that don't show up directly.
        This helps detect if a window is worth examining for value changes that
        don't show up as focus changes.

        :return:
        """
        if self.is_bad_window:
            return False
        return self._changed == 0 and self._window_focus_id != 0

    @property
    def difficult_to_detect(self) -> bool:
        """
        Without a detected focus, window change nor anything with focus then
        there still be undetected changes in non-focusable controls (labels),
        but without hints, they will be difficut to find.

        :return:
        """
        if self.is_bad_window:
            return False
        return self._changed == 0 and self._window_focus_id == 0

    @property
    def window_changed(self) -> bool:
        if self.is_bad_window:
            return False
        return (self._changed & WindowStateMonitor.WINDOW_CHANGED) != 0

    @property
    def visibility_changed(self) -> bool:
        if self.is_bad_window:
            return False
        return (self._changed & WindowStateMonitor.CONTROL_VISIBILITY_CHANGED) != 0

    @property
    def windialog(self) -> WinDialog:
        return self._windialog

    @property
    def window_id(self) -> int:
        return self._window_id

    @property
    def window_instance(self) -> WindowMonitor:
        return self._window_instance

    @property
    def focus_id(self) -> int:
        return self._window_focus_id

    @property
    def is_control_visible(self) -> bool:
        if self.is_bad_window:
            return False
        return self._is_control_visible

    @property
    def revoice(self) -> bool:
        if self.is_bad_window:
            return False
        revoice_trigger: bool = self._revoice
        return revoice_trigger

    @property
    def is_bad_window(self):
        return self._changed == WindowStateMonitor.BAD_WINDOW


    @revoice.setter
    def revoice(self, value: bool) -> None:
        self._revoice = value
        self._changed |= WindowStateMonitor.REVOICE_CONTEXT
        self._changed |= WindowStateMonitor.WINDOW_FOCUS_CHANGED

    def __repr__(self) -> str:
        changed_str: str = f'\n changed: {self._changed} '
        windialog_str: str = f'\n windialog: {self._windialog} '
        window_id_str: str = f'\n window_id: {self.window_id} '
        focus_id_str: str = f'\n focus_id: {self.focus_id} '
        visible_str: str = f'\n visible: {self.is_control_visible} '
        #  focus_changed_action_str = f'\n focus_changed_action: {self._focus_changed_action} '
        dialog_changed_str: str = f'\n visibility_changed: {self.visibility_changed} '
        return (f'{changed_str}{windialog_str}{window_id_str}'
                f'{focus_id_str}{visible_str}'
                # f'{focus_changed_action_str}'
                f'{dialog_changed_str}')
    @property
    def succinct(self) -> str:
        msg: str = ''
        if self.is_bad_window:
            msg = f'{msg}BAD window '
        if self.focus_changed:
            msg = f'{msg}focus_chg: window: {self.window_id} focus: {self.focus_id} '
        if self.is_control_visible:
            msg = f'{msg} visible '
        if self.revoice:
            msg = f'{msg} revoice '
        if self.potential_change:
            msg = f'{msg} pot_change '
        return msg

    @property
    def verbose(self) -> str:
        msg: str = self.succinct
        if self.control_focus_changed:
            msg = f'{msg} ctrl_focus_chng '
        if self.difficult_to_detect:
            msg = f'{msg} difficult_detection '
        if self.window_changed:
            msg = f'{msg} window_chng '
        if self.visibility_changed:
            msg = f'{msg} visibility_chng '
        return msg


class WindowStateMonitor:

    _logger: BasicLogger = None
    _window_state_listener_lock: threading.RLock = None
    _window_state_lock: threading.RLock = None
    _window_state_listeners: OrderedDict_type[str, ListenerInfo]
    _window_state_listeners = OrderedDict()
    IDLE_POLLING_INTERVAL: float = 0.6
    POLLING_INTERVAL: Final[float] = 0.2
    NON_FOCUSED_POLLING_INTERVAL: Final[float] = 0.4
    current_polling_interval: float = POLLING_INTERVAL
    INVALID_DIALOG: Final[int] = 9999

    WINDOW_CHANGED: Final[int] = 0x01
    WINDOW_FOCUS_CHANGED: Final[int] = 0x02

    '''
    Can not detect slider value changes without polling.
    Cursor movement detected without changing control focus
    probably due to a control like the slider using the cursor movement
    to adjust value

    FOCUS_VALUE_CHANGED: Final[int] = 0x04
    '''
    BAD_WINDOW: Final[int] = 0x08
    # The focused control has had a visibility change since the last
    # call.
    CONTROL_VISIBILITY_CHANGED: Final[int] = 0x010
    REVOICE_CONTEXT: Final[int] = 0x20

    previous_window_state: WinDialogState = WinDialogState()
    previous_dialog_state: WinDialogState = WinDialogState()
    previous_chosen_state: WinDialogState = previous_window_state

    @classmethod
    def class_init(cls) -> None:
        """

        """
        if cls._logger is None:
            cls._logger: BasicLogger = MY_LOGGER
            cls._window_state_listener_lock = threading.RLock()
            cls._window_state_lock = threading.RLock()

            # Weird problems with recursion if we make requests to the super
            util.runInThread(cls.monitor_gui_state, args=[],
                             name='MonGuSt',
                             delay=0.0)

    @classmethod
    def revoice_current_focus(cls):
        with cls._window_state_lock:
            window_state: WinDialogState = cls.previous_chosen_state.copy()
            window_state.revoice = True
            # cls._logger.debug(f'Revoice')
            cls._notify_listeners(window_state)

    @classmethod
    def monitor_gui_state(cls) -> None:
        while not Monitor.wait_for_abort(timeout=cls.current_polling_interval):
            window_state: WinDialogState
            window_state = cls.check_win_dialog_state()
            if (KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO
                    and Constants.STOP_ON_PLAY):
                cls.current_polling_interval = cls.IDLE_POLLING_INTERVAL
            elif window_state.focus_changed:
                cls.current_polling_interval = cls.POLLING_INTERVAL
            else:
                cls.current_polling_interval = cls.NON_FOCUSED_POLLING_INTERVAL

            # notify_listeners does additional filtering
            if not window_state.is_bad_window:
                cls._notify_listeners(window_state)

    @classmethod
    def check_win_dialog_state(cls) -> WinDialogState:
        """
        Detects if current window, dialog or focus has changed.

        :return: 0 if current window, dialog and focus have not changed
                 Otherwise returns a binary value indicating what has
                 changed, based on ORing the following:
                    WINDOW_CHANGED: Final[int] = 0x01
                    WINDOW_FOCUS_CHANGED: Final[int] = 0x02
                    WINDOW_CHANGED: Final[int] = 0x04
                    WINDOW_FOCUS_CHANGED: Final[int] = 0x08
        """
        changed: int = 0
        window_changed: int
        new_window_state: WinDialogState
        new_window_state = cls.check_window_state()
        window_changed = new_window_state.changed
        dialog_changed: int
        new_dialog_state: WinDialogState
        new_dialog_state = cls.check_dialog_state()
        dialog_changed = new_dialog_state.changed
        cls.previous_dialog_state = new_dialog_state
        cls.previous_window_state = new_window_state

        # if either dialog or window is BAD (perhaps there is no current dialog)
        # then ignore the bad one and work on the good one.
        #
        window_state: WinDialogState = None
        if dialog_changed == 0 and window_changed == 0:
            window_state = new_dialog_state
            if (new_dialog_state.window_id !=
                    WindowStateMonitor.previous_chosen_state.window_id):
                window_state = new_window_state
            WindowStateMonitor.previous_chosen_state = window_state
            return window_state  # Both are marked the same

        # We can't be certain which window / dialog is visible. See is_visible.
        # if (not WinDialogState.current_dialog_focus_visible or
        #         not WinDialogState.current_window_focus_visible):
        #     return WindowStateMonitor

        if dialog_changed != WindowStateMonitor.BAD_WINDOW:
            # cls._logger.debug(f'Setting WINDOW_CHANGED and windialog to DIALOG')
            window_state = new_dialog_state
        elif window_changed != WindowStateMonitor.BAD_WINDOW:
            # cls._logger.debug(f'Setting WINDOW_CHANGED and windialog to WINDOW')
            window_state = new_window_state
        else:
            changed = WindowStateMonitor.BAD_WINDOW
            previous_window_id = WindowStateMonitor.previous_chosen_state.window_id
            window_state = new_window_state
            if previous_window_id == new_dialog_state.window_id:
                window_state = new_dialog_state
            new_dialog_state.set_changed(changed)

        #  cls._logger.debug(f'{window_state.verbose}')
        WindowStateMonitor.previous_chosen_state = window_state
        return window_state

    @classmethod
    def check_window_state(cls) -> WinDialogState:
        new_window_id: int = xbmcgui.getCurrentWindowId()
        changed: int = 0x00
        new_window_instance: WindowMonitor

        # It is possible to have both WINDOW_CHANGED and WINDOW_CHANGED.
        # But we only consider changes to one at a time. If there is any
        # DIALOG_FOCUS change, then ignore WINDOW_CHANGED.
        # TODO: What about INFO pop-ups. Are there any other cases?
        #       Perhaps look at window order.
        # TODO: Are there cases where dialog does not have focus, but should
        #       be read, like a window?

        new_windialog: WinDialog = WinDialog.WINDOW
        new_visible: bool = False
        other_changes: WindowChanges | None = None
        with cls._window_state_lock:
            # cls._logger.debug(f'win_id: {new_window_id}')
            if (new_window_id is None or
                    new_window_id == WindowStateMonitor.INVALID_DIALOG):
                return cls.handle_bad_window()

            if new_window_id != cls.previous_window_state.window_id:
                # new_window_instance = xbmcgui.Window(new_window_id)
                new_window_instance = WindowMonitor(new_window_id)
            else:
                new_window_instance = cls.previous_window_state.window_instance
            if new_window_instance is None:
                return cls.handle_bad_window()

            # This will get the changes for the previous window or a
            # brand new one

            # other_changes: WindowChanges = new_window_instance.get_changed()
            new_window_focus_id = abs(new_window_instance.getFocusId())
            new_visible = cls.is_visible(new_window_focus_id)
            # cls._logger.debug(f'new_window_focus_id: {new_window_focus_id}')
            # TODO: verify
            #
            if new_window_id != cls.previous_window_state.window_id:
                # cls._logger.debug(f'WINDOW_ID changed')
                changed |= WindowStateMonitor.WINDOW_CHANGED
            # The visibility of the focused item has changed:
            #  - The focused item has changed
            #  - The focused item has not changed but is_control_visible
            #    has changed
            if new_window_focus_id != 0:
                if new_window_focus_id != cls.previous_window_state.focus_id:
                    changed |= WindowStateMonitor.WINDOW_FOCUS_CHANGED
                    changed |= WindowStateMonitor.CONTROL_VISIBILITY_CHANGED
                    # cls._logger.debug(f'focus_changed. windialog is WINDOW')
                else:
                    if new_visible != cls.previous_window_state.is_control_visible:
                        changed |= WindowStateMonitor.CONTROL_VISIBILITY_CHANGED

            # Check for subtle changes: Are there cursor right/left changes
            # that didn't show up in focus changes because the control,
            # like a slider, used those to change the value, therefore
            # needing voicing?
            """
            if not (changed & (
                    WindowStateMonitor.WINDOW_CHANGED
                    | WindowStateMonitor.WINDOW_FOCUS_CHANGED)):
                if other_changes.focus_changed or other_changes.clicked:
                    changed |= WindowStateMonitor.FOCUS_VALUE_CHANGED
                    cls._logger.debug(f'clicked: {other_changes.clicked} '
                                      f'other_focus_changed: '
                                      f'{other_changes.focus_changed}')
                if other_changes.cursor_left or other_changes.cursor_right:
                    changed |= WindowStateMonitor.FOCUS_VALUE_CHANGED
                    cls._logger.debug(f'cursor_left: {other_changes.cursor_left} '
                                      f'cursor_right: {other_changes.cursor_right}')
            """
        new_state: WinDialogState
        new_state = WinDialogState(windialog=new_windialog,
                                   window_id=new_window_id,
                                   window_instance=new_window_instance,
                                   window_focus_id=new_window_focus_id,
                                   is_control_visible=new_visible,
                                   changed=changed)

        # cls._logger.debug(f'changed: {changed} '
        #                   f'window_id: {WinDialogState.current_window_id} '
        #                   f'focus: {WinDialogState.current_window_focus_id} ')
        return new_state

    @classmethod
    def handle_bad_window(cls) -> WinDialogState:
        # Something ain't right. Reset our state so that on the next call
        # it is just like going to a new dialog. Returning BAD_DATA will
        # tell monitor to omit informing listeners.

        bad_window_state: WinDialogState
        bad_window_state = WinDialogState(windialog=WinDialog.DIALOG,
                                          window_id=WindowStateMonitor.INVALID_DIALOG,
                                          window_instance=None,
                                          window_focus_id=0,
                                          is_control_visible=False,
                                          changed=WindowStateMonitor.BAD_WINDOW)

        return bad_window_state

    @classmethod
    def check_dialog_state(cls) -> WinDialogState:
        new_dialog_id: int | None = xbmcgui.getCurrentWindowDialogId()
        new_dialog_instance: WindowMonitor = None
        new_dialog_focus_id: int = 0
        changed: int = 0x00
        other_changes: WindowChanges | None = None

        # It is possible to have both WINDOW_CHANGED and WINDOW_CHANGED.
        # But we only consider changes to one at a time. If there is any
        # FOCUS change, then ignore WINDOW_CHANGED.
        # TODO: What about INFO pop-ups. Are there any other cases?
        #       Perhaps look at window order.
        # TODO: Are there cases where dialog does not have focus, but should
        #       be read, like a window?

        visible: bool = False
        with cls._window_state_lock:
            # cls._logger.debug(f'win_id: {new_dialog_id}')
            if (new_dialog_id is None
                    or new_dialog_id == WindowStateMonitor.INVALID_DIALOG):
                return cls.handle_bad_window()

            if new_dialog_id != cls.previous_dialog_state.window_id:
                new_dialog_instance = WindowMonitor(new_dialog_id)
            else:
                new_dialog_instance = cls.previous_dialog_state.window_instance
            if new_dialog_instance is None:
                return cls.handle_bad_window()

            # This will get the changes for the previous window or a
            # brand new one

            # other_changes: WindowChanges = new_dialog_instance.get_changed()
            new_dialog_focus_id: int = new_dialog_instance.getFocusId()
            new_visible = cls.is_visible(new_dialog_focus_id)
            # cls._logger.debug(f'new_dialog_focus_id: {new_dialog_focus_id}')

            # TODO: verify
            #
            if new_dialog_id != cls.previous_dialog_state.window_id:
                # cls._logger.debug(f'DIALOG_WINDOW changed')
                changed |= (WindowStateMonitor.WINDOW_CHANGED
                            | WindowStateMonitor.WINDOW_FOCUS_CHANGED)
            # The visibility of the focused item has changed:
            #  - The focused item has changed
            #  - The focused item has not changed but is_control_visible
            #    has changed
            if new_dialog_focus_id != 0:
                if new_dialog_focus_id != cls.previous_dialog_state.focus_id:
                    changed |= WindowStateMonitor.WINDOW_FOCUS_CHANGED
                    changed |= WindowStateMonitor.CONTROL_VISIBILITY_CHANGED
                else:
                    if new_visible != cls.previous_dialog_state.is_control_visible:
                        changed |= WindowStateMonitor.CONTROL_VISIBILITY_CHANGED

                    # cls._logger.debug(f'focus_changed. windialog is DIALOG')
                    cls.previous_dialog_state.current_windialog = WinDialog.DIALOG
        new_state: WinDialogState
        new_state = WinDialogState(windialog=WinDialog.DIALOG,
                                   window_id=new_dialog_id,
                                   window_instance=new_dialog_instance,
                                   window_focus_id=new_dialog_focus_id,
                                   is_control_visible=new_visible,
                                   changed=changed)
        return new_state

    @classmethod
    def register_window_state_listener(cls,
                                       listener: Callable[[WinDialogState], bool],
                                       name: str = None,
                                       require_focus_change: bool = True,
                                       window_id: int = -1,
                                       control_id: int = -1,
                                       insert_at_front: bool = False) -> None:
        """

        :param listener: Receives regular notifications about the current window
                state. The signature of the listener is:
                listener_name(changed: int, windialog_state: WinDialogState) -> bool
                changed requires a bitmask to examine. See WinDialogState for
                details.
        :param name:
        :param require_focus_change: Normally listeners are called only when
                          focus changes. This saves cpu time because most
                          changes occur only when focus changes. However,
                          some controls such as sliders don't change focus
                          as the user adjusts the slider.
        :param window_id: Only send event when the current window_id matches
                          -1 matches any window_id
        :param control_id: Only send event when the current control_id matches
                           -1 matches any control
        :param insert_at_front: Inserts this listener to front of list
        :return: True prevents any other listener from receiving a notification
                 of this event.

        Listeners are called in the order they are registered. Crude, but works
        okay. The first listeners are called in the reverse order that they
        are registered. The first listeners registered are for groups of windows
        One group for most windows that are scraped by the 'old scraper',
        another group that uses this new scraper. So any controls registering
        will get registered after that resulting in listeners being called
        in the order: control-specific listeners, new-scraper and finally
        the old scraper.
        """
        # cls._logger.debug(f'Registering {name}')
        with cls._window_state_listener_lock:
            if not Monitor.is_abort_requested():
                found: bool = False
                for registered_listener in cls._window_state_listeners:
                    registered_listener: ListenerInfo
                    reg_listener: Callable[[int, WinDialogState], bool]
                    if registered_listener[0] == listener:
                        found = True
                        break
                if not found:
                    listener_info: ListenerInfo
                    listener_info = ListenerInfo(listener,
                                                 require_focus_change=require_focus_change,
                                                 window_id_filter=window_id,
                                                 focus_id_filter=control_id)
                    cls._window_state_listeners[name] = listener_info
                    if insert_at_front:
                        cls._window_state_listeners.move_to_end(name, last=False)

    @classmethod
    def unregister_window_state_listener(cls, name: str = '',
                                         listener: Callable[[WinDialogState],
                                                            bool] = None) -> None:
        """
        :param name: Same name as used for creation
        :param listener:
        :return:
        """
        clz = WindowStateMonitor
        if listener is None:
            raise ValueError('Missing Listener')

        with cls._window_state_listener_lock:
            try:
                if name in cls._window_state_listeners.keys():
                    del cls._window_state_listeners[name]
                else:
                    clz._logger.debug(f'Could not delete listener '
                                      f'name: {name}')
            except ValueError:
                pass

    @classmethod
    def _notify_listeners(cls, window_state: WinDialogState) -> None:
        """
        :param window_state: contains detailed change state as well as useful
            properties to access the state.
        :return:
        """
        # cls._logger.debug(f'notify_listeners dialog_window: '
        #                   f'{WinDialogState.current_window_id} '
        #                   f'{WinDialogState.current_dialog_id} ')
        with cls._window_state_listener_lock:
            listeners = copy.copy(cls._window_state_listeners)
            if Monitor.is_abort_requested():
                cls._window_state_listeners.clear()

        for listener_name, listener_info in listeners.items():
            listener_info: ListenerInfo
            listener_name: str
            listener: Callable[[WinDialogState], bool]
            listener = listener_info.listener
            window_id_filter: int = listener_info.window_id_filter
            focus_id_filter: int = listener_info.focus_id_filter
            try:
                """
                cls._logger.debug(f'wind_id filter: {window_id_filter} '
                                  f'window_id: {window_state.window_id} '
                                  f'focus_id filter {focus_id_filter} '
                                  f'focus_id: {window_state.focus_id}')
                """
                if (listener_info.require_focus_change and
                        window_state.changed == 0):
                    continue
                if window_id_filter != -1 and window_id_filter != window_state.window_id:
                    continue
                if focus_id_filter != -1 and focus_id_filter != window_state.focus_id:
                    continue
                handled: bool = listener(window_state)
                #  cls._logger.debug(f'handled: {handled}')
                if handled:
                    break
            except AbortException as e:
                reraise(*sys.exc_info())
            except Exception as e:
                cls._logger.exception('')
                break

            # if cls._logger.isEnabledFor(DEBUG_V):
            #     cls._logger.debug_v(
            #             f'Notifying listener: {listener_name}')
            # thread = threading.Thread(
            #         target=listener, name='Monitor.inform_' + listener_name)
            # thread.start()

    @classmethod
    def get_listener_name(cls,
                          listener: Callable[[int, WinDialogState], bool]) -> str:
        listener_name: str = ''
        if hasattr(listener, '__name__'):
            try:
                listener_name = listener.__name__
            except AbortException:
                reraise(*sys.exc_info())
            except:
                pass
        elif hasattr(listener, 'name'):
            try:
                listener_name = listener.name
            except AbortException:
                reraise(*sys.exc_info())
            except:
                pass

        return listener_name

    @classmethod
    def get_window(cls, dialog_id: int = None) -> xbmcgui.WindowDialog | xbmcgui.Window:
        """
          Creates a Dialog instance for the dialog identified by the
          given id, or cls.current_dialog_id
          :param dialog_id  ID used to create Dialog instance. If
          ommitted, then cls.current_dialog_id is used
        """
        dialog_instance: xbmcgui.Window
        if dialog_id is None or dialog_id == 9999:
            _, dialog_state = cls.check_dialog_state()  # Same as current dialog

            dialog_id = dialog_state.window_id
            dialog_instance = dialog_state.window_instance
        # cls._logger.debug(f'dialog_id: {dialog_id}')
        elif dialog_id == cls.previous_dialog_state.window_id:
            dialog_instance = cls.previous_dialog_state.window_instance
        elif dialog_id == cls.previous_window_state.window_id:
            dialog_instance = cls.previous_window_state.window_instance
        else:
            #  dialog_instance = xbmcgui.WindowDialog(dialog_id)
            dialog_instance = xbmcgui.Window(dialog_id)

        return dialog_instance

    @classmethod
    def is_visible(cls, control_id: int, window_id: int = -1) -> bool:
        """
        Kodi doesn't provide access to every control type. For example, you
        can't instantiate a GroupList control. Therefore, you can't directly
        tell if it is visible or not. (groan). The alternative is to use
        condition visibility:

             xbmc.getCondVisibility(f'Control.IsVisible({self.control_id})')

        The problem with this is that you can NOT specify the window id.
        But since we are only interested in the currently focused window, we
        should be okay.

        :param control_id:
        :param window_id:
        :return:
        """
        # cls._logger.debug(f'control_id: {control_id} window_id: {window_id}')
        if (window_id != -1 and
                cls.previous_dialog_state.window_id != window_id and
                cls.previous_window_state.window_id != window_id):
            return False

        return xbmc.getCondVisibility(f'Control.IsVisible({control_id})')
        '''
        else:
            control: xbmcgui.Control
            try:
                control = WinDialogState.controls_in_window.get(control_id)
                if control is not None:
                    return control.isVisible()
            except Exception as e:
                cls._logger.exception(f'window_id: {window_id} control_id: {control_id}')

            try:
                if window_id != -1:
                    if window_id == WinDialogState.current_dialog_id:
                        control = WinDialogState.current_dialog_instance.getControl(
                            control_id)
                    elif window_id == WinDialogState.current_window_id:
                        control = WinDialogState.current_window_instance.getControl(
                            control_id)
                    else:
                        control = WinDialogState.current_window_instance.getControl(
                            control_id)
                else:
                    control = WinDialogState.current_window_instance.getControl(
                    control_id)

                WinDialogState.controls_in_window[control_id] = control

                # if window_id == 13000:
                #     control_id = 1106
                # cls._logger.debug(f'window_id: {window_id} control_id: {control_id}')
                # cls._logger.debug(f'control: {control}')
                # cls._logger.debug(f'visible: {control.isVisible()}')
            except Exception as e:
                cls._logger.exception(f'windowid: {window_id} controlid: {control_id}')
                return False
            return control.isVisible()
            '''


WindowStateMonitor.class_init()
