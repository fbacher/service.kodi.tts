# coding=utf-8

import xml.etree.ElementTree as ET
from enum import StrEnum
from pathlib import Path
from typing import Callable, List, Tuple

from common.logger import BasicLogger, DEBUG_V
from gui.base_tags import control_elements, ControlElement, Item, WindowType
from gui.element_parser import ( BaseElementParser,
                                ElementHandler)
from gui.parser.parse_button import ParseButton
from gui.parser.parse_controls import CreateControl, ParseControls
from gui.parser.parse_control import ParseControl
from gui.base_parser import BaseParser
from gui.parser.parse_edit import ParseEdit
from gui.parser.parse_focused_layout import ParseFocusedLayout
from gui.parser.parse_group import ParseGroup
from gui.parser.parse_group_list import ParseGroupList
from gui.parser.parse_item_layout import ParseItemLayout
from gui.parser.parse_label import ParseLabel
from gui.parser.parse_list import ParseList
from gui.parser.parse_radio_button import ParseRadioButton
from gui.parser.parse_scrollbar import ScrollbarParser
from gui.parser.parse_slider import ParseSlider
from gui.parser.parse_spin import ParseSpin
from gui.parser.parse_spinex import ParseSpinex
from gui.parser.parse_topic import ParseTopic
from windows.windowparser import WindowParser
from gui.base_tags import ElementKeywords as EK

module_logger = BasicLogger.get_logger(__name__)


class InitParsers:
    @staticmethod
    def init_all():
        ParseLabel.init_class()
        ParseButton.init_class()
        ParseRadioButton.init_class()
        ParseSlider.init_class()
        ParseSpin.init_class()
        ParseSpinex.init_class()
        CreateControl.init_class()
        ParseControl.init_class()
        ParseControls.init_class()
        ParseGroup.init_class()
        ParseGroupList.init_class()
        ParseGroupList.init_class()
        ParseItemLayout.init_class()
        ParseFocusedLayout.init_class()
        ParseList.init_class()
        BaseElementParser.init_class()
        ScrollbarParser.init_class()
        ParseEdit.init_class()
        ParseTopic.init_class()
        ElementHandler.init_class()


InitParsers.init_all()


