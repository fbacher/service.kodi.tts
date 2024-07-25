# coding=utf-8

"""
Tags available to all controls

id 	Specifies the control's id. The value this takes depends on the control type,
and the window that you are using the control on. There are special control id's that
must be present in each window. Any other controls that the skinner adds can be any id
they like. Any controls that the skinner specifies content needs not have an id unless
it's needed for animation purposes. For instance, most image and label controls don't
need an id if the skinner specifies they're content.

visible 	Specifies a condition as to when this control will be visible. Can be true,
false, or a condition. See Conditional Visibility for more information. Defaults to true.


"""
from collections import namedtuple
from enum import auto, Enum, StrEnum
from typing import Dict, ForwardRef, Iterable, List, TypeAlias

from common.logger import BasicLogger
import xml.etree.ElementTree as ET
from enum import auto, Enum
from typing import Callable, ForwardRef, List, Tuple, Union

from common.logger import BasicLogger

module_logger = BasicLogger.get_module_logger(module_path=__file__)

AttribInfo = namedtuple('attrib_info', ['attrib_name', 'attrib_value',
                                         'status'])


class BaseAttributeType(StrEnum):
    ID = 'id'
    CONTROL_TYPE = 'type'
    SLIDER = 'slider'
    LABEL = 'label'
    LABEL_ID = 'label_id'
    SET_FOCUS = 'setfocus'
    TYPE = 'type'
    ALT_TYPE = 'alt_type'
    LABEL_FOR = 'label_for'
    LABELED_BY = 'labeled_by'
    ALT_LABEL = 'alt_label'
    TOPIC = 'topic'
    NAME = 'name'
    HINT_TEXT = 'hinttext'
    FLOWS_TO = 'flowsto'
    FLOWS_FROM = 'flowsfrom'
    # For binary controls: RadioButton. By default, 'Enabled' is
    # substituted for '(*)' from the ListItem value of the control
    TRUE_MSG_ID = 'true_msg_id'
    # For binary controls: RadioButton. By default, 'Disabled' is
    # substituted for '()' from the ListItem value of the control
    FALSE_MSG_ID = 'false_msg_id'
    # INNER/OUTER are to traverse the logically
    # superior/inferior topic (window header is
    # superior to all, categories, etc. are in
    # between and detail values are most inferior)
    INNER_TOPIC = 'innertopic'
    OUTER_TOPIC = 'outertopic'
    # LEFT/RIGHT are for topics to the physical left/right.
    # similar for UP/DOWN.
    TOPIC_LEFT = 'topicleft'
    TOPIC_RIGHT = 'topicright'
    TOPIC_UP = 'topicup'
    TOPIC_DOWN = 'topicdown'
    RANK = 'rank'
    TOPIC_TYPE = 'topictype'
    UNITS = 'units'  # complex string value


class ControlType(StrEnum):
    BUTTON = 'button'
    CONTROLS = 'controls'
    CONTROL = 'control'
    DIALOG = 'dialog'
    EDIT = 'edit'
    EPG_GRID = 'epggrid'
    FADE_LABEL = 'fadelabel'
    FIXED_LIST = 'fixedlist'
    GAME_CONTROLLER = 'gamecontroller'
    GAME_CONTROLLER_LIST = 'gamecontrollerlist'
    GAME_WINDOW = 'gamewindow'
    GROUP = 'group'
    GROUP_LIST = 'grouplist'
    IMAGE = 'image'
    LABEL_CONTROL = 'label'
    LIST = 'list'
    MENU_CONTROL = 'menucontrol'
    MOVER = 'mover'
    MULTI_IMAGE = 'multiimage'
    PANEL = 'panel'
    PROGRESS = 'progress'
    RADIO_BUTTON = 'radiobutton'
    RANGES = 'ranges'
    RESIZE = 'resize'
    RSS = 'rss'
    SCROLL_BAR = 'scrollbar'
    SLIDER_EX = 'sliderex'
    SLIDER = 'slider'
    SPIN_CONTROL_EX = 'spincontrolex'
    SPIN_CONTROL = 'spincontrol'
    TEXT_BOX = 'textbox'
    TOGGLE_BUTTON = 'togglebutton'
    UNKNOWN = 'unknown_control'
    VIDEO_WINDOW = 'video_window'
    VISUALISATION = 'visiualisation'
    WINDOW = 'window'
    WRAP_LIST = 'wraplist'


