# coding=utf-8

import xml.etree.ElementTree as ET
from logging import DEBUG
from typing import Dict, ForwardRef, List, Tuple, Union

import xbmc

from common.logger import BasicLogger, DEBUG_VERBOSE, DISABLED
from gui import ParseError
from gui.i_model import IModel

from gui.base_topic_model import BaseTopicModel
from gui.no_topic_models import BaseFakeTopic
from utils import util
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)
tts_logger: BasicLogger = BasicLogger.get_addon_logger()
scraper_logger = tts_logger.getChild('gui')


scraper_logger.info(f'scraper_logger: {scraper_logger.name}'
                    f' parent: {scraper_logger.parent}')
scraper_logger.debug(f'scraper_logger: {scraper_logger.name}'
                     f' parent: {scraper_logger.parent}')

scraper_logger.debug_verbose('debug_verbose')
scraper_logger.debug_extra_verbose('extra_verbose')

tts_logger.info('tts_logger info')
tts_logger.debug_verbose('tts_logger debug_verbose')
tts_logger.debug_extra_verbose('tts_logger extra_verbose')

module_logger.info(f'module_logger: {module_logger.name} '
                   f'parent: {module_logger.parent}')
module_logger.debug(f'Ho imo')
module_logger.debug_verbose('verbose')
module_logger.debug_extra_verbose('extra verbose')


