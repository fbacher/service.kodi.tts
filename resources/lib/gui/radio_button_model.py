# coding=utf-8

from typing import Callable, List

import xbmc

from common.logger import BasicLogger, DEBUG_V
from common.messages import Messages
from common.phrases import Phrase
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlElement, Item
from gui.element_parser import (ElementHandler)
from gui.no_topic_models import NoRadioButtonTopicModel
from gui.parser.parse_radio_button import ParseRadioButton
from gui.radio_button_topic_model import RadioButtonTopicModel
from gui.statements import Statements
from gui.topic_model import TopicModel
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class NoRadioButonTopicModel:
    pass


class RadioButtonModel(BaseLabelModel):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.RADIO_BUTTON]

    def __init__(self, parent: BaseModel, parsed_radio_button: ParseRadioButton) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
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
        self._children: List[BaseModel] = []

        self.convert(parsed_radio_button)

    def convert(self, parsed_radio_button: ParseRadioButton) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_radio_button: A ParseButton instance that
               needs to be converted to a RadioButtonModel
        :return:
        """
        clz = type(self)
        self._control_type = parsed_radio_button.control_type
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
            self.topic = RadioButtonTopicModel(self, parsed_radio_button.topic)
        else:
            self.topic = NoRadioButtonTopicModel(self)
            if clz._logger.isEnabledFor(DEBUG_V):
                clz._logger.debug_v(f'# parsed children: '
                                          f'{len(parsed_radio_button.get_children())}')
        for child in parsed_radio_button.children:
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
        """
               RadioButton supports label2 dependent on its config. Will have to
               write code to determine at run time. True only with RadioButton having
               empty radiowidth and radioheight.
         """
        #  ControlCapabilities.LABEL2
        return False

    @property
    def supports_value(self) -> bool:
        """
        Some controls, such as a button, radio button or label are unable to provide a value.
        I.E. it can't give any indication of what happens when pressed. If the
        topic for this control or another provides flows_from/flows_to or similar,
        then a value can be determined that way, but not using this method.
        :return:
        """
        return False

    def voice_control(self, stmts: Statements) -> bool:
        """

        :param stmts: Statements to append to
        :return: True if anything appended to stmts, otherwise False
     """
        clz = type(self)
        focus_changed: bool = self.windialog_state.focus_changed
        success: bool = True
        if self.topic is not None:
            topic: TopicModel = self.topic
            if not focus_changed:
                success = self.voice_radio_button_value(stmts, focus_changed)
                return success
            success = self.voice_heading(stmts)
            success = self.voice_radio_button_label(stmts, focus_changed)

        # TODO, incomplete
        return success

    def voice_heading(self, stmts: Statements) -> bool:
        """

        :param stmts:
        :return: True if heading was appended to stmts, otherwise False
        """
        clz = type(self)
        success: bool = False
        success = self.voice_control_name(stmts)
        topic: TopicModel | None = self.topic
        return success

    def voice_radio_button_label(self, stmts: Statements, focus_changed) -> bool:
        clz = type(self)
        success = self.voice_labeled_by(stmts)
        clz._logger.debug(f'voice_labeled_by: {success}')
        if not success:
            success = self.topic.voice_alt_label(stmts)
        if not success:
            success = self.topic.voice_label_expr(stmts)
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
                    clz._logger.debug(f'text: {new_text} focus_changed: {focus_changed}')
                    if new_text != '' and focus_changed:
                        stmts.last.phrases.append(Phrase(text=new_text))
                except ValueError as e:
                    clz._logger.exception('')
                    pass
        return success

    def voice_radio_button_value(self, stmts, focus_changed: bool) -> bool:
        # Control ID should be an integer
        clz = type(self)
        success: bool = False
        if self.control_id != -1:
            try:
                query: str = f'Control.GetLabel({self.control_id}).index(0)'
                text: str = xbmc.getInfoLabel(query)
                # None is returned with no substitutions needed
                new_text: str = Messages.format_boolean(text=text)
                clz._logger.debug(f'text: {new_text} focus_changed: {focus_changed}')
                if new_text != '' and focus_changed:
                    stmts.last.phrases.append(Phrase(text=new_text))
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
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False) -> str:

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

        if include_children:
            for child in self.children:
                child: BaseModel
                result: str = child.to_string(include_children=include_children)
                results.append(result)
        results.append(f'END RadioButtonModel')
        return '\n'.join(results)
