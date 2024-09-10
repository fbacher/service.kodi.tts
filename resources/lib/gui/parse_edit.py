# coding=utf-8

import xml.etree.ElementTree as ET
from enum import StrEnum
from typing import Callable, ForwardRef, List, Tuple

from common.logger import BasicLogger
from gui import ControlElement
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ElementKeywords as EK, Item
from gui.element_parser import ControlElementHandler, ElementHandler
from gui.parse_control import ParseControl
from gui.parse_topic import ParseTopic

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ParseEdit(ParseControl):
    item: Item = control_elements[ControlElement.EDIT]

    _logger: BasicLogger = None

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)
            ElementHandler.add_handler(cls.item.key, cls.get_instance)
            ControlElementHandler.add_handler(cls.item, cls.get_instance)

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
        self.topic: ParseTopic | None = None
        self.action_expr: str = ''
        # self.button
        # self.controls
        self.description: str = ''
        self.enable_expr: str = ''
        # self.group
        self.hint_text_expr: str = ''
        self.info_expr: str = ''
        self.label_expr: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        # self.on_info_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.visible_expr: str = ''

    @property
    def control_type(self) -> ControlElement:
        return BaseParser.control_type.fget(self)

    @control_type.setter
    def control_type(self, value: ControlElement) -> None:
        BaseParser.control_type.fset(self, value)

    @classmethod
    def get_instance(cls, parent: ParseControl,
                     el_edit: ET.Element) -> ForwardRef('EditParser'):
        self = ParseEdit(parent)
        self.parse_edit(el_edit)
        return self

    def parse_edit(self, el_edit: ET.Element) -> None:
        """
        Parse the 'edit' control
        label       Specifies the header text which should be shown. You should specify
            an entry from the strings.po here (either the Kodi strings.po or your skin's
            strings.po file), however you may also hardcode a piece of text also if you
            wish, though of course it will not be localized. You can use the full label
            formatting syntax and you may also specify more than one piece of information
            here by using the $INFO and $LOCALIZE formats.strings.xml)
        hinttext 	Specifies the text which should be displayed in the edit label
            control, until the user enters some text. It can be used to provide a clue as
            to what a user should enter in this control.

        :param el_edit:
        :return:
        """
        clz = type(self)
        self.control_type = ControlElement.EDIT
        control_id_str: str = el_edit.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            self.control_id = control_id

        tags_to_parse: Tuple[str, ...] = (EK.TOPIC, EK.VISIBLE,
                                          EK.ON_CLICK, EK.DESCRIPTION, EK.LABEL)
        elements: [ET.Element] = el_edit.findall(f'./*')
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
                    str_enum = EK(key)
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

    def __repr__(self) -> str:
        clz = type(self)
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

        label_expr: str = ''
        if self.label_expr != '':
            label_expr = f'\n label_expr: {self.label_expr}'
        info_expr: str = ''
        if len(self.info_expr) > 0:
            info_expr = f'\n info_expr: {self.info_expr}'

        results: List[str] = []
        result: str = (f'\nParseEdit type: {self.control_type} '
                       f'id: {self.control_id} '
                       f'{visible_expr}{label_expr}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'{info_expr}'
                       f'\n # children: {len(self.children)}')
        results.append(result)

        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        return '\n'.join(results)


ParseEdit.init_class()
