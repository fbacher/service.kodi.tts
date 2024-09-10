# coding=utf-8

from typing import Callable, List, Tuple

from common.logger import BasicLogger, DEBUG_VERBOSE
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import (control_elements, ControlElement, Item)
from gui.element_parser import (ElementHandler)
from gui.focused_layout_topic_model import FocusedLayoutTopicModel
from gui.label_model import LabelModel
from gui.no_topic_models import NoFocusedLayoutTopicModel
from gui.parse_focused_layout import ParseFocusedLayout
from gui.topic_model import TopicModel
from windows.ui_constants import UIConstants
from windows.window_state_monitor import WinDialogState, WindowStateMonitor

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class FocusedLayoutModel(BaseModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlElement.FOCUSED_LAYOUT]

    def __init__(self, parent: BaseModel,
                 parsed_focused_layout: ParseFocusedLayout) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(window_model=parent.window_model,
                         parser=parsed_focused_layout)
        self.parent: BaseModel = parent
        self.broken: bool = False
        self.condition_expr: str = ''
        self.description: str = ''
        self.convert(parsed_focused_layout)

    def convert(self, parsed_focused_layout: ParseFocusedLayout) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_focused_layout: A ParseFocusedLayout instance that
               needs to be converted to a FocusedItemLayoutModel
        :return:
        """
        clz = type(self)
        self.condition_expr = parsed_focused_layout.condition_expr
        self.description = parsed_focused_layout.description

        if parsed_focused_layout.topic is not None:
            self.topic = FocusedLayoutTopicModel(self, parsed_focused_layout.topic)
        else:
            self.topic = NoFocusedLayoutTopicModel(self)

        clz._logger.debug(f'# parsed children: '
                          f'{len(parsed_focused_layout.get_children())}')

        for child in parsed_focused_layout.children:
            child: BaseParser
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
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
            Gets ListItems for this item_layout.

            List Containers can ONLY have Images and Labels. At this time we
            don't care about the images. The labels use ListItems/InfoLabels,
            so they are all that is needed to get the values.

        :return: A List of all ListItems in this ItemLayout
        """
        clz = FocusedLayoutModel
        list_items: List[str] = []
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'# children: {len(self.children)}')
        for layout_item in self.children:
            layout_item: LabelModel
            #  clz._logger.debug(f'item: {layout_item} visible: {layout_item.is_visible()}')
            #  Don't know how to check visibility of a particular label in List
            list_items.append(layout_item.label_expr)
        return list_items

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
            description_str = f'\ndescription: {self.description}'

        condition_str: str = ''
        if self.condition_expr != '':
            condition_str = f'\n  condition: {self.condition_expr}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nFocusedItemLayoutModel type: {self.control_type} '
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
        results.append('END FocusedItemLayoutModel')
        return '\n'.join(results)
