# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *

from common.logger import BasicLogger
from common.messages import Messages
from .base import WindowReaderBase

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class HomeDialogReader(WindowReaderBase):
    ID = 'progressdialog'
    _logger: BasicLogger = None

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None) -> None:
        cls = type(self)
        super().__init__(win_id, service)
        cls._logger = module_logger.getChild(cls.__class__.__name__)

    def getControlText(self, controlID):
        cls = type(self)
        #  label_id: str = f'{self.service.controlID}6'
        #  info = xbmc.getInfoLabel(f'Control.GetLabel({label_id})')
        text = xbmc.getInfoLabel('System.CurrentControl')
        # info = xbmc.getInfoLabel(f'{1732}')
        # cls._logger.debug(f'controlID: {controlID}  '
        #                   f'service.controlID: {self.service.controlID} '
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
        return (text, text)

    def getControlPostfix(self, controlID, ):
        cls = type(self)
        if not self.service.speakListCount:
            return ''
        numItems = xbmc.getInfoLabel(f'Container({self.service.controlID}).NumItems')
        #  container_listitem_label = xbmc.getInfoLabel(
        #     f'Container({self.service.controlID}).ListItem.label')  # Sets
        #  container_label = xbmc.getInfoLabel(f'Container({
        #  self.service.controlID}6.label)')
        label_id: str = f'{self.service.controlID}6'
        x = xbmc.getInfoLabel(f'Control.GetLabel({label_id})')
        cls._logger.debug(f'x: {x}')

        if numItems:
            result = f'{x} ' + '{0} {1}'.format(numItems,
                                                numItems != '1'
                                                and Messages.get_msg(Messages.ITEMS)
                                                or Messages.get_msg(Messages.ITEM))
            """
            winID = xbmcgui.getCurrentWindowId()
            window = xbmcgui.Window(winID)
            # label_id = 1732

            # cls._logger.debug(f'label_id: {label_id} label: {label.getLabel()}')
            cls._logger.debug(f'controlID: {controlID} result: {result}')
            info = xbmc.getInfoLabel(f'Container().ListItem.label')
            cls._logger.debug(f'info: {info}')
            cls._logger.debug(f'container_listitem_label: {container_listitem_label}')
            # cls._logger.debug(f'container_label: {container_label}')
            """
            return result
        return ''
