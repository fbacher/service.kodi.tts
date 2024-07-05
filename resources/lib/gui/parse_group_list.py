# coding=utf-8

from typing import Callable, List, Tuple
import xml.etree.ElementTree as ET
from gui.base_tags import ElementKeywords as EK

from common.logger import BasicLogger, DEBUG_VERBOSE
from gui import ControlType
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, Item
from gui.element_parser import BaseElementParser, ElementHandler
from gui.parse_control import ParseControl
from gui.base_tags import BaseAttributeType as BAT
from gui.parse_topic import ParseTopic

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ParseGroupList(ParseControl):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.GROUP_LIST.name]

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)
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

        self.topic: ParseTopic | None = None
        self.default_control_always: bool = False
        self.default_control_id: int = -1
        self.description: str = ''
        # self.group
        self.alt_label_expr: str = ''
        self.alt_type_expr: str = ''
        self.hint_text_expr: str = ''
        self.info_expr: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        self.on_info_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.orientation_expr: str = 'vertical'
        self.page_control_id: int = -1
        self.scroll_time: int = 200
        self.visible_expr: str = ''

    @classmethod
    def get_instance(cls, parent: ParseControl,
                     el_group_list: ET.Element) -> BaseParser:
        self = ParseGroupList(parent)
        self.parse_group_list(el_group_list)
        return self

    def parse_group_list(self, el_group_list: ET.Element) -> None:
        """
        Parse the 'button' control

        :param el_group_list:
        :return:

         <control type="grouplist" id="3"  alt_type="heading"
                     alt_label="Settings Categories">
                <description>Categories Area</description>
                <left>45</left>
                <top>70</top>
                <width>759</width>
                <height>40</height>
                <itemgap>5</itemgap>
                <defaultcontrol>100</defaultcontrol>
                <align>center</align>
                <orientation>horizontal</orientation>
                <alt_label>Categories</alt_label>
                <!-- <onleft>300</onleft>
                <onright>102</onright> -->
                <onup>9001</onup>
                <ondown>100</ondown>
        """
        clz = type(self)
        self.control_type = ControlType.GROUP_LIST
        control_id_str: str = el_group_list.attrib.get('id')
        if control_id_str is not None:
            control_id: int = int(control_id_str)
            self.control_id = control_id

        alt_label_str: str = el_group_list.attrib.get(BAT.ALT_LABEL)
        if alt_label_str is not None:
            self.alt_label_expr = alt_label_str

        alt_type_str: str = el_group_list.attrib.get(BAT.ALT_TYPE)
        if alt_type_str is not None:
            self.alt_type_expr = alt_type_str

        DEFAULT_TAGS: Tuple[str, ...] = (EK.DESCRIPTION, EK.VISIBLE)
        DEFAULT_FOCUS_TAGS: Tuple[str, ...] = (EK.ENABLE, EK.ON_FOCUS, EK.ON_UNFOCUS,
                                               EK.ON_INFO)
        GROUP_LIST_CONTROL_TAGS: Tuple[str, ...] = (EK.HINT_TEXT,
                                                    EK.PAGE_CONTROL,
                                                    EK.ORIENTATION,
                                                    EK.SCROLL_TIME,
                                                    EK.ALT_LABEL,
                                                    EK.DEFAULT_CONTROL,
                                                    EK.CONTROL)
        tags_to_parse: Tuple[str, ...] = ((EK.TOPIC,) + DEFAULT_FOCUS_TAGS +
                                          DEFAULT_TAGS + GROUP_LIST_CONTROL_TAGS)

        children: [ET.Element] = el_group_list.findall(f'./*')
        child: ET.Element
        for child in children:
            #  clz._logger.debug(f'element.tag: {element.tag} text: {element.text}')
            if child.tag in tags_to_parse:
                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose(f'element_tag: {child.tag}')
                key: str = child.tag
                control_type: ControlType = clz.get_control_type(child)
                if control_type is not None:
                    key = control_type.name
                item: Item = control_elements[key]
                # Values copied to self
                handler: Callable[[BaseParser, ET.Element], str | BaseParser]
                handler = ElementHandler.get_handler(item.key)
                parsed_instance: BaseParser = handler(self, child)
                if parsed_instance is not None:
                    if key == EK.TOPIC:
                        self.topic = parsed_instance
                    elif control_type is not None:
                        self.children.append(parsed_instance)

            # else:
            #     if child.tag not in ('top', 'left', 'width', 'height', 'bottom'):
            #         clz._logger.debug(f'ParseGroupList ignored element: {child.tag}')

    def __repr__(self) -> str:
        clz = type(self)
        # Remove:  has_path, label, scroll, action
        # Verify removal: onfocus, onup, enable etc.

        alt_label_str = ''
        if self.alt_label_expr != '':
            alt_label_str = f'\n alt_label: {self.alt_label_expr}'

        alt_type_str = ''
        if self.alt_type_expr != '':
            alt_type_str = f'\n alt_type: {self.alt_type_expr}'

        if self.on_focus_expr is not None and (len(self.on_focus_expr) > 0):
            on_focus_expr: str = f'\n on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr is not None and (len(self.on_unfocus_expr) > 0):
            on_unfocus_expr: str = f'\n on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''

        default_control_id: str = ''
        if self.default_control_id >= 0:
            default_control_id = f'\n default_control: {self.default_control_id}'
        default_control_always: str = ''
        if not self.default_control_always:
            default_control_always = f'\n default_control_always: {self.default_control_always}'
        description_str: str = ''
        if self.description != '':
            description_str = f'\n description: {self.description}'

        scroll_time_str: str = f'\n scroll_time; {self.scroll_time}ms'

        visible_expr_str: str = ''
        if self.visible_expr != '':
            visible_expr_str = f'\n visible: {self.visible_expr}'

        # self.enable_expr: str = parsed_group_list.enable_expr

        hint_text_expr_str: str = ''
        if self.hint_text_expr != '':
            hint_text_expr_str = '\n hint_text: {self.hint_text_expr}'

        on_info_expr_str: str = ''
        if self.on_info_expr != '':
            on_info_expr_str = f'\n on_info_expr: {self.on_info_expr}'

        page_control_id_str: str = ''
        if self.page_control_id >= 0:
            page_control_id_str = f'\n page_control_id: {self.page_control_id}'

        orientation_expr: str = '\n orientation: vertical'
        if self.orientation_expr is not None and len(self.orientation_expr) > 0:
            orientaton_expr = f'\n orientation: {self.orientation_expr}'

        info_expr: str = ''
        if len(self.info_expr) > 0:
            info_expr = f'\n info_expr: {self.info_expr}'
        selected_expr: str = ''

        results: List[str] = []
        result: str = (f'\nGroupListModel type: {self.control_type} '
                       f'id: {self.control_id}{alt_label_str}{alt_type_str}'
                       f'{default_control_id}{default_control_always}'
                       f'{page_control_id_str}'
                       f'{description_str}'
                       f'{hint_text_expr_str}'
                       f'{visible_expr_str}'
                       f'{selected_expr}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'{info_expr}{orientation_expr}'
                       f'{on_info_expr_str}'
                       f'{scroll_time_str}'
                       f'\n #children: {len(self.children)}'
                       )
        results.append(result)

        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        return '\n'.join(results)


ParseGroupList.init_class()
