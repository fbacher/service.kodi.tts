# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *
from common.logger import BasicLogger

from common.messages import Messages
from common.phrases import PhraseList
from . import base
from .window_state_monitor import WinDialogState

MY_LOGGER = BasicLogger.get_logger(__name__)


class VideoLibraryWindowReader(base.DefaultWindowReader):
    ID = 'videolibrary'

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None,
                 windialog_state: WinDialogState = None) -> None:
        super().__init__(win_id, service)
        clz = type(self)

    def getControlText(self, control_id, phrases: PhraseList) -> bool:
        cls = type(self)
        text: str
        compare: str
        success: bool = False
        MY_LOGGER.debug(f'control_id: {control_id} incomming phrases: {phrases}')
        if self.slideoutHasFocus():
            success = self.getSlideoutText(control_id, phrases)
            MY_LOGGER.debug(f'slideoutHasFocus success: {success} phrases: {phrases}')
            return success
        if not control_id:
            return False
        text = xbmc.getInfoLabel('ListItem.Label')
        #  MY_LOGGER.debug(f'text: {text} phrases: {phrases}')
        if not text:
            return base.DefaultWindowReader.getControlText(self, control_id,
                                                           phrases)
        MY_LOGGER.debug(f'A ListItem label: {text}')
        status: str = ''
        if xbmc.getCondVisibility('ListItem.IsResumable'):
            status = f': {Messages.get_msg(Messages.RESUMABLE)}'
        elif xbmc.getInfoLabel('ListItem.Overlay') == 'OverlayWatched.png':
            status = f': {Messages.get_msg(Messages.WATCHED)}'
        #  MY_LOGGER.debug(f'text: {text} status: {status} phrases: {phrases}')
        phrases.add_text(texts=f'{text} {status}')
        return True
