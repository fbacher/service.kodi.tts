# coding=utf-8
from typing import Tuple

import xbmc

from gui.base_control import BaseControl

"""
Tag 	Description

* scroll 	When true, the text will scroll if longer than the label's <width>. If 
  false, the text will be truncated. Defaults to false.
* label 	Specifies the text which should be drawn. You should specify an entry from 
  the strings.po here (either the Kodi strings.po or your skin's strings.po file), 
  however you may also hardcode a piece of text also if you wish, though of course it 
  will not be localisable. You can use the full label formatting syntax and you may also 
  specify more than one piece of information here by using the $INFO and $LOCALIZE 
  formats.
* info 	Specifies the information that should be presented. Kodi will auto-fill in this 
  info in place of the <label>. See here for more information.
* number 	Specifies a number that should be presented. This is just here to allow a 
  skinner to use a number rather than a text label (as any number given to <label> will 
  be used to lookup in strings.po)
* haspath 	Specifies whether or not this label is filled with a path. Long paths are 
  shortened by compressing the file path while keeping the actual filename full length.
* scrollsuffix 	Specifies the suffix used in scrolling labels. Defaults to "¦".

These don't appear to be useful for accessibility

align 	Can be left, right, or center. Aligns the text within the given label <width>. 
Defaults to left
aligny 	Can be top or center. Aligns the text within its given label <height>. Defaults 
to top
angle 	The angle the text should be rendered at, in degrees. A value of 0 is horizontal.
font 	Specifies the font to use from the font.xml file.
textcolor 	Specifies the color the text should be, in hex AARRGGBB format, or a name 
from the colour theme.
shadowcolor 	Specifies the color of the drop shadow on the text, in AARRGGBB format, 
or a name from the colour theme.
wrapmultiline 	If true, any text that doesn't fit on one line will be wrapped onto 
multiple lines.
scrollspeed 	Scroll speed of text in pixels per second. Defaults to 60.
 
"""


class Label(BaseControl):

    def __init__(self, win_dialog_id: int, label: str = None, info: str = None,
                 is_number: bool = False, has_path: bool = False,
                 scroll_suffix: str = None,
                 id_val: int = None, visible: bool = False):
        super().__init__(win_dialog_id=win_dialog_id, id_val=id_val, visible=visible)
        self.label: str = label
        self.info: str = info
        self.is_number: int = is_number
        self.has_path: bool = has_path
        self.scroll_sufix: str = scroll_suffix

    def get_label(self) -> Tuple[str, str]:
        if self.label is None:
            return 'Label not set'
        text: str = xbmc.getInfoLabel('System.CurrentControl')  # Not if this doesn't have focus

    def set_label(self, label: str):
        self.label = label

    def set_parent(self, parent: BaseControl):
        super().set_parent(parent)
