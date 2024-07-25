# coding=utf-8

from typing import Callable, Dict, ForwardRef, List

import xbmc
import xbmcgui

from common.logger import BasicLogger, DEBUG_VERBOSE
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlType, ElementType, Item, WindowType
from gui.button_model import ButtonModel
from gui.controls_model import ControlsModel
from gui.edit_model import EditModel
from gui.element_parser import (ElementHandler)
from gui.group_list_model import GroupListModel
from gui.group_model import GroupModel
from gui.label_model import LabelModel
from gui.parse_topic import ParseTopic
from gui.parse_window import ParseWindow
from gui.base_tags import ElementKeywords as EK
from gui.radio_button_model import RadioButtonModel
from gui.scrollbar_model import ScrollbarModel
from gui.slider_model import SliderModel
from gui.topic_model import TopicModel
from windows.ui_constants import AltCtrlType
from windows.window_state_monitor import WinDialog, WinDialogState, WindowStateMonitor

ElementHandler.add_model_handler(ControlsModel.item, ControlsModel)
ElementHandler.add_model_handler(GroupModel.item, GroupModel)
ElementHandler.add_model_handler(ButtonModel.item, ButtonModel)
ElementHandler.add_model_handler(RadioButtonModel.item, RadioButtonModel)
ElementHandler.add_model_handler(LabelModel.item, LabelModel)
ElementHandler.add_model_handler(GroupListModel.item, GroupListModel)
ElementHandler.add_model_handler(ScrollbarModel.item, ScrollbarModel)
ElementHandler.add_model_handler(EditModel.item, EditModel)
ElementHandler.add_model_handler(SliderModel.item, SliderModel)
ElementHandler.add_model_handler(TopicModel.item, TopicModel)


module_logger = BasicLogger.get_module_logger(module_path=__file__)


