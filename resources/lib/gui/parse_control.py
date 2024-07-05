
# coding=utf-8

import xml.etree.ElementTree as ET
from collections import namedtuple
from enum import auto, Enum
from typing import Callable, Dict, ForwardRef, List, Tuple, Union

from common.logger import BasicLogger
from gui.base_control import BaseControl
from gui.base_parser import BaseParser
from gui.base_tags import (control_elements, control_elements, ControlType,
                           ElementKeywords, ElementType, Item, Items, Tag)
from gui.base_tags import BaseAttributeType as BAT
from gui.base_tags import ElementKeywords as EK
from gui.element_parser import BaseElementParser, ElementHandler
from gui.exceptions import ParseError
from gui.parse_controls import ParseControls

module_logger = BasicLogger.get_module_logger(module_path=__file__)

AttribInfo = namedtuple('attrib_info', ['attrib_name', 'attrib_value',
                                         'status'])


class ParseControl(BaseParser):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.CONTROL.name]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)
        ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self,
                 parent: Union[ForwardRef('ParseControl'), ParseControls]
                 ) -> None:
        super().__init__(parent)
        clz = type(self)
        self.control_id: int = -1
        self.control_type: ControlType = ControlType.UNKNOWN
        self.children: List[BaseParser] = []
        self.attributes_with_values: List[str] = clz.item.attributes_with_values
        self.attributes: List[str] = clz.item.attributes
        self.parent: Union[ForwardRef('ParseControl'), ParseControls] = parent
        self.visible_expr: str = ''

    @classmethod
    def get_instance(cls, parent: BaseParser,
                     control_el: ET.Element) -> BaseParser | None:
        """
             Determines the type of control and calls the appropriate parser to handle it

             :param item:
             :param parent:
             :param control_el: Contains a Control element as determined by the caller
             :return:
         """
        # Current element should be a control. Determine control type

        control_type: ControlType = cls.get_control_type(control_el)
        if control_type is None:
            raise ParseError(f'Expected {Tag.CONTROL.value} not {control_el.tag}')
        if control_type.name not in control_elements.keys():
            cls._logger.debug(f'Expected a controltype not {control_type}')
            return None
        # Once the control's type is determined, call the appropriate handler

        item: Item = control_elements[control_type.name]
        #  clz._logger.debug(f'item: {item.key} {item}')
        parser: BaseElementParser = ElementHandler.get_handler(item.key)
        child: ParseControl = parser(parent, control_el)
        #  cls._logger.debug(str(child))
        return child

    def get_children(self) -> List[BaseParser]:
        return self.children

    def update_children(self) -> None:
        for child in self.children:
            child: BaseParser

    def __repr__(self) -> str:
        clz = type(self)

        control_id: str = ''
        if self.control_id is not None and self.control_id > 0:
            control_id = f'id: {self.control_id}'
        visible_expr: str = ''
        if self.visible_expr is not None and len(self.visible_expr) > 0:
            visible_expr = f'\n visible_expr: {self.visible_expr}'

        result: str = (f'\nParseControl type: {self.control_type}{control_id}'
                       f'{visible_expr}'
                       f'\n  # children: {len(self.children)}')

        results: List[str] = []
        results.append(result)
        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        return '\n'.join(result)
