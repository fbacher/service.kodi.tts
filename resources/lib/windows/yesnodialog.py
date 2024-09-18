# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *
from common.logger import BasicLogger
from common.phrases import Phrase, PhraseList

from . import guitables
from .base import WindowReaderBase
module_logger = BasicLogger.get_logger(__name__)


class YesNoDialogReader(WindowReaderBase):
    ID = 'yesnodialog'

    def getControlText(self, control_id: int, phrases: PhraseList) -> bool:
        clz = type(self)
        text = xbmc.getInfoLabel('System.CurrentControl')
        phrases.add_text(texts=text)
        return True

    def getHeading(self, phrases: PhraseList) -> bool:
        return guitables.convertTexts(10100, ('1',), phrases)

    def getWindowTexts(self, phrases: PhraseList) -> bool:
        return self.getWindowExtraTexts(phrases)

    def getWindowExtraTexts(self, phrases: PhraseList) -> bool:
        return guitables.convertTexts(10100, ('2', '3', '4', '9'),
                                      phrases)
