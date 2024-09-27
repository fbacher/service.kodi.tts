# coding=utf-8
import collections
from typing import ForwardRef, List, Tuple, Union


class ITopic:
    def __init__(self) -> None:
        pass

class IWindowStructure:

    def __init__(self) -> None:
        pass

    def get_control_and_topic_for_id(self, topic_id: str | int)\
            -> Tuple[ForwardRef('IModel'), ITopic]:
        return self.get_control_and_topic_for_id(topic_id)

    def get_topic_for_id(self, ctrl_topic_or_tree_id: str) \
                     -> Tuple[ForwardRef('IModel'), ForwardRef('BaseTopicModel')]:
        return self.get_topic_for_id(ctrl_topic_or_tree_id)

    def get_model_for_control_id(self, control_id: int) \
            -> Union[ForwardRef('IModel'), None]:
        return self.get_model_for_control_id(control_id)
