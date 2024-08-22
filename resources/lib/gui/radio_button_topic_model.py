# coding=utf-8

from common.logger import BasicLogger
from gui.base_model import BaseModel
from gui.parse_topic import ParseTopic
from gui.topic_model import TopicModel

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class RadioButtonTopicModel(TopicModel):
    """
        Handles 'topic' metadata embedded in skin .xml files to help voice
        RadioButton controls.

        Notes:
            It may be possible to use the function SetProperty with onclick to
            set the state of the button in a window property and the access that
            value using an infolabel.
    """
    _logger: BasicLogger = None

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = RadioButtonTopicModel
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)

        super().__init__(parent=parent, parsed_topic=parsed_topic)
