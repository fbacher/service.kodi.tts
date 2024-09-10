# coding=utf-8

from typing import Callable, List

from common.debug import Debug
from common.logger import BasicLogger
from common.phrases import PhraseList
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import (control_elements, ControlElement, Item)
from gui.element_parser import ElementHandler
from gui.label_topic_model import LabelTopicModel
from gui.no_topic_models import NoLabelTopicModel
from gui.parse_label import ParseLabel
from gui.statements import Statements, StatementType
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class LabelModel(BaseLabelModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlElement.LABEL_CONTROL]

    def __init__(self, parent: BaseModel, parsed_label: ParseLabel) -> None:
        clz = LabelModel
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(window_model=parent.window_model, parser=parsed_label)
        # self.parent = parent
        self.label_for: str = ''
        self.hint_text_expr: str = ''
        self.parent: BaseModel = None
        # self.attributes_with_values: List[str] = clz.item.attributes_with_values
        # self.attributes: List[str] = clz.item.attributes
        self.visible_expr: str = ''
        self.default_control_always: bool = False
        self.default_control_id: int = -1
        self.scroll: bool = False
        self.scroll_suffix: str = '|'
        self.scroll_speed: int = 60  # pixels per sec
        self.label_expr: str = ''
        self.info_expr: str = ''
        self.number_expr: str = ''
        self.has_path: bool = False
        self.wrap_multiline: bool = False
        self.description: str = ''

        self.convert(parsed_label)

    def convert(self, parsed_label: ParseLabel) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_label: A ParseGroup instance that
               needs to be convertd to a GroupModel
        :return:
        """
        clz = LabelModel
        self.visible_expr = parsed_label.visible_expr
        self.wrap_multiline = parsed_label.wrap_multiline
        self.info_expr = parsed_label.info_expr
        # self.attributes_with_values: List[str]
        # self.attributes: List[str]
        self.label_for = parsed_label.label_for
        if self.label_for != '':
            clz._logger.debug(f'label_for: {self.label_for}')
        # self.default_control_always = parsed_label.default_control_always
        # self.default_control_id = parsed_label.default_control_id
        self.scroll: bool = parsed_label.scroll
        self.scroll_suffix = parsed_label.scroll_suffix
        self.scroll_speed = parsed_label.scroll_speed
        self.label_expr = parsed_label.label_expr
        self.info_expr = parsed_label.info_expr
        self.number_expr = parsed_label.number_expr
        self.has_path = parsed_label.has_path
        self.wrap_multiline = parsed_label.wrap_multiline
        self.description = parsed_label.description

        if parsed_label.topic is not None:
            self.topic = LabelTopicModel(self, parsed_label.topic)
        else:
            self.topic = NoLabelTopicModel(self)

        for child in parsed_label.children:
            child: BaseParser
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
            self.children.append(child_model)

    @property
    def supports_heading_label(self) -> bool:
        """
        Indicates whether this control provides a label which explains what it
        is for. For example, a button's label almost certainly is to explain
        why you should press it. On the other hand a label control does not.
        A label control may be displaying a date or the result of an action.
        More information is needed for controls like labels in order to know
        what to do with them.

        :return:
        """
        return False

    @property
    def supports_label(self) -> bool:
        # ControlCapabilities.LABEL
        return True

    @property
    def supports_label2(self) -> bool:
        #  ControlCapabilities.LABEL2
        return False

    @property
    def supports_value(self) -> bool:
        """
        This control is unable to provide a value. I.E. it can't give any
        indication of what happens when pressed. If the topic for this
        control or another provides flows_from/flows_to or similar, then a
        value can be determined that way, but not using this method.
        :return:
        """
        return False

    def voice_control(self, stmts: Statements,
                      focus_changed: bool,
                      windialog_state: WinDialogState) -> bool:
        """

        :param stmts: Statements to append to
        :param focus_changed: If True, then voice changed heading, labels and all
                              If False, then only voice a change in value.
        :param windialog_state: contains some useful state information
        :return: True if anything appended to phrases, otherwise False


     Note that focus_changed = False can occur even when a value has changed.
     One example is when user users cursor to select different values in a
     slider, but never leaves the control's focus.
     """
        clz = LabelModel
        success: bool = True
        if self.topic is not None:
            topic: LabelTopicModel = self.topic
            clz._logger.debug(f'topic: {topic.alt_type}')
            success = topic.voice_alt_control_name(stmts)
            if not success:
                success = self.voice_control_name(stmts)
            success = self.voice_heading(stmts)
            success = self.voice_label(stmts)
            success = self.voice_label2(stmts)
            # Voice either next Topic down or focus item
        else:
            topic: NoLabelTopicModel = self.topic

        # TODO, incomplete
        return success

    def voice_controls_labels(self, stmts: Statements) -> bool:
        """
            Voices ONLY label, since ControlLabel does not support label2
        :param stmts:
        :return:

        """
        result: bool = self.voice_label(stmts)
        return result

    def voice_labels(self, stmts: Statements, voice_label: bool = True,
                     voice_label_2: bool = True) -> bool:
        """
        Redundant with voice_label since ControlLabel does not support Label2.
        Simplier to keep it.

        :param stmts:
        :param voice_label: Voice the label, if supportted by control
        :param voice_label_2 Voice label_2, if supported by control (Not supported)
        :return:
        """
        if not voice_label:
            return False
        return self.voice_label(stmts)

    def voice_label(self, stmts: Statements,
                    control_id_expr: int | str | None = None,
                    stmt_type: StatementType = StatementType.NORMAL) -> bool:
        """
        TODO: Get rid of control_id, rely on Topic code handling

        :param stmts: Any found text is appended to this
        :param control_id_expr:  If non-None, then used as the control_id instead
               of self.control_id
        :param stmt_type: Sets the StatementType of voiced label.
        :return:
        """
        clz = LabelModel
        clz._logger.debug(f'voice_label control_id: {self.control_id} '
                          f'control_id_expr: {control_id_expr}')
        success: bool = False
        control_id: int | None
        control_query: str | None
        success = self.get_label_ll(stmts, label_expr=control_id_expr,
                                    stmt_type=stmt_type)
        clz._logger.debug(f'{stmts}')
        return success

    def voice_value(self, stmts: Statements) -> bool:
        """
        Voice this label as a value for some other control.
        Let the other control decide whether to ignore repeat values.
        That will be consistent with a control deciding when to voice its
        value.
        :param stmts:
        :return:
        """
        clz = LabelModel
        # clz._logger.debug(f'label_model: {self}')
        # temp_phrases: PhraseList = PhraseList(check_expired=False)
        success: bool = self.voice_label(stmts)
        # if temp_phrases.equal_text(self.previous_value):
        #     return False
        # else:
        #     self.previous_value = temp_phrases
        #    phrases.extend(temp_phrases)
        return success

    def __repr__(self) -> str:
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False) -> str:
        clz = LabelModel
        control_id: str = ''
        if self.control_id != '':
            control_id = f' id: {self.control_id}'

        description_str: str = ''
        if self.description != '':
            description_str = f'\n  decription: {self.description}'

        label_for_str: str = ''
        if self.label_for != '':
            label_for_str = f'\n  label_for: {self.label_for}'

        visible_expr: str = ''
        if self.visible_expr is not None and len(self.visible_expr) > 0:
            visible_expr = f'\n  visible_expr: {self.visible_expr}'

        label_expr: str = ''
        if self.label_expr is not None and len(self.label_expr) > 0:
            label_expr = f'\n  label_expr: {self.label_expr}'
        number_expr: str = ''
        if self.number_expr:
            number_expr = f'\n  number_expr: {number_expr}'

        has_path_str: str = ''
        if self.has_path:
            has_path_str = f'\n  has_path: {self.has_path}'

        hint_text_str: str = ''
        if self.hint_text_expr != '':
            hint_text_str = f'\n  hint_text: {self.hint_text_expr}'

        info_expr: str = ''
        if len(self.info_expr) > 0:
            info_expr = f'\n  info_expr: {self.info_expr}'

        if len(self.visible_expr) > 0:
            visible_expr: str = f'\n visible: {self.visible_expr}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nLabelModel type: {self.control_type}'
                       #  f' item: {clz.item} key: {clz.item.key}'
                       f'{control_id}'
                       f'{description_str}'
                       f'{label_for_str}'
                       f'{visible_expr}'
                       f'{label_expr}'
                       f'{number_expr}{has_path_str} '
                       f'{hint_text_str}'
                       f'{info_expr}'
                       f'{topic_str}'
                       f'\n  #children: {len(self.children)}'
                       )
        results.append(result)

        if include_children:
            for child in self.children:
                child: BaseModel
                results.append(child.to_string(include_children))
        results.append(f'\nEND LabelModel')

        return '\n'.join(results)
