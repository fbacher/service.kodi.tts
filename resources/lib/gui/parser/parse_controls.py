# coding=utf-8

import xml.etree.ElementTree as ET
from logging import DEBUG
from typing import ForwardRef, List

from common.logger import BasicLogger
from gui.base_parser import BaseParser
from gui.base_tags import (BaseAttributeType, control_elements, ControlElement,
                           Item, Tag)
from gui.base_tags import ElementKeywords as EK
from gui.element_parser import BaseElementParser, ElementHandler
from gui.exceptions import ParseError

module_logger = BasicLogger.get_logger(__name__)


class ParseControls(BaseParser):
    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.CONTROLS]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self, parent: BaseParser) -> None:
        super().__init__(parent)
        clz = type(self)
        self.item: Item = clz.item
        self.control_id: int = -1
        self.children: List[ForwardRef('ParseControl')] = []

    @classmethod
    def get_instance(cls, parent: BaseParser,
                     el_child: ET.Element) -> BaseParser:
        self = ParseControls(parent=parent)
        self.parse_controls(el_child)
        return self

    @property
    def control_type(self) -> ControlElement:
        return BaseParser.control_type.fget(self)

    @control_type.setter
    def control_type(self, value: ControlElement) -> None:
        BaseParser.control_type.fset(self, value)

    def parse_controls(self, controls_el: ET.Element) -> None:
        """
        Parses a 'controls' type element
        :param controls_el:
        :return:
        """
        clz = type(self)
        # clz._logger.debug(f'In parse_controls tag: {controls_el.tag}')
        el_child: ET.Element
        control_id: str = controls_el.attrib.get(BaseAttributeType.ID.value)
        if control_id is not None and len(control_id) > 0:
            self.control_id = int(control_id)
        el_children: List[ET.Element] = controls_el.findall(f'./{EK.CONTROLS.value}')
        el_children.extend(controls_el.findall(f'./{EK.CONTROL.value}'))

        #  clz._logger.debug(f'# children {len(children)}')
        for el_child in el_children:
            if el_child.tag != EK.CONTROL.value:
                raise ParseError(f'Expected {EK.CONTROL.value} not {el_child.tag}')
            parse_control: ForwardRef('ParseControl')
            parse_control = CreateControl.get_instance(self, el_child)
            if parse_control is not None:
                # clz._logger.debug(f'Adding control to self.children: {parse_control}')
                self.children.append(parse_control)

    def get_children(self) -> List[BaseParser]:
        return self.children

    def __repr__(self) -> str:

        results: List[str] = []
        control_id: str = ''
        if self.control_id != -1:
            control_id = f' id: {self.control_id}'
        result: str = f'Controls {control_id}'
        results.append(result)
        if False:
            for control in self.children:
                control: ParseControl
                result = str(control)
                results.append(result)

        return '\n'.join(results)


class CreateControl(BaseParser):

    _logger: BasicLogger = module_logger

    @classmethod
    def get_instance(cls,  parent: BaseParser,
                     control_el: ET.Element) -> ForwardRef('ParseControl'):
        """
             Determines the type of control and calls the appropriate parser to handle it

             :param parent: Window, Controls or other Control (group)
             :param control_el: Contains a Control element as determined by the caller
             :return:
         """
        # Current element should be a control. Determine control type

        control_type: ControlElement = cls.get_control_type(control_el)
        if control_type is None:
            raise ParseError(f'Expected {Tag.CONTROL.value} not {control_el.tag}')
        if control_type.name not in control_elements.keys():
            if cls._logger.isEnabledFor(DEBUG):
                cls._logger.debug(f'Expected a controltype not {control_type}')
            return
        # Once the control's type is determined, call the appropriate handler

        item: Item = control_elements[control_type]
        # cls._logger.debug(f'item: type: {type(item.key)} {item}')
        parser: BaseElementParser = ElementHandler.get_handler(item.key)
        child: ForwardRef('ParseControl') = parser(parent, control_el)
        # cls._logger.debug(str(child))
        return child


ParseControls.init_class()
CreateControl.init_class()
