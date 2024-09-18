# coding=utf-8
import collections
from typing import ForwardRef, List, Tuple

from gui.window_structure import WindowStructure


class ITopic:
    def __init__(self) -> None:
        pass

class IWindowStructure:

    @classmethod
    def get_window_struct(cls, window_id: int) -> ForwardRef('WindowStructure'):
        return WindowStructure.get_window_struct(window_id)

    def __init__(self, window_id: int) -> None:
        self.window_struct = WindowStructure.get_window_struct(window_id)

    def get_control_and_topic_for_id(self, topic_id: str) -> Tuple[int, ITopic]:
        return self.window_struct.get_control_and_topic_for_id(topic_id)

    def get_topic_for_id(self,
                         ctrl_topic_or_tree_id: str) \
                     -> Tuple[ForwardRef('IModel'), ForwardRef('BaseTopicModel')]:
        return self.window_struct.get_topic_for_id(ctrl_topic_or_tree_id)
