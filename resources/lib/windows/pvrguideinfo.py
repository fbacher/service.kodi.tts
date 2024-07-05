# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

from common.logger import BasicLogger
from common.phrases import PhraseList
from .base import WindowReaderBase

from common import *
module_logger = BasicLogger.get_module_logger(module_path=__file__)


class PVRGuideInfoReader(WindowReaderBase):
    ID = 'pvrguideinfo'

    def getWindowTexts(self, phrases: PhraseList) -> bool:
        return self.getWindowExtraTexts(phrases)
