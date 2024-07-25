# coding=utf-8

from pathlib import Path
from typing import Callable, Dict, ForwardRef, Tuple, Type, Union

import xbmc
import xbmcvfs

from common.logger import *
from gui import BaseParser
from gui.base_model import BaseModel
from gui.base_tags import control_elements, Item
import xml.etree.ElementTree as ET
from typing import Callable

from gui.base_tags import ControlType, Tag
from gui.base_tags import ElementKeywords as EK
from gui.exceptions import ParseError
module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ElementTextAccess:
    """
       Utility to get the text field of an arbitrary element
    """
    _logger: BasicLogger = None

    def __init__(self, parent: BaseParser, tag_name: str,
                 default_value: str | None = None) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        self.parent = parent
        self.tag_name: str = tag_name
        self.default_value: str | None = default_value

    def get_value(self, el_element: ET.Element) -> str:
        clz = type(self)
        value_str: str = el_element.text
        if value_str is None:
            clz._logger.debug(f'{self.tag_name} value not specified')
            value_str = self.default_value

        return value_str

    def get_value_as_int(self, el_element: ET.Element,
                         default_int_value: int | None) -> int:
        clz = type(self)
        value_str: str | None = self.get_value(el_element)
        value_int: int | None = default_int_value
        if value_str is not None:
            try:
                value_int = int(value_str)
            except Exception as e:
                clz._logger.debug(f'Exception during conversion to int value: '
                                  f'{value_str} Setting to default: {default_int_value}')
                value_int = default_int_value
        return value_int

    def get_value_as_bool(self, el_element: ET.Element,
                          default_bool_value: bool | None) -> bool:
        clz = type(self)
        value_str: str | None = self.get_value(el_element)
        value_bool: bool | None = default_bool_value
        if value_str is not None:
            try:
                value_bool = bool(value_str)
            except Exception as e:
                clz._logger.debug(f'Exception during conversion to bool value: '
                                  f'{value_str} Setting to default: {default_bool_value}')
                value_bool = default_bool_value
        return value_bool


class ElementAttribAccess:
    """
       Utility to get an attribute of an arbitrary element
    """
    _logger: BasicLogger = None

    def __init__(self, parent: BaseParser, tag_name, attrib_name: str,
                 default_value: str | None = None) -> None:
        super().__init__(parent)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        self.parent = parent
        self.tag_name: str = tag_name
        self.attrib_name: str = attrib_name
        self.default_value: str | None = default_value

    def get_value(self, el_element: ET.Element) -> str:
        clz = type(self)
        try:
            if el_element.tag != self.tag_name:
                raise ParseError(f'Current element has incorrect tag: {self.tag_name}.')
        except Exception as e:
            raise ParseError(f'Exception occurred accessing tag: {self.tag_name}')

        try:
            value_str: str = el_element.attrib.get(self.attrib_name)
        except Exception as e:
            clz._logger.debug(f'Exception occurred accessing attribute: '
                              f'{self.attrib_name} of tag: {self.tag_name}. '
                              f'Returning default: {self.default_value}')
            return self.default_value

        if value_str is None:
            value_str = self.default_value

        return value_str

    def get_value_as_int(self, el_element: ET.Element,
                         default_int_value: int | None) -> int:
        clz = type(self)
        value_str: str | None = self.get_value(el_element)
        value_int: int | None = default_int_value
        if value_str is not None:
            try:
                value_int = int(value_str)
            except Exception as e:
                clz._logger.debug(f'Exception during conversion to int value: '
                                  f'{value_str} Setting to default: {default_int_value}')
                value_int = default_int_value
        return value_int

    def get_value_as_bool(self, el_element: ET.Element,
                          default_bool_value: bool | None) -> bool:
        clz = type(self)
        value_str: str | None = self.get_value(el_element)
        value_bool: bool | None = default_bool_value
        if value_str is not None:
            try:
                value_bool = bool(value_str)
            except Exception as e:
                clz._logger.debug(f'Exception during conversion to bool value: '
                                  f'{value_str} Setting to default: {default_bool_value}')
                value_bool = default_bool_value
        return value_bool


class BaseElementParser:
    _logger: BasicLogger = None

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)

    def __init__(self, parent: BaseParser) -> None:
        self.parent: BaseParser = parent

    @classmethod
    def get_instance(cls, parent: BaseParser,
                     el_child: ET.Element) -> ForwardRef('BaseElementParser'):
        self = BaseElementParser(parent)
        return self

    def parse_element(self) -> None:
        pass

    def __repr__(self) -> str:
        return f'de nada'


