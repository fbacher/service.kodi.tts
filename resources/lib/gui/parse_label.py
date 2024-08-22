# coding=utf-8

import xml.etree.ElementTree as ET
from typing import Callable, List, Tuple

from common.logger import BasicLogger
from gui import BaseParser
from gui.base_tags import (BaseAttributeType as BAT, control_elements, ControlType,
                           ElementKeywords as EK, Item)
from gui.element_parser import ElementHandler
from gui.parse_control import ParseControl
from gui.parse_topic import ParseTopic

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ParseLabel(ParseControl):

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
    item: Item = control_elements[ControlType.LABEL.name]
    label = BasicLogger = None

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__class__.__name__)

    def __init__(self, parent: BaseParser) -> None:
        super().__init__(parent)
        self.control_type = ControlType.LABEL
        self.topic: ParseTopic | None = None
        self.scroll: bool = False
        self.scroll_suffix: str = '|'
        self.scroll_speed: int = 60  # pixels per sec
        self.label_expr: str = ''
        self.info_expr: str = ''
        self.number_expr: str = ''
        self.has_path: bool = False
        self.hint_text_expr: str = ''
        self.wrap_multiline: bool = False
        self.description: str = ''
        self.visible_expr: str = ''
        self.label_for: str = ''

    @classmethod
    def get_instance(cls, parent: BaseParser,
                     el_label: ET.Element) -> ParseControl:
        self = ParseLabel(parent)
        self.parse_label(el_label)
        return self

    def parse_label(self, el_label: ET.Element) -> None:
        """
        Parse the 'label' control

        :param el_label:
        :return:
        """
        clz = type(self)


        """
         <control type="label">
                <label>$INFO[ListItem.Label]</label>
         </control>
    
            * info 	Specifies the information that should be presented. Kodi will 
            auto-fill in this
              info in place of the <label>. See here for more information.
            * number 	Specifies a number that should be presented. This is just here 
            to allow a
              skinner to use a number rather than a text label (as any number given to 
              <label> will
              be used to lookup in strings.po)
            * haspath 	Specifies whether or not this label is filled with a path. Long 
            paths are
              shortened by compressing the file path while keeping the actual filename 
              full length.
            * scrollsuffix 	Specifies the suffix used in scrolling labels. Defaults to 
            "¦".
        """

        control_id_str: str = ''

        if el_label.attrib.get('id') is not None:
            control_id: int = int(el_label.attrib.get('id'))
            self.control_id = control_id

        label_for_str: str = el_label.attrib.get(BAT.LABEL_FOR)
        if label_for_str is not None:
            self.label_for = label_for_str

        el_scroll_suffix: ET.Element = el_label.find(f'./{EK.SCROLL_SUFFIX}')
        if el_scroll_suffix is not None:
            scroll_suffix: str = el_scroll_suffix.text
            if scroll_suffix is None:
                clz._logger.debug(f'scrollsuffix value not specified. Ignored')
            self.scroll_suffix = scroll_suffix

        tags_to_parse: Tuple[str, ...] = (EK.TOPIC, EK.LABEL, EK.SCROLL, EK.NUMBER,
                                          EK.HAS_PATH, EK.INFO, EK.ACTION,
                                          EK.ORIENTATION, EK.HINT_TEXT,
                                          EK.DESCRIPTION)
        orphans: List[ET.Element] = []
        elements: [ET.Element] = el_label.findall(f'./*')
        element: ET.Element
        for element in elements:
            #  clz._logger.debug(f'element.tag: {element.tag} text: {element.text}')
            if element.tag in tags_to_parse:
                # clz._logger.debug(f'element_tag: {element.tag}')
                key: str = element.tag
                control_type: ControlType = clz.get_control_type(element)
                if control_type is not None:
                    key = control_type.name
                item: Item = control_elements[key]
                # Values copied to self
                handler: Callable[[BaseParser, ET.Element], str | BaseParser]
                handler = ElementHandler.get_handler(item.key)
                parsed_instance: BaseParser = handler(self, element)
                if parsed_instance is not None:
                    if control_type is not None:
                        self.children.append(parsed_instance)
                    if key == EK.TOPIC:
                        self.topic = parsed_instance
            # else:
            #     if element.tag not in ('top', 'left', 'width', 'height', 'bottom'):
            #         clz._logger.debug(f'ParseLabel ignored element: {element.tag}')

    def __repr__(self) -> str:
        clz = type(self)
        control_id: str = ''
        if self.control_id != -1:
            control_id = f' id: {self.control_id}'

        label_for_str: str = ''
        if self.label_for != '':
            label_for_str = f'\n label_for: {self.label_for}'

        visible_expr: str = ''
        if self.visible_expr != '':
            visible_expr = f'\n visible_expr: {self.visible_expr}'

        label_expr: str = ''
        if self.label_expr != '':
            label_expr = f'\n label_expr: {self.label_expr}'
        number_expr: str = ''
        if self.number_expr:
            number_expr = f'\n number_expr: {number_expr}'

        has_path_str: str = ''
        if self.has_path:
            has_path_str = f'\n has_path: {self.has_path}'

        hint_text_str: str = ''
        if self.hint_text_expr != '':
            hint_text_str = f'\n hint_text: {self.hint_text_expr}'

        scroll_suffix: str = ''
        # if self.scroll_suffix: str = '|'  # appended to scrolled lines (?)
        info_expr: str = ''
        if len(self.info_expr) > 0:
            info_expr = f'\n info_expr: {self.info_expr}'

        if len(self.visible_expr) > 0:
            visible_expr: str = f'\n visible: {self.visible_expr}'

        topic_str: str = ''
        if self.topic != '':
            topic_str = f'\n  Topic:{self.topic}'

        results: List[str] = []
        result: str = (f'\nParseLabel type: {self.control_type}'
                       f'{control_id}{label_for_str}'
                       f'{visible_expr}'
                       f'{number_expr}{has_path_str} '
                       f'{hint_text_str}'
                       f'{info_expr}{topic_str}'
                       f'\n #children: {len(self.children)}{label_expr}')

        results.append(result)

        for child in self.get_children():
            child: BaseParser
            results.append(str(child))

        results.append(f'END ParseLabel')
        return '\n'.join(results)


ElementHandler.add_handler(ParseLabel.item.key, ParseLabel.get_instance)
