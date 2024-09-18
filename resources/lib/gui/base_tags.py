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

import xbmcgui

from common.logger import BasicLogger
import xml.etree.ElementTree as ET
from enum import auto, Enum
from typing import Callable, ForwardRef, List, Tuple, Union

from common.logger import BasicLogger

module_logger = BasicLogger.get_logger(__name__)

AttribInfo = namedtuple('attrib_info', ['attrib_name', 'attrib_value',
                                         'status'])


class BaseAttributeType(StrEnum):
    ID = 'id'
    CONDITION = 'condition'
    CONTROL_TYPE = 'type'
    SLIDER = 'slider'
    LABEL = 'label'
    LABEL_ID = 'label_id'
    SET_FOCUS = 'setfocus'
    TYPE = 'type'
    # ALT_TYPE specifies the control type to use that may be more clear
    # than the Kodi control names. TODO: create type listing suggested
    # alt-types.  If a string is specified, then it is for a pre-defined
    # alt-type. If an int, then it is a message id.
    ALT_TYPE = 'alt_type'
    # HEADING_LABEL specifies a label used for the heading of this control
    # If an integer, then it is a message_id
    # If text it is either an $INFOLABEL or a topic_name where it's
    # HEADING_LABEL is used instead
    HEADING_LABEL = 'heading_label'
    # HEADING_NEXT specifies an additional topic containing a sub-heading
    # to voice
    HEADING_NEXT = 'heading_next'
    # LABEL_FOR marks a control as being the label for another control
    # Typically the control needing this label also has a LABELED_BY
    # reference back to this topic
    LABEL_FOR = 'label_for'
    # See LABEL_FOR
    LABELED_BY = 'labeled_by'
    # ALT_LABEL specifies an alternate label to use that may be more
    # accessible. ALT_LABEL may be an int, which is interpreted as a
    # message id. (To use another control as a label, use LABELED_BY
    # instead.) ALT_LABEL may be a string, in which case it is
    # interpreted as an INFO_LABEL or similar.
    ALT_LABEL = 'alt_label'
    TOPIC = 'topic'
    # NAME is the id to use for this Topic
    NAME = 'name'
    # HINT_TEXT supplies additional text that may clarify what the control
    # is for, or perhaps your options, etc. Format is the same as ALT_LABEL
    HINT_TEXT = 'hint_text'
    # FLOWS_TO indicates that the result of this control (label or value)
    # is voiced by another control. FLOWS_TO specifies the int id or topic name
    # of the other control. Typically, the receiving control has a FLOWS_FROM
    # referencing back to this topic or control with the FLOWS_TO
    FLOWS_TO = 'flows_to'
    # See FLOWS_TO, above
    FLOWS_FROM = 'flows_from'
    # For binary controls: RadioButton. By default, 'Enabled' is
    # substituted for '(*)' from the ListItem value of the control
    TRUE_MSG_ID = 'true_msg_id'
    # For binary controls: RadioButton. By default, 'Disabled' is
    # substituted for '()' from the ListItem value of the control
    FALSE_MSG_ID = 'false_msg_id'
    # READ_NEXT is typically used for non-focusable items. It indicates that
    # more than one thing needs to be read for, say, a window header.
    READ_NEXT = 'read_next'
    # INNER/OUTER are to traverse the logically
    # superior/inferior topic (window header is
    # superior to all, categories, etc. are in
    # between and detail values are most inferior)
    INNER_TOPIC = 'inner_topic'
    OUTER_TOPIC = 'outer_topic'
    # LEFT/RIGHT are for topics to the physical left/right.
    # similar for UP/DOWN.
    TOPIC_LEFT = 'topic_left'
    TOPIC_RIGHT = 'topic_right'
    TOPIC_UP = 'topic_up'
    TOPIC_DOWN = 'topic_down'
    RANK = 'rank'
    # TOPIC_TYPE specifies how this topic is used.
    # It can be one of 'heading'
    TOPIC_TYPE = 'topic_type'   # Consider removing
    # UNITS indicates that the value needs to be formatted to the
    # given units. The value of units needs to be one of the
    # predefined units (TODO: Add the units)
    UNITS = 'units'  # complex string value


