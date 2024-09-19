# coding=utf-8

"""
Provides a Skeleton Topic Model that supports a Label control without
a topic. It is meant to help simplify the implementations.
"""
from typing import Callable, Final, ForwardRef, List, Tuple

from common.logger import BasicLogger
from gui.base_model import BaseModel
from gui.base_tags import (BaseAttributeType as BAT, control_elements, Item, Requires)
from gui.interfaces import IWindowStructure
from gui.parser.parse_topic import ParseTopic
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class BaseTopicModel:
    """

    """
    _logger: BasicLogger = module_logger  # None
    item: Item = control_elements[BAT.TOPIC]

    def __init__(self, parent: BaseModel,
                 parsed_topic: ParseTopic | None, rank: int = 0,
                 real_topic: bool = True) -> None:
        clz = BaseTopicModel

        # Glue this node to it's parent BaseModel

        self._parent: BaseModel = parent
        self.is_real_topic: bool = real_topic
        self.is_new_topic: bool = True
        self._name: str = parent.tree_id
        if clz._logger is None:
            clz._logger = module_logger

        if parsed_topic is None:

            # Mark as a TopicModel. Used in BaseModel
            self.is_topic: bool = True
            self._name: str = ''
            self.rank: int = rank
            self._topic_right: Final[str] = ''
            self._topic_left:  Final[str] = ''
            self._topic_up:  Final[str] = ''
            self._topic_down: Final[str] = ''

            self._description: Final[str] = ''
            self._hint_text_expr: Final[str] = ''
            self._info_expr: Final[str] = ''

            # flows_to_topic & flows_to_model are the DESTINATION of the
            # flow. Therefore, the flows_to_topic will actually be the one
            # with a flows_from = to the topic with flows_to in it.
            # Similar for flows_to_model
            self._flows_from_expr:  Final[str] = ''

            # flows_to_expr can reference EITHER a topic or a control
            # So we have a home for both. Makes it much more clear than
            # a union.
            #
            self._flows_to: Final[str] = ''
            self._flows_to_expr: str = ''
            self._labeled_by_expr:  Final[str] = ''
            self._labeled_by: str = ''
            self._label_for: str = ''
            self._label_for_expr: Final[str] = ''
            self._label_expr: Final[str] = ''
            self._read_next_expr: Final[str] = ''
            self._inner_topic: Final[str] = ''
            self._outer_topic: Final[str] = ''
            self._read_next: str = ''
            return

        if clz._logger is None:
            clz._logger = module_logger
        # Mark as a TopicModel. Used in BaseModel
        self.is_topic: bool = True
        self._name: str = parsed_topic.name
        self.rank: int = rank
        self._topic_right: Final[str] = parsed_topic.topic_right
        self._topic_left:  Final[str] = parsed_topic.topic_left
        self._topic_up:  Final[str] = parsed_topic.topic_up
        self._topic_down: Final[str] = parsed_topic.topic_down

        self._description: Final[str] = parsed_topic.description
        self._hint_text_expr: Final[str] = parsed_topic.hint_text_expr
        self._info_expr: Final[str] = parsed_topic.info_expr

        # flows_to_topic & flows_to_model are the DESTINATION of the
        # flow. Therefore, the flows_to_topic will actually be the one
        # with a flows_from = to the topic with flows_to in it.
        # Similar for flows_to_model
        clz._logger.debug(f'parsed_topic.flows_from: {parsed_topic.flows_from}')
        self._flows_from_expr: str = parsed_topic.flows_from
        self._flows_to_expr: str = parsed_topic.flows_to

        # flows_to_expr can reference EITHER a topic or a control
        # So we have a home for both. Makes it much more clear than
        # a union.
        #
        self._flows_to_topic: BaseTopicModel | None = None
        self._flows_to_model: BaseModel | None = None
        self._flows_from_topic: BaseTopicModel | None = None
        self._flows_from_model: BaseModel | None = None

        self._labeled_by_expr:  Final[str] = parsed_topic.labeled_by_expr
        self._labeled_by: str = ''
        self._label_for: str = ''
        self._label_for_expr: Final[str] = parsed_topic.label_for_expr
        self._label_expr: Final[str] = parsed_topic.label_expr
        self._read_next_expr: Final[str] = parsed_topic.read_next_expr
        self._inner_topic: Final[str] = parsed_topic.inner_topic
        self._outer_topic: Final[str] = parsed_topic.outer_topic
        self._read_next: str = ''

    @property
    def name(self) -> str:
        """

        :return:
        """
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def parent(self) -> BaseModel:
        """

        :return:
        """
        return self._parent

    @property
    def window_model(self) -> ForwardRef('WindowModel'):
        """

        :return:
        """
        return self._parent.window_model

    @property
    def windialog_state(self) -> WinDialogState:
        """

        :return:
        """
        return self.parent.windialog_state

    @windialog_state.setter
    def windialog_state(self, updated_state: WinDialogState) -> None:
        self.parent.windialog_state = updated_state

    @property
    def window_struct(self) -> IWindowStructure:
        return self._parent.window_struct

    @property
    def window_id(self) -> int:
        """

        :return:
        """
        return self.windialog_state.window_id

    @property
    def focus_changed(self) -> bool:
        """

        :return:
        """
        return self.window_model.windialog_state.focus_changed

    @property
    def topic_right(self) -> str:
        """

        :return:
        """
        return self._topic_right

    @property
    def topic_left(self) -> str:
        """

        :return:
        """
        return self._topic_left

    @property
    def flows_from_expr(self) -> str:
        """

        :return:
        """
        return self._flows_from_expr

    @property
    def flows_from_topic(self) -> ForwardRef('TopicModel') | None:
        """

        :return:
        """
        return self._flows_from_topic

    @flows_from_topic.setter
    def flows_from_topic(self, topic: ForwardRef('TopicModel')) -> None:
        """

        :return:
        """
        self._flows_from_topic = topic

    @property
    def flows_from_model(self) -> BaseModel | None:
        """

        :return:
        """
        return self._flows_from_model

    @flows_from_model.setter
    def flows_from_model(self, model: BaseModel) -> None:
        """

        :return:
        """
        self._flows_from_model = model

    @property
    def flows_to_expr(self) -> str:
        """

        :return:
        """
        return self._flows_to_expr

    @property
    def flows_to_topic(self) -> ForwardRef('TopicModel'):
        """

        :return:
        """
        return self._flows_to_topic

    @flows_to_topic.setter
    def flows_to_topic(self, topic: ForwardRef('TopicModel')) -> None:
        """

        :return:
        """
        self._flows_to_topic = topic

    @property
    def flows_to_model(self) -> BaseModel | None:
        """

        :return:
        """
        return self._flows_to_model

    @flows_to_model.setter
    def flows_to_model(self, model: BaseModel) -> None:
        """

        :return:
        """
        self._flows_to_topic = model

    @property
    def labeled_by(self) -> str:
        """

        :return:
        """
        return self._labeled_by

    @labeled_by.setter
    def labeled_by(self, value: str) -> None:
        self._labeled_by = value

    @property
    def label_for(self) -> str:
        """

        :return:
        """
        return self._label_for

    @label_for.setter
    def label_for(self, value: str) -> None:
        self._label_for = value

    @property
    def label_for_expr(self) -> str:
        """

        :return:
        """
        return self._label_for_expr

    @property
    def labeled_by_expr(self) -> str:
        """

        :return:
        """
        return self._labeled_by_expr

    @property
    def label_expr(self) -> str:
        """

        :return:
        """
        return self._label_expr

    @property
    def read_next(self) -> str:
        """

        :return:
        """
        return self._read_next

    @read_next.setter
    def read_next(self, value: str) -> None:
        self._read_next = value

    @property
    def read_next_expr(self) -> str:
        """

        :return:
        """
        return self._read_next_expr

    @property
    def inner_topic(self) -> str:
        """

        :return:
        """
        return self._inner_topic

    @property
    def outer_topic(self) -> str:
        """

        :return:
        """
        return self._outer_topic

    @property
    def topic_up(self) -> str:
        """

        :return:
        """
        return self._topic_up

    @property
    def topic_down(self) -> str:
        """

        :return:
        """
        return self._topic_down

    @property
    def description(self) -> str:
        """

        :return:
        """
        return self._description

    @property
    def hint_text_expr(self) -> str:
        """

        :return:
        """
        return self._hint_text_expr

    @property
    def info_expr(self) -> str:
        """

        :return:
        """
        return self._info_expr
