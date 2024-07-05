# coding=utf-8

from typing import Callable, List

import xbmc
import xbmcgui

from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui.base_label_model import BaseLabelModel
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import control_elements, ControlType, Item, WindowType
from gui.element_parser import (BaseElementParser,
                                ElementHandler)
from gui.label_model import LabelModel
from gui.parse_group import ParseGroup
from gui.parse_group_list import ParseGroupList
from gui.parse_topic import ParseTopic
from gui.topic_model import TopicModel
from windows.ui_constants import AltCtrlType, UIConstants
from windows.window_state_monitor import WinDialog, WinDialogState, WindowStateMonitor

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class GroupListModel(BaseModel):

    _logger: BasicLogger = None
    item: Item = control_elements[ControlType.GROUP_LIST.name]

    def __init__(self, parent: BaseModel,
                 parsed_group_list: ParseGroupList) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        super().__init__(window_model=parent.window_model, parser=parsed_group_list)
        self.parent = parent
        self.previous_heading: PhraseList = PhraseList()
        self.previous_active_item: PhraseList = PhraseList()
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
        self.item_count: int = 0
        self.children: List[BaseModel] = []

        if parsed_group_list.topic is not None:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], TopicModel]
            model_handler = ElementHandler.get_model_handler(ParseTopic.item)
            self.topic = model_handler(self, parsed_group_list.topic)

        self.convert_children(parsed_group_list)

    def convert_children(self,
                         parsed_group_list: ParseGroupList) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_group_list: A ParseGroupList instance that
               needs to be convertd to a GroupListModel
        :return:
        """
        clz = type(self)

        clz._logger.debug(f'# parsed children: {len(parsed_group_list.get_children())}')
        parsers: List[BaseParser] = parsed_group_list.get_children()

        for parser in parsers:
            parser: BaseParser
            # clz._logger.debug(f'parser: {parser}')
            model_handler:  Callable[[BaseModel, BaseParser], BaseModel]
            # clz._logger.debug(f'About to create model from {parser.item}')
            model_handler = ElementHandler.get_model_handler(parser.item)
            child_model: BaseModel = model_handler(self, parser)
            self.children.append(child_model)

    def clear_history(self) -> None:
        clz = type(self)
        clz._logger.debug(f'clear_history {self.previous_heading}')
        self.previous_heading.clear()
        self.previous_active_item.clear()

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
            return True

        temp_phrases: PhraseList = PhraseList()
        success = self.voice_heading(temp_phrases)
        if not self.previous_heading.equal_text(temp_phrases):
            self.previous_heading.clear()
            self.previous_heading.extend(temp_phrases)
            phrases.extend(temp_phrases)

        # Voice either focused control, or label/text
        temp_phrases.clear()
        success = self.voice_active_item(temp_phrases)
        if not self.previous_active_item.equal_text(temp_phrases):
            self.previous_active_item.clear()
            self.previous_active_item.extend(temp_phrases)
            phrases.extend(temp_phrases)
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
            temp_phrases: PhraseList = PhraseList()
            orientation_str: str = self.get_list_orientation()
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
            success = self.voice_active_item(phrases)
            # Voice either next Topic down or focus item

            # success = self.voice_controlx(phrases)
            return success
        # TODO, incomplete
        return False
        '''
        # TODO, incomplete

    def voice_heading(self, phrases: PhraseList) -> bool:
        """
          Construct a heading appropriate for a Group List. Typical
          heading is "Vertical Group List. Engine Settings. 15 Items".
          Repeated voicings are suppressed.

        :param phrases: Any generated phrases is appended
        :return:
        """
        """
            TODO:  This is a BIG translation NO-NO.
            Constructing a phrase from other phrases:
            "Horizontal" "Group List". Need to rework after there is a clearer
            picture on how to handle.
        """
        clz = type(self)
        success: bool = False
        # Only return text which is not repetitious
        topic: TopicModel | None = self.topic
        if topic is None:
            return self.get_heading_without_topic(phrases)

        success: bool = self.voice_labeled_by(phrases)
        if not success:
            success = self.voice_topic_label_expr(phrases)
        orientation_str: str = self.get_list_orientation()
        control_name: str = ''
        control_name = self.get_control_name()
        phrases.append(Phrase(text=f'{orientation_str} {control_name}'))
        success = self.voice_number_of_items(phrases)
        return success

    def get_heading_without_topic(self, phrases: PhraseList) -> bool:
        phrases.append(Phrase(text='get_heading_without_text not implemented'))
        return True

    def get_list_orientation(self) -> str:
        msg_id: int = 32809
        if self.orientation_expr == UIConstants.VERTICAL:
            msg_id = 32808
        orientation: str = Messages.get_msg_by_id(msg_id=msg_id)
        return orientation

    def voice_topic_label_expr(self, phrases: PhraseList) -> bool:
        # Need to better define what this is
        success: bool = True
        if self.topic.label_expr != '':
            # TODO
            try:
                msg_id: int = int(self.topic.label_expr)
                text = Messages.get_msg_by_id(msg_id)
                if text != '':
                    phrase: Phrase = Phrase(text=text)
                    phrases.append(phrase)
            except ValueError as e:
                success = False
            if not success:
                phrase = Phrase(text=f'topic label_expr: {self.topic.label_expr}')
                phrases.append(phrase)
                success = True
        else:
            success = False
        return success

    def voice_number_of_items(self, phrases: PhraseList) -> bool:
        """
            Voice the number items and their orientation:
                "15 Horizontal Items"
        :param phrases:
        :return:
        """
        success: bool = True
        if hasattr(self, 'item_count'):
            visible_items: int = self.visible_item_count()
            if visible_items > 0:
                success = Messages.add_formatted_msg(phrases, Messages.UI_ITEMS,
                                                    f'{visible_items}')
        return success

    def voice_active_item(self, phrases: PhraseList) -> bool:
        """
        Only used when chain of Topics are not available from Window to
         focused/active control.

        :param phrases:
        :return:
        """
        clz = type(self)
        # Ignore voicing some non-focused text at the moment
        # focused_control_id: int = self.window_model.win_or_dialog.
        container_id = self.control_id
        if container_id > 0:
            #  position is zero-based
            pos_str: str = xbmc.getInfoLabel(f'Container({container_id}).Position')
            pos: int = self.get_non_negative_int(pos_str)
            pos += 1  # Convert to one-based item #
            clz._logger.debug(f'container position: {pos} container_id: {container_id}')
            current_item: str = xbmc.getInfoLabel(f'Container({container_id}).CurrentItem')
            clz._logger.debug(f'current_item: {current_item}')
            phrases.append(Phrase(text=f'Item: {pos}'))
            win: xbmcgui.Window = self.window_model.win_or_dialog
            focused_control: int = win.getFocusId()
            clz._logger.debug(f'Focused control: {focused_control}')
            return True

        # TODO START HERE!!
        return False


    def voice_controlx(self, phrases: PhraseList) -> bool:
        """
            Voice the UI type (value of 'alt_type' which is 'group list' by
            default)
            Next, voice alt_label.
            If no alt_label, voice any labeled_by
            if no labeled_by, voice label
            Voice info at some point
            Group Lists don't have a label to fall back on.

            Voice Hints only when requested. Voice AFTER any label
            What about extra voicing? label2, Info_labels?

            An alt-label has same syntax and symantics as a regular label:
            If int, then it is a message ID

            Message could be:
              An info expression
            Messages are influenced by:
              focusedlayouts
            can come from label, fadelabel and textbox
            more text can come from visibile children

            # of items, excluding parent folder:

            Container(id).NumItems  # Works for groupLists

            Container(id).CurrentItem # Might work for groupList
            Container(id).HasFocus(item_number) # Might work
            Container(id).Position # Works for groupList
        """
        clz = type(self)
        succes: bool = True
        phrase: Phrase
        topic: TopicModel = self.topic

        #  if topic.alt_type == AltCtrlType.BUTTON_LIST:

        if hasattr(self, 'item_count'):
            visible_items: int = self.visible_item_count()
            if visible_items > 0:
                text = Messages.get_formatted_msg(Messages.UI_ITEMS,
                                                  f'{visible_items}')
                phrase = Phrase(text)
                phrases.append(phrase)

        # Voice any item count. Each visible child control is an
        # item.

        current_item: int = 0
        for control in self.children:
            control_topic: TopicModel = None
            clz._logger.debug(f'child # {current_item} type: {type(control)}')
            # Voice "Item 5"
            if (control.topic is not None and control.control_id != -1
                    and control.is_visible()):
                current_item += 1
                text = Messages.get_formatted_msg(Messages.UI_ITEM,
                                                  f'{current_item}')
                phrase = Phrase(text)
                phrases.append(phrase)

            container_id: int = 3
            try:
                # Works for groupLists
                num_items: str
                num_items = xbmc.getInfoLabel(f'Container({container_id}).NumItems')
                clz._logger.debug(f'num_items: {num_items}')
            except Exception as e:
                clz._logger.exception(f'floof')

            curr_item: str = '1'
            # try:
            #    # Doesn't work for groupList
            #    curr_item: str
            #    curr_item = xbmc.getInfoLabel(f'Container({container_id}).CurrentItem')
            #    clz._logger.debug(f'current_item: {curr_item}')
            #except Exception as e:
            #    clz._logger.exception('boom boom')
            # try:
            #    # Does not Work
            #    it_num: str
            #    it_num = xbmc.getInfoLabel(f'Container({container_id}).HasFocus({curr_item})')
            #    clz._logger.debug(f'it_num: {it_num}')
            #except Exception as e:
            #    clz._logger.exception('boom boom')
            try:
                # Works for groupList
                pos: str = xbmc.getInfoLabel(f'Container(container_id).Position')
                clz._logger.debug(f'pos: {pos}')
            except Exception as e:
                clz._logger.exception('boom')

            # Add the control-type of a child
            if control.topic is not None:
                control_topic = control.topic
                success = control_topic.voice_alt_control_name(phrases)
                if not success:
                    alt_ctrl_type: AltCtrlType
                    alt_ctrl_type = (
                        AltCtrlType.alt_ctrl_type_for_ctrl_name(control.control_type.name))
                    success = AltCtrlType.get_message(alt_ctrl_type, phrases)

            # Can't voice control's label unless we have it's ID
            # Note, change to drill down into each child's
            # control's children to see which has a label

            if control.control_id != -1:
                if hasattr(topic.parent, 'label_expr'):
                    parent_model: BaseModel = topic.parent
                    parent_model: BaseLabelModel
                    success = (parent_model.get_label_text(), phrases)
            elif control_topic is not None:
                success = control_topic.voice_alt_label(phrases)

        clz._logger.debug(f'{phrases}')
        return True

    def get_label(self, phrases: PhraseList) -> bool:
        clz = type(self)
        success: bool = True
        if self.topic is not None:
            topic: TopicModel = self.topic
            success = topic.voice_alt_label(phrases)
        if not success:
            # TODO use topic get_alt_label
            pass
        return success

    def voice_item(self, phrases: PhraseList) -> bool:
        clz = type(self)
        success: bool = True
        phrase: Phrase
        topic: TopicModel = self.topic

        #  if topic.alt_type == AltCtrlType.BUTTON_LIST:

        if hasattr(self, 'item_count'):
            visible_items: int = self.visible_item_count()
            if visible_items > 0:
                text = Messages.get_formatted_msg(Messages.UI_ITEMS,
                                                  f'{visible_items}')
                phrase = Phrase(text)
                phrases.append(phrase)

        # Voice any item count. Each visible child control is an
        # item.

        current_item: int = 0
        for control in self.children:
            control_topic: TopicModel = None
            clz._logger.debug(f'child # {current_item} type: {type(control)}')

            # Voice "Item 5"
            if (control.topic is None and
                    control.is_visible()):
                current_item += 1
                text = Messages.get_formatted_msg(Messages.UI_ITEM,
                                                  f'{current_item}')
                phrase = Phrase(text)
                phrases.append(phrase)

            # Add the control-type of a child
            if control.topic is not None:
                control_topic = control.topic
                success = control_topic.voice_alt_control_name(phrases)
        return success

    def visible_item_count(self) -> int:
        clz = type(self)
        item_count: int = 0
        for child in self.children:
            # clz._logger.debug(f'child # {item_count} type: {type(child)}')
            if child.is_visible():
                item_count += 1

        return item_count

    def __repr__(self) -> str:
        clz = type(self)
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

        for child in self.children:
            child: BaseParser
            results.append(str(child))

        results.append('END GroupListModel')
        return '\n'.join(results)
