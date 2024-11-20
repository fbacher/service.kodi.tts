# coding=utf-8
from __future__ import annotations

"""
     Supervises the voicing of a Kodi Window.  Windows are read-only, while
     WindowDialogs also provide for user input.

     VoiceWindow provides the code to determine how to voice a Window based
     on what it learns from Windows class, which is in charge of providing
     instrospection of the Kodi Window.s

     Typical operations on a Window for voicing:

     On focus of a window:
         Voice the title of the Window.
         Voice labels/headings of each focused Control until the inner-most
         control has been voiced. The Control classes will handle this job,
         as well as other voicing of Controls.

     """
import xbmc
import xbmcgui

from common.logger import BasicLogger
from windows import guitables
from windows.guitables import window_map

module_logger = BasicLogger.get_logger(__name__)


class VoiceWindow:
    """
        A new instance of VoiceWindow is created when the focus has changed to
        a different Window. The old Window instance (and state) is lost.

        When a Window is first voiced, the Window name is voiced. Next,
        chain of focused controls are voiced by the VoiceControl classes.
        The majority of work is in the VoiceControl classes.
    """

    def __init__(self, win_dialog_id: int, addon_id: str = None):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger

        self.win_dialog_id: int = win_dialog_id
        self.addon_id: str | None = addon_id
        self.window: xbmcgui.Window = None
