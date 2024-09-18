# coding=utf-8

from typing import Callable, List, Tuple

import xbmcgui

from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import PhraseList
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import (control_elements, ControlElement, Item, Requires, ValueUnits)
from gui.element_parser import (ElementHandler)
from gui.no_topic_models import NoSliderTopicModel
from gui.parser.parse_slider import ParseSlider
from gui.slider_topic_model import SliderTopicModel
from gui.topic_model import TopicModel
from windows.ui_constants import UIConstants
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class SliderModel(BaseModel):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.SLIDER]

    def __init__(self, parent: BaseModel, parsed_slider: ParseSlider) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
        super().__init__(window_model=parent.window_model, parser=parsed_slider)
        self.parent: BaseModel = parent
        self.broken: bool = False
        self.visible_expr: str = ''
        self.description: str = ''
        self.alt_label_expr: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.enable_expr: str = ''
        self.hint_text_expr: str = ''
        self.action_expr: str = ''
        self.labeled_by_expr: str = ''
        self.info_expr: str = ''
        self.on_info_expr: str = ''
        self.orientation_expr: str = 'vertical'
        self.attributes_with_values: List[str] = clz.item.attributes_with_values
        self.attributes: List[str] = clz.item.attributes
        self._listener: Callable[[int, WinDialogState], bool] | None = None
        self.value: float = 0.0
        self.value_changed: bool = False

        self.convert(parsed_slider)

        self.slider_control: xbmcgui.ControlSlider | None = None
        if Requires.TOPIC_UNITS not in self.topic.requires:
            clz._logger.error(f"SliderModels MUST have units specified in it's Topic")
            clz._logger.debug(f'requires: {self.topic.requires}')
            clz._logger.debug(f'{self.topic.units}')
        else:
            self.units: ValueUnits = self.topic.units
            clz._logger.debug(f'units: {self.units}')

    def convert(self, parsed_slider: ParseSlider) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_slider: A ParseSlider instance that
               needs to be converted to a SliderModel
        :return:
        """
        clz = type(self)
        self.visible_expr = parsed_slider.visible_expr
        self.description = parsed_slider.description
        self.alt_label_expr = parsed_slider.alt_label_expr
        self.on_focus_expr = parsed_slider.on_focus_expr
        self.on_unfocus_expr = parsed_slider.on_unfocus_expr
        self.enable_expr = parsed_slider.enable_expr
        self.hint_text_expr = parsed_slider.hint_text_expr
        self.action_expr = parsed_slider.action_expr
        self.labeled_by_expr = parsed_slider.labeled_by_expr
        self.info_expr = parsed_slider.info_expr
        self.on_info_expr = parsed_slider.on_info_expr
        self.orientation_expr = parsed_slider.orientation_expr

        if parsed_slider.topic is not None:
            self.topic = SliderTopicModel(self, parsed_slider.topic)
        else:
            self.topic = NoSliderTopicModel(self)
        for child in parsed_slider.children:
            child: BaseParser
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
            self.children.append(child_model)

    @property
    def supports_label(self) -> bool:
        # ControlCapabilities.LABEL
        return False

    @property
    def supports_label2(self) -> bool:
        #  ControlCapabilities.LABEL2
        return False

    @property
    def supports_change_without_focus_change(self) -> bool:
        """
            Indicates if the control supports changes that can occur without
            a change in Focus. Slider is an example. User modifies value without
            leaving the container. Further, you only want to voice the value,
            not the control name, etc.
        :return:
        """
        return True

    def voice_control(self, phrases: PhraseList,
                      focus_changed: bool,
                      windialog_state: WinDialogState) -> bool:
        """
        :param phrases: PhraseList to append to
        :param focus_changed: If True, then voice changed heading, labels and all
                              If False, then only voice a change in value.
        :param windialog_state: contains some useful state information
        :return: True if anything appended to phrases, otherwise False

        Note that focus_changed = False can occur even when a value has changed.
        One example is when user users cursor to select different values in a
        slider, but never leaves the control's focus.
        """
        clz = type(self)
        success: bool = True
        if not focus_changed:
            # Only voice change in value
            success = self.voice_value(phrases, focus_changed)
            return success
        if self.topic is not None:
            topic: TopicModel = self.topic
            temp_phrases: PhraseList = PhraseList(check_expired=False)
            heading_success: bool = self.voice_heading(phrases)
            # if not self.previous_heading.equal_text(temp_phrases):
            #     self.previous_heading.clear()
            #     self.previous_heading.extend(temp_phrases)
            #     phrases.extend(temp_phrases)

            # temp_phrases.clear()
            # Simply appends one value if it has changed
            success = self.voice_value(phrases, focus_changed)
            if heading_success:
                success = True
            return success
        # TODO, incomplete
        return False

    def get_orientation(self) -> str:
        msg_id: int = 32809
        if self.orientation_expr == UIConstants.VERTICAL:
            msg_id = 32808
        orientation: str = Messages.get_msg_by_id(msg_id=msg_id)
        return orientation

    def voice_value(self, phrases: PhraseList, focus_changed: bool = True) -> bool:
        clz = SliderModel
        clz._logger.debug(f'Not Supported')
        return False

    def get_working_value(self) -> Tuple[bool, float]:
        """
            Gets the intermediate value of this control. Used for controls where
            the value is entered over time, such as fine-tuning a slider value.
            The control's focus does not change so the value must be checked
            as long as the focus remains on the control. Further, the user wants
            to hear changes as they are being made and does not want to hear
            extra verbage, such as headings.

        :return: A Tuple with the first value indicating if there has been a
                 change in value since the last call. The second value is the
                 current value.
        """
        clz = SliderModel
        #  clz._logger.debug(f'{windialog_state}')

        if self.focus_changed:
            # clz._logger.debug(f'value was: {self.value} changed: {self.value_changed}'
            #                   f' control_id: {self.control_id}')
            # clz._logger.debug(f'value_id: {hex(id(self.value))} '
            #                   f'changed: {hex(id(self.value_changed))}')
            self.value = None
        # clz._logger.debug(f'value was: {self.value} changed: {self.value_changed} ')
        # clz._logger.debug(f'value_id: {hex(id(self.value))} '
        #                   f'changed: {hex(id(self.value_changed))}')
        self.slider_control = self.get_control_slider(self.control_id)
        new_value: float = self.slider_control.getFloat()

        new_value = round(new_value, 2)
        self.value_changed: bool = (self.value != new_value)
        # clz._logger.debug(f'new_value: {new_value} previous: {self.value} '
        #                   f'changed: {self.value_changed}')
        self.value = new_value
        return self.value_changed, self.value

    '''
    def start_monitor(self):
        """
        Register to receive simple status events while this control has focus.

        Mostly used to trigger this control to poll for any value change so that
        the change can be voiced. Crude, but our options are limited.

        :return:
        """
        clz = SliderModel
        self._listener = self.poll_for_value_change
        clz._logger.debug(f'Registering listener')
        WindowStateMonitor.register_window_state_listener(self._listener,
                                                          name='slider',
                                                          require_focus_change=False,
                                                          window_id=self.windialog_state.window_id,
                                                          control_id=self.control_id,
                                                          insert_at_front=True)

    def poll_for_value_change(self, changed: int,
                              windialog_state: WinDialogState) -> bool:
        """
        Used to trigger a poll for a value change in this slider.

        Called in response to start_monitor.

        :param changed: bit-mask value of window/control state. See WinDialogState
        :param windialog_state: contains detailed change state as well as useful
            properties to access the state.
        :return: True if this event was handled by this listener and does not
        need to be given to other listeners.
        """
        clz = SliderModel
        #  clz._logger.debug(f'{windialog_state}')
        if (windialog_state.focus_id != self.control_id or
                windialog_state.window_id != self.window_id):
            return False
        self.slider_control = self.get_control_slider(self.control_id)
        new_value: float = self.slider_control.getFloat()
        new_value = round(new_value, 1)
        self.value_changed: bool = (self.value != new_value)
        clz._logger.debug(f'value: {new_value} previous: {self.value} '
                          f'changed: {self.value_changed}')
        self.value = new_value

        # if self.value_changed:
        #     self.topic.value_changed(new_value)

        # Want regular mechanism to do the voicing
        return False

    def stop_monitor(self):
        """
        Unregister listener to prevent unneeded callbacks. Called with this
        control no longer has focus.

        :return:
        """
        WindowStateMonitor.unregister_window_state_listener(name=f'slider_{self.control_id}',
                                                            listener=self._listener)
    '''

    def __repr__(self) -> str:
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False) -> str:
        """
        Convert self to a string.

        :param include_children:
        :return:
        """
        clz = type(self)
        description_str: str = ''

        if self.description != '':
            description_str = f'\ndescription: {self.description}'

        visible_expr: str = ''
        if self.visible_expr is not None and len(self.visible_expr) > 0:
            visible_expr = f'\nvisible_expr: {self.visible_expr}'

        enable_str: str = ''
        if self.enable_expr != '':
            enable_str = f'\nenable_expr: {self.enable_expr}'

        if self.on_focus_expr is not None and (len(self.on_focus_expr) > 0):
            on_focus_expr: str = f'\non_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr is not None and (len(self.on_unfocus_expr) > 0):
            on_unfocus_expr: str = f'\non_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''

        labeled_by_expr: str = ''
        if self.labeled_by_expr != '':
            labeled_by_expr = f'\nlabeled_by_expr: {self.labeled_by_expr}'

        alt_label_expr: str = ''
        if self.alt_label_expr != '':
            alt_label_expr = f'\nalt_label_expr: {self.alt_label_expr}'

        hint_text_str: str = ''
        if self.hint_text_expr != '':
            hint_text_str = f'\nhint_text: {self.hint_text_expr}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nSliderModel type: {self.control_type} '
                       f'id: {self.control_id} '
                       f'{enable_str}'
                       f'{description_str}'
                       f'{visible_expr}'
                       f'{labeled_by_expr}'
                       f'{alt_label_expr}'
                       f'{hint_text_str}'
                       f'{on_focus_expr}'
                       f'{on_unfocus_expr}'
                       f'{topic_str}'
                       f'\n#children: {len(self.children)}')
        results.append(result)

        if include_children:
            for child in self.children:
                child: BaseModel
                result: str = child.to_string(include_children=include_children)
                results.append(result)
        results.append('END SliderModel')
        return '\n'.join(results)
