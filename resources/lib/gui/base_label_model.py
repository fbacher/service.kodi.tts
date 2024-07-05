# coding=utf-8

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, ForwardRef, List, Tuple

import xbmc
import xbmcgui

from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_model import BaseModel
from gui.base_tags import control_elements, ControlType, Item, WindowType

from gui.base_parser import BaseParser
from gui.base_tags import ElementKeywords as EK
from windows.ui_constants import UIConstants

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class BaseLabelModel(BaseModel):

    _logger: BasicLogger = None

    def __init__(self, window_model: BaseModel, parser: BaseParser) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(window_model, parser)

        self.label_expr: str = ''
        self.info_expr: str = ''

    def voice_labelx(self, phrases: PhraseList) -> bool:
        """
            Gets the text value from this label.
            If the label contains a number, then interpret as a message id
            Otherwise, interpret as an $INFOLABEL or

        :return: text
        """
        clz = type(self)
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
        new_phrases: PhraseList = PhraseList()
        for text in texts:
            if text == '':
                if len(new_phrases) > 0:
                    new_phrases[-1].set_post_pause(Phrase.PAUSE_DEFAULT)
                continue
            phrase = Phrase(text)
            new_phrases.append(phrase)

        clz._logger.debug(f'Phrases: {new_phrases}')
        phrases.extend(new_phrases)
        return success

    def voice_control_label(self, phrases: PhraseList,
                            control_id_expr: int | str | None = None,
                            focus_change: bool = True) -> bool:
        """

        :param phrases: PhraseList to append to
        :param control_id_expr: control_id (int)
        :param focus_change: If True, then voice changed heading, labels and all
                              If False, then only voice a change in value.
        :return: True if anything appended to phrases, otherwise False

        Note that focus_changed = False can occur even when a value has changed.
        One example is when user users cursor to select different values in a
        slider, but never leaves the control's focus.
        """
        clz = type(self)
        # Control ID should be an integer
        success: bool = False
        control_id: int = -1
        if control_id_expr is not None:
            control_id = self.get_non_negative_int(control_id_expr)
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
                    phrases.append(Phrase(text=text))
            except ValueError as e:
                success = False
            if not success:
                try:
                    query: str = f'Control.GetLabel({control_id})'
                    text: str = xbmc.getInfoLabel(query)
                    clz._logger.debug(f'Text: {text}')
                    if text != '':
                        phrases.append(Phrase(text=text))
                        success = True
                except ValueError as e:
                    success = False
        return success

    def voice_control_label2(self, phrases: PhraseList,
                             control_id_expr: int | str | None = None) -> bool:
        clz = type(self)
        # Control ID should be an integer
        success: bool = False
        control_id: int = -1
        if control_id_expr is not None:
            control_id = self.get_non_negative_int(control_id_expr)
        else:
            control_id = self.control_id
        if self.control_id != -1:
            try:
                query: str = f'Control.GetLabel({control_id}).index(1)'
                text: str = xbmc.getInfoLabel(query)
                clz._logger.debug(f'Text: {text}')
                if text != '':
                    phrases.append(Phrase(text=text))
                    success = True
            except ValueError as e:
                success = False
        return success
