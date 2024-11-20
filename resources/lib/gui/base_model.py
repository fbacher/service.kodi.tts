# coding=utf-8
from __future__ import annotations

from logging import DEBUG
from typing import Dict, ForwardRef, List, Tuple, Union

import xbmc
import xbmcgui

from common.constants import Constants
from common.logger import BasicLogger, DEBUG_V, DISABLED
from common.message_ids import MessageId, MessageUtils
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_tags import ControlElement, Requires, WindowType

from gui.base_parser import BaseParser
from gui.i_model import IModel
from gui.interfaces import IWindowStructure
from gui.statements import Statement, Statements, StatementType
from utils import util
from windows.ui_constants import AltCtrlType, UIConstants
from windows.window_state_monitor import WinDialogState

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class BaseModel(IModel):

    def __init__(self, window_model: ForwardRef('BaseModel'),
                 parser: BaseParser, windialog_state: WinDialogState | None) -> None:
        super().__init__()
        clz = BaseModel

        MY_LOGGER.debug(f'Entering BaseModel Parser: {type(parser)}')
        self._window_model: ForwardRef('WindowModel') = window_model

        self._control_id: int = parser.control_id
        #  self._window_id: int | None = None
        self._window_struct: IWindowStructure = None
        self._control_type: ControlElement = parser.control_type
        #  MY_LOGGER.debug(f'initial control_type: {self._control_type} '
        #                   f'control_id: {self._control_id}')
        self._tree_id: str = f'JUNK'
        self._topic: ForwardRef('TopicModel') = None
        self._root_topic: ForwardRef('WindowTopicModel') = None
        self._topic_checked: bool = False
        # Default msg_id for controls which return a boolean (such as a
        # RadioButton). The value should be tailored for the control.
        # Here, we choose simply 'True' and 'False'. Controls can override.
        # If using Topics, the values can be specified there.
        self.default_true_msg_id: int = MessageId.TRUE.value
        self.default_false_msg_id: int = MessageId.FALSE.value
        # Parent models can specify that the topic MUST have something defined.
        # Example, Sliders require that it's topic MUST define the units, scale,
        # etc. for the slider, since there is no way to get this from kodi api
        self._requires: List[Requires] = []
        self._children: List[BaseModel] = []

    @property
    def control_id(self) -> int:
        clz = type(self)
        # MY_LOGGER.debug(f'self: {self.__class__.__name__} '
        #                   f'control_id: {self._control_id}')
        return self._control_id

    @property
    def window_id(self) -> int:
        return self.window_model.windialog_state.window_id

    @property
    def window_struct(self) -> IWindowStructure:
        MY_LOGGER.debug(f'_window_model: {self._window_model is None}')
        return self.window_model.window_struct

    @property
    def windialog_state(self) -> WinDialogState:
        MY_LOGGER.debug(f'window_model is None: {self._window_model is None}')
        if self._window_model is not None:
            MY_LOGGER.debug(f'windialog_state is None:'
                            f' {self._window_model.windialog_state is None}')
        return self._window_model.windialog_state

    # @property
    # def parent(self) -> ForwardRef('BaseModel'):
    #     return self._parent

    """
        Properties about the capabilities of its control. These are defaults.
        Controls needing to override simply supply the same property, but with
        different return value
        
    """

    @property
    def supports_label(self) -> bool:
        """
            A control which getLabel or at least Control.GetLabel({control_id})
            work.
        :return:
        """
        # ControlCapabilities.LABEL

        return True

    @property
    def supports_label2(self) -> bool:
        """
         A control which getLabel2 or at least Control.GetLabel({control_id}.index(1))
            work.
        :return:
        """
        #  ControlCapabilities.LABEL2

        return False

    @property
    def supports_value(self) -> bool:
        """
        Some controls can not report any value, that is, it can't give any
        indication of what happens when pressed. If the topic for this
        control or another provides flows_from/flows_to or similar, then a
        value can be determined that way, but not using this method.
        :return:
        """
        return True

    @property
    def supports_boolean_value(self) -> bool:
        """
        Some controls, such as RadioButton, support a boolean value
        (on/off, disabled/enabled, True/False, etc.). Such controls
        Use the value "(*)" to indicate True and "( )" to indicate False.
        :return:
        """
        return False

    @property
    def true_value(self) -> str:
        clz = BaseModel
        if not self.supports_boolean_value:
            raise ValueError('Does not support boolean value')
        true_msg: str = ''
        if self.topic is not None:
            true_msg = self.topic.true_value
        else:
            true_msg = MessageUtils.get_msg(self.default_true_msg_id)
        MY_LOGGER.debug(f'true_msg: {true_msg}')
        return true_msg

    @property
    def false_value(self) -> str:
        if not self.supports_boolean_value:
            raise ValueError('Does not support boolean value')
        false_msg: str = ''
        if self.topic is not None:
            false_msg = self.topic.false_value
        else:
            false_msg = MessageUtils.get_msg(self.default_false_msg_id)
        return false_msg

    @property
    def supports_heading_label(self) -> bool:
        """
            A control that defaults to using its label as a heading
        :return:
        """
        # ControlCapabilities.LABEL

        return True

    @property
    def supports_label_value(self) -> bool:
        """
            A control with a label that is frequently used as a value
        :return:
        """
        # ControlCapabilities.LABEL

        return False

    @property
    def supports_label2_value(self) -> bool:
        """
         A control that supports label2 that is frequently used as a value.

        :return:
        """
        #  ControlCapabilities.LABEL2

        return False

    @property
    def supports_container(self) -> bool:
        """
           Only a few controls are containers and even then, some don't fully
           support containers.

           Known Containers
               FixedList?, List, Panel, WrapList
           Known semi-containers
               GroupList
           :return:
        """
        return False

    @property
    def supports_orientation(self) -> bool:
        """
           List-type controls support orientation (vertical or horizontal)

           Known Containers
               FixedList?, List, Panel, WrapList
           Known semi-containers
               GroupList
           :return:
        """
        return False

    @property
    def supports_item_count(self) -> bool:
        """
           Indicates if the country supports item_count. List type containers/
           controls, such as GroupList do

           :return:
        """
        return False

    @property
    def supports_item_number(self) -> bool:
        """
            Indicates if the control supports reporting the current item number.
            The list control is not capable of these, although it supports
            item_count.
        :return:
        """
        return False

    @property
    def supports_change_without_focus_change(self) -> bool:
        """
            Indicates if the control supports changes that can occur without
            a change in Focus. Slider is an example. User modifies value without
            leaving the container. Further, you only want to voice the value,
            not the control name, etc.
        :return:
        """
        return False

    @property
    def topic(self) -> ForwardRef('BaseTopicModel'):
        return self._topic

    @topic.setter
    def topic(self, new_topic: ForwardRef('BaseTopicModel')):
        clz = ForwardRef('BaseModel')
        """
        MY_LOGGER.debug(f'self: {self.__class__.__name__} '
                          f'parent: {self.parent.__class__.__name__} '
                          f'control_id: {self.parent.control_id} '
                          f'new_value: {new_control_id}')
        """
        self._topic = new_topic

    @property
    def root_topic(self) -> ForwardRef('RootTopicModel') | None:
        """
        Returns the root_topic node for this window/dialog.
        The root topic represents the Window/Dialog

        :return:
        """
        return self._root_topic

    @property
    def window_model(self) -> ForwardRef('WindowModel'):
        return self._window_model

    @property
    def focus_changed(self) -> bool:
        return self.window_model.windialog_state.focus_changed

    @property
    def control_type(self) -> ControlElement:
        return self._control_type

    @property
    def tree_id(self) -> str:
        return self._tree_id

    @tree_id.setter
    def tree_id(self, new_tree_id: str):
        self._tree_id = new_tree_id

    @property
    def topic_checked(self) -> bool:
        return self._topic_checked

    @topic_checked.setter
    def topic_checked(self, checked: bool) -> None:
        self._topic_checked = checked

    @property
    def requires(self) -> List[Requires]:
        return self._requires

    @property
    def children(self) -> List[ForwardRef('BaseModel')]:
        return self._children

    '''
    @control_id.setter
    def control_id(self, new_control_id):
        clz = type(self)
        MY_LOGGER.debug(f'self: {self.__class__.__name__} '
                          f'parent: {self.parent.__class__.__name__} '
                          f'control_id: {self.parent.control_id} '
                          f'new_value: {new_control_id}')
        self.parent.control_id = new_control_id
    '''

    def voice_control(self, stmts: Statements) -> bool:
        """

        :param stmts: Statements to append to
        :return: True if anything appended to phrases, otherwise False
        """
        clz = BaseModel
        # TODO, incomplete
        return False

    def voice_label_heading(self, stmts: Statements) -> bool:
        """
        Voices a Control's label as the heading

        :param stmts:
        :return:
        """
        if not self.supports_heading_label:
            return False
        return self.voice_label(stmts)

    def get_real_topic(self) -> ForwardRef('BaseTopicModel'):
        """
          Returns a valid (not fake), new style topic or None

        :return:
        """
        if self.topic is None:
            return None
        if not self.topic.is_new_topic or not self.topic.is_real_topic:
            return None
        return self.topic

    def get_control_name(self) -> str:
        clz = BaseModel
        control_name: str = ''
        if self.topic is not None:
            control_name = self.topic.get_alt_control_name()
        if control_name == '':
            control_type: AltCtrlType
            control_type = AltCtrlType.get_default_alt_ctrl_type(self.control_type)
            control_name = Messages.get_msg_by_id(control_type.value)
            MY_LOGGER.debug(f'control_name: {control_name}')
        return control_name

    def voice_control_name(self, stmts: Statements) -> bool:
        clz = BaseModel
        success: bool = False
        control_name: str = self.get_control_name()
        stmts.last.phrases.append(Phrase(text=control_name, check_expired=False))
        return success

    def voice_control_heading(self, stmts: Statements) -> bool:
        clz = BaseModel
        success: bool = False
        success = self.voice_labeled_by(stmts)
        if not success:
            success = self.voice_label_expr(stmts)
        success = self.voice_chained_controls(stmts)
        return success

    def voice_value(self, stmts: Statements) -> bool:
        return False

    def get_item_number(self, control_id: int | None = None) -> int:
        """
        Used to get the current item number from a List type topic. Called from
        a child topicof the list

        :param control_id: optional id of the control to query. Defaults to
                           the currently focused control
        :return: Current topic number, or -1
        """
        return -1

    def voice_item_number(self, stmts: Statements) -> bool:
        """
        Called at the end of voicing a list type of control in order to voice
        the item number of one of the list's child controls.

        :param stmts: Any voiced text is appended to this
        :return: True if something was voiced, otherwise False

        The current topic is for the list-type control which has just been
        voiced. Before "direct_voicing_topics" voices a child item of this
        list, voice its item_number.

        Note that eeach time an item of this list is voiced, this list control
        will be revisited for voicing. Usually nothing is voiced since the
        voicing of the list control will have not changed and therefore
        supressed from voicing. The item number will change for each child.

        """
        return False

    def get_working_value(self, item_number: int) -> float | List[str]:
        """
            Gets the intermediate value of this control. Used for controls where
            the value is entered over time, such as a list container where
            you can scroll through your choices (via cursor up/down, etc.)
            without changing focus.

            The control's focus does not change so the value must be checked
            as long as the focus remains on the control. Further, the user wants
            to hear changes as they are being made and does not want to hear
            extra verbage, such as headings.

        :param item_number: 1-based item number
        :return: List of values from the current item_number and from the
                 first item_layout and focused_layout with a passing condition.
        """
        return ['Not implemented']

    def get_orientation(self) -> str:
        clz = BaseModel
        return ''

    def voice_active_item_value(self, stmts: Statements) -> bool:
        """
        Only used when chain of Topics are not available from Window to
         focused/active control.

        :param stmts:
        :return:
        """
        return False

    def voice_labeled_by(self, stmts: Statements) -> bool:
        """
        Voice this control's label
        A topic's labeled_by says to get the label for this control from somewhere
        else. The labeled_by_expr may be one of:
                 A control_id (must be numeric)  TODO: Consider allowing an int-sting
                 A topic name another topic to get the label from
                 A tree_id (dynamically created when window defined) TODO: implement

        :param stmts:
        :return:
        """
        # Needs work
        clz = BaseModel
        success: bool = False
        MY_LOGGER.debug(f'In voice_labeled_by')
        if self.topic.labeled_by_expr != '':
            control_id: int = util.get_non_negative_int(self.topic.labeled_by_expr)
            if control_id == -1:
                MY_LOGGER.debug(
                    f"Can't find labeled by for {self.topic.labeled_by_expr}")
                return False
            label_cntrl: BaseModel
            label_cntrl = self.window_model.get_control_model(control_id)
            label_cntrl: ForwardRef('LabelModel')
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'labeled_by: {self.topic.labeled_by_expr}')
            if label_cntrl is not None:
                control_type: ControlElement = label_cntrl.control_type
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'label_cntrl: {control_type}')
                if label_cntrl.control_type != ControlElement.LABEL_CONTROL:
                    success = label_cntrl.voice_labels(stmts)  # Label and Label 2
                else:
                    success = label_cntrl.voice_label(stmts)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{stmts.last.phrases}')
        return success

    def voice_heading_without_topic(self, stmts: Statements) -> bool:
        stmts.last.phrases.append(
                Phrase(text='voice_heading_without_topic not implemented',
                       check_expired=False))
        return True

    def voice_labels(self, stmts: Statements, voice_label: bool = True,
                     voice_label_2: bool = True) -> bool:
        """
            Voices label as well as label_2, if it is supported

          :param stmts: Any found text is appended to this
          :param voice_label: Voice the label, if supportted by control
          :param voice_label_2 Voice label_2, if supported by control
          :return:
          """
        clz = BaseModel
        # Control ID should be an integer
        success: bool = False
        control_id: int = self.control_id

        if control_id > 0:
            try:
                success = self.voice_label_ll(stmts, label_expr=str(control_id),
                                              label_1=self.supports_label,
                                              label_2=self.supports_label2)
            except ValueError as e:
                success = False
            except Exception:
                MY_LOGGER.exception('')
        return success

    def voice_label(self, stmts: Statements,
                    control_id_expr: int | str | None = None,
                    stmt_type: StatementType = StatementType.NORMAL) -> bool:
        """
        Voices the label of a control
        :param stmts: Any found text is appended to stmts
        :param control_id_expr:  If non-None, then used as the control_id instead
               of self.control_id
        :param stmt_type StatementType to assign any voiced Statements
        :return:
        """
        clz = BaseModel
        # Control ID should be an integer
        success: bool = False
        control_id: int = self.control_id
        if control_id_expr is None:
            control_id_expr = str(self.control_id)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'control_id_expr: {control_id_expr}')
        if control_id != -1:
            try:
                success = self.voice_label_ll(stmts, label_expr=control_id_expr,
                                              stmt_type=stmt_type)
            except ValueError as e:
                success = False
            except Exception:
                MY_LOGGER.exception('')
        return success

    def voice_label2(self, stmts: Statements,
                     control_id_expr: int | str | None = None,
                     stmt_type: StatementType = StatementType.NORMAL) -> bool:
        # ONY works for edit controls (NOT ControlLabel). Lies when there is
        # no label2 and simply returns label.

        clz = BaseModel
        # Control ID should be an integer
        success: bool = False
        control_id: int = -1
        if control_id_expr is not None:
            control_id = util.get_non_negative_int(control_id_expr)
        else:
            control_id = self.control_id
        if self.control_id != -1:
            try:
                query: str = f'Control.GetLabel({control_id}.index(1))'
                text: str = xbmc.getInfoLabel(query)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Text: {text}')
                if text != '':
                    stmts.last.phrases.append(Phrase(text=text, check_expired=False))
                    success = True
            except ValueError as e:
                success = False
        return success

    def voice_label_value(self, stmts: Statements,
                    control_id_expr: int | str | None = None,
                    stmt_type: StatementType = StatementType.NORMAL) -> bool:
        """
            Voices this control's label as the value of the control.
            Generally, when voicing something like a RadioButton the label
            is part of the heading for the control while label2 is the
            value of the RaioButton. Further, at least in english, the
            heading is usually voiced before the value.

        :param stmts: Any found text is appended to stmts
        :param control_id_expr:  If non-None, then used as the control_id instead
               of self.control_id
        :param stmt_type StatementType to assign any voiced Statements
        :return:
        """
        clz = BaseModel
        # Control ID should be an integer
        success: bool = False
        control_id: int = self.control_id
        if control_id_expr is None:
            control_id_expr = str(self.control_id)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'control_id_expr: {control_id_expr}')
        if control_id != -1:
            try:
                success = self.voice_label_ll(stmts, label_expr=control_id_expr,
                                              stmt_type=stmt_type)
            except ValueError as e:
                success = False
            except Exception:
                MY_LOGGER.exception('')
        return success

    def voice_label2_value(self, stmts: Statements,
                           control_id_expr: int | str | None = None,
                           stmt_type: StatementType = StatementType.VALUE) -> bool:
        """
            Voices any label2 value as this control's value

        :param stmts:
        :param control_id_expr:
        :param stmt_type:
        :return:
        """
        clz = BaseModel
        # Control ID should be an integer
        success: bool = False
        control_id: int = -1
        if control_id_expr is not None:
            control_id = util.get_non_negative_int(control_id_expr)
        else:
            control_id = self.control_id
        if self.control_id != -1:
            try:
                query: str = f'Control.GetLabel({control_id}.index(1))'
                text: str = xbmc.getInfoLabel(query)
                bool_text: str = ''
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Text: {text}')
                if text != '':
                    if self.supports_boolean_value:
                        is_true: bool
                        new_text: str
                        is_true, new_text = self.is_true(text)
                        MY_LOGGER.debug(f'is_true: {is_true}')
                        if is_true is not None:
                            if is_true:
                                bool_text = self.true_value
                            else:
                                bool_text = self.false_value
                    MY_LOGGER.debug(f'bool_text: {bool_text}')
                    stmt: Statement = Statement(
                            PhraseList.create(texts=bool_text, check_expired=False),
                            stmt_type=stmt_type)
                    stmts.append(stmt)
                    success = True
            except ValueError as e:
                MY_LOGGER.exception('')
                success = False
        return success

    def voice_control_value(self, stmts: Statements,
                            control_id: int | None = None) -> bool:
        """
        Gets the value from a control.
        Depending upon the control, it may have one or two labels. When there
        are two labels, the value is usually label_2

        :param stmts:
        :param control_id:
        :return:
        """
        success: bool = False
        clz = BaseModel
        if MY_LOGGER.isEnabledFor(DISABLED):
            MY_LOGGER.debug_v(f'control_id: {control_id} self.control_id: {self.control_id}')
        if control_id is None:
            control_id = self.control_id

        label_1: bool = True
        if self.supports_label2:
            label_1 = False
        success = self.voice_label_ll(stmts, label_expr=str(control_id),
                                      label_1=label_1, label_2=True)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'{stmts.last.phrases}')
        return success

    def visible_item_count(self) -> int:
        clz = BaseModel
        if not self.supports_item_count:
            return -1
        # Can specify the control_id, but assume we have focus
        container_id: str = f'{self.control_id}'
        num_items_str: str = xbmc.getInfoLabel(f'Container({container_id}).NumItems')
        #  MY_LOGGER.debug(f'num_items_str: {num_items_str}')
        if num_items_str.isdigit():
            return int(num_items_str)
        return -1

    def get_info_label(self, label_expr: str) -> str | None:
        """
           Queries xbmc for the value of the given Info Label.

        :param label_expr:  A Kodi info-label or list-item expression

        :return: True if one or more statements was found and added
        """
        clz = BaseModel
        if label_expr == '':
            return None
        try:
            if label_expr.startswith('$LOCALIZE'):
                label_expr = label_expr[10:-1]
                if label_expr.isdigit():
                    label_num: int = int(label_expr)
                    text = MessageUtils.get_msg_by_id(label_num)
                    return text
                else:
                    MY_LOGGER.debug(f'ERROR: expected $LOCALIZE to contain '
                                      f'a number not: {label_expr}')
                    return ''
        except ValueError:
            MY_LOGGER.exception('')
            return ''

        if label_expr.startswith('$INFO['):
            label_expr = label_expr[6:-1]
        try:
            text = xbmc.getInfoLabel(f'{label_expr}')
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'label_expr: {label_expr} = {text}')
        except ValueError as e:
            MY_LOGGER.exception('')
            text = ''

        '''
        if text == '':
            text = CriticalSettings.ADDON.getInfoLabel(label_expr)
            MY_LOGGER.debug(f'label_expr: {label_expr} = {text}')
        '''
        if text == '':
            MY_LOGGER.debug(f'Failed to get label_expr {label_expr}')
            return None
        return text

    """
        Useful Container/List functions
        container_id = 101
        pos_str: str = xbmc.getInfoLabel(f'Container({container_id}).Position')
        num_items_str: str = xbmc.getInfoLabel(f'Container({container_id}).NumItems')

        num_all_items_str: str = xbmc.getInfoLabel(
            f'Container({container_id}).NumAllItems')
        num_non_folder_items: str = xbmc.getInfoLabel(
            f'Container({container_id}).NumNonFolderItems')
        num_current_item: str = xbmc.getInfoLabel(
            f'Container({container_id}).CurrentItem')
        position_0: str = xbmc.getInfoLabel(f'Container({container_id}).Position(0)')
        has_focus_1: str = xbmc.getInfoLabel(f'Container({container_id}).HasFocus(1)')
        MY_LOGGER.debug(f'pos_str: {pos_str}'
                          f' num_items: {num_items_str}'
                          f' num_all_items: {num_all_items_str}'
                          f' num_non_folder_items: {num_non_folder_items}'
                          f' num_current_item: {num_current_item}'
                          f' position_0: {position_0}'
                          f' has_focus_1: {has_focus_1}')
    """
    """
        Difficult to handle children without focus/visibility (groups)
        item_count = 0
        for child in self.children:
            child: BaseModel
            MY_LOGGER.debug(f'count: {item_count} child: {child.control_id} '
                              f'topic: {child.topic} visible: {child.is_visible()}')
            if child.is_visible():
                item_count += 1
        return item_count
    """

    def is_true(self, text: str) -> Tuple[bool | None, str]:
        """
        Inspects text to see if it has Kodi's encoded boolean value at the end.
        '(*)' is True while '( )' is False. RadioButton returns an encoded bool
        in its Label2 value (even when the radiobutton is zero size).

        :param text: Text to examine
        :return: a Tuple with the
                  -first value of None, indicating no boolean code was found,
                   otherwise, the value is True if the embeded value was True
                  -second value is the value of text, with any embedded value
                   removed
        """
        clz = type(self)
        value: bool | None = None
        if text.endswith(')'):  # Skip this most of the time
            # For boolean settings
            if text.endswith('( )'):
                text = text[0:-4]
                value = False
            elif text.endswith('(*)'):
                text = text[0:-4]
                value = True
        return value, text

    def is_visible(self) -> bool:
        clz = BaseModel
        if self.control_id != -1:
            # WindowModel.control_id is the Window ID. We can't set the
            # window id using CondVisibility. Grrr

            #  MY_LOGGER.debug(f'is_visible control_id: {self.control_id}')
            return xbmc.getCondVisibility(f'Control.IsVisible({self.control_id})')

            # Can not use this on all control types (GroupList is one that blows up)
            # return WindowStateMonitor.is_visible(self.control_id,
            #                                      self.window_model.control_id)

    def sayText(self, stmts: Statements) -> None:
        """
        Used for voicing text when the request to voice came within the
        *_model and *topic_model classes (such as a call-back on a polling-thread
        to voice slider values).

        :param stmts:
        :return:
        """
        from service_worker import TTSService
        service = TTSService.instance
        service.sayText(stmts.as_phrases())

    def get_control_button(self, iControlId: int) -> xbmcgui.ControlButton:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.window_model.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlButton
        return control

    def get_control_edit(self, iControlId: int) -> xbmcgui.ControlEdit:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.window_model.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlEdit
        return control

    def get_control_group(self, iControlId: int) -> xbmcgui.ControlGroup:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.window_model.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlGroup
        return control

    def get_control_label(self, iControlId: int) -> xbmcgui.ControlLabel:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.window_model.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlLabel
        return control

    def get_control_radio_button(self, iControlId: int) -> xbmcgui.ControlRadioButton:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.window_model.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlRadioButton
        return control

    def get_control_slider(self, iControlId: int) -> xbmcgui.ControlSlider:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.window_model.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlSlider
        return control

    @classmethod
    def get_model_instance(cls) -> ForwardRef('BaseModel'):
        pass

    def get_msg_id_for_str(self, msg_expr: str) -> int:
        """
               Attempts to convert control_expr to an int

               :param msg_expr: String representation of a msg id
               :return: msg_expr converted to a positive int or
                        -1 if msg_expr is not a positive int

               """
        value: int = -1
        try:
            value = int(msg_expr)
            if value <= 0:
                value = -1
        except ValueError:
            value = -1
        return value

    def get_control(self, control_id: int) -> xbmcgui.Control:
        clz = BaseModel
        window: xbmcgui.Window | xbmcgui.WindowDialog = self.window_model.win_or_dialog
        MY_LOGGER.debug(f'control_id: {control_id}')
        control: xbmcgui.Control = window.getControl(control_id)
        # MY_LOGGER.debug(f'control: {control}')
        return control

    def get_label_control(self, control_id: int) -> xbmcgui.ControlLabel:
        clz = BaseModel
        MY_LOGGER.debug(f'control_id: {control_id}')
        control: xbmcgui.Control
        control = self.get_control(control_id)
        control: xbmcgui.ControlLabel
        return control

    def get_button_control(self, control_id: int) -> xbmcgui.ControlButton | None:
        clz = BaseModel
        MY_LOGGER.debug(f'control_id: {control_id}')
        control: xbmcgui.Control
        try:
            control = self.get_control(control_id)
        except Exception as e:
            MY_LOGGER.exception('')
            control = None
        control: xbmcgui.ControlButton
        return control

    '''
    def convertElements(self,
                        elements: List[BaseParser]) -> None:
        for element in elements:
            element: BaseParser
            key: str = element.item.keyword
            if key == 'visible':
                self.visible_expr: str = element.visible_expr
    '''

    def get_current_label_value(self, stmts: Statements, clean_string: bool) -> bool:
        """
        Return this label's value. Which can sometimes be a real chore.

        :param stmts append any resulting string to
        :param clean_string if True then 'clean' the string using
        :return:
        """
        text = xbmc.getInfoLabel('System.CurrentControl')

        return False

    def voice_label_ll(self, stmts: Statements, label_expr: str | None,
                       label_1: bool = True, label_2: bool = False,
                       stmt_type: StatementType = StatementType.NORMAL) -> bool:
        """
            Converts a label expression which may be a simple integer string
            or an infoList expression, etc.

        :param stmts Any resulting label or list item text is added to this
        :param label_expr: used for label query
        :param label_1: If True then return the value of getLabel
        :param label_2: If True, and the control supports label 2, then return
                        its value
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
        if text_1 is not None and text_1 != '':
            stmts.append(Statement(PhraseList.create(texts=text_1,
                                                     check_expired=False),
                                   stmt_type=stmt_type))
            success_1 = True
        if text_2 is not None and text_2 != '':
            success_2 = True
            if text_1 != '':
                stmts.last.phrases.add_text(texts=text_2)
            else:
                stmts.append(Statement(PhraseList.create(texts=text_2,
                                                         check_expired=False),
                                       stmt_type=stmt_type))
        return success_1 or success_2

    def get_label_ll(self, label_expr: str | None,
                     label_1: bool = True, label_2: bool = False,
                     ) -> Tuple[str | None, str | None]:
        """
            Converts a label expression which may be a simple integer string
            or an infoList expression, etc.

        :param label_expr: used for label query
        :param label_1: If True then return the value of getLabel
        :param label_2: If True, and the control supports label 2, then return
                        its value
        :return: Values of label_1 and label_2, or None for each that
                does not have a volue
        """
        clz = BaseModel
        text: str = ''

        """
         The control_id_expr can contain:
             A control_id (must be all numeric)
             A info-label type expression: begins with $INFO or $PROP, $LOCALIZE.
             A complex expression:
               $INFO[MusicPlayer.Artist,$LOCALIZE[557]: ,:] $INFO[Player.Title,$LOCALIZE[369]: ,:]
        
        For now, will ignore complex parsing. 
        
        For complex parsing, see window.windowparser.extractInfos. It basically 
        parses bracket ('[]') nested text in a query into seperate queries
        
        The result of the query can need clenup. The result can contain embedded
        color, text style, etc. See window.ui_constants it contains some regular
        expressions
        """
        clz = BaseModel
        MY_LOGGER.debug(f'label_1: {label_1} label_2: {label_2} '
                          f'label_expr: {label_expr}\n '
                          f'supports_label_1: {self.supports_label} '
                          f'supports_label_2: {self.supports_label2}')
        if not (label_1 or label_2):
            return None, None,

        control_id: int | None = None
        if label_expr is not None:
            if isinstance(label_expr, int):
                control_id = label_expr
                if control_id < 0:
                    return None, None
            elif label_expr.isdigit():
                control_id = int(label_expr)
                if control_id <= 0:
                    return None, None
        else:
            control_id = self.control_id

        query_1: str = ''
        query_2: str = ''
        text_1: str = ''
        text_2: str = ''
        if control_id is not None:
            if label_1 and self.supports_label:
                query_1 = f'Control.GetLabel({control_id})'
            if label_2 and self.supports_label2:
                query_2 = f'Control.GetLabel({control_id}.index(1))'

        elif label_expr.startswith('$INFO['):  # ex: $INFO[System.Time]
            query_1: str = f'Control.GetLabel({label_expr[6:-1]})'
        # A tts invention. A window Property query
        elif label_expr.startswith('$PROP['):
            info: str = label_expr[6:-1]
            query_1 = f'Window().Property({info})'
        if query_1 != '' and label_1:
            try:
                text_1 = xbmc.getInfoLabel(f'{query_1}')  # TODO: May require post-processing
                text_1 = text_1.strip()
                visible: bool = xbmc.getCondVisibility(f'Control.IsVisible({control_id})')
                MY_LOGGER.debug(f'query_1: {query_1} text_1: {text_1} visible {visible}')
                MY_LOGGER.debug(f'text_2: {text_2}')
            except:
                MY_LOGGER.exception(f'control_expr: {query_1} label_1')
        if query_2 != '' and label_2:
            try:
                text_2 = xbmc.getInfoLabel(query_2)  # TODO: May require post-processing
                text_2 = text_2.strip()
            except:
                MY_LOGGER.exception(f'control_expr: {query_2} label_1')

        if text_1 != '' or text_2 != '':
            MY_LOGGER.debug(f'text_1: {text_1} text_2: {text_2}')
        return text_1, text_2

    def get_info_label_ll(self, stmts: Statements, query: str) -> bool:
        """
        Tries to get the value of a label using an info-label query

        :param stmts: To append any result to
        :param query: An info-label style query for the label control
        :return:
        """
        clz = BaseModel
        if query != '':
            try:
                text: str = xbmc.getInfoLabel(query)  # TODO: May require post-processing
                text = text.strip()
                if text != '':
                    stmts.append(Statement(PhraseList.create(texts=text,
                                                             check_expired=False)))
                return True
            except:
                MY_LOGGER.exception('')
        return False

    def to_string(self, include_children: bool = False) -> str:
        return ''
