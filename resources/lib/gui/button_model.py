# coding=utf-8

from typing import Callable, List

import xbmc
import xbmcgui

from common.logger import BasicLogger
from common.phrases import Phrase, PhraseList
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlElement, Item
from gui.button_topic_model import ButtonTopicModel
from gui.element_parser import ElementHandler
from gui.no_topic_models import NoButtonTopicModel
from gui.parser.parse_button import ParseButton
from gui.topic_model import TopicModel
from utils import util
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class ButtonModel(BaseLabelModel):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.BUTTON]

    def __init__(self, parent: BaseModel, parsed_button: ParseButton) -> None:
        clz = ButtonModel
        if clz._logger is None:
            clz._logger = module_logger
        super().__init__(window_model=parent.window_model, parser=parsed_button)
        self.attributes_with_values: List[str] = clz.item.attributes_with_values
        self.attributes: List[str] = clz.item.attributes
        self.visible_expr: str = ''
        self.label_expr: str = ''
        self.wrap_multiline: bool = False
        self.description: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.enable_expr: str = ''

        self.convert(parsed_button)

    def convert(self, parsed_button: ParseButton) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_button: A ParseButton instance that
               needs to be converted to a ButtonModel
        :return:
        """
        clz = ButtonModel
        self.visible_expr = parsed_button.visible_expr
        self.wrap_multiline = parsed_button.wrap_multiline
        # self.attributes_with_values: List[str]
        # self.attributes: List[str]
        self.label_expr = parsed_button.label_expr
        self.description = parsed_button.description
        self.enable_expr = parsed_button.enable_expr

        if parsed_button.topic is not None:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            self.topic = ButtonTopicModel(self, parsed_button.topic)
        else:
            self.topic = NoButtonTopicModel(self)
        for child in parsed_button.children:
            child: BaseParser
            model_handler:  Callable[[BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
            self.children.append(child_model)

    @property
    def supports_label(self) -> bool:
        # ControlCapabilities.LABEL
        return True

    @property
    def supports_label2(self) -> bool:
        #  ControlCapabilities.LABEL2
        return False

    @property
    def supports_value(self) -> bool:
        """
        This control is unable to provide a value. I.E. it can't give any
        indication of what happens when pressed. If the topic for this
        control or another provides flows_from/flows_to or similar, then a
        value can be determined that way, but not using this method.
        :return:
        """
        return False

    def voice_control(self, phrases: PhraseList) -> bool:
        """

        :param phrases: PhraseList to append to
        :return: True if anything appended to phrases, otherwise False
        """
        clz = ButtonModel

        if self.control_id is not None:
            if not self.is_visible():
                clz._logger.debug(f'not visible, exiting')
                return False

        focus_changed = self.windialog_state.focus_changed
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
            temp_phrases: PhraseList = PhraseList(check_expired=False)
            success = topic.voice_topic_value(temp_phrases)
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
        clz = ButtonModel
        success: bool = False
        success = self.voice_control_name(phrases)
        if self.topic is None:
            return self.voice_heading_without_topic(phrases)

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
        clz = ButtonModel
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
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False):
        clz = ButtonModel
        clz = ButtonModel
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

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nButtonModel type: {self.control_type} '
                       f'id: {self.control_id} '
                       f'{description_str}'
                       f'{visible_expr}{label_expr}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'\n wrap_multiline: {self.wrap_multiline}'
                       f'{topic_str}'
                       f'\n #children: {len(self.children)}')
        results.append(result)

        if include_children:
            for child in self.children:
                child: BaseModel
                results.append(str(child))
        results.append(f'END ButtonModel')

        return '\n'.join(results)
