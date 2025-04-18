# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys
import time

import xbmc
import xbmcgui

from backends.settings.service_types import ServiceKey
from common import *

from backends.settings.setting_properties import SettingProp
from common import utils
from common.constants import Constants
from common.logger import *
from common.messages import Messages
from common.settings import Settings
from windows.base import WindowHandlerBase, WindowReaderBase
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class ProgressNotice(xbmcgui.Window):

    def __init__(self, winID: int):
        self._logger = module_logger
        self.winID: int = winID
        xbmcgui.Window.__init__(self, winID)

        self.started = False
        self.finished = False
        self.seen = False
        self.valid = True
        self.title = None
        self.progress = None
        self.currentProgress = None
        self.last = 0

        if self._logger.isEnabledFor(DEBUG):
            self._logger.debug('BG Prog: Created')

    def ready(self):
        if self.started and self.title:
            return True
        self.started = True
        self.setTitle()
        if self._logger.isEnabledFor(DEBUG):
            self._logger.debug(f'BG Prog: Ready ({self.title})')
        return False

    def setTitle(self):
        if self.title:
            return
        tail = utils.tailXBMCLog()
        for t in reversed(tail):
            l = t.lower()
            if 'thread epgupdater start' in l:
                self.title = Messages.get_msg(Messages.IMPORTING_PVR_EPG)
                return
            elif 'thread pvrguiinfo start' in l:
                self.title = Messages.get_msg(Messages.LOADING_PVR_EPG)
                return

        if self.progress:
            self.title = Messages.get_msg(Messages.BACKGROUND_PROGRESS_STARTED)

    def visible(self):
        return xbmc.getCondVisibility('Window.IsVisible({0})'.format(self.winID))

    def updateProgress(self):
        try:
            control: xbmcgui.Control = self.getControl(32)
            control: xbmcgui.ControlSlider
            new_prog = int(control.getPercent())
            if new_prog == self.progress:
                return None
            if (self.progress and new_prog) or self.started:
                if self.ready():
                    if new_prog < self.progress and self.progress:
                        self.finish()
                        return None
            self.progress = new_prog
            self.currentProgress = f'{self.progress}%'
        except AbortException:
            reraise(*sys.exc_info())
        except:
            self._logger.error('BG Progress')

    def finish(self):
        if self.finished:
            return
        self.finished = True
        if self._logger.isEnabledFor(DEBUG):
            self._logger.debug(f'BG Prog: Finished - Seen: {self.seen}')

    def done(self):
        return self.finished and not self.valid

    def update(self):
        if self.finished:
            return
        if not self.visible():
            self.finish()
            return
        self.updateProgress()

    def getProgress(self):
        if not self.currentProgress:
            return None
        prog = self.currentProgress
        self.currentProgress = None
        return prog

    def getMessage(self):
        if not self.started or not self.valid:
            return
        if self.seen:
            if self.finished:
                self.valid = False
                return Messages.get_msg(Messages.BACKGROUND_PROGRESS_DONE)
            else:
                return self.getProgress()
        else:
            if self.finished:
                self.valid = False
                return None
            self.seen = True
            return self.title


class BackgroundProgress(WindowHandlerBase):
    ID = 'backgroundprogress'

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None,
                 windialog_state: WinDialogState = None) -> None:
        cls = type(self)
        super().__init__(win_id, service)
        cls._logger = module_logger

    def init(self):
        self._win = None
        self.updateFromSettings()
        return self

    def updateFromSettings(self):
        self.last = 0
        self.interval = Settings.getSetting(ServiceKey.BACKGROUND_PROGRESS_INTERVAL,
                                            5)
        self.playDuringMedia = Settings.getSetting(
                                        ServiceKey.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
                                        False)

    def _visible(self):
        return WindowHandlerBase.visible(self)

    def visible(self):
        visible = self._visible()
        if visible:
            if not Settings.getSetting(ServiceKey.SPEAK_BACKGROUND_PROGRESS,
                                       False):
                return False
        else:
            if self._win:
                return True

        return visible

    def win(self):
        if not self._win:
            if not self._visible():
                return
            self.updateFromSettings()
            self._win = ProgressNotice(self.winID)
        return self._win

    def shouldSpeak(self, isSpeaking):
        if not self.playDuringMedia and xbmc.getCondVisibility('Player.Playing'):
            return False
        now = time.time()
        if now - self.last < self.interval:
            return False
        if not isSpeaking:
            return now

    def getMonitoredText(self, isSpeaking=False):
        win = self.win()
        if not win:
            return None
        win.update()
        if win.done():
            self._win = None
        now = self.shouldSpeak(isSpeaking)
        if now:
            message = win.getMessage()
            if message:
                self.last = now
                return message
        return None


class BackgroundProgressReader(BackgroundProgress, WindowReaderBase):
    pass
