# -*- coding: utf-8 -*-

import time

import xbmc
import xbmcgui

from backends.settings.setting_properties import SettingsProperties
from common import utils
from common.constants import Constants
from common.logger import *
from common.messages import Messages
from common.settings import Settings
from windows.base import WindowHandlerBase, WindowReaderBase

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)
else:
    module_logger = BasicLogger.get_module_logger()


class ProgressNotice(xbmcgui.Window):

    def __init__(self, winID: str):
        self._logger = module_logger.getChild(
                self.__class__.__name__)  # type: BasicLogger
        self.winID = winID
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
            self._logger.debug('BG Prog: Ready ({0})'.format(self.title))
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
            new_prog = int(self.getControl(32).getPercent())
            if new_prog == self.progress:
                return None
            if (self.progress and new_prog) or self.started:
                if self.ready():
                    if new_prog < self.progress and self.progress:
                        self.finish()
                        return None
            self.progress = new_prog
            self.currentProgress = '{0}%'.format(self.progress)
        except:
            self._logger.error('BG Progress')

    def finish(self):
        if self.finished:
            return
        self.finished = True
        if self._logger.isEnabledFor(DEBUG):
            self._logger.debug('BG Prog: Finished - Seen: {0}'.format(self.seen))

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

    def init(self):
        self._win = None
        self.updateFromSettings()
        return self

    def updateFromSettings(self):
        self.last = 0
        self.interval = Settings.getSetting(
            SettingsProperties.BACKGROUND_PROGRESS_INTERVAL,
            SettingsProperties.TTS_SERVICE, 5)
        self.playDuringMedia = Settings.getSetting(
                SettingsProperties.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
                SettingsProperties.TTS_SERVICE, False)

    def _visible(self):
        return WindowHandlerBase.visible(self)

    def visible(self):
        visible = self._visible()
        if visible:
            if not Settings.getSetting(SettingsProperties.SPEAK_BACKGROUND_PROGRESS,
                                       SettingsProperties.TTS_SERVICE,
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