class TopicElement(StrEnum):
        # ALT_TYPE specifies the control type to use that may be more clear
        # than the Kodi control names. TODO: create type listing suggested
        # alt-types.  If a string is specified, then it is for a pre-defined
        # alt-type. If an int, then it is a message id.
    ALT_TYPE = 'alt_type'
        # ALT_TYPE TBD
    ALT_INFO = 'alt_info'
        # CONTAINER_TOPIC specifies the topic whis is the container (list-like)
        # topic of this topic.
    CONTAINER_TOPIC = 'container_topic'
        # HEADING_LABEL specifies a label used for the heading of this control
        # If an integer, then it is a message_id
        # If text it is an $INFOLABEL
    HEADING_LABEL = 'heading_label'
        # HEADING_LABELED_BY specifies another topic id or control_id to
        # get the label from.
    HEADING_LABELED_BY = 'heading_labeled_by'
        # HEADING_NEXT specifies an additional topic containing a sub-heading
        # to voice
    HEADING_NEXT = 'heading_next'
        # LABEL_FOR marks a control as being the label for another control
        # Typically the control needing this label also has a LABELED_BY
        # reference back to this topic
    LABEL_FOR = 'label_for'
        # See LABEL_FOR
    LABELED_BY = 'labeled_by'
        # ALT_LABEL specifies an alternate label to use that may be more
        # accessible. ALT_LABEL may be an int, which is interpreted as a
        # message id. (To use another control as a label, use LABELED_BY
        # instead.) ALT_LABEL may be a string, in which case it is
        # interpreted as an INFO_LABEL or similar.
    ALT_LABEL = 'alt_label'
    TOPIC = 'topic'
        # NAME is the id to use for this Topic
    NAME = 'name'
        # HINT_TEXT supplies additional text that may clarify what the control
        # is for, or perhaps your options, etc. Format is the same as ALT_LABEL
    HINT_TEXT = 'hint_text'
        # FLOWS_TO indicates that the result of this control (label or value)
        # is voiced by another control. FLOWS_TO specifies the int id or topic name
        # of the other control. Typically, the receiving control has a FLOWS_FROM
        # referencing back to this topic or control with the FLOWS_TO
    FLOWS_TO = 'flows_to'
        # See FLOWS_TO, above
    FLOWS_FROM = 'flows_from'
        # For binary controls: RadioButton. By default, 'Enabled' is
        # substituted for '(*)' from the ListItem value of the control
    TRUE_MSG_ID = 'true_msg_id'
        # For binary controls: RadioButton. By default, 'Disabled' is
        # substituted for '()' from the ListItem value of the control
    FALSE_MSG_ID = 'false_msg_id'
        # READ_NEXT is typically used for non-focusable items. It indicates that
        # more than one thing needs to be read for, say, a window header.
    READ_NEXT = 'read_next'
        # INNER/OUTER are to traverse the logically
        # superior/inferior topic (window header is
        # superior to all, categories, etc. are in
        # between and detail values are most inferior)
    INNER_TOPIC = 'inner_topic'
    OUTER_TOPIC = 'outer_topic'
        # References a topic containg heading information to voice for this control
    TOPIC_HEADING = 'topic_heading'
        # LEFT/RIGHT are for topics to the physical left/right.
        # similar for UP/DOWN.
    TOPIC_LEFT = 'topic_left'
    TOPIC_RIGHT = 'topic_right'
    TOPIC_UP = 'topic_up'
    TOPIC_DOWN = 'topic_down'
    RANK = 'rank'
        # TOPIC_TYPE specifies how this topic is used.
        # It can be one of 'heading'
    TOPIC_TYPE = 'topic_type'
        # UNITS indicates that the value needs to be formatted to the
        # given units. The value of units needs to be one of the
        # form:  scale=db, type=float, step=.1, min=-12, max=12.
        # The value will appear in the form <scaled_value><scale_suffix> and
        # conforming to the range number-type and step specified.
        #  Example: 3.1db  Instead of 3.09db
    UNITS = 'units'
        # Format the value (after formatting with UNITS, above) to add text, etc.
    VALUE_FORMAT = 'value_format'
        #  Get the value from a control/listitem or from TTS <control>module
    VALUE_FROM = 'value_from'

