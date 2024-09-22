# coding=utf-8

import xml.etree.ElementTree as ET
from enum import StrEnum
from typing import ForwardRef, List, Tuple

from common.logger import BasicLogger, DEBUG_XV
from gui import BaseParser
from gui.base_tags import (control_elements, BaseAttributeType as BAT,
                           ControlElement, ElementKeywords as EK, Item)
from gui.element_parser import BaseElementParser, ElementHandler
from gui.parser.parse_control import ParseControl
from gui.parser.parse_topic import ParseTopic

module_logger = BasicLogger.get_logger(__name__)


class ParseItemLayout(ParseControl):
    """

        Tag 	Description
        id
        visible
        control
        topic

    """
    item: Item = control_elements[ControlElement.ITEM_LAYOUT]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        cls._logger.debug(f'Registering with ElementHandler')
        ElementHandler.add_handler(ControlElement.ITEM_LAYOUT, cls.get_instance)

    def __init__(self, parent: ParseControl) -> None:
        super().__init__(parent)
        self.topic: ParseTopic | None = None
        self.condition_expr: str = ''
        self.description: str = ''

        """
        <itemlayout width="250" height="29" condition="true">
                <control type="image">
                        <left>5</left>
                        <top>3</top>
                        <width>22</width>
                        <height>22</height>
                        <info>ListItem.Icon</info>
                </control>
                <control type="label">
                        <left>30</left>
                        <top>3</top>
                        <width>430</width>
                        <height>22</height>
                        <font>font13</font>
                        <aligny>center</aligny>
                        <selectedcolor>green</selectedcolor>
                        <align>left</align>
                        <info>ListItem.Label</info>
                </control>
        """
        self.children: List[ParseControl] = []

    @classmethod
    def get_instance(cls, parent: ParseControl,
                     el_item_layout: ET.Element) -> ForwardRef('ParseItemLayout'):
        self = ParseItemLayout(parent)
        self.parse_item_layout(el_item_layout)
        return self

    def parse_item_layout(self, el_item_layout: ET.Element):
        """
        Parse the 'itemlayout' control

        :param el_item_layout:
        :return:
        """
        clz = type(self)
        self.parse_item_layout_worker(el_item_layout)
        self.parent.item_layouts.append(self)

    def parse_item_layout_worker(self, el_item_layout: ET.Element) -> None:
        """
        Parse the 'itemlayout' or 'focusedlayout' control
        Note that ParseFocusedLayout extends this class and also calls
        this method. The caller appends the result to its parent

        :param el_item_layout:
        :return:
        """
        clz = type(self)
        self.control_type = ControlElement.ITEM_LAYOUT
        control_id_str: str = el_item_layout.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            super().control_id = control_id

        condition_str: str = el_item_layout.attrib.get(BAT.CONDITION)
        if condition_str is not None:
            self.condition_expr = condition_str

        SUPPORTED_CONTROL_TYPES: Tuple[str, str] = (ControlElement.LABEL_CONTROL,
                                                    ControlElement.IMAGE)
        # DEFAULT_TAGS: Tuple[str, ...] = (EK.DESCRIPTION, EK.VISIBLE)
        # DEFAULT_FOCUS_TAGS: Tuple[str, ...] = (EK.ENABLE, EK.ON_FOCUS, EK.ON_UNFOCUS)
        ITEM_LAYOUT_TAGS: Tuple[str, ...] = (EK.CONTROL,)
        tags_to_parse: Tuple[str, ...] = ((EK.TOPIC,) + ITEM_LAYOUT_TAGS)

        elements: [ET.Element] = el_item_layout.findall(f'./*')
        element: ET.Element
        for element in elements:
            if clz._logger.isEnabledFor(DEBUG_XV):
                clz._logger.debug_xv(f'element: {element.tag}'
                                                f' {element.attrib.get("type")}')
            if element.tag in tags_to_parse:
                key: str = element.tag
                control_type: ControlElement = clz.get_control_type(element)
                str_enum: StrEnum = None
                if control_type is not None:
                    str_enum = control_type
                    if control_type not in SUPPORTED_CONTROL_TYPES:
                        msg: str = ('ItemLayout can ONLY have controls of '
                                    f'type Label or Image not {key} '
                                    f'control_type: {control_type} '
                                    f'str_enum: {str_enum}')
                        clz._logger.debug(msg)
                        #  raise ParseError(msg)
                else:
                    str_enum = EK(key)
                item: Item = control_elements[str_enum]
                info_handler: BaseElementParser = ElementHandler.get_handler(str_enum)
                parsed_instance: BaseParser = info_handler(self, element)
                if clz._logger.isEnabledFor(DEBUG_XV):
                    clz._logger.debug_xv(f'parsed_item_instance: '
                                                    f'{parsed_instance}')
                if parsed_instance is not None:
                    if control_type is not None:
                        self.children.append(parsed_instance)
                    if str_enum == EK.TOPIC:
                        self.topic = parsed_instance

    def __repr__(self) -> str:
        clz = type(self)

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        description_str: str = ''
        if self.description != '':
            description_str = f'\n  description: {self.description}'

        condition_str: str = ''
        if self.condition_expr != '':
            condition_str = f'\n  condition: {self.condition_expr}'

        results: List[str] = []
        result: str = (f'\nParseItemLayout type: {self.control_type} '
                       f'id: {self.control_id}'
                       f'{description_str}'
                       f'{topic_str}'
                       f'{condition_str}'
                       f'\n#children: {len(self.children)}'
                       )
        results.append(result)

        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        results.append(f'\nEND ParseItemLayout')

        return '\n'.join(results)
