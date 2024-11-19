# coding=utf-8
import pathlib
from typing import Callable, Dict, ForwardRef, List

import xbmc

from common.logger import BasicLogger, DEBUG_V, DEBUG_XV
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlElement, Item, WindowType
from gui.base_topic_model import BaseTopicModel
from gui.element_parser import (ElementHandler)
from gui.interfaces import IWindowStructure
from gui.no_topic_models import NoWindowTopicModel
from gui.parser.parse_window import ParseWindow
from gui.statements import Statements
from gui.topic_model import TopicModel
from gui.window_topic_model import WindowTopicModel
from windows.window_state_monitor import WinDialogState


my_logger = BasicLogger.get_logger(__name__)


class WindowModel(BaseModel):

    item: Item = control_elements[ControlElement.WINDOW]
    window_models: Dict[int, ForwardRef('WindowModel')] = {}

    @classmethod
    def get_instance(cls, window_id: int,
                     xml_path: pathlib.Path,
                     windialog_state: WinDialogState)\
            -> ForwardRef('WindowModel'):
        my_logger.debug(f'windialog_state is None: {windialog_state is None}')
        if window_id not in cls.window_models.keys():
            parser: ParseWindow = ParseWindow.get_instance(xml_path=xml_path,
                                                           is_addon=True)
            if my_logger.isEnabledFor(DEBUG_XV):
                my_logger.debug_xv(f'DUMP PARSED: window_id: {window_id}')
                for result in parser.dump_parsed():
                    my_logger.debug_xv(result)
                my_logger.debug_v('finished DUMP PARSED')
            window_parser = parser
            window_model: ForwardRef('WindowModel') = WindowModel(window_parser,
                                                                  windialog_state)
            cls.window_models[window_id] = window_model
        return cls.window_models[window_id]

    def __init__(self, parsed_window: ParseWindow,
                 windialog_state: WinDialogState) -> None:
        clz = WindowModel
        my_logger.debug(f'windialog_state is None: {windialog_state is None}')
        self._windialog_state: WinDialogState = windialog_state
        super().__init__(window_model=self, parser=parsed_window,
                         windialog_state=windialog_state)
        my_logger.debug(f'I am here in WindowModel')

        # Reduce the number of repeated phrases.
        # Detect when there has been a change to a new window, or when the focus
        # has changed.

        self.xml_path: pathlib.Path = parsed_window.xml_path
        self.window_type: WindowType = parsed_window.window_type
        self.default_control_id: str = parsed_window.default_control_id
        self.window_modality: str = parsed_window.window_modality  # Only dialogs
        self.menu_control: int = parsed_window.menu_control
        self.visible_expr: str = parsed_window.visible_expr

        self.best_alt_label: str = ''
        self.best_hint_text: str = ''

        # window: xbmcgui.Window = WindowStateMonitor.get_dialog()
        # control = window.getControl(100)
        # my_logger.debug(f'control label: {control.getLabel()}')

        # Now, covert all controls that have been previously parsed into models.
        # Uses depth-first search though the controls

        self.convert_controls(parsed_window)
        #  self._windialog_state: WinDialogState = None
        self._window_struct: IWindowStructure = None

    def convert_controls(self, parsed_window: ParseWindow) -> None:
        clz = WindowModel
        children: List[BaseParser] = []
        # parsers: List[BaseParser] = parsed_window.parsers
        # my_logger.debug(f'# children: {len(parsed_window.children)}')

        if parsed_window.topic is not None:
            self.topic = WindowTopicModel(parent=self,
                                          parsed_topic=parsed_window.topic)
        else:
            self.topic = NoWindowTopicModel(self)

        for child in parsed_window.children:
            child: BaseParser
            model_handler: Callable[[BaseModel, BaseParser,
                                     WinDialogState | None], BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            value_or_control = model_handler(self, child)
            if my_logger.isEnabledFor(DEBUG_V):
                my_logger.debug_v(f'value_or_control: {value_or_control}')
            if value_or_control is not None:
                if (child.item.key in (ControlElement.CONTROLS.name,
                                       ControlElement.CONTROL.name)):
                    self.children.append(value_or_control)

    @property
    def window_model(self) -> ForwardRef('WindowModel'):
        return self

    @property
    def window_struct(self) -> IWindowStructure:
        if self._window_model == self:
            return self._window_struct
        return self._window_model.window_struct

    @window_struct.setter
    def window_struct(self, window_struct: IWindowStructure) -> None:
        self._window_struct = window_struct

    @property
    def windialog_state(self) -> WinDialogState:
        return self._windialog_state

    @windialog_state.setter
    def windialog_state(self, updated_value: WinDialogState) -> None:
        """
           The WinDialogState changes for every evaluation of the window.
        :param updated_value:
        :return:
        """
        self._windialog_state = updated_value

    def voice_control(self, stmts: Statements) -> bool:
        """
        Generate the speech for the window itself. Takes into account
        whether this was previously voiced.

        Typical content for a window is:
            "Window" | "Dialog" <title of window>

        If this content is the same as what was most recently voiced, then
        the voicing is skipped. There is not sufficient information to reliably
        predict when the text has changed, so it is generated each time and
        then compared with the previous text. Perhaps this can be improved upon.

        In the case of a Window/Dialog, the voiced content comes from the
        Window's 'header'. Other controls have other logical sections.

        :param stmts: Statements to append to
        :return: True if anything appended to stmts, otherwise False
        """
        clz = WindowModel
        success: bool = False
        # Only voice when window is newly changed
        # TODO: improve by taking into account when window voicing fails to occur
        # such as when there is an interruption (focus change occurs before this
        # window info is announced, causing the window not being announced when
        # focus change announced).
        my_logger.debug(f'changed: {self.windialog_state.changed}')
        if not self.windialog_state.window_changed:
            return False
        # TODO, incomplete
        return success

    def voice_heading(self, stmts: Statements) -> bool:
        """
        Generate the speech for the window header. Takes into account
        whether this header was previously voiced.
        :param stmts:
        :return:
        """
        clz = WindowModel
        success: bool = False
        control_name: str = ''
        topic: TopicModel = self.topic
        success = self.voice_control_name(stmts)
        if topic is not None:
            my_logger.debug(f'topic: {topic.name} real: {topic.is_real_topic} '
                              f'new: {topic.is_new_topic} type: {type(topic)}')
            if topic.is_real_topic and topic.is_new_topic:
                topic: BaseTopicModel
                success = topic.voice_topic_heading(stmts)
            #  success = topic.voice_labeled_by(stmts)
        if not success:
            success = self.voice_control_heading(stmts)
        return success

    def __repr__(self) -> str:
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False) -> str:
        clz = WindowModel
        result: str = ''

        #  Start with this window
        window_str: str = (f'\nWindowModel window: {self.control_type} id: '
                           f'{self.window_id}')
        if self.menu_control != -1:
            menu_ctrl_str = f'\n menu_ctrl: {self.menu_control}'
        default_control_str: str = f''
        if self.default_control_id != '':
            default_control_str = f'\n default_control: {self.default_control_id}'
        visible_expr_str: str = ''
        if self.visible_expr != '':
            visible_expr_str = f'\n visible_expr: {self.visible_expr}'
        window_modality: str = ''
        if self.window_modality != '':
            window_modality = f'\n window_modality: {self.window_modality}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result = (f'{window_str}{default_control_str}{visible_expr_str}'
                  f'{window_modality}')
        results.append(result)
        results.append(f'{topic_str}')

        results.append(f' # children: {len(self.children)}')
        if include_children:
            for control in self.children:
                control: BaseModel
                results.append(f"child type: {type(control)}")
                result: str = control.to_string(include_children)
                results.append(result)

        results.append('\nFinete')
        return '\n'.join(results)

    def is_visible(self) -> bool:
        return xbmc.getCondVisibility(f'Window.IsVisible({self.control_id})')


ElementHandler.add_model_handler(WindowModel.item, WindowModel)
