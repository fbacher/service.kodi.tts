# coding=utf-8

from typing import Callable, Final, ForwardRef, List, Tuple, Union

import xbmcgui

from common.logger import BasicLogger
from common.messages import Message, Messages
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlType, Item, Requires, Units
from gui.element_parser import (BaseElementParser, ElementHandler)
from gui.parse_slider import ParseSlider
from gui.parse_label import ParseLabel
from gui.parse_topic import ParseTopic
from gui.topic_model import TopicModel
from windows.ui_constants import UIConstants

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SliderModel(BaseModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.SLIDER.name]

    def __init__(self, parent: BaseModel, parsed_slider: ParseSlider) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
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
        self.children: List[BaseModel] = []
        self.attributes_with_values: List[str] = clz.item.attributes_with_values
        self.attributes: List[str] = clz.item.attributes

        self.convert(parsed_slider)

        if Requires.TOPIC_UNITS not in self.topic.requires:
            clz._logger.error(f"SliderModels MUST have units specified in it's Topic")
            clz._logger.debug(f'requires: {self.topic.requires}')
            clz._logger.debug(f'{self.topic.units}')
            clz._logger.debug(f'{self.topic.units[0]}')
        else:
            self.units_scale: Units = self.topic.units[0]
            self.units_type: Units = self.topic.units[1]
            self.units_step: float | int = self.topic.units[2]
            self.units_min_value: float | int = self.topic.units[3]
            self.units_max_value: float | int = self.topic.units[4]
            self.units_scale_msg_id: int = 0  # No scale to voice, just a number
            clz._logger.debug(f'units_scale_msgid units: {self.units_scale}'
                              f' SCALE_DB: {Units.SCALE_DB}')
            if self.units_scale == Units.SCALE_DB:
                self.units_scale_msg_id = Messages.MSG_UNITS_DB
                clz._logger.debug(f'msgid: {self.units_scale_msg_id}')
            if self.units_scale == Units.SCALE_PERCENT:
                self.units_scale_msg_id = Messages.MSG_UNITS_PERCENT

        self.previous_heading: PhraseList = PhraseList()
        self.previous_value: int | float = -123456789

    def convert(self, parsed_slider: ParseSlider) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_slider: A ParseSlider instance that
               needs to be converted to a SliderModel
        :return:
        """
        clz = type(self)
        self.control_type = parsed_slider.control_type
        self.control_id: str = parsed_slider.control_id
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
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(ParseTopic.item)
            self.topic = model_handler(self, parsed_slider.topic)

        clz._logger.debug(f'# parsed children: {len(parsed_slider.get_children())}')

        for child in parsed_slider.children:
            child: BaseParser
            model_handler: Callable[[BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
            self.children.append(child_model)

    def clear_history(self) -> None:
        self.previous_heading.clear()
        self.previous_value = -123456789

    def voice_control(self, phrases: PhraseList,
                      focus_changed: bool) -> bool:
        """

        :param phrases: PhraseList to append to
        :param focus_changed: If True, then voice changed heading, labels and all
                              If False, then only voice a change in value.
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
            temp_phrases: PhraseList = PhraseList()
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

    def voice_heading(self, phrases: PhraseList) -> bool:
        """
        Slider control does NOT have a label. Visually a nearby label control
        (or some similar control) provides the label. But there is NO linkage.
        Must manually provide label or label control in a Topic to have it
        properly voiced.

        :param phrases:
        :return: True if heading was appended to phrases, otherwise False
        """
        clz = type(self)
        success: bool = False
        topic: TopicModel | None = self.topic
        if topic is None:
            return self.get_heading_without_topic(phrases)
        success = self.voice_labeled_by(phrases)
        clz._logger.debug(f'voice_labeled_by: {success}')
        if not success:
            success = self.topic.voice_label_expr(phrases)
            clz._logger.debug(f'voice_label_expr: {success}')
        orientation_str: str = self.get_slider_orientation()
        control_name: str
        control_name = self.get_control_name()
        phrases.append(Phrase(text=f'{orientation_str} {control_name}'))
        return success

    def get_slider_orientation(self) -> str:
        msg_id: int = 32809
        if self.orientation_expr == UIConstants.VERTICAL:
            msg_id = 32808
        orientation: str = Messages.get_msg_by_id(msg_id=msg_id)
        return orientation

    def voice_value(self, phrases: PhraseList, focus_changed: bool = True) -> bool:
        value: float | int = self.get_value()
        if focus_changed or value != self.previous_value:
            if self.units_scale_msg_id == 0:
                text = f'{value}'
            else:
                text = Messages.get_formatted_msg_by_id(self.units_scale_msg_id, value)
            if text != '':
                phrase: Phrase = Phrase(text=text)
                phrases.append(phrase)
        self.previous_value = value
        return True

    def get_value(self) -> float | int:
        clz = type(self)
        slider_ctrl: xbmcgui.ControlSlider
        clz._logger.debug(f'Getting control')
        control_id: int = self.get_non_negative_int(self.control_id)
        ctrl: xbmcgui.Control = self.get_control(control_id)
        ctrl: xbmcgui.ControlSlider
        if (not self.topic_checked and
                (self.topic is None or (Requires.TOPIC_UNITS not in self.topic.requires))):
            clz._logger.debug(f'Slider REQUIRES that "Topic.Units" be defined'
                              f' for the slider')
            clz._logger.debug(f'topic.requires: {self.topic.requires}')
            self.broken = True
        self.topic_checked = True

        if self.broken:
            return 0

        value: float | int = 0
        if self.units_type == Units.TYPE_FLOAT:
            value: float = ctrl.getFloat()
        else:
            value: int = ctrl.getInt()

        clz._logger.debug(f'Slider value: {value}')
        return value

    def __repr__(self) -> str:
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

        for child in self.children:
            child: BaseParser
            results.append(str(child))

        results.append('END SliderModel')
        return '\n'.join(results)