class ElementType(StrEnum):
    CONTROL = 'control'
    NON_CONTROL = 'noncontrol'
    BOTH = 'both'
    ATTRIB = 'attrib'
    HINT_TEXT = 'hinttext'
    ALT_LABEL = 'alt_label'
    ALT_INFO = 'alt_info'
    WINDOW = 'window'

# Tags available to all controls
"""
description 	Only used to make things clear for the skinner. Not read by Kodi at all.
left 	        Specifies where the left edge of the control should be drawn, relative 
to it's parent's left edge. If an "r" is included (eg 180r) then the measurement is 
taken from the parent's right edge (in the left direction). This can be an absolute 
value or a %.
top 	        Specifies where the top edge of the control should be drawn, relative to 
it's parent's top edge. If an "r" is included (eg 180r) then the measurement is taken 
from the parent's bottom edge (in the up direction). This can be an absolute value or a %.
right 	        Specifies where the right edge of the control should be drawn. This can 
be an absolute value or a %.
bottom 	        Specifies where the bottom edge of the control should be drawn. This can 
be an absolute value or a %.
centerleft 	    A   ligns the control horizontally at the given coordinate measured from 
the left side of the parent control. This can be an absolute value or a %.
centerright 	Aligns the control horizontally at the given coordinate measured from 
the right side of the parent control. This can be an absolute value or a %.
centertop 	    Aligns the control vertically at the given coordinate measured from the 
top side of the parent control. This can be an absolute value or a %.
centerbottom 	Aligns the control vertically at the given coordinate measured from the 
bottom side of the parent control. This can be an absolute value or a %.
width 	        Specifies the width that should be used to draw the control. You can use 
<width>auto</width> for labels (in grouplists) and button/togglebutton controls.
height 	        Specifies the height that should be used to draw the control.
visible 	    Specifies a condition as to when this control will be visible. Can be 
true, false, or a condition. See Conditional Visibility for more information. Defaults 
to true.
animation 	    Specifies the animation to be run when the control enters a particular 
state. See Animating your skin for more information.
camera 	        Specifies the location (relative to the parent's coordinates) of the 
camera. Useful for the 3D animations such as rotatey. Format is <camera x="20" y="30" 
/>. 'r' values and % are also supported.
depth 	        Specifies the 3D stereoscopic depth of a control. possible values range 
from -1.0 to 1.0, which brings control "to back" and "to front".
colordiffuse 	This specifies the color to be used for the texture basis. It's in hex 
AARRGGBB format. If you define <colordiffuse>FFFF00FF</colordiffuse> (magenta), 
the image will be given a magenta tint when rendered. Defaults to FFFFFFFF (no tint). 
You can also specify this as a name from the colour theme.

Tags available to focusable controls

onup 	        Specifies the <id> of the control that should be moved to when the user 
moves up off this control. Can point to a control group (which remembers previous 
focused items).
ondown 	        Specifies the <id> of the control that should be moved to when the user 
moves down off this control. Can point to a control group (which remembers previous 
focused items).
onleft 	        Specifies the <id> of the control that should be moved to when the user 
moves left off this control. Can point to a control group (which remembers previous 
focused items).
onright     	Specifies the <id> of the control that should be moved to when the user 
moves right off this control. Can point to a control group (which remembers previous 
focused items).
onback 	        Specifies the <id> of the control that should be focussed when the user 
presses the back key. Can point to a control group (which remembers previous focused 
items).
oninfo 	        Specifies the built-in function that should be executed when the user 
presses the info key.
onfocus 	    Specifies the built-in function that should be executed when the control 
is focussed.
onunfocus 	    Specifies the built-in function that should be executed when the control 
is loses focus.
hitrect 	    Specifies the location and size of the "focus area" of this control (
relative to the parent's coordinates) used by the mouse cursor. Format is <hitrect 
x="20" y="30" w="50" h="10" />
hitrectcolor 	This adds the ability to visualize hitrects for controls. When visible 
and there's a <hitrectcolor> tag, it will paint a colored rectangle over the actual 
control. Colors can be specified in AARRGGBB format or a name from the color theme.
enable 	        Specifies a condition as to when this control will be enabled. Can be 
true, false, or a condition. See Conditional Visibility for more information. Defaults 
to true.
pulseonselect 	This specifies whether or not a button type will "pulse" when it has 
focus. This is done by varying the alpha channel of the button. Defaults to true. 
"""


