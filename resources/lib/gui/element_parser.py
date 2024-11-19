# coding=utf-8
from enum import StrEnum
from pathlib import Path
from typing import Callable, Dict, ForwardRef, Tuple, Type, Union


from common.logger import *
from gui import BaseParser
from gui.base_model import BaseModel
from gui.base_tags import (control_elements, Item, BoolMessageType, TopicElement,
                           TopicKeyword, TopicType,
                           UnitsType,
                           ValueFromType, ValueUnits)
import xml.etree.ElementTree as ET
from typing import Callable

from gui.base_tags import ControlElement, Tag
from gui.base_tags import ElementKeywords as EK
from gui.base_tags import TopicElement as TE
from gui.exceptions import ParseError
from windows.ui_constants import AltCtrlType
from windows.window_state_monitor import WinDialogState

MY_LOGGER = BasicLogger.get_logger(__name__)


class ElementTextAccess:
    """
       Utility to get the text field of an arbitrary element
    """

    def __init__(self, parent: BaseParser, tag_name: str,
                 default_value: str | None = None) -> None:
        clz = type(self)
        self.parent = parent
        self.tag_name: str = tag_name
        self.default_value: str | None = default_value

    def get_value(self, el_element: ET.Element) -> str:
        clz = type(self)
        value_str: str = el_element.text
        if value_str is None:
            MY_LOGGER.debug_xv(f'{el_element.tag} value not specified')
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
                MY_LOGGER.debug(f'Exception during conversion to int value: '
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
                MY_LOGGER.debug(f'Exception during conversion to bool value: '
                                  f'{value_str} Setting to default: {default_bool_value}')
                value_bool = default_bool_value
        return value_bool


class ElementAttribAccess:
    """
       Utility to get an attribute of an arbitrary element
    """
    def __init__(self, parent: BaseParser, tag_name, attrib_name: str,
                 default_value: str | None = None) -> None:
        super().__init__(parent)
        clz = type(self)

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
            MY_LOGGER.debug(f'Exception occurred accessing attribute: '
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
                MY_LOGGER.debug(f'Exception during conversion to int value: '
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
                MY_LOGGER.debug(f'Exception during conversion to bool value: '
                                  f'{value_str} Setting to default: {default_bool_value}')
                value_bool = default_bool_value
        return value_bool


class BaseElementParser:

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
        if action_expr is None:
            action_expr = ''
        if parent is not None:
            parent.action_expr = action_expr
        return action_expr

    @classmethod
    def parse_orientation(cls, parent: BaseParser | None = None,
                          el_orientation: ET.Element = None) -> str | None:
        text_access: ElementTextAccess
        text_access = ElementTextAccess(parent=parent,
                                        tag_name=EK.ORIENTATION.value)
        orientation_expr: str = 'vertical'
        if el_orientation is not None:
            orientation_expr: str = el_orientation.text
            if orientation_expr is None:
                MY_LOGGER.debug_xv(f'orientation value not specified. Ignored')
                orientation_expr = 'vertical'
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
                MY_LOGGER.debug_xv(f'default_control value not specified. Ignored')
        parent.default_control_always = default_control_always
        try:
            default_control_id = int(default_control_str)
        except Exception as e:
            MY_LOGGER.debug_v(f'Invalid number for default_control_id: '
                              f'{default_control_str}')
        parent.default_control_id = default_control_id
        return default_control_id, default_control_always

    @classmethod
    def parse_on_focus(cls, parent: BaseParser | None = None,
                       el_on_focus: ET.Element = None) -> str | None:
        on_focus_expr: str = ''
        on_focus_value: str = el_on_focus.text
        if on_focus_value is None:
            MY_LOGGER.debug_xv(f'onFocus value not specified')
            on_focus_value = ''
        parent.on_focus_expr = on_focus_value
        return on_focus_value

    @classmethod
    def parse_enable(cls, parent: BaseParser | None = None,
                     el_enable: ET.Element = None) -> str | None:
        enable_value: str = el_enable.text
        if enable_value is None:
            MY_LOGGER.debug_xv(f'enable value not specified')
            enable_value = ''
        parent.enable_value_expr = enable_value
        return enable_value

    @classmethod
    def parse_on_unfocus(cls, parent: BaseParser | None = None,
                         el_on_unfocus: ET.Element = None) -> str | None:
        on_unfocus_expr: str = ''
        on_unfocus_expr: str = el_on_unfocus.text
        if on_unfocus_expr is None:
            MY_LOGGER.debug_xv(f'onUnFocus value not specified')
            on_unfocus_expr = ''
        parent.on_unfocus_expr = on_unfocus_expr
        return on_unfocus_expr

    @classmethod
    def parse_visible(cls, parent: BaseParser | None = None,
                      el_visible: ET.Element = None) -> str | None:
        visible_expr: str = el_visible.text
        if visible_expr is None:
            MY_LOGGER.debug_xv(f'{el_visible.tag} value not specified')
            visible_expr = ''
        parent.visible_expr = visible_expr
        return visible_expr

    @classmethod
    def parse_menu_control(cls, parent: BaseParser | None = None,
                           el_menu_control: ET.Element = None) -> int:
        menu_control_str: str = el_menu_control.text
        if menu_control_str is None:
            MY_LOGGER.debug_xv(f'menu_control value not specified')
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
    def parse_labeled_by(cls, parent: BaseParser | None = None,
                         el_labeled_by: ET.Element = None) -> str | None:
        labeled_by_expr: str = el_labeled_by.text
        if labeled_by_expr is None:
            labeled_by_expr = ''
        parent.labeled_by_expr = labeled_by_expr
        return None

    @classmethod
    def parse_label_for(cls, parent: BaseParser | None = None,
                    el_label_for: ET.Element = None) -> str | None:
        label_for_expr: str = el_label_for.text
        if label_for_expr is None:
            label_for_expr = ''
        parent.label_for_expr = label_for_expr
        return None

    @classmethod
    def parse_alt_info(cls, parent: BaseParser | None = None,
                       el_alt_info: ET.Element = None) -> str | None:
        alt_info_expr: str = el_alt_info.text
        if alt_info_expr is None:
            alt_info_expr = ''
        parent.alt_info_expr = alt_info_expr
        return None

    @classmethod
    def parse_alt_label(cls, parent: BaseParser | None = None,
                        el_alt_label: ET.Element = None) -> None:
        alt_label_expr: str = el_alt_label.text
        if alt_label_expr is None:
            alt_label_expr = ''
        parent.alt_label_expr = alt_label_expr
        return None

    @classmethod
    def parse_alt_type(cls, parent: BaseParser | None = None,
                       el_alt_type: ET.Element = None) -> None:
        """
        Parses an alt-type.
        An alt-type is an optional element which allows an alternative translated
        label to be associated with a control's type. A number of alternative
        labels are predefined in window.ui_constants.AltCtrlType. In addition,
        a msg_id can be used.

        If alt-type is not specified, then the default AltCtrlType for the
        control will be used.

        :param parent: parser that is parsing a particular element (typically
                       a Kodi control)
        :param el_alt_type: If a string, then should match an AltCtrlType.name
                            value. If an integer, then is interpreted as a
                            Kodi message id. Anything else is an error.
        :return:
        """
        clz = ElementParser
        alt_type: str | None = None
        if el_alt_type is not None:
            alt_type = el_alt_type.text
        MY_LOGGER.debug(f'alt_type: {alt_type} parent: {parent.control_id}')
        parent.alt_type_expr = alt_type

    @classmethod
    def parse_heading_label(cls, parent: BaseParser | None = None,
                            el_heading_label: ET.Element = None) -> str | None:
        heading_label: str = el_heading_label.text
        if heading_label is None:
            MY_LOGGER.debug_xv(f'{el_heading_label.tag} value not specified')
            heading_label = ''
        parent.heading_label = heading_label
        return None

    @classmethod
    def parse_heading_labeled_by(cls, parent: BaseParser | None = None,
                                 el_heading_labeled_by: ET.Element = None) -> str | None:
        heading_labeled_by: str = el_heading_labeled_by.text
        if heading_labeled_by is None:
            MY_LOGGER.debug_xv(f'{el_heading_labeled_by.tag} value not specified')
            heading_labeled_by = ''
        parent.heading_labeled_by = heading_labeled_by
        return None

    @classmethod
    def parse_heading_next(cls, parent: BaseParser | None = None,
                           el_heading_next: ET.Element = None) -> str | None:
        heading_next: str = el_heading_next.text
        if heading_next is None:
            MY_LOGGER.debug_xv(f'{el_heading_next.tag} value not specified')
            heading_next = ''
        parent.heading_next = heading_next
        return None

    @classmethod
    def parse_hint_text(cls, parent: BaseParser | None = None,
                        el_hint_text: ET.Element = None) -> str | None:
        hint_text_expr: str = el_hint_text.text
        if hint_text_expr is None:
            MY_LOGGER.debug_xv(f'{el_hint_text.tag} value not specified')
            hint_text_expr = ''
        parent.hint_text_expr = hint_text_expr
        return None

    @classmethod
    def parse_flows_to(cls, parent: BaseParser | None = None,
                       el_flows_to: ET.Element = None) -> str | None:
        flows_to: str = el_flows_to.text
        if flows_to is None:
            MY_LOGGER.debug_xv(f'{el_flows_to.tag} value not specified')
            flows_to = ''
        parent.flows_to = flows_to
        return None

    @classmethod
    def parse_flows_from(cls, parent: BaseParser | None = None,
                         el_flows_from: ET.Element = None) -> str | None:
        flows_from: str = el_flows_from.text
        if flows_from is None:
            MY_LOGGER.debug_xv(f'{el_flows_from.tag} value not specified')
            flows_from = ''
        parent.flows_from = flows_from
        return None


    @classmethod
    def parse_true_msg_id(cls, parent: BaseParser | None = None,
                          el_true_msg_id: ET.Element = None) -> int | None:
        true_msg_id: str = el_true_msg_id.text
        if true_msg_id is None:
            MY_LOGGER.debug_xv(f'{el_true_msg_id.tag} value not specified')
        try:
            if true_msg_id.isdigit():
                parent.true_msg_id = int(true_msg_id)
                MY_LOGGER.debug(f'true_id: {true_msg_id}')
            else:
                try:
                    true_id: BoolMessageType = BoolMessageType[true_msg_id.upper()]
                    MY_LOGGER.debug(f'true_id: {true_id}')
                    parent.true_msg_id = true_id.value
                except ValueError:
                    values: str = ''
                    bool_type: BoolMessageType
                    for bool_type in BoolMessageType:
                        values = f'{values} {bool_type.name}'
                    MY_LOGGER.info(f'Invalid value for "true_msg_id". Must be a '
                                     f'message id or one of: {values}')
        except ValueError:
            MY_LOGGER.info(f'Non-numeric value specified for "true_msg_id":'
                           f' {true_msg_id}')
            parent.true_msg_id = None  # Default value
        return None

    @classmethod
    def parse_false_msg_id(cls, parent: BaseParser | None = None,
                           el_false_msg_id: ET.Element = None) -> int | None:
        false_msg_id: str = el_false_msg_id.text
        if false_msg_id is None:
            MY_LOGGER.debug_xv(f'{el_false_msg_id.tag} value not specified')
        try:
            if false_msg_id.isdigit():
                parent.false_msg_id = int(false_msg_id)
                MY_LOGGER.debug(f'false_id: {false_msg_id}')
            else:
                try:
                    false_id: BoolMessageType = BoolMessageType[false_msg_id.upper()]
                    MY_LOGGER.debug(f'false_id: {false_id}')
                    parent.false_msg_id = false_id.value
                except ValueError:
                    values: str = ''
                    bool_type: BoolMessageType
                    for bool_type in BoolMessageType:
                        values = f'{values} {bool_type.name}'
                    MY_LOGGER.info(f'Invalid value for "false_msg_id". Must be a '
                                   f'message id or one of: {values}')
        except ValueError:
            MY_LOGGER.info(f'Non-numeric value specified for "false_msg_id":'
                           f' {false_msg_id}')
            parent.false_msg_id = None  # Default value
        return None

    @classmethod
    def parse_read_next(cls, parent: BaseParser | None = None,
                          el_read_next: ET.Element = None) -> str | None:
        read_next_expr: str = el_read_next.text
        if read_next_expr is None:
            MY_LOGGER.debug_xv(f'{el_read_next.tag} value not specified')
            read_next_expr = ''
        parent.read_next_expr = read_next_expr
        return None

    @classmethod
    def parse_inner_topic(cls, parent: BaseParser | None = None,
                          el_inner_topic: ET.Element = None) -> str | None:
        inner_topic: str = el_inner_topic.text
        if inner_topic is None:
            MY_LOGGER.debug_xv(f'{el_inner_topic.tag} value not specified')
            inner_topic = ''
        parent.inner_topic = inner_topic
        return None

    @classmethod
    def parse_outer_topic(cls, parent: BaseParser | None = None,
                          el_outer_topic: ET.Element = None) -> str | None:
        outer_topic: str = el_outer_topic.text
        if outer_topic is None:
            MY_LOGGER.debug_xv(f'{el_outer_topic.tag} value not specified')
            outer_topic = ''
        parent.outer_topic = outer_topic
        return None

    @classmethod
    def parse_topic_left(cls, parent: BaseParser | None = None,
                          el_topic_left: ET.Element = None) -> str | None:
        topic_left: str = el_topic_left.text
        if topic_left is None:
            MY_LOGGER.debug_xv(f'{el_topic_left.tag} value not specified')
            topic_left = ''
        parent.topic_left = topic_left
        return None

    @classmethod
    def parse_topic_right(cls, parent: BaseParser | None = None,
                         el_topic_right: ET.Element = None) -> str | None:
        topic_right: str = el_topic_right.text
        if topic_right is None:
            MY_LOGGER.debug_xv(f'{el_topic_right.tag} value not specified')
            topic_right = ''
        parent.topic_right = topic_right
        return None

    @classmethod
    def parse_topic_up(cls, parent: BaseParser | None = None,
                         el_topic_up: ET.Element = None) -> str | None:
        topic_up: str = el_topic_up.text
        if topic_up is None:
            MY_LOGGER.debug_xv(f'{el_topic_up.tag} value not specified')
            topic_up = ''
        parent.topic_up = topic_up
        return None

    @classmethod
    def parse_topic_down(cls, parent: BaseParser | None = None,
                         el_topic_down: ET.Element = None) -> str | None:
        topic_down: str = el_topic_down.text
        if topic_down is None:
            MY_LOGGER.debug_xv(f'{el_topic_down.tag} value not specified')
            topic_down = ''
        parent.topic_down = topic_down
        return None

    @classmethod
    def parse_topic_rank(cls, parent: BaseParser | None = None,
                         el_topic_rank: ET.Element = None) -> str | None:
        rank: str = el_topic_rank.text
        if rank is None:
            MY_LOGGER.debug_xv(f'{el_topic_rank.tag} value not specified')
            rank = ''
        parent.rank = rank
        return None

    @classmethod
    def parse_topic_type(cls, parent: BaseParser | None = None,
                         el_topic_type: ET.Element = None) -> str | None:
        clz = ElementParser
        topic_type_str: str = el_topic_type.text
        topic_type: TopicType = TopicType.DEFAULT
        if topic_type_str is None:
            MY_LOGGER.debug_xv(f'{el_topic_type.tag} value not specified')
            topic_type_str = ''
        if topic_type_str == '':
            topic_type_str = TopicType.DEFAULT.value()
        try:
            topic_type = TopicType(topic_type_str)
        except Exception:
            MY_LOGGER.info(f'Invalid topic_type specified: {topic_type_str} '
                             f'replacing with default')
            topic_type = TopicType.DEFAULT
        parent.topic_type = topic_type
        return None

    @classmethod
    def parse_topic_heading(cls, parent: BaseParser | None = None,
                            el_topic_heading: ET.Element = None) -> str | None:
        clz = ElementParser
        topic_heading: str = el_topic_heading.text
        if topic_heading is None:
            MY_LOGGER.debug_xv(f'{el_topic_heading.tag} value not specified')
            topic_heading = ''
        parent.topic_heading = topic_heading
        return None

    @classmethod
    def parse_topic_units(cls, parent: BaseParser | None = None,
                         el_topic_units: ET.Element = None) -> str | None:
        units_unit: str = el_topic_units.attrib.get(TopicKeyword.UNIT)
        if units_unit is None:
            MY_LOGGER.debug_xv(f'{el_topic_units.tag} value not specified')
            unit = ''
        units_type_str: str = el_topic_units.attrib.get(TopicKeyword.TYPE)
        units_type: UnitsType = UnitsType.FLOAT
        if units_type_str is None:
            MY_LOGGER.debug_xv(f'{el_topic_units.tag} value not specified. '
                                      f'Assuming float')
        elif units_type_str in (UnitsType.INT.value, UnitsType.FLOAT.value):
            units_type = UnitsType(units_type_str)
        else:
            MY_LOGGER.debug(f'{TopicKeyword.TYPE} is not {UnitsType.INT} nor'
                              f'{UnitsType.FLOAT.value}. Assuming '
                              f'{UnitsType.FLOAT.value}')

        units_digits: int = 1
        units_digits_str: str = el_topic_units.attrib.get(TopicKeyword.DECIMAL_DIGITS)
        if units_digits_str is None or not units_digits_str.isdigit():
            MY_LOGGER.debug_v(f'{TopicKeyword.DECIMAL_DIGITS}'
                                      f' value not specified or not an integer')
        else:
            units_digits = int(units_digits_str)

        value_units: ValueUnits
        value_units = ValueUnits(units_unit, units_type, units_digits)
        parent.units = value_units
        return None

    @classmethod
    def parse_topic_value_format(cls, parent: BaseParser | None = None,
                                 el_topic_value_format: ET.Element = None) -> str | None:
        value_format: str = el_topic_value_format.text
        if value_format is None:
            value_format = ''
        parent.value_format = value_format
        return None

    @classmethod
    def parse_topic_value_from(cls, parent: BaseParser | None = None,
                               el_topic_value_from: ET.Element = None) -> str | None:
        clz = ElementParser
        value_from_str: str = el_topic_value_from.text
        value_from: ValueFromType = ValueFromType.NONE
        if value_from_str is None:
            MY_LOGGER.debug_xv(f'{el_topic_value_from.tag} value not specified')
        try:
            value_from = ValueFromType(value_from_str)
        except ValueError:
            MY_LOGGER.exception('Invalid ValueFromType')

        parent.value_from = value_from
        return None

    @classmethod
    def parse_container_topic(cls, parent: BaseParser | None = None,
                               el_container_topic: ET.Element = None) -> None:
        clz = ElementParser
        container_topic: str = el_container_topic.text
        if container_topic is None:
            MY_LOGGER.debug_xv(f'{el_container_topic.tag} value not specified')

        parent.container_topic = container_topic
        return None

    @classmethod
    def parse_description(cls, parent: BaseParser | None = None,
                          el_description: ET.Element = None) -> str | None:
        description: str = el_description.text
        if description is None:
            MY_LOGGER.debug_xv(f'{el_description.tag} value not specified')
            description = ''
        parent.description = description
        return description

    @classmethod
    def parse_number(cls, parent: BaseParser | None = None,
                     el_number: ET.Element = None) -> str | None:
        """
        TODO:  Better define.
        :param parent:
        :param el_number:
        :return:
        """
        number_expr: str = el_number.text
        if number_expr is None:
            MY_LOGGER.debug_xv(f'{el_number.tag} value not specified')
            number_expr = ''
        parent.number_expr = number_expr
        return number_expr

    @classmethod
    def parse_has_path(cls, parent: BaseParser | None = None,
                       el_has_path: ET.Element = None) -> str | bool:
        has_path_expr: str = el_has_path.text
        if has_path_expr is None:
            MY_LOGGER.debug_xv(f'{el_has_path.tag} value not specified')
        parent.has_path_expr = has_path_expr.lower() == 'true'
        return parent.has_path_expr

    @classmethod
    def parse_selected(cls, parent: BaseParser | None = None,
                       el_selected: ET.Element = None) -> str | bool:
        selected_expr: str = el_selected.text
        if selected_expr is None:
            MY_LOGGER.debug_xv(f'{el_selected.tag} value not specified')
            selected_expr = ''
        parent.selected_expr = selected_expr
        return selected_expr

    @classmethod
    def parse_page_control_id(cls, parent: BaseParser | None = None,
                            el_page_control_id: ET.Element = None) -> int | None:
        page_control_id_str: str = el_page_control_id.text
        page_control_id: int | None
        if page_control_id_str is None:
            MY_LOGGER.debug_xv(f'{el_page_control_id.tag} value not specified')
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
            MY_LOGGER.debug_xv(f'scrolltime value not specified')
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
            MY_LOGGER.debug_xv(f'{show_one_page_expr} value not specified')
        parent.show_one_page = show_one_page_expr.lower() == 'true'
        return parent.show_one_page

    @classmethod
    def parse_wrap_multiline(cls, parent: BaseParser | None = None,
                            el_show_one_page: ET.Element = None) -> int | None:
        wrap_multiline_expr: str = el_show_one_page.text
        if wrap_multiline_expr is None:
            MY_LOGGER.debug_xv(f'{el_show_one_page.tag} value not specified')
        parent.wrap_multiline = wrap_multiline_expr.lower() == 'true'
        return parent.wrap_multiline

    @classmethod
    def parse_topic(cls, parent: BaseParser | None = None,
                    el_topic: ET.Element = None) -> int | None:
        """
              <topic name="speech_engine" label="102"
                                           hinttext="Select to choose speech engine"
                            topicleft="category_keymap" topicright="" topicup="engine_settings"
                                    topicdown="" rank="3">header</topic>
        :param el_topic:
        :param parent:
        :return:
        """
        pass

    @classmethod
    def no_op(cls, parent: Union[ForwardRef('BaseParser'), None] = None,
              el_page_control_id: ET.Element = None) -> int | None:
        return None

class ControlElementHandler:
    element_handlers: Dict[str, ForwardRef('BaseElementParser')] = {}

    @classmethod
    def add_handler(cls, item: Item,
                    element_parser: ForwardRef('BaseElementParser')) -> None:
        cls.element_handlers[item.key] = element_parser

    @classmethod
    def get_handler(cls, item: Item) -> ForwardRef('BaseElementParser'):
        if item.ignore:
            return ElementParser.noop  # Acts as a Null parser

        element_handler: ForwardRef('BaseElementParser') = None
        MY_LOGGER.debug_v(f'Item key: {item.key}')
        try:
            element_handler = cls.element_handlers[item.key]
        except Exception:
            MY_LOGGER.debug_v(f'Handler not found for element: {item.key}')
            raise ParseError(f'Handler not found for element: {item.key}')
        return element_handler


class ElementHandler:
    # parse_info(cls, parent: BaseParser | None = None,
    # el_info: ET.Element = None) -> str | None:
    #  Callable[[BaseModel, BaseParser], BaseModel]:
    element_handlers: Dict[str, Callable[[BaseParser, ET.Element], str]] = {}
    model_handlers: Dict[str, BaseModel] = {}

    @classmethod
    def init_class(cls) -> None:
        cls.add_handler(EK.INFO, ElementParser.parse_info)
        cls.add_handler(EK.INFO2, ElementParser.parse_info2)
        cls.add_handler(EK.ACTION, ElementParser.parse_action)
        cls.add_handler(TE.ALT_TYPE, ElementParser.parse_alt_type)
        cls.add_handler(TE.ALT_INFO, ElementParser.parse_alt_info)
        cls.add_handler(TE.CONTAINER_TOPIC, ElementParser.parse_container_topic)
        cls.add_handler(TE.LABEL_FOR, ElementParser.parse_label_for)
        cls.add_handler(TE.LABELED_BY, ElementParser.parse_labeled_by)
        cls.add_handler(TE.FLOWS_TO, ElementParser.parse_flows_to)
        cls.add_handler(TE.FLOWS_FROM, ElementParser.parse_flows_from)
        cls.add_handler(TE.TRUE_MSG_ID, ElementParser.parse_true_msg_id)
        cls.add_handler(TE.FALSE_MSG_ID, ElementParser.parse_false_msg_id)
        cls.add_handler(TE.READ_NEXT, ElementParser.parse_read_next)
        cls.add_handler(TE.INNER_TOPIC, ElementParser.parse_inner_topic)
        cls.add_handler(TE.OUTER_TOPIC, ElementParser.parse_outer_topic)
        cls.add_handler(TE.TOPIC_LEFT, ElementParser.parse_topic_left)
        cls.add_handler(TE.TOPIC_RIGHT, ElementParser.parse_topic_right)
        cls.add_handler(TE.TOPIC_UP, ElementParser.parse_topic_up)
        cls.add_handler(TE.TOPIC_DOWN, ElementParser.parse_topic_down)
        cls.add_handler(TE.TOPIC_TYPE, ElementParser.parse_topic_type)
        cls.add_handler(TE.TOPIC_HEADING, ElementParser.parse_topic_heading)
        cls.add_handler(TE.HEADING_LABEL, ElementParser.parse_heading_label)
        cls.add_handler(TE.HEADING_LABELED_BY,
                        ElementParser.parse_heading_labeled_by)
        cls.add_handler(TE.HEADING_NEXT, ElementParser.parse_heading_next)
        cls.add_handler(TE.UNITS, ElementParser.parse_topic_units)
        cls.add_handler(TE.VALUE_FROM, ElementParser.parse_topic_value_from)
        cls.add_handler(TE.VALUE_FORMAT, ElementParser.parse_topic_value_format)
        cls.add_handler(EK.ORIENTATION, ElementParser.parse_orientation)
        cls.add_handler(EK.DEFAULT_CONTROL, ElementParser.parse_default_control)
        cls.add_handler(EK.ON_FOCUS, ElementParser.parse_on_focus)
        cls.add_handler(EK.ENABLE, ElementParser.parse_enable)
        cls.add_handler(EK.ON_UNFOCUS, ElementParser.parse_on_unfocus)
        cls.add_handler(EK.VISIBLE, ElementParser.parse_visible)
        cls.add_handler(EK.LABEL, ElementParser.parse_label)
        cls.add_handler(TE.ALT_LABEL, ElementParser.parse_alt_label)
        cls.add_handler(EK.MENU_CONTROL, ElementParser.parse_menu_control)
        cls.add_handler(TE.HINT_TEXT, ElementParser.parse_hint_text)
        cls.add_handler(EK.DESCRIPTION, ElementParser.parse_description)
        cls.add_handler(EK.NUMBER, ElementParser.parse_number)
        cls.add_handler(EK.HAS_PATH, ElementParser.parse_has_path)
        cls.add_handler(EK.SELECTED, ElementParser.parse_selected)
        cls.add_handler(EK.PAGE_CONTROL, ElementParser.parse_page_control_id)
        cls.add_handler(EK.SCROLL_TIME, ElementParser.parse_scroll_time)
        cls.add_handler(EK.SCROLL, ElementParser.parse_scroll)
        cls.add_handler(EK.SHOW_ONE_PAGE, ElementParser.parse_show_one_page)
        cls.add_handler(EK.WRAP_MULTILINE, ElementParser.parse_wrap_multiline)

    @classmethod
    def add_handler(cls, item_key: str | StrEnum,
                    element_parser: Callable[[BaseParser, ET.Element],
                    None | str | int | BaseParser | Tuple[str | int, bool]]) -> None:
        if isinstance(item_key, StrEnum):
            enum_key: StrEnum = item_key
            item_key = enum_key.name

        #  MY_LOGGER.debug(f'Added ElementHandler {item_key}')
        cls.element_handlers[item_key] = element_parser

    @classmethod
    def get_handler(cls,
                    item_key: str | StrEnum
                    ) -> Callable[[BaseParser,  ET.Element | TopicElement],
                                  str | BaseParser]:
        item: Item | None = None
        try:
            if isinstance(item_key, StrEnum):
                enum_key: StrEnum = item_key
                item_key = enum_key.name
                # MY_LOGGER.debug(f'key is enum: {enum_key.name} {enum_key} '
                #                   f'item_key: {item_key}')
            # else:
            #     MY_LOGGER.debug(f'key is str: {item_key} type: {type(item_key)}')
            item: Item = control_elements[item_key]
        except KeyError:
            item = None

        #  MY_LOGGER.debug_v(f'item: {item_key}')
        if item is None or item.ignore:
            MY_LOGGER.debug_v(f'about to call no-op')
            return ElementParser.no_op  # Acts as a Null parser

        # element_handler:  Callable[[BaseParser, ET.Element], str] = None
        try:
            element_handler = cls.element_handlers[item.key]
        except Exception:
            MY_LOGGER.debug_v(f'Handler not found for element: {item.key}')
            raise ParseError(f'Handler not found for element: {item.key}')
        return element_handler


    @classmethod
    def add_model_handler(cls, item: Item,
                          model: Type[BaseModel]) -> None:
        #  MY_LOGGER.debug_v(f'item: {item.key} model: {model}')
        cls.model_handlers[item.key] = model

    @classmethod
    def get_model_handler(cls, item: Item) -> \
            Callable[[BaseModel, BaseParser, WinDialogState | None],
                     ForwardRef('TopicModel') | BaseModel]:
        supress_keys = (ControlElement.IMAGE.name,)
        if item.ignore:
            if item.key not in supress_keys:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'Skipping ignored item: {item.key}')
                pass

        model: BaseModel = None
        try:
            model = cls.model_handlers[item.key]
        except Exception:
            MY_LOGGER.debug_v(f'Model not found for element: {item.key}')
            raise ParseError(f'Model not found for element: {item.key}')
        return model


ElementHandler.init_class()
