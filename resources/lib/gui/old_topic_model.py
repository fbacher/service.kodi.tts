# coding=utf-8

from typing import Callable, ForwardRef, List, Tuple

import xbmc

from common.critical_settings import CriticalSettings
from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import BaseAttributeType as BAT, control_elements, Item, Requires
from gui.base_topic_model import BaseTopicModel
from gui.element_parser import ElementHandler
from gui.parse_topic import ParseTopic
from gui.topic_model import TopicModel
from windows.ui_constants import AltCtrlType, UIConstants

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class OldTopicModel(BaseTopicModel):

    _logger: BasicLogger = None
    item: Item = control_elements[BAT.TOPIC]

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = TopicModel
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)

        # Must be set prior to super
        self.parent: BaseModel = parent
        self._control_id = parent.control_id

        self._logger.debug(f'old parent: {parent.__class__.__name__} '
                           f'topic: {parsed_topic.name} nodes control_id:'
                           f' {parent.control_id} topic control_id: {self.control_id}')
        super().__init__(parent=parent, topic_name=parsed_topic.name,
                         rank=parsed_topic.rank)
        # Mark as a TopicModel. Used in BaseModel
        self.is_topic: bool = True
        self.is_new_topic: bool = False
        self.alt_label_expr: str = parsed_topic.alt_label_expr
        # if self.alt_label_expr == '':
        #     AltCtrlType.get_ctrl_type_for_control(self.parent.control_type)
        self.label_expr: str = parsed_topic.label_expr
        self.labeled_by_expr: str = parsed_topic.labeled_by_expr
        self.label_for_expr: str = parsed_topic.label_for_expr
        self.description: str = parsed_topic.description
        self.hint_text_expr: str = parsed_topic.hint_text_expr
        self.info_expr: str = parsed_topic.info_expr
        self.inner_topic: str = parsed_topic.inner_topic
        self.outer_topic: str = parsed_topic.outer_topic
        self.flows_from: str = parsed_topic.flows_from
        self.flows_to: str = parsed_topic.flows_to
        self.topic_left: str = parsed_topic.topic_left
        self.topic_right: str = parsed_topic.topic_right
        self.topic_up: str = parsed_topic.topic_up
        self.topic_down: str = parsed_topic.topic_down
        self.alt_type: str = parsed_topic.alt_type
        if self.parent.control_type == '':
            self.alt_type = AltCtrlType.NONE
        else:
            self.alt_type = UIConstants.alt_ctrl_type_for_ctrl_type.get(
                    self.parent.control_type)
        self.rank: int = parsed_topic.rank
        self.read_next_expr: str = parsed_topic.read_next_expr
        self.true_msg_id: int = -1
        if parsed_topic.true_msg_id is not None:
            self.true_msg_id = parsed_topic.true_msg_id
        self.false_msg_id: int = -1
        if parsed_topic.false_msg_id is not None:
            self.false_msg_id = parsed_topic.false_msg_id

        #  TODO: Units looks weird. Probably should be a pattern to format with.

        self.units: None | Tuple[str, str, float | int, float | int, float | int] = None
        self.units = parsed_topic.units
        self.requires: List[Requires.TOPIC_UNITS] = []
        if self.units is not None:
            self.requires.append(Requires.TOPIC_UNITS)
        self.children: List[BaseModel] = []

        # Type provides a means to voice what kind of control this is other than just
        # the Kodi standard controls, group, groupList, etc.

        self.type: str = parsed_topic.type

        self.attributes_with_values: List[str] = clz.item.attributes_with_values
        self.attributes: List[str] = clz.item.attributes

        self.convert(parsed_topic)

    def convert(self, parsed_topic: ParseTopic) -> None:
        """
            Convert Parsed elements, etc. to a model.

        :param parsed_topic: A ParseSlider instance that
               needs to be converted to a TopicModel
        :return:
        """
        clz = TopicModel
        for child in parsed_topic.children:
            child: BaseParser
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
            self.children.append(child_model)

        clz._logger.debug(f'parent: {type(self.parent)}')
        self.parent.topic = self
        clz._logger.debug(f'topic name: {self.name}')

    @property
    def control_id(self) -> int:
        clz = TopicModel
        clz._logger.debug(f'self: {self.__class__.__name__} '
                          f'control_id: {self._control_id}')
        return self._control_id

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

    def get_topic_name(self) -> Phrase:
        return Phrase(text=self.name)

    def voice_alt_control_name(self, phrases: PhraseList) -> bool:
        clz = TopicModel
        if self.alt_type == '':
            return False
        alt_name: str = self.get_alt_control_name()
        if alt_name == '':
            return False
        phrases.append(Phrase(text=alt_name, post_pause_ms=Phrase.PAUSE_DEFAULT))
        return True

    def get_alt_control_name(self) -> str:
        clz = TopicModel
        if self.alt_type == '':
            return ''

        phrases: PhraseList = PhraseList(check_expired=False)
        alt_type: AltCtrlType = AltCtrlType.alt_ctrl_type_for_ctrl_name(self.alt_type)
        success = AltCtrlType.get_message(alt_type, phrases)
        return phrases[-1].get_text()

    def get_alt_control_type(self) -> AltCtrlType:
        alt_type: str = ''
        if self.alt_type != '':
            alt_type: AltCtrlType = AltCtrlType.alt_ctrl_type_for_ctrl_name(self.alt_type)
        return alt_type

    def voice_alt_label(self, phrases: PhraseList) -> bool:
        clz = TopicModel
        if self.alt_label_expr == '':
            return False

        alt_label_id: int = -1
        try:
            alt_label_id = int(self.alt_label_expr)
            text: str = Messages.get_msg_by_id(alt_label_id)
            if text != '':
                phrases.append(Phrase(text=text))
                return True
        except ValueError as e:
            clz._logger.debug(f'Invalid int alt_label_id: {alt_label_id}')
            text = ''
        return False

    def voice_info_label(self, phrases: PhraseList) -> bool:
        clz = OldTopicModel
        if self.alt_label_expr == '':
            return False

        try:
            text = xbmc.getInfoLabel(f'{self.alt_label_expr}')
            clz._logger.debug(f'alt_label_expr: {self.alt_label_expr} = {text}')
        except ValueError as e:
            text = ''

        if text == '':
            text = CriticalSettings.ADDON.getInfoLabel(self.alt_label_expr)
            clz._logger.debug(f'alt_label_expr: {self.alt_label_expr} = {text}')
        if text == '':
            clz._logger.debug(f'Failed to get alt_label_expr {self.alt_label_expr}')
            return False

        #  clz._logger.debug(f'text: {text}')
        #  TAG_RE = re.compile(r'(?i)\[/?(?:B|I|COLOR|UPPERCASE|LOWERCASE)[^]]*]')
        text = UIConstants.TAG_RE.sub('', text).strip(' .')
        # clz._logger.debug(f'text: {text}')
        texts: List[str] = text.split('[CR]')
        clz._logger.debug(f'texts: {texts}')
        for text in texts:
            if text == '':
                if len(phrases) > 0:
                    phrases[-1].set_post_pause(Phrase.PAUSE_DEFAULT)
                continue
            phrase = Phrase(text)
            phrases.append(phrase)
        clz._logger.debug(f'phrases: {phrases}')
        return True

    def voice_label_expr(self, phrases: PhraseList) -> bool:
        clz = OldTopicModel
        success: bool = False
        if self.label_expr != '':
            # First, assume label_expr is the id of a label
            #
            try:
                msg_id: int = int(self.label_expr)
                text = Messages.get_msg_by_id(msg_id)
                if text != '':
                    phrase: Phrase = Phrase(text=text)
                    phrases.append(phrase)
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

    def voice_labeled_by(self, phrases: PhraseList) -> bool:
        """
        Orchestrates voicing using any labeled_by reference. Delegates most of
        the work to this topic's control.

        :param phrases: Appends any voicings to phrases
        :return: True if phrases was added to. Otherwise, False
        """
        # Needs work
        clz = OldTopicModel
        success: bool = False
        if self.labeled_by_expr != '':
            control_id: int = BaseModel.get_non_negative_int(self.labeled_by_expr)
            if control_id == -1:
                clz._logger.debug(
                        f"Can't find labeled by for {self.labeled_by_expr}")
                return False
            label_cntrl: BaseModel
            label_cntrl = self.parent.window_model.get_control_model(control_id)
            label_cntrl: ForwardRef('LabelModel')
            clz._logger.debug(f'labeled_by: {self.labeled_by_expr}')
            clz._logger.debug(f'label_cntrl: {label_cntrl is not None}')
            if label_cntrl is not None:
                # TODO: Change to use voice_generic_label
                success = label_cntrl.voice_labels(phrases)  # Label and Label 2
        clz._logger.debug(f'{phrases}')
        return success

    def voice_labels(self, phrases: PhraseList,
                     control_id_expr: str | None = None) -> bool:
        """
        Convenience method that calls this topic's control to voice the labels.

        :param phrases: Append any voicings to phrases
        :param control_id_expr: IGNORED
        :return: True if at least one phrase was appended. False if no phrases
                added.
        TODO: don't inherit from BaseModel!!!
        """
        clz = OldTopicModel
        clz._logger.debug(f'In OLD topic_model')
        return self.parent.voice_labels(phrases)

    def voice_generic_label(self, phrases: PhraseList) -> bool:
        """
        Voices the label for this topic's control. The label can be the actual
        control's label, or may be an alt_label, a labeled_by, etc. It all
        depends on which is found first.

        :param phrases: Append any voicings to phrases
        :return: True if at least one phrase was appended. False if no phrases
                 added.
        """
        """
        Label search order:
            alt_label
            labeled_by
            control's label(s)
        """
        success: bool = True
        if self.alt_label_expr != '':
            success = self.voice_info_label(phrases)
        if not success:
            success = self.voice_labeled_by(phrases)
        if not success:
            success = self.voice_labels(phrases)
        return success

    def voice_chained_controls(self, phrases: PhraseList,
                               head_of_chain: bool = False) -> bool:
        """
        Voices a chain of controls that don't get focus (labels) and there is
        no other mechanism to read them (no label_for or flows_to). This still
        a hack-in-progress. Requires more work to understand the problem and
        options.

        :param phrases: Voiced phrases are appended
        :param head_of_chain: True only when this is the originating topic.
        :return:

        Note: The topic that is at the head of the chain first voices its own
              labels, then it requests any topic that it has a read_next for
              to voice.
        """
        clz = OldTopicModel
        clz._logger.debug(f'In voice_chained_controls read_next: {self.read_next_expr}')
        success: bool = False
        if self.read_next_expr == '':
            return success

        next_topic: OldTopicModel = self.parent.get_topic_for_id(self.read_next_expr)
        if next_topic is None or next_topic == '':
            clz._logger.debug(f"Can't find read_next {self.read_next_expr}")
            return False
        if not head_of_chain:
            success = next_topic.voice_generic_label(phrases)
        next_topic.voice_chained_controls(phrases, head_of_chain=False)
        clz._logger.debug(f'{phrases}')
        return success

    def voice_value(self, phrases: PhraseList) -> bool:
        """
        Voice a control's value. Used primarily when a control's value comes from
        another control ('flows_to'). Let the control using the value decide
        whether it should be voiced (repeat values are supressed when the focus
        has not changed).

        :param phrases:
        :return:
        """
        clz = OldTopicModel
        success: bool = False
        # When a control, like a button, impacts the value of another control,
        # then the control 'flows_to' another (TODO: perhaps more than one?) control.
        # When voicing a control's label, see if another control also needs to be voiced
        #
        if self.flows_to != '':
            # flows_to can be a control_id or a topic name
            clz._logger.debug(f'flows_to: {self.flows_to}')
            topic_to: OldTopicModel = self.parent.get_topic_for_id(self.flows_to)
            clz._logger.debug(f'topic_to: {topic_to}')
            success = topic_to.voice_value(phrases)
            return success
        control_model: ForwardRef('BasicModel')
        control_model = self.parent
        return control_model.voice_value(phrases)

    def __repr__(self) -> str:
        clz = TopicModel

        name_str: str = ''
        if self.name != '':
            name_str = (f'\n  name_str: {self.name} control_id: {self.control_id} '
                        f'parent_control: {self.parent.__class__.__name__} '
                        f'{self.parent.control_id}')

        label_expr: str = ''
        if self.label_expr != '':
            label_expr = f'\n  label_expr: {self.label_expr}'
        alt_label_expr: str = ''
        if self.alt_label_expr != '':
            alt_label_expr = f'\n  alt_label_expr: {self.alt_label_expr}'
        labeled_by_str: str = ''
        if self.labeled_by_expr != '':
            labeled_by_str = f'\n  labeled_by: {self.labeled_by_expr}'
        label_for_str: str = ''
        if self.label_for_expr != '':
            label_for_str = f'\n label_for: {self.label_for_expr}'
        info_expr: str = ''
        if len(self.info_expr) > 0:
            info_expr = f'\n  info_expr: {self.info_expr}'

        description_str: str = ''
        if self.description != '':
            description_str = f'\n  description: {description_str}'

        hint_text_str: str = ''
        if self.hint_text_expr != '':
            hint_text_str = f'\n  hint_text: {self.hint_text_expr}'

        inner_topic_str: str = ''
        if self.inner_topic != '':
            inner_topic_str = f'\n  inner_topic: {self.inner_topic}'

        outer_topic_str: str = ''
        if self.outer_topic != '':
            outer_topic_str = f'\n  outer_topic: {self.outer_topic}'

        flows_to_str: str = ''
        if self.flows_to != '':
            flows_to_str = f'\n  flows_to: {self.flows_to}'

        flow_from_str: str = ''
        if self.flows_from != '':
            flow_from_str = f'\n  flow_from: {self.flows_from}'

        topic_up_str: str = ''
        if self.topic_up != '':
            topic_up_str = f'\n  topicup: {self.topic_up}'

        topic_down_str: str = ''
        if self.topic_down != '':
            topic_down_str = f'\n  topicdown: {self.topic_down}'

        topic_left_str: str = ''
        if self.topic_left != '':
            topic_left_str = f'\n  topicleft: {self.topic_left}'

        topic_right_str: str = ''
        if self.topic_right != '':
            topic_right_str = f'\n  topic_right: {self.topic_right}'

        alt_type_str: str = ''
        if self.alt_type != '':
            alt_type_str = f'\n  alt_type: {self.alt_type}'

        rank_str: str = ''
        if self.rank != -1:
            rank_str = f'\n  rank: {self.rank}'

        read_next_expr_str: str = ''
        if self.read_next_expr != '':
            read_next_expr_str = f'\n  read_next_expr: {self.read_next_expr}'

        true_msg_id_str: str = ''
        if self.true_msg_id > 0:
            true_msg_id_str = f'\n  true_msg_id: {self.true_msg_id}'

        false_msg_id_str: str = ''
        if self.false_msg_id > 0:
            false_msg_id_str = f'\n  false_msg_id: {self.false_msg_id}'

        units_str = ''
        if self.units is not None:
            units_str = (f'\n units: (scale: {self.units[0]}, type: {self.units[1]} '
                         f'step: {self.units[2]}, min: {self.units[3]}, '
                         f'max: {self.units[4]})')

        results: List[str] = []
        result: str = (f'\nOldTopicModel:  {name_str}'
                       f'{label_expr}'
                       f'{labeled_by_str}'
                       f'{alt_label_expr}'
                       f'{label_for_str}'
                       f'{info_expr}'
                       f'{description_str}'
                       f'{hint_text_str}'
                       f'{inner_topic_str}'
                       f'{outer_topic_str}'
                       f'{flow_from_str}'
                       f'{flows_to_str}'
                       f'{topic_up_str}'
                       f'{topic_down_str}'
                       f'{topic_left_str}'
                       f'{topic_right_str}'
                       f'{alt_type_str}'
                       f'{rank_str}'
                       f'{read_next_expr_str}'
                       f'{true_msg_id_str}'
                       f'{false_msg_id_str}'
                       f'{units_str}'

                       f'\n  # children: {len(self.children)}'
                       )
        results.append(result)

        for child in self.children:
            child: BaseParser
            results.append(str(child))
        results.append('END OLD_TOPIC_MODEL')

        return '\n'.join(results)