class WindowStructure:
    """
        Manages the Nodes (controls/topics) in a window. Provides lookup
        of nodes by control_id, and topic_id. Maintains the relationship
        between nodes so that you can determine, for example, all of the
        nodes between a given node and the root (very useful to find which
        nodes may need to be voiced based on a change made to the currelty
        focused node, etc.)

    """
    # _logger: BasicLogger = Logger.get_logger(Logger.SCRAPER)
    _logger: BasicLogger = module_logger
    _window_struct_map: Dict[int, ForwardRef('WindowStructure')] = {}

    def __init__(self, window: IModel) -> None:
        clz = WindowStructure
        if clz._logger is None:
            clz._logger = module_logger

        self.window: IModel = window
        clz._logger.debug(f'window_id: {window.control_id}')
        clz._window_struct_map[window.control_id] = self
        self._root_topic: BaseTopicModel = window.topic
        self.window_topic_id: str = window.topic.topic_id

        self.test_node_list: List[IModel] = []  # For testing
        self.topic_by_tree_id: Dict[str, BaseTopicModel] = {}
        self.topic_by_topic_name: Dict[str, BaseTopicModel] = {}
        #  self.ordered_topics_by_name: Dict[str, BaseTopicModel] = {}
        self._windialog_state: WinDialogState = None

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
        self._model_for_control_id: Dict[int, IModel] = {}
        #  self.control_stack_map: Dict[str, List[IModel]] = {}

        self.build_control_tree(node=window, level=0)
        parents: List[IModel] = [window]
        #  self.build_parent_list_map(window, parents)
        #  self.build_topic_maps()

        self.test_window_id_map()
        self.test_get_control_and_topic_for_id()
        clz._logger.debug(f'Finished WindowStructure init')

    def set_windialog_state(self, windialog_state: WinDialogState) -> None:
        self._windialog_state: WinDialogState = windialog_state

    @classmethod
    def get_window_struct(cls, window_id: int) -> ForwardRef('WindowStructure'):
        cls._logger.debug(f'window_id: {window_id}')
        return cls._window_struct_map.get(window_id, None)

    @property
    def windialog_state(self) -> WinDialogState:
        return self._windialog_state

    @property
    def focus_changed(self) -> bool:
        return self._windialog_state.focus_changed

    @property
    def root_topic(self) -> BaseTopicModel | None:
        """
        Returns the root_topic node for this window/dialog.
        The root topic represents the Window/Dialog

        :return:
        """
        return self._root_topic

    def get_model_for_control_id(self, control_id: int) -> IModel | None:
        if not isinstance(control_id, int):
            raise ValueError('control_id must be int')
        return self._model_for_control_id.get(control_id, None)

    def set_model_for_control_id(self, control_id: int, value: IModel) -> None:
        if not isinstance(control_id, int):
            raise ValueError('control_id must be int')
        self._model_for_control_id[control_id] = value

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
        the traversal. The tree_id is set to the node's control_id, if it exiss (>0)
        Otherwise, it is manufatured from the position of the node in the tree.

        :param node: BasicModel node to add to the tree.
        :param level: Incremented on each recursion. Used to help generate names
                     for un-named nodes
        :param child_idx: Incremented for each child node visited.
        :return:
        """
        # Window control ALWAYS has an ID. Tree_id assigned in constructor

        clz = WindowStructure
        clz._logger.debug(f'In build_control_tree')
        topic_str: str = ''
        self.test_node_list.append(node)
        if node.topic is not None and node.topic.is_real_topic:
            clz._logger.debug(f'REAL TOPIC: {node.topic}')
            topic_str: str = f'{node.topic}'
        else:
            clz._logger.debug(f'UNREAL TOPIC: {node.topic} control_id:'
                              f' {node.control_id} node: {node}')

        clz._logger.debug_verbose(
                f'topic: {topic_str} '
                f' control_id: {node.control_id}'
                f' control_id type: {type(node.control_id)} '
                f' type: {type(node)} parent: {type(node)}')
        if node.control_id >= 0:
            self.set_model_for_control_id(node.control_id, node)
            node.tree_id = f'{node.control_id}'
            clz._logger.debug(f'added node: {node.control_id} to model_for_control_id')
        else:  # Control_id is invalid.
            #  Generate fake ID for controls which don't have an explicit ID
            node.tree_id = f'L{level}C{child_idx}'
        topic_str: str = ''
        if node.topic is not None:
            topic_str = node.topic.name
        clz._logger.debug(f'Working on tree_id: {node.tree_id}  topic: {topic_str}'
                          f'{node}')

        try:
            # Copy tree_id to any topic linked to the node. But
            # ignore 'fake' topics (manufactured dummy ones to simplify code)
            if node.topic is not None and node.topic.is_real_topic:
                clz._logger.debug(f'REAL TOPIC: {node.topic}')
                node.topic.tree_id = node.tree_id
                if self.root_topic is None:
                    clz._logger.error('root_topic not set')
                    raise ParseError('root topic not set')

                if node.tree_id in self.topic_by_tree_id.keys():
                    clz._logger.debug(f'Dupe topic tree_id: {node.tree_id}')
                    raise ET.ParseError(f'Duplicate topic by tree_id: '
                                        f'{node.tree_id} '
                                        f'topic: {node.topic.name}')

                # Add non-fake topic to topic map indexed by tree_id

                clz._logger.debug(f'Adding node: {node.tree_id} to topic_by_tree_id')
                self.topic_by_tree_id[node.tree_id] = node.topic

                clz._logger.debug(f'Adding topic: {node.topic.name} id:'
                                  f' {node.tree_id}')
                clz._logger.debug_verbose(f'{node.topic}\n{node.topic.parent}')

                if node.topic.name in self.topic_by_topic_name.keys():
                    raise ET.ParseError(f'Duplicate topic name: {node.topic.name}')

                # Add non-fake topic to topic map indexed by topic name

                self.topic_by_topic_name[node.topic.name] = node.topic

                # Add control node to window_id_map indexed by tree_id

                self.window_id_map[node.tree_id] = node
            else:
                clz._logger.debug(f'UNREAL TOPIC: {node.topic}')
        except ET.ParseError:
            clz._logger.exception(f'Ignoring topic {node.topic.name}')
        except Exception:
            clz._logger.exception(f'Ignoring topic {node.topic.name}')

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
        #  clz._logger.debug(f'parents: # {len(parents)}')
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
        root_topic: BaseTopicModel = self.root_topic
        topic: ForwardRef('BaseTopicModel') = root_topic
        while topic is not None:
            if topic.name == '':
                raise ET.ParseError(f'Topic.name is empty')

            if topic in self.ordered_topics_by_name:
                continue
            self.ordered_topics_by_name[topic.name] = topic
            try:
                if not topic.is_real_topic or topic.topic_right == '':
                    clz._logger.debug(f'Topic topic_right is empty for topic: '
                                      f'{topic.name}')
                elif topic.topic_right in self.topic_by_topic_name:
                    topic = self.topic_by_topic_name[topic.topic_right]
                else:
                    topic = None  # Navigation will not advance right
                    continue
            except Exception as e:
                clz._logger.exception('')
                raise ET.ParseError(f'Topics are NOT traversable. name not found '
                                    f'topic: {topic}\n size of topic_by_topic_name: '
                                    f'{len(self.topic_by_topic_name)}')
            if topic.name == root_topic.name:
                clz._logger.debug_verbose(f'Reached root topic.')
                break
    '''

    def get_control_and_topic_for_id(self,
                                     control_topic_id_or_tree_id: str) \
            -> Tuple[ForwardRef('IModel'), ForwardRef('BaseBaseTopicModel')]:
        """
            Fetches any control and/or topic that has a matching:
                control_id (numeric)
                topic_id (topic name)
                tree_id (rarely used)

        :param control_topic_id_or_tree_id:
        :return:  control, topic
        """
        clz = WindowStructure

        search_id: str = control_topic_id_or_tree_id
        clz._logger.debug(f'In get_control_and_topic_for_id search: {search_id}')
        clz._logger.debug(f'{self}')

        if search_id == '':
            return None, None

        topic: ForwardRef('BaseTopicModel') = None
        control: ForwardRef('IModel') = None

        # Try to search by numeric control id
        control_id: str = search_id
        control = self.get_control_model(control_id)
        if control is None:
            clz._logger.debug(f'Did NOT find control {control_id} '
                              f'window.control_id: {self.window.control_id}')
        if control is not None:
            topic = control.topic
            clz._logger.debug(f'get_control_model returns: control: {control} topic {topic}')
        else:
            # Perhaps search_id is actually a topic name or tree-id.
            # There is no search for controls by that, but probably not
            # a big deal. All topics have topic ids so we should be able to
            # find both topic and control from it. tree_ids are explicitly for
            # controls without ids, so you can't find them from that
            topic = self.topic_by_topic_name.get(search_id)
            if topic is None:
                topic = self.topic_by_tree_id.get(search_id)
            if topic is not None:
                control = topic.parent
        if topic is not None:
            # clz._logger.debug(f'topic {topic}')
            if not topic.is_real_topic or not topic.is_new_topic:
                clz._logger.debug_verbose(f'topic is_real: {topic.is_real_topic} '
                                          f'{topic.is_new_topic}')
                topic = None
        return control, topic

    def get_topic_for_id(self,
                         ctrl_topic_or_tree_id: str)\
            -> Tuple[ForwardRef('IModel'), ForwardRef('BaseTopicModel')]:
        """
        Retrieves a topic (if it exists) given one of:
                control_id (must be an int)
                topic_id (topic name)
                tree_id
        :param ctrl_topic_or_tree_id:
        :return:
        """
        clz = WindowStructure
        control_model: IModel = None
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'ctrl_topic_or_tree_id: {ctrl_topic_or_tree_id}')
        control_id: int = util.get_non_negative_int(ctrl_topic_or_tree_id)
        if control_id != -1:
            clz._logger.debug(f'got model for {ctrl_topic_or_tree_id}')
            control_model = self.get_control_model(control_id)
        topic: ForwardRef('BaseTopicModel') = None
        topic = self.topic_by_topic_name.get(ctrl_topic_or_tree_id)
        if topic is None:
            clz._logger.debug(f'topic not found for topic name {ctrl_topic_or_tree_id}')
            # TODO: Merge topic_by_tree_id with topic_by_topic_name
            topic = self.topic_by_tree_id.get(ctrl_topic_or_tree_id)
            if topic is None:
                clz._logger.debug(f'topic not found for tree_id: {ctrl_topic_or_tree_id}')
            else:
                clz._logger.debug(
                    f'got topic from topic_by_tree_id from {ctrl_topic_or_tree_id} '
                    f'topic: {topic}')
        else:
            pass
            clz._logger.debug(f'got topic from topic_by_topic_name from '
                              f'{ctrl_topic_or_tree_id}')
        # if topic is not None:
        #     clz._logger.debug(f'control from topic: {topic.parent}')
        return control_model, topic

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
        clz._logger.debug(f'control_id: {control_id}')
        result = self.get_model_for_control_id(control_id)
        return result

    def get_control_model_by_tree_id(self, tree_id: str) -> IModel | None:
        return self.window_id_map.get(tree_id)

    def get_current_control_model(self) -> IModel | None:
        try:
            control_id_str: str = xbmc.getInfoLabel('System.CurrentControlId')
            return self.get_control_model(control_id_str)
        except Exception as e:
            return None

    def to_string(self, include_children: bool = False) -> str:
        return ''

    '''
            self.topic_by_tree_id: Dict[str, BaseTopicModel] = {}
            self.topic_by_topic_name: Dict[str, BaseTopicModel] = {}

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
            topic: BaseTopicModel
            expected_topic_name: str | None = None
            if node.topic is not None:
                expected_topic_name = node.topic.name

            if node.control_id > 0:
                node_id = f'{node.control_id}'
                control, topic = self.get_control_and_topic_for_id(node_id)
                if control is None:
                    clz._logger.debug(f'Error: Should have found control {node_id}')
                elif f'{control.control_id}' != node_id:
                    clz._logger.debug(f'Error: control ids should match: '
                                      f'control_id: {control.control_id} '
                                      f'node_id: {node_id}')
                if topic is None:
                    if expected_topic_name is not None:
                        if not isinstance(node.topic, BaseFakeTopic):
                            clz._logger.debug(f'Topic node not found '
                                              f'expected: {expected_topic_name}')

    def test_get_control_and_topic_for_id(self) -> None:
        clz = WindowStructure
        node: IModel
        for node in self.test_node_list:
            node_id: str = None
            control: IModel
            topic: BaseTopicModel
            expected_topic_name: str | None = None
            if node.topic is not None:
                expected_topic_name = node.topic.name

            if node.control_id > 0:
                node_id = f'{node.control_id}'
                control, topic = self.get_control_and_topic_for_id(node_id)
                if control is None:
                    clz._logger.debug(f'Error: Should have found control {node_id}')
                elif f'{control.control_id}' != node_id:
                    clz._logger.debug(f'Error: control ids should match: '
                                      f'control_id: {control.control_id} '
                                      f'node_id: {node_id}')
                if topic is None:
                    if expected_topic_name is not None:
                        if not isinstance(node.topic, BaseFakeTopic):
                            clz._logger.debug(f'Topic node not found '
                                              f'expected: {expected_topic_name}')

            if node.topic is not None:
                topic: BaseTopicModel
                topic = node.topic
                found_topic: BaseTopicModel
                self.test_find_topic(topic.name)
                self.test_find_topic(topic.flows_to)
                self.test_find_topic(topic.flows_from)
                self.test_find_topic(topic.labeled_by)
                self.test_find_topic(topic.label_for)
                self.test_find_topic(topic.outer_topic)
                self.test_find_topic(topic.inner_topic)

    def test_find_topic(self, topic_name: str) -> None:
        clz = WindowStructure
        if topic_name is None or topic_name == '':
            return
        found_topic: BaseTopicModel
        control, found_topic = self.get_control_and_topic_for_id(topic_name)
        if found_topic is None:
            if not topic_name.startswith(f'Fake_topic'):
                clz._logger.debug(f'Error: Should have found topic {found_topic} '
                                  f'for topic: {topic_name}')
            else:
                # clz._logger.debug(f'topic: {topic_name} gives FakeTopic')
                pass
        elif found_topic.name != topic_name:
            clz._logger.debug(f'Error: Topics not identical: {topic_name} vs '
                              f'{found_topic} for {topic_name}')
