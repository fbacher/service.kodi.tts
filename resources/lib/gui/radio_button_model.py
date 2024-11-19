# coding=utf-8

from typing import Callable, List, Tuple

import xbmc

from common.logger import BasicLogger, DEBUG_V, DISABLED
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlElement, Item
from gui.element_parser import (ElementHandler)
from gui.gui_globals import GuiGlobals
from gui.no_topic_models import NoRadioButtonTopicModel
from gui.parser.parse_radio_button import ParseRadioButton
from gui.radio_button_topic_model import RadioButtonTopicModel
from gui.statements import Statement, Statements, StatementType
from gui.topic_model import TopicModel
from windows.window_state_monitor import WinDialogState

MY_LOGGER = BasicLogger.get_logger(__name__)


class NoRadioButonTopicModel:
    pass


class RadioButtonModel(BaseLabelModel):

    item: Item = control_elements[ControlElement.RADIO_BUTTON]

    def __init__(self, parent: BaseModel, parsed_radio_button: ParseRadioButton,
                 windialog_state: WinDialogState | None = None) -> None:
        clz = type(self)
        super().__init__(parent.window_model, parsed_radio_button,
                         windialog_state=windialog_state)
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
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'# parsed children: '
                                          f'{len(parsed_radio_button.get_children())}')
        for child in parsed_radio_button.children:
            child: BaseParser
            model_handler:  Callable[[BaseModel, BaseParser, WinDialogState | None],
                                     BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child, None)
            self.children.append(child_model)

    @property
    def supports_label(self) -> bool:
        # ControlCapabilities.LABEL
        return True

    @property
    def supports_label_2(self) -> bool:
        return True

    @property
    def supports_label_2_label(self) -> bool:
        return False

    @property
    def supports_label2_value(self) -> bool:
        """
               RadioButton supports label2 dependent on its config. Will have to
               write code to determine at run time. There is a note from Kodi docs
               that RadioButton only supports this when the RadioButton is zero
               size. However, experiments show that when the RadioButton is
               non-zero and visible, the value of label2 is the same as for
               label, but with a suffix indicating the boolean state of the
               RadioButton. The suffix is '(*)' when True or '( )' when False
         """
        #  ControlCapabilities.LABEL2
        return True

    @property
    def supports_boolean_value(self) -> bool:
        """
        Some controls, such as RadioButton, support a boolean value
        (on/off, disabled/enabled, True/False, etc.). Such controls
        Use the value "(*)" to indicate True and "( )" to indicate False.
        :return:
        """
        return True

    @property
    def supports_value(self) -> bool:
        """
        Some controls, such as a button, radio button or label are unable to provide a value.
        I.E. it can't give any indication of what happens when pressed. If the
        topic for this control or another provides flows_from/flows_to or similar,
        then a value can be determined that way, but not using this method.
        :return:
        """
        return True

    @property
    def supports_change_without_focus_change(self) -> bool:
        """
            Indicates if the control supports changes that can occur without
            changes in Focus. Slider is an example. User modifies value without
            leaving the container. Further, you only want to voice the value,
            not the control name, etc.
        :return:
        """
        return True

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
            MY_LOGGER.debug('Hello!')
            if not focus_changed:
                success = self.voice_label2_value(stmts, focus_changed,
                                                  stmt_type=StatementType.VALUE)
                return success
            success = self.voice_radio_button_label(stmts, focus_changed)
            success = self.voice_label2_value(stmts, focus_changed,
                                              stmt_type=StatementType.VALUE)

        # TODO, incomplete
        return success

    '''
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
    '''
    def voice_radio_button_label(self, stmts: Statements, focus_changed) -> bool:
        clz = type(self)
        success = self.voice_labeled_by(stmts)
        MY_LOGGER.debug(f'voice_labeled_by: {success}')
        if not success:
            success = self.topic.voice_alt_label(stmts)
        if not success:
            success = self.topic.voice_label_expr(stmts)
            MY_LOGGER.debug(f'voice_label_expr: {success}')
        if not success:
            if self.control_id != -1:
                try:
                    query: str = f'Control.GetLabel({self.control_id}).index(0)'
                    text: str = xbmc.getInfoLabel(query)
                    # None is returned when no substitutions have been done on text
                    new_text: str = Messages.format_boolean(text=text)
                    if new_text is None:
                        new_text = ''
                    MY_LOGGER.debug(f'text: {new_text} focus_changed: {focus_changed}')
                    if new_text != '' and focus_changed:
                        stmts.last.phrases.append(Phrase(text=new_text,
                                                         check_expired=False))
                except ValueError as e:
                    MY_LOGGER.exception('')
                    pass
        return success

    def voice_label2_value(self, stmts: Statements,
                           control_id_expr: int | str | None = None,
                           stmt_type: StatementType = StatementType.VALUE) -> bool:
        """
            Extracts the radio button's boolean pressed state from the encoded
            suffix of label2. The suffix is either '(*)' (true) or '( )' (false).
            Further, if the topic has true_msg_id and false_msg_id, then
            the boolean value will be converted to the defined translated value.

        :param stmts:
        :param control_id_expr:
        :param stmt_type:
        :return:
         """
        # Control ID should be an integer
        clz = type(self)
        success: bool = False
        if self.control_id == -1:
            raise NotImplementedError(f'RadioButton Model net setup to handle '
                                      f'other control_Id\'s value')
        try:
            if self.supports_boolean_value:
                # RadioButtons ALL support boolean value (whether button
                # pressed or not). Translate to desired phrasing: On/Off, Yes/NO,
                # enabled/disabled, etc.
                text: str = xbmc.getInfoLabel(f'Control.GetLabel('
                                              f'{self.control_id}.index(1))')
                bool_text: str = ''
                is_true: bool
                new_text: str
                # is_true is None if text does not end with boolean indicator:
                # '(*)' (true)  or '( )' (false), otherwise it returns the
                # bool value of the indicator.
                # new_text is the boolean indicator, or None

                is_true, new_text = self.is_true(text)
                MY_LOGGER.debug(f'is_true: {is_true}')
                if is_true is not None:
                    if is_true:
                        bool_text = self.true_value
                    else:
                        bool_text = self.false_value
                previous_val: str = GuiGlobals.saved_states.get(
                        'radio_button_model_value')
                GuiGlobals.require_focus_change = False
                if previous_val is not None and previous_val == bool_text:
                    return False
                GuiGlobals.saved_states['radio_button_model_value'] = bool_text
                MY_LOGGER.debug(f'bool_text: {bool_text}')
                stmt: Statement = Statement(
                        PhraseList.create(texts=bool_text, check_expired=False),
                        stmt_type=stmt_type)
                stmts.append(stmt)
                success = True
        except ValueError as e:
            MY_LOGGER.exception('')
        return success

    def voice_label_ll(self, stmts: Statements, label_expr: str | None,
                       label_1: bool = True, label_2: bool = False,
                       stmt_type: StatementType = StatementType.NORMAL) -> bool:
        """
            Converts a label expression which may be a simple integer string
            or an infoList expression, etc.

        :param stmts Any resulting label or list item text is added to phrases
        :param label_expr: used for label query
        :param label_1: If True then return the value of getLabel
        :param label_2: If True, and the control supports label 2, then return
                        it's value
        :param stmt_type: StatementType to assign any Statements
        :return: True if any text added to phrases, otherwise False

        If both label and label_2 are False, then nothing is added to phrases.
        If both label1 and label2 are True, then both values of label and label_2
        are added to phrases.
        """
        clz = BaseModel
        text_1: str
        text_2: str
        success_1: bool = False
        success_2: bool = False
        text_1, text_2 = self.get_label_ll(label_expr, label_1, label_2)
        if text_1 != '':
            stmts.append(Statement(PhraseList.create(texts=text_1,
                                                     check_expired=False),
                                   stmt_type=stmt_type))
            success_1 = True
        if text_2 != '':
            success_2 = True
            if text_1 != '':
                stmts.last.phrases.add_text(texts=text_2)
            else:
                stmts.append(Statement(PhraseList.create(texts=text_2,
                                                         check_expired=False),
                                       stmt_type=stmt_type))
        return success_1 or success_2

    '''
    def format_bool_value(self, text: str, phrases: PhraseList, focus_changed: bool,
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
            MY_LOGGER.debug(f'text: {text} focus_changed: {focus_changed} '
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