class ElementParser:
    _logger: BasicLogger = None

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)

    @classmethod
    def parse_info(cls, parent: BaseParser | None = None,
                   el_info: ET.Element = None) -> str | None:
        text_access: ElementTextAccess = ElementTextAccess(parent=parent,
                                                           tag_name=EK.INFO.value)

        info_expr: str = text_access.get_value(el_info)
        if parent is not None:
            parent.info_expr = info_expr
        return info_expr

    @classmethod
    def parse_info2(cls, parent: BaseParser | None = None,
                   el_info2: ET.Element = None) -> str | None:
        text_access: ElementTextAccess = ElementTextAccess(parent=parent,
                                                           tag_name=EK.INFO2.value)

        info2_expr: str = text_access.get_value(el_info2)
        if parent is not None:
            parent.info2_expr = info2_expr
        return info2_expr

    @classmethod
    def parse_action(cls, parent: BaseParser | None = None,
                     el_info: ET.Element = None) -> str | None:
        text_access: ElementTextAccess = ElementTextAccess(parent=parent,
                                                           tag_name=EK.ACTION.value,
                                                           default_value='')
        action_expr: str = text_access.get_value(el_info)
        if parent is not None:
            parent.action_expr = action_expr
        return action_expr

    @classmethod
    def parse_orientation(cls, parent: BaseParser | None = None,
                          el_orientation: ET.Element = None) -> str | None:
        text_access: ElementTextAccess = ElementTextAccess(parent=parent,
                                                           tag_name=[EK.ORIENTATION.value])
        orientation_expr: str = 'vertical'
        if el_orientation is not None:
            orientation_expr: str = el_orientation.text
            if orientation_expr is None:
                cls._logger.debug(f'orientation value not specified. Ignored')
        parent.orientation_expr = orientation_expr
        return orientation_expr

    @classmethod
    def parse_default_control(cls, parent: BaseParser | None = None,
                              el_default_control: ET.Element = None) -> Tuple[int, bool]:
        """
           defaultcontrol   specifies the default control of the window. This is the id of
                            the control that will receive focus when the window is first
                            opened. Note that most Kodi windows save the current focus
                            when you leave the window, and will return to the last focused
                            item when you return to a window. This behaviour can be stopped
                            by specifying the attribute always="true".

           <defaultcontrol always="false">2</defaultcontrol>
           :returns A Tuple[default_control_id: int, default_control_always: bool]
           """
        default_control_id: int = 0
        default_control_expr: str = ''
        default_control_expr = el_default_control.attrib.get('always')
        default_control_always: bool = False
        if default_control_expr is not None and default_control_expr.lower() == 'true':
            default_control_always = True
        default_control_str: str = '-1'
        if el_default_control is not None:
            default_control_str: str = el_default_control.text
            if default_control_str is None:
                cls._logger.debug(f'default_control value not specified. Ignored')
        parent.default_control_always = default_control_always
        try:
            default_control_id = int(default_control_str)
        except Exception as e:
            cls._logger.debug(f'Invalid number for default_control_id: '
                              f'{default_control_str}')
        parent.default_control_id = default_control_id
        return default_control_id, default_control_always

    @classmethod
    def parse_on_focus(cls, parent: BaseParser | None = None,
                       el_on_focus: ET.Element = None) -> str | None:
        on_focus_expr: str = ''
        on_focus_value: str = el_on_focus.text
        if on_focus_value is None:
            cls._logger.debug(f'onFocus value not specified')
        parent.on_focus_expr = on_focus_value
        return on_focus_value

    @classmethod
    def parse_enable(cls, parent: BaseParser | None = None,
                     el_enable: ET.Element = None) -> str | None:
        enable_value: str = el_enable.text
        if enable_value is None:
            cls._logger.debug(f'enable value not specified')
        parent.enable_value_expr = enable_value
        return enable_value

    @classmethod
    def parse_on_unfocus(cls, parent: BaseParser | None = None,
                         el_on_unfocus: ET.Element = None) -> str | None:
        on_unfocus_expr: str = ''
        on_unfocus_expr: str = el_on_unfocus.text
        if on_unfocus_expr is None:
            cls._logger.debug(f'onUnFocus value not specified')
        parent.on_unfocus_expr = on_unfocus_expr
        return on_unfocus_expr

    @classmethod
    def parse_visible(cls, parent: BaseParser | None = None,
                      el_visible: ET.Element = None) -> str | None:
        visible_expr: str = el_visible.text
        if visible_expr is None:
            cls._logger.debug(f'{el_visible} value not specified')
        parent.visible_expr = visible_expr
        return visible_expr

    @classmethod
    def parse_menu_control(cls, parent: BaseParser | None = None,
                           el_menu_control: ET.Element = None) -> int:
        menu_control_str: str = el_menu_control.text
        if menu_control_str is None:
            cls._logger.debug(f'menu_control value not specified')
        menu_control: int = -1
        if len(menu_control_str) > 0:
            try:
                menu_control = int(menu_control_str)
            except Exception:
                menu_control = -1

        parent.menu_control = menu_control
        return menu_control

    @classmethod
    def parse_label(cls, parent: BaseParser | None = None,
                    el_label: ET.Element = None) -> str | None:
        label_expr: str = el_label.text
        if label_expr is None:
            label_expr = ''
        parent.label_expr = label_expr
        return label_expr

    @classmethod
    def parse_alt_label(cls, parent: BaseParser | None = None,
                        el_label: ET.Element = None) -> str | None:
        alt_label_expr: str = el_label.text
        if alt_label_expr is None:
            alt_label_expr = ''
        parent.alt_label_expr = alt_label_expr
        return alt_label_expr

    @classmethod
    def parse_hint_text(cls, parent: BaseParser | None = None,
                        el_hint_text: ET.Element = None) -> str | None:
        hint_text_expr: str = el_hint_text.text
        if hint_text_expr is None:
            cls._logger.debug(f'{el_hint_text} value not specified')
            hint_text_expr = ''
        parent.hint_text_expr = hint_text_expr
        return hint_text_expr

    @classmethod
    def parse_description(cls, parent: BaseParser | None = None,
                          el_description: ET.Element = None) -> str | None:
        description: str = el_description.text
        if description is None:
            cls._logger.debug(f'{el_description} value not specified')
            description = ''
        parent.description = description
        return description

    @classmethod
    def parse_number(cls, parent: BaseParser | None = None,
                     el_number: ET.Element = None) -> str | None:
        number_expr: str = el_number.text
        if number_expr is None:
            cls._logger.debug(f'{el_number} value not specified')
        parent.number_expr = number_expr
        return number_expr

    @classmethod
    def parse_has_path(cls, parent: BaseParser | None = None,
                       el_has_path: ET.Element = None) -> str | bool:
        has_path_expr: str = el_has_path.text
        if has_path_expr is None:
            cls._logger.debug(f'{has_path_expr} value not specified')
        parent.has_path_expr = has_path_expr.lower() == 'true'
        return parent.has_path_expr

    @classmethod
    def parse_selected(cls, parent: BaseParser | None = None,
                       el_selected: ET.Element = None) -> str | bool:
        selected_expr: str = el_selected.text
        if selected_expr is None:
            cls._logger.debug(f'{selected_expr} value not specified')
        parent.selected_expr = selected_expr
        return selected_expr

    @classmethod
    def parse_page_control_id(cls, parent: BaseParser | None = None,
                            el_page_control_id: ET.Element = None) -> int | None:
        page_control_id_str: str = el_page_control_id.text
        page_control_id: int | None
        if page_control_id_str is None:
            cls._logger.debug(f'{page_control_id_str} value not specified')
            page_control_id = None
        else:
            page_control_id = int(page_control_id_str)
        parent.page_control_id = page_control_id
        return page_control_id

    @classmethod
    def parse_scroll(cls, parent: BaseParser | None = None,
                     el_scroll: ET.Element = None) -> int | None:
        scroll_str: str = el_scroll.text
        scroll: bool = False
        if scroll_str is not None:
            scroll = scroll_str.lower() == 'true'

        parent.scroll = scroll
        return scroll

    @classmethod
    def parse_scroll_time(cls, parent: BaseParser | None = None,
                          el_scroll_time: ET.Element = None) -> int | None:
        scroll_time_str: str = el_scroll_time.text
        scroll_time: int
        if scroll_time_str is None:
            cls._logger.debug(f'scrolltime value not specified')
            scroll_time = 200
        else:
            scroll_time = int(scroll_time_str)

        parent.scroll_time = scroll_time
        return scroll_time

    @classmethod
    def parse_show_one_page(cls, parent: BaseParser | None = None,
                            el_show_one_page: ET.Element = None) -> int | None:
        show_one_page_expr: str = el_show_one_page.text
        if show_one_page_expr is None:
            cls._logger.debug(f'{show_one_page_expr} value not specified')
        parent.show_one_page = show_one_page_expr.lower() == 'true'
        return parent.show_one_page

    @classmethod
    def parse_wrap_multiline(cls, parent: BaseParser | None = None,
                            el_show_one_page: ET.Element = None) -> int | None:
        wrap_multiline_expr: str = el_show_one_page.text
        if wrap_multiline_expr is None:
            cls._logger.debug(f'{wrap_multiline_expr} value not specified')
        parent.wrap_multiline = wrap_multiline_expr.lower() == 'true'
        return parent.wrap_multiline

    @classmethod
    def parse_true_msg_id(cls, parent: BaseParser | None = None,
                            el_true_msg_id: ET.Element = None) -> int | None:
        true_msg_id: str = el_true_msg_id.text
        if true_msg_id is None:
            cls._logger.debug(f'{true_msg_id} value not specified')
        try:
            parent.true_msg_id = int(true_msg_id)
        except ValueError:
            cls._logger.info(f'Non-numeric value specified for "true_msg_id":'
                             f' {true_msg_id}')
            parent.true_msg_id = None  # Default value

        return parent.true_msg_id

    @classmethod
    def parse_false_msg_id(cls, parent: BaseParser | None = None,
                          el_flase_msg_id: ET.Element = None) -> int | None:
        false_msg_id: str = el_flase_msg_id.text
        if false_msg_id is None:
            cls._logger.debug(f'{false_msg_id} value not specified')
        try:
            parent.false_msg_id = int(false_msg_id)
        except ValueError:
            cls._logger.info(f'Non-numeric value specified for "false_msg_id":'
                             f' {false_msg_id}')
            parent.false_msg_id = None  # Default value
        return parent.false_msg_id

    @classmethod
    def parse_topic(cls, parent: BaseParser | None = None,
                    el_topic: ET.Element = None) -> int | None:
        """
              <topic name="speech_engine" label="102"
                                           hinttext="Select to choose speech engine"
                            topicleft="category_keymap" topicright="" topicup="engine_settings"
                                    topicdown="" rank="3">header</topic>
        :param parent:
        :return:
        """
        pass

    @classmethod
    def no_op(cls, parent: Union[ForwardRef('BaseParser'), None] = None,
              el_page_control_id: ET.Element = None) -> int | None:
        return None

