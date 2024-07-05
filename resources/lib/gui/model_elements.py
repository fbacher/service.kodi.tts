# coding=utf-8

from pathlib import Path
from typing import Callable, Dict, ForwardRef, Tuple, Type, Union

import xbmc
import xbmcvfs

from common.logger import *
from common.monitor import Monitor
from gui import BaseParser
from gui.base_model import BaseModel
from gui.base_parser import BaseControlParser
from gui.base_tags import control_elements, ControlType, Item
from gui.exceptions import ParseError
import xml.etree.ElementTree as ET
from enum import auto, Enum
from typing import Callable

from common.logger import BasicLogger
from gui.base_tags import ControlType, Tag
from gui.base_tags import BaseAttributeType as BAT
from gui.base_tags import ElementKeywords as EK
from gui.exceptions import ParseError
module_logger = BasicLogger.get_module_logger(module_path=__file__)


class BaseModelElement:
    _logger: BasicLogger = None
    item: Item = None

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)

    def __init__(self, parent: BaseParser) -> None:
        self.parent: BaseParser = parent

    @classmethod
    def get_instance(cls, parent: BaseParser,
                     el_child: ET.Element) -> ForwardRef('BaseModelElement'):
        self = BaseModelElement(parent)
        return self

    def parse_element(self) -> None:
        pass

    def __repr__(self) -> str:
        return f'de nada'


class ModelElement:
    _logger: BasicLogger = None

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)

    @classmethod
    def parse_default_control(cls, parent: BaseParser | None = None,
                              el_default_control: ET.Element = None) -> Tuple[str, bool]:
        """
           defaultcontrol   specifies the default control of the window. This is the id of
                            the control that will receive focus when the window is first
                            opened. Note that most Kodi windows save the current focus
                            when you leave the window, and will return to the last focused
                            item when you return to a window. This behaviour can be stopped
                            by specifying the attribute always="true".

           <defaultcontrol always="false">2</defaultcontrol>
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
            parent.default_control_id = int(default_control_str)
        except Exception as e:
            cls._logger.debug(f'Invalid number for default_control_id: '
                              f'{default_control_str}')
        return default_control_expr, default_control_always

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
    def parse_label(cls, parent: BaseParser | None = None,
                    el_label: ET.Element = None) -> str | None:
        label_expr: str = el_label.text
        if label_expr is None:
            cls._logger.debug(f'{el_label} value not specified')
        parent.label_expr = label_expr
        return label_expr

    @classmethod
    def parse_hint_text(cls, parent: BaseParser | None = None,
                        el_hint_text: ET.Element = None) -> str | None:
        hint_text_expr: str = el_hint_text.text
        if hint_text_expr is None:
            cls._logger.debug(f'{el_hint_text} value not specified')
        parent.hint_text_expr = hint_text_expr
        return hint_text_expr

    @classmethod
    def parse_description(cls, parent: BaseParser | None = None,
                          el_description: ET.Element = None) -> str | None:
        description: str = el_description.text
        if description is None:
            cls._logger.debug(f'{el_description} value not specified')
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
    def no_op(cls, parent: Union[ForwardRef('BaseParser'), None] = None,
              el_page_control_id: ET.Element = None) -> int | None:
        return None

class ModelElementHandler:
    _logger: BasicLogger = None
    element_handlers: Dict[str, ForwardRef('BaseModelElement')] = {}

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)

    @classmethod
    def add_handler(cls, item: Item,
                    element_parser: ForwardRef('BaseModelElement')) -> None:
        cls.element_handlers[item.key] = element_parser

    @classmethod
    def get_handler(cls, item: Item) -> ForwardRef('BaseModelElement'):
        if item.ignore:
            return ModelElement.noop  # Acts as a Null parser

        element_handler: ForwardRef('BaseModelElement') = None
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
    def get_model_handler(cls, item: Item) -> ForwardRef('BaseModelElement'):
        if item.ignore:
            return ModelElement.no_op  # Acts as a Null parser

        model: ForwardRef('BaseModelElement') = None
        #  cls._logger.debug(f'Item key: {item.key}')
        try:
            model = cls.model_handlers[item.key]
        except Exception:
            cls._logger.debug(f'Model not found for element: {item.key}')
            raise ParseError(f'Model not found for element: {item.key}')
        return model


class ModelHandler:
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
        cls.add_handler(EK.INFO.value, ModelElement.parse_info)
        cls.add_handler(EK.ACTION.value, ModelElement.parse_action)
        cls.add_handler(EK.ORIENTATION.value, ModelElement.parse_orientation)
        cls.add_handler(EK.DEFAULT_CONTROL.value, ModelElement.parse_default_control)
        cls.add_handler(EK.ON_FOCUS.value, ModelElement.parse_on_focus)
        cls.add_handler(EK.ON_UNFOCUS.value, ModelElement.parse_on_unfocus)
        cls.add_handler(EK.VISIBLE.value, ModelElement.parse_visible)
        cls.add_handler(EK.LABEL.value, ModelElement.parse_label)
        cls.add_handler(EK.HINT_TEXT.value, ModelElement.parse_hint_text)
        cls.add_handler(EK.DESCRIPTION.value, ModelElement.parse_description)
        cls.add_handler(EK.NUMBER.value, ModelElement.parse_number)
        cls.add_handler(EK.HAS_PATH.value, ModelElement.parse_has_path)
        cls.add_handler(EK.SELECTED.value, ModelElement.parse_selected)
        cls.add_handler(EK.PAGE_CONTROL.value, ModelElement.parse_page_control_id)
        cls.add_handler(EK.SCROLL_TIME.value, ModelElement.parse_scroll_time)
        cls.add_handler(EK.SHOW_ONE_PAGE.value, ModelElement.parse_show_one_page)
        cls.add_handler(EK.WRAP_MULTILINE.value, ModelElement.parse_wrap_multiline)

    @classmethod
    def add_handler(cls, item_key: str,
                    element_parser: Callable[[BaseParser, ET.Element],
                    str | BaseParser | Tuple[str, bool]]) -> None:
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
            return ModelElement.no_op  # Acts as a Null parser

        # element_handler:  Callable[[BaseParser, ET.Element], str] = None
        #  cls._logger.debug(f'Item key: {item.key}')
        try:
            element_handler = cls.element_handlers[item.key]
            cls._logger.debug(f'element_handler: {element_handler}')
        except Exception:
            cls._logger.debug(f'Handler not found for element: {item.key}')
            raise ParseError(f'Handler not found for element: {item.key}')
        return element_handler


    @classmethod
    def add_model_handler(cls, item: Item,
                          model: Type[BaseModel]) -> None:
        cls._logger.debug(f'item: {item.key} model: {model}')
        cls.model_handlers[item.key] = model

    @classmethod
    def get_model_handler(cls, item: Item) -> Callable[[BaseModel, BaseParser], BaseModel]:
        supress_keys = ('image')
        cls._logger.debug(f'key: {item.key} contained: {item.key in supress_keys}')
        if item.ignore:
            if item.key not in supress_keys:
                cls._logger.debug(f'Skipping ignored item: {item.key}')

        model: BaseModel = None
        try:
            model = cls.model_handlers[item.key]
        except Exception:
            cls._logger.debug(f'Model not found for element: {item.key}')
            raise ParseError(f'Model not found for element: {item.key}')
        return model


ModelHandler.init_class()
ModelElement.init_class()
