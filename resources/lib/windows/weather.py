# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *
from common.logger import BasicLogger
from common.phrases import PhraseList

from . import windowparser
from .base import parseItemExtra, WindowReaderBase
module_logger = BasicLogger.get_module_logger(module_path=__file__)


class WeatherReader(WindowReaderBase):
    ID = 'weather'

    def getWindowTexts(self, phrases: PhraseList) -> bool:
        return self.getWindowExtraTexts(phrases)

    def getWindowExtraTexts(self, phrases: PhraseList) -> bool:
        return windowparser.getWindowParser().getWindowTexts(phrases)

    def getItemExtraTexts(self, control_id: int, phrases: PhraseList) -> bool:
        excludes: PhraseList = PhraseList()
        self.getControlText(control_id, excludes)
        return parseItemExtra(control_id, excludes, phrases)

    def getControlText(self, control_id: int, phrases: PhraseList) -> bool:
        clz = type(self)
        if not control_id:
            return False
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text:
            return False
        phrases.add_text(texts=text)
        return True
