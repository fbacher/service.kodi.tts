# coding=utf-8

"""
Provides a Skeleton Topic Model that supports a Label control without
a topic. It is meant to help simplify the implementations.
"""

from common.logger import BasicLogger
from gui.base_fake_topic import BaseFakeTopic
from gui.base_model import BaseModel
from gui.base_tags import (BaseAttributeType as BAT, control_elements, Item)

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class NoGroupTopicModel(BaseFakeTopic):
    """
        Provides a skeletal Topic implementation
    """
    _logger: BasicLogger = None
    item: Item = control_elements[BAT.TOPIC]

    def __init__(self, parent: BaseModel) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        fake_name: str = 'Fake_topic'  # patch up later
        super().__init__(parent=parent, topic_name=fake_name)
