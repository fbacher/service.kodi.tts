# coding=utf-8
from typing import ForwardRef, List


class IModel:
    def __init__(self) -> None:
        self.children: List[str] | None = None
        self.tree_id: str = ''

    @property
    def topic(self) -> ForwardRef('BaseTopicModel'):
        raise NotImplementedError('IModel does not implement')

    @property
    def control_id(self) -> int:
        raise NotImplementedError('IModel does not implement')
