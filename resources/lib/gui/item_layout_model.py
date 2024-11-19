# coding=utf-8

from typing import Callable, List, Tuple

from common.logger import BasicLogger
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import (control_elements, ControlElement, Item)
from gui.element_parser import (ElementHandler)
from gui.item_layout_topic_model import ItemLayoutTopicModel
from gui.label_model import LabelModel
from gui.no_topic_models import NoItemLayoutTopicModel
from gui.parser.parse_item_layout import ParseItemLayout
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class ItemLayoutModel(BaseModel):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.ITEM_LAYOUT]

    def __init__(self, parent: BaseModel, parsed_item_layout: ParseItemLayout,
                 windialog_state: WinDialogState | None = None) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
        super().__init__(window_model=parent.window_model, parser=parsed_item_layout,
                         windialog_state=windialog_state)
        self.parent: BaseModel = parent
        self.broken: bool = False
        self.condition_expr: str = ''
        self.description: str = ''
        self.convert(parsed_item_layout)

    def convert(self, parsed_item_layout: ParseItemLayout) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_item_layout: A ParseItemLayout instance that
               needs to be converted to a ItemLayoutModel
        :return:
        """
        clz = type(self)
        self.condition_expr = parsed_item_layout.condition_expr
        self.description = parsed_item_layout.description

        if parsed_item_layout.topic is not None:
            self.topic = ItemLayoutTopicModel(self, parsed_item_layout.topic)
        else:
            self.topic = NoItemLayoutTopicModel(self)
        clz._logger.debug(f'# parsed children: {len(parsed_item_layout.children)}')
        for child in parsed_item_layout.children:
            child: BaseParser
            model_handler: Callable[[BaseModel, BaseParser, WinDialogState | None],
                                    BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child, None)
            self.children.append(child_model)

    @property
    def supports_label(self) -> bool:
        # ControlCapabilities.LABEL
        return True

    @property
    def supports_label2(self) -> bool:
        #  ControlCapabilities.LABEL2
        return False

    @property
    def condition_passes(self) -> bool:
        if self.condition_expr == '':
            return True

    def get_info_labels(self) -> List[str]:
        """
            Gets ListItems for this item_layout, after stripping the $INFO[
            prefix and ] suffix.

            List Containers can ONLY have Images and Labels. At this time we
            don't care about the images. The labels use ListItems/InfoLabels,
            so they are all that is needed to get the values.

        :return: A List of all ListItems in this ItemLayout
        """
        clz = ItemLayoutModel
        list_items: List[str] = []
        clz._logger.debug(f'# children: {len(self.children)}')
        for layout_item in self.children:
            layout_item: LabelModel
            label_expr: str = layout_item.label_expr
            if label_expr.startswith('$INFO['):
                label_expr = label_expr[6:-1]

            #  Don't know how to check visibility of a particular label in List
            #  if layout_item.is_visible():
            list_items.append(label_expr)
        return list_items

    def get_working_value(self) -> Tuple[bool, float]:
        """
            Gets the intermediate value of this control. Used for controls where
            the value is entered over time, such as a list container where
            you can scroll through your choices (via cursor up/down, etc.)
            without changing focus.

            The control's focus does not change so the value must be checked
            as long as the focus remains on the control. Further, the user wants
            to hear changes as they are being made and does not want to hear
            extra verbage, such as headings.

        :return: A Tuple with the first value indicating if there has been a
                 change in value since the last call. The second value is the
                 current value.
        """
        clz = ItemLayoutModel
        #  clz._logger.debug(f'{windialog_state}')

    def __repr__(self) -> str:
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False) -> str:
        """
        Convert self to a string.

        :param include_children:
        :return:
        """
        clz = type(self)
        description_str: str = ''
        if self.description != '':
            description_str = f'\n  description: {self.description}'

        condition_str: str = ''
        if self.condition_expr != '':
            condition_str = f'\n  condition: {self.condition_expr}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nItemLayoutModel type: {self.control_type} '
                       f'id: {self.control_id} '
                       f'{condition_str}'
                       f'{description_str}'
                       f'{topic_str}'
                       f'\n#children: {len(self.children)}')
        results.append(result)

        for child in self.children:
            child: BaseModel
            result: str = child.to_string(include_children=include_children)
            results.append(result)
        results.append('END ItemLayoutModel')
        return '\n'.join(results)