class TopicKeyword(StrEnum):
    UNIT = 'unit'
    TYPE = 'type'
    DECIMAL_DIGITS = 'decimal_digits'

class UnitsType(StrEnum):
    INT = 'int'
    FLOAT = 'float'

class TopicType(StrEnum):
    HEADING = 'heading'
    VALUE = 'value'
    DEFAULT = 'default'
    #  NONE causes no voicing of the control. Default value for
    #  control_type "group".
    NONE = 'none'

class TopicAltType(StrEnum):
    DIALOG = 'dialog'
    WINDOW = 'window'

class ValueFromType(StrEnum):
    INTERNAL = 'internal'
    NONE = 'none'


class ValueUnits:

    def __init__(self, units_unit: str, unit_type: UnitsType,
                 units_digits: int) -> None:
        clz = ValueUnits
        # ex: units unit="db" type="float" decimal_digits="1
        self.units: str = units_unit
        self.unit_type: UnitsType = unit_type
        self.units_digits: int = units_digits
        return

    def format_value(self, value: float | int) -> str:
        clz = ValueUnits
        result: str = ''
        try:

            if self.unit_type == UnitsType.INT:
                # Converts 1234 with units of 'db'  to '1234db'
                result = f'{int(value)}{self.units}'
            else:
                # Float
                result: str = f'{value:.{self.units_digits}f}{self.units}'
        except Exception:
            clz._logger.exception('')
        return result

    def __repr__(self) -> str:
        result: str = (f'UNITS:'
                       f'\n  units: {self.units} '
                       f'\n  unit_type: {self.unit_type} '
                       f'\n  units_digits: {self.units_digits}'
                       f'\nEND UNITS')
        return result


class ControlElement(StrEnum):
    BUTTON = 'button'
    COLOR_BUTTON = 'colorbutton'
    CONTROLS = 'controls'
    CONTROL = 'control'
    DIALOG = 'dialog'
    EDIT = 'edit'
    EPG_GRID = 'epggrid'
    FADE_LABEL = 'fadelabel'
    FIXED_LIST = 'fixedlist'
    FOCUSED_LAYOUT = 'focusedlayout'
    GAME_CONTROLLER = 'gamecontroller'
    GAME_CONTROLLER_LIST = 'gamecontrollerlist'
    GAME_WINDOW = 'gamewindow'
    GROUP = 'group'
    GROUP_LIST = 'grouplist'
    IMAGE = 'image'
    ITEM_LAYOUT = 'itemlayout'
    # To distinguish from Label attribute or elements within a Control
    LABEL_CONTROL = 'label'
    LIST = 'list'
    MENU_CONTROL = 'menucontrol'
    MOVER = 'mover'
    MULTI_IMAGE = 'multiimage'
    PANEL = 'panel'
    PROGRESS = 'progress'
    RADIO_BUTTON = 'radiobutton'
    RANGES = 'ranges'
    RENDER_ADDON = 'renderaddon'
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

    @classmethod
    def parse_control_type(cls, ctrl_type: str) -> ForwardRef('ControlElement'):
        """
           Converts a control's type (i.e. the parsed control's "type" attribute)
           into ControlElement
           :param ctrl_type:
           :return: the appropriate ControlType for the given ctrl_type
           :raise ValueError: on error
           """
        ctrl_name: str = ctrl.__class__.__name__
        module_logger.debug(f'ctrl_name: {ctrl_name}')
        ctrl_element: ControlElement = None
        try:
            ctrl_element = ControlElement(ctrl_type)
        except ValueError:
            raise ValueErro('Invalid ctrl_type: {ctrl_type}')
        return ctrl_element

    @classmethod
    def parse_kodi_control_type(cls,
                                kodi_control: xbmcgui.Control) -> ForwardRef('ControlElement'):
        """
        Similar to parse_control_type, except the control type comes
        directly from the class name of xbmc.getControl(). Used when
        there is no other access to the control name.

        :param kodi_control: xbmcgui.Control to derive the control type from
        :return: ControlElement for the given control
        :raise ValueError:
             if control type can not be determined.
        """
        ctrl_name: str = ctrl.__class__.__name__
        module_logger.debug(f'ctrl_name: {ctrl_name}')
        return ControlElement.parse_control_type(ctrl_name)


