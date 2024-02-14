# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

from .base import WindowReaderBase

from common import *

class PVRGuideInfoReader(WindowReaderBase):
    ID = 'pvrguideinfo'

    def getWindowTexts(self): return self.getWindowExtraTexts()
