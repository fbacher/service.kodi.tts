# coding=utf-8

from typing import Callable, ForwardRef, List, Union

import xbmc
import xbmcgui

from common.constants import Constants
from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlType, Item
from gui.element_parser import (ElementHandler)
from gui.parse_radio_button import ParseRadioButton
from gui.parse_topic import ParseTopic
from gui.topic_model import TopicModel
from gui.window import Window

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class RadioButtonModel(BaseLabelModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.RADIO_BUTTON.name]

    def __init__(self, parent: BaseModel, parsed_radio_button: ParseRadioButton) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(parent.window_model, parsed_radio_button)
        self.parent = parent
        self.description: str = ''
        self.enable_expr: str = ''
        self.label2_expr: str = ''
        self.label_expr: str = ''
        self.labeled_by_expr: str = ''
        self.selected_expr: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.visible_expr: str = ''
        self.wrap_multiline: bool = False
        self.alt_label_expr: str = ''
        self.hint_text_expr: str = ''
        self.on_info_expr: str = ''
        self.children: List[BaseModel] = []

        self.previous_heading: PhraseList = PhraseList()
        self.previous_text_value: str = ''

        self.convert(parsed_radio_button)

    def convert(self, parsed_radio_button: ParseRadioButton) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_radio_button: A ParseButton instance that
               needs to be converted to a RadioButtonModel
        :return:
        """
        clz = type(self)
        self.control_type = parsed_radio_button.control_type
        self.control_id = parsed_radio_button.control_id
        self.description = parsed_radio_button.description
        self.enable_expr = parsed_radio_button.enable_expr
        self.label2_expr = parsed_radio_button.label2_expr
        self.label_expr = parsed_radio_button.label_expr
        self.labeled_by_expr = parsed_radio_button.labeled_by_expr
        self.selected_expr = parsed_radio_button.selected_expr
        # self.on_click
        self.on_focus_expr = parsed_radio_button.on_focus_expr
        self.on_unfocus_expr = parsed_radio_button.on_unfocus_expr
        self.visible_expr = parsed_radio_button.visible_expr
        self.wrap_multiline = parsed_radio_button.wrap_multiline
        self.alt_label_expr = parsed_radio_button.alt_label_expr
        self.hint_text_expr = parsed_radio_button.hint_text_expr
        self.on_info_expr = parsed_radio_button.on_info_expr

        if parsed_radio_button.topic is not None:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(ParseTopic.item)
            self.topic = model_handler(self, parsed_radio_button.topic)


        clz._logger.debug(f'# parsed children: {len(parsed_radio_button.get_children())}')

        for child in parsed_radio_button.children:
            child: BaseParser
            # clz._logger.debug(f'child: {child}')
            model_handler:  Callable[[BaseModel, BaseParser], BaseModel]
            # clz._logger.debug(f'About to create model from {type(child).item}')
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
            self.children.append(child_model)

    def clear_history(self) -> None:
        clz = type(self)
        clz._logger.debug(f'clear_history')
        self.previous_heading.clear()
        self.previous_text_value = ''

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
            if not focus_changed:
                success = self.voice_radio_button_value(phrases, focus_changed)
                return success
            clz._logger.debug(f'topic: {topic.alt_type}')
            temp_phrases: PhraseList = PhraseList()
            heading_success: bool = self.voice_heading(temp_phrases)
            if heading_success and not self.previous_heading.equal_text(temp_phrases):
                self.previous_heading.clear()
                self.previous_heading.extend(temp_phrases)
                phrases.extend(temp_phrases)
            success = self.voice_radio_button_label(phrases, focus_changed)

        # TODO, incomplete
        return success

    def voice_heading(self, phrases: PhraseList) -> bool:
        """

        :param phrases:
        :return: True if heading was appended to phrases, otherwise False
        """
        clz = type(self)
        success: bool = False
        success = self.voice_control_name(phrases)
        topic: TopicModel | None = self.topic
        return success

    def voice_radio_button_label(self, phrases: PhraseList, focus_changed) -> bool:
        clz = type(self)
        success = self.voice_labeled_by(phrases)
        clz._logger.debug(f'voice_labeled_by: {success}')
        if not success:
            success = self.topic.voice_alt_label(phrases)
        if not success:
            success = self.topic.voice_label_expr(phrases)
            clz._logger.debug(f'voice_label_expr: {success}')
        if not success:
            if self.control_id != -1:
                try:
                    query: str = f'Control.GetLabel({self.control_id}).index(0)'
                    text: str = xbmc.getInfoLabel(query)
                    # None is returned when no substitutions have been done on text
                    new_text: str = Messages.format_boolean(text=text)
                    if new_text is None:
                        new_text = ''
                    clz._logger.debug(f'text: {new_text} focus_changed: {focus_changed} '
                                      f'previous_text: {self.previous_text_value}')
                    if new_text != '' and (
                            focus_changed or new_text != self.previous_text_value):
                        phrases.append(Phrase(text=new_text))
                    self.previous_text_value = new_text
                except ValueError as e:
                    clz._logger.exception('')
                    pass
        return success

    def voice_radio_button_value(self, phrases, focus_changed: bool) -> bool:
        # Control ID should be an integer
        clz = type(self)
        success: bool = False
        if self.control_id != -1:
            try:
                query: str = f'Control.GetLabel({self.control_id}).index(0)'
                text: str = xbmc.getInfoLabel(query)
                # None is returned with no substitutions needed
                new_text: str = Messages.format_boolean(text=text)
                clz._logger.debug(f'text: {new_text} focus_changed: {focus_changed} '
                                  f'previous_text: {self.previous_text_value}')
                if new_text != '' and (focus_changed or new_text != self.previous_text_value):
                    phrases.append(Phrase(text=new_text))
                self.previous_text_value = new_text
            except ValueError as e:
                pass
        return success

    '''
    def format_value(self, text: str, phrases: PhraseList, focus_changed: bool,
                     enabled_msgid: int = Messages.ENABLED.get_msg_id(),
                     disabled_msgid: int = Messages.DISABLED.get_msg_id()) -> bool:
        clz = type(self)
        success: bool = False
        new_text: str = text
        if text.endswith(')'):  # Skip this most of the time
            # For boolean settings
            new_text: str = text.replace('( )',
                                         f'{Constants.PAUSE_INSERT} '
                                         f'{Messages.get_msg_by_id(disabled_msgid)}')
            new_text = new_text.replace('(*)',
                                        f'{Constants.PAUSE_INSERT} '
                                        f'{Messages.get_msg_by_id(enabled_msgid)}')
        if new_text != '' and (focus_changed or text != self.previous_text_value):
            clz._logger.debug(f'text: {text} focus_changed: {focus_changed} '
                              f'previous_text: {self.previous_text_value} '
                              f'new_text: {new_text}')
            phrases.append(Phrase(text=new_text))
            success = True
        self.previous_text_value = text
        return success
    '''

    def __repr__(self) -> str:
        clz = type(self)
        labeled_by_str: str = ''
        if self.labeled_by_expr != '':
            labeled_by_str = f' labeled_by: {self.labeled_by_expr}'

        if self.on_focus_expr is not None and (len(self.on_focus_expr) > 0):
            on_focus_expr: str = f'\n  on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr is not None and (len(self.on_unfocus_expr) > 0):
            on_unfocus_expr: str = f'\n  on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''
        visible_expr: str = ''
        if self.visible_expr is not None and len(self.visible_expr) > 0:
            visible_expr = f'\n  visible_expr: {self.visible_expr}'

        description_str: str = ''
        if self.description != '':
            description_str = f'\n  description: {self.description}'

        enable_expr_str: str = ''
        if self.enable_expr != '':
            enable_expr_str = f'\n  enable: {self.enable_expr}'

        label2_expr_str: str = ''
        if self.label2_expr != '':
            label2_expr = f'\n  label2: {self.label2_expr}'

        selected_expr_str: str = ''
        if self.selected_expr != '':
            selected_expr_str = f'\n  selected: {self.selected_expr}'

        wrap_multiline_str = ''
        if self.wrap_multiline:
            wrap_multiline_str = f'\n  wrap_multiline: {self.wrap_multiline}'

        alt_label_expr_str: str = ''
        if self.alt_label_expr != '':
            alt_label_expr_str = f'\n  alt_label: {self.alt_label_expr}'

        hint_text_expr_str: str = ''
        if self.hint_text_expr != '':
            hint_text_expr_str = f'\n  hint_text: {self.hint_text_expr}'

        on_info_expr_str: str = ''
        if self.on_info_expr != '':
            on_info_expr_str = f'\n  on_info: {self.on_info_expr}'

        label_expr_str: str = ''
        if self.label_expr is not None and len(self.label_expr) > 0:
            label_expr_str = f'\n  label: {self.label_expr}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n{self.topic}'

        results: List[str] = []
        result: str = (f'\nRadioButtonModel type: {self.control_type} '
                       f'id: {self.control_id}{labeled_by_str}'
                       f'{selected_expr_str}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'{visible_expr}{description_str}'
                       f'{enable_expr_str}'
                       f'{label_expr_str}'
                       f'{label2_expr_str}'
                       f'{wrap_multiline_str}'
                       f'{alt_label_expr_str}'
                       f'{hint_text_expr_str}'
                       f'{on_info_expr_str}'
                       f'{topic_str}'
                       f'\n  #children: {len(self.children)}'
                       )
        results.append(result)

        for child in self.children:
            child: BaseParser
            results.append(str(child))

        results.append(f'END RadioButtonModel')
        return '\n'.join(results)
