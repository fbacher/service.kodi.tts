# coding=utf-8

"""
<control type="sliderex" id="12">
      <description>My first settings slider control</description>
      <visible>true</visible>
      <info></info>
      <label>46</label>

Sliderex specific tags:

Tags that are relevent to accessibility:
** info 	Specifies the information that the slider controls. See here for more
information.
** label 	Either a numeric reference into strings.po (for localization), or a string that
will be shown on the left of the control.

Tags available to focusable controls

onfocus 	Specifies the built-in function that should be executed when the control is
focussed.
onunfocus 	Specifies the built-in function that should be executed when the control is
loses focus.

Tags available to all controls

id 	Specifies the control's id. The value this takes depends on the control type,
and the window that you are using the control on. There are special control id's that
must be present in each window. Any other controls that the skinner adds can be any id
they like. Any controls that the skinner specifies content needs not have an id unless
it's needed for animation purposes. For instance, most image and label controls don't
need an id if the skinner specifies they're content.

visible 	Specifies a condition as to when this control will be visible. Can be true,
false, or a condition. See Conditional Visibility for more information. Defaults to true.
animation 	Specifies the animation to be run when the control enters a particular
state. See Animating your skin for more information.


Tags not relavant to accessibility

sliderwidth 	Specifies the width of the slider portion of the slider control (ie
without the text value, if present). The texture image for the slider background will
be resized to fit into this width, and the nib textures will be resized by the same
amount.
sliderheight 	Specifies the height of the slider portion of the slider control (ie
without the text value, if present). The texture image for the slider background will
be resized to fit into this height, and the nib textures will be resized by the same
amount.
texturefocus 	Specifies the image file which should be displayed for the control when
it has focus. See here for additional information about textures.
texturenofocus 	Specifies the image file which should be displayed for the control when
it doesn't focus.
texturebg 	Specifies the image file which should be displayed in the background of the
slider portion of the control. Will be positioned so that the right edge is
<textoffsetx> away from the right edge of the <texturefocus> image, and centered
vertically.
textureslidernib 	Specifies the image file which should be displayed for the slider
nib.
textureslidernibfocus 	Specifies the image file which should be displayed for the
slider nib when it has focus.
font 	Font used for the controls label. From fonts.xml.
textcolor 	Color used for displaying the label. In AARRGGBB hex format, or a name from
the colour theme.
disabledcolor 	Color used for the label if the control is disabled. In AARRGGBB hex
format, or a name from the colour theme.
shadowcolor 	Specifies the color of the drop shadow on the text. In AARRGGBB hex
format, or a name from the colour theme.
textoffsetx 	Amount to offset the label from the left edge of the control.


Tags available to all controls
Tag(s) 	Definition

Tags relevant to Accessibility

description 	Only used to make things clear for the skinner. Not read by Kodi at all.
type 	The type of control.

id 	Specifies the control's id. The value this takes depends on the control type,
and the window that you are using the control on. There are special control id's that
must be present in each window. Any other controls that the skinner adds can be any id
they like. Any controls that the skinner specifies content needs not have an id unless
it's needed for animation purposes. For instance, most image and label controls don't
need an id if the skinner specifies they're content.

visible 	Specifies a condition as to when this control will be visible. Can be true,
false, or a condition. See Conditional Visibility for more information. Defaults to true.
animation 	Specifies the animation to be run when the control enters a particular
state. See Animating your skin for more information.

Tags not relevant to accessibility

left 	Specifies where the left edge of the control should be drawn, relative to it's
parent's left edge. If an "r" is included (eg 180r) then the measurement is taken from
the parent's right edge (in the left direction). This can be an absolute value or a %.

top 	Specifies where the top edge of the control should be drawn, relative to it's
parent's top edge. If an "r" is included (eg 180r) then the measurement is taken from
the parent's bottom edge (in the up direction). This can be an absolute value or a %.

right 	Specifies where the right edge of the control should be drawn. This can be an
absolute value or a %.

bottom 	Specifies where the bottom edge of the control should be drawn. This can be an
absolute value or a %.

centerleft 	Aligns the control horizontally at the given coordinate measured from the
left side of the parent control. This can be an absolute value or a %.

centerright 	Aligns the control horizontally at the given coordinate measured from
the right side of the parent control. This can be an absolute value or a %.

centertop 	Aligns the control vertically at the given coordinate measured from the top
side of the parent control. This can be an absolute value or a %.

centerbottom 	Aligns the control vertically at the given coordinate measured from the
bottom side of the parent control. This can be an absolute value or a %.

width 	Specifies the width that should be used to draw the control. You can use
<width>auto</width> for labels (in grouplists) and button/togglebutton controls.

height 	Specifies the height that should be used to draw the control.

camera 	Specifies the location (relative to the parent's coordinates) of the camera.
Useful for the 3D animations such as rotatey. Format is <camera x="20" y="30" />. 'r'
values and % are also supported.

depth 	Specifies the 3D stereoscopic depth of a control. possible values range from
-1.0 to 1.0, which brings control "to back" and "to front".

colordiffuse 	This specifies the color to be used for the texture basis. It's in hex
AARRGGBB format. If you define <colordiffuse>FFFF00FF</colordiffuse> (magenta),
the image will be given a magenta tint when rendered. Defaults to FFFFFFFF (no tint).
You can also specify this as a name from the colour theme.

Control-positioning.jpg
Tags available to focusable controls

These are the tags relevant to accessibility

onfocus 	Specifies the built-in function that should be executed when the control is
focussed.
onunfocus 	Specifies the built-in function that should be executed when the control is
loses focus.

Tags 	Definition
onup 	Specifies the <id> of the control that should be moved to when the user moves up
off this control. Can point to a control group (which remembers previous focused items).

ondown 	Specifies the <id> of the control that should be moved to when the user moves
down off this control. Can point to a control group (which remembers previous focused
items).

onleft 	Specifies the <id> of the control that should be moved to when the user moves
left off this control. Can point to a control group (which remembers previous focused
items).

onright 	Specifies the <id> of the control that should be moved to when the user
moves right off this control. Can point to a control group (which remembers previous
focused items).

onback 	Specifies the <id> of the control that should be focussed when the user presses
the back key. Can point to a control group (which remembers previous focused items).
oninfo 	Specifies the built-in function that should be executed when the user presses
the info key.

hitrect 	Specifies the location and size of the "focus area" of this control (
relative to the parent's coordinates) used by the mouse cursor. Format is <hitrect
x="20" y="30" w="50" h="10" />

hitrectcolor 	This adds the ability to visualize hitrects for controls. When visible
and there's a <hitrectcolor> tag, it will paint a colored rectangle over the actual
control. Colors can be specified in AARRGGBB format or a name from the color theme.
enable 	Specifies a condition as to when this control will be enabled. Can be true,
false, or a condition. See Conditional Visibility for more information. Defaults to true.

pulseonselect 	This specifies whether or not a button type will "pulse" when it has
focus. This is done by varying the alpha channel of the button. Defaults to true.

"""