class ControlElementHandler:
    _logger: BasicLogger = None
    element_handlers: Dict[str, ForwardRef('BaseElementParser')] = {}

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)

    @classmethod
    def add_handler(cls, item: Item,
                    element_parser: ForwardRef('BaseElementParser')) -> None:
        cls.element_handlers[item.key] = element_parser

    @classmethod
    def get_handler(cls, item: Item) -> ForwardRef('BaseElementParser'):
        if item.ignore:
            return ElementParser.noop  # Acts as a Null parser

        element_handler: ForwardRef('BaseElementParser') = None
        #  cls._logger.debug(f'Item key: {item.key}')
        try:
            element_handler = cls.element_handlers[item.key]
        except Exception:
            cls._logger.debug(f'Handler not found for element: {item.key}')
            raise ParseError(f'Handler not found for element: {item.key}')
        return element_handler


    @classmethod
    def add_model_handler(cls, item: Item,
                    model: ForwardRef('BaseModel')) -> None:
        cls.model_handlers[item.key] = model

    @classmethod
    def get_model_handler(cls, item: Item) -> ForwardRef('BaseElementParser'):
        if item.ignore:
            return ElementParser.no_op  # Acts as a Null parser

        model: ForwardRef('BaseElementParser') = None
        #  cls._logger.debug(f'Item key: {item.key}')
        try:
            model = cls.model_handlers[item.key]
        except Exception:
            cls._logger.debug(f'Model not found for element: {item.key}')
            raise ParseError(f'Model not found for element: {item.key}')
        return model