class ParseWindow(BaseParser):
    """
    The header contains the following tags:

    onload
        Optional: the build-in function to execute when the window opens
    onunload
        Optional: the build-in function to execute when the window closes
    defaultcontrol
        This specifies the default control of the window. This is the id of the control
        that will receive focus when the window is first opened. Note that most Kodi
        windows save the current focus when you leave the window, and will return to the
        last focused item when you return to a window. This behaviour can be stopped by
        specifying the attribute always="true".
    menucontrol
        This specifies the control that will be focused when the users presses the 'menu' /
        'm' button.
    backgroundcolor
        Specifies whether the window needs clearing prior to rendering, and if so which
        colour to use. Defaults to clearing to black. Set to 0 (or 0x00000000) to have no
        clearing at all. If your skin always renders opaque textures over the
        entire screen (eg using a backdrop image or multiple backdrop images)
        then setting the background color to 0 is the most optimal value and may
        improve performance significantly on slow GPUs.
    visible
        Specifies the conditions under which a dialog will be visible. Kodi evaluates this
        at render time, and shows or hides a dialog depending on the evaluation of this
        tag. See here for more details. Applies only to type="dialog" windows. By default
        if a dialog visibility depends on visible condition it will be set as Modeless. A
        modeless dialog won't be able to catch input as any keystroke/action will be sent
        to the underlying window. Since v20 you can override this behaviour by setting
        modality="modal" on the root element of the window/dialog XML definition.
    animation
        Specifies the animation effect to perform when opening or closing the window. See
        here for more details.
    zorder
        This specifies the “depth” that the window should be drawn at. Windows with higher
        zorder are drawn on top of windows with lower z-order. All dialogs by default have
        zorder 1, so if you have a particular dialog that you want underneath all others,
        give it a zorder of 0. (Note that the normal render order is: The base window,
        then the overlays (music + video), then dialogs. <zorder> only effects the
        rendering of the dialogs.
    coordinates
        This block is used to specify how Kodi should compute the coordinates of
        all controls.
    left
        Sets the horizontal “origin” position of the window. Defaults to 0 if not present.
    top
        Sets the vertical “origin” position of the window. Defaults to 0 if not present.
    origin
        Sets a conditional origin for the window. The window will display at (x,y)
         whenever
        the origin condition is met. You can have as many origin tags as you like – they
        are evaluated in the order present in the file, and the first one for which the
        condition is met wins. If none of the origin conditions are met, we fall back to
        the <left> and <top> tags.
    previouswindow
        This can be used to specify a window to force Kodi to go to on press of the Back
        button. Normally Kodi keeps a “window stack” of previous windows to handle this.
        This tag allows you to override this behaviour. The value is the name of
        the window.
    views
        This tag lets you use view id's beyond 50 to 59 it also lets you set the order in
        which they cycle with the change view button in the skin. Only useful in
        My<Foo>.xml windows.
    controls
        This is the block the defines all controls that will appear on this window.

    """
    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.WINDOW]


    def __init__(self):
        super().__init__(parent=None, window_parser=self)
        clz = type(self)
        clz._logger.debug(f'SETTING self.control_type to WINDOW')
        self.control_type = ControlElement.WINDOW
        self.topic: ParseTopic | None = None
        self.xml_path: Path = None  # Source path of current window xml
        self.win_parser: WindowParser = None
        self.window_type: WindowType = None
        # self.win_dialog_id: int = -1
        self.control_id: int = 0
        self.window_modality: str = ''   # Only applies to dialogs
        self.xml_root: ET.Element = None
        self.menu_control: int = -1
        self.default_control_id: str = None
        self.children: List[BaseParser] = []
        self.visible_expr: str = ''

        if clz._logger.isEnabledFor(DEBUG_V):
            clz._logger.debug_v(f'control_type.label: {self.control_type} '
                          f'name: {self.control_type.name} '
                          f'value: {self.control_type.value}'
                          f'str: {str(self.control_type)}')

    @property
    def control_type(self) -> ControlElement:
        return BaseParser.control_type.fget(self)

    @control_type.setter
    def control_type(self, value: ControlElement) -> None:
        BaseParser.control_type.fset(self, value)

    def calculate_allowed_children(self) -> None:
        pass

    def parse_window(self, control_id: int,
                     xml_path: Path | None, is_addon: bool = False) -> None:
        """
         Get window type
         Get default control id
         Get any property information
         For each immediate child have Control build the model for each Control
         and pass back relevent information for Window
        """
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG_V):
            clz._logger.debug_xv(f'In create_model xml_path: {xml_path}')
        if xml_path is None:
            xml_path: Path = Path('/home/fbacher/.kodi/addons/skin.estuary/xml/Home.xml')
        self.xml_path = xml_path
        if self.xml_path is None:
            if clz._logger.isEnabledFor(DEBUG_V):
                clz._logger.debug_v(f'xml_path path not found: {self.xml_path}. Now what?')
            return
        self.control_id = 0  # Windows do not have a control
        #  clz._logger.debug(f'About to parse: {self.xml_path}')
        self.win_parser: WindowParser = WindowParser(self.xml_path)
        self.xml_root = self.win_parser.get_xml_root()
        # Now extract what we need to get information about the Window

        # type == window | dialog
        self.window_type: WindowType = self.win_parser.get_window_type()
        self.default_control_id = self.get_default_control()

        # Parse each child element/control
        tags_to_parse: Tuple[str, ...] = (EK.TOPIC, EK.MENU_CONTROL,
                                          EK.CONTROL, EK.CONTROLS)
        elements: [ET.Element] = self.xml_root.findall(f'./*')
        element: ET.Element
        for element in elements:
            if element.tag in tags_to_parse:
                #  clz._logger.debug(f'element_tag: {element.tag}')
                key: str = element.tag
                control_type: ControlElement = clz.get_control_type(element)
                str_enum: StrEnum = None
                if control_type is not None:
                    str_enum = control_type
                else:
                    str_enum = EK(element.tag)

                # control_elements MUCH prefers a StrEnum, otherwise it MUST
                # be the 'name' property of the proper StrEnum defined in base_tags

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

    def get_default_control(self) -> str:
        default_control_element: ET.Element
        def_control: ET.Element = self.xml_root.find(f'./{EK.DEFAULT_CONTROL.value}')
        return def_control.text

    def __repr__(self) -> str:
        clz = type(self)
        result: str = ''

        #  Start with this window
        window_str: str = (f'\nwindow: {self.window_type} id: {self.control_id}')
        menu_ctrl_str: str = ''
        if self.menu_control != -1:
            menu_ctrl_str = f'\n menu_ctrl: {self.menu_control}'
        default_control_str: str = f''
        if self.default_control_id != '':
            default_control_str = f'\n default_control: {self.default_control_id}'
        visible_expr_str: str = ''
        if self.visible_expr != '':
            visible_expr_str = f'\n visible_expr: {self.visible_expr}'
        window_modality: str = ''
        if self.window_modality != '':
            window_modality = f'\n window_modality: {self.window_modality}'

        topic_str: str = ''
        if self.topic != '':
            topic_str = f'\n  Topic:{self.topic}'

        results: List[str] = []
        result = (f'ParseWindow: {window_str}{default_control_str}'
                  f'{menu_ctrl_str}{visible_expr_str}{window_modality}'
                  f'{topic_str}')
        results.append(result)
        if clz._logger.isEnabledFor(DEBUG_V):
            clz._logger.debug_v(f'\n # children: {len(self.children)}')
        for control in self.children:
            control: BaseParser
            result: str = str(control)
            results.append(result)

        return '\n'.join(results)

    def dump_parsed(self) -> List[str]:
        clz = type(self)
        results: List[str] = []
        result: str = str(self)
        results.append(result)

        """
        for child in self.parsers:
            child: BaseParser
            child_result: str = str(child)
            results.append(child_result)
        """

        return results
