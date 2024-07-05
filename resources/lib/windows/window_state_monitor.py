# coding=utf-8
import copy
import sys
import threading
from enum import StrEnum
from typing import Callable, Dict, Final

import xbmc
import xbmcgui

from common import AbortException, reraise
from common.logger import BasicLogger
from common.monitor import Monitor
from gui import ParseError
from utils import util

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class WinDialog(StrEnum):
    WINDOW = 'window'
    DIALOG = 'dialog'


class WinDialogState:
    # Change to attributes with WindowStateMonitor._window_state_lock

    current_windialog: WinDialog = WinDialog.WINDOW
    current_window_id: int = -1
    current_dialog_id: int = -1
    current_window_instance: xbmcgui.Window | None = None
    controls_in_window: Dict[int, xbmcgui.Control] = {}
    current_window_focus_id: int = 0    # Dialogs appearing as windows can
                                        # have focus (groan).
    current_dialog_instance: xbmcgui.WindowDialog | None = None
    current_dialog_focus_id: int = 0  # Windows don't have focus


class WindowStateMonitor:

    _logger: BasicLogger = None
    _window_state_listener_lock: threading.RLock = None
    _window_state_lock: threading.RLock = None
    _window_state_listeners: Dict[str, Callable[[int], bool]] = {}
    POLLING_INTERVAL: Final[float] = 0.2
    INVALID_DIALOG: Final[int] = 9999
    WINDOW_CHANGED: Final[int] = 0x01
    WINDOW_FOCUS_CHANGED: Final[int] = 0x02
    DIALOG_CHANGED: Final[int] = 0x04
    DIALOG_FOCUS_CHANGED: Final[int] = 0x08
    BAD_WINDOW: Final[int] = 0xF0
    BAD_DIALOG: Final[int] = 0xF1


    @classmethod
    def class_init(cls) -> None:
        """

        """
        if cls._logger is None:
            cls._logger: BasicLogger = module_logger.getChild(cls.__class__.__name__)
            cls._window_state_listener_lock = threading.RLock()
            cls._window_state_lock = threading.RLock()

            # Weird problems with recursion if we make requests to the super
            util.runInThread(cls.monitor_gui_state, args=[],
                             name='monitor_gui_state',
                             delay=0.0)

    @classmethod
    def monitor_gui_state(cls) -> None:
        while not Monitor.wait_for_abort(timeout=cls.POLLING_INTERVAL):
            changed = cls.check_win_dialog_state()
            if changed not in (WindowStateMonitor.BAD_DIALOG,
                               WindowStateMonitor.BAD_WINDOW):
                cls._notify_listeners(changed)

    @classmethod
    def check_win_dialog_state(cls) -> int:
        """
        Detects if current window, dialog or focus has changed.

        :return: 0 if current window, dialog and focus have not changed
                 Otherwise returns a binary value indicating what has
                 changed, based on ORing the following:
                    WINDOW_CHANGED: Final[int] = 0x01
                    WINDOW_FOCUS_CHANGED: Final[int] = 0x02
                    DIALOG_CHANGED: Final[int] = 0x04
                    DIALOG_FOCUS_CHANGED: Final[int] = 0x08
        """
        changed: int = 0
        window_changed: int = cls.check_window_state()
        dialog_changed: int = cls.check_dialog_state()

        # if either dialog or window is BAD (perhaps there is no current dialog)
        # then ignore the bad one and work on the good one.
        #
        # But if BOTH bad, then ignore both.

        if dialog_changed == 0 and window_changed == 0:
            return 0

        if dialog_changed != WindowStateMonitor.BAD_DIALOG:
            # cls._logger.debug(f'Setting DIALOG_CHANGED and windialog to DIALOG')
            changed = dialog_changed
            WindowStateMonitor.current_windialog = WinDialog.DIALOG
        elif window_changed != WindowStateMonitor.BAD_WINDOW:
            # cls._logger.debug(f'Setting WINDOW_CHANGED and windialog to WINDOW')
            changed = window_changed
            WindowStateMonitor.current_windialog = WinDialog.WINDOW
        else:
            changed = WindowStateMonitor.BAD_WINDOW  # Either BAD state will do.
        return changed
        """
        if changed != 0:
            cls._logger.debug(f'final dialog_id: {WinDialogState.current_dialog_id} '
                              f'inst: {WinDialogState.current_dialog_instance}')
            cls._logger.debug(f'      window_id: {WinDialogState.current_window_id}')
            cls._logger.debug(f'      dialog_focus_id: '
                              f'{WinDialogState.current_dialog_focus_id}')
            cls._logger.debug(f'      window_focus_id: '
                              f'{WinDialogState.current_window_focus_id}')
            cls._logger.debug(f'changed: {changed} Win_Dialog: '
                              f'{WinDialogState.current_windialog}')
        """

    @classmethod
    def check_window_state(cls) -> int:
        new_window_id: int = xbmcgui.getCurrentWindowId()
        new_window_instance: xbmcgui.Window = None  # WindowDialog = None
        new_window_focus_id: int = 0
        changed: int = 0x00

        # It is possible to have both WINDOW_CHANGED and DIALOG_CHANGED.
        # But we only consider changes to one at a time. If there is any
        # DIALOG_FOCUS change, then ignore WINDOW_CHANGED.
        # TODO: What about INFO pop-ups. Are there any other cases?
        #       Perhaps look at window order.
        # TODO: Are there cases where dialog does not have focus, but should
        #       be read, like a window?

        with cls._window_state_lock:
            # cls._logger.debug(f'win_id: {new_window_id}')
            if (new_window_id is None or
                    new_window_id == WindowStateMonitor.INVALID_DIALOG):
                return cls.handle_bad_window()

            if new_window_id != WinDialogState.current_window_id:
                new_window_instance = xbmcgui.Window(new_window_id)
            else:
                new_window_instance = WinDialogState.current_window_instance
            if new_window_instance is None:
                return cls.handle_bad_window()

            new_window_focus_id: int = abs(new_window_instance.getFocusId())
            # cls._logger.debug(f'new_window_focus_id: {new_window_focus_id}')
            # TODO: verify
            #
            if new_window_id != WinDialogState.current_window_id:
                # cls._logger.debug(f'WINDOW_ID changed')
                changed |= (WindowStateMonitor.WINDOW_CHANGED
                            | WindowStateMonitor.WINDOW_FOCUS_CHANGED)
            if (new_window_focus_id != WinDialogState.current_window_focus_id
                    and new_window_focus_id != 0):
                changed |= WindowStateMonitor.WINDOW_FOCUS_CHANGED
                # cls._logger.debug(f'focus_changed. windialog is WINDOW')
                WinDialogState.current_windialog = WinDialog.WINDOW

        WinDialogState.current_window_instance = new_window_instance
        WinDialogState.current_window_focus_id = new_window_focus_id
        WinDialogState.current_window_id = new_window_id

        # cls._logger.debug(f'changed: {changed} '
        #                   f'window_id: {WinDialogState.current_window_id} '
        #                   f'focus: {WinDialogState.current_window_focus_id} ')
        return changed

    @classmethod
    def handle_bad_window(cls) -> int:
        # Something ain't right. Reset our state so that on the next call
        # it is just like going to a new window. Returning BAD_DATA will
        # tell monitor to omit informing listeners.

        WinDialogState.current_window_instance = None
        WinDialogState.current_window_focus_id = 0
        WinDialogState.current_window_id = WindowStateMonitor.INVALID_DIALOG
        changed = WindowStateMonitor.BAD_WINDOW
        return changed

    @classmethod
    def handle_bad_dialog(cls) -> int:
        # Something ain't right. Reset our state so that on the next call
        # it is just like going to a new dialog. Returning BAD_DATA will
        # tell monitor to omit informing listeners.

        WinDialogState.current_dialog_instance = None
        WinDialogState.current_dialog_focus_id = 0
        WinDialogState.current_dialog_id = WindowStateMonitor.INVALID_DIALOG
        changed = WindowStateMonitor.BAD_DIALOG
        return changed

    @classmethod
    def check_dialog_state(cls) -> int:
        new_dialog_id: int | None = xbmcgui.getCurrentWindowDialogId()
        new_dialog_instance: xbmcgui.Window = None  # WindowDialog = None
        new_dialog_focus_id: int = 0
        changed: int = 0x00

        # It is possible to have both WINDOW_CHANGED and DIALOG_CHANGED.
        # But we only consider changes to one at a time. If there is any
        # FOCUS change, then ignore WINDOW_CHANGED.
        # TODO: What about INFO pop-ups. Are there any other cases?
        #       Perhaps look at window order.
        # TODO: Are there cases where dialog does not have focus, but should
        #       be read, like a window?

        with cls._window_state_lock:
            # cls._logger.debug(f'win_id: {new_dialog_id}')
            if (new_dialog_id is None
                    or new_dialog_id == WindowStateMonitor.INVALID_DIALOG):
                return cls.handle_bad_dialog()

            if new_dialog_id != WinDialogState.current_dialog_id:
                new_dialog_instance = xbmcgui.Window(new_dialog_id)
            else:
                new_dialog_instance = WinDialogState.current_dialog_instance
            if new_dialog_instance is None:
                return cls.handle_bad_dialog()

            new_dialog_focus_id: int = abs(new_dialog_instance.getFocusId())
            # cls._logger.debug(f'new_dialog_focus_id: {new_dialog_focus_id}')

            # TODO: verify
            #
            if new_dialog_id != WinDialogState.current_dialog_id:
                # cls._logger.debug(f'DIALOG_WINDOW changed')
                changed |= (WindowStateMonitor.DIALOG_CHANGED
                            | WindowStateMonitor.DIALOG_FOCUS_CHANGED)
            if (new_dialog_focus_id != WinDialogState.current_dialog_focus_id
                    and new_dialog_focus_id != 0):
                changed |= WindowStateMonitor.DIALOG_FOCUS_CHANGED
                # cls._logger.debug(f'focus_changed. windialog is DIALOG')
                WinDialogState.current_windialog = WinDialog.DIALOG

        WinDialogState.current_dialog_instance = new_dialog_instance
        WinDialogState.current_dialog_focus_id = new_dialog_focus_id
        WinDialogState.current_dialog_id = new_dialog_id

        # cls._logger.debug(f'changed: {changed} '
        #                   f'dialog_id: {WinDialogState.current_dialog_id} '
        #                   f'focus: {WinDialogState.current_dialog_focus_id} ')
        return changed

    @classmethod
    def register_window_state_listener(cls,
                                       listener: Callable[[int], bool],
                                       name: str = None) -> None:
        """

        :param listener:
        :param name:
        :return:
        """
        # cls._logger.debug(f'Registering {name}')
        with cls._window_state_listener_lock:
            if not (Monitor.is_abort_requested()
                    or listener in cls._window_state_listeners):

                cls._window_state_listeners[name] = listener

    @classmethod
    def unregister_window_state_listener(cls,
                                         listener: Callable[[int], bool]) -> None:
        """

        :param listener:
        :return:
        """
        with cls._window_state_listener_lock:
            try:
                name: str = cls.get_listener_name(listener)
                if listener in cls._window_state_listeners:
                    del cls._window_state_listeners[name]
            except ValueError:
                pass

    @classmethod
    def _notify_listeners(cls, changed: int) -> None:
        """
        :param changed:
        :return:
        """
        # cls._logger.debug(f'notify_listeners dialog_window: '
        #                   f'{WinDialogState.current_window_id} '
        #                   f'{WinDialogState.current_dialog_id} ')
        with cls._window_state_listener_lock:
            listeners = copy.copy(cls._window_state_listeners)
            if Monitor.is_abort_requested():
                cls._window_state_listeners.clear()

        for listener_name, listener in listeners.items():
            listener_name: str
            listener: Callable[[int], bool]
            try:
                handled: bool = listener(changed)
                # cls._logger.debug(f'handled: {handled}')
                if handled:
                    break
            except AbortException as e:
                reraise(*sys.exc_info())
            except Exception as e:
                cls._logger.exception('')
                break

            # if cls._logger.isEnabledFor(DEBUG_VERBOSE):
            #     cls._logger.debug_verbose(
            #             f'Notifying listener: {listener_name}')
            # thread = threading.Thread(
            #         target=listener, name='Monitor.inform_' + listener_name)
            # thread.start()

    @classmethod
    def get_listener_name(cls,
                          listener: Callable[[int], bool]) -> str:
        listener_name: str = 'unknown'
        if hasattr(listener, '__name__'):
            try:
                listener_name = listener.__name__
            except:
                pass
        elif hasattr(listener, 'name'):
            try:
                listener_name = listener.name
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
        dialog_instance: xbmcgui.Window  #  Dialog
        if dialog_id is None or dialog_id == 9999:
            cls.check_dialog_state()
            dialog_id = WinDialogState.current_dialog_id
        # cls._logger.debug(f'dialog_id: {dialog_id}')
        if dialog_id == WinDialogState.current_dialog_id:
            dialog_instance = WinDialogState.current_dialog_instance
        elif dialog_id == WinDialogState.current_window_id:
            dialog_instance = WinDialogState.current_window_instance
        else:
            #  dialog_instance = xbmcgui.WindowDialog(dialog_id)
            dialog_instance = xbmcgui.Window(dialog_id)

        return dialog_instance

    @classmethod
    def is_visible(cls, control_id: int, window_id: int = -1) -> bool:
        # cls._logger.debug(f'control_id: {control_id} window_id: {window_id}')
        if (window_id != -1 and
           WinDialogState.current_dialog_id != window_id and
           WinDialogState.current_window_id != window_id):
            return False
        else:
            control: xbmcgui.Control
            try:
                control = WinDialogState.controls_in_window.get(control_id)
                if control is not None:
                    return control.isVisible()
            except Exception as e:
                cls._logger.exception('')

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
                    control = WinDialogState.current_window_instance.getControl(control_id)

                WinDialogState.controls_in_window[control_id] = control

                # if window_id == 13000:
                #     control_id = 1106
                # cls._logger.debug(f'window_id: {window_id} control_id: {control_id}')
                # cls._logger.debug(f'control: {control}')
                # cls._logger.debug(f'visible: {control.isVisible()}')
            except Exception as e:
                cls._logger.exception('')
                return False
            return control.isVisible()


WindowStateMonitor.class_init()
