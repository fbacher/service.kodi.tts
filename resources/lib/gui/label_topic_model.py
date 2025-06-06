# coding=utf-8

from common.logger import BasicLogger
from gui.base_model import BaseModel
from gui.parser.parse_topic import ParseTopic
from gui.topic_model import TopicModel
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class LabelTopicModel(TopicModel):

    _logger: BasicLogger = module_logger

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = LabelTopicModel
        if clz._logger is None:
            clz._logger = module_logger

        super().__init__(parent=parent, parsed_topic=parsed_topic)