class WindowModel(BaseModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.WINDOW.name]

    def __init__(self, parsed_window: ParseWindow) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(window_model=self, parser=parsed_window)
        clz._logger.debug(f'I am here in WindowModel')

        # Reduce the number of repeated phrases.
        # Detect when there has been a change to a new window, or when the focus
        # has changed.

        self.changed: bool = True
        self.focused_topic_id: str = ""
        self.focus_id: int = -1

        self.window_type: WindowType = parsed_window.window_type
        self.win_or_dialog: xbmcgui.Window | xbmcgui.WindowDialog
        self.win_dialog_id: int = -1
        if WinDialogState.current_windialog == WinDialog.WINDOW:
            self.win_or_dialog_id = WinDialogState.current_window_id
            self.win_or_dialog = WinDialogState.current_window_instance
        else:
            self.win_or_dialog_id = WinDialogState.current_dialog_id
            self.win_or_dialog = WinDialogState.current_dialog_instance

        self.window_title_id: int = parsed_window.window_title_id
        self.default_control_id: str = parsed_window.default_control_id
        self.window_modality: str = parsed_window.window_modality   # Only dialogs
        self.menu_control: int = parsed_window.menu_control
        self.visible_expr: str = parsed_window.visible_expr
        self.tts: str = parsed_window.tts
        self.children: List[BaseModel] = []

        '''
          Track what we have voiced so we don't repeat unless the context has
          changed. The window basically just has a window heading to track.
        '''
        self.previous_heading: PhraseList = PhraseList()

        # Each control can have one Topic
        # self.topic: TopicModel = None

        """
            All Topics in this window. The first one is for this control
        """

        self.topics: List[TopicModel] = []

        """
            Map of all Controls in Window, indexed by it's 'tree_id'.
            A tree_id is same as it's control_id, but when there is no
            control_id, it is L<control_depth>C<child#>
            The control_id is most useful, but the other form allows other
            controls to be looked-up, even if awkwardly
        """

        self.window_id_map: Dict[str, BaseModel] = {}
        """     
            Map of all Controls in Window, which have a control_id
            Many controls don't have a control_id
        """
        self.control_id_map: Dict[int, BaseModel] = {}

        self.best_alt_label: str = ''
        self.best_hint_text: str = ''
        self.control_stack_map: Dict[str, List[BaseModel]] = {self.tree_id: self}
        self.topic_by_tree_id: Dict[str, TopicModel] = {}
        self.topic_by_topic_name: Dict[str, TopicModel] = {}
        self.ordered_topics_by_name: Dict[str, TopicModel] = {}

        # window: xbmcgui.Window = WindowStateMonitor.get_dialog()
        # control = window.getControl(100)
        # clz._logger.debug(f'control label: {control.getLabel()}')

        self.convert_controls(parsed_window)
        self.build_control_tree(window=self, level=0)
        parents: List[BaseModel] = [self]
        self.build_parent_list_map(self, parents)
        self.build_topic_maps(window=self)

        #  Contains child controls
        #  parsed_window.children: List[BaseParser] = []
        #
        #  Contains additional elements for this control
        #  parsed_window.parsers: List[BaseElementParser] = []

    def convert_controls(self, parsed_window: ParseWindow) -> None:
        clz = type(self)
        children: List[BaseParser] = []
        # parsers: List[BaseParser] = parsed_window.parsers
        # clz._logger.debug(f'# children: {len(parsed_window.children)}')

        if parsed_window.topic is not None:
            self.topic = TopicModel(self, parsed_window.topic)
        for child in parsed_window.children:
            child: BaseParser
            #  clz._logger.debug(f'About to create model from window{child}')
            model_handler: Callable[[BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            value_or_control = model_handler(self, child)
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'value_or_control: {value_or_control}')
            if value_or_control is not None:
                if (child.item.key in (ControlType.CONTROLS.name,
                                       ControlType.CONTROL.name)):
                    self.children.append(value_or_control)

    '''
    def build_control_tree(self):
        """
        Build a tree of controls. Ideally there would be 'topic' nodes that have
        labels appropriate for the topic (heading, hint, alt-lable, etc) and then
        would contain the immediate members of the topic as immediate children.
        Subtopics would be contained in childen of type topic, or topic grandchildren.
        But, this would require major rework and is not likely necessary.

        Any control which has labels, hints, etc. can be considered a topic. Leaf
        nodes are topics with one member, itself. Groups, in particular, can be topics
        with labels, etc. that apply to all members of the group (and decendents).

        label_for and labeled_by tend to identify topics. topic_id attributes
        explicitly define one. Without the presence of these on a window, a best-
        guesse is used. Basically, if there is a label associated with an
        enclosing group, then it will be assumed to be a topic label. Hard-coded
        rules will be made for specific windows/dialogs.

        :return:
        """

        """
         Every control has a list of all it's direct children. In addition, every
         control has a link to its parent. Assign a unique ID to every control 
         Controls are NOT required to have ids. Ids are ultimately positive integers,
         but names can be used. For those without an assigned ID, label them 
         according to their tree depth and their index in the list of children 
         for their parent. In other words, if a Node is contained in a group
         which is a direct child of the Window. Further, if the node is the 
         fifth child of this group, then the node's id will be: "L1C5" for
         "level1, child 4".  To reduce confusion, this ID will be kept in 
         the tree_id: str field. For controls which already have ids, the 
         control_id will be copied to tree_id.
        """
        clz = type(self)
        # Window control ALWAYS has an ID. Tree_id assigned in constructor
        level: int = 0
        if self.control_id >= 0:
            self.control_id_map[self.control_id] = self

        #  For each node, track the stack of nodes above to the root
        #  self.control_stack_map[self.tree_id] = self.
        child_idx: int = 0
        for child in self.children:
            child: BaseModel
            if child.control_id < 0:
                child.tree_id = f'L{level}C{child_idx}'
            else:
                child.tree_id = f'{child.control_id}'
            #  clz._logger.debug(f'child: {type(child)} tree_id: {child.tree_id}')
            child.build_control_tree(self, level=level)
            child_idx += 1
            clz._logger.debug(f'isinstance of TopicModel: {isinstance(child, TopicModel)} '
                              f'type: {type(child)} parent: {type(self)}')
            if isinstance(child, TopicModel):
                self.topics.append(child)
    '''

    def set_changed(self, changed: int, focused_topic_id: str, focus_id: str) -> None:
        self.changed: int = changed
        self.focused_topic_id: str = focused_topic_id
        self.focus_id: str = focus_id

    def clear_history(self) -> None:
        self.previous_heading.clear()

    def voice_control(self, phrases: PhraseList,
                      focus_changed: bool) -> bool:
        """
        Generate the speech for the window itself. Takes into account
        whether this was previously voiced.

        Typical content for a window is:
            "Window" | "Dialog" <title of window>

        If this content is the same as what was most recently voiced, then
        the voicing is skipped. There is not sufficient information to reliably
        predict when the text has changed, so it is generated each time and
        then compared with the previous text. Perhaps this can be improved upon.

        In the case of a Window/Dialog, the voiced content comes from the
        Window's 'header'. Other controls have other logical sections.

        :param phrases:
        :param focus_changed: If True, then voice changed heading, labels and all
                              If False, then only voice a change in value.
        :return:
        """
        clz = type(self)
        success: bool = False
        # Only voice when window is newly changed
        # TODO: improve by taking into account when window voicing fails to occur
        # such as when there is an interruption (focus change occurs before this
        # window info is announced, causing the window not being announced when
        # focus change announced).
        clz._logger.debug(f'changed: {self.changed}')
        if not (self.changed & (WindowStateMonitor.DIALOG_CHANGED or
                                WindowStateMonitor.WINDOW_CHANGED)):
            return True

        if self.topic is not None:
            topic: TopicModel = self.topic
            clz._logger.debug(f'topic: {topic.alt_type}')
            if topic.alt_type in (AltCtrlType.DIALOG, AltCtrlType.WINDOW):
                temp_phrases: PhraseList = PhraseList()
                success = self.voice_heading(temp_phrases)
                if not self.previous_heading.equal_text(temp_phrases):
                    self.previous_heading.clear()
                    self.previous_heading.extend(temp_phrases)
                    phrases.extend(temp_phrases)
        # TODO, incomplete
        return success

    def voice_heading(self, phrases: PhraseList) -> bool:
        """
        Generate the speech for the window header. Takes into account
        whether this header was previously voiced.
        :param phrases:
        :return:
        """
        clz = type(self)
        success: bool = False
        control_name: str = ''
        topic: TopicModel = self.topic
        success = self.voice_control_name(phrases)
        if topic is not None:
            success = self.voice_labeled_by(phrases)
        if not success:
            success = self.voice_heading_without_topic(phrases)
        return success

    def voice_heading_without_topic(self, phrases: PhraseList) -> bool:
        phrases.append(Phrase(text='get_heading_without_text not implemented'))
        return True

    def build_parent_list_map(self, parent: BaseModel, parents: List[BaseModel]):
        """
        This time, record the parent chain for each child
        """

        clz = type(self)
        self.control_stack_map[parent.tree_id] = parents
        #  clz._logger.debug(f'parents: # {len(parents)}')
        for child in parent.children:
            child: BaseModel
            new_parents = parents.copy()
            new_parents.append(child)
            self.build_parent_list_map(child, new_parents)

    def get_control_model(self, control_id_expr: str) -> BaseModel | None:
        """
          Map of all Controls in Window, which have a control_id
          Many controls don't have a control_id
        :param control_id_expr:
        :return:
        """
        control_id: int = self.get_non_negative_int(control_id_expr)
        if control_id < 0:
            return None
        return self.control_id_map.get(control_id)

    def get_control_model_by_tree_id(self, tree_id: str) -> BaseModel | None:
        return self.window_id_map.get(tree_id)

    def get_current_control_model(self) -> BaseModel | None:
        try:
            control_id_str: str = xbmc.getInfoLabel('System.CurrentControlId')
            return self.get_control_model(control_id_str)
        except Exception as e:
            return None

    def get_window_heading_id(self) -> str:
        return f'{self.window_title_id}'

    previously_voiced_items: Dict[str, BaseModel] = {}
    about_to_voice_items: Dict[str, BaseModel] = {}

    def is_already_voiced(self, model: BaseModel) -> bool:
        previously_voiced: BaseModel = None

    def __repr__(self) -> str:
        clz = type(self)
        result: str = ''

        #  Start with this window
        window_str: str = (f'\nWindowModel window: {self.control_type} id: '
                           f'{self.control_id} '
                           f'window_title_id: {self.window_title_id} '
                           f'tts: {self.tts}')
        menu_ctrl_str: str = ''
        if self.menu_control != -1:
            menu_ctrl_str = f'\n menu_ctrl: {self.menu_control}'
        default_control_str: str = f''
        if self.default_control_id != '':
            default_control_str = f'\n default_control: {self.default_control_id}'
        visible_expr_str: str = ''
        if self.visible_expr != '':
            visible_expr_str = f'\n visible_expr: {self.visible_expr}'
        window_modality: str = ''
        if self.window_modality != '':
            window_modality = f'\n window_modality: {self.window_modality}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result = f'{window_str}{default_control_str}{visible_expr_str}{window_modality}'
        results.append(result)
        results.append(f'{topic_str}')

        results.append(f' # children: {len(self.children)}')
        for control in self.children:
            control: BaseModel
            result: str = str(control)
            results.append(result)

        results.append('\nFinete')
        return '\n'.join(results)

    @classmethod
    def get_instance(cls) -> ForwardRef('WindowModel'):
        return WindowModel()

    def is_visible(self) -> bool:
        return xbmc.getCondVisibility(f'Window.IsVisible({self.control_id})')


ElementHandler.add_model_handler(WindowModel.item, WindowModel)