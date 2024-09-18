# coding=utf-8
from collections import namedtuple
from typing import Dict, ForwardRef, List, Tuple
import xml.etree.ElementTree as ET

import xbmc

from common.logger import BasicLogger
from gui import ParseError
from gui.base_tags import AttribInfo, control_elements, ControlElement, ElementType, Item
from gui.window import Window

ControlInfo = namedtuple('ControlInfo', ['win_dialog_id', 'control_id',
                                         'is_current_window'])
module_logger = BasicLogger.get_logger(__name__)


class BaseControlx:
    _logger: BasicLogger = module_logger

    @classmethod
    def class_init(cls):
        if cls._logger is None:
            cls._logger = module_logger

    def __init__(self, control_type: ControlElement, win_dialog_id: int, id_val: int = None,
                 visible: bool = False):
        clz = type(self)
        self.win_dialog_id: int = win_dialog_id
        self.window_name: str = Window.get_window_name_for_id(win_dialog_id)
        self.id: int = id_val
        self.control_type: ControlElement = control_type
        self.visible: bool = visible
        self.parent: BaseControl = None
        self.parent_type: ControlElement = None
        self.parent_id: int = None

        self.child_by_id: Dict[str, BaseControl] = {}
        self.child_ids_by_type: Dict[ControlElement.name, List[int]] = {}

    def get_win_dialog_id(self) -> int:
        return self.win_dialog_id

    def get_id(self) -> int:
        return self.id

    def get_type(self) -> ControlElement:
        return self.control_type

    def set_parent(self, parent: ForwardRef('BaseControl')) -> None:
        self.parent = parent

    def set_parent_ids(self, parent_type: ControlElement, parent_id: int) -> None:
        self.parent_type = parent_type
        self.parent_id = parent_id

    def get_parent(self) -> ForwardRef('BaseControl'):
        return self.parent

    def get_parent_ids(self) -> Tuple[ControlElement, int]:
        return self.parent_type, self.parent_id

    def set_child(self, child: ForwardRef('BaseControl')) -> None:
        self.child_by_id[child.get_id()] = child

    def get_label(self, control_id: int, win_dialog_id: int) -> str:
        if Window.has_focus(win_dialog_id):

            xbmc.getInfoLabel("Control.GetLabel({control_id})[.index()]")

        text: str = xbmc.getInfoLabel('System.CurrentControl')  # Not if this doesn't have focus
        return text

    @staticmethod
    def get_current_control() -> ControlInfo:
        control_name: str = xbmc.getInfoLabel('System.CurrentControl')
        control_id: str = BaseControl.get_current_control_id()
        current_window_name: str = Window.get_current_window_name()
        module_logger.debug(f'control_name: {control_name} '
                            f'current_window_name: {current_window_name} '
                            f'current_control_id: {control_id}')
        result: ControlInfo = ControlInfo(current_window_name,
                                          control_name,
                                          current_window_name)
        result.control_id = control_name
        return result

    @classmethod
    def get_control_type(cls, element: ET.Element) -> ControlElement | None:
        is_control: bool = (element.tag == Tag.CONTROL.value)
        if not is_control:
            return None
        control_type_str: str = element.attrib.get(BAT.CONTROL_TYPE.value)
        if control_type_str is None:
            raise ParseError(f'Missing Control Type')
        control_type: ControlElement = ControlElement(control_type_str)
        return control_type

    @staticmethod
    def get_current_control_id() -> str:
        control_id: str = xbmc.getInfoLabel('System.CurrentControlId')
        return control_id

    @classmethod
    def get_attribs(cls, el_current: ET.Element) ->List[AttribInfo]:
        result: List[AttribInfo] = []
        attrib_entry: Dict[str, str] = el_current.attrib
        cls._logger.debug(f'attrib_entry: {attrib_entry}')
        tag: str = el_current.tag
        for key in attrib_entry.keys():
            cls._logger.debug(f'key: {key}')
            attrib: str = attrib_entry[key]
            if tag == 'control' and key == 'type':
                control_type: ControlElement = cls.get_control_type(el_current)
                key = control_type.name
            item: Item = control_elements.get(key)
            status: str = ''
            if item is None:
                item = Item(keyword=key, is_control=False,
                            element_type=ElementType.ATTRIB, registered=False,
                            element_tag=el_current.tag)
                status = f'unregistered tag: {el_current.tag}'

            result_entry: AttribInfo = (key, attrib, status)
            result.append(result_entry)

        return result

    @classmethod
    def get_all_immediate_attribs(cls, el_current: ET.Element) -> List[AttribInfo]:
        child: ET.Element
        attribs: List[AttribInfo] = []
        attribs.extend(cls.get_attribs(el_current))

        for child in el_current.findall('./*'):
            attribs.extend(cls.get_attribs(child))

        return attribs

    @classmethod
    def get_attribs(cls, el_current: ET.Element) -> List[AttribInfo]:
        result: List[AttribInfo] = []
        attrib_entry: Dict[str, str] = el_current.attrib
        cls._logger.debug(f'attrib_entry: {attrib_entry}')
        tag: str = el_current.tag
        for key in attrib_entry.keys():
            cls._logger.debug(f'key: {key}')
            attrib: str = attrib_entry[key]
            if tag == 'control':
                control_type: ControlElement = cls.get_control_type(el_current)
                key = control_type.name
            item: Item = control_elements.get(key)
            status: str = ''
            if item is None:
                item = Item(keyword=key, is_control=False,
                            element_type=ElementType.ATTRIB, registered=False,
                            element_tag=el_current.tag)
                status = f'unregistered tag: {el_current.tag}'

            result_entry: AttribInfo = (key, attrib, status)
            result.append(result_entry)

        return result


BaseControl.class_init()
