# coding=utf-8
import xml.etree.ElementTree as ET
from typing import Callable, List, Tuple

from common.logger import BasicLogger
from gui.base_parser import BaseParser
from gui.base_tags import (BaseAttributeType as BAT, control_elements, ControlType,
                           ElementKeywords as EK, Item)
from gui.element_parser import ElementHandler
from gui.parse_control import ParseControl
from gui.parse_topic import ParseTopic

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ParseGroup(ParseControl):
    """
    Tag 	Descriptione

    """
    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.GROUP.name]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)
        ElementHandler.add_handler(cls.item.key, cls.get_instance)

    def __init__(self, parent: ParseControl) -> None:
        clz = type(self)
        super().__init__(parent)
        #  clz._logger.debug('In ParseGroup.init')
        self.item: Item = clz.item  # instance needed for add_handler...
        self.topic: ParseTopic | None = None
        self.default_control_always: bool = False
        self.default_control_id: int = -1
        self.alt_type_expr: str = ''
        self.description: str = ''
        self.visible_expr: str = ''
        self.enable_expr: str = ''
        self.label_expr: str = ''
        self.alt_label_expr: str = ''
        self.best_tts_label_expr: str = ''
        self.alt_info_expr: str = ''
        self.labeled_by_expr: str = ''
        self.label_for_expr: str = ''
        self.hint_text_expr: str = ''
        #  self.info_expr: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        # self.on_info_expr: str = ''
        self.on_unfocus_expr: str = ''

    @classmethod
    def get_instance(cls, parent: ParseControl,
                     el_group: ET.Element) -> BaseParser:
        # cls._logger.debug(f'In ParseGroup.get_instance')
        self = ParseGroup(parent)
        self.parse_group(el_group)
        return self

    def parse_group(self, el_group: ET.Element) -> None:
        """
        Parse the 'group' control

        :param el_group:
        :return:

         Group control only uses 'default_control_id', in addition to the
         default controls

         The only Default controls we care about:

            Item('label'),
            Item('wrapmultiline'),
            Item('description'),
            Item('visible'),
            # Only applies when control is focusable
            Item('onfocus'),
            Item('onunfocus'),

        """
        clz = type(self)
        # Have already determined that this is a control and that it is a
        # Group control type. Get any ID

        #  clz._logger.debug(f'In ParseGroup.parse_group')
        self.control_type = ControlType.GROUP
        control_id_str: str = el_group.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            self.control_id = control_id

        alt_label_str: str = el_group.attrib.get(BAT.ALT_LABEL)
        if alt_label_str is not None:
            self.alt_label_expr = alt_label_str

        alt_type_str: str = el_group.attrib.get(BAT.ALT_TYPE)
        if alt_type_str is not None:
            self.alt_type_expr = alt_type_str

        label_expr: str = el_group.attrib.get('label')
        if label_expr is not None:
            self.label_expr = label_expr

        DEFAULT_TAGS: Tuple[str, ...] = (EK.DESCRIPTION, EK.VISIBLE)
        # DEFAULT_FOCUS_TAGS: Tuple[str, ...] = (EK.ENABLE, EK.ON_FOCUS, EK.ON_UNFOCUS,
        #                                        EK.ON_INFO)
        GROUP_CONTROL_TAGS: Tuple[str, ...] = (EK.TOPIC, EK.HINT_TEXT,
                                               EK.ALT_LABEL,
                                               EK.DEFAULT_CONTROL,
                                               EK.CONTROL,
                                               EK.CONTROLS)
        tags_to_parse: Tuple[str, ...] = DEFAULT_TAGS + GROUP_CONTROL_TAGS

        elements: [ET.Element] = el_group.findall(f'./*')
        element: ET.Element
        for element in elements:
            if element.tag in tags_to_parse:
                # clz._logger.debug(f'element_tag: {element.tag}')
                key: str = element.tag
                control_type: ControlType = clz.get_control_type(element)
                if control_type is not None:
                    key = control_type.name
                item: Item = control_elements[key]
                # Values copied to self
                handler: Callable[[BaseParser, ET.Element], str | BaseParser]
                handler = ElementHandler.get_handler(item.key)
                parsed_instance: BaseParser = handler(self, element)
                if parsed_instance is not None:
                    if control_type is not None:
                        self.children.append(parsed_instance)
            # else:
            #     if element.tag not in ('top', 'left', 'width', 'height', 'bottom'):
            #         clz._logger.debug(f'ParseGroup ignored element: {element.tag}')

    def __repr__(self) -> str:
        clz = type(self)

        # group ONLY has default control, id, label_id. May possibly want
        # some focusable items IFF we add those for accessibility.
        # Also may add info and description

        default_control_str: str = ''
        if self.default_control_id != '':
            default_control_str = (f'\n default_control: {self.default_control_id} '
                                   f' always: {self.default_control_always}')
        '''
        if self.on_focus_expr is not None and (len(self.on_focus_expr) > 0):
            on_focus_expr: str = f' on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr is not None and (len(self.on_unfocus_expr) > 0):
            on_unfocus_expr: str = f' on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''
        '''
        visible_expr: str = ''
        if self.visible_expr != '':
            visible_expr = f'\n visible_expr: {self.visible_expr}'

        topic_str: str = ''
        if self.topic != '':
            topic_str = f'\n  Topic:{self.topic}'

        results: List[str] = []
        result: str = (f'\nParseGroup type: {self.control_type} id: {self.control_id} '
                       f'{default_control_str}{visible_expr}{topic_str}'
                       f'\n #children: {len(self.children)}')
        results.append(result)
        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        return '\n'.join(results)


ParseGroup.init_class()
