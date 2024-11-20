# coding=utf-8
from __future__ import annotations


try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from logging import DEBUG
from typing import Callable, ForwardRef, List, Tuple
import xml.etree.ElementTree as ET

from common.messages import Messages
from gui.base_tags import (ElementKeywords as EK, TopicElement, TopicType, ValueFromType,
                           ValueUnits)
from gui.base_tags import BaseAttributeType as BAT, TopicElement as TE

from common.logger import BasicLogger, DEBUG_V, DEBUG_XV, DISABLED
from gui import ControlElement, ParseError
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, Item
from gui.element_parser import BaseElementParser, ElementHandler
from windows.ui_constants import AltCtrlType

module_logger = BasicLogger.get_logger(__name__)


class ParseTopic(BaseParser):
    """
          <topic name="speech_engine" label="102"
                                       hinttext="Select to choose speech engine"
                        topicleft="category_keymap" topicright="" topicup="engine_settings"
                                topicdown="" rank="3">header</topic>
    :param parent:
    :return:
    """
    item: Item = control_elements[EK.TOPIC]
    _logger: BasicLogger = module_logger

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        ElementHandler.add_handler(EK.TOPIC, cls.parse_topic)

    @classmethod
    def parse_topic(cls, parent: BaseParser | None = None,
                    el_topic: ET.Element = None) -> ForwardRef('ParseTopic'):
        """
             <topic name="speech_engine" label="102" rank="3">
                                           hinttext="Select to choose speech engine"
                            topicleft="category_keymap" topicright="" topicup="engine_settings"
                                    topicdown="" rank="3">header</topic>
        """
        #  cls._logger.debug(f'ParseTopic')
        topic = ParseTopic(parent, el_topic)
        return topic

    def __init__(self, parent: BaseParser, el_topic: ET.Element = None) -> None:
        super().__init__(parent)
        clz = ParseTopic
        clz._logger.debug(f'SETTING self.control_id to parent: {parent.control_id}')
        self.control_id = parent.control_id
        self.name: str = ''
        self.alt_label_expr: str = ''
        self.container_topic: str = ''
        self.heading_label: str = ''
        self.heading_labeled_by: str = ''
        self.heading_next: str = ''
        self.label_expr: str = ''
        self.labeled_by_expr: str = ''
        self.label_for_expr: str = ''
        self.description: str = ''
        self.hint_text_expr: str = ''
        self.info_expr: str = ''
        self.inner_topic: str = ''
        self.outer_topic: str = ''
        self.flows_to: str = ''
        self.flows_from: str = ''
        self.topic_left: str = ''
        self.topic_right: str = ''
        self.topic_up: str = ''
        self.topic_down: str = ''
        self.topic_heading: str = ''
        self.topic_type: TopicType = TopicType.DEFAULT
        self._alt_type: str = ''  # Can not resolve this until TopicModels created
        # Raw from xml Topic Element Used to create alt_type, above.
        self.alt_type_expr: str = ''
        self.rank: int = -1
        self.read_next_expr: str = ''
        self.true_msg_id: int | None = None
        self.false_msg_id: int | None = None
        self.units: ValueUnits | None = None
        self.value_format: str = ''
        self.value_from: ValueFromType = ValueFromType.NONE
        self.children: List[BaseParser] = []

        # Type provides a means to voice what kind of control this is other than just
        # the Kodi standard controls, group, groupList, etc.

        self.type: str = ''  # header, custom,
        if el_topic.tag != TE.TOPIC:
            raise ParseError(f'Expected {TE.TOPIC} not {el_topic.tag}')
        name: str | None = el_topic.attrib.get(TE.NAME)
        if name is None or name == '':
            raise ParseError(f'Expected Topic name attribute')
        self.name = name

        rank_str: str | None = el_topic.attrib.get(TE.RANK)
        if rank_str is not None:
            if not rank_str.isdigit():
                clz._logger.info(f'topic rank is not a number for topic: {self.name} '
                                 f'from the path {self.get_xml_path()}')
            else:
                self.rank = int(rank_str)

        element: ET.Element
        #  Should add as element
        #  element = el_topic.find(f'./{EK.DESCRIPTION}')
        for tag in TopicElement:
            tag: str
            if tag == TopicElement.NAME:  # attribute
                continue
            element = el_topic.find(f'./{tag}')
            if element is not None:

                key: str = element.tag
                control_type: ControlElement = clz.get_control_type(element)
                str_enum: StrEnum = None
                if control_type is not None:
                    str_enum = control_type
                else:
                    str_enum = TE(key)  # Any valid topic element
                item: Item = control_elements[str_enum]
                # Values copied to self
                handler: Callable[[BaseParser, TopicElement], str | BaseParser]
                handler = ElementHandler.get_handler(item.key)
                parsed_instance: BaseParser = handler(self, element)
                if parsed_instance is not None:
                    self.children.append(parsed_instance)
        parent.topic = self
        #  clz._logger.debug(f'{self}')

    @property
    def control_type(self) -> ControlElement:
        return BaseParser.control_type.fget(self)

    @control_type.setter
    def control_type(self, value: ControlElement) -> None:
        BaseParser.control_type.fset(self, value)

    @property
    def alt_type(self) -> str:
        """
        Creates alternate type string during creation of Topic Models.
        This is due to it being awkward to create sooner.

        :return:
        """
        clz = ParseTopic
        msg_id: int = -1
        clz._logger.debug_xv(f'alt_type_expr: |{self.alt_type_expr}|')
        # If not defined, get default translated value for control
        if self.alt_type_expr is None or self.alt_type_expr == '':
            alt_ctrl_type: AltCtrlType
            alt_ctrl_type = AltCtrlType.get_default_alt_ctrl_type(self.parent.control_type)
            if clz._logger.isEnabledFor(DISABLED):
                clz._logger.debug(f'alt_type based on atl_type_expr: {self.alt_type_expr} '
                                  f'now: {alt_ctrl_type} parent.control_type: '
                                  f'{self.parent.control_type}')
            msg_id = alt_ctrl_type.value
            if clz._logger.isEnabledFor(DISABLED):
                clz._logger.debug(f'default alt_type for control ctrl_id: '
                                  f'{self.parent.control_id} '
                                          f'{self.parent.control_type} '
                                          f'alt_ctrl_type: {alt_ctrl_type} '
                                          f'msg_id: {msg_id}')
        elif self.alt_type_expr.isdigit():
            msg_id = int(self.alt_type_expr)
            clz._logger.debug_xv(f'isdigit msg_id: {msg_id}')
        else:
            try:
                alt_type: AltCtrlType
                alt_type = AltCtrlType.get_alt_type_for_name(self.alt_type_expr)
                if clz._logger.isEnabledFor(DEBUG):
                    clz._logger.debug(f'alt_type: {alt_type} alt_type_str: '
                                              f'{alt_type.get_message_str()}')
                self._alt_type = alt_type.get_message_str()
            except ValueError:
                msg_id = -1
        if msg_id > 0:
            self._alt_type = Messages.get_msg_by_id(msg_id)
            clz._logger.debug(f'final alt_type: {self._alt_type}')
        return self._alt_type

    def __repr__(self) -> str:
        clz = type(self)

        name_str: str = ''
        if self.name != '':
            name_str = f'\n  name_str: {self.name}'

        label_expr: str = ''
        if self.label_expr != '':
            label_expr = f'\n  label_expr: {self.label_expr}'
        labeled_by_str: str = ''
        if self.labeled_by_expr != '':
            labeled_by_str = f'\n  labeled_by: {self.labeled_by_expr}'

        label_for_str: str = ''
        if self.label_for_expr != '':
            label_for_str = f'\n  label_for_expr: {self.label_for_expr}'
        alt_label_str: str = ''
        if self.alt_label_expr != '':
            alt_label_str = f'\n  alt_label_expr: {self.alt_label_expr}'
        info_expr: str = ''
        if len(self.info_expr) > 0:
            info_expr = f'\n  info_expr: {self.info_expr}'

        description_str: str = ''
        if self.description != '':
            description_str = f'\n  description: {description_str}'

        hint_text_str: str = ''
        if self.hint_text_expr != '':
            hint_text_str = f'\n  hint_text_expr: {self.hint_text_expr}'

        flows_to_str: str = ''
        if self.flows_to != '':
            self.flows_to_str = f'\n  flows_to: {self.flows_to}'

        flows_from_str: str = ''
        if self.flows_from != '':
            self.flows_from_str = f'\n  flows_from: {self.flows_from}'

        topic_heading_str: str = ''
        if self.topic_heading != '':
            topic_heading_str = f'\n  topic_heading: {self.topic_heading}'

        heading_label_str: str = ''
        if self.heading_label != '':
            heading_label_str = f'\n  heading_label: {self.heading_label}'

        heading_labeled_by_str: str = ''
        if self.heading_labeled_by != '':
            heading_labeled_by_str = f'\n  heading_labeled_by: {self.heading_labeled_by}'

        heading_next_str: str = ''
        if self.heading_next != '':
            heading_next_str = f'\n  heading_next: {self.heading_next}'

        topic_type_str: str = ''
        if self.topic_type != '':
            topic_type_str = f'\n  topic_type: {self.topic_type}'

        outer_topic_str: str = ''
        if self.outer_topic != '':
            outer_topic_str = f'\n  outer_topic: {self.outer_topic}'

        inner_topic_str: str = ''
        if self.inner_topic != '':
            inner_topic_str = f'\n  inner_topic: {self.inner_topic}'

        topic_up_str: str = ''
        if self.topic_up != '':
            topic_up_str = f'\n  topic_up: {self.topic_up}'

        topic_down_str: str = ''
        if self.topic_down != '':
            topic_down_str = f'\n  topic_down: {self.topic_down}'

        topic_left_str: str = ''
        if self.topic_left != '':
            topic_left_str = f'\n  topic_left: {self.topic_left}'

        topic_right_str: str = ''
        if self.topic_right != '':
            topic_right_str = f'\n  topic_right: {self.topic_right}'

        topic_right_str: str = ''
        if self.topic_right != '':
            topic_right_str = f'\n  topic_right: {self.topic_right}'

        alt_type_str: str = ''
        if self.alt_type_expr != '':
            alt_type_str = f'\n  alt_type: {self.alt_type_expr}'

        rank_str: str = ''
        if self.rank > -1:
            rank_str = f'\n  rank: {self.rank}'

        units_str = ''
        if self.units is not None:
            units_str = f'\n {self.units}'

        results: List[str] = []
        result: str = (f'\nParseTopic:  {name_str}'
                       f'{label_expr}'
                       f'{labeled_by_str}'
                       f'{label_for_str}'
                       f'{alt_label_str}'
                       f'{info_expr}'
                       f'{description_str}'
                       f'{hint_text_str}'
                       f'{flows_to_str}'
                       f'{flows_from_str}'
                       f'{topic_up_str}'
                       f'{topic_down_str}'
                       f'{topic_left_str}'
                       f'{topic_right_str}'
                       f'{topic_heading_str}'
                       f'{heading_label_str}'
                       f'{heading_labeled_by_str}'
                       f'{heading_next_str}'
                       f'{outer_topic_str}'
                       f'{inner_topic_str}'
                       f'{topic_type_str}'
                       f'{alt_type_str}'
                       f'{rank_str}'
                       f'{units_str}'
                       f'\n #children: {len(self.children)}'
                       )
        results.append(result)

        for child in self.children:
            child: BaseParser
            results.append(str(child))

        results.append(f'\nEND ParseTopic')
        return '\n'.join(results)


ParseTopic.init_class()
