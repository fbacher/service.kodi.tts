# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *

from .base import WindowReaderBase


class ContextMenuReader(WindowReaderBase):
    ID = 'contextmenu'

    def getControlText(self, controlID):
        text = xbmc.getInfoLabel('System.CurrentControl')
        return (text, text)

    def getWindowExtraTexts(self):
        return None