class ElementType(StrEnum):
    CONTROL = 'control'
    NON_CONTROL = 'noncontrol'
    BOTH = 'both'
    ATTRIB = 'attrib'
    WINDOW = 'window'


class MessageType(Enum):
    YES = 32173
    NO = 32174
    ENABLED = 32338
    DISABLED = 32339
    ON = 32818
    OFF = 32819
    TRUE = 32820
    FALSE = 32821
    FAST = 32822
    SLOW = 32823


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
        keyword: str | StrEnum = keyword
        if isinstance(keyword, StrEnum):
            enum_key: StrEnum = keyword
            keyword = enum_key.name
            # module_logger.debug(f'key is enum: {enum_key.name} {enum_key} '
            #                   f'keyword: {keyword}')
        else:
            pass
            # module_logger.debug(f'key is str: {keyword} type: {type(keyword)}')

        self.keyword: str = keyword
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

    def __getitem__(self, key: str | StrEnum) -> Item:
        if isinstance(key, StrEnum):
            key = key.name
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
    AUTO_SCROLL = 'autoscroll'
    BUTTON = 'button'
    CONTENT = 'content'
    CONTROL = 'control'
    CONTROLS = 'controls'
    DESCRIPTION = 'description'
    DEFAULT_CONTROL = 'defaultcontrol'
    DIALOG = 'dialog'
    ENABLE = 'enable'
    #  FALSE_MSG_ID = 'false_msg_id'
    FOCUSED_LAYOUT = 'focusedlayout'
    GROUP = 'group'
    HAS_PATH = 'haspath'
    HINT_TEXT = 'hinttext'
    INFO = 'info'
    INFO2 = 'info2'  # slider, pvr only
    ITEM_LAYOUT = 'itemlayout'
    LABEL = 'label'
    LABEL2 = 'label2'
    MENU_CONTROL = 'menucontrol'
    NUMBER = 'number'
    ON_FOCUS = 'onfocus'
    ON_CLICK = 'onclick'
    ON_INFO = 'oninfo'
    ON_UNFOCUS = 'onunfocus'
    ORIENTATION = 'orientation'
    PAGE_CONTROL = 'pagecontrol'
    PRELOAD_ITEMS = 'preloaditems'
    SHOW_ONE_PAGE = 'showonepage'
    SCROLL = 'scroll'
    SCROLL_LIST = 'scrollist'
    SCROLL_SUFFIX = 'scrollsuffix'
    SCROLL_TIME = 'scrolltime'  # Might care about scrolling of ui during TTS
    SELECTED = 'selected'
    TOPIC = 'topic'
    VIEW_TYPE = 'viewtype'
    VISIBLE = 'visible'
    WINDOW = 'window'
    WRAP_MULTILINE = 'wrapmultiline'


class IgnoredKeywords(StrEnum):
    TEXTURE_FOCUS = 'texturefocus'
    TEXTURE_NO_FOCUS ='texturenofocus'
    FOCUSED_COLOR ='focusedcolor'
    TEXT_COLOR ='textcolor'
    DISABLED_COLOR ='disabledcolor'
    INVALID_COLOR ='invalidcolor'
    SHADOW_COLOR ='shadowcolor'
    # Position related
    POS_X ='posx'
    POS_Y ='posy'
    ALIGN ='align'
    ALIGN_Y ='aligny'
    TEXT_OFFSET_X ='textoffsetx'
    TEXT_OFFSET_Y ='textoffsety'
    TEXT_WIDTH ='textwidth'
    # Action related
    ON_CLICK ='onclick'
    # Misc
    FONT ='font'
    COLOR_DIFFUSE ='colordiffuse'
    # Position items
    WIDTH ='width'
    HEIGHT ='height'
    PULSE_ON_SELECT = 'pulseonselect'
    ON_UP = 'onup'
    ON_DOWN = 'ondown'
    ON_LEFT = 'onleft'
    ON_RIGHT = 'onright'
    COORDINATES = 'coordinates'
    TEXTURE = 'texture'

control_attributes_with_values: List[str]
control_attributes_with_values = ['id', 'type',
                                  BaseAttributeType.ALT_TYPE,
                                  'label_for'
                                  'labeled_by', 'flows_to', 'flows_from']

