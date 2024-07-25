# coding=utf-8

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, ForwardRef, List, Tuple

import xbmc
import xbmcgui

from common.critical_settings import CriticalSettings
from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_tags import control_elements, ControlType, Item, Requires, WindowType

from gui.base_parser import BaseParser
from windows.ui_constants import AltCtrlType
from windows.window_state_monitor import WinDialog, WinDialogState, WindowStateMonitor

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class BaseModel:

    _logger: BasicLogger = None

    def __init__(self, window_model: ForwardRef('BaseModel'),  parser: BaseParser) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)

        self.window_model: ForwardRef('WindowModel') = window_model

        self.control_id: int = parser.control_id
        self.control_type: ControlType = parser.control_type
        self.tree_id: str = f'JUNK'
        self.topic: ForwardRef('TopicModel') = None
        self.topic_checked: bool = False
        # Parent models can specify that the topic MUST have something defined.
        # Example, Sliders require that it's topic MUST define the units, scale,
        # etc. for the slider, since there is no way to get this from kodi api
        self.requires: List[Requires] = []
        self.item_count: int = 0

        ### self.control_id: int = parsed_window.win_dialog_id
        self.children: List[BaseModel] = []

    def clear_history(self) -> None:
        pass

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
        success: bool = False
        if self.topic is not None:
            topic: ForwardRef('TopicModel') = self.topic
            clz._logger.debug(f'topic: {topic.alt_type}')
            success = self.voice_heading(phrases)
            success = self.voice_number_of_items(phrases)
            # Voice either focused control, or label/text
            # success = self.voice_active_item(phrases)
            # Voice either next Topic down or focus item

            # success = self.voice_controlx(phrases)
            return success
        # TODO, incomplete
        return False

    def get_control_name(self) -> str:
        clz = type(self)
        control_name: str = ''
        if self.topic is not None:
            control_name = self.topic.get_alt_control_name()
        if control_name == '':
            control_type: AltCtrlType
            control_type = AltCtrlType.alt_ctrl_type_for_ctrl_name(self.control_type)
            control_name = Messages.get_msg_by_id(control_type.value)
        return control_name

    def voice_control_name(self, phrases: PhraseList) -> bool:
        clz = type(self)
        success: bool = False
        control_name: str = self.get_control_name()
        phrases.append(Phrase(text=control_name))
        return success

    def voice_heading(self, phrases: PhraseList) -> bool:
        clz = type(self)
        success: bool = False
        if self.topic is None:
            return self.get_heading_without_topic(phrases)

        success = self.voice_labeled_by(phrases)
        if not success:
            success = self.topic.voice_label_expr(phrases)
        return success

    def voice_number_of_items(self, phrases: PhraseList) -> bool:
        return False

    def voice_labeled_by(self, phrases: PhraseList) -> bool:
        # Needs work
        clz = type(self)
        success: bool = False
        if self.topic.labeled_by_expr != '':
            control_id: int = self.get_non_negative_int(self.topic.labeled_by_expr)
            if control_id == -1:
                clz._logger.debug(
                    f"Can't find labeled by for {self.topic.labeled_by_expr}")
                return False
            label_cntrl: BaseModel
            label_cntrl = self.window_model.get_control_model(control_id)
            label_cntrl: ForwardRef('LabelModel')
            clz._logger.debug(f'labeled_by: {self.topic.labeled_by_expr}')
            clz._logger.debug(f'label_cntrl: {label_cntrl is not None}')
            if label_cntrl is not None:
                success = label_cntrl.voice_label(phrases)
        clz._logger.debug(f'{phrases}')
        return success

    def get_heading_without_topic(self, phrases: PhraseList) -> bool:
        phrases.append(Phrase(text='get_heading_without_text not implemented'))
        return True

    '''
    def voice_labeled_by(self, phrases: PhraseList) -> bool:
        clz = type(self)
        success: bool = False
        # label_by_expr can be:
        #    topic_id
        #    a control_id in the current window
        #    Message id
        #    Some other expression (info label?)
        clz._logger.debug(f'labeled_by_expr: {self.topic.labeled_by_expr}')
        if self.topic.labeled_by_expr != '':
            # First try for topic_id
            topic: ForwardRef('TopicModel')
            control_id: int = self.get_non_negative_int(self.topic.labeled_by_expr)
            if control_id == -1:
                clz._logger.debug(f"Can't find labeled by for {self.topic.labeled_by_expr}')

        clz._logger.debug(f'{phrases}')
        return success
    '''

    def voice_label(self, phrases, control_id_expr: int | str | None = None) -> bool:
        """

        :param phrases: Any found text is appended to this
        :param control_id_expr:  If non-None, then used as the control_id instead
               of self.control_id
        :return:
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

    def voice_label2(self, phrases, control_id_expr: int | str | None = None) -> bool:
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
                query: str = f'Control.GetLabel({control_id}.index(1))'
                text: str = xbmc.getInfoLabel(query)
                clz._logger.debug(f'Text: {text}')
                if text != '':
                    phrases.append(Phrase(text=text))
                    success = True
            except ValueError as e:
                success = False
        return success

    def voice_value(self, phrases: PhraseList) -> bool:
        clz = type(self)
        clz._logger.debug(f'voice_value not implemented')
        return False

    def visible_item_count(self) -> int:
        self.item_count = 0
        for child in self.children:
            child: BaseModel
            if not hasattr(child, 'topic_model') and child.is_visible():
                self.item_count += 1
        return self.item_count

    def is_visible(self) -> bool:
        if self.control_id != -1:
            # WindowModel.control_id is the Window ID
            return WindowStateMonitor.is_visible(self.control_id,
                                                 self.window_model.control_id)

    def build_control_tree(self, window: ForwardRef('BaseModel'), level: int) -> None:
        # Window control ALWAYS has an ID. Tree_id assigned in constructor
        from gui.topic_model import TopicModel

        clz = type(self)
        topic_str: str = ''
        if self.topic is not None:
            topic_str: str = f'{self.topic}'
        clz._logger.debug(
                f'topic: {topic_str} '
                f' control_id: {self.control_id}'
                f' type: {type(self)} parent: {type(self)}')
        if self.control_id >= 0:
            window.control_id_map[self.control_id] = self

        # We have a bit of a conumdrum here. We use the controlID as an identifier
        # in several fields and tables. But, many controls don't have an ID, so we
        # generate a fake. The generator code was written to work in the recursive
        # code and not here.
        #
        # The truth is this impacts ONLY ONE node (window), since that is the only
        # node that is not a child of another node. The window node is also
        # guaranteed to have a real ID. I probably should have written this to
        # insert a fake root node so that even the window node could be handled
        # like all others.
        #
        #  Sigh...

        if self.control_id > 0:
            self.tree_id = f'{self.control_id}'
            if self.topic is not None:
                topic: TopicModel = self.topic
                topic.tree_id = self.tree_id
                window.topics.append(topic)
                if topic.tree_id in window.topic_by_tree_id.keys():
                    raise ET.ParseError(f'Duplicate topic by tree_id: {topic.tree_id} '
                                        f'topic: {topic.name}')
                window.topic_by_tree_id[topic.tree_id] = topic
                clz._logger.debug(f'Adding topic: {topic.name}')
                clz._logger.debug(f'{topic} \n{topic.parent}')
                if topic.name in window.topic_by_topic_name.keys():
                    raise ET.ParseError(f'Duplicate topic name: {topic.name}')

                window.topic_by_topic_name[topic.name] = topic
                window.window_id_map[self.tree_id] = self

        level += 1
        child_idx: int = 0

        # Visit every node in window
        for child in self.children:
            child: BaseModel

            # Generate fake ID for controls which don't have an explicit ID
            # There other case with real IDs, is handled by the caller.
            if child.control_id < 0:
                child.tree_id = f'L{level}C{child_idx}'
                if child.topic is not None:
                    topic: TopicModel = child.topic
                    topic.tree_id = child.tree_id
                    window.topics.append(topic)
                    window.topic_by_tree_id[topic.tree_id] = topic
                    clz._logger.debug(f'Adding topic: {topic.name}')
                    window.topic_by_topic_name[topic.name] = topic
                    window.window_id_map[self.tree_id] = self

            child.build_control_tree(window, level=level)
            child_idx += 1

    def build_topic_maps(self, window: ForwardRef('BaseModel')) -> None:
        """
          Create ordered map of topics. Ordered by traversing right from each
          topic, beginning with the window topic. The key is topic.name
       """
        clz = type(self)
        from gui.topic_model import TopicModel

        clz._logger.debug(f'size of window.topics: {len(window.topics)}')
        root_topic: TopicModel = window.topics[0]
        topic: TopicModel = root_topic
        while topic is not None:
            if topic.name == '':
                raise ET.ParseError(f'Topic.name is empty')
            window.ordered_topics_by_name[topic.name] = topic
            try:
                if topic.topic_right == '':
                    clz._logger.debug(f'Topic.topic_right is empty for topic: '
                                      f'{topic.name}')
                elif topic.topic_right in window.topic_by_topic_name:
                    topic = window.topic_by_topic_name[topic.topic_right]
                else:
                    topic = None  # Navigation will not advance right
                    continue
            except Exception as e:
                clz._logger.exception('')
                raise ET.ParseError(f'Topics are NOT traversable. name not found '
                                    f'topic: {topic}\n size of topic_by_topic_name: '
                                    f'{len(window.topic_by_topic_name)}')
            if topic.name == root_topic.name:
                clz._logger.debug(f'Reached root topic.')
                break

    def get_topic_for_id(self, ctrl_or_topic_id: str) -> ForwardRef('TopicModel'):
        clz = type(self)
        clz._logger.debug(f'ctrl_or_topic_id: {ctrl_or_topic_id}')
        topic: ForwardRef('TopicModel')
        topic = self.window_model.topic_by_topic_name.get(ctrl_or_topic_id)
        if topic is None:
            # TODO: Merge topic_by_tree_id with topic_by_topic_name
            topic = self.window_model.topic_by_tree_id.get(ctrl_or_topic_id)
            # clz._logger.debug(
            #     f'got topic from topic_by_tree_id from {ctrl_or_topic_id} '
            #     f'topic: {topic}')
        else:
            pass
            # clz._logger.debug(f'got topic from topic_by_topic_name from {ctrl_or_topic_id} '
            #                   f'topic: {topic}')
        # if topic is not None:
        #     clz._logger.debug(f'control from topic: {topic.parent}')
        return topic

    @classmethod
    def get_model_instance(cls) -> ForwardRef('BaseModel'):
        pass

    def get_non_negative_int(self, control_expr: str) -> int:
        """
        Attempts to convert control_expr to an int

        :param control_expr: String representation of an int id, or
        some non-control-id
        :return: abs(int value of control_expr), or -1 if control_expr
            is not an int
        """
        try:
            return abs(int(control_expr))
        except ValueError:
            return -1

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
        clz = type(self)
        window: xbmcgui.Window | xbmcgui.WindowDialog = self.window_model.win_or_dialog
        clz._logger.debug(f'control_id: {control_id}')
        control: xbmcgui.Control = window.getControl(control_id)
        # clz._logger.debug(f'control: {control}')
        return control

    def get_label_control(self, control_id: int) -> xbmcgui.ControlLabel:
        clz = type(self)
        clz._logger.debug(f'control_id: {control_id}')
        control: xbmcgui.Control
        control = self.get_control(control_id)
        control: xbmcgui.ControlLabel
        return control

    def get_button_control(self, control_id: int) -> xbmcgui.ControlButton | None:
        clz = type(self)
        clz._logger.debug(f'control_id: {control_id}')
        control: xbmcgui.Control
        try:
            control = self.get_control(control_id)
        except Exception as e:
            clz._logger.exception('')
            control = None
        control: xbmcgui.ControlButton
        return control

    def convertElements(self,
                        elements: List[BaseParser]) -> None:
        for element in elements:
            element: BaseParser
            key: str = element.item.keyword
            if key == 'visible':
                self.visible_expr: str = element.visible_expr

    def get_current_label_value(self, phrases: PhraseList, clean_string: bool) -> bool:
        """
        Return this label's value. Which can sometimes be a real chore.

        :param phrases append any resulting string to
        :param clean_string if True then 'clean' the string using
        :return:
        """
        text = xbmc.getInfoLabel('System.CurrentControl')

        return
