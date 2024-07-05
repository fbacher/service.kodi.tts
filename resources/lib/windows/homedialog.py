# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc
import xbmcgui

from common import *

from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from .base import WindowReaderBase

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class HomeDialogReader(WindowReaderBase):
    ID = 'progressdialog'
    _logger: BasicLogger = None

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None) -> None:
        cls = type(self)
        super().__init__(win_id, service)
        cls._logger = module_logger.getChild(cls.__class__.__name__)

    def getControlText(self, control_id, phrases: PhraseList) -> bool:
        cls = type(self)
        #  label_id: str = f'{self.service.current_control_id}6'
        #  info = xbmc.getInfoLabel(f'Control.GetLabel({label_id})')

        text: str = xbmc.getInfoLabel('System.CurrentControl')

        # info = xbmc.getInfoLabel(f'{1732}')
        # cls._logger.debug(f'control_id: {control_id}  '
        #                   f'service.current_control_id: {self.service.current_control_id} '
        #                   f'text: {text}')

        #  winID = xbmcgui.getCurrentWindowId()
        #  window = xbmcgui.Window(winID)
        # label_id = 1732
        # label: xbmcgui.ControlLabel = window.getControl(label_id)
        #  x = xbmc.getInfoLabel(f'Control.GetLabel({label_id})')
        #  cls._logger.debug(f'label: {x}')
        #  cls._logger.debug(f'label_id: {label_id} label: {x}')
        # cls._logger.debug(f'visible: {label.isVisible()}')
        # x = xbmc.getInfoLabel(f'Control.GetLabel({label_id})')
        #  cls._logger.debug(f'infoLabel(label): {x}')
        #  label.setLabel('set label', label2='set label2')
        #  cls._logger.debug(f'new label: {label.getLabel()}')
        if text != '':
            phrases.add_text(texts=text)
            return True
        return False

    def getControlPostfix(self, control_id, phrases: PhraseList) -> bool:
        clz = type(self)
        # Experiment proves, that at least under some conditions, you can
        # add control ids to system .xml files and reference them at
        # run-time
        #
        """
        win: xbmcgui.Window = xbmcgui.Window(self.winID)
        for ctl_id in (314159, 314160, 314161):
            control: xbmcgui.Control = win.getControl(ctl_id)
            control: xbmcgui.ControlLabel
            clz._logger.debug(f'control: {control}')
            text: str = control.getLabel()
            query: str = f'Control.GetLabel({ctl_id})'
            text_1: str = xbmc.getInfoLabel(query)
            clz._logger.debug(f'label text_1: {text_1}')
            query: str = f'Control.GetLabel({ctl_id}).index(1)'
            text_2: str = xbmc.getInfoLabel(query)
            clz._logger.debug(f'text_1: {text_1} text_2: {text_2}')
        """
        if not self.service.speakListCount:
            return False
        num_items: str = xbmc.getInfoLabel(f'Container({self.service.current_control_id})'
                                           f'.NumItems')
        #  container_listitem_label = xbmc.getInfoLabel(
        #     f'Container({self.service.current_control_id}).ListItem.label')  # Sets
        #  container_label = xbmc.getInfoLabel(f'Container({
        #  self.service.current_control_id}6.label)')
        label_id: str = f'{self.service.current_control_id}6'
        x = xbmc.getInfoLabel(f'Control.GetLabel({label_id})')
        if num_items is None or num_items == '0':
            return False

        clz._logger.debug(f'CHECK numItems: {num_items} x: {x} label_id: {label_id}')
        tmp: str
        if num_items == '1':
            tmp = Messages.get_msg(Messages.ITEM)
        else:
            tmp = Messages.get_msg(Messages.ITEMS)
        result: str = f'{x} {tmp}'
        phrases.add_text(texts=result)
        return True