class KeywordInfo:

    def __init__(self, keyword: str, only_focusable: bool, tts_ignored: bool,
                 element_type: ElementType):
        self.keyword: str = keyword
        self.only_focusable: bool = only_focusable
        self.tts_ignored: bool = tts_ignored
        self.element_type: ElementType = element_type


KeywordInfo("description", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("left", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("top", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("right", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("bottom", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("centerleft", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("centerright", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("centertop", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("centerbottom", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("width", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("height", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("visible", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("animation", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("camera", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("depth", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("colordiffuse", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)

KeywordInfo("onup", only_focusable=True, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("ondown", only_focusable=True, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("onleft", only_focusable=True, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("onright", only_focusable=True, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("onback", only_focusable=True, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("oninfo", only_focusable=True, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("onfocus", only_focusable=True, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("onunfocus", only_focusable=True, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("hitrect", only_focusable=True, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("hitrectcolor", only_focusable=True, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("enable", only_focusable=True, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("pulseonselect", only_focusable=True, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("control", only_focusable=False, tts_ignored=False,
            element_type=ElementType.CONTROL)
KeywordInfo("controls", only_focusable=False, tts_ignored=False,
            element_type=ElementType.CONTROL)
KeywordInfo("action", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("default_control", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("onclick", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("visible", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("label", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo(ControlType.LABEL_CONTROL.name, only_focusable=False, tts_ignored=False,
            element_type=ElementType.CONTROL)
KeywordInfo("label2", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("menucontrol", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("visible", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("info", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("number", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("haspath", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("scrollsuffix", only_focusable=False, tts_ignored=True,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("orientation", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)
KeywordInfo("scroll", only_focusable=False, tts_ignored=False,
            element_type=ElementType.NON_CONTROL)


class Item:
    """
    Defines every element Tag and the possible attributes that it can have
    """

    def __init__(self, keyword: str | StrEnum, attributes: str | List[str] | None = None,
                 attributes_with_values: str | List[str] | None = None,
                 ignore: bool = False, is_control: bool = False,
                 focusable: bool = True,
                 element_type: ElementType = ElementType.NON_CONTROL,
                 registered: bool = True, element_tag: str = ''):
        """
        Defines the possible attributes that a particular Element can have

        :param keyword:
        :param attributes: Attribute names which do not have values
        :param attributes_with_values: Attribute names that do have values
        :param ignore:  If True, then TTS ignores this element
        :param focusable: For Controls, True if the Control receives focus
        :param is_control: True, then is keyword is a Control
        :param element_type: CONTROL when the element is a Control,
                             NON_CONTROL when the element is not a Control
                             BOTH when the element can be both
        """
        self.keyword: str | StrEnum = keyword
        attribs: List[str] = []
        if attributes is not None:
            if not isinstance(attributes, list):
                attribs = [attributes]
            else:
                attribs = attributes
        self.attributes: List[str] = attribs

        attribs_with_values: List[str] = []
        if attributes_with_values is not None:
            if not isinstance(attributes_with_values, list):
                attribs_with_values = [attributes_with_values]
            else:
                attribs_with_values = attributes_with_values
        self.attributes_with_values: List[str] = attribs_with_values
        self.ignore: bool = ignore
        self.is_control = is_control
        self.focusable: bool = focusable
        self.element_type: ElementType = element_type
        self.registered: bool = registered
        self.element_tag: str = element_tag

    @property
    def key(self) -> str | StrEnum:
        """
        The Element's tag value, for use as a map's key
        :return:
        """
        return self.keyword

    @property
    def value(self) -> ForwardRef('Item'):
        """
        For use as the 'value' entry in a Dict of Items
        :return:
        """
        return self

    def __repr__(self) -> str:
        result: str
        keyword_str: str = f'{self.keyword}'
        ignore_str: str = f'ignore: {self.ignore}'
        focusable_str: str = f'focusable: {self.focusable}'
        element_type_str: str = f'element_type: {self.element_type}'
        is_control_str: str = f'is_control: {self.is_control}'
        registered_str: str = ''
        if not self.registered:
            registered_str = f' registered: {self.registered} tag: {self.element_tag}'

        """
        attribs: List[str] = []
        if attributes is not None:
            if not isinstance(attributes, list):
                attribs = [attributes]
            else:
                attribs = attributes
        self.attributes: List[str] = attribs

        attribs_with_values: List[str] = []
        if attributes_with_values is not None:
            if not isinstance(attributes_with_values, list):
                attribs_with_values = [attributes_with_values]
            else:
                attribs_with_values = attributes_with_values
        self.attributes_with_values: List[str] = attribs_with_values
        """
        result = (f'{keyword_str} {ignore_str} {focusable_str} {element_type_str} '
                  f'{is_control_str}{registered_str}')
        return result


class Items:

    def __init__(self) -> None:
        self.items: Dict[str | StrEnum, Item] = {}

    def add(self, item: Item) -> None:
        clz = type(self)
        if item.key in self.items.keys():
            module_logger.debug(f'Dupe: {item.key}')
            raise KeyError(f'Duplicate: {item.key}')
        self.items[item.key] = item

    def add_all(self, items: Iterable[Item]) -> None:
        clz = type(self)
        item: Item
        for item in items:
            try:
                self.add(item)
            except KeyError:
                module_logger.debug(f'duplicate: {item.key}')

    def keys(self):
        return self.items.keys()

    def values(self):
        return self.items.values()

    def get(self, key) -> Item:
        return self.items.get(key)

    def __getitem__(self, key: str) -> Item:
        item: Item = self.get(key)
        if item is None:
            raise KeyError(f'{key}')
        return item



class Tag(StrEnum):
    CONTROL = 'control'
    ON_FOCUS = 'onfocus'
    ON_CLICK = 'onclick'
    VISIBLE = 'visible'


class ElementKeywords(StrEnum):
    ACTION = 'action'
    ALT_LABEL = 'alt_label'
    BUTTON = 'button'
    DEFAULT_CONTROL = 'defaultcontrol'
    DIALOG = 'dialog'
    CONTROL = 'control'
    CONTROLS = 'controls'
    GROUP = 'group'
    ON_FOCUS = 'onfocus'
    ON_UNFOCUS = 'onunfocus'
    ON_CLICK = 'onclick'
    PAGE_CONTROL = 'pagecontrol'
    VISIBLE = 'visible'
    HINT_TEXT = 'hinttext'
    LABEL = 'label'
    LABEL2 = 'label2'
    INFO = 'info'
    MENU_CONTROL = 'menucontrol'
    NUMBER = 'number'
    SHOW_ONE_PAGE = 'showonepage'
    HAS_PATH = 'haspath'
    SCROLL_SUFFIX = 'scrollsuffix'
    SCROLL = 'scroll'
    SCROLL_TIME = 'scrolltime'  # Might care about scrolling of ui during TTS
    SELECTED = 'selected'
    ON_INFO = 'oninfo'
    ORIENTATION = 'orientation'
    DESCRIPTION = 'description'
    ENABLE = 'enable'
    TOPIC = 'topic'
    WINDOW = 'window'
    WRAP_MULTILINE = 'wrapmultiline'

control_attributes_with_values: List[str]
control_attributes_with_values = ['id', 'type',
                                  BaseAttributeType.ALT_TYPE,
                                  'label_for'
                                  'labeled_by', 'flows_to', 'flows_from']
control_elements: Items = Items()
control_items_list: List[Item] = [
    Item(ElementType.ALT_LABEL, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ElementType.ALT_INFO, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ElementType.HINT_TEXT, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(keyword=ControlType.CONTROL.name, is_control=True,
         element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(keyword=ControlType.CONTROLS.name, is_control=True,
         element_type=ElementType.CONTROL,
         attributes_with_values=['id', 'type']),
    Item(keyword="colorbutton", is_control=True, ignore=True,
         element_type=ElementType.CONTROL),
    Item(keyword="defaultcontrol", is_control=False, ignore=False,
         element_type=ElementType.NON_CONTROL),
    Item(keyword='dialog', is_control=False, ignore=False,
         attributes_with_values=['type', 'tts', 'label'],
         element_type=ElementType.WINDOW),
    Item(ControlType.BUTTON.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item("renderaddon", is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlType.SCROLL_BAR.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlType.EPG_GRID.name, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlType.EDIT.name, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlType.FADE_LABEL.name, is_control=True, ignore=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlType.FIXED_LIST.name, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlType.GAME_WINDOW.name, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlType.GAME_CONTROLLER.name, is_control=True,
         element_type=ElementType.CONTROL),
    Item(ControlType.GAME_CONTROLLER_LIST.name, is_control=True,
         element_type=ElementType.CONTROL),
    Item(ControlType.GROUP.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values, attributes=None,
         focusable=True),
    Item(ControlType.GROUP_LIST.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item("haspath", is_control=False, element_type=ElementType.NON_CONTROL),
    Item(ControlType.IMAGE.name, is_control=True, focusable=False,
         element_type=ElementType.CONTROL, ignore=True),
    Item(ControlType.LABEL_CONTROL.name, is_control=True, focusable=False,
         element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item("label", is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item("label2", is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL),
    Item("hinttext", is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL),
    Item(ControlType.LIST.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlType.MENU_CONTROL.name, is_control=True, element_type=ElementType.NON_CONTROL),
    Item(ControlType.MOVER.name, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlType.MULTI_IMAGE.name, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item("number", is_control=False, focusable=True,
         element_type=ElementType.NON_CONTROL),
    Item(ControlType.PANEL.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item('pagecontrol', is_control=False, element_type=ElementType.NON_CONTROL),
    Item(ControlType.PROGRESS.name, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlType.RSS.name, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlType.RANGES.name, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlType.RADIO_BUTTON.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlType.RESIZE.name, is_control=True, element_type=ElementType.CONTROL),
    Item("selected", is_control=False, element_type=ElementType.NON_CONTROL),
    Item('scrollist', is_control=False, element_type=ElementType.NON_CONTROL),
    Item('scrolltime', is_control=False, element_type=ElementType.NON_CONTROL),
    Item('scroll', is_control=False, element_type=ElementType.NON_CONTROL),
    Item('showonepage', is_control=False, element_type=ElementType.NON_CONTROL),
    Item(ControlType.SLIDER_EX.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlType.SLIDER.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlType.SPIN_CONTROL.name, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlType.SPIN_CONTROL_EX.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlType.TEXT_BOX.name, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlType.TOGGLE_BUTTON.name, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ElementKeywords.TOPIC, is_control=False, ignore=False,
         element_type=ElementType.NON_CONTROL),
    Item(ControlType.VIDEO_WINDOW.name, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlType.VISUALISATION.name, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlType.WINDOW.name, is_control=False,
         attributes_with_values=['type', 'tts', 'label'],
         element_type=ElementType.WINDOW),
    Item("wraplist", is_control=True, element_type=ElementType.CONTROL),
    # ]
    # control_elements.add_all(control_items_list)

    # non_default: List[Item] = [
    Item('angle', ignore=True),
    # ]

    # non_default_items: Items = Items()
    # non_default_items.add_all(non_default)

    # tmp: List[Item] = [
    # The only ones we care about
    Item('action'),
    Item('enable'),
    #  Item('label'),
    Item('orientation'),
    Item('wrapmultiline'),
    Item('description'),
    Item('info'),
    Item('visible'),

    # Color related
    Item('texturefocus', attributes_with_values='colordiffuse', ignore=True),
    Item('texturenofocus', attributes_with_values='colordiffuse', ignore=True),
    Item('focusedcolor', ignore=True),
    Item('textcolor', ignore=True),
    Item('disabledcolor', ignore=True),
    Item('invalidcolor', ignore=True),
    Item('shadowcolor', ignore=True),
    # Position related
    Item('posx', ignore=True),
    Item('posy', ignore=True),
    Item('align', ignore=True),
    Item('aligny', ignore=True),
    Item('textoffsetx', ignore=True),
    Item('textoffsety', ignore=True),
    Item('textwidth', ignore=True),
    # Action related
    Item('onclick', ignore=True),
    # Misc
    Item('font', ignore=True),
    Item('colordiffuse', ignore=True),
    # Position items
    Item('width', ignore=True),
    Item('height', ignore=True),
    #    ]

    # default_items: Items = Items()
    # default_items.add_all(tmp)

    # focusable_control_default_items: List[Item] = [
    # The only ones we care about
    Item('onfocus'),
    Item('onunfocus'),
    # Who cares?
    Item('pulseonselect', ignore=True),
    Item('onup', ignore=True),
    Item('ondown', ignore=True),
    Item('onleft', ignore=True),
    Item('onright', ignore=True),
    Item('coordinates', ignore=True),
    Item('texture', ignore=True)
    ]
control_elements.add_all(control_items_list)

class WindowType(StrEnum):
    WINDOW = 'window'
    DIALOG = 'dialog'
    UNKNOWN = 'unknown_window_type'


class BaseAttributes:

    def __init__(self, id_val: int, visible: bool):
        self.id: int = id_val
        self.visible: bool = visible

class Attributes:
    def __init__(self, item: Item) -> None:
        self.item = item

    def parse_all_attributes(self, el_element: ET.Element):
        attributes: Dict[str, str] = el_element.attrib


class IDAttribute:

    attrib_type: BaseAttributeType = BaseAttributeType.ID

    def __init__(self, id_val: int):
        self.id: int = id_val

    def get_value(self) -> int:
        return self.id


class Tag(StrEnum):
    CONTROL = 'control'
    ON_FOCUS = 'onfocus'
    ON_CLICK = 'onclick'
    VISIBLE = 'visible'


class ElementKeywords(StrEnum):
    ACTION = 'action'
    ALT_LABEL = 'alt_label'
    BUTTON = 'button'
    DEFAULT_CONTROL = 'defaultcontrol'
    DIALOG = 'dialog'
    CONTROL = 'control'
    CONTROLS = 'controls'
    GROUP = 'group'
    ON_FOCUS = 'onfocus'
    ON_UNFOCUS = 'onunfocus'
    ON_CLICK = 'onclick'
    PAGE_CONTROL = 'pagecontrol'
    VISIBLE = 'visible'
    HINT_TEXT = 'hinttext'
    LABEL = 'label'
    LABEL2 = 'label2'
    INFO = 'info'
    INFO2 = 'info2'  # slider, pvr only
    MENU_CONTROL = 'menucontrol'
    NUMBER = 'number'
    SHOW_ONE_PAGE = 'showonepage'
    HAS_PATH = 'haspath'
    SCROLL_SUFFIX = 'scrollsuffix'
    SCROLL = 'scroll'
    SCROLL_TIME = 'scrolltime'  # Might care about scrolling of ui during TTS
    SELECTED = 'selected'
    ON_INFO = 'oninfo'
    ORIENTATION = 'orientation'
    DESCRIPTION = 'description'
    ENABLE = 'enable'
    TOPIC = 'topic'
    FALSE_MSG_ID = 'false_msg_id'
    WINDOW = 'window'
    WRAP_MULTILINE = 'wrapmultiline'


class Requires(Enum):
    TOPIC_UNITS = auto()


class Units(StrEnum):
    SCALE_DB = 'db'
    SCALE_PERCENT = '%'
    SCALE_NUMBER = 'number'
    TYPE_FLOAT = 'float'
    TYPE_INT = 'int'
