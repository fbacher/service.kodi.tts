# -*- coding: utf-8 -*-
import time

import xbmc

from . import guitables
from .base import WindowReaderBase


class ProgressDialogReader(WindowReaderBase):
    ID = 'progressdialog'

    def init(self):
        self.lastProgressPercentUnixtime = 0
        self.progressPercent = -1

    def getHeading(self):
        return xbmc.getInfoLabel('Control.GetLabel(1)') or ''

    def getWindowTexts(self):
        return guitables.convertTexts(self.winID, (
        '2', '3', '4', '9'))  # 1,2,3=Older Skins 9=Newer Skins

    def getWindowExtraTexts(self):
        return guitables.convertTexts(self.winID, (
        '2', '3', '4', '9'))  # 1,2,3=Older Skins 9=Newer Skins

    def getMonitoredText(self, isSpeaking=False):
        progress = xbmc.getInfoLabel('System.Progressbar')
        if not progress or progress == self.progressPercent:
            return None
        if isSpeaking is None:
            now = time.time()
            if now - self.lastProgressPercentUnixtime < 2:
                return None
            self.lastProgressPercentUnixtime = now
        elif isSpeaking:
            return
        self.progressPercent = progress
        return '%s%%' % progress
