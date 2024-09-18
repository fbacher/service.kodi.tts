# coding=utf-8

from typing import ForwardRef

import xbmc

from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_model import BaseModel
from gui.base_tags import (BaseAttributeType as BAT, control_elements, Item)
from gui.parser.parse_topic import ParseTopic
from gui.statements import Statement, Statements, StatementType
from gui.topic_model import TopicModel
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class WindowTopicModel(TopicModel):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[BAT.TOPIC]

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = WindowTopicModel
        if clz._logger is None:
            clz._logger = module_logger

        super().__init__(parent=parent, parsed_topic=parsed_topic)

    @property
    def control_id(self) -> int:
        clz = type(self)
        clz._logger.debug(f'self: {self.__class__.__name__} '
                          f'parent: {self.parent.__class__.__name__} '
                          f'control_id: {super().control_id}')
        return super().control_id

    '''
    @control_id.setter
    def control_id(self, new_control_id):
        self.parent.control_id = new_control_id
    '''

    def get_hint_text(self, stmts: Statements) -> bool:
        if self.hint_text_expr == '':
            return True

        hint_text_id: int = -1
        try:
            hint_text_id = int(self.hint_text_expr)
            text = xbmc.getLocalizedString(hint_text_id)
            phrases: PhraseList = PhraseList.create(texts=text, check_expired=False)
            stmts.append(Statement(phrases, StatementType.HINT_TEXT))
        except ValueError as e:
            # Try as a Info Label,or such
            return False
        return True

    def get_topic_name(self) -> Phrase:
        return Phrase(text=self.name)

    def voice_control(self, stmts: Statements,
                      focus_changed: bool,
                      windialog_state: WinDialogState) -> bool:
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
        :param focus_changed: If True, then voice changed heading, labels and all
                              If False, then only voice a change in value.
        :param windialog_state: contains some useful state information
        :return: True if anything appended to phrases, otherwise False
        """

        clz = WindowTopicModel
        success: bool = False
        if self.alt_type == '':
            clz._logger.debug(f'{self.alt_type} not set')
            return False
        success = super().voice_control(stmts, focus_changed, windialog_state)
        # TODO, incomplete
        # clz._logger.debug(f'{phrases}')
        return success

    def voice_topic_headingx(self, stmts: Statements) -> bool:
        """
        Generate the speech for the window header. Takes into account
        whether this header was previously voiced.

        Specifically, Heading voices:
           Alt-ControlType, otherwise Control type
           Alt-Label, otherwise labeled_by, otherwise topic.label, otherwise
           the control's label
           next_header chain

        :param stmts: To append text to
        :return:
        """
        clz = WindowTopicModel
        success: bool = False
        control_name: str = ''
        clz._logger.debug(f'About to call voice_alt_control_name')
        success = self.voice_alt_control_name(stmts)
        if not success:
            success = self.voice_alt_label(stmts)
        if not success:
            clz._logger.debug(f'About to call model\'s voice_control_name')
            success = self.parent.voice_control_name(stmts)
        success |= self.voice_labeled_by(stmts)
        if not success:
            success = self.voice_label_expr(stmts)
        if not success:
            # label_2 is generally for value. We just want label
            success = self.voice_control_labels(stmts, voice_label=True, voice_label_2=False,
                                                control_id_expr=str(self.control_id))
        success |= self.voice_chained_controls(stmts)
        if not success:
            success |= self.parent.voice_control_heading(stmts)
        return success

    def voice_alt_label(self, stmts: Statements) -> bool:
        clz = WindowTopicModel
        if self.alt_label_expr == '':
            return False

        alt_label_id: int = -1
        try:
            alt_label_id = int(self.alt_label_expr)
            text: str = Messages.get_msg_by_id(alt_label_id)
            if text != '':
                stmts.last.phrases.append(Phrase(text=text))
                return True
        except ValueError as e:
            clz._logger.debug(f'Invalid int alt_label_id: {alt_label_id}')
            text = ''
        return False

    def voice_generic_label(self, stmts: Statements,
                            chain: bool = True) -> bool:
        """
        Voices the label for this topic's control. The label can be the actual
        control's label, or may be an alt_label, a labeled_by, etc. It all
        depends on which is found first.

        :param stmts: Append any voicings to stmts
        :param chain: If True, then call voice_chained_controls after voicing
                      the label
        :return: True if at least one phrase was appended. False if no phrases
                 added.
        """
        """
        Label search order:
            alt_label
            labeled_by
            control's label(s)
        """
        clz = WindowTopicModel
        clz._logger.debug(f'In voice_generic_label')
        success: bool = True
        if self.alt_label_expr != '':
            success = self.voice_info_label(stmts)
        else:
            success = False
        if not success:
            success = self.voice_labeled_by(stmts)
        if not success:
            clz._logger.debug(f'This control does not support labels')
            # success = self.voice_controls_labels(stmts)
        if chain:
            _ = self.voice_chained_controls(stmts)
        return success

    def voice_chained_controls(self, stmts: Statements) -> bool:
        """
        Voices controls in response to the presence of a topic's 'read-next' references
        to other topics. The chain continues as long as there are read-next
        references.

        Returns immediately if the current topic does not have 'read-next'

        :param stmts: Voiced stmts are appended
        :return:

        Note: The topic that is at the head of the chain first voices its own
              labels, then it requests any topic that it has a read_next for
              to voice.
        """
        clz = WindowTopicModel
        clz._logger.debug(f'In voice_chained_controls read_next_expr: '
                          f'{self.read_next_expr}')
        clz._logger.debug(f'{self}')
        success: bool = False
        if self.read_next_expr == '':
            return success
        control_model: BaseModel
        next_topic: TopicModel
        control_model, next_topic = self.window_struct.get_topic_for_id(
                self.read_next_expr)
        if next_topic is None or next_topic == '':
            clz._logger.debug(f"Can't find read_next_expr {self.read_next_expr}")
            return False
        success |= next_topic.voice_chained_controls(stmts, head_of_chain=False)
        clz._logger.debug(f'{stmts}')
        return success

    def voice_topic_value(self, stmts: Statements) -> bool:
        """
        Voice a control's value. Used primarily when a control's value comes from
        another control ('flows_to'). Let the control using the value decide
        whether it should be voiced (repeat values are supressed when the focus
        has not changed).

        :param stmts:
        :return:
        """
        clz = WindowTopicModel
        success: bool = False
        # When a control, like a button, impacts the value of another control,
        # then the control 'flows_to' another (TODO: perhaps more than one?) control.
        # When voicing a control's label, see if another control also needs to be voiced
        #
        if self.flows_to_expr is not None and self.flows_to_expr != '':
            # flows_to can be a control_id or a topic name
            clz._logger.debug(f'flows_to: {self.flows_to_expr}')
            control_model: BaseModel
            topic_to: TopicModel
            control_model, topic_to = self.window_struct.get_topic_for_id(
                    self.flows_to_expr)
            clz._logger.debug(f'topic_to: {topic_to}')
            success = topic_to.voice_topic_value(stmts)
            return success
        control_model: ForwardRef('BasicModel')
        control_model = self.parent
        return control_model.voice_control_value(stmts)

    def is_visible(self) -> bool:
        return self.parent.is_visible()
