# coding=utf-8

"""
Provides a Skeleton Topic Model that supports a Label control without
a topic. It is meant to help simplify the implementations.
"""
from typing import Callable, ForwardRef, List, Tuple

from common.logger import BasicLogger
from gui.base_model import BaseModel
from gui.base_tags import (BaseAttributeType as BAT, control_elements, Item, Requires)
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class BaseTopicModel:
    _logger: BasicLogger = None
    item: Item = control_elements[BAT.TOPIC]

    def __init__(self, parent: BaseModel,
                 topic_name: str, rank: int = 0,
                 real_topic: bool = True) -> None:
        clz = BaseTopicModel

        # Glue this node to it's parent BaseModel

        self._parent: BaseModel = parent
        self.is_real_topic: bool = real_topic
        self.is_new_topic: bool = True
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        # Mark as a TopicModel. Used in BaseModel
        self.is_topic: bool = True
        clz._logger.debug(f'parent is: {parent.__class__.__name__}')
        self._name: str = topic_name
        self.rank: int = rank

    @property
    def name(self) -> str:
        return self._name

    @property
    def parent(self) -> BaseModel:
        return self._parent

    @property
    def window_model(self) -> ForwardRef('WindowModel'):
        return self._parent.window_model

    @property
    def windialog_state(self) -> WinDialogState:
        return self.window_model.windialog_state

    @property
    def window_id(self) -> int:
        return self.windialog_state.window_id

    @property
    def focus_changed(self) -> bool:
        return self.window_model.windialog_state.focus_changed
