# coding=utf-8

from typing import Callable, ForwardRef, List, Union

import xbmc
import xbmcgui

from common.logger import BasicLogger
from common.phrases import Phrase, PhraseList
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlType, Item
from gui.element_parser import ElementHandler
from gui.parse_button import ParseButton
from gui.parse_topic import ParseTopic
from gui.topic_model import TopicModel
from gui.window import Window
from windows.window_state_monitor import WinDialog, WinDialogState

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ButtonModel(BaseLabelModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.BUTTON.name]

    def __init__(self, parent: BaseModel, parsed_button: ParseButton) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(window_model=parent.window_model, parser=parsed_button)
        self.parent = parent
        self.children: List[BaseModel] = []
        self.parent: BaseModel = None
        self.attributes_with_values: List[str] = clz.item.attributes_with_values
        self.attributes: List[str] = clz.item.attributes
        self.visible_expr: str = ''
        self.label_expr: str = ''
        self.wrap_multiline: bool = False
        self.description: str = ''
        self.alt_label_expr: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.enable_expr: str = ''
        self.hint_text_expr: str = ''

        self.previous_heading: PhraseList = PhraseList()
        self.previous_value: PhraseList = PhraseList()

        self.convert(parsed_button)

    def convert(self, parsed_button: ParseButton) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_button: A ParseButton instance that
               needs to be converted to a ButtonModel
        :return:
        """
        clz = type(self)
        self.topic: TopicModel | None = None  # Will get filled in by TopicModel
        self.control_type = parsed_button.control_type
        self.visible_expr = parsed_button.visible_expr
        self.wrap_multiline = parsed_button.wrap_multiline
        # self.attributes_with_values: List[str]
        # self.attributes: List[str]
        self.label_expr = parsed_button.label_expr
        self.description = parsed_button.description
        self.hint_text_expr = parsed_button.hint_text_expr
        self.alt_label_expr = parsed_button.alt_label_expr
        self.enable_expr = parsed_button.enable_expr

        if parsed_button.topic is not None:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(ParseTopic.item)
            self.topic = model_handler(self, parsed_button.topic)

        clz._logger.debug(f'# parsed children: {len(parsed_button.get_children())}')

        for child in parsed_button.children:
            child: BaseParser
            # clz._logger.debug(f'child: {child}')
            model_handler:  Callable[[BaseModel, BaseParser], BaseModel]
            # clz._logger.debug(f'About to create model from {type(child).item}')
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
            self.children.append(child_model)

    def clear_history(self) -> None:
        self.previous_heading.clear()
        self.previous_value.clear()

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
            if focus_changed:
                success = self.voice_heading(phrases)
                # if not self.previous_heading.equal_text(temp_phrases):
                #     self.previous_heading.clear()
                #     self.previous_heading.extend(temp_phrases)
                #     phrases.extend(temp_phrases)

                # Voice either focused control, or label/text
                #temp_phrases.clear()
            temp_phrases: PhraseList = PhraseList()
            success = topic.voice_value(temp_phrases)
            if focus_changed or not self.previous_value.equal_text(temp_phrases):
                phrases.extend(temp_phrases)
            self.previous_value.clear()
            self.previous_value.extend(temp_phrases)
            return success
        # TODO, incomplete
        return False

    def voice_value(self, phrases: PhraseList) -> bool:
        """
        ControlButton does not have a value.

        :param phrases:
        :return:
        """
        return False

    def voice_heading(self, phrases: PhraseList) -> bool:
        clz = type(self)
        success: bool = False
        success = self.voice_control_name(phrases)
        if self.topic is None:
            return self.get_heading_without_topic(phrases)

        success = self.voice_labeled_by(phrases)
        clz._logger.debug(f'voice_labeled_by: {success}')
        if not success:
            success = self.topic.voice_alt_label(phrases)
        if not success:
            success = self.topic.voice_label_expr(phrases)
            clz._logger.debug(f'voice_label_expr: {success}')
        if not success:
            success = self.voice_button_label(phrases)
            clz._logger.debug(f'voice_button_label: {success}')
        clz._logger.debug(f'{phrases}')
        return success

    def voice_button_label(self, phrases, control_id_expr: int | str | None = None) -> bool:
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
                button_cntrl: xbmcgui.ControlButton
                # clz._logger.debug(f'Getting control')
                button_cntrl = self.get_button_control(control_id)
                # clz._logger.debug(f'Getting Text')
                text = button_cntrl.getLabel()
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

    def __repr__(self) -> str:
        clz = type(self)
        clz = type(self)
        description_str: str = ''

        if self.description != '':
            description_str = f'\n description: {self.description}'

        visible_expr: str = ''
        if self.visible_expr != '':
            visible_expr = f'\n visible_expr: {self.visible_expr}'

        enable_str: str = ''
        if self.enable_expr != '':
            enable_str = f'\n enable_expr: {self.enable_expr}'

        if self.on_focus_expr != '':
            on_focus_expr: str = f'\n on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr != '':
            on_unfocus_expr: str = f'\n on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''

        label_expr: str = ''
        if self.label_expr != '':
            label_expr = f'\n label_expr: {self.label_expr}'

        alt_label_expr: str = ''
        if self.alt_label_expr != '':
            alt_label_expr = f'\n alt_label_expr: {self.alt_label_expr}'

        hint_text_str: str = ''
        if self.hint_text_expr != '':
            hint_text_str = f'\n hint_text: {self.hint_text_expr}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nButtonModel type: {self.control_type} '
                       f'id: {self.control_id} '
                       f'{description_str}'
                       f'{visible_expr}{label_expr}{alt_label_expr}{hint_text_str}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'\n wrap_multiline: {self.wrap_multiline}'
                       f'{topic_str}'
                       f'\n #children: {len(self.children)}')
        results.append(result)

        for child in self.children:
            child: BaseParser
            results.append(str(child))
        results.append(f'END ButtonModel')

        return '\n'.join(results)
