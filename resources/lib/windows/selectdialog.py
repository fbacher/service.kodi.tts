# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *
from common.logger import BasicLogger

from common.messages import Messages
from common.phrases import Phrase, PhraseList
from .base import CURRENT_SKIN, WindowReaderBase
module_logger = BasicLogger.get_logger(__name__)


class SelectDialogReader(WindowReaderBase):
    ID = 'selectdialog'

    def getHeading(self, phrases: PhraseList) -> bool:
        if CURRENT_SKIN == 'confluence':
            return False  # Broken for Confluence
        return WindowReaderBase.getHeading(self, phrases)

    def getControlText(self, control_id, phrases: PhraseList) -> bool:
        clz = type(self)
        label = xbmc.getInfoLabel('System.CurrentControl')
        selected = xbmc.getCondVisibility(
                'Container({0}).ListItem.IsSelected'.format(
                    control_id)) and ': {0}'.format(
                Messages.get_msg(Messages.SELECTED)) or ''
        text = f'{label}{selected}'
        phrases.add_text(texts=text)
        return True

    def getWindowExtraTexts(self, phrases) -> bool:
        return False
