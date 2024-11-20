# coding=utf-8
from __future__ import annotations
import sys
import xml.etree.ElementTree as ET
from logging import DEBUG
from typing import Dict, ForwardRef, List, Tuple, Union

import xbmc

from common import AbortException, reraise
from common.logger import BasicLogger, DEBUG_V, DEBUG_XV, DISABLED
from gui import ControlElement, ParseError
from gui.i_model import IModel

from gui.no_topic_models import BaseFakeTopic
from gui.topic_model import TopicModel
from utils import util
from windows.window_state_monitor import WinDialogState

MY_LOGGER = BasicLogger.get_logger(__name__)


class WindowStructure:
    """
        Manages the Nodes (controls/topics) in a window. Provides lookup
        of nodes by control_id, and topic_id. Maintains the relationship
        between nodes so that you can determine, for example, all of the
        nodes between a given node and the root (very useful to find which
        nodes may need to be voiced based on a change made to the currelty
        focused node, etc.)

    """
    #
    # Map of every WindowStructure by window_id
    _window_struct_map: Dict[int, ForwardRef('WindowStructure')] = {}

    @classmethod
    def get_instance(cls, window: IModel) -> ForwardRef('WindowStructure'):
        if window.window_id not in cls._window_struct_map.keys():
            wind_struct: ForwardRef('WindowStructure') = WindowStructure(window)
            cls._window_struct_map[window.window_id] = wind_struct
        return cls._window_struct_map[window.window_id]

    def __init__(self, window: IModel) -> None:
        """
        Builds the window structures. DO NOT CALL prior to all windows and topics have
        been created.

        :param window: The top of the window tree, WindowModel. The entire window and
                        topics are expected to be created prior to this call.
        """
        clz = WindowStructure

        self.window: IModel = window
        window.window_struct = self
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'window: {window.window_id} windialog_state:'
                                f' {window.windialog_state}')
        self._windialog_state: WinDialogState = window.windialog_state

        topic_id: str = ''
        if window.topic is not None:
            topic_id = window.topic.name
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'window_id: {window.windialog_state.window_id} '
                                f'topic: {topic_id}')
        self._root_topic: TopicModel = window.topic
        self.window_topic_id: str = topic_id

        self._test_node_list: List[IModel] = []  # For testing
        self._topic_by_tree_id: Dict[str, TopicModel] = {}
        self._topic_by_topic_name: Dict[str, TopicModel] = {}
        #  self.ordered_topics_by_name: Dict[str, TopicModel] = {}

        """
          Map of all Controls in Window, indexed by it's 'tree_id'.
          A tree_id is same as it's control_id, but when there is no
          control_id, it is L<control_depth>C<child#>
          The control_id is most useful, but the other form allows other
          controls to be looked-up, even if awkwardly
        """

        self._window_id_map: Dict[str, IModel] = {}
        """     
            Map of all Controls in Window, which have a control_id
            Many controls don't have a control_id
        """
        self._model_for_control_id: Dict[int, IModel] = {}
        #  self.control_stack_map: Dict[str, List[IModel]] = {}

        self.build_control_tree(node=window, level=0)
        parents: List[IModel] = [window]
        #  self.build_parent_list_map(window, parents)
        #  self.build_topic_maps()

        self.test_window_id_map()
        self.test_get_control_and_topic_for_id()
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'Finished WindowStructure init')

    def _destroy(self):
        clz = type(self)
        del MY_LOGGER
        del self.window
        del clz._window_struct_map
        del self._root_topic
        del self.window_topic_id
        del self._test_node_list
        del self._topic_by_tree_id
        del self._topic_by_topic_name
        del self._window_id_map
        del self._model_for_control_id

    def set_windialog_state(self, windialog_state: WinDialogState) -> None:
        self._windialog_state: WinDialogState = windialog_state

    @classmethod
    def get_window_struct(cls, window_id: int) -> ForwardRef('WindowStructure'):
        #  MY_LOGGER.debug(f'window_id: {window_id}')
        return cls._window_struct_map.get(window_id, None)

    @property
    def windialog_state(self) -> WinDialogState:
        return self._windialog_state

    @property
    def focus_changed(self) -> bool:
        return self._windialog_state.focus_changed

    @property
    def root_topic(self) -> TopicModel | None:
        """
        Returns the root_topic node for this window/dialog.
        The root topic represents the Window/Dialog

        :return:
        """
        return self._root_topic

    @property
    def test_node_list(self) -> List[IModel]:
        return self._test_node_list

    def add_test_node(self, value: IModel):
        clz = WindowStructure
        if not isinstance(value, IModel):
            raise ValueError(f'value is NOT a Model: {value}')
        self._test_node_list.append(value)

    def get_topic_by_tree_id(self, tree_id: str) -> TopicModel:
        clz = WindowStructure
        if not isinstance(tree_id, str):
            raise ValueError(f'tree_id: {tree_id} MUST be a str not:{type(tree_id)}')
        topic: TopicModel = self._topic_by_tree_id.get(tree_id)
        if topic is not None and MY_LOGGER.isEnabledFor(DISABLED):
            MY_LOGGER.debug_v(f'Found: topic: {topic.name}')
        return topic

    def add_topic_by_tree_id(self, tree_id: str, topic: TopicModel) -> None:
        clz = WindowStructure
        if not isinstance(tree_id, str):
            raise ValueError(f'Expected tree_id to str not {type(tree_id)}')
        if not isinstance(topic, TopicModel):
            raise ValueError(f'Expected topic to TopicModel not {type(topic)}')
        if (MY_LOGGER.isEnabledFor(DEBUG_V) and
                tree_id in self._topic_by_tree_id.keys()):
            MY_LOGGER.debug_v(f'Duplicate tree_id in _topic_by_tree_id: {tree_id}')
        self._topic_by_tree_id[tree_id] = topic

    def get_topic_by_topic_name(self, topic_name: str) -> TopicModel | None:
        clz = WindowStructure
        if topic_name is None:
            raise ValueError('topic_name is None')
        if isinstance(topic_name, str) and topic_name.isdigit():
            return None
        if not isinstance(topic_name, str):
            raise ValueError(f'topic_name: {topic_name} MUST be a str not:{type(topic_name)}')
        topic: TopicModel = self._topic_by_topic_name.get(topic_name)
        if topic is None:
            MY_LOGGER.debug(f'Could not find topic with name: {topic_name}')
            #  raise ValueError(f'Could not find topic with name: {topic_name}')
        elif MY_LOGGER.isEnabledFor(DISABLED):
            MY_LOGGER.debug_v(f'Found: topic: {topic.name}')
        return topic

    def add_topic_by_topic_name(self, topic_name: str, topic: TopicModel) -> None:
        clz = WindowStructure
        if not isinstance(topic_name, str):
            raise ValueError(f'Expected topic_name to be str not {type(topic_name)}')
        if topic_name.isdigit():
            raise ValueError(f'Expected topic_name to be an integer.')
        if not isinstance(topic, TopicModel):
            raise ValueError(f'Expected topic to TopicModel not {type(topic)}')
        if topic_name in self._topic_by_topic_name.keys():
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Duplicate topic_name in _topic_by_topic_name: {topic_name}')
        self._topic_by_topic_name[topic_name] = topic

    """
      Map of all Controls in Window, indexed by it's 'tree_id'.
      A tree_id is same as it's control_id, but when there is no
      control_id, it is L<control_depth>C<child#>
      The control_id is most useful, but the other form allows other
      controls to be looked-up, even if awkwardly
    """

    def get_model_by_tree_id(self, window_id: str) -> IModel | None:
        clz = WindowStructure
        if not isinstance(window_id, str):
            raise ValueError(f'window_id: {window_id} MUST be a str not:'
                             f'{type(window_id)}')
        window_model: IModel = self._window_id_map.get(window_id)
        if MY_LOGGER.isEnabledFor(DEBUG_V) and window_model is None:
            MY_LOGGER.debug_v(f'window_id: {window_id} NOT found')
        return window_model

    def add_window_model_by_window_id(self, window_id: str, window_model: IModel) -> None:
        if not isinstance(window_id, str):
            raise ValueError(f'window_id: {window_id} MUST be a str not:'
                             f'{type(window_id)}')
        if not isinstance(window_model, IModel):
            raise ValueError(f'window_model: MUST be a Model not:'
                             f'{type(window_model)}')
        self._window_id_map[window_id] = window_model

    def get_model_for_control_id(self, control_id: int) -> IModel | None:
        clz = WindowStructure
        if not isinstance(control_id, int):
            raise ValueError('control_id must be int')
        model: IModel = self._model_for_control_id.get(control_id)
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'found: {model.control_id} {model.control_type}')
        return model

    def set_model_for_control_id(self, control_id: int, model: IModel) -> None:
        clz = WindowStructure
        if not isinstance(control_id, int):
            raise ValueError('control_id must be int')
        if not isinstance(model, IModel):
            raise ValueError(f'model: MUST be a Model not:'
                             f'{type(model)}')
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'added control_id: {control_id} control_type:'
                                f' {model.control_type}'
                                f' to model_for_control_id')
        self._model_for_control_id[control_id] = model

    def build_control_tree(self, node: IModel,
                           level: int, child_idx: int = 0) -> None:
        """
        Called immediately after all Models have been created from their ParsedControl
        nodes. Starts with the WindowModel node and recurses depth-first to simplify
        the implementation.

        Multiple structures are populated so that nodes can be found multiple
        ways.
            All nodes with topics are added...
                topic_by_topic_name[node.topic.name] = node.topic

            Maps to find control nodes by their tree_id (valid control_id or
            manufactured id)

            All nodes with topics are added...
                topic_by_tree_id[node.tree_id] = node.topic

            All nodes are added...
                window_id_map[node.tree_id] = node

            All nodes with valid control_ids are added
                model_for_control_id[node.control_id] = node

            For testing, all nodes are added...
                test_node_list: List[IModel] = node

        Each node's tree_id is used as the index. The tree_id is assigned during
        the traversal. The tree_id is set to the node's control_id, if it text_exists (>-1)
        Otherwise, it is manufatured from the position of the node in the tree.

        :param node: BasicModel node to add to the tree.
        :param level: Incremented on each recursion. Used to help generate names
                     for un-named nodes
        :param child_idx: Incremented for each child node visited.
        :return:
        """
        # Window control ALWAYS has an ID. Tree_id assigned in constructor

        clz = WindowStructure
        if MY_LOGGER.isEnabledFor(DISABLED):
            MY_LOGGER.debug_v(f'In build_control_tree')
        topic_str: str = ''
        self.add_test_node(node)
        if node.topic is not None and node.topic.is_real_topic:
            #  MY_LOGGER.debug(f'REAL TOPIC: {node.topic}')
            topic_str: str = f'{node.topic}'
        else:
            if node.topic is not None:
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'UNREAL TOPIC: {node.topic.name} control_id:'
                                         f' {node.control_id} ')
            elif node.control_type != ControlElement.CONTROLS:
                # A Controls control only holds other controls
                pass
        if MY_LOGGER.isEnabledFor(DISABLED):
            MY_LOGGER.debug_v(
                    f'topic: {topic_str} '
                    f' control_id: {node.control_id}'
                    f' parent: {node}')
        if node.control_id >= 0:  # Control_id 0 is for window control
            self.set_model_for_control_id(node.control_id, node)
            node.tree_id = f'{node.control_id}'

        else:  # Control_id is invalid.
            #  Generate fake ID for controls which don't have an explicit ID
            node.tree_id = f'L{level}C{child_idx}'
        topic_str: str = ''
        if node.topic is not None:
            topic_str = node.topic.name
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug(f'Working on tree_id: {node.tree_id}  topic: {topic_str}')

        try:
            # Copy tree_id to any topic linked to the node. But
            # ignore 'fake' topics (manufactured dummy ones to simplify code)
            if node.topic is not None and node.topic.is_real_topic:
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'REAL TOPIC: {node.topic.name}')
                node.topic.tree_id = node.tree_id
                if self.root_topic is None:
                    MY_LOGGER.error('root_topic not set')
                    raise ParseError('root topic not set')

                if node.tree_id in self._topic_by_tree_id.keys():
                    MY_LOGGER.debug(f'Dupe topic tree_id: {node.tree_id}')
                    raise ET.ParseError(f'Duplicate topic by tree_id: '
                                        f'{node.tree_id} '
                                        f'topic: {node.topic.name}')

                # Add non-fake topic to topic map indexed by tree_id

                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'Adding node: |{node.tree_id}| '
                                         f'type: {type(node.tree_id)} to topic_by_tree_id')
                self.add_topic_by_tree_id(node.tree_id, node.topic)
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'Adding topic: {node.topic.name} id:'
                                         f' {node.tree_id}')
                    MY_LOGGER.debug_xv(f'{node.topic}\n{node.topic.parent}')
                # Add non-fake topic to topic map indexed by topic name

                    MY_LOGGER.debug_xv(f'Adding topic {node.topic.name} to'
                                         f' topic_by_topic_name')
                self.add_topic_by_topic_name(node.topic.name, node.topic)

                # Add control node to window_id_map indexed by tree_id
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'Adding topic with tree_id '
                                         f'|{node.tree_id}| type: {type(node.tree_id)}'
                                         f' to window_id_map')
                self.add_window_model_by_window_id(node.tree_id, node)
            else:
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'UNREAL TOPIC: {node.topic.name}')
        except ET.ParseError:
            MY_LOGGER.exception(f'Ignoring topic {node.topic.name}')
        except AbortException:
            self._destroy()
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception(f'Ignoring topic {node.topic.name}')

        # Depth first, so down another level
        level += 1
        child_idx: int = 0
        for child in node.children:
            child: IModel

            self.build_control_tree(child, level=level, child_idx=child_idx)
            child_idx += 1

    '''
    def build_parent_list_map(self, parent: IModel, parents: List[IModel]):
        """
        This time, record the parent chain for each child
        First iteration has window's root as parent and empty list as parents

        TODO: Note that parents list is copied to new node before adding new ancestor
            to it. Could use much shaller structure, such as each node as a
            Tuple[parent_id, List[ancestor_ids]] Or could ditch the map and just
            traverse tree via ancestor links on demand.
        """
        clz = WindowStructure
        self.control_stack_map[parent.tree_id] = parents
        #  MY_LOGGER.debug(f'parents: # {len(parents)}')
        for child in parent.children:
            child: IModel
            new_parents = parents.copy()
            new_parents.append(child)
            self.build_parent_list_map(child, new_parents)
    '''
    '''
        Not used
    def build_topic_maps(self) -> None:
        """
          Create ordered map of topics. Ordered by traversing right from each
          topic, beginning with the window topic. The key is topic.name

          TODO:  Rework this turkey. Assumes that you link every node in tree
          topic.right. This is quite restrictive, error prone and perhaps
          of not much value.
       """
        clz = WindowStructure
        root_topic: TopicModel = self.root_topic
        topic: ForwardRef('TopicModel') = root_topic
        while topic is not None:
            if topic.name == '':
                raise ET.ParseError(f'Topic.name is empty')

            if topic in self.ordered_topics_by_name:
                continue
            self.ordered_topics_by_name[topic.name] = topic
            try:
                if not topic.is_real_topic or topic.topic_right == '':
                    MY_LOGGER.debug(f'Topic topic_right is empty for topic: '
                                      f'{topic.name}')
                elif topic.topic_right in self.topic_by_topic_name:
                    topic = self.topic_by_topic_name[topic.topic_right]
                else:
                    topic = None  # Navigation will not advance right
                    continue
            except Exception as e:
                MY_LOGGER.exception('')
                raise ET.ParseError(f'Topics are NOT traversable. name not found '
                                    f'topic: {topic}\n size of topic_by_topic_name: '
                                    f'{len(self.topic_by_topic_name)}')
            if topic.name == root_topic.name:
                MY_LOGGER.debug_v(f'Reached root topic.')
                break
    '''

    def get_control_and_topic_for_id(self,
                                     control_topic_or_tree_id: str | int) \
            -> Tuple[ForwardRef('IModel'), ForwardRef('BaseTopicModel')]:
        """
            Fetches any control and/or topic that has a matching:
                control_id (numeric)
                topic_id (topic name)
                tree_id (rarely used)

        :param control_topic_or_tree_id:
        :return:  control, topic
        """
        clz = WindowStructure
        search_id: str = str(control_topic_or_tree_id)
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'search_id type: {type(search_id)} value:'
                                 f' |{search_id}|')
        if search_id == '':
            return None, None

        topic: ForwardRef('TopicModel') = None
        control: ForwardRef('IModel') = None

        # Try to search by numeric control id
        control_id: str = search_id
        control = self.get_control_model(control_id)
        if control is not None:
            topic = control.topic
            topic_name: str = ''
            if topic is not None:
                topic_name = topic.name
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'get_control_model rtns ctrl_id:'
                                     f' {control.control_id} '
                                     f'topic: {topic_name}')
        # Search for topic
        if search_id.isdigit():
            topic = self.get_topic_by_tree_id(search_id)
            if topic is not None:
                MY_LOGGER.debug_v(f'Found topic {topic.name} by tree_id: {search_id}')
        if topic is None:
            topic = self.get_topic_by_topic_name(search_id)
        if topic is not None:
            control = topic.parent
            # MY_LOGGER.debug(f'topic {topic}')
            if not topic.is_real_topic or not topic.is_new_topic:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'topic is_real: {topic.is_real_topic} '
                                        f'{topic.is_new_topic}')
                topic = None
        if control is None:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Did NOT find control {control_id} '
                                  f'window_id: {self.window.window_id}')
        return control, topic

    '''
    def get_control_and_topic_for_id(self,
                                     ctrl_topic_or_tree_id: str)\
            -> Tuple[ForwardRef('IModel'), ForwardRef('TopicModel')]:
        """
        Retrieves a topic (if it text_exists) given one of:
                control_id (must be an int)
                topic_id (topic name)
                tree_id
        :param ctrl_topic_or_tree_id:
        :return:
        """
        clz = WindowStructure
        control_model: IModel | None = None
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'ctrl_topic_or_tree_id: {ctrl_topic_or_tree_id}')
        control_id: int = util.get_non_negative_int(ctrl_topic_or_tree_id)
        if control_id != -1:
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug(f'got model for {ctrl_topic_or_tree_id}')
            control_model = self.get_control_model(control_id)
        topic: ForwardRef('TopicModel') = None
        topic = self.get_topic_by_topic_name(ctrl_topic_or_tree_id)
        if topic is None:
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'topic not found for topic name {ctrl_topic_or_tree_id}')
            # TODO: Merge topic_by_tree_id with topic_by_topic_name
            topic = self.get_topic_by_tree_id(ctrl_topic_or_tree_id)
            if topic is None:
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'topic not found for tree_id: {ctrl_topic_or_tree_id}')
            else:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(
                        f'got topic from topic_by_tree_id from {ctrl_topic_or_tree_id} '
                        f'topic: {topic}')
        else:
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'got topic from topic_by_topic_name from '
                                  f'{ctrl_topic_or_tree_id}')
        # if topic is not None:
        #     MY_LOGGER.debug(f'control from topic: {topic.parent}')
        return control_model, topic
    '''

    def get_control_model(self, control_id_expr: str | int) -> IModel | None:
        """
          Map of all Controls in Window, which have a control_id
          Many controls don't have a control_id
        :param control_id_expr:
        :return:
        """
        clz = WindowStructure
        control_id: int = util.get_non_negative_int(control_id_expr)
        if control_id < 0:
            return None
        result = self.get_model_for_control_id(control_id)
        return result

    def get_control_model_by_tree_id(self, tree_id: str) -> IModel | None:
        clz = WindowStructure
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'tree_id: type: {type(tree_id)} |{tree_id}|')
        value: IModel | None = self.get_model_by_tree_id(tree_id)
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'Found: {value}')
        return value

    def get_current_control_model(self) -> IModel | None:
        try:
            control_id_str: str = xbmc.getInfoLabel('System.CurrentControlId')
            return self.get_control_model(control_id_str)
        except AbortException:
            self._destroy()
            reraise(*sys.exc_info())
        except Exception as e:
            return None

    def to_string(self, include_children: bool = False) -> str:
        return ''

    '''
            self.topic_by_tree_id: Dict[str, TopicModel] = {}
            self.topic_by_topic_name: Dict[str, TopicModel] = {}

            """
              Map of all Controls in Window, indexed by it's 'tree_id'.
              A tree_id is same as it's control_id, but when there is no
              control_id, it is L<control_depth>C<child#>
              The control_id is most useful, but the other form allows other
              controls to be looked-up, even if awkwardly
            """

            self.window_id_map: Dict[str, IModel] = {}
            """     
                Map of all Controls in Window, which have a control_id
                Many controls don't have a control_id
            """
            self.model_for_control_id: Dict[int, IModel] = {}
             
    '''

    def test_window_id_map(self) -> None:
        """
        Can find control or topic by:
            numeric control_id
            topic_id
            tree_id
        :return:
        """
        clz = WindowStructure
        node: IModel
        for node in self.test_node_list:
            node_id: str = None
            control: IModel
            topic: TopicModel
            expected_topic_name: str | None = None
            if node.topic is not None:
                expected_topic_name = node.topic.name

            if node.control_id > -1:
                node_id = f'{node.control_id}'
                control, topic = self.get_control_and_topic_for_id(node_id)
                if control is None:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Error: Should have found control {node_id}')
                elif f'{control.control_id}' != node_id:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Error: control ids should match: '
                                          f'control_id: {control.control_id} '
                                          f'node_id: {node_id}')
                if topic is None:
                    if expected_topic_name is not None:
                        if not isinstance(node.topic, BaseFakeTopic):
                            if MY_LOGGER.isEnabledFor(DEBUG_V):
                                MY_LOGGER.debug_v(f'Topic node not found '
                                                    f'expected: {expected_topic_name}')

    def test_get_control_and_topic_for_id(self) -> None:
        clz = WindowStructure
        node: IModel
        for node in self.test_node_list:
            node_id: str = None
            control: IModel
            topic: TopicModel
            expected_topic_name: str | None = None
            if node.topic is not None:
                expected_topic_name = node.topic.name

            if node.control_id > -1:
                node_id = f'{node.control_id}'
                control, topic = self.get_control_and_topic_for_id(node_id)
                if control is None:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Error: Should have found control {node_id}')
                elif f'{control.control_id}' != node_id:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Error: control ids should match: '
                                          f'control_id: {control.control_id} '
                                          f'node_id: {node_id}')
                if topic is None:
                    if expected_topic_name is not None:
                        if not isinstance(node.topic, BaseFakeTopic):
                            if MY_LOGGER.isEnabledFor(DEBUG):
                                MY_LOGGER.debug(f'Topic node not found '
                                                  f'expected: {expected_topic_name}')

            if node.topic is not None:
                topic: TopicModel
                topic = node.topic
                found_topic: TopicModel
                self.test_find_topic(topic.name)
                self.test_find_topic(topic.flows_to_expr)
                self.test_find_topic(topic.flows_from_expr)
                self.test_find_topic(topic.labeled_by)
                self.test_find_topic(topic.label_for)
                self.test_find_topic(topic.outer_topic)
                self.test_find_topic(topic.inner_topic)

    def test_find_topic(self, topic_name: str) -> None:
        clz = WindowStructure
        if topic_name is None or topic_name == '':
            return
        found_topic: TopicModel
        control, found_topic = self.get_control_and_topic_for_id(topic_name)
        if found_topic is None:
            if MY_LOGGER.isEnabledFor(DEBUG):
                if not topic_name.startswith(f'Fake_topic'):
                    MY_LOGGER.debug(f'Error: Should have found topic {found_topic} '
                                      f'for topic: {topic_name}')
                else:
                    # MY_LOGGER.debug(f'topic: {topic_name} gives FakeTopic')
                    pass
        elif topic_name not in (found_topic.name, found_topic.control_id,
                                found_topic.window_id):
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Error: Topics not identical: {topic_name} vs '
                                  f'{found_topic} for {topic_name}')
