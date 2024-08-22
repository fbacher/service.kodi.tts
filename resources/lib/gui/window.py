# coding=utf-8
"""
  Represents a  Kodi Window.  A Window can have its own Properties as well
  as controls. Windows are read-only, while WindowDialogs also provide
  for user input.

  This class provides methods/functions to introspect a given window to be
  able to voice its contents. Controls are handled by other classes.

  While this class provides the introspection, VoiceWindow provides the
  code to determine how to voice a Window based on what it learns from
  here.

  Typical operations on a Window for voicing:

  On focus of a window:
      Voice the title of the Window.
      Voice labels/headings of each focused Control until the inner-most
      control has been voiced. The Control classes will handle this job,
      as well as other voicing of Controls.

  """

from pathlib import Path
from typing import Tuple

import xbmc
import xbmcgui

from common.logger import BasicLogger, DEBUG_VERBOSE
from gui.base_tags import WindowType
from windows import guitables
from windows.guitables import window_map
from windows.window_state_monitor import WinDialog, WinDialogState, WindowStateMonitor
from windows.windowparser import WindowParser

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class Window:
    """
    The introspection is based upon information gathered by several sources:
    First, the active skin's .xml files provide the primary information.
    WindowParser processes the .xml files, filters out items which are not
    useful for voicing (colors, images, fonts, etc.) and expands all includes.

    Additional information comes from Kodi xmb, xbmcgui as well as InfoLabels,
    Boolean conditions, etc.

    """

    _logger: BasicLogger = None
    _active_win_dialog_id: int | None = None

    def __init__(self, win_dialog_id: int, addon_id: str = None):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)

        self.stop: bool = False
        self.win_dialog_id: int = win_dialog_id
        self.addon_id: str | None = addon_id
        self.xml_path: Path | None = None
        self.parsed_xml: WindowParser | None = None
        self.window_type: WindowType = WindowType.UNKNOWN

    def kill_window(self) -> None:
        self.stop = True

    def get_win_dialog_id(self) -> int:
        return self.win_dialog_id

    def get_addon_id(self) -> str:
        return self.addon_id

    def get_property(self, property_id: str) -> str:
        """
        Returns a window property as a string, similar to an infolabel.
        """
        # win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        #  win: xbmcgui.Window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        win: xbmcgui.Window = WindowStateMonitor.previous_chosen_state.window_instance
        property_value: str = win.getProperty(property_id)
        return property_value

    @staticmethod
    def has_focus(win_dialog_id: int | str) -> bool:
        focused: bool = xbmc.getCondVisibility(f'[Window.Is({win_dialog_id})]')
        return focused

    @staticmethod
    def is_active(win_dialog_id: int | str) -> bool:
        active: bool = xbmc.getCondVisibility(f'[Window.IsActive({win_dialog_id})]')
        return active

    @staticmethod
    def get_current_win_dialog_id() -> Tuple[int, WindowType]:
        win_dialog_id: int = Window.get_current_active_win_dialog_id()
        window_type: WindowType = WindowType.WINDOW
        if win_dialog_id == 0:
            win_dialog_id = Window.get_current_active_dialog_id()
            window_type = WindowType.DIALOG
        return win_dialog_id, window_type

    @staticmethod
    def get_current_active_win_dialog_id() -> int:
        """
        Returns the id for the current 'active' window as an integer.

        :return: The currently active window Id
        """
        return WindowStateMonitor.previous_chosen_state.window_id

    @staticmethod
    def get_current_active_dialog_id() -> int:
        """
        Returns the id for the current 'active' dialog as an integer.

        :return: The currently active dialog Id
        """
        return WindowStateMonitor.previous_chosen_state.window_id

    @staticmethod
    def is_visible(win_dialog_id: int | str) -> bool:
        visible: bool = Window.is_true(f'[Window.IsVisible({win_dialog_id})]')
        return visible

    @staticmethod
    def get_current_window_name() -> str:
        window_name: str = Window.get_info_label('System.CurrentWindow')
        return window_name

    @staticmethod
    def get_window_name_for_id(win_dialog_id: int) -> str:
        name: str | None = None
        window_name: str | None = None
        if win_dialog_id in window_map:
            name_id: str | int = guitables.window_map[win_dialog_id].msg_id
            if isinstance(name_id, int):
                name = xbmc.getLocalizedString(name_id)
                window_name: str = window_map[win_dialog_id].window_name
            if Window._logger.isEnabledFor(DEBUG_VERBOSE):
                Window._logger.debug(f'winID: {win_dialog_id} name_id: {name_id} window '
                                     f"name: {name} currentWindow: "
                                     f"{xbmc.getInfoLabel('System.CurrentWindow')}")
            if window_name is None or len(window_name) == 0:
                window_name = name
        elif win_dialog_id > 12999:
            window_name = guitables.getWindowAddonName(win_dialog_id)
            Window._logger.debug(f'from WindowAddonName window_name: {window_name}')
        return window_name

    @staticmethod
    def get_info_label(query: str) -> str:
        """
        Window([window]).Property(key)
        :param query:
        :return:

        ListItems, Windows, Containers can have properties, including user defined ones.
        Note InfoLabels include Propery queries. This class only handles Window
        properties

        Window([window]).Property(key)
        """
        return xbmc.getInfoLabel(query)

    @staticmethod
    def is_true(query: str) -> bool:
        """
        dispite the method name, it basically runs any boolean test.
          List of boolean conditions: https://kodi.wiki/view/List_of_boolean_conditions
        You can combine two (or more) of the above settings by
        using ``+`` as an AND operator, ``|`` as an OR operator, ``!``
        as a NOT operator, and ``[`` and ``]`` to bracket expressions.

        Example::

        visible = xbmc.getCondVisibility('[Control.IsVisible(41) + !Control.IsVisible(
        12)]')
        """
        return xbmc.getCondVisibility(query)

    def window_state(self, changed: int) -> None:
        if changed & WindowStateMonitor.WINDOW_CHANGED:
            self.kill_window()
