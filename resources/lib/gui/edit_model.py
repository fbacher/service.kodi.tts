# coding=utf-8

from typing import Callable, ForwardRef, List, Union

from common.logger import BasicLogger
from common.phrases import PhraseList
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlType, Item
from gui.element_parser import (BaseElementParser, ElementHandler)
from gui.parse_edit import ParseEdit
from gui.parse_topic import ParseTopic
from gui.topic_model import TopicModel

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class EditModel(BaseLabelModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.EDIT.name]

    def __init__(self, parent: BaseLabelModel, parsed_edit: ParseEdit) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(window_model=parent.window_model, parser=parsed_edit)
        self.parent = parent
        self.action_expr: str = ''
        self.description: str = ''
        self.enable_expr: str = ''
        self.hint_text_expr: str = ''
        self.info_expr: str = ''
        self.label_expr: str = ''
        self.on_focus_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.visible_expr: str = ''
        self.children: List[BaseModel] = []

        self.previous_heading: PhraseList = PhraseList()

        self.convert(parsed_edit)

    def convert(self, parsed_edit: ParseEdit) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_edit: A ParsEdit instance that
               needs to be converted to a EditModel
        :return:
        """
        clz = type(self)
        self.control_type = parsed_edit.control_type
        self.control_id = parsed_edit.control_id
        self.description = parsed_edit.description
        self.enable_expr = parsed_edit.enable_expr
        self.label_expr = parsed_edit.label_expr
        # self.on_click
        self.on_focus_expr = parsed_edit.on_focus_expr
        self.on_unfocus_expr = parsed_edit.on_unfocus_expr
        self.visible_expr = parsed_edit.visible_expr
        self.hint_text_expr = parsed_edit.hint_text_expr
        self.action_expr = parsed_edit.action_expr
        self.info_expr = parsed_edit.info_expr

        if parsed_edit.topic is not None:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(ParseTopic.item)
            self.topic = model_handler(self, parsed_edit.topic)

        clz._logger.debug(f'# parsed children: {len(parsed_edit.get_children())}')

        for child in parsed_edit.children:
            child: BaseParser
            # clz._logger.debug(f'child: {child}')
            model_handler:  Callable[[BaseModel, BaseParser], BaseModel]
            # clz._logger.debug(f'About to create model from {type(child).item}')
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
            self.children.append(child_model)

    def clear_history(self) -> None:
        self.previous_heading.clear()

    def __repr__(self) -> str:
        clz = type(self)
        if self.on_focus_expr != '':
            on_focus_expr: str = f'\n on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr != '':
            on_unfocus_expr: str = f'\n on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''
        visible_expr: str = ''
        if self.visible_expr != '':
            visible_expr = f'\n  visible_expr: {self.visible_expr}'

        description_str: str = ''
        if self.description != '':
            description_str = f'\n description: {self.description}'

        self.action_expr: str = ''

        action_expr_str: str = ''
        if self.action_expr != '':
            action_expr_str = f'\n action: {self.action_expr}'

        enable_expr_str: str = ''
        if self.enable_expr != '':
            enable_expr_str = f'\n enable: {self.enable_expr}'

        hint_text_expr_str: str = ''
        if self.hint_text_expr != '':
            hint_text_expr_str = f'\n hint_text: {self.hint_text_expr}'

        info_expr_str: str = ''
        if self.info_expr != '':
            info_expr_str = f'\n info: {self.info_expr}'

        label_expr_str: str = ''
        if self.label_expr != '':
            label_expr_str = f'\n label: {self.label_expr}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nParseEdit type: {self.control_type} '
                       f'id: {self.control_id}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'{visible_expr}{description_str}'
                       f'{description_str}'
                       f'{enable_expr_str}'
                       f'{label_expr_str}'
                       f'{hint_text_expr_str}'
                       f'{info_expr_str}'
                       f'{action_expr_str}'
                       f'{visible_expr}'
                       f'{topic_str}'
                       f'\n #children: {len(self.children)}'
                       )
        results.append(result)

        for child in self.children:
            child: BaseParser
            results.append(str(child))

        return '\n'.join(results)