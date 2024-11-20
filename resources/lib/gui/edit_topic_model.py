# coding=utf-8
from __future__ import annotations

from typing import ForwardRef

from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_model import BaseModel
from gui.base_tags import (BaseAttributeType as BAT, control_elements, Item)
from gui.parser.parse_topic import ParseTopic
from gui.statements import Statements
from gui.topic_model import TopicModel
from windows.ui_constants import AltCtrlType
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class EditTopicModel(TopicModel):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[BAT.TOPIC]

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = EditTopicModel
        if clz._logger is None:
            clz._logger = module_logger

        super().__init__(parent=parent, parsed_topic=parsed_topic)

    def voice_heading(self, stmts: Statements) -> bool:
        """
        Generate the speech for the window header. Takes into account
        whether this header was previously voiced.
        :param stmts:
        :return:
        """
        clz = EditTopicModel
        success: bool = False
        # TODO: Voice control name
        #
        success = self.voice_generic_label(stmts)
        return success

    def voice_alt_control_name(self, stmts: Statements) -> bool:
        clz = EditTopicModel
        if self.alt_type == '':
            return False
        alt_name: str = self.get_alt_control_name()
        if alt_name == '':
            return False
        stmts.last.phrases.append(Phrase(text=alt_name,
                                         post_pause_ms=Phrase.PAUSE_DEFAULT,
                                         check_expired=False))
        return True

    def get_alt_control_name(self) -> str:
        clz = EditTopicModel
        if self.alt_type == '':
            return ''

        phrases: PhraseList = PhraseList(check_expired=False)
        alt_type: AltCtrlType = AltCtrlType.get_alt_type_for_name(self.alt_type)
        success = AltCtrlType.get_message(alt_type, phrases)
        return phrases[-1].get_text()

    def get_alt_control_type(self) -> AltCtrlType:
        alt_type: str = ''
        if self.alt_type != '':
            alt_type: AltCtrlType = AltCtrlType.get_alt_type_for_name(self.alt_type)
        return alt_type

    def voice_alt_label(self, stmts: Statements) -> bool:
        clz = EditTopicModel
        if self.alt_label_expr == '':
            return False

        alt_label_id: int = -1
        try:
            alt_label_id = int(self.alt_label_expr)
            text: str = Messages.get_msg_by_id(alt_label_id)
            if text != '':
                stmts.last.phrases.append(Phrase(text=text, check_expired=False))
                return True
        except ValueError as e:
            clz._logger.debug(f'Invalid int alt_label_id: {alt_label_id}')
            text = ''
        return False

    def voice_label_expr(self, stmts: Statements) -> bool:
        clz = EditTopicModel
        success: bool = False
        if self.label_expr != '':
            # First, assume label_expr is the id of a label
            #
            try:
                msg_id: int = int(self.label_expr)
                text = Messages.get_msg_by_id(msg_id)
                if text != '':
                    phrase: Phrase = Phrase(text=text, check_expired=False)
                    stmts.last.phrases.append(phrase)
                    success = True
            except ValueError as e:
                success = False
            if not success:
                clz._logger.debug(f'No message found for topic label')
                # phrase = Phrase(text=f'label_expr: {self.label_expr}')
                # phrases.append(phrase)
                # success = False
        else:
            success = False
        return success

    def voice_labeled_by(self, stmts: Statements) -> bool:
        """
        Orchestrates voicing using any labeled_by reference. Delegates most of
        the work to this topic's control.

        Note that the topic with the labeled by may require a chain of labels
        to be read.

        :param stmts: Appends any voicings to stmts
        :return: True if stmts was added to. Otherwise, False
        """
        # Needs work
        clz = EditTopicModel
        clz._logger.debug(
                f'In voice_labeled_by labeled_by_expr: {self.labeled_by_expr}')
        success: bool = False
        # The labeled_by_expr can contain:
        #     A control_id (must be all numeric)
        #     A topic name
        #     A tree_id (dynamically created when window defined)
        control: BaseModel | None
        topic: TopicModel | None
        control, topic = self.window_struct.get_control_and_topic_for_id(
                self.labeled_by_expr)
        if topic is not None:
            success = topic.voice_control_labels(stmts)
        else:
            # Have to do it the hard way without topic, if possible.
            # TODO: Implement
            success = False
        clz._logger.debug(f'{stmts.last}')
        return success

    def voice_controls_labels(self, stmts: Statements) -> bool:
        """
        Convenience method that calls this topic's control to get the label.

        :param stmts: Append any voicings to stmts
        :return: True if at least one phrase was appended. False if no stmts
                added.
        TODO: don't inherit from BaseModel!!!
        """
        clz = EditTopicModel
        clz._logger.debug(f'In voice_controls_labels about to call'
                          f' WindowTopicModel.voice_controls_labels')
        # Only voice the control's label
        return self.voice_controls_labels(stmts)

    def voice_generic_label(self, stmts: Statements,
                            chain: bool = True) -> bool:
        """
        Voices the label for this topic's control. The label can be the actual
        control's label, or may be an alt_label, a labeled_by, etc. It all
        depends on which is found first.

        :param stmts: Append any voicings to stmts
        :param chain: If True, then call voice_chained_controls after voicing
                      the label
        :return: True if at least one phrase was appended. False if no stmts
                 added.
        """
        """
        Label search order:
            alt_label
            labeled_by
            control's label(s)
        """
        clz = EditTopicModel
        clz._logger.debug(f'In voice_generic_label')
        success: bool = True
        if self.alt_label_expr != '':
            success = self.voice_info_label(stmts)
        else:
            success = False
        if not success:
            success = self.voice_labeled_by(stmts)
        if not success:
            success = self.voice_control_labels(stmts)
        if chain:
            # If this topic has a 'read_next' value, then voice the label(s)
            # from that topic
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
        clz = EditTopicModel
        clz._logger.debug(f'In voice_chained_controls')
        clz._logger.debug(f'{self}')

        success: bool = True
        if self.read_next_expr == '':
            return success

        control_model: BaseModel
        next_topic: TopicModel
        control_model, next_topic = self.window_struct.get_control_and_topic_for_id(
                self.read_next_expr)
        if next_topic is None:
            clz._logger.debug(f"Can't find read_next_expr {self.read_next_expr}")
            return False
        _ = next_topic.voice_generic_label(stmts)
        clz._logger.debug(f'{stmts.last.phrases}')
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
        clz = EditTopicModel
        success: bool = False
        # When a control, like a button, impacts the value of another control,
        # then the control 'flows_to' another (TODO: perhaps more than one?) control.
        # When voicing a control's label, see if another control also needs to be voiced
        #
        if self.flows_to_expr != '':
            # flows_to can be a control_id or a topic name
            clz._logger.debug(f'flows_to: {self.flows_to_expr}')
            control_model: BaseModel
            topic_to: TopicModel
            control_model, topic_to = self.window_struct.get_control_and_topic_for_id(self.flows_to_expr)

            clz._logger.debug(f'topic_to: {topic_to}')
            success = topic_to.voice_topic_value(stmts)
            return success
        control_model: ForwardRef('BasicModel')
        control_model = self.parent
        return control_model.voice_value(stmts)

    def is_visible(self) -> bool:
        return self.parent.is_visible()
