# coding=utf-8
from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import namedtuple
from typing import ForwardRef, List, Union

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from common.logger import BasicLogger
from gui.base_parser import BaseParser
from gui.base_tags import (control_elements, ControlElement,
                           Item, Tag)
from gui.element_parser import BaseElementParser, ElementHandler
from gui.exceptions import ParseError
from gui.parser.parse_controls import ParseControls

module_logger = BasicLogger.get_logger(__name__)

AttribInfo = namedtuple('attrib_info', ['attrib_name', 'attrib_value',
                                        'status'])


class ParseControl(BaseParser):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.CONTROL]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self,
                 parent: Union[ForwardRef('ParseControl'), ParseControls]
                 ) -> None:
        super().__init__(parent)
        clz = type(self)
        clz._logger.debug(f'SETTING control_id and control_type to -1 Unknown')
        self.control_id: int = -1
        self.control_type: ControlElement = ControlElement.UNKNOWN
        self.children: List[BaseParser] = []
        self.attributes_with_values: List[str] = clz.item.attributes_with_values
        self.attributes: List[str] = clz.item.attributes
        #  self.parent: Union[ForwardRef('ParseControl'), ParseControls] = parent
        self.visible_expr: str = ''

    '''
    @property
    def control_id(self) -> ControlElement:
        return BaseParser.control_type.fget(self)

    @control_id.setter
    def control_id(self, value: ControlElement) -> None:
        BaseParser.control_type.fset(self, value)

    @property
    def control_type(self) -> ControlElement:
        return BaseParser.control_type.fget(self)

    @control_type.setter
    def control_type(self, value: ControlElement) -> None:
        BaseParser.control_type.fset(self, value)
    '''

    @classmethod
    def get_instance(cls, parent: BaseParser,
                     control_el: ET.Element) -> BaseParser | None:
        """
             Determines the type of control and calls the appropriate parser to handle it

             :param parent:
             :param control_el: Contains a Control element as determined by the caller
             :return:
         """
        # Current element should be a control. Determine control type

        control_type: ControlElement = cls.get_control_type(control_el)
        if control_type is None:
            raise ParseError(f'Expected {Tag.CONTROL.value} not {control_el.tag}')
        str_enum: StrEnum = None
        if control_type is not None:
            str_enum = control_type
        item: Item = control_elements[str_enum]
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
