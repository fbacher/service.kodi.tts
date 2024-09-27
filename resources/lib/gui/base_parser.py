# coding=utf-8
from pathlib import Path
from typing import Any, Callable, Dict, ForwardRef, List, Tuple, Union

import xbmc
import xbmcvfs

from common.logger import *
from common.monitor import Monitor
from gui.base_tags import ControlElement, Item, Units
from gui.exceptions import ParseError
import xml.etree.ElementTree as ET
from enum import auto, Enum
from typing import Callable

from common.logger import BasicLogger
from gui.base_tags import ControlElement, Tag
from gui.base_tags import BaseAttributeType as BAT
from gui.base_tags import ElementKeywords as EK
from gui.exceptions import ParseError
module_logger = BasicLogger.get_logger(__name__)


class BaseControlParser:
    _logger: BasicLogger = module_logger

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger

    def __init__(self, parent: ForwardRef('BaseParser')) -> None:
        self.parent: BaseParser = parent
        self.tag: str = ''
        self.type: str = ''

    @classmethod
    def no_op(cls, parent: Union[ForwardRef('BaseParser'), None] = None,
              el_page_control_id: ET.Element = None) -> int | None:
        return None

    def __repr__(self) -> str:
        if self.type not in ('image',):
            return f'Ignored tag: {self.tag} type: {self.type}'
        return ''


