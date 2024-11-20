# coding=utf-8
from __future__ import annotations

import xml.etree.ElementTree as ET

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from typing import Callable, ForwardRef, List, Tuple

from common.logger import BasicLogger, DEBUG_V
from gui import BaseParser
from gui.base_tags import control_elements, ControlElement, ElementKeywords as EK, Item
from gui.element_parser import ElementHandler
from gui.parser.parse_control import ParseControl
from gui.parser.parse_topic import ParseTopic

module_logger = BasicLogger.get_logger(__name__)


class ScrollbarParser(ParseControl):

    """
    Control 	scrollbar

    The scroll bar control is used as a page control for lists, panels, wraplists,
    fixedlists, textboxes, and grouplists. You can choose the position, size,
    and look of the scroll bar.

    orientation 	Specifies whether this scrollbar is horizontal or vertical.
                    Defaults to vertical.
    showonepage 	Specifies whether the scrollbar will show if the container
                    it's controlling has just one page. Defaults to true
    """

    item: Item = control_elements[ControlElement.SCROLL_BAR]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self, parent: ParseControl) -> None:
        super().__init__(parent)
        clz = ScrollbarParser
        clz._logger.debug(f'SETTING self.control_type to SCROLL_BAR')
        self.control_type = ControlElement.SCROLL_BAR
        self.topic: ParseTopic | None = None
        self.orientation_expr: str = 'vertical'
        self.show_one_page: bool = True
        self.description: str = ''
        self.visible_expr: str = ''
        self.enable_expr: str = ''
        self.hint_text_expr: str = ''
        # self.info_expr: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        # self.on_info_expr: str = ''
        self.on_unfocus_expr: str = ''

    @property
    def control_type(self) -> ControlElement:
        return BaseParser.control_type.fget(self)

    @control_type.setter
    def control_type(self, value: ControlElement) -> None:
        BaseParser.control_type.fset(self, value)

    @classmethod
    def get_instance(cls, parent: ParseControl,
                     el_scrollbar: ET.Element) -> ForwardRef('ScrollbarParser'):
        self = ScrollbarParser(parent)
        self.parse_scrollbar(el_scrollbar)
        return self

    def parse_scrollbar(self, el_scrollbar: ET.Element) -> None:
        """
        Parse the 'scrollbar' control

        :param el_scrollbar:
        :return:
        """
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG_V):
            clz._logger.debug_v(f'In parse_scrollbar')
        self.control_type = ControlElement.SCROLL_BAR
        control_id_str: str = el_scrollbar.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            self.control_id = control_id
            self.control_id = control_id
            clz._logger.debug(f'SETTING control_id to {control_id}')

        tags_to_parse: Tuple[str, ...] = (EK.TOPIC, EK.LABEL, EK.SCROLL, EK.NUMBER,
                                          EK.HAS_PATH, EK.INFO, EK.ACTION,
                                          EK.ORIENTATION, EK.SHOW_ONE_PAGE)
        elements: [ET.Element] = el_scrollbar.findall(f'./*')
        element: ET.Element
        for element in elements:
            if element.tag in tags_to_parse:
                #  clz._logger.debug(f'element_tag: {element.tag}')
                key: str = element.tag
                control_type: ControlElement = clz.get_control_type(element)
                str_enum: StrEnum = None
                if control_type is not None:
                    str_enum = control_type
                else:
                    str_enum = EK(key)
                item: Item = control_elements[str_enum]
                # Values copied to self
                handler: Callable[[BaseParser, ET.Element], str | BaseParser]
                handler = ElementHandler.get_handler(item.key)
                parsed_instance: BaseParser = handler(self, element)
                if parsed_instance is None:
                    if clz._logger.isEnabledFor(DEBUG_V):
                        clz._logger.debug_v(f'None parser for {item.key}')
                if parsed_instance is not None:
                    if control_type is not None:
                        self.children.append(parsed_instance)
                    if str_enum == EK.TOPIC:
                        self.topic = parsed_instance
            elif clz._logger.isEnabledFor(DEBUG_V):
                if element.tag not in ('top', 'left', 'width', 'height', 'bottom'):
                    clz._logger.debug(f'ParseScrollbar ignored element: '
                                      f'{element.tag}')

    def __repr__(self) -> str:
        clz = type(self)
        visible_expr: str = ''
        if self.visible_expr is not None and len(self.visible_expr) > 0:
            visible_expr = f'\n visible_expr: {self.visible_expr}'

        show_one_page: str = f'\n show_one_page: {self.show_one_page}'

        results: List[str] = []
        result: str = (f'\nParseScrollbar type: {self.control_type} '
                       f'id: {self.control_id} {show_one_page}{visible_expr}'
                       f'\n #children: {len(self.children)}')
        results.append(result)

        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        return '\n'.join(results)


ScrollbarParser.init_class()
