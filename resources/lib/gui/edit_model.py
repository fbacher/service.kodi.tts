# coding=utf-8

from typing import Callable, List

from common.logger import BasicLogger
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlElement, Item
from gui.edit_topic_model import EditTopicModel
from gui.element_parser import (ElementHandler)
from gui.no_topic_models import NoEditTopicModel
from gui.parser.parse_edit import ParseEdit
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class EditModel(BaseLabelModel):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.EDIT]

    def __init__(self, parent: BaseLabelModel, parsed_edit: ParseEdit,
                 windialog_state: WinDialogState | None = None) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
        super().__init__(window_model=parent.window_model,
                         parser=parsed_edit, windialog_state=windialog_state)
        self.parent = parent
        self.action_expr: str = ''
        self.description: str = ''
        self.enable_expr: str = ''
        self.control_hint_text: str
        self.hint_text_expr: str = ''
        self.info_expr: str = ''
        self.label_expr: str = ''
        self.on_focus_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.visible_expr: str = ''
        self.topic: EditTopicModel | None = None

        self.convert(parsed_edit)

    def convert(self, parsed_edit: ParseEdit) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_edit: A ParsEdit instance that
               needs to be converted to a EditModel
        :return:
        """
        clz = type(self)
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
            self.topic = EditTopicModel(self, parsed_edit.topic)
        else:
            self.topic = NoEditTopicModel(self)

        clz._logger.debug(f'# parsed children: {len(parsed_edit.get_children())}')

        for child in parsed_edit.children:
            child: BaseParser
            # clz._logger.debug(f'child: {child}')
            model_handler: Callable[[BaseModel, BaseParser, WinDialogState | None],
                                    BaseModel]
            # clz._logger.debug(f'About to create model from {type(child).item}')
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child, None)
            self.children.append(child_model)

    def __repr__(self) -> str:
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False) -> str:
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

        if include_children:
            for child in self.children:
                child: BaseParser
                results.append(str(child))

        return '\n'.join(results)
