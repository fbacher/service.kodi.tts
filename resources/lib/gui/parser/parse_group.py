# coding=utf-8
import xml.etree.ElementTree as ET
from enum import StrEnum
from typing import Callable, List, Tuple

from common.logger import BasicLogger
from gui.base_parser import BaseParser
from gui.base_tags import (control_elements, ControlElement,
                           ElementKeywords as EK, TopicElement as TE, Item)
from gui.element_parser import ElementHandler
from gui.parser.parse_control import ParseControl
from gui.parser.parse_topic import ParseTopic

module_logger = BasicLogger.get_logger(__name__)


class ParseGroup(ParseControl):
    """
    Tag 	Descriptione

    """
    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.GROUP]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self, parent: ParseControl) -> None:
        clz = type(self)
        super().__init__(parent)
        #  clz._logger.debug('In ParseGroup.init')
        self.item: Item = clz.item  # instance needed for add_handler...
        self.topic: ParseTopic | None = None
        self.default_control_always: bool = False
        self.default_control_id: int = -1
        self.description: str = ''
        self.visible_expr: str = ''
        self.enable_expr: str = ''
        self.label_expr: str = ''
        self.best_tts_label_expr: str = ''
        self.alt_info_expr: str = ''

    @property
    def control_type(self) -> ControlElement:
        return BaseParser.control_type.fget(self)

    @control_type.setter
    def control_type(self, value: ControlElement) -> None:
        BaseParser.control_type.fset(self, value)

    @classmethod
    def get_instance(cls, parent: ParseControl,
                     el_group: ET.Element) -> BaseParser:
        # cls._logger.debug(f'In ParseGroup.get_instance')
        self = ParseGroup(parent)
        self.parse_group(el_group)
        return self

    def parse_group(self, el_group: ET.Element) -> None:
        """
        Parse the 'group' control

        :param el_group:
        :return:

         Group control only uses 'default_control_id', in addition to the
         default controls

         The only Default controls we care about:

            Item('label'),
            Item('wrapmultiline'),
            Item('description'),
            Item('visible'),
            # Only applies when control is focusable
            Item('onfocus'),
            Item('onunfocus'),

        """
        clz = type(self)
        # Have already determined that this is a control and that it is a
        # Group control type. Get any ID

        #  clz._logger.debug(f'In ParseGroup.parse_group')
        clz._logger.debug(f'SETTING self.control_type to GROUP')
        self.control_type = ControlElement.GROUP

        control_id_str: str = el_group.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            self.control_id = control_id
            clz._logger.debug(f'SETTING self.control_id to {control_id}')

        DEFAULT_TAGS: Tuple[str, ...] = (EK.DESCRIPTION, EK.VISIBLE)
        GROUP_CONTROL_TAGS: Tuple[str, ...] = (TE.TOPIC,
                                               EK.DEFAULT_CONTROL,
                                               EK.CONTROL,
                                               EK.CONTROLS)
        tags_to_parse: Tuple[str, ...] = DEFAULT_TAGS + GROUP_CONTROL_TAGS

        elements: [ET.Element] = el_group.findall(f'./*')
        element: ET.Element
        for element in elements:
            if element.tag in tags_to_parse:
                # clz._logger.debug(f'element_tag: {element.tag}')
                key: str = element.tag
                control_type: ControlElement = clz.get_control_type(element)
                str_enum: StrEnum = None
                if control_type is not None:
                    str_enum = control_type
                elif str_enum == TE.TOPIC:
                    str_enum = TE.TOPIC
                else:
                    str_enum = EK(key)

                item: Item = control_elements[str_enum]
                # Values copied to self
                handler: Callable[[BaseParser, ET.Element], str | BaseParser]
                handler = ElementHandler.get_handler(item.key)
                #  clz._logger.debug(f'str_enum: {str_enum} item: {item} ')
                #  clz._logger.debug(f'item_key: {item.key} handler: {handler} '
                #                    f'element: {element}')
                parsed_instance: BaseParser = handler(self, element)
                if parsed_instance is not None:
                    if control_type is not None:
                        # clz._logger.debug(f'parsed_instance: {parsed_instance} '
                        #                   f'control_type: {control_type}')
                        self.children.append(parsed_instance)
            # else:
            #     if element.tag not in ('top', 'left', 'width', 'height', 'bottom'):
            #         clz._logger.debug(f'ParseGroup ignored element: {element.tag}')

    def __repr__(self) -> str:
        clz = type(self)

        # group ONLY has default control, id, label_id. May possibly want
        # some focusable items IFF we add those for accessibility.
        # Also may add info and description

        default_control_str: str = ''
        if self.default_control_id != '':
            default_control_str = (f'\n default_control: {self.default_control_id} '
                                   f' always: {self.default_control_always}')
        visible_expr: str = ''
        if self.visible_expr != '':
            visible_expr = f'\n visible_expr: {self.visible_expr}'

        topic_str: str = ''
        if self.topic != '':
            topic_str = f'\n  Topic:{self.topic}'

        results: List[str] = []
        result: str = (f'\nParseGroup type: {self.control_type} id: {self.control_id} '
                       f'{default_control_str}{visible_expr}{topic_str}'
                       f'\n #children: {len(self.children)}')
        results.append(result)
        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        return '\n'.join(results)


ParseGroup.init_class()
