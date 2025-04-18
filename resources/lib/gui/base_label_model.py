# coding=utf-8
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, ForwardRef, List, Tuple

import xbmc
import xbmcgui

from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_model import BaseModel
from gui.base_tags import control_elements, ControlElement, Item, WindowType

from gui.base_parser import BaseParser
from gui.base_tags import ElementKeywords as EK
from gui.statements import Statements
from utils import util
from windows.ui_constants import UIConstants
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class BaseLabelModel(BaseModel):

    _logger: BasicLogger = module_logger

    def __init__(self, window_model: BaseModel, parser: BaseParser,
                 windialog_state: WinDialogState) -> None:
        clz = BaseLabelModel
        if clz._logger is None:
            clz._logger = module_logger
        super().__init__(window_model, parser,  windialog_state=windialog_state)

        self.label_expr: str = ''
        self.info_expr: str = ''

    @property
    def supports_label(self) -> bool:
        # ControlCapabilities.LABEL
        return True

    @property
    def supports_label2(self) -> bool:
        #  ControlCapabilities.LABEL2
        return False

    '''
    def voice_labelx(self, stmts: Statements) -> bool:
        """
            Gets the text value from this label.
            If the label contains a number, then interpret as a message id
            Otherwise, interpret as an $INFOLABEL or

        :return: text
        """
        clz = BaseLabelModel
        success: bool = True
        text: str = None
        text_id: int = -1
        if self.label_expr != '':
            try:
                text_id = int(self.label_expr)
                text = Messages.get_msg(text_id)
            except ValueError:
                text_id = -1  # Shouldn't need to do this

        if text is None or text == '-':
            # Perhaps an info label
            if hasattr(self, 'info_expr') and self.info_expr != '':
                text = xbmc.getInfoLabel(f'{self.info_expr}')
            if text is None or text == '-':
                text = xbmc.getInfoLabel(f'Control.getLabel({self.control_id})')
        if text == '' or text == '-':
            clz._logger.debug(f'text is None')
            success = False
            return success

        text = UIConstants.TAG_RE.sub('', text).strip(' .')
        texts: List[str] = text.split('[CR]')
        new_phrases: PhraseList = PhraseList(check_expired=False)
        for text in texts:
            if text == '':
                if len(new_phrases) > 0:
                    new_phrases[-1].set_post_pause(Phrase.PAUSE_DEFAULT)
                continue
            phrase = Phrase(text)
            new_phrases.append(phrase)

        clz._logger.debug(f'Phrases: {new_phrases}')
        stmts.last.phrases.extend(new_phrases)
        return success
    '''

    def voice_control_label(self, stmts: Statements,
                            control_id_expr: int | str | None = None) -> bool:
        """

        :param stmts: Statements to append to
        :param control_id_expr: control_id (int)
        :return: True if anything appended to stmts, otherwise False
        """
        clz = BaseLabelModel
        # Control ID should be an integer
        success: bool = False
        control_id: int = -1
        if control_id_expr is not None:
            control_id = util.get_non_negative_int(control_id_expr)
        else:
            control_id = self.control_id

        clz._logger.debug(f'control_id: {control_id}')
        if control_id != -1:
            try:
                label_cntrl: xbmcgui.ControlLabel
                clz._logger.debug(f'Getting control')
                label_cntrl = self.get_label_control(control_id)
                clz._logger.debug(f'Getting Text')
                text = label_cntrl.getLabel()
                clz._logger.debug(f'Text: {text}')
                if text != '':
                    success = True
                    stmts.last.phrases.append(Phrase(text=text, check_expired=False))
            except ValueError as e:
                success = False
            if not success:
                try:
                    query: str = f'Control.GetLabel({control_id})'
                    text: str = xbmc.getInfoLabel(query)
                    clz._logger.debug(f'Text: {text}')
                    if text != '':
                        stmts.last.phrases.append(Phrase(text=text, check_expired=False))
                        success = True
                except ValueError as e:
                    success = False
        return success

    def voice_control_label2(self, stmts: Statements,
                             control_id_expr: int | str | None = None) -> bool:
        clz = BaseLabelModel
        # Control ID should be an integer
        success: bool = False
        control_id: int = -1
        if control_id_expr is not None:
            control_id = util.get_non_negative_int(control_id_expr)
        else:
            control_id = self.control_id
        if self.control_id != -1:
            try:
                query: str = f'Control.GetLabel({control_id}).index(1)'
                text: str = xbmc.getInfoLabel(query)
                clz._logger.debug(f'Text: {text}')
                if text != '':
                    stmts.last.phrases.append(Phrase(text=text, check_expired=False))
                    success = True
            except ValueError as e:
                success = False
        return success
