# coding=utf-8
from __future__ import annotations

from typing import Callable, List

import xbmc
import xbmcgui

from common.logger import BasicLogger, DEBUG_V, DEBUG_XV
from common.message_ids import MessageId
from common.messages import Messages
from common.phrases import Phrase
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlElement, Item
from gui.control_relationships import Topic
from gui.element_parser import (ElementHandler)
from gui.group_list_topic_model import GroupListTopicModel
from gui.no_topic_models import NoGroupListTopicModel
from gui.parser.parse_group_list import ParseGroupList
from gui.statements import Statements
from gui.topic_model import TopicModel
from utils import util
from windows.ui_constants import UIConstants
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class GroupListModel(BaseModel):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.GROUP_LIST]

    def __init__(self, parent: BaseModel,
                 parsed_group_list: ParseGroupList,
                 windialog_state: WinDialogState | None = None) -> None:
        clz = GroupListModel
        super().__init__(window_model=parent.window_model, parser=parsed_group_list,
                         windialog_state=windialog_state)
        # TODO: Super should take control_type as param
        # self.control_id: str = parsed_group_list.control_id
        self.default_control_id = parsed_group_list.default_control_id
        self.default_control_always: bool = parsed_group_list.default_control_always
        self.description: str = parsed_group_list.description
        self.visible_expr = parsed_group_list.visible_expr
        # self.enable_expr: str = parsed_group_list.enable_expr
        self.hint_text_expr: str = parsed_group_list.hint_text_expr
        self.alt_label_expr: str = parsed_group_list.alt_label_expr
        self.alt_type_expr: str = parsed_group_list.alt_type_expr
        self.info_expr: str = parsed_group_list.info_expr
        self.on_focus_expr: str = parsed_group_list.on_focus_expr
        # self.on_info_expr: str = ''
        self.on_unfocus_expr: str = parsed_group_list.on_unfocus_expr
        self.orientation_expr: str = parsed_group_list.orientation_expr
        self.page_control_id: int = parsed_group_list.page_control_id
        self.on_info_expr: str = parsed_group_list.on_info_expr
        self.scroll_time: int = parsed_group_list.scroll_time

        if parsed_group_list.topic is not None:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser],
            TopicModel | BaseModel]
           #  model_handler = ElementHandler.get_model_handler(ParseTopic.item)
            self.topic = GroupListTopicModel(self, parsed_group_list.topic)
        else:
            self.topic = NoGroupListTopicModel(self)

        self.convert_children(parsed_group_list)

    @property
    def supports_label(self) -> bool:
        # ControlCapabilities.LABEL
        return True

    @property
    def supports_label2(self) -> bool:
        #  ControlCapabilities.LABEL2
        return False

    @property
    def supports_container(self) -> bool:
        """
        Only a few controls are containers and even then, some don't fully
        support containers.

        Known Containers
            FixedList?, List, Panel, WrapList
        Known semi-containers
            GroupList
        :return:
        """
        return True

    @property
    def supports_orientation(self) -> bool:
        """
           List-type controls support orientation (vertical or horizontal)

           Known Containers
               FixedList?, List, Panel, WrapList
           Known semi-containers
               GroupList
           :return:
        """
        return True

    @property
    def supports_item_count(self) -> bool:
        """
           Indicates if the country supports item_count. List type containers/
           controls, such as GroupList do

           :return:
        """
        return True

    @property
    def supports_item_number(self) -> bool:
        """
            Indicates if the control supports reporting the current item number.
            The list control is not capable of these, although it supports
            item_count.
        :return:
        """
        return True

    @property
    def supports_item_number(self) -> bool:
        """
            Indicates if the control supports reporting the current item number.
            The list control is not capable of these, although it supports
            item_count.
        :return:
        """
        return True

    def convert_children(self,
                         parsed_group_list: ParseGroupList) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_group_list: A ParseGroupList instance that
               needs to be convertd to a GroupListModel
        :return:
        """
        #  clz = ForwardRef('GroupListModel')
        clz = type(self)

        clz._logger.debug(f'# parsed children: {len(parsed_group_list.get_children())}')
        parsers: List[BaseParser] = parsed_group_list.get_children()

        if parsed_group_list.topic is not None:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser],
                                    TopicModel | BaseModel]
            self.topic = GroupListTopicModel(self, parsed_group_list.topic)
        else:
            self.topic = NoGroupListTopicModel(self)

        count: int = 0
        for parser in parsers:
            parser: BaseParser
            # clz._logger.debug(f'parser: {parser}')
            model_handler:  Callable[[BaseModel, BaseParser, WinDialogState | None],
                                     BaseModel]
            model_handler = ElementHandler.get_model_handler(parser.item)
            child_model: BaseModel = model_handler(self, parser, None)
            # clz._logger.debug(f'About to add model from {parser.item} count: {count}')
            # clz._logger.debug(f'visible: {child_model.is_visible()} topic: '
            #                   f'{child_model.topic}')
            self.children.append(child_model)

    def voice_control(self, stmts: Statements) -> bool:
        """

        :param stmts: Statements to append to
        :return: True if anything appended to stmts, otherwise False

        Note that focus_changed = False can occur even when a value has changed.
        One example is when user users cursor to select different values in a
        slider, but never leaves the control's focus.
        """
        clz = GroupListModel

        # Update the state
        success: bool = True
        focus_changed: bool = self.windialog_state.focus_changed
        if not focus_changed:
            return True

        if self.control_id is not None:
            if not self.is_visible():
                return False
        if clz._logger.isEnabledFor(DEBUG_V):
            clz._logger.debug_v(f'control_id {self.control_id} visible')

        success = self.voice_control_heading(stmts)
        success = self.voice_active_item_value(stmts)
        return success

        '''
         if self.topic is not None:
            topic: TopicModel = self.topic
            clz._logger.debug(f'topic: {topic.alt_type}')
            """
                 TODO:  This is a BIG translation NO-NO.
                 Constructing a phrase from other phrases:
                   "Horizontal" "Group List". Need to rework after there is a clearer
                   picture on how to handle.
             """
            temp_phrases: PhraseList = PhraseList(check_expired=False)
            orientation_str: str = self.get_orientation()
            control_type: str
             control_type = topic.get_alt_control_name()
            if control_type == '':
                control_type = self.get_control_name()
            temp_phrases.append(Phrase(text=f'{orientation_str} {control_type}'))
            # TODO END

            success = self.voice_heading(temp_phrases)
            success = self.voice_number_of_items(temp_phrases)
            clz._logger.debug(f'temp: {temp_phrases}')
            clz._logger.debug(f'previous: {self.previous_heading}')
            different: bool = False
            if len(self.previous_heading) == len(temp_phrases):
                for p in range(0, len(self.previous_heading) - 1):
                    if self.previous_heading[p].text_equals(temp_phrases[p]):
                        different = True
                        break
            else:
                different = True
            if different:
                clz._logger.debug(f'different: {different}')
                self.previous_heading.clear()
                self.previous_heading.extend(temp_phrases)
                phrases.extend(temp_phrases)

            # Voice either focused control, or label/text
            success = self.voice_active_item_value(phrases)
            # Voice either next Topic down or focus item

            # success = self.voice_controlx(phrases)
            return success
        # TODO, incomplete
        return False
        '''
        # TODO, incomplete

    def voice_control_heading(self, stmts: Statements) -> bool:
        """
          Construct a heading appropriate for a Group List. Typical
          heading is "Vertical Group List. Engine Settings. 15 Items".
          Repeated voicings are suppressed.

        :param stmts: Any generated stmts is appended
        :return:
        """
        """
            TODO:  This is a BIG translation NO-NO.
            Constructing a phrase from other stmts:
            "Horizontal" "Group List". Need to rework after there is a clearer
            picture on how to handle.
        """
        clz = GroupListModel
        success: bool = False
        # Only return text which is not repetitious
        topic: TopicModel | None = self.topic
        if topic is None:
            return self.voice_heading_without_topic(stmts)

        success: bool = self.voice_labeled_by(stmts)
        if not success:
            success = self.voice_topic_label_expr(stmts)
        orientation_str: str = self.get_orientation()
        control_name: str = ''
        control_name = self.get_control_name()
        success = self.voice_number_of_items(stmts, control_name,
                                             orientation_str)
        return success

    def voice_heading_without_topic(self, stmts: Statements) -> bool:
        stmts.last.phrases.append(Phrase(text='get_heading_without_text not implemented',
                                         check_expired=False))
        return True

    def get_orientation(self) -> str:
        msg_id: int = 32809
        if self.orientation_expr == UIConstants.VERTICAL:
            msg_id = 32808
        orientation: str = Messages.get_msg_by_id(msg_id=msg_id)
        return orientation

    def voice_topic_label_expr(self, stmts: Statements) -> bool:
        # Need to better define what this is
        success: bool = True
        if self.topic.label_expr != '':
            # TODO
            try:
                msg_id: int = int(self.topic.label_expr)
                text = Messages.get_msg_by_id(msg_id)
                if text != '':
                    phrase: Phrase = Phrase(text=text, check_expired=False)
                    stmts.last.phrases.append(phrase)
            except ValueError as e:
                success = False
            if not success:
                phrase = Phrase(text=f'topic label_expr: {self.topic.label_expr}',
                                check_expired=False)
                stmts.last.phrases.append(phrase)
                success = True
        else:
            success = False
        return success

    def voice_active_item_value(self, stmts: Statements) -> bool:
        """
        If the control that 'owns' the active item (usually the one with focus)
        is known, or it's topic, then have them voice it (with preference for
        the topic). Otherwise, voice it here.

        :param stmts:
        :return:
        """
        clz = GroupListModel
        # Ignore voicing some non-focused text at the moment
        if not self.focus_changed:
            return False

        focused_control_id: int = self.windialog_state.focus_id
        model: BaseModel = self.window_struct.get_model_for_control_id(focused_control_id)
        control_id: int
        topic: TopicModel
        model, topic = self.window_struct.get_control_and_topic_for_id(focused_control_id)
        if topic is not None and focused_control_id != self.control_id:
            return False  # Assume that the topic is on the stack to evaluate this
        if model is not None and focused_control_id != self.control_id:
            return False  # Assume that the control's model will be called  FUTURE

        container_id = self.control_id
        if container_id > 0:
            #  position is zero-based
            # pos_str: str = xbmc.getInfoLabel(f'Container({container_id}).Position')
            # pos: int = util.get_non_negative_int(pos_str)
            # pos += 1  # Convert to one-based item #
            # if clz._logger.isEnabledFor(DEBUG_XV):
            #     clz._logger.debug_xv(f'container position: {pos} container_id:'
            #                          f' {container_id}')
            #
            #  TODO: Get the control and value using another call that gets it from
            #     the control. Here we are getting it from the container without giving
            #     the control the ability to customize

            num_items: str = xbmc.getInfoLabel(f'Container({container_id}).NumItems')
            item_num: str = xbmc.getInfoLabel(f'Container({container_id}).CurrentItem')
            content: str = xbmc.getInfoLabel(f'Container({container_id}).Content')
            # value: str = xbmc.getInfoLabel(
            #         f'Container(container_id).ListItemPosition(0).Label')
            value: str = xbmc.getInfoLabel('ListItem.Label')
            control_type: ControlElement = ControlElement.UNKNOWN
            if clz._logger.isEnabledFor(DEBUG_V):
                clz._logger.debug_v(f'item_num: {item_num} control_type: {control_type} '
                                    f'content: {content} value: {value} '
                                    f'container_id: {container_id}')
            text: str = (MessageId.CONTAINER_ITEM_NUMBER_CONTROL_AND_VALUE
                         .get_formatted_msg(f'{item_num}', control_type, ''))
            phrase: Phrase = Phrase(text=text, check_expired=False)
            stmts.last.phrases.append(phrase)
            if clz._logger.isEnabledFor(DEBUG_V):
                clz._logger.debug_v(f'phrase: {phrase}')

            win: xbmcgui.Window = self.windialog_state.window_instance
            focused_control: int = win.getFocusId()
            if clz._logger.isEnabledFor(DEBUG_XV):
                clz._logger.debug_xv(f'Focused control: {focused_control}')
            return True

        # TODO START HERE!!
        return False

    def get_label(self, stmts: Statements) -> bool:
        clz = GroupListModel
        success: bool = True
        if self.topic is not None:
            topic: TopicModel = self.topic
            success = topic.voice_alt_label(stmts)
        if not success:
            # TODO use topic get_alt_label
            pass
        return success

    def __repr__(self) -> str:
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False) -> str:
        clz = GroupListModel
        # Remove:  has_path, label, scroll, action
        # Verify removal: onfocus, onup, enable etc.

        alt_label_str = ''
        if self.alt_label_expr != '':
            alt_label_str = f'\n  alt_label: {self.alt_label_expr}'

        alt_type_str = ''
        if self.alt_type_expr != '':
            alt_type_str = f' alt_type: {self.alt_type_expr}'

        if self.on_focus_expr is not None and (len(self.on_focus_expr) > 0):
            on_focus_expr: str = f'\n  on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr is not None and (len(self.on_unfocus_expr) > 0):
            on_unfocus_expr: str = f'\n  on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''
        default_control_id: str = ''
        if self.default_control_id >= 0:
            default_control_id = f'\n  default_control: {self.default_control_id}'
        default_control_always: str = ''
        if self.default_control_always:
            default_control_always = (f'\n  default_control_always: '
                                      f'{self.default_control_always}')

        description_str: str = ''
        if self.description != '':
            description_str = f'\n  description: {self.description}'

        scroll_time_str = ''
        if self.scroll_time != 200:
            scroll_time_str: str = f'\n  scroll_time; {self.scroll_time} ms'

        visible_expr_str: str = ''
        if self.visible_expr != '':
            visible_expr_str = f'\n  visible: {self.visible_expr}'

        # self.enable_expr: str = parsed_group_list.enable_expr

        hint_text_expr_str: str = ''
        if self.hint_text_expr != '':
            hint_text_expr_str = '\n  hint_text: {self.hint_text_expr}'

        on_info_expr_str: str = ''
        if self.on_info_expr != '':
            on_info_expr_str = f'\n  on_info_expr: {self.on_info_expr}'

        page_control_id_str: str = ''
        if self.page_control_id >= 0:
            page_control_id_str = f'\n  page_control_id: {self.page_control_id}'

        orientation_expr: str = ' orientation: vertical'
        if self.orientation_expr != 'vertical':
            orientaton_expr = f'\n  orientation: {self.orientation_expr}'

        info_expr: str = ''
        if len(self.info_expr) > 0:
            info_expr = f' info_expr: {self.info_expr}'
        selected_expr: str = ''

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        results: List[str] = []
        result: str = (f'\nGroupListModel type: {self.control_type} '
                       f'id: {self.control_id}{alt_label_str}{alt_type_str}'
                       f'{default_control_id}{default_control_always}'
                       f'{page_control_id_str}'
                       f'{description_str}'
                       f'{hint_text_expr_str}'
                       f'{visible_expr_str}'
                       f'{selected_expr}'
                       f'{on_focus_expr}{on_unfocus_expr}'
                       f'{info_expr}{orientation_expr}'
                       f'{on_info_expr_str}'
                       f'{scroll_time_str}'
                       f'{topic_str}'
                       f'\n  #children: {len(self.children)}'
                       )
        results.append(result)
        if include_children:
            for child in self.children:
                child: BaseModel
                result: str = child.to_string(include_children=include_children)
                results.append(result)
        results.append('END GroupListModel')
        return '\n'.join(results)
