# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *
from common.logger import BasicLogger
from common.phrases import PhraseList

from .base import WindowReaderBase

module_logger = BasicLogger.get_logger(__name__)


class SubtitlesDialogReader(WindowReaderBase):
    ID = 'subtitlesdialog'

    def getControlText(self, control_id: int, phrases: PhraseList) -> bool:
        clz = type(self)
        texts: List[str] = [xbmc.getInfoLabel('System.CurrentControl')]
        if xbmc.getCondVisibility(
                'Container({0}).ListItem.property(hearing_imp)'.format(control_id)):
            texts.append('closed caption')
        if xbmc.getCondVisibility(
                'Container({0}).ListItem.property(sync)'.format(control_id)):
            texts.append('sync')
        texts.append(
            xbmc.getInfoLabel('Container({0}).ListItem.Label2'.format(control_id)))
        texts.append('{0} stars'.format(
            xbmc.getInfoLabel('Container({0}).ListItem.ActualIcon'.format(control_id))))
        text = ': '.join(texts)
        # TODO: Fix - this doesn't work when scrolling off the top or
        # bottom of the list
        text_id: str = text + xbmc.getInfoLabel(f'Container({control_id}).Position')
        phrases.add_text(texts=text, text_id=text_id)
        return True
