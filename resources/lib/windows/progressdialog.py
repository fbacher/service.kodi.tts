# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import time

import xbmc

from common import *
from common.logger import BasicLogger
from common.phrases import PhraseList

from . import guitables
from .base import WindowReaderBase
from .window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class ProgressDialogReader(WindowReaderBase):
    ID = 'progressdialog'

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None,
                 windialog_state: WinDialogState = None) -> None:
        cls = type(self)
        super().__init__(win_id, service, windialog_state)
        self.last_progress_percent_unix_time: int = 0
        self.progress_percent: int = -1

    def init(self):
        self.last_progress_percent_unix_time = 0
        self.progress_percent = -1

    def getHeading(self, phrases: PhraseList) -> bool:
        text: str | None = xbmc.getInfoLabel('Control.GetLabel(1)')
        if text is None:
            return False
        phrases.add_text(texts=text)
        return True

    def getWindowTexts(self, phrases: PhraseList) -> bool:
        return guitables.convertTexts(self.winID, (
            '2', '3', '4', '9'), phrases)  # 1,2,3=Older Skins 9=Newer Skins

    def getWindowExtraTexts(self, phrases: PhraseList) -> bool:
        return guitables.convertTexts(self.winID, (
            '2', '3', '4', '9'), phrases)  # 1,2,3=Older Skins 9=Newer Skins

    def getMonitoredText(self, isSpeaking=False) -> str | None:
        progress = xbmc.getInfoLabel('System.Progressbar')
        if not progress or progress == self.progress_percent:
            return None
        if isSpeaking is None:
            now = time.time()
            if now - self.last_progress_percent_unix_time < 2:
                return None
            self.last_progress_percent_unix_time = now
        elif isSpeaking:
            return None
        self.progress_percent = progress
        return f'{progress}%'
