# coding=utf-8

import xml.etree.ElementTree as ET
from typing import Callable, ForwardRef, List, Tuple

from common.logger import BasicLogger, DEBUG_VERBOSE
from gui import BaseParser
from gui.base_tags import control_elements, ControlType, ElementKeywords as EK, Item
from gui.element_parser import ElementHandler
from gui.parse_control import ParseControl
from gui.parse_topic import ParseTopic

module_logger = BasicLogger.get_module_logger(module_path=__file__)


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

    item: Item = control_elements[ControlType.SCROLL_BAR.name]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)
            ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self, parent: ParseControl) -> None:
        super().__init__(parent)
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
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'In parse_scrollbar')
        self.control_type = ControlType.SCROLL_BAR
        control_id_str: str = el_scrollbar.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            self.control_id = control_id
            self.control_id = control_id

        tags_to_parse: Tuple[str, ...] = (EK.TOPIC, EK.LABEL, EK.SCROLL, EK.NUMBER,
                                          EK.HAS_PATH, EK.INFO, EK.ACTION,
                                          EK.ORIENTATION, EK.SHOW_ONE_PAGE)
        elements: [ET.Element] = el_scrollbar.findall(f'./*')
        element: ET.Element
        for element in elements:
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
                if parsed_instance is None:
                    if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                        clz._logger.debug_verbose(f'None parser for {item.key}')
                if parsed_instance is not None:
                    if control_type is not None:
                        self.children.append(parsed_instance)
                    if key == EK.TOPIC:
                        self.topic = parsed_instance
            elif clz._logger.isEnabledFor(DEBUG_VERBOSE):
                if element.tag not in ('top', 'left', 'width', 'height', 'bottom'):
                    clz._logger.debug_verbose(f'ParseScrollbar ignored element: '
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
