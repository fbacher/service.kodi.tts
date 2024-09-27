# coding=utf-8
from typing import ForwardRef

import xbmc

from common.logger import BasicLogger
from gui.base_model import BaseModel
from gui.parser.parse_topic import ParseTopic
from gui.statements import Statements
from gui.topic_model import TopicModel

module_logger = BasicLogger.get_logger(__name__)


class GroupListTopicModel(TopicModel):

    _logger: BasicLogger = module_logger

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = GroupListTopicModel
        if clz._logger is None:
            clz._logger = module_logger

        super().__init__(parent=parent, parsed_topic=parsed_topic)

    @property
    def parent(self) -> ForwardRef('GroupListModel'):
        parent = super().parent
        parent: ForwardRef('GroupListModel')
        return parent

    def voice_active_item_value(self, stmts: Statements) -> bool:
        return self.parent.voice_active_item_value(stmts)

    def visible_item_count(self) -> int:
        """
        Determines the nmber of visible items in the group simply by
        counting the children which are visible.
        :return:
        """
        clz = GroupListTopicModel
        return self.parent.visible_item_count()

    @property
    def supports_item_collection(self) -> bool:
        """
        Indicates that this control contains multiple items.
        Used to influence how the heading for this control is read.

        :return:
        """
        return True

    def __repr__(self) -> str:
        """
            Don't print children by default
        :return:
        """
        return self.to_string(include_children=False)
