# coding=utf-8

from common.logger import BasicLogger, DEBUG_V, DISABLED
from gui.base_model import BaseModel
from gui.parser.parse_topic import ParseTopic
from gui.topic_model import TopicModel
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class GroupTopicModel(TopicModel):

    _logger: BasicLogger = module_logger

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = GroupTopicModel
        if clz._logger is None:
            clz._logger = module_logger

        super().__init__(parent=parent, parsed_topic=parsed_topic)

    @property
    def control_id(self) -> int:
        clz = GroupTopicModel
        if clz._logger.isEnabledFor(DISABLED):
            clz._logger.debug_v(f'self: {self.__class__.__name__} '
                              f'parent: {self.parent.__class__.__name__} '
                              f'control_id: {super().control_id}')
        return super().control_id

    '''
    def voice_control(self, phrases: PhraseList,
                      focus_changed: bool,
                      windialog_state: WinDialogState) -> bool:
        """
        Generate the speech for this group. Takes into account
        whether this was previously voiced.

        Groups are frequently not voiced, however they are the logical place to
        voice headings, titles, hints, help, etc. By using a Topic for a group
        you can achieve at least some of these things.

                :param phrases: PhraseList to append to
        :param focus_changed: If True, then voice changed heading, labels and all
                              If False, then only voice a change in value.
        :param windialog_state: contains some useful state information
        :return: True if anything appended to phrases, otherwise False
        """
        clz = GroupTopicModel
        success: bool = False
        # Only voice when window is newly changed
        # TODO: improve by taking into account when window voicing fails to occur
        # such as when there is an interruption (focus change occurs before this
        # window info is announced, causing the window not being announced when
        # focus change announced).
        clz._logger.debug(f'changed: {windialog_state.changed}')

        temp_phrases: PhraseList = PhraseList(check_expired=False)
        success = self.voice_topic_headingtemp_phrases)
        if not self.parent.previous_heading.equal_text(temp_phrases):
            self.parent.previous_heading.clear()
            self.parent.previous_heading.extend(temp_phrases)
            phrases.extend(temp_phrases)

            success = self.parent.voice_number_of_items(phrases)
            # Voice either focused control, or label/text
            # success = self.voice_active_item_value(phrases)
            # Voice either next Topic down or focus item

            # success = self.voice_controlx(phrases)

        # TODO, incomplete
        clz._logger.debug(f'{phrases}')
        return success
    '''

    '''
    def get_hint_text(self, phrases: PhraseList) -> bool:
        if self.hint_text_expr == '':
            return True

        hint_text_id: int = -1
        try:
            hint_text_id = int(self.hint_text_expr)
            text = xbmc.getLocalizedString(hint_text_id)
            phrase: Phrase = Phrase(text=text)
            phrases.append(phrase)
        except ValueError as e:
            # Try as a Info Label,or such
            return False
        return True
    '''

    '''
    def voice_topic_headingself, phrases: PhraseList) -> bool:
        """
        Generate the speech for the window header. Takes into account
        whether this header was previously voiced.
        :param phrases:
        :return:
        """
        clz = GroupTopicModel
        success: bool = False
        # TODO: Voice control name
        #
        success = self.voice_generic_label(phrases)
        clz._logger.debug(f'From voice_generic_label {phrases}')
        return success
    '''
    '''
    def voice_labeled_by(self, phrases: PhraseList) -> bool:
        """
        Orchestrates voicing using any labeled_by reference. Delegates most of
        the work to this topic's control.

        Note that the topic with the labeled by may require a chain of labels
        to be read.

        :param phrases: Appends any voicings to phrases
        :return: True if phrases was added to. Otherwise, False
        """
        # Needs work
        clz = GroupTopicModel
        if self.labeled_by_expr == '':
            return False

        clz._logger.debug(
                f'In voice_labeled_by labeled_by_expr: {self.labeled_by_expr}')
        success: bool = False
        # The labeled_by_expr can contain:
        #     A control_id (must be all numeric)
        #     A topic name
        #     A tree_id (dynamically created when window defined)
        #     A info-label type expression: begins with $INFO or $PROP

        label: str = ''
        info: str = ''
        if self.labeled_by_expr.startswith('$INFO['):
            info: str = self.labeled_by_expr[6:-1]
            label: str = xbmc.getInfoLabel(info)
        elif self.labeled_by_expr.startswith('$PROP['):
            info: str = self.labeled_by_expr[6:-1]
            label: str = xbmc.getInfoLabel(f'Window().Property({info})')
        if label is not None and label != '':
            phrases.add_text(texts=label)
            return True
        elif info is not None and info != '':
            self._logger.debug(f'BAD $INFO or $PROP query: {info}')
            return False

        control: BaseModel | None
        topic: TopicModel | None
        control, topic = self.parent.get_control_and_topic_for_id(self.labeled_by_expr)
        success = False
        if topic is not None:
            try:
                success = topic.voice_control_labels(phrases)
            except Exception:
                clz._logger.exception('')
                success = False
        if not success:
            # Have to do it the hard way without topic, if possible.
            # TODO: Implement
            success = False
        clz._logger.debug(f'{phrases}')
        return success
    '''
