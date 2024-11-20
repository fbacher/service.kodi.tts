# coding=utf-8
from __future__ import annotations

import xml.etree.ElementTree as ET

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from typing import Callable, ForwardRef, List, Tuple

from common.logger import BasicLogger
from gui import ControlElement
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ElementKeywords as EK, TopicElement as TE, Item
from gui.element_parser import ElementHandler
from gui.parser.parse_control import ParseControl
from gui.parser.parse_topic import ParseTopic

module_logger = BasicLogger.get_logger(__name__)


class ParseRadioButton(ParseControl):
    """
        label 	The label used on the button. It can be a link into strings.po,
                        or an actual text label.
        label2 	Optional. Will display an 'on' or 'off' label. Only available if you
                        specify an empty radiowidth and radioheight.
        onclick 	The function to perform when the radio button
                        is clicked. Should be a built in function.
        onfocus 	Specifies the action to perform when the button is focused. Should
                    be a built in function. The action is performed after any
                    focus animations have completed. See here for more information.
        onunfocus 	Specifies the action to perform when the button loses focus. Should
                    be a built in function.
    """
    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.RADIO_BUTTON]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self, parent: ParseControl) -> None:
        """
        Parses the xml for a RadioButton Control
        :param parent:

        """
        super().__init__(parent)
        clz = ParseRadioButton
        clz._logger.debug(f'SETTING self.control_type to RADIO_BUTTON')
        self.control_type = ControlElement.RADIO_BUTTON
        self.topic: ParseTopic | None = None
        self.description: str = ''
        self.enable_expr: str = ''
        self.label2_expr: str = ''
        self.label_expr: str = ''
        self.labeled_by_expr: str = ''
        self.selected_expr: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.visible_expr: str = ''
        self.wrap_multiline: bool = False
        self.alt_label_expr: str = ''
        self.hint_text_expr: str = ''
        self.on_info_expr: str = ''

    @property
    def control_type(self) -> ControlElement:
        return BaseParser.control_type.fget(self)

    @control_type.setter
    def control_type(self, value: ControlElement) -> None:
        BaseParser.control_type.fset(self, value)

    @classmethod
    def get_instance(cls, parent: ParseControl,
                     el_button: ET.Element) -> ForwardRef('ParseRadioButton'):
        self = ParseRadioButton(parent)
        self.parse_radio_button(el_button)
        return self

    def parse_radio_button(self, el_button: ET.Element) -> None:
        """
        Parse the 'radiobutton' control

        :param el_button:
        :return:
        """
        clz = type(self)

        self.control_type = ControlElement.RADIO_BUTTON
        control_id_str: str = el_button.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            self.control_id = control_id
            clz._logger.debug(
                f'SETTING {self.control_type} self.control_id to {control_id} '
                f'control_id_str: {control_id_str}')

        tags_to_parse: Tuple[str, ...] = (TE.TOPIC, EK.VISIBLE, EK.SELECTED,
                                          EK.ENABLE, EK.WRAP_MULTILINE,
                                          EK.ON_CLICK, EK.DESCRIPTION, EK.LABEL,
                                          EK.LABEL2, EK.ON_CLICK, EK.ON_FOCUS,
                                          EK.ON_UNFOCUS, EK.ON_INFO)
        elements: [ET.Element] = el_button.findall(f'./*')
        element: ET.Element
        for element in elements:
            if element.tag in tags_to_parse:
                # clz._logger.debug(f'element_tag: {element.tag}')
                key: str = element.tag
                control_type: ControlElement = clz.get_control_type(element)
                str_enum: StrEnum = None
                if control_type is not None:
                    str_enum = control_type
                else:
                    str_enum = EK(key)  # TE.TOPIC also in EK
                item: Item = control_elements[str_enum]

                # Values copied to self
                handler: Callable[[BaseParser, ET.Element], str | BaseParser]
                handler = ElementHandler.get_handler(item.key)
                parsed_instance: BaseParser = handler(self, element)
                if parsed_instance is not None:
                    if control_type is not None:
                        self.children.append(parsed_instance)
                    if str_enum == EK.TOPIC:
                        self.topic = parsed_instance
            # else:
            #     if element.tag not in ('top', 'left', 'width', 'height', 'bottom'):
            #         clz._logger.debug(f'ParseRadioButton ignored element: {element.tag}')

    def __repr__(self) -> str:
        clz = type(self)
        labeled_by_str: str = ''
        if self.labeled_by_expr != '':
            labeled_by_str = f'\n labeled_by: {self.labeled_by_expr}'

        if self.on_focus_expr != '':
            on_focus_expr: str = f'\n on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr != '':
            on_unfocus_expr: str = f'\n on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''
        visible_expr: str = ''
        if self.visible_expr != '':
            visible_expr = f'\n visible_expr: {self.visible_expr}'

        description_str: str = ''
        if self.description != '':
            description_str = f'\ndescription: {self.description}'

        enable_expr_str: str = ''
        if self.enable_expr != '':
            enable_expr_str = f'\nenable: {self.enable_expr}'

        label2_expr_str: str = ''
        if self.label2_expr != '':
            label2_expr = f'\nlabel2: {self.label2_expr}'

        selected_expr_str: str = ''
        if self.selected_expr != '':
            selected_expr_str = f'\nselected: {self.selected_expr}'

        wrap_multiline_str = ''
        if self.wrap_multiline:
            wrap_multiline_str = f'\nwrap_multiline: {self.wrap_multiline}'

        alt_label_expr_str: str = ''
        if self.alt_label_expr != '':
            alt_label_expr_str = f'\nalt_label: {self.alt_label_expr}'

        hint_text_expr_str: str = ''
        if self.hint_text_expr != '':
            hint_text_expr_str = f'\nhint_text: {self.hint_text_expr}'

        on_info_expr_str: str = ''
        if self.on_info_expr != '':
            on_info_expr_str = f'\non_info: {self.on_info_expr}'

        label_expr_str: str = ''
        if self.label_expr != '':
            label_expr_str = f'\nlabel: {self.label_expr}'

        results: List[str] = []
        result: str = (f'\nParseRadioButton type: {self.control_type} '
                       f'id: {self.control_id}{labeled_by_str}'
                       f'{selected_expr_str}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'{visible_expr}{description_str}'
                       f'{enable_expr_str}'
                       f'{label_expr_str}'
                       f'{label2_expr_str}'
                       f'{wrap_multiline_str}'
                       f'{alt_label_expr_str}'
                       f'{hint_text_expr_str}'
                       f'{on_info_expr_str}'
                       f'\n #children: {len(self.children)}{visible_expr}'
                       )
        results.append(result)

        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        results.append(f'END ParseRadiobutton')
        return '\n'.join(results)


ParseRadioButton.init_class()
