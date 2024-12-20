# coding=utf-8
from typing import ForwardRef, List

from gui import ControlElement
from windows.window_state_monitor import WinDialogState


class IModel:
    def __init__(self) -> None:
        #  self.children: List[str] | None = None
        #  self.tree_id: str = ''
        pass

    @property
    def topic(self) -> ForwardRef('BaseTopicModel'):
        raise NotImplementedError('IModel does not implement')

    @property
    def control_id(self) -> int:
        raise NotImplementedError('IModel does not implement')

    @property
    def control_type(self) -> ControlElement:
        raise NotImplementedError('IModel does not implement')

    @property
    def window_id(self) -> int:
        raise NotImplementedError('IModel does not implement')

    @property
    def windialog_state(self) -> WinDialogState:
        raise NotImplementedError('IModel does not implement')
