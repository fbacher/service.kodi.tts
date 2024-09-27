# coding=utf-8

import xml.etree.ElementTree as ET
from enum import StrEnum
from typing import ForwardRef, List, Tuple

from common.logger import BasicLogger, DEBUG_V
from gui import BaseParser
from gui.base_tags import (control_elements, ControlElement,
                           ControlElement as CE,
                           ElementKeywords as EK, Item)
from gui.element_parser import BaseElementParser, ElementHandler
from gui.parser.parse_control import ParseControl
from gui.parser.parse_topic import ParseTopic

module_logger = BasicLogger.get_logger(__name__)


class ParseList(ParseControl):
    """

        Tag 	Description

        info 	Specifies the information that the slider controls. See here for more
                information.
        orientation 	Specifies whether this scrollbar is horizontal or vertical.
                        Defaults to vertical.
        action 	Can be volume to adjust the volume, seek to change the seek position,
                pvr.seek for timeshifting in PVR.

        id
        visible

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
    item: Item = control_elements[ControlElement.LIST]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger
        ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self, parent: ParseControl) -> None:
        super().__init__(parent)
        clz = ParseList
        clz._logger.debug(f'SETTING self.control_type to LIST')
        self.control_type = ControlElement.LIST
        self.topic: ParseTopic | None = None
        self.item_layouts: List[ForwardRef('ParseItemLayout')] = []
        self.focused_layouts: List[ForwardRef('ParseFocusedLayout')] = []
        self.orientation_expr: str = 'vertical'
        self.page_control: int = -1
        self.viewtype: str = ''  # Probably of no interest
        self.visible_expr: str = ''
        self.description: str = ''
        self.enable_expr: str = ''
        self.on_focus_expr: str = ''
        self.on_unfocus_expr: str = ''

    @property
    def control_type(self) -> ControlElement:
        return BaseParser.control_type.fget(self)

    @control_type.setter
    def control_type(self, value: ControlElement) -> None:
        BaseParser.control_type.fset(self, value)

    @classmethod
    def get_instance(cls, parent: ParseControl,
                     el_info: ET.Element) -> ForwardRef('ParseList'):
        self = ParseList(parent)
        self.parse_list(el_info)
        return self

    def parse_list(self, el_list: ET.Element):
        """
        Parse the 'label' control

        :param el_list:
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

        self.control_type = ControlElement.LIST
        control_id_str: str = el_list.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            self.control_id = control_id

        DEFAULT_TAGS: Tuple[str, ...] = (EK.DESCRIPTION, EK.VISIBLE)
        DEFAULT_FOCUS_TAGS: Tuple[str, ...] = (EK.ENABLE, EK.ON_FOCUS, EK.ON_UNFOCUS)
        LIST_CONTROL_TAGS: Tuple[str, ...] = (EK.ORIENTATION,
                                              EK.PAGE_CONTROL,
                                              CE.ITEM_LAYOUT, CE.FOCUSED_LAYOUT,
                                              EK.CONTENT, EK.PRELOAD_ITEMS
                                              )
        tags_to_parse: Tuple[str, ...] = ((EK.TOPIC,) + DEFAULT_FOCUS_TAGS +
                                          DEFAULT_TAGS + LIST_CONTROL_TAGS)

        elements: [ET.Element] = el_list.findall(f'./*')
        element: ET.Element
        for element in elements:
            if element.tag in tags_to_parse:
                if clz._logger.isEnabledFor(DEBUG_V):
                    clz._logger.debug_v(f'element_tag: {element.tag}')
                key: str = element.tag
                control_type: ControlElement
                control_type = clz.get_control_type(element)
                if clz._logger.isEnabledFor(DEBUG_V):
                    clz._logger.debug_v(f'control_type: {control_type} self: '
                                              f'{self.control_type} key: {key}')
                str_enum: StrEnum = None
                if control_type is not None:
                    str_enum = control_type
                else:
                    str_enum = EK(key)
                item: Item = control_elements[str_enum]
                info_handler: BaseElementParser
                info_handler = ElementHandler.get_handler(item.key)
                parsed_instance: BaseParser = info_handler(self, element)
                if clz._logger.isEnabledFor(DEBUG_V):
                    clz._logger.debug_v(f'adding parsed_instance:'
                                              f' {parsed_instance}')
                if parsed_instance is not None:
                    if str_enum == CE.FOCUSED_LAYOUT:
                        self.focused_layouts.append(parsed_instance)
                    elif str_enum == CE.ITEM_LAYOUT:
                        if clz._logger.isEnabledFor(DEBUG_V):
                            clz._logger.debug_v(f'Adding to item_layouts:'
                                                      f' {parsed_instance}')
                        self.item_layouts.append(parsed_instance)
                    elif control_type is not None:
                        self.children.append(parsed_instance)
                    elif str_enum == EK.TOPIC:
                        self.topic = parsed_instance

    def __repr__(self) -> str:
        """
          Convert self to a string.

          :param include_children:
          :return:
        """
        clz = type(self)
        description_str: str = ''

        if self.description != '':
            description_str = f'\n  description: {self.description}'

        visible_expr: str = ''
        if self.visible_expr is not None and len(self.visible_expr) > 0:
            visible_expr = f'\n  visible_expr: {self.visible_expr}'

        enable_str: str = ''
        if self.enable_expr != '':
            enable_str = f'\n  enable_expr: {self.enable_expr}'

        if self.on_focus_expr is not None and (len(self.on_focus_expr) > 0):
            on_focus_expr: str = f'\n  on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr is not None and (len(self.on_unfocus_expr) > 0):
            on_unfocus_expr: str = f'\n  on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''

        orientation_str: str = ''
        if self.orientation_expr != '':
            orientation_str = f'\n  orientation: {self.orientation_expr}'

        page_control_str: str = ''
        if self.page_control != -1:
            page_control_str = f'\n  page_control: {self.page_control}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        viewtype_str: str = ''
        if self.viewtype != '':
            viewtype_str = f'\n  view_type: {self.viewtype}'

        item_layouts_str: str = ''
        for item_layout in self.item_layouts:
            item_layouts_str = f' \n {item_layout}'

        focused_item_layouts_str: str = ''
        for focused_item_layout in self.focused_layouts:
            focused_item_layouts_str = f'\n {focused_item_layout}'

        results: List[str] = []
        result: str = (f'\nParseList type: {self.control_type} '
                       f'id: {self.control_id} '
                       f'{enable_str}'
                       f'{description_str}'
                       f'{visible_expr}'
                       f'{orientation_str}'
                       f'{page_control_str}'
                       f'{viewtype_str}'
                       f'{on_focus_expr}'
                       f'{on_unfocus_expr}'
                       f'{topic_str}'
                       f'{item_layouts_str}'
                       f'{focused_item_layouts_str}'
                       f'\n#children: {len(self.children)}')
        results.append(result)

        for child in self.children:
            child: BaseParser
            results.append(str(child))

        results.append('END ParseList')
        return '\n'.join(results)
