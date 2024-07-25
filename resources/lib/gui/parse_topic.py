# coding=utf-8

from typing import Callable, ForwardRef, List, Tuple
import xml.etree.ElementTree as ET
from gui.base_tags import ElementKeywords as EK
from gui.base_tags import BaseAttributeType as BAT

from common.logger import BasicLogger
from gui import ControlType, ParseError
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, Item
from gui.element_parser import BaseElementParser, ControlElementHandler, ElementHandler

module_logger = BasicLogger.get_module_logger(module_path=__file__)


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
    _logger: BasicLogger = None

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)
            ElementHandler.add_handler(cls.item.key, cls.parse_topic)

    @classmethod
    def parse_topic(cls, parent: BaseParser | None = None,
                    el_topic: ET.Element = None) -> ForwardRef('ParseTopic'):
        """
             <topic name="speech_engine" label="102"
                                           hinttext="Select to choose speech engine"
                            topicleft="category_keymap" topicright="" topicup="engine_settings"
                                    topicdown="" rank="3">header</topic>
        """
        #  cls._logger.debug(f'ParseTopic')
        topic = ParseTopic(parent, el_topic)
        return topic

    def __init__(self, parent: BaseParser, el_topic: ET.Element = None) -> None:
        super().__init__(parent)
        clz = type(self)
        #  clz._logger.debug(f'ParseTopic')
        self.name: str = ''
        self.alt_label_expr: str = ''
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
        self.alt_type: str = ''
        self.rank: int = -1
        self.true_msg_id: int | None = None
        self.false_msg_id: int | None = None
        self.units: None | Tuple[str, str, float | int, float | int, float | int] = None
        self.children: List[BaseParser] = []

        # Type provides a means to voice what kind of control this is other than just
        # the Kodi standard controls, group, groupList, etc.

        self.type: str = ''  # header, custom,

        attributes_to_parse: Tuple[str, ...] = (BAT.TOPIC,
                                                BAT.LABEL,  # Used for label="32807"
                                                BAT.ALT_LABEL, BAT.ALT_TYPE,
                                                BAT.NAME, BAT.HINT_TEXT,
                                                BAT.LABEL_FOR, BAT.LABELED_BY,
                                                BAT.TRUE_MSG_ID,
                                                BAT.FALSE_MSG_ID,
                                                BAT.RANK,
                                                BAT.INNER_TOPIC,
                                                BAT.OUTER_TOPIC,
                                                BAT.FLOWS_TO,
                                                BAT.FLOWS_FROM,
                                                BAT.TOPIC_DOWN,
                                                BAT.TOPIC_UP, BAT.TOPIC_LEFT,
                                                BAT.TOPIC_RIGHT)
        tags_to_parse: Tuple[str, ...] = (EK.DESCRIPTION, EK.TOPIC)

        if el_topic.tag != EK.TOPIC:
            raise ParseError(f'Expected {EK.TOPIC} not {el_topic.tag}')

        label_attrib_str: str = el_topic.attrib.get(BAT.LABEL)
        if label_attrib_str is not None:
            self.label_expr = label_attrib_str
        if BAT.ALT_LABEL in el_topic.attrib:
            self.alt_label_expr = el_topic.attrib.get(BAT.ALT_LABEL)
        if BAT.ALT_TYPE in el_topic.attrib:
            self.alt_type = el_topic.attrib.get(BAT.ALT_TYPE)
        if BAT.NAME in el_topic.attrib:
            self.name = el_topic.attrib.get(BAT.NAME)
        if BAT.HINT_TEXT in el_topic.attrib:
            self.hint_text_expr = el_topic.attrib.get(BAT.HINT_TEXT)
        if BAT.LABEL_FOR in el_topic.attrib:
            self.label_for_expr = el_topic.attrib.get(BAT.LABEL_FOR)
        if BAT.LABELED_BY in el_topic.attrib:
            self.labeled_by_expr = el_topic.attrib.get(BAT.LABELED_BY)
        if BAT.RANK in el_topic.attrib:
            try:
                self.rank = int(el_topic.attrib.get(BAT.RANK))
                #  clz._logger.debug(f'RANK: {self.rank}')
            except Exception as e:
                clz._logger.exception('')
        if BAT.INNER_TOPIC in el_topic.attrib:
            self.inner_topic = el_topic.attrib.get(BAT.INNER_TOPIC)
        if BAT.OUTER_TOPIC in el_topic.attrib:
            self.outer_topic = el_topic.attrib.get(BAT.OUTER_TOPIC)
        if BAT.FLOWS_TO in el_topic.attrib:
            self.flows_to = el_topic.attrib.get(BAT.FLOWS_TO)
        if BAT.FLOWS_FROM in el_topic.attrib:
            self.flows_from = el_topic.attrib.get(BAT.FLOWS_FROM)
        if BAT.TOPIC_DOWN in el_topic.attrib:
            self.topic_down = el_topic.attrib.get(BAT.TOPIC_DOWN)
        if BAT.TOPIC_UP in el_topic.attrib:
            self.topic_up = el_topic.attrib.get(BAT.TOPIC_UP)
        if BAT.TOPIC_LEFT in el_topic.attrib:
            self.topic_left = el_topic.attrib.get(BAT.TOPIC_LEFT)
        if BAT.TOPIC_RIGHT in el_topic.attrib:
            self.topic_right = el_topic.attrib.get(BAT.TOPIC_RIGHT)
        if BAT.FALSE_MSG_ID in el_topic.attrib:
            self.false_msg_id = el_topic.attrib.get(BAT.FALSE_MSG_ID)
        if BAT.TRUE_MSG_ID in el_topic.attrib:
            self.true_msg_id = el_topic.attrib.get(BAT.TRUE_MSG_ID)
        if BAT.UNITS in el_topic.attrib:
            self.units = self.parse_units(el_topic.attrib.get(BAT.UNITS))

        element: ET.Element
        element = el_topic.find(f'./{EK.DESCRIPTION}')
        if element is not None:
            if element.tag in tags_to_parse:
                #  clz._logger.debug(f'element_tag: {element.tag}')
                key: str = element.tag
                control_type: ControlType = clz.get_control_type(element)
                if control_type is not None:
                    key = control_type.name
                item: Item = control_elements[key]
                # Values copied to self
                handler: Callable[[BaseParser, ET.Element], str | BaseParser]
                handler = ElementHandler.get_handler(item.key)
                parsed_instance: BaseParser = handler(self, element)
                if control_type is not None and parsed_instance is not None:
                    self.children.append(parsed_instance)
        self.parent.topic = self
        #  clz._logger.debug(f'{self}')

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
            hint_text_str = f'\n  topic: {self.hint_text_expr}'

        flows_to_str: str = ''
        if self.flows_to != '':
            self.flows_to_str = f'\n  flows_to: {self.flows_to}'

        flows_from_str: str = ''
        if self.flows_from != '':
            self.flows_from_str = f'\n  flows_from: {self.flows_from}'

        topic_up_str: str = ''
        if self.topic_up != '':
            topic_up_str = f'\n  topicup: {self.topic_up}'

        topic_down_str: str = ''
        if self.topic_down != '':
            topic_down_str = f'\n  topicdown: {self.topic_down}'

        topic_left_str: str = ''
        if self.topic_left != '':
            topic_left_str = f'\n  topicleft: {self.topic_left}'

        topic_right_str: str = ''
        if self.topic_right != '':
            topic_right_str = f'\n  topic_right: {self.topic_right}'

        topic_right_str: str = ''
        if self.topic_right != '':
            topic_right_str = f'\n  topic_right: {self.topic_right}'

        alt_type_str: str = ''
        if self.alt_type != '':
            alt_type_str = f'\n  alt_type: {self.alt_type}'

        rank_str: str = ''
        if self.rank > -1:
            rank_str = f'\n  rank: {self.rank}'

        units_str = ''
        if self.units is not None:
            units_str = (f'\n units: (scale: {self.units[0]}, type: {self.units[1]} '
                         f'step: {self.units[2]}, min: {self.units[3]}, '
                         f'max: {self.units[4]})')

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