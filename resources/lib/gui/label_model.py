# coding=utf-8
import re
from typing import Callable, ForwardRef, List, Union

import xbmc
import xbmcgui

from common.logger import BasicLogger
from common.phrases import Phrase, PhraseList
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlType, Item
from gui.element_parser import (BaseElementParser, ElementHandler)
from gui.parse_label import ParseLabel
from gui.parse_topic import ParseTopic
from gui.topic_model import TopicModel
from gui.window import Window
from windows.ui_constants import UIConstants
from windows.window_state_monitor import WinDialog, WinDialogState

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class LabelModel(BaseLabelModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.LABEL_CONTROL.name]

    def __init__(self, parent: BaseModel, parsed_label: ParseLabel) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(window_model=parent.window_model, parser=parsed_label)
        self.parent = parent
        self.control_type: ControlType = ControlType.LABEL_CONTROL
        self.label_for: str = ''
        self.hint_text_expr: str = ''
        self.children: List[BaseModel] = []
        self.parent: BaseModel = None
        self.attributes_with_values: List[str] = clz.item.attributes_with_values
        self.attributes: List[str] = clz.item.attributes
        self.visible_expr: str = ''
        self.default_control_always: bool = False
        self.default_control_id: int = -1
        self.scroll: bool = False
        self.scroll_suffix: str = '|'
        self.scroll_speed: int = 60  # pixels per sec
        self.label_expr: str = ''
        self.info_expr: str = ''
        self.number_expr: str = ''
        self.has_path: bool = False
        self.wrap_multiline: bool = False
        self.description: str = ''

        self.previous_heading: PhraseList = PhraseList()
        self.previous_value: PhraseList = PhraseList()
        self.convert(parsed_label)

    def convert(self, parsed_label: ParseLabel) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_label: A ParseGroup instance that
               needs to be convertd to a GroupModel
        :return:
        """
        clz = type(self)
        self.visible_expr = parsed_label.visible_expr
        self.wrap_multiline = parsed_label.wrap_multiline
        self.info_expr = parsed_label.info_expr
        # self.attributes_with_values: List[str]
        # self.attributes: List[str]
        self.label_for = parsed_label.label_for
        clz._logger.debug(f'label_for: {self.label_for}')
        # self.default_control_always = parsed_label.default_control_always
        # self.default_control_id = parsed_label.default_control_id
        self.scroll: bool = parsed_label.scroll
        self.scroll_suffix = parsed_label.scroll_suffix
        self.scroll_speed = parsed_label.scroll_speed
        self.label_expr = parsed_label.label_expr
        self.hint_text_expr = parsed_label.hint_text_expr
        self.info_expr = parsed_label.info_expr
        self.number_expr = parsed_label.number_expr
        self.has_path = parsed_label.has_path
        self.wrap_multiline = parsed_label.wrap_multiline
        self.description = parsed_label.description

        if parsed_label.topic is not None:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(ParseTopic.item)
            self.topic = model_handler(self, parsed_label.topic)

        for child in parsed_label.children:
            child: BaseElementParser
            keyword: str = child.item.keyword
            model_handler:  Callable[[BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
            self.children.append(child_model)

        children: List[BaseParser] = []
        parsers: List[BaseElementParser] = []

    def clear_history(self) -> None:
        self.previous_heading.clear()

    def voice_control(self, phrases: PhraseList,
                      focus_changed: bool) -> bool:
        """

        :param phrases: PhraseList to append to
        :param focus_changed: If True, then voice changed heading, labels and all
                              If False, then only voice a change in value.
        :return: True if anything appended to phrases, otherwise False

        Note that focus_changed = False can occur even when a value has changed.
        One example is when user users cursor to select different values in a
        slider, but never leaves the control's focus.
        """
        clz = type(self)
        success: bool = True
        if self.topic is not None:
            topic: TopicModel = self.topic
            clz._logger.debug(f'topic: {topic.alt_type}')
            success = topic.voice_alt_control_name(phrases)
            if not success:
                success = self.voice_control_name(phrases)
            success = self.voice_heading(phrases)
            success = self.voice_label(phrases)
            success = self.voice_label2(phrases)
            # Voice either next Topic down or focus item

        # TODO, incomplete
        return success

    def voice_label(self, phrases, control_id_expr: None = None) -> bool:
        # Control ID should be an integer
        clz = type(self)
        clz._logger.debug(f'voice_label control_id: {self.control_id}')
        success: bool = False
        if self.control_id != -1:
            try:
                query: str = f'Control.GetLabel({self.control_id})'
                text: str = xbmc.getInfoLabel(query)
                clz._logger.debug(f'text: {text}')
                if text != '':
                    phrases.append(Phrase(text=text))
                    success = True
            except ValueError as e:
                clz._logger.exception('')
                pass
        return success

    def voice_value(self, phrases: PhraseList) -> bool:
        """
        Voice this label as a value for some other control.
        Let the other control decide whether to ignore repeat values.
        That will be consistent with a control deciding when to voice its
        value.
        :param phrases:
        :return:
        """
        clz = type(self)
        # clz._logger.debug(f'label_model: {self}')
        # temp_phrases: PhraseList = PhraseList()
        success: bool = self.voice_label(phrases)
        # if temp_phrases.equal_text(self.previous_value):
        #     return False
        # else:
        #     self.previous_value = temp_phrases
        #    phrases.extend(temp_phrases)
        return success

    def __repr__(self) -> str:
        clz = type(self)
        control_id: str = ''
        if self.control_id != '':
            control_id = f' id: {self.control_id}'

        label_for_str: str = ''
        if self.label_for != '':
            label_for_str = f'\n label_for: {self.label_for}'

        visible_expr: str = ''
        if self.visible_expr is not None and len(self.visible_expr) > 0:
            visible_expr = f'\n  visible_expr: {self.visible_expr}'

        label_expr: str = ''
        if self.label_expr is not None and len(self.label_expr) > 0:
            label_expr = f'\n  label_expr: {self.label_expr}'
        number_expr: str = ''
        if self.number_expr:
            number_expr = f'\n  number_expr: {number_expr}'

        has_path_str: str = ''
        if self.has_path:
            has_path_str = f'\n  has_path: {self.has_path}'

        hint_text_str: str = ''
        if self.hint_text_expr != '':
            hint_text_str = f'\n  hint_text: {self.hint_text_expr}'

        info_expr: str = ''
        if len(self.info_expr) > 0:
            info_expr = f'\n  info_expr: {self.info_expr}'

        if len(self.visible_expr) > 0:
            visible_expr: str = f'\n visible: {self.visible_expr}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nLabelModel type: {self.control_type}'
                       #  f' item: {clz.item} key: {clz.item.key}'
                       f'{control_id}{label_for_str}'
                       f'{visible_expr}'
                       f'{visible_expr}{label_expr}'
                       f'{number_expr}{has_path_str} '
                       f'{hint_text_str}'
                       f'{info_expr}'
                       f'{topic_str}'
                       f'\n  #children: {len(self.children)}'
                       )
        results.append(result)

        for child in self.children:
            child: BaseParser
            results.append(str(child))
        results.append(f'\nEND LabelModel')

        return '\n'.join(results)