class ElementHandler:
    _logger: BasicLogger = None
    # parse_info(cls, parent: BaseParser | None = None,
    # el_info: ET.Element = None) -> str | None:
    #  Callable[[BaseModel, BaseParser], BaseModel]:
    element_handlers: Dict[str, Callable[[BaseParser, ET.Element], str]] = {}
    model_handlers: Dict[str, BaseModel] = {}

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)
        cls.add_handler(EK.INFO.value, ElementParser.parse_info)
        cls.add_handler(EK.INFO2.value, ElementParser.parse_info2)
        cls.add_handler(EK.ACTION.value, ElementParser.parse_action)
        cls.add_handler(EK.ORIENTATION.value, ElementParser.parse_orientation)
        cls.add_handler(EK.DEFAULT_CONTROL.value, ElementParser.parse_default_control)
        cls.add_handler(EK.ON_FOCUS.value, ElementParser.parse_on_focus)
        cls.add_handler(EK.ENABLE.value, ElementParser.parse_enable)
        cls.add_handler(EK.ON_UNFOCUS.value, ElementParser.parse_on_unfocus)
        cls.add_handler(EK.VISIBLE.value, ElementParser.parse_visible)
        cls.add_handler(EK.LABEL.value, ElementParser.parse_label)
        cls.add_handler(EK.ALT_LABEL.value, ElementParser.parse_alt_label)
        cls.add_handler(EK.MENU_CONTROL.value, ElementParser.parse_menu_control)
        cls.add_handler(EK.HINT_TEXT.value, ElementParser.parse_hint_text)
        cls.add_handler(EK.DESCRIPTION.value, ElementParser.parse_description)
        cls.add_handler(EK.NUMBER.value, ElementParser.parse_number)
        cls.add_handler(EK.HAS_PATH.value, ElementParser.parse_has_path)
        cls.add_handler(EK.SELECTED.value, ElementParser.parse_selected)
        cls.add_handler(EK.PAGE_CONTROL.value, ElementParser.parse_page_control_id)
        cls.add_handler(EK.SCROLL_TIME.value, ElementParser.parse_scroll_time)
        cls.add_handler(EK.SCROLL.value, ElementParser.parse_scroll)
        cls.add_handler(EK.SHOW_ONE_PAGE.value, ElementParser.parse_show_one_page)
        cls.add_handler(EK.WRAP_MULTILINE.value, ElementParser.parse_wrap_multiline)

    @classmethod
    def add_handler(cls, item_key: str,
                    element_parser: Callable[[BaseParser, ET.Element],
                    str | int | BaseParser | Tuple[str, bool]]) -> None:
        cls.element_handlers[item_key] = element_parser

    @classmethod
    def get_handler(cls, key: str) -> Callable[[BaseParser, ET.Element], str | BaseParser]:
        item: Item = None
        try:
            item: Item = control_elements[key]
        except KeyError:
            item = None

        cls._logger.debug(f'item: {item}')
        if item is None or item.ignore:
            cls._logger.debug(f'about to call no-op')
            return ElementParser.no_op  # Acts as a Null parser

        # element_handler:  Callable[[BaseParser, ET.Element], str] = None
        #  cls._logger.debug(f'Item key: {item.key}')
        try:
            element_handler = cls.element_handlers[item.key]
            #  cls._logger.debug(f'element_handler: {element_handler}')
        except Exception:
            cls._logger.debug(f'Handler not found for element: {item.key}')
            raise ParseError(f'Handler not found for element: {item.key}')
        return element_handler


    @classmethod
    def add_model_handler(cls, item: Item,
                          model: Type[BaseModel]) -> None:
        #  cls._logger.debug(f'item: {item.key} model: {model}')
        cls.model_handlers[item.key] = model

    @classmethod
    def get_model_handler(cls, item: Item) -> \
            Callable[[BaseModel, BaseModel, BaseParser],
                     ForwardRef('TopicModel') | BaseModel]:
        supress_keys = (ControlType.IMAGE.name,)
        # cls._logger.debug(f'key: {item.key} contained: {item.key in supress_keys}')
        if item.ignore:
            if item.key not in supress_keys:
                # cls._logger.debug(f'Skipping ignored item: {item.key}')
                pass

        model: BaseModel = None
        try:
            model = cls.model_handlers[item.key]
        except Exception:
            cls._logger.debug(f'Model not found for element: {item.key}')
            raise ParseError(f'Model not found for element: {item.key}')
        return model


ElementHandler.init_class()
ElementParser.init_class()
