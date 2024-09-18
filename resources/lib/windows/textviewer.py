# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import hashlib
import re
import time

import xbmc

from common import *
from common.logger import BasicLogger
from common.phrases import PhraseList

from .base import WindowReaderBase
module_logger = BasicLogger.get_logger(__name__)


class TextViewerReader(WindowReaderBase):
    ID = 'textviewer'

    def __init__(self) -> None:
        # super.__init__()
        self.start = time.time()
        self._last_md5sum: bytes = None
        self.doubleChecked: bool = False

    def init(self) -> None:
        self.start = time.time()
        self._last_md5sum: bytes = None
        self.doubleChecked: bool = False

    def last(self, new):
        new_text_thumbprint: str = ''.join(new)
        if len(new_text_thumbprint) == 0:
            return

        md5sum = new and hashlib.md5(new_text_thumbprint).digest() or None
        if md5sum == self._last_md5sum:
            return True
        self._last_md5sum = md5sum

    def getViewerTexts(self) -> List[str]:
        text = xbmc.getInfoLabel('Control.GetLabel(5)') or xbmc.getInfoLabel(
                'Control.GetLabel(2000)')
        if text:
            return self.processLines(text.splitlines())
        else:
            return self.getLegacyTextbox()

    def getLegacyTextbox(self) -> List[str]:
        folderPath = xbmc.getInfoLabel('Container.FolderPath')
        if folderPath.startswith('addons://'):
            import os
            import codecs
            changelog = os.path.join(xbmc.getInfoLabel('ListItem.Property(Addon.Path)'),
                                     'changelog.txt')
            if not os.path.exists(changelog):
                return []
            with codecs.open(changelog, 'r', 'utf-8') as f:
                lines = f.readlines()
            return self.processLines(lines)
        return []

    def processLines(self, lines) -> List[str]:
        ret: List[str] = []
        for l in lines:
            if not re.search('\w', l):
                continue
            ret.append(l.strip())
        return ret

    def getWindowTexts(self, phrases: PhraseList) -> bool:
        texts: List[str] | None = self.getViewerTexts()
        if texts and not self.last(texts):
            phrases.add_text(texts=texts)
            return True
        return False

    def getControlText(self, control_id, phrases: PhraseList) -> bool:
        return False

    def getMonitoredText(self, isSpeaking: bool = False) -> List[str] | None:
        if self.doubleChecked:
            return None
        if time.time() - self.start > 2:
            self.doubleChecked = True
            texts: List[str] = self.getViewerTexts()
            if self.last(texts):
                return None
            return texts
