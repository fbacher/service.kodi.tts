# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *

from common.messages import Messages
from .base import CURRENT_SKIN, WindowReaderBase


class SelectDialogReader(WindowReaderBase):
    ID = 'selectdialog'

    def getHeading(self):
        if CURRENT_SKIN == 'confluence':
            return None  # Broken for Confluence
        return WindowReaderBase.getHeading(self)

    def getControlText(self, controlID):
        label = xbmc.getInfoLabel('System.CurrentControl')
        selected = xbmc.getCondVisibility(
                'Container({0}).ListItem.IsSelected'.format(
                    controlID)) and ': {0}'.format(
                Messages.get_msg(Messages.SELECTED)) or ''
        text = '{0}{1}'.format(label, selected)
        return (text, text)

    def getWindowExtraTexts(self):
        return None
