# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *
from common.logger import BasicLogger

from common.messages import Messages
from common.phrases import PhraseList
from .base import WindowReaderBase
module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SettingsReader(WindowReaderBase):
    ID = 'settings'

    def getWindowExtraTexts(self, phrases: PhraseList) -> bool:
        return False

    def getItemExtraTexts(self, control_id, phrases: PhraseList) -> bool:
        text: str = xbmc.getInfoLabel(f'Container({control_id}).ListItem.Label2')
        if text:
            phrases.add_text(texts=text)
            return True
        return False

    def getControlText(self, control_id: int, phrases: PhraseList) -> bool:
        clz = type(self)
        if not control_id:
            return False
        sub = ''
        text = self.getSettingControlText(control_id)
        if text.startswith('-'):
            sub = f'{Messages.get_msg(Messages.SUB_SETTING)}: '
        phrases.add_text(texts=f'{sub} {text}')
        return True
