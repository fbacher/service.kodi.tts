# coding=utf-8
from enum import StrEnum
from typing import Callable, List, Tuple
import xml.etree.ElementTree as ET
from gui.base_tags import ElementKeywords as EK

from common.logger import BasicLogger
from gui import ControlElement
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, Item
from gui.element_parser import ElementHandler
from gui.parser.parse_control import ParseControl
from gui.parser.parse_topic import ParseTopic

module_logger = BasicLogger.get_logger(__name__)


class ParseButton(ParseControl):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.BUTTON]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self, parent: ParseControl) -> None:
        """
        Parses the xml for a Button Control
        :param parent:

          <control type="button">
                <description>Close Window button</description>
                <label/>
                <onclick>PreviousMenu</onclick>
                <visible>system.getbool(input.enablemouse)</visible>
            </control>
        """
        super().__init__(parent)
        self.label_expr: str = ''
        self.topic: ParseTopic | None = None
        self.alt_label_expr: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.wrap_multiline: bool = False
        self.description: str = ''
        self.visible_expr: str = ''
        self.enable_expr: str = ''
        self.hint_text_expr: str = ''
        # self.info_expr: str = ''
        # self.on_info_expr: str = ''


    @classmethod
    def get_instance(cls, parent: ParseControl,
                     el_button: ET.Element) -> BaseParser:
        self = ParseButton(parent)
        self.parse_button(el_button)
        return self

    def parse_button(self, el_button: ET.Element) -> None:
        """
        Parse the 'button' control

        :param el_button:
        :return:
        """
        clz = type(self)
        self.control_type = ControlElement.BUTTON
        control_id_str: str = el_button.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            self.control_id = control_id

        DEFAULT_TAGS: Tuple[str, ...] = (EK.DESCRIPTION, EK.VISIBLE)
        DEFAULT_FOCUS_TAGS: Tuple[str, ...] = (EK.ENABLE, EK.ON_FOCUS, EK.ON_UNFOCUS)
        BUTTON_CONTROL_TAGS: Tuple[str, ...] = (EK.LABEL,
                                                EK.WRAP_MULTILINE)
        tags_to_parse: Tuple[str, ...] = ((EK.TOPIC,) + DEFAULT_FOCUS_TAGS +
                                          DEFAULT_TAGS + BUTTON_CONTROL_TAGS)

        children: [ET.Element] = el_button.findall(f'./*')
        child: ET.Element
        for child in children:
            #  clz._logger.debug(f'child.tag: {child.tag} text: {child.text}')
            if child.tag in tags_to_parse:
                #  clz._logger.debug(f'child_tag: {child.tag}')
                key: str = child.tag
                control_type: ControlElement = clz.get_control_type(child)
                # clz._logger.debug(f'control_type: {control_type}')
                str_enum: StrEnum = None
                if control_type is not None:
                    str_enum = control_type
                else:
                    str_enum = EK(key)
                item: Item = control_elements[str_enum]
                # Values copied to self
                handler: Callable[[BaseParser, ET.Element], str | BaseParser]
                handler = ElementHandler.get_handler(item.key)
                parsed_instance: BaseParser = handler(self, child)
                if parsed_instance is not None:
                    if control_type is not None:
                        self.children.append(parsed_instance)
                    if key == EK.TOPIC:
                        self.topic = parsed_instance
            # else:
            #     if clz._logger.isEnabledFor(DEBUG_V):
            #         if child.tag not in ('top', 'left', 'width', 'height', 'bottom'):
            #             clz._logger.debug(f'ParseButton ignored element: {child.tag}')

    def __repr__(self) -> str:
        clz = type(self)
        description_str: str = ''

        if self.description != '':
            description_str = f'\n description: {self.description}'

        visible_expr: str = ''
        if self.visible_expr != '':
            visible_expr = f'\n visible_expr: {self.visible_expr}'

        enable_str: str = ''
        if self.enable_expr != '':
            enable_str = f'\n enable_expr: {self.enable_expr}'

        if self.on_focus_expr != '':
            on_focus_expr: str = f'\n on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr != '':
            on_unfocus_expr: str = f'\n on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''

        label_expr: str = ''
        if self.label_expr != '':
            label_expr = f'\n label_expr: {self.label_expr}'

        alt_label_expr: str = ''
        if self.alt_label_expr != '':
            alt_label_expr = f'\n alt_label_expr: {self.alt_label_expr}'

        hint_text_str: str = ''
        if self.hint_text_expr != '':
            hint_text_str = f'\n hint_text: {self.hint_text_expr}'

        results: List[str] = []
        result: str = (f'\nParseButton type: {self.control_type} '
                       f'id: {self.control_id} '
                       f'{description_str}'
                       f'{visible_expr}{label_expr}{alt_label_expr}{hint_text_str}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'\n wrap_multiline: {self.wrap_multiline}'
                       f'\n #children: {len(self.children)}')
        results.append(result)

        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        return '\n'.join(results)


ParseButton.init_class()
