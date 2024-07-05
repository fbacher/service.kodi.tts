# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *
from common.logger import BasicLogger
from common.phrases import PhraseList

from .base import WindowReaderBase

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ContextMenuReader(WindowReaderBase):
    ID = 'contextmenu'

    def getControlText(self, control_id, phrases: PhraseList) -> bool:
        clz = type(self)
        text: str = xbmc.getInfoLabel('System.CurrentControl')
        if text is not None and text != '':
            phrases.add_text(texts=text)
            return True
        return False

    def getWindowExtraTexts(self, phrases: PhraseList) -> bool:
        return False
