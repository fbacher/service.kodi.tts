# coding=utf-8

from typing import Callable, List

from common.logger import BasicLogger
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlType, Item
from gui.element_parser import (BaseElementParser,
                                ElementHandler)
from gui.parse_group import ParseGroup
from gui.parse_scrollbar import ScrollbarParser
from gui.parse_topic import ParseTopic

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ScrollbarModel(BaseModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.SCROLL_BAR.name]

    def __init__(self, parent: BaseModel, parsed_scrollbar: ScrollbarParser) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(parent.window_model, parsed_scrollbar)

        self.orientation_expr: str = 'vertical'
        self.show_one_page: bool = parsed_scrollbar.show_one_page
        self.description: str = parsed_scrollbar.description
        self.visible_expr: str = parsed_scrollbar.visible_expr
        self.enable_expr: str = parsed_scrollbar.enable_expr
        self.hint_text_expr: str = parsed_scrollbar.hint_text_expr
        # self.info_expr: str =
        # self.on_click
        self.on_focus_expr: str = parsed_scrollbar.on_focus_expr
        # self.on_info_expr: str = ''
        self.on_unfocus_expr: str = parsed_scrollbar.on_unfocus_expr
        self.children: List[BaseModel] = []

        self.convert_children(parsed_scrollbar)

    def convert_children(self, parsed_scrollbar: ScrollbarParser) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_scrollbar: A ScrollbarParser instance that
               needs to be convertd to a ScrollbarModel
        :return:
        """
        clz = type(self)

        if parsed_scrollbar.topic is not None:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(ParseTopic.item)
            self.topic = model_handler(self, parsed_scrollbar.topic)

        clz._logger.debug(f'# parsed children: {len(parsed_scrollbar.get_children())}')
        parsers: List[BaseParser] = parsed_scrollbar.get_children()

        for parser in parsers:
            parser: BaseParser
            # clz._logger.debug(f'parser: {parser}')
            model_handler:  Callable[[BaseModel, BaseParser], BaseModel]
            # clz._logger.debug(f'About to create model from {parser.item}')
            model_handler = ElementHandler.get_model_handler(parser.item)
            child_model: BaseModel = model_handler(self, parser)
            self.children.append(child_model)

    def __repr__(self) -> str:
        clz = type(self)
        # Remove:  has_path, label, scroll, action
        # Verify removal: onfocus, onup, enable etc.

        if self.on_focus_expr != '':
            on_focus_expr: str = f'\n on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr != '':
            on_unfocus_expr: str = f'\n on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''

        description_str: str = ''
        if self.description != '':
            description_str = f'\n description: {self.description}'

        visible_expr_str : str = ''
        if self.visible_expr != '':
            visible_expr_str = f'\n visible: {self.visible_expr}'

        hint_text_expr_str: str = ''
        if self.hint_text_expr != '':
            hint_text_expr_str = '\n hint_text: {self.hint_text_expr}'

        show_one_page_str: str = ''
        if not self.show_one_page:
            show_one_page_str = f'\n show_one_page: {self.show_one_page}'

        visible_expr: str = ''
        if self.visible_expr != '':
            visible_expr = f'\n visible_expr: {self.visible_expr}'

        orientation_expr: str = ' orientation: vertical'
        if self.orientation_expr != '':
            orientaton_expr = f'\n orientation: {self.orientation_expr}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nScrollbarModel type: {self.control_type} '
                       f'id: {self.control_id}'
                       f'{show_one_page_str}'
                       f'{description_str}'
                       f'{hint_text_expr_str}'
                       f'{visible_expr_str}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'{orientation_expr}'
                       f'{topic_str}'
                       f' #children: {len(self.children)}{visible_expr}'
                       )
        results.append(result)

        for child in self.children:
            child: BaseModel
            results.append(str(child))

        return '\n'.join(results)