class BaseParser:
    item: Item = None
    _logger: BasicLogger = module_logger

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger

    def __init__(self, parent: ForwardRef('BaseParser'),
                 window_parser: Union[ForwardRef('ParseWindow'), None] = None) -> None:
        self._window_parser: BaseParser = None
        self._parent: BaseParser = parent
        if window_parser is not None:
            self._window_parser = window_parser
        elif self._parent is not None:
            self._window_parser: BaseParser = parent.window_parser
        self._control_id: int = -1   # Dummy field
        self._control_type: ControlElement = ControlElement.UNKNOWN
        self.tree_id: str = 'DUMMY_BASE_PARSER'
        self.topic: ForwardRef('TopicModel') = None

    @property
    def control_id(self) -> int:
        return self._control_id

    @control_id.setter
    def control_id(self, value: int) -> None:
        clz = BaseParser
        clz._logger.debug(f'new: {value} old {self._control_id} {type(self)}')
        self._control_id = value

    @property
    def control_type(self) -> ControlElement:
        # Window has no parent. Probably should change that
        clz = BaseParser

        if self.parent is not None:
            return self._control_type
        else:
            return self._control_type

    @control_type.setter
    def control_type(self, value: ControlElement) -> None:
        clz = BaseParser
        # Window has no parent
        if self.parent is not None:
            if clz._logger.isEnabledFor(DISABLED):
                clz._logger.debug_xv(f'parent: {self.parent.control_id} '
                                     f'control_id: {self.control_id} '
                                     f'parent control_type: '
                                     f'{self.parent._control_type} self: '
                                     f'{self._control_type} new: {value} '
                                     f'{type(self)}')
            self._control_type = value
        elif clz._logger.isEnabledFor(DISABLED):
            clz._logger.debug_xv(f'self: {self._control_type} new: {value}')
            self._control_type = value

    @property
    def parent(self) -> ForwardRef('BaseParser'):
        return self._parent

    @property
    def window_parser(self) -> ForwardRef('BaseParser'):
        return self._window_parser

    def get_xml_path(self) -> Path | None:
        return self.window_parser.xml_path

    @classmethod
    def get_xml_file_for_current_window(cls) -> Path | None:
        xml_file: str = xbmc.getInfoLabel('Window.Property(xmlfile)')
        xml_path: Path = Path(xml_file)
        if not (xml_path.is_file() and xml_path.exists()):
            if cls._logger.isEnabledFor(DEBUG_V):
                cls._logger.debug_v(f'Window xml file not found: {xml_path}')
            return None
        return xml_path

    @classmethod
    def get_xml_file_for_window(cls, win_dialog_id: int | str) -> Path | None:
        xml_file: str = xbmc.getInfoLabel('Window(win_dialog_id).Property(xmlfile)')
        if xml_file is None:
            if cls._logger.isEnabledFor(DEBUG_V):
                cls._logger.debug_v(f'xml file not defined: for win_dialog_id:'
                                           f' {win_dialog_id}')
            return None
        xml_path: Path = Path(xml_file)
        if not (xml_path.is_file() and xml_path.exists()):
            if cls._logger.isEnabledFor(DEBUG_V):
                cls._logger.debug(f'xml file not found: for win_dialog_id: {win_dialog_id}'
                                  f' {xml_path}')
            return None
        return xml_path

    @classmethod
    def get_kodi_skin_path(cls, fname) -> Path:
        Monitor.exception_on_abort()
        skin_path: Path
        base_path: Path = Path(xbmcvfs.translatePath('special://skin'))
        if cls._logger.isEnabledFor(DEBUG_V):
            cls._logger.debug_v(f'base_path: {base_path}')
        for res in ('720p', '1080i'):
            skin_path = base_path / res
            if skin_path.is_file() and skin_path.exists():
                break
        else:
            aspect = xbmc.getInfoLabel('Skin.AspectRatio')
            addonXMLPath: Path = base_path / 'addon.xml'
            if cls._logger.isEnabledFor(DEBUG):
                cls._logger.debug(f'addonXMLPath: {addonXMLPath}')
            skin_path: Path = Path('')
            if addonXMLPath.is_file() and addonXMLPath.exists():
                with open(addonXMLPath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for l in lines:
                    if f'aspect="{aspect}"' in l:
                        folder = l.split('folder="', 1)[-1].split('"', 1)[0]
                        skin_path = base_path / folder
        path: Path = skin_path / fname
        if not (path.is_file() and path.exists()):
            path = Path('')
        if module_logger.isEnabledFor(DEBUG):
            module_logger.debug_v(f'Including: {path}')
        return path

    @classmethod
    def gettWindowXMLFile(cls, simple_path: Path) -> Path | None:
        """
        Find the path for the current window's xml file. The file may be in one
        of serveral paths.

        :return:
        """
        Monitor.exception_on_abort()
        # simple_path: Path = Path(xbmc.getInfoLabel('Window.Property(xmlfile)'))
        skin_path: Path = cls.get_kodi_skin_path(simple_path)
        possible_paths: Tuple[Path, Path] = simple_path, skin_path
        for path in possible_paths:
            if path.is_file and path.exists():
                return path
        return None

    @classmethod
    def get_control_type(cls, element: ET.Element) -> ControlElement | None:
        clz = BaseParser
        is_control: bool = element.tag in (EK.CONTROL.value, EK.CONTROLS.value)
        if not is_control:
            return None
        for key, value in element.attrib.items():
            clz._logger.debug(f'Key: {key} value: {value}')

        if element.tag == EK.CONTROLS.value:
            return ControlElement.CONTROLS
        control_type_str: str = element.attrib.get(BAT.CONTROL_TYPE)
        if cls._logger.isEnabledFor(DEBUG_V):
            clz._logger.debug_v(f'control_type_str: {control_type_str}')
        if control_type_str is None:
            raise ParseError(f'Missing Control Type')
        control_type: ControlElement = ControlElement(control_type_str)
        if cls._logger.isEnabledFor(DEBUG_V):
            clz._logger.debug_v(f'done: {control_type.value} orig: {control_type_str}')
        return control_type

    @classmethod
    def parse_units(cls,
                    units: str) -> Tuple[Units, Units, float | int, float | int, float | int] | None:
        """
        Parses string into units.
            Example input: "scale=db, type=float, step=.1, min=-12, max=12"
            returns ("db", "float", 0.1, -12, 12)

        :param units: String containing the tokens in any order:
            scale:: db | % | number
            type:: float | int
            step:: a float number indicating the size of each unit
            min:: the maximum possible value of the specified type
            max:: the maximum possible value of the specified type
        :return: parsed units in the following order:
                 (scale, type, step, min, max)
        """
        clz = BaseParser
        expressions: List[str] = units.split(',')
        if cls._logger.isEnabledFor(DEBUG_V):
            clz._logger.debug_v(f'units: {units} split: {expressions}')
        result: List[Any] = []
        scale_value: Units | None = None
        type_value: Units | None = None
        step_value: float | None = None
        min_value: float | None = None
        max_value: float | None = None
        failed: bool = False
        for expr in expressions:
            tokes: List[str] = expr.split('=')
            #  clz._logger.debug_v(f'expr: {expr} tokes: {tokes}')
            try:
                tokes[0] = tokes[0].strip()
                tokes[1] = tokes[1].strip()
                # clz._logger.debug_v(f'tokes: {tokes[0]} {tokes[1]}')
                if tokes[0] == 'scale':
                    scale_value = Units(tokes[1])
                if tokes[0] == 'type':
                    if tokes[1] in ('float', 'int'):
                        type_value = Units(tokes[1])
                        # clz._logger.debug_v(f'type_value = {tokes[1]} {type_value}')
                if tokes[0] == 'step':
                    step_value = float(tokes[1])
                    # clz._logger.debug_v(f'step_value = {tokes[1]} {step_value}')
                if tokes[0] == 'min':
                    min_value = float(tokes[1])
                if tokes[0] == 'max':
                    max_value = float(tokes[1])
                if type_value == 'int':
                    step_value = int(step_value)
                    min_value = int(min_value)
                    max_value = int(max_value)
            except Exception as e:
                clz._logger.exception('')
        if scale_value is None:
            if cls._logger.isEnabledFor(DEBUG):
                cls._logger.debug(f'Expected to find a value for "scale"')
            failed = True
        if type_value is None:
            if cls._logger.isEnabledFor(DEBUG):
                clz._logger.debug(f'Expected to find a value for "type"')
            failed = True
        if step_value is None:
            if cls._logger.isEnabledFor(DEBUG):
                clz._logger.debug(f'Expected to find a value for "step"')
            failed = True
        if min_value is None:
            if cls._logger.isEnabledFor(DEBUG):
                clz._logger.debug(f'Expected to find a value for "min"')
            failed = True
        if max_value is None:
            if cls._logger.isEnabledFor(DEBUG):
                clz._logger.debug(f'Expected to find a value for "max"')
            failed = True

        if not failed:
            return scale_value, type_value, step_value, min_value, max_value
        return None


BaseParser.init_class()