control_elements: Items = Items()

control_items_list: List[Item] = [
    Item(TopicElement.ALT_LABEL, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.ALT_TYPE, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.ALT_INFO, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.CONTAINER_TOPIC, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.LABEL_FOR, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.LABELED_BY, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.NAME, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.HINT_TEXT, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.FLOWS_TO, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.FLOWS_FROM, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.TRUE_MSG_ID, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.FALSE_MSG_ID, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.READ_NEXT, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.TOPIC_HEADING, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.HEADING_LABEL, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.HEADING_LABELED_BY, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.HEADING_NEXT, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.INNER_TOPIC, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.OUTER_TOPIC, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.TOPIC_LEFT, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.TOPIC_RIGHT, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.RANK, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.TOPIC_TYPE, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.UNITS, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.VALUE_FROM, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.VALUE_FORMAT, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.TOPIC_DOWN, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.TOPIC_UP, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(TopicElement.TOPIC, is_control=False, ignore=False,
         element_type=ElementType.NON_CONTROL),

    Item(keyword=ControlElement.CONTROL, is_control=True,
         element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(keyword=ControlElement.CONTROLS, is_control=True,
         element_type=ElementType.CONTROL,
         attributes_with_values=['id', 'type']),
    Item(keyword=ControlElement.COLOR_BUTTON, is_control=True, ignore=True,
         element_type=ElementType.CONTROL),
    Item(keyword=ElementKeywords.DEFAULT_CONTROL, is_control=False, ignore=False,
         element_type=ElementType.NON_CONTROL),
    Item(keyword=ElementKeywords.DIALOG, is_control=False, ignore=False,
         attributes_with_values=['type', 'tts', 'label'],
         element_type=ElementType.WINDOW),
    Item(ControlElement.BUTTON, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlElement.RENDER_ADDON, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlElement.SCROLL_BAR, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlElement.EPG_GRID, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlElement.EDIT, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlElement.FADE_LABEL, is_control=True, ignore=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlElement.FIXED_LIST, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlElement.GAME_WINDOW, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlElement.FOCUSED_LAYOUT, is_control=False,
         element_type=ElementType.NON_CONTROL),
    Item(ControlElement.GAME_CONTROLLER, is_control=True,
         element_type=ElementType.CONTROL),
    Item(ControlElement.GAME_CONTROLLER_LIST, is_control=True,
         element_type=ElementType.CONTROL),
    Item(ControlElement.GROUP, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values, attributes=None,
         focusable=True),
    Item(ControlElement.GROUP_LIST, is_control=True,
         element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ElementKeywords.HAS_PATH, is_control=False,
         element_type=ElementType.NON_CONTROL),
    Item(ControlElement.IMAGE, is_control=True, focusable=False,
         element_type=ElementType.CONTROL, ignore=True),
    Item(ControlElement.LABEL_CONTROL, is_control=True, focusable=False,
         element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ElementKeywords.LABEL, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ElementKeywords.LABEL2, is_control=False, focusable=False,
         element_type=ElementType.NON_CONTROL),
    Item(ControlElement.ITEM_LAYOUT, is_control=False,
         element_type=ElementType.NON_CONTROL),
    Item(ControlElement.LIST, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlElement.MENU_CONTROL, is_control=True, element_type=ElementType.NON_CONTROL),
    Item(ControlElement.MOVER, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlElement.MULTI_IMAGE, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ElementKeywords.NUMBER, is_control=False, focusable=True,
         element_type=ElementType.NON_CONTROL),
    Item(ControlElement.PANEL, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ElementKeywords.PAGE_CONTROL, is_control=False, element_type=ElementType.NON_CONTROL),
    Item(ControlElement.PROGRESS, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlElement.RSS, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlElement.RANGES, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlElement.RADIO_BUTTON, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlElement.RESIZE, is_control=True, element_type=ElementType.CONTROL),
    Item(ElementKeywords.SELECTED, is_control=False, element_type=ElementType.NON_CONTROL),
    Item(ElementKeywords.SCROLL_LIST, is_control=False, element_type=ElementType.NON_CONTROL),
    Item(ElementKeywords.SCROLL_TIME, is_control=False, element_type=ElementType.NON_CONTROL),
    Item(ElementKeywords.SCROLL, is_control=False, element_type=ElementType.NON_CONTROL),
    Item(ElementKeywords.SHOW_ONE_PAGE, is_control=False, element_type=ElementType.NON_CONTROL),
    Item(ControlElement.SLIDER_EX, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlElement.SLIDER, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlElement.SPIN_CONTROL, is_control=True, element_type=ElementType.CONTROL),
    Item(ControlElement.SPIN_CONTROL_EX, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlElement.TEXT_BOX, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlElement.TOGGLE_BUTTON, is_control=True, element_type=ElementType.CONTROL,
         attributes_with_values=control_attributes_with_values),
    Item(ControlElement.VIDEO_WINDOW, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlElement.VISUALISATION, is_control=True, focusable=False,
         element_type=ElementType.CONTROL),
    Item(ControlElement.WINDOW, is_control=False,
         attributes_with_values=['type', 'tts', 'label'],
         element_type=ElementType.WINDOW),
    Item(ControlElement.WRAP_LIST, is_control=True, element_type=ElementType.CONTROL),

    Item('angle', ignore=True),

    # The only ones we care about
    Item(ElementKeywords.ACTION),
    Item(ElementKeywords.ENABLE),
    Item(ElementKeywords.ORIENTATION),
    Item(ElementKeywords.WRAP_MULTILINE),
    Item(ElementKeywords.DESCRIPTION),
    Item(ElementKeywords.INFO),
    Item(ElementKeywords.VISIBLE),

    # Color related
    Item(IgnoredKeywords.TEXTURE_FOCUS, attributes_with_values='colordiffuse', ignore=True),
    Item(IgnoredKeywords.TEXTURE_NO_FOCUS, attributes_with_values='colordiffuse', ignore=True),
    Item(IgnoredKeywords.FOCUSED_COLOR, ignore=True),
    Item(IgnoredKeywords.TEXT_COLOR, ignore=True),
    Item(IgnoredKeywords.DISABLED_COLOR, ignore=True),
    Item(IgnoredKeywords.INVALID_COLOR, ignore=True),
    Item(IgnoredKeywords.SHADOW_COLOR, ignore=True),
    # Position related
    Item(IgnoredKeywords.POS_X, ignore=True),
    Item(IgnoredKeywords.POS_Y, ignore=True),
    Item(IgnoredKeywords.ALIGN, ignore=True),
    Item(IgnoredKeywords.ALIGN_Y, ignore=True),
    Item(IgnoredKeywords.TEXT_OFFSET_X, ignore=True),
    Item(IgnoredKeywords.TEXT_OFFSET_Y, ignore=True),
    Item(IgnoredKeywords.TEXT_WIDTH, ignore=True),
    # Action related
    Item(IgnoredKeywords.ON_CLICK, ignore=True),
    # Misc
    Item(IgnoredKeywords.FONT, ignore=True),
    Item(IgnoredKeywords.COLOR_DIFFUSE, ignore=True),
    # Position items
    Item(IgnoredKeywords.WIDTH, ignore=True),
    Item(IgnoredKeywords.HEIGHT, ignore=True),
    #    ]

    # default_items: Items = Items()
    # default_items.add_all(tmp)

    # focusable_control_default_items: List[Item] = [
    # The only ones we care about
    Item(ElementKeywords.ON_FOCUS),
    Item(ElementKeywords.ON_UNFOCUS),
    # Who cares?
    Item(IgnoredKeywords.PULSE_ON_SELECT, ignore=True),
    Item(IgnoredKeywords.ON_UP, ignore=True),
    Item(IgnoredKeywords.ON_DOWN, ignore=True),
    Item(IgnoredKeywords.ON_LEFT, ignore=True),
    Item(IgnoredKeywords.ON_RIGHT, ignore=True),
    Item(IgnoredKeywords.COORDINATES, ignore=True),
    Item(IgnoredKeywords.TEXTURE, ignore=True)
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

class Requires(Enum):
    TOPIC_UNITS = auto()


class Units(StrEnum):
    SCALE_DB = 'db'
    SCALE_PERCENT = '%'
    SCALE_NUMBER = 'number'
