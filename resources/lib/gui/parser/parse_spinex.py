# coding=utf-8
from __future__ import annotations

import xml.etree.ElementTree as ET

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from typing import ForwardRef, List, Tuple

from common.logger import BasicLogger
from gui import BaseParser
from gui.base_tags import control_elements, ControlElement, ElementKeywords as EK, Item
from gui.element_parser import BaseElementParser, ElementHandler
from gui.parser.parse_control import ParseControl
from gui.parser.parse_topic import ParseTopic

module_logger = BasicLogger.get_logger(__name__)


class ParseSpinex(ParseControl):
    """

        Tag 	Description

        info 	Specifies the information that the slider controls. See here for more
                information.

        action 	Can be volume to adjust the volume, seek to change the seek position,
                pvr.seek for timeshifting in PVR.

        id
        visible

        label

        oninfo 	Specifies the built-in function that should be executed when the user
                presses the info key.
        onfocus 	Specifies the built-in function that should be executed when the
                control is focussed.
        onunfocus 	Specifies the built-in function that should be executed when the
                control is loses focus.
        enable 	Specifies a condition as to when this control will be enabled. Can be
                true, false, or a condition. See Conditional Visibility for more information.
                Defaults to true.
    """
    item: Item = control_elements[ControlElement.SPIN_CONTROL_EX]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self, parent: ParseControl) -> None:
        super().__init__(parent)
        clz = ParseSpinex
        clz._logger.debug(f'SETTING self.control_type to SPIN_CONTROL_EX')
        self.control_type = ControlElement.SPIN_CONTROL_EX
        self.topic: ParseTopic | None = None
        self.action_expr: str = ''
        self.labeled_by_expr: str = ''
        self.info_expr: str = ''
        self.action_expr: str = ''
        self.orientation_expr: str = 'horizontal'
        self.visible_expr: str = ''
        self.description: str = ''
        self.enable_expr: str = ''
        self.hint_text_expr: str = ''
        self.alt_label_expr: str = ''
        self.on_focus_expr: str = ''
        self.on_info_expr: str = ''
        self.on_unfocus_expr: str = ''

    @classmethod
    def get_instance(cls, parent: ParseControl,
                     el_spinex: ET.Element) -> ForwardRef('ParseSpinex'):
        self = ParseSpinex(parent)
        self.parse_spinex(el_spinex)
        return self

    def parse_spinex(self, el_spinex: ET.Element):
        """
        Parse the 'label' control

        :param el_spinex:
        :return:
        """
        clz = type(self)
        """
             Tag 	Description
            info 	Specifies the information that the slider controls. See here for 
                    more information.
            orientation 	Specifies whether this scrollbar is horizontal or vertical. 
                    Defaults to vertical.
            action 	Can be volume to adjust the volume, seek to change the seek 
                     position, pvr.seek for timeshifting in PVR. 
        """
        control_id_str: str = el_spinex.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            self.control_id = control_id
            clz._logger.debug(
                    f'SETTING {self.control_type} self.control_id to {control_id} '
                    f'control_id_str: {control_id_str}')

        DEFAULT_TAGS: Tuple[str, ...] = (EK.DESCRIPTION, EK.VISIBLE)
        DEFAULT_FOCUS_TAGS: Tuple[str, ...] = (EK.ENABLE, EK.ON_FOCUS, EK.ON_UNFOCUS)
        SLIDER_CONTROL_TAGS: Tuple[str, ...] = (EK.ORIENTATION, EK.ACTION, EK.INFO)
        tags_to_parse: Tuple[str, ...] = ((EK.TOPIC,) + DEFAULT_FOCUS_TAGS +
                                          DEFAULT_TAGS + SLIDER_CONTROL_TAGS)

        elements: [ET.Element] = el_spinex.findall(f'./*')
        element: ET.Element
        for element in elements:
            if element.tag in tags_to_parse:
                key: str = element.tag
                control_type: ControlElement = clz.get_control_type(element)
                str_enum: StrEnum = None
                if control_type is not None:
                    str_enum = control_type
                else:
                    str_enum = EK(key)
                info_handler: BaseElementParser = ElementHandler.get_handler(key)
                parsed_instance: BaseParser = info_handler(self, element)
                if parsed_instance is not None:
                    if control_type is not None:
                        self.children.append(parsed_instance)
                    if str_enum == EK.TOPIC:
                        self.topic = parsed_instance

    def __repr__(self) -> str:
        clz = type(self)
        labeled_by_str: str = ''
        if self.labeled_by_expr != '':
            labeled_by_str = f'\n labeled_by: {self.labeled_by_expr}'

        if self.on_focus_expr is not None and (len(self.on_focus_expr) > 0):
            on_focus_expr: str = f'\n on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr is not None and (len(self.on_unfocus_expr) > 0):
            on_unfocus_expr: str = f'\n on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''
        visible_expr: str = ''
        if self.visible_expr is not None and len(self.visible_expr) > 0:
            visible_expr = f'\n visible_expr: {self.visible_expr}'

        alt_label_expr: str = ''
        if self.alt_label_expr != '':
            alt_label_expr = f'\n alt_label_expr: {self.alt_label_expr}'

        info_expr: str = ''
        if len(self.info_expr) > 0:
            info_expr = f'\n info_expr: {self.info_expr}'

        action = ''
        if len(self.action_expr) > 0:
            action = f'\n action: {self.action_expr}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nParseSpinex type: {self.control_type} '
                       f'id: {self.control_id}{labeled_by_str}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'{info_expr}'
                       f'{action}'
                       f'{visible_expr}{alt_label_expr}'
                       f'{topic_str}'
                       f'\n#children: {len(self.children)}'
                       )
        results.append(result)

        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        results.append(f'\nEND ParseSpinex')

        return '\n'.join(results)
