# coding=utf-8

from logging import DEBUG
from typing import Dict, ForwardRef, List, Tuple, Union

import xbmc
import xbmcgui

from common.logger import BasicLogger, DEBUG_V, DISABLED
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

module_logger = BasicLogger.get_logger(__name__)


class BaseModel(IModel):

    _logger: BasicLogger = module_logger

    def __init__(self, window_model: ForwardRef('BaseModel'),
                 parser: BaseParser) -> None:
        clz = BaseModel
        if clz._logger is None:
            clz._logger = module_logger

        self._windialog_state: WinDialogState | None = None
        self._window_model: ForwardRef('WindowModel') = window_model
        self._control_id: int = parser.control_id
        #  self._window_id: int | None = None
        self._window_struct: IWindowStructure = None
        self._control_type: ControlElement = parser.control_type
        self._tree_id: str = f'JUNK'
        self._topic: ForwardRef('TopicModel') = None
        self._root_topic: ForwardRef('WindowTopicModel') = None
        self._topic_checked: bool = False
        # Parent models can specify that the topic MUST have something defined.
        # Example, Sliders require that it's topic MUST define the units, scale,
        # etc. for the slider, since there is no way to get this from kodi api
        self._requires: List[Requires] = []
        self._children: List[BaseModel] = []

    @property
    def control_id(self) -> int:
        clz = type(self)
        # clz._logger.debug(f'self: {self.__class__.__name__} '
        #                   f'control_id: {self._control_id}')
        return self._control_id

    @property
    def window_id(self) -> int:
        return self.windialog_state.window_id

    @property
    def window_struct(self) -> IWindowStructure:
        return self._window_model.window_struct

    @property
    def windialog_state(self) -> WinDialogState:
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
    def supports_heading_label(self) -> bool:
        """
        Indicates whether this control provides a label which explains what it
        is for. For example, a button's label almost certainly is to explain
        why you should press it. On the other hand a label control does not.
        A label control may be displaying a date or the result of an action.
        More information is needed for controls like labels in order to know
        what to do with them.

        :return:
        """
        return True

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
    def supports_item_count(self) -> bool:
        """
           Indicates if the country supports item_count. List type containers/
           controls, such as GroupList do

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
        clz._logger.debug(f'self: {self.__class__.__name__} '
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
        return self.windialog_state.focus_changed

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
        clz._logger.debug(f'self: {self.__class__.__name__} '
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

    def voice_controls_heading(self, stmts: Statements) -> bool:
        stmts.last.phrases.append(Phrase(text='get_heading_without_text not implemented'))
        return True

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
        return control_name

    def voice_control_name(self, stmts: Statements) -> bool:
        clz = BaseModel
        success: bool = False
        control_name: str = self.get_control_name()
        stmts.last.phrases.append(Phrase(text=control_name))
        return success

    def voice_control_heading(self, stmts: Statements) -> bool:
        clz = BaseModel
        success: bool = False
        success = self.voice_labeled_by(stmts)
        if not success:
            success = self.voice_label_expr(stmts)
        success = self.voice_chained_controls(stmts)
        return success

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

    def voice_active_item(self, stmts: Statements) -> bool:
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
        clz._logger.debug(f'In voice_labeled_by')
        if self.topic.labeled_by_expr != '':
            control_id: int = util.get_non_negative_int(self.topic.labeled_by_expr)
            if control_id == -1:
                clz._logger.debug(
                    f"Can't find labeled by for {self.topic.labeled_by_expr}")
                return False
            label_cntrl: BaseModel
            label_cntrl = self.window_model.get_control_model(control_id)
            label_cntrl: ForwardRef('LabelModel')
            if clz._logger.isEnabledFor(DEBUG_V):
                clz._logger.debug_v(f'labeled_by: {self.topic.labeled_by_expr}')
            if label_cntrl is not None:
                control_type: str = label_cntrl.control_type
                if clz._logger.isEnabledFor(DEBUG_V):
                    clz._logger.debug_v(f'label_cntrl: {control_type}')
                if label_cntrl.control_type != ControlElement.LABEL_CONTROL:
                    success = label_cntrl.voice_labels(stmts)  # Label and Label 2
                else:
                    success = label_cntrl.voice_label(stmts)
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug(f'{stmts.last.phrases}')
        return success

    def voice_heading_without_topic(self, stmts: Statements) -> bool:
        stmts.last.phrases.append(
                Phrase(text='voice_heading_without_topic not implemented'))
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
                success = self.get_label_ll(stmts, label_expr=str(control_id),
                                            label_1=self.supports_label,
                                            label_2=self.supports_label2)
            except ValueError as e:
                success = False
            except Exception:
                clz._logger.exception('')
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
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug(f'control_id_expr: {control_id_expr}')
        if control_id != -1:
            try:
                success = self.get_label_ll(stmts, label_expr=control_id_expr,
                                            stmt_type=stmt_type)
            except ValueError as e:
                success = False
            except Exception:
                clz._logger.exception('')
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
                if clz._logger.isEnabledFor(DEBUG):
                    clz._logger.debug(f'Text: {text}')
                if text != '':
                    stmts.last.phrases.append(Phrase(text=text))
                    success = True
            except ValueError as e:
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
        if clz._logger.isEnabledFor(DISABLED):
            clz._logger.debug_v(f'control_id: {control_id} self.control_id: {self.control_id}')
        if control_id is None:
            control_id = self.control_id

        label_1: bool = True
        if self.supports_label2:
            label_1 = False
        success = self.get_label_ll(stmts, label_expr=str(control_id),
                                    label_1=label_1,  label_2=True)
        if clz._logger.isEnabledFor(DEBUG_V):
            clz._logger.debug_v(f'{stmts.last.phrases}')
        return success

    def visible_item_count(self) -> int:
        clz = BaseModel
        if not self.supports_item_count:
            return -1
        # Can specify the control_id, but assume we have focus
        container_id: str = f'{self.control_id}'
        num_items_str: str = xbmc.getInfoLabel(f'Container({container_id}).NumItems')
        #  clz._logger.debug(f'num_items_str: {num_items_str}')
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
        if label_expr.startswith('$INFO['):
            label_expr = label_expr[6:-1]
        try:
            text = xbmc.getInfoLabel(f'{label_expr}')
            if clz._logger.isEnabledFor(DEBUG):
                clz._logger.debug(f'label_expr: {label_expr} = {text}')
        except ValueError as e:
            clz._logger.exception('')
            text = ''

        '''
        if text == '':
            text = CriticalSettings.ADDON.getInfoLabel(label_expr)
            clz._logger.debug(f'label_expr: {label_expr} = {text}')
        '''
        if text == '':
            clz._logger.debug(f'Failed to get label_expr {label_expr}')
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
        clz._logger.debug(f'pos_str: {pos_str}'
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
            clz._logger.debug(f'count: {item_count} child: {child.control_id} '
                              f'topic: {child.topic} visible: {child.is_visible()}')
            if child.is_visible():
                item_count += 1
        return item_count
    """

    def is_visible(self) -> bool:
        clz = BaseModel
        if self.control_id != -1:
            # WindowModel.control_id is the Window ID. We can't set the
            # window id using CondVisibility. Grrr

            #  clz._logger.debug(f'is_visible control_id: {self.control_id}')
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
        control = self.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlButton
        return control

    def get_control_edit(self, iControlId: int) -> xbmcgui.ControlEdit:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlEdit
        return control

    def get_control_group(self, iControlId: int) -> xbmcgui.ControlGroup:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlGroup
        return control

    def get_control_label(self, iControlId: int) -> xbmcgui.ControlLabel:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlLabel
        return control

    def get_control_radio_button(self, iControlId: int) -> xbmcgui.ControlRadioButton:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.windialog_state.window_instance.getControl(iControlId)
        control: xbmcgui.ControlRadioButton
        return control

    def get_control_slider(self, iControlId: int) -> xbmcgui.ControlSlider:
        """

        :param iControlId:
        :return:
        """
        control: xbmcgui.Control
        control = self.windialog_state.window_instance.getControl(iControlId)
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
        clz._logger.debug(f'control_id: {control_id}')
        control: xbmcgui.Control = window.getControl(control_id)
        # clz._logger.debug(f'control: {control}')
        return control

    def get_label_control(self, control_id: int) -> xbmcgui.ControlLabel:
        clz = BaseModel
        clz._logger.debug(f'control_id: {control_id}')
        control: xbmcgui.Control
        control = self.get_control(control_id)
        control: xbmcgui.ControlLabel
        return control

    def get_button_control(self, control_id: int) -> xbmcgui.ControlButton | None:
        clz = BaseModel
        clz._logger.debug(f'control_id: {control_id}')
        control: xbmcgui.Control
        try:
            control = self.get_control(control_id)
        except Exception as e:
            clz._logger.exception('')
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

    def get_label_ll(self, stmts: Statements, label_expr: str | None,
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
        clz._logger.debug(f'label_1: {label_1} label_2: {label_2} '
                          f'label_expr: {label_expr}\n '
                          f'supports_label_1: {self.supports_label} '
                          f'supports_label_2: {self.supports_label2}')
        success_1: bool = True
        success_2: bool = True
        if not (label_1 or label_2):
            return False

        control_id: int | None = None
        if label_expr is not None:
            if isinstance(label_expr, int):
                control_id = label_expr
                if control_id < 0:
                    return False
            elif label_expr.isdigit():
                control_id = int(label_expr)
                if control_id <= 0:
                    return False
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
                text_2 = xbmc.getInfoLabel('Control.GetLabel(100)')
                text_3 = xbmc.getInfoLabel('Control.GetLabel("100")')
                visible: bool = xbmc.getCondVisibility(f'Control.IsVisible({control_id})')
                clz._logger.debug(f'query_1: {query_1} text_1: {text_1} visible {visible}')
                clz._logger.debug(f'text_2: {text_2} text_3: {text_3}')
                if text_1 != '':
                    stmts.append(Statement(PhraseList.create(texts=text_1,
                                                             check_expired=False),
                                       stmt_type=stmt_type))
            except:
                clz._logger.exception(f'control_expr: {query_1} label_1')
                success_1 = False
        if query_2 != '' and label_2:
            try:
                text_2 = xbmc.getInfoLabel(query_2)  # TODO: May require post-processing
                text_2 = text_2.strip()
                if text_2 != '':
                    if text_1 != '':
                        stmts.last.phrases.add_text(texts=text_2)
                    else:
                        stmts.append(Statement(PhraseList.create(texts=text_2,
                                                                 check_expired=False),
                                               stmt_type=stmt_type))

            except:
                clz._logger.exception(f'control_expr: {query_2} label_1')
                success_2 = False

        if text_1 != '' or text_2 != '':
            clz._logger.debug(f'text_1: {text_1} text_2: {text_2} \n  stmts: {stmts}')
        return success_1 and success_2

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
                clz._logger.exception('')
        return False
