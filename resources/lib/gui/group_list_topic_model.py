# coding=utf-8
from typing import ForwardRef

import xbmc

from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.parse_topic import ParseTopic
from gui.statements import Statement, Statements
from gui.topic_model import TopicModel
from windows.ui_constants import AltCtrlType
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class GroupListTopicModel(TopicModel):

    _logger: BasicLogger = None

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = GroupListTopicModel
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)

        super().__init__(parent=parent, parsed_topic=parsed_topic)

    @property
    def parent(self) -> ForwardRef('GroupListModel'):
        parent = super().parent
        parent: ForwardRef('GroupListModel')
        return parent

    def get_item_number(self) -> int:
        """
        Used to get the current item number from a List type topic. Called from
        a child topicof the list

        :return: Current topic number, or -1
        """
        clz = GroupListTopicModel
        if not self.supports_item_count:
            return -1

        from gui.group_list_model import GroupListModel

        container_id: int = self.control_id
        curr_item: str = ''
        try:
            curr_item = xbmc.getInfoLabel(f'Container({container_id}).CurrentItem')
        except Exception:
            clz._logger.exception('')

        item_number: int = -1
        if curr_item.isdigit():
            item_number = int(curr_item)
        return item_number

    def voice_active_item(self, stmts: Statements) -> bool:
        return self.parent.voice_active_item(stmts)

    def visible_item_count(self) -> int:
        """
        Determines the nmber of visible items in the group simply by
        counting the children which are visible.
        :return:
        """
        clz = GroupListTopicModel
        return self.parent.visible_item_count()
