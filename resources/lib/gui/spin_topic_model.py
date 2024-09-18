# coding=utf-8
from typing import ForwardRef

from common.logger import BasicLogger
from gui.base_model import BaseModel
from gui.parser.parse_topic import ParseTopic
from gui.topic_model import TopicModel

module_logger = BasicLogger.get_logger(__name__)


class SpinTopicModel(TopicModel):

    _logger: BasicLogger = module_logger

    def __init__(self, parent: BaseModel, parsed_spin_topic: ParseTopic) -> None:
        clz = SpinTopicModel
        if clz._logger is None:
            clz._logger = module_logger

        super().__init__(parent=parent, parsed_topic=parsed_spin_topic)

    @property
    def parent(self) -> ForwardRef('SpinTopicModel'):
        return self._parent
