# coding=utf-8
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import ForwardRef, List

from common.logger import BasicLogger
from gui import BaseParser
from gui.base_tags import control_elements, ControlElement, Item
from gui.element_parser import ElementHandler
from gui.parser.parse_control import ParseControl
from gui.parser.parse_item_layout import ParseItemLayout
from gui.parser.parse_topic import ParseTopic

module_logger = BasicLogger.get_logger(__name__)


class ParseFocusedLayout(ParseItemLayout):
    """

        Tag 	Description
        id
        visible
        control
        topic

    """

    item: Item = control_elements[ControlElement.FOCUSED_LAYOUT]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        #  cls._logger.debug(f'Registering with ElementHandler')
        ElementHandler.add_handler(ControlElement.FOCUSED_LAYOUT,
                                   cls.get_instance)

    def __init__(self, parent: ParseControl) -> None:
        super().__init__(parent)
        self.topic: ParseTopic | None = None
        self.description: str = ''
        self.condition: str = ''
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
                     el_item_layout: ET.Element) -> ForwardRef('ParseFocusedLayout'):
        self = ParseFocusedLayout(parent)
        self.parse_focused_layout(el_item_layout)
        return self

    def parse_focused_layout(self, el_item_layout: ET.Element):
        """
        Parse the 'itemlayout' control

        :param el_item_layout:
        :return:
        """
        clz = type(self)

        self.parse_item_layout_worker(el_item_layout)
        self.parent.focused_layouts.append(self)

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
            condition_str = f'\n condition: {self.condition_expr}'

        results: List[str] = []
        result: str = (f'\nParseFocusedLayout type: {self.control_type} '
                       f'id: {self.control_id}'
                       f'{topic_str}'
                       f'{description_str}'
                       f'{condition_str}'
                       f'\n#children: {len(self.children)}'
                       )
        results.append(result)

        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        results.append(f'\nEND ParseFocusedLayout')

        return '\n'.join(results)
