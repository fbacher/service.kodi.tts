# coding=utf-8
from typing import ForwardRef

from common.logger import BasicLogger
from common.phrases import PhraseList
from gui.base_model import BaseModel
from gui.base_tags import ValueFromType
from gui.gui_globals import GuiGlobals
from gui.parse_topic import ParseTopic
from gui.statements import Statement, Statements, StatementType
from gui.topic_model import TopicModel
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SpinTopicModel(TopicModel):

    _logger: BasicLogger = None

    def __init__(self, parent: BaseModel, parsed_spin_topic: ParseTopic) -> None:
        clz = SpinTopicModel
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)

        super().__init__(parent=parent, parsed_topic=parsed_spin_topic)

    @property
    def parent(self) -> ForwardRef('SpinTopicModel'):
        return self._parent
