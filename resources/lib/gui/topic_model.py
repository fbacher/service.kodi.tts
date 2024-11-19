# coding=utf-8

"""
Provides the bulk of the work for voicing topics (with a lot of work coming from the
non-topic models, which are parents of Toopics). The control-specific topic modules
only have code specialized for their nature.

The basic idea is that a 'topic' represents a description of a viewable thing.
For example, a Window generally has a title, help text, etc. A list of items
similarly has a list type, a title, # of items in the list, help text, etc.
Each of the items in the list has an item number for it's position in the list,
an item type (a button, slider, etc.), a label and usually a value.

Funnily enough, topics more or less map into UI controls. With this model we can
discover the text that we want to voice for each topic, beginning with the Window
and decending through every control in the path to the one with focus. At this
point you decide how much to voice. You don't need to voice the name of the window
every time anything is voiced in the window. Nor do you have to voice the table,
etc.. Instead, begining with the Window topic, you compare each with the
previously voiced text. If a difference is found, you revoice that topic and
every remaining topic until the focused topic is reached.

This simple rule works even if the focus changes. You only voice what changes.
"""
from logging import DEBUG
from typing import Callable, Final, ForwardRef, List

import xbmc

from common.logger import BasicLogger, DEBUG_XV, DEBUG_V, DISABLED
from common.message_ids import MessageId, MessageUtils
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui import BaseParser
from gui.base_model import BaseModel
from gui.base_tags import (BaseAttributeType as BAT, control_elements, ControlElement, Item,
                           Requires,
                           TopicType, ValueFromType, ValueUnits)
from gui.base_topic_model import BaseTopicModel
from gui.element_parser import ElementHandler
from gui.gui_globals import GuiGlobals
from gui.interfaces import IWindowStructure
from gui.parser.parse_topic import ParseTopic
from gui.statements import Statement, Statements, StatementType
from windows.window_state_monitor import WinDialogState

MY_LOGGER = BasicLogger.get_logger(__name__)


class TopicModel(BaseTopicModel):
    item: Item = control_elements[BAT.TOPIC]

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        super().__init__(parent=parent, parsed_topic=parsed_topic,
                         rank=parsed_topic.rank)
        clz = TopicModel
        # Glue this node to it's parent BaseModel
        self._control_id: Final[int] = parent.control_id
        self.alt_label_expr: Final[str] = parsed_topic.alt_label_expr
        # if self.alt_label_expr == '':
        #     AltCtrlType.get_ctrl_type_for_control(self.parent.control_type)
        self.container_topic: str = parsed_topic.container_topic
        self._container_topic: TopicModel | None = None

        tmp_topic_type: TopicType = parsed_topic.topic_type

        # Don't voice Groups which have no content

        if (self.parent.control_type in (ControlElement.GROUP, ControlElement.LABEL_CONTROL)
                and tmp_topic_type == TopicType.DEFAULT):
            tmp_topic_type = TopicType.NONE
        self.topic_type: Final[TopicType] = tmp_topic_type
        if MY_LOGGER.isEnabledFor(DISABLED):
            MY_LOGGER.debug(f'name: {self.name} orig topic_type: {tmp_topic_type} '
                              f'topic_type: {self.topic_type}')
        #  self.topic_heading: Final[str] = parsed_topic.topic_heading
        self.heading_label: Final[str] = parsed_topic.heading_label
        self.heading_labeled_by: Final[str] = parsed_topic.heading_labeled_by
        self.heading_next: Final[str] = parsed_topic.heading_next
        self._heading_next: TopicModel | None = None
        #  TODO- Revisit this ugly alt_type
        self.alt_type: Final[str] = parsed_topic.alt_type
        # MY_LOGGER.debug(f'Just set alt_type from parsed_topic: {self.alt_type}')
        tmp_msg_id: int = -1
        if parsed_topic.true_msg_id is not None:
            tmp_msg_id = parsed_topic.true_msg_id
        self.true_msg_id: Final[int] = tmp_msg_id
        tmp_false_msg_id: int = -1
        if parsed_topic.false_msg_id is not None:
            tmp_false_msg_id = parsed_topic.false_msg_id
        self.false_msg_id: Final[int] = tmp_false_msg_id

        MY_LOGGER.debug(f'true_msg_id: {self.true_msg_id} '
                        f'false_msg_id: {self.false_msg_id}')
        #  TODO: Units looks weird. Probably should be a pattern to format with.

        self.units: Final[ValueUnits] = parsed_topic.units
        self.requires: List[Requires.TOPIC_UNITS] = []  # future
        if self.units is not None:
            self.requires.append(Requires.TOPIC_UNITS)
        self.value_from: Final[ValueFromType] = parsed_topic.value_from
        self.value_format: Final[str] = parsed_topic.value_format
        self.children: List[BaseModel] = []
        self._window_struct: IWindowStructure = None

        # Type provides a means to voice what kind of control this is other than just
        # the Kodi standard controls, group, groupList, etc.

        self.type: Final[str] = parsed_topic.type

        self.attributes_with_values: List[str] = clz.item.attributes_with_values
        self.attributes: List[str] = clz.item.attributes
        self.convert(parsed_topic)
        #  self._container_topic: TopicModel | None = None  # Can not initialize in init

    @property
    def control_type(self) -> ControlElement:
        return self.parent.control_type

    @property
    def parent(self) -> BaseModel:
        return self._parent

    def convert(self, parsed_topic: ParseTopic) -> None:
        """
            Convert Parsed elements, etc. to a model.

        :param parsed_topic: A Topic instance that
               needs to be converted to a TopicModel
        :return:
        """
        clz = TopicModel
        for child in parsed_topic.children:
            child: BaseParser
            try:
                model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
                model_handler = ElementHandler.get_model_handler(child.item)
                child_model: BaseModel = model_handler(self, child)
                self.children.append(child_model)
            except Exception as e:
                MY_LOGGER.debug(f'self: {self} child: {child}')
                MY_LOGGER.exception(f'{e}')

        #  MY_LOGGER.debug(f'parent: {type(self.parent)}')
        self.parent.topic = self
        #  MY_LOGGER.debug(f'parent topic: {self.parent.topic.name}')

    @property
    def name(self) -> str:
        return super().name

    @property
    def supports_label(self) -> bool:
        """
            A control which getLabel or at least Control.GetLabel({control_id})
            work.
        :return:
        """
        # ControlCapabilities.LABEL

        return self.parent.supports_label

    @property
    def supports_label2(self) -> bool:
        """
         A control which getLabel2 or at least Control.GetLabel({control_id}.index(1))
            work.
        :return:
        """
        #  ControlCapabilities.LABEL2

        return self.parent.supports_label2

    @property
    def supports_value(self) -> bool:
        """
        Some controls, such as a button, radio button or label are unable to provide
         a value.
        I.E. it can't give any indication of what happens when pressed. If the
        topic for this control or another provides flows_from/flows_to or similar,
        then a value can be determined that way, but not using this method.
        :return:
        """
        return self.parent.supports_value

    @property
    def supports_boolean_value(self) -> bool:
        """
        Some controls, such as RadioButton, support a boolean value
        (on/off, disabled/enabled, True/False, etc.). Such controls
        Use the value "(*)" to indicate True and "( )" to indicate False.
        :return:
        """
        return self.parent.supports_boolean_value

    @property
    def true_value(self) -> str:
        clz = TopicModel
        MY_LOGGER.debug(f'In true_value msg_id: {self.true_msg_id}')
        if not self.supports_boolean_value:
            raise ValueError('Does not support boolean value')
        if self.true_msg_id == -1:
            raise ValueError('Invalid message id: {self.true_msg_id}')
        true_msg: str = MessageUtils.get_msg(self.true_msg_id)
        MY_LOGGER.debug(f'true_msg: {true_msg}')
        return true_msg

    @property
    def false_value(self) -> str:
        if not self.supports_boolean_value:
            raise ValueError('Does not support boolean value')
        if self.false_msg_id == -1:
            raise ValueError(f'Invalid message id: {self.false_msg_id}')
        false_msg: str = MessageUtils.get_msg(self.false_msg_id)
        return false_msg

    @property
    def supports_heading_label(self) -> bool:
        """
            A control with a label that is being used as a heading
        :return:
        """
        # ControlCapabilities.LABEL

        return self.parent.supports_heading_label

    @property
    def supports_label_value(self) -> bool:
        """
            A control with a label that is frequently used as a value
        :return:
        """
        # ControlCapabilities.LABEL

        return self.parent.supports_label_value

    @property
    def supports_label2_value(self) -> bool:
        """
         A control that supports label2 that is frequently used as a value.

        :return:
        """
        #  ControlCapabilities.LABEL2

        return self.parent.supports_label2_value

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
        return self.parent.supports_container

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
        return self.parent.supports_orientation

    @property
    def supports_item_count(self) -> bool:
        """
           Indicates if the control supports item_count. List type containers/
           controls, such as GroupList do.

           :return:
        """
        return self.parent.supports_item_count

    @property
    def supports_item_number(self) -> bool:
        """
            Indicates if the control supports reporting the current item number.
            The list control is not capable of these, although it supports
            item_count.
        :return:
        """
        return self.parent.supports_item_number

    @property
    def supports_change_without_focus_change(self) -> bool:
        """
            Indicates if the control supports changes that can occur without
            a change in Focus. Slider is an example. User modifies value without
            leaving the container. Further, you only want to voice the value,
            not the control name, etc.
        :return:
        """
        return False

    @property
    def supports_item_collection(self) -> bool:
        """
        Indicates that this control contains multiple items.
        Used to influence how the heading for this control is read.

        The heading for a simple object, such as a button is read:
          [Item #] Control_heading(s) Control_type Control_Value
          "[item 5] Button Enabled"
        While a collection is read:
          Control_heading(s) [Orientation] control_type [# Items]
          "Basic Settings. Vertical Group List 5 Items"

        :return:
        """
        return False

    @property
    def control_id(self) -> int:
        clz = TopicModel
        #  MY_LOGGER.debug(f'self: {self.__class__.__name__} '
        #                   f'control_id: {self._control_id}')
        return self._control_id

    def is_visible(self) -> bool:
        return self.parent.is_visible()

    def voice_topic_hint(self, stmts: Statements) -> bool:
        clz = TopicModel
        # if self.hint_text_expr == '':
        #     return False
        success: bool = False
        hint_text_id: int = -1
        try:
            if self.hint_text_expr.isdigit():
                hint_text_id = int(self.hint_text_expr)
                text = MessageUtils.get_msg_by_id(hint_text_id)
            else:
                text = self.hint_text_expr
            if text == "":
                success = False
            else:
                phrase: Phrase = Phrase(text=text, check_expired=False)
                #  MY_LOGGER.debug(f'hint_text: {self.hint_text_expr} {hint_text_id}'
                #                    f' {text}')
                phrase.set_pre_pause(phrase.PAUSE_PRE_HINT)
                phrase.set_post_pause(phrase.PAUSE_POST_HINT)
                phrases: PhraseList = PhraseList(check_expired=False)
                phrases.append(phrase)
                stmts.append(Statement(phrases, StatementType.HINT_TEXT))
                #  MY_LOGGER.debug(f'{stmts}')
                success = True
        except ValueError as e:
            # Try as an Info Label,or such
            success = False
        return success

    def get_topic_name(self) -> Phrase:
        return Phrase(text=self.name, check_expired=False)

    def voice_control(self, stmts: Statements) -> bool:
        """

        :param stmts: Statements to append to
        :return: True if anything appended to phrases, otherwise False
        """
        """
        Note that focus_changed = False can occur even when a value has changed.
        One example is when user uses cursor to select different values in a
        slider, but never leaves the control's focus.

        Only voice when window/control is newly changed
        TODO: improve by taking into account when window voicing fails to occur
              such as when there is an interruption (focus change occurs before this
              window info is announced, causing the window not being announced when
              focus change announced).

            A heading consists of several parts:
           Heading label(s)
           orientation of control (for lists, etc)
           # of items in control (for lists, containers, etc.)

        value/values are NOT part of the heading and voiced in
        voice_topic_value.

        A Basic Window Heading is:

        <topic name="window_header" rank="1">
          <topic_type>heading</topic_type>
          <heading_label>1</heading_label>
          <hint_text>33100</hint_text>
          <alt_type>DIALOG</alt_type>
          <inner_topic>engine_settings</inner_topic>
          <topic_left></topic_left>
          <topic_right></topic_right>
          <topic_up>header</topic_up>
          <topic_down>header_group</topic_down>
        </topic>

        The name is up to you. The name can be referenced by other topics.
        A topic_type of heading indicates this topic has heading information
        in it (TODO: remove topic-type heading, redundant).

        labeled_by indicates where to get the heading's label from
        alt_type specifies an alternate control type to voice. More alternate
        control types to choose from to provide better information for the listener.
        hint_text is read when requested by the user. This is in addition to the
        other text. It is read after the normal text is read.

        To successfully voice the needed topics for an arbitrary control, a
        chain of topics linked by outer_topic from the focused control to the
        window heading must exist. The outer_topic is is_required (except for the
        root topic for the window).

        TODO: Remove inner_topic

        topic_up, etc. are reserved for navigating controls that do not receive
        focus, or that do not have control_ids.

        Other, advanced topic elements:
        heading_next is used when more than one heading label needs to be read.
        Perhaps you
        have a Title and sub-title, each with its own label. By defining the
        topic for title with a heading_next element referencing the sub-title's id,
        the subtitle gets read after the title. A topic can have a single
        heading_next, but a chain of topics can be linked with heading_next fields.

        read_next is similar to heading_next, except used for voicing labels
        in a non-heading context.

        labeled_by References a label to voice for this control. Typically used
        when the control does not have a label and the label, being a label,
        never gets focus so it can not otherwise be found

        label_for  Marks a control as being the label for another control
        Typically the control needing this label also has a LABELED_BY
        reference back to this topic

        flows_from Similar to labeled_by. Sometimes a control gets its value
        from another control, such as when you have a slider, which has no label,
        has to go through some tricks to get its value from some other, perhaps
        hidden or invisible label.

        flows_to See flows_from. Indicates that this control sends its value to
        another (which is marked with flows_from, refering to this control)

        alt_label specifies an alternate label to use that may be more
        # accessible. ALT_LABEL may be an int, which is interpreted as a
        # message id. (To use another control as a label, use LABELED_BY
        # instead.) ALT_LABEL may be a string, in which case it is
        # interpreted as an INFO_LABEL or similar.

    NAME = 'name' key that topics used to reference one another

        hint_text supplies additional text that may clarify what the control
        # is for, or perhaps your options, etc. Format is the same as ALT_LABEL

        true_msg_id For boolean controls: RadioButton. By default, 'Enabled' is
        # substituted for '(*)' from the ListItem value of the control

        false-msg_id For binary controls: RadioButton. By default, 'Disabled' is
        # substituted for '( )' from the ListItem value of the control
        # READ_NEXT is typically used for non-focusable items. It indicates that
        # more than one thing needs to be read for, say, a window header.

        UNITS = 'units'  # complex string value
        """
        clz = TopicModel
        #  MY_LOGGER.debug(f'on entry to voice_control: {phrases}')
        # Update the state
        focus_changed: bool = self.windialog_state.focus_changed
        if self.control_id is not None and self.control_id > 0:
            if not self.is_visible():
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'not visible, '
                                        f'control_id: {self.control_id}')
                return False
        if MY_LOGGER.isEnabledFor(DEBUG_XV):  # More detail
            MY_LOGGER.debug_xv(f'visible control_id {self.control_id} '
                                 f'focus_changed: {focus_changed} '
                                 f'focus_id: {self.windialog_state.focus_id}\n'
                                 f'  {self}')
        elif MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'visible control_id {self.control_id} '
                                f'focus_changed: {focus_changed} '
                                f'focus_id: {self.windialog_state.focus_id}\n'
                                f'  {self.name}')
        '''
            One problem with voicing without a focus change is that
            the code has to evaluate almost every poll request (about
            10/second. This has the side effect of increasing the probability
            that previous text gets stomped on. For example, TTS 
            starts in voicing only on focus change. The focus changes
            and you start to voice whatever controls have changed. 
            If the control that you are voicing is one that can change
            without focus, then 1/10th of a second later, this code is
            called again, long before the initial heading info is voiced.
            If there is any difference in the text generated on this
            call than when voicing the heading, then the voicing of the
            heading will be aborted mid-stream and the new text, 
            which will be missing everything that is in common with this
            new text (up until the first change). Currently there is no 
            way to tell if something being voiced has completed voicing.
            
            To improve on the situation the code tries to reduce what is
            voiced and to focus on what has changed.
        '''
        success: bool = True
        if focus_changed:
            success = self.voice_item_number(stmts)
            success = self.voice_topic_heading(stmts)
            success = self.voice_topic_value(stmts)
            success = self.voice_topic_hint(stmts)
        elif self.supports_change_without_focus_change:
            # Control with focus, most likely has value
            if self.windialog_state.focus_id == self.control_id:
                #  MY_LOGGER.debug(f'Calling voice_working_value')
                # success = self.voice_item_number(stmts)
                # success = self.voice_topic_heading(stmts)
                #  success = self.voice_topic_value(stmts)
                success = self.voice_working_value(stmts)
                # success = self.voice_topic_hint(stmts)
                #  stmts.mark_as_silent(stmt_filter=(StatementType.NORMAL,),
                #                       interrupt=False)
            else:
                success = self.voice_item_number(stmts)
                success = self.voice_topic_heading(stmts)
                success = self.voice_topic_value(stmts)
                success = self.voice_topic_hint(stmts)
        else:
            success = self.voice_item_number(stmts)
            success = self.voice_topic_heading(stmts)
            success = self.voice_topic_value(stmts)
            success = self.voice_topic_hint(stmts)
        return success

    def voice_topic_heading(self, stmts: Statements) -> bool:
        """
            TODO: Reword and breakup for different methods.
                  This method ONLY worries about the topic's heading

        Generate the speech for header that this control may have.
        A header for a window or control is only voiced when the focus
        changes to that window or control, or when explicitly re-voiced.

        For example, a GroupList logically has a heading. When the heading is
        read, it should also include the orientation (horizontal/vertical) and
        the number of items in the list.

        The heading is designated by the Topic. Without a Topic an attempt
        is made to guess what to voice. via BaseModel.voice_control_heading

        The heading does NOT include the control's value (unless the control is
        a label).  TODO: Fix

          TODO: ? The header's topic must be marked with topic_type heading

        See Voice_control which is responsible for voicing (almost)
        everything about a control. It calls voice_heading to do its part.
        Prior to calling voice_heading, any item# and controltype info is
        voiced.

        A heading consists of several parts:
           Heading label(s)
           orientation of control (for lists, etc)
           # of items in control (for lists, containers, etc.)

        value/values are NOT part of the heading and voiced in
        voice_topic_value.

        For group controls:
            The control's heading(s) are voiced

        The control's name, orientation and # of items in the control
        are voiced first (see voice_control_name_heading).

        For non-group controls:
            Finally, the control's heading(s) are voiced

        The rational for voicing heading in a different order depending upon
        the control type is that Grouping controls tend to start a new
        section and frequently any label for the group is above the group.

        However, for a normal control, say a Button, it seems that any
        heading is more like a simple title for the button and it seems
        more logical (to me, today) to voice it after the control type.

        Example. A GroupList contains multiple buttons, sliders, etc.
        The first item is a button. Navigating to it would result in:
            "Basic Settings. GroupList five items."
            "Button. Engine. value Google TTS"

        To successfully voice the needed topics for an arbitrary control, a
        chain of topics linked by outer_topic from the focused control to the
        window heading must exist. The outer_topic is is_required (except for the
        root topic for the window).

        Other, advanced topic elements:
        heading_next is used when more than one heading label needs to be read.
        Perhaps you
        have a Title and sub-title, each with its own label. By defining the
        topic for title with a heading_next element referencing the sub-title's id,
        the subtitle gets read after the title. A topic can have a single
        heading_next, but a chain of topics can be linked with heading_next fields.

        read_next is similar to heading_next, except used for voicing labels
        in a non-heading context.

        labeled_by References a label to voice for this control. Typically used
        when the control does not have a label and the label, being a label,
        never gets focus so it can not otherwise be found

        label_for  Marks a control as being the label for another control
        Typically the control needing this label also has a LABELED_BY
        reference back to this topic

        flows_from Similar to labeled_by. Sometimes a control gets its value
        from another control, such as when you have a slider, which has no label,
        has to go through some tricks to get its value from some other, perhaps
        hidden or invisible label.

        flows_to See flows_from. Indicates that this control sends its value to
        another (which is marked with flows_from, refering to this control)

        alt_label specifies an alternate label to use that may be more
        # accessible. ALT_LABEL may be an int, which is interpreted as a
        # message id. (To use another control as a label, use LABELED_BY
        # instead.) ALT_LABEL may be a string, in which case it is
        # interpreted as an INFO_LABEL or similar.

    NAME = 'name' key that topics used to reference one another

        hint_text supplies additional text that may clarify what the control
        # is for, or perhaps your options, etc. Format is the same as ALT_LABEL

        true_msg_id For boolean controls: RadioButton. By default, 'Enabled' is
        # substituted for '(*)' from the ListItem value of the control

        false-msg_id For binary controls: RadioButton. By default, 'Disabled' is
        # substituted for '( )' from the ListItem value of the control
        # READ_NEXT is typically used for non-focusable items. It indicates that
        # more than one thing needs to be read for, say, a window header.

        UNITS = 'units'  # complex string value

        :param stmts:
        :return:
        """
        clz = TopicModel
        success: bool = False

        # Don't voice anything for a control-type marked NONE
        if self.topic_type == TopicType.NONE:
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'Not voicing topic: {self.name} due to'
                                   f' TopicType.NONE')
            return False
        if MY_LOGGER.isEnabledFor(DEBUG_XV) and not stmts.is_empty:
            MY_LOGGER.debug_xv(f'on entry to voice_topic_heading: {stmts}')
        '''
             The heading for a simple object, such as a button is read:
              [Item #] Control_heading(s) Control_type Control_Value
              "[item 5] Button Enabled"
            While a collection is read:
              Control_heading(s) [Orientation] control_type [# Items]
              "Basic Settings. Vertical Group List 5 Items"
          '''
        if self.supports_item_collection:
            # Voice the heading of the collection first
            success = self.voice_heading_label(stmts)

        control_name: str = self.get_best_control_name()
        orientation: str = ''
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug(f'topic: {self.name} control_name: {control_name}')
        if self.supports_orientation:
            orientation: str = self.get_orientation()

        visible_item_count: int = -1
        if self.supports_item_count:
            visible_item_count = self.visible_item_count()

        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'control_id: {self.control_id} '
                              f'control_name: {control_name} '
                              f'orientation: {orientation} '
                              f'items: {visible_item_count}')
        success = self.voice_control_name_heading(stmts, control_name,
                                                  orientation, visible_item_count)

        #  Finally, voice the control's heading label(s)

        #  MY_LOGGER.debug(f'from voice_control_name_heading {stmts}')
        if not self.supports_item_collection:
            # For regular controls, voice the heading after any control name
            # and item number
            success = self.voice_heading_label(stmts)
        MY_LOGGER.debug(f'Exiting voice_topic_heading: {stmts}')
        return success

    def voice_control_name_heading(self, stmts: Statements, control_name: str,
                                   orientation: str, visible_item_count: int) -> bool:
        """
        Voices a formatted heading containing a control's: name,
        orientation and item-count, as appropriate. All are translated.

        :param stmts:
        :param control_name:
        :param orientation: Translated string for orientation or an empty
                            string if the control does not support orientation
        :param visible_item_count: Non-positive values indicate item_count is
                                   not supported by control
        :return:
        """
        clz = TopicModel
        text: str = ''
        has_items: bool = visible_item_count > 0
        has_orientation = orientation != ''

        if has_items and has_orientation:
            text = MessageId.HEADING_WITH_ORIENTATION_AND_ITEMS.get_formatted_msg(
                    orientation,
                    control_name,
                    f'{visible_item_count}')
        elif has_items:
            text = MessageId.HEADING_WITH_ITEMS.get_formatted_msg(
                    control_name,
                    f'{visible_item_count}')
        elif has_orientation:
            text = MessageId.HEADING_WITH_ORIENTATION.get_formatted_msg(
                    orientation,
                    control_name)
        else:
            text = control_name
        if text != '':
            stmt: Statement = Statement(PhraseList.create(texts=text,
                                                          check_expired=False))
            stmts.append(stmt)
            return True
        return False

    def voice_heading_label(self, stmts: Statements,
                            chain: bool = True) -> bool:
        """
        Voices a label for this topic's heading. label information is contained
        in heading_label and heading_next.

        :param stmts: Append any voicings to stmts
        :param chain: If True and self.heading_next is not empty,
                      then call voice_chained_headings after voicing the label
        :return: True if at least one phrase was appended. False if no phrases
                 added.

        Attempts to voice from multiple sources until succes, or there are
        no more sources. The sources are, in order: heading_label,
        heading_labeled_by, the control's own label.

        NOTE: chain is currently ignored.

         If chain is True, then call voice_chained_headings to voice sub-headings,
         etc.

        If heading_label is an int, then it is a message id. Otherwise, it is
        interpreted as an infolabel.

        If heading_labeled_by is an int, then it is assumed to be a
        control_id.  If a str, then it is assumed to be a topic_id
        (name).
        If a topic_id is referenced, then voice the heading_label
        from that topic.

        If neither heading_label nor heading_labeled_by are voiced, then
        if the control is marked supports_heading_label then one of
        the control's "normal" labels are read.
        """
        clz = TopicModel
        success: bool = False

        # Use heading_label, if available
        if self.heading_label != '':
            if self.heading_label.isdigit():
                msg_id: int = int(self.heading_label)
                text: str = MessageUtils.get_msg(msg_id)
                if text != '':
                    success = True
                    phrases: PhraseList = PhraseList.create(texts=text,
                                                            check_expired=False)
                    stmts.append(Statement(phrases))
            else:
                # TODO: START HERE. SHOULD NOT VOICE_INFO_LABEL
                success = self.voice_info_label(stmts, self.heading_label)
            if chain:
                self.voice_chained_headings(stmts)

            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'heading_label: {self.heading_label} {stmts}')
        # Otherwise, read any heading_labeled_by
        elif self.heading_labeled_by != '':
            success = self.voice_heading_labeled_by(stmts, chain)

        """
           Be careful voicing standard labels because it can lead to duplicate
           voicings. 

           You can not tell if a label control's single displayed string is 
           a heading, giving direction or a value. For this reason labels are not
           processed here unless they explicitly use heading_label or heading_labeled_by.

           Other controls, such as Button also have only one label to display, but 
           is almost certainly for an instruction on what the button is for. Other
           measures must be taken to read the value of the button, likely through 
           flows_to, etc., but that is the responsibility of other code.
         """
        if not success and self.supports_heading_label:
            success = self.voice_label_heading(stmts)
            MY_LOGGER.debug(f'label_heading: {stmts} self: {type(self)}')
        return success

    def voice_label_heading(self, stmts: Statements) -> bool:
        """
        Voices a Control's label as the heading

        :param stmts:
        :return:
        """
        if not self.supports_heading_label:
            return False
        return self.parent.voice_label_heading(stmts)

    def get_orientation(self) -> str:
        """
        Primarily used for lists and containers. Also sliders, scrollbars, etc.

        :return:
        """
        clz = TopicModel
        orientation: str = self.parent.get_orientation()
        return orientation

    def visible_item_count(self) -> int:
        """
        Determines the nmber of visible items in the group simply by
        counting the children which are visible.
        :return:
        """
        if not self.supports_item_count:
            return -1
        return self.parent.visible_item_count()

    def voice_active_item_value(self, stmts: Statements) -> bool:
        return False

    '''
    def voice_control_name_and_value(self, stmts: Statements) -> bool:
        success: bool = False
        self.voice_topic_value(stmts)
        return success
    '''

    '''
    def voice_best_control_name(self, stmts: Statements) -> bool:
        clz = TopicModel
        best_name: str = self.get_best_control_name()
        #  MY_LOGGER.debug(f'{best_name}')
        if best_name == '':
            return False
        stmts.last.phrases.add_text(texts=best_name)
        return True
    '''

    def get_best_control_name(self) -> str:
        best_name: str = self.get_alt_control_name()
        if best_name == '':
            best_name = self.parent.get_control_name()
        return best_name

    def voice_alt_control_name(self, stmts: Statements) -> bool:
        clz = TopicModel
        MY_LOGGER.debug(f'alt_type: {self.alt_type}')
        if self.alt_type in ('', 'none'):
            return False
        alt_name: str = self.get_alt_control_name()
        MY_LOGGER.debug(f'alt_name: {alt_name}')
        if alt_name == '':
            return False
        stmts.last.phrases.append(Phrase(text=alt_name,
                                         post_pause_ms=Phrase.PAUSE_DEFAULT,
                                         check_expired=False))
        return True

    def get_alt_control_name(self) -> str:
        clz = TopicModel
        if MY_LOGGER.isEnabledFor(DISABLED):
            MY_LOGGER.debug(f'topic: {self.name} alt_type: {self.alt_type} '
                              f'topic: {self}')
        if self.alt_type in ('', 'none'):
            return ''
        return self.alt_type

    def voice_alt_label(self, stmts: Statements) -> bool:
        clz = TopicModel
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
            MY_LOGGER.debug(f'Invalid int alt_label_id: {alt_label_id}')
            text = ''
        return False

    """
    ------------------------------------------------------------------------------------
                      L A B E L S
        From Kodi wiki:
        
        Label Parsing
            
            
            In label controls, fadelabel controls, built-in functions as well as in the 
            LCD label definition files you can specify more than one piece of 
            information to be displayed in a single line of text (or across multiple 
            lines of text) by using the $INFO, $ESCINFO[] and $LOCALIZE keywords in a 
            <label> tag. In addition to this, you can use the Label Formatting syntax 
            to specify color and style information for the text (changeable within a 
            single label).
            Example
            
              <label>A good example of a $INFO[MusicPlayer.Title,song title: , 
              $COMMA and a]$INFO[MusicPlayer.Artist, song artist:]</label>
            
              <label>$LOCALIZE[31005]</label>
            
              <label>The following will be localized from an addons strings - $ADDON[
              addon.id.here 32001]</label>
            
            How the parsing works
            
                Kodi runs through and replaces any $LOCALIZE[number] blocks with the 
                real string from strings.po.
                Kodi then runs through and translates the $INFO[infolabel,prefix,
                postfix] blocks from left to right.
                If the Info manager returns an empty string from the infolabel, 
                then nothing is rendered for that block.
                If the Info manager returns a non-empty string from the infolabel, 
                then Kodi prints the prefix string, then the returned infolabel 
                information, then the postfix string. Note that any $COMMA fields are 
                replaced by real commas, and $$ is replaced by $.
                Any pieces of information outside of the $INFO blocks are rendered 
                unchanged.
            
            So, in the above example, if nothing is playing then the label will print: 
            A good example of a
            
            If a song is playing but it has no Title (ie MusicPlayer.Title returns an 
            empty string) but does have an artist, it will return: A good example of a 
            song artist: <Artist>
            
            If a song is playing that has title and artist information, it will return: 
            A good example of a song title: <Title>, and a song artist: <Artist>
            
            
            $ESCINFO[] should be used when passing an infolabel to a built-in function, 
            when this infolabel is likely to contain commas (,) and/or quotes (").
            
            eg: PlayMedia($INFO[ListItem.Path]) might return: PlayMedia(
            /some/path/with_a_file_that_includes,a_comma.avi)
            
            This will be read by the builtin function generator as PlayMedia called 
            with 2 parameters: "/some/path/with_a_file_that_includes" and "a_comma.avi".
            
            If you use PlayMedia($ESCINFO[ListItem.Path]) however, it will make sure 
            that whatever is returned by the infolabel is sent on to the builtin as a 
            single parameter. 
    """

    def voice_label(self, stmts: Statements,
                    control_id_expr: int | str | None = None) -> bool:
        """
        Voices the label of a control
        :param stmts: Any found text is appended to stmts
        :param control_id_expr:  If non-None, then used as the control_id instead
               of self.control_id
        :return:
        """
        clz = TopicModel
        success = self.parent.voice_label(stmts, control_id_expr)
        return success

    def voice_label2(self, stmts: Statements,
                     control_id_expr: int | str | None = None,
                     stmt_type: StatementType = StatementType.NORMAL) -> bool:
        return False

    def voice_info_label(self, stmts: Statements, label_expr: str) -> bool:
        """
           Queries xbmc for the value of the given Info Label.

        :param stmts: Any statements are appended to this
        :param label_expr:  A Kodi info-label or list-item expression
        :return: True if one or more statements was found and added
        """
        clz = TopicModel
        #  TODO: None means that there was a label expression and it failed
        #        to get label. Should not try anymore. Need a means to do this.
        #        Exception? Tuple return code? Enum return code?
        text: str | None = self.parent.get_info_label(label_expr)
        if text is None:
            return False

        # Append these phrase(s) to existing statement
        phrases: PhraseList = stmts.last.phrases
        phrases.add_text(text)
        return True

    def voice_label_expr(self, stmts: Statements) -> bool:
        """
        Voice a label using a label_expr
              A label_expression can be:
                msg_id for a label (int)

        :param stmts:
        :return:
        """
        clz = TopicModel
        success: bool = False
        phrases: PhraseList = stmts.last.phrases
        if self.label_expr != '':
            # First, assume label_expr is the id of a label
            #
            try:
                msg_id: int = int(self.label_expr)
                text = Messages.get_msg_by_id(msg_id)
                if text != '':
                    phrase: Phrase = Phrase(text=text, check_expired=False)
                    phrases.append(phrase)
                    success = True
            except ValueError as e:
                success = False
            if not success:
                MY_LOGGER.debug(f'No message found for topic label')
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

        The labeled_by_expr can contain:
            A control_id (must be all numeric)
            A topic name
            A tree_id (dynamically created when window defined)
            A info-label type expression: begins with $INFO or $PROP

        Note that the topic with the labeled by may require a chain of labels
        to be read.

        :param stmts: Appends any voicings to stmts
        :return: True if phrases was added to. Otherwise, False
        """
        # Needs work
        clz = TopicModel
        if self.labeled_by_expr == '':
            return False

        MY_LOGGER.debug(f'labeled_by_expr: {self.labeled_by_expr}')

        # Process any InfoLabel

        label: str = ''
        info: str = ''
        if self.labeled_by_expr.startswith('$INFO['):
            info: str = self.labeled_by_expr[6:-1]
            label: str = xbmc.getInfoLabel(info)
        elif self.labeled_by_expr.startswith('$PROP['):
            info: str = self.labeled_by_expr[6:-1]
            label: str = xbmc.getInfoLabel(f'Window().Property({info})')
        if label is not None and label != '':
            stmts.last.phrases.add_text(texts=label)
            return True
        elif info is not None and info != '':
            MY_LOGGER.debug(f'BAD $INFO or $PROP query: {info}')
            return False

        success: bool = False
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
        MY_LOGGER.debug(f'{stmts.last.phrases}')
        return success

    def voice_heading_labeled_by(self,
                                 stmts: Statements,
                                 chain: bool = False) -> bool:
        """
        Voice any heading_labeled_by an element in this topic.

        Orchestrates voicing using any heading_labeled_by reference. Delegates most of
        the work to this topic's control.

        The heading_labeled_by can contain:
             A control_id (must be all numeric)
             A topic name
             A tree_id (dynamically created when window defined)

        Note that the topic with the heading_labeled by may require a chain of labels
        to be read.

        :param chain:
        :param stmts: Appends any voicings to stmts
        :return: True if phrases was added to. Otherwise, False
        """
        # Needs work
        clz = TopicModel
        success: bool = False
        control: BaseModel | None
        topic: TopicModel | None
        control, topic = self.window_struct.get_control_and_topic_for_id(
                self.heading_labeled_by)
        if topic is not None:
            # topic is the topic that heading_labeled_by references
            # Have that topic voice the label
            success = topic.voice_heading_label(stmts, chain)
            MY_LOGGER.debug(f'voice_heading_label returned: {stmts.last}')
        elif control is not None:
            control: BaseModel
            success = control.voice_heading_without_topic(stmts)
        MY_LOGGER.debug(f'voice_heading_labeled_by: {self.heading_labeled_by}')
        return success

    def voice_control_labels(self, stmts: Statements, voice_label: bool = True,
                             voice_label_2: bool = True,
                             control_id_expr: str | None = None) -> bool:
        """
        Convenience method that calls this topic's control to voice the labels.

        :param stmts: Any found text is appended to this
        :param voice_label: Voice the label, if supportted by control
        :param voice_label_2 Voice label_2, if supported by control
        :param control_id_expr:  If non-None, then used as the control_id instead
               of self.control_id
        TODO: don't inherit from BaseModel!!!
        """
        if control_id_expr is None or control_id_expr == '':
            control_id_expr = str(self.control_id)
        success: bool = self.parent.voice_labels(stmts, voice_label=voice_label,
                                                 voice_label_2=voice_label_2)
        if self.read_next_expr != '':
            self.voice_chained_controls(stmts)
        return success

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

        Voice ONE of the following, in order: alt_label, labeled_by, control's label(s).
        Afterwords, if chain is True, then call voice_chained_controls



        Example INFO labels
                 xbmc.getInfoLabel(
                                                       '$INFO[MusicPlayer.Artist,'
                                                       '$LOCALIZE[557]: ,:] $INFO['
                                                       'Player.Title,$LOCALIZE[369]: ,'
                                                       ':]'))

        timelineInfo: Tuple[str_or_int, ...]
            timelineInfo = (Messages.get_msg(Messages.CHANNEL),  # PVR
                            '$INFO[ListItem.ChannelNumber]',
                            '$INFO[ListItem.ChannelName]',
                            '$INFO[ListItem.StartTime]',
                            19160,
                            '$INFO[ListItem.EndTime]',
                            '$INFO[ListItem.Plot]'
                            )

        """
        clz = TopicModel
        MY_LOGGER.debug(f'In voice_generic_label')
        success: bool = True
        if self.alt_label_expr != '':
            success = self.voice_info_label(stmts, self.alt_label_expr)
            if success and MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'from voice_info_label {stmts.last}')

        else:
            success = False
        if not success:
            # If a Topic has the same id for labeled_by and flows_to,
            # then do only one of them.
            success = self.voice_labeled_by(stmts)
            if success and MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'from voice_labeled_by {stmts.last}')

        if not success:
            success = self.voice_control_labels(stmts)
            if success and MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'from voice_control_labels {stmts.last}')

        if chain:
            # If this topic has a 'read_next' value, then voice the label(s)
            # from that topic
            _ = self.voice_chained_controls(stmts)
            MY_LOGGER.debug(f'post voice_chained_controls: {stmts.last}')
        return success

    def voice_topic_value(self, stmts: Statements) -> bool:
        """
            Voice a control's value. Used primarily when a control's value comes from
            another control ('flows_to') or when the control's value can change without
            a focus change (radiobutton, etc.). Let the control using the value decide
            whether it should be voiced (repeat values are supressed when the focus
            has not changed).

            If both labeled_by and flows_to are present, ignore labeled_by, otherwise,
            only voice flows_to. If neither is present, then voice any label.

            Whenever voicing, if there is a choice to voice label_2, then do so,
            otherwise label.

            :param stmts:
            :return:
        """
        clz = TopicModel
        success: bool = False
        if self.supports_container:
            success = self.voice_active_item_value(stmts)
        elif self.flows_to_expr != '':
            success = self.voice_flows_to(stmts)
            if success:
                return success

        if not self.supports_value:  # Not all controls have a value, get elsewhere
            return False

        model: ForwardRef('BasicModel')
        model = self.parent
        success = False
        if model.supports_label2_value:
            success = model.voice_label2_value(stmts=stmts,
                                               control_id_expr=None,
                                               stmt_type=StatementType.VALUE)
        if not success and model.supports_label_value:
            success = model.voice_label_value(stmts=stmts,
                                              control_id_expr=None,
                                              stmt_type=StatementType.VALUE)
        return success

    def get_item_number(self) -> int:
        """
        Used to get the current item number from a List type topic. Called from
        a child topc of the list

        :return: Current topic number, or -1
        """
        clz = TopicModel
        if not self.supports_item_count:
            return -1

        container_id: int = self.control_id
        curr_item: str = ''
        try:
            curr_item = xbmc.getInfoLabel(f'Container({container_id}).CurrentItem')
        except Exception:
            MY_LOGGER.exception('')

        item_number: int = -1
        if curr_item.isdigit():
            item_number = int(curr_item)
            MY_LOGGER.debug(f'Item # {item_number}')
        return item_number

    def voice_item_number(self, stmts: Statements) -> bool:
        """
        A topic has an item number if its container_topic is a list-type control
        (supports_item_count).

        :param stmts: Any voiced text is appended to this
        :return: True if something was voiced, otherwise False

        This will query any container_topic of this topic to get the item number,
        if any.
        """
        clz = TopicModel

        if self._container_topic is None and self.container_topic != '':
            if self.container_topic != '':
                #  MY_LOGGER.debug('Resolved container_topic')
                if self._container_topic is None:
                    control_model, self._container_topic =\
                        self.window_struct.get_control_and_topic_for_id(
                            self.container_topic)
        if (self._container_topic is None
                or not self._container_topic.supports_item_number):
            return False

        item_number: int = self._container_topic.get_item_number()
        if item_number < 1:
            return False

        text = MessageId.ITEM_WITH_NUMBER.get_formatted_msg(f'{item_number}')
        stmts.last.phrases.add_text(texts=text)
        return True

    def voice_chained_controls(self, stmts: Statements) -> bool:
        """
        Voices controls in response to the presence of a topic's 'read-next' references
        to other topics. The chain continues as long as there are read-next
        references.

        Returns immediately if the current topic does not have 'read-next'

        :param stmts: Voiced phrases are appended
        :return:

        Note: The topic that is at the head of the chain first voices its own
              labels, then it requests any topic that it has a read_next for
              to voice.
        """
        clz = TopicModel
        MY_LOGGER.debug(f'In voice_chained_controls')
        success: bool = True
        if self.read_next_expr == '':
            return success

        if self._read_next is None and self.read_next_expr != '':
            MY_LOGGER.debug(f"Can't find read_next_expr {self.read_next_expr}")
            return False
        _ = self._read_next.voice_generic_label(stmts, chain=True)
        MY_LOGGER.debug(f'from voice_generic_label {stmts.last}')
        return success

    def voice_chained_headings(self, stmts: Statements) -> bool:
        """
        Voices headings in response to the presence of a topic's 'heading_next'
        references to other topics. The chain continues as long as there are
        heading_next references.

        :param stmts: Voiced phrases are appended
        :return:

        Note: The topic that is at the head of the chain first voices its own
              label.
        """
        clz = TopicModel
        #  MY_LOGGER.debug(f'In voice_chained_headings')
        success: bool = True
        if self.heading_next == '':
            return success

        if self._heading_next is None:
            control, topic = self.window_struct.get_control_and_topic_for_id(
                    self.heading_next)
            if topic is not None:
                self._heading_next = topic
            else:
                MY_LOGGER.debug(f"Can't find heading_next {self.heading_next}")
                return False

        _ = self._heading_next.voice_heading_label(stmts, chain=True)
        MY_LOGGER.debug(f'{stmts.last}')
        return success

    def voice_flows_to(self, stmts: Statements,
                       stmt_type: StatementType = StatementType.NORMAL) -> bool:
        """
        Voice a control's value. Used primarily when a control's value comes from
        another control ('flows_to'). Let the control using the value decide
        whether it should be voiced.

        TODO: flows_to_expr can refer to:
                a topic
                a model
                a control
                an info_label
                For now, this routine only handles topic and model

        When a control, like a button, impacts the value of another control, a label,
        then the button 'flows_to' the label (TODO: perhaps more than one?) control.

        If a control has a label, it is voiced first. If the control has a 'flows_to'
        then that is voiced next. (TODO: What about a chain of 'flows_to'? What about
        additional labels, labeled_bys or flows_to in a chain?)

        If both labeled_by and flows_to are present, ignore labeled_by, otherwise,
        only voice flows_to.

        Whenever voicing, if there is a choice to voice label_2, then do so,
        otherwise label.

        NOTE: TODO: For now, flows_to values are ONLY voiced if the control that
                    it comes from is visible.
                    Possible ways to overcome this limitation:
                      - Allow condition expressions in flows_to
                      - Add attributes to flows_to
                    Similar issues are chaining and labeled_by + flows_to, etc.

        :param stmts:
        :param stmt_type: Sets the StatementType of the voiced Statement
        :return:
        """
        clz = TopicModel
        success: bool = False

        if self.flows_to_expr == '':
            return False

        # flows_to can be a control_id or a topic name
        # if self.labeled_by_expr == self.flows_to:
        # Will cause the same thing to be voiced. Already voiced
        # labeled_by, so skip this
        #    MY_LOGGER.debug(f'Already voiced by labeled_by')
        #   return False
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'flows_to: {self.flows_to_expr}')

        # Get the destination topic/model
        if self.flows_to_topic is None and self.flows_to_model is None:
            self.flows_to_model, self.flows_to_topic =\
                self.window_struct.get_control_and_topic_for_id(self.flows_to_expr)

            if self.flows_to_topic is None and self.flows_to_model is None:
                MY_LOGGER.info(f'Can not find flows_to topic NOR model for id: '
                                 f'{self.flows_to_topic}')
                return False

        control_id: str | int = -1
        visible: bool = False
        if self.flows_to_topic is not None:
            control_id = self.flows_to_topic.control_id
            visible = self.flows_to_topic.is_visible()
            if visible:
                success = self.flows_to_topic.parent.voice_label(stmts, control_id,
                                                                 stmt_type=stmt_type)
        else:
            control_id = self.flows_to_model.control_id
            visible = self.flows_to_model.is_visible()
            if visible:
                success = self.flows_to_model.voice_label(stmts, control_id,
                                                          stmt_type=stmt_type)
        MY_LOGGER.debug(f'control_id: {control_id} visible: {visible}')
        return success

    def voice_working_value(self, stmts: Statements) -> bool:
        """
            Voices the value of this topic without any heading. Primarily
            used by controls, where the value is entered over time, by an
            analog slider, or multiple keystrokes, etc.... The intermediate
            changes need to be voiced without added verbage.
        :param stmts:
        :return:
        """
        return False

    def voice_control_value(self, stmts: Statements,
                            control_topic: ForwardRef(
                                    'TopicModel') = None) -> bool:
        """
        Voices another control's value. Sometimes a control, such as a button
        may change the value in a label. This allows the label to be read.

        :param stmts:
        :param control_topic:
        :return:
        """
        clz = TopicModel
        control_id: int = self.control_id
        if control_topic is not None:
            control_id = control_topic.control_id
        success = self.parent.voice_control_value(stmts, control_id)
        return success

    def __repr__(self) -> str:
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = True) -> str:
        """
        Convert TopicModel to a string.
        Note that include_children defaults to True since Topics currently
        have no children. If there were any, they would be few and not nested.

        :param include_children:
        :return:
        """
        clz = TopicModel

        class_name: str = self.__class__.__name__
        name_str: str = ''
        if self.name != '':
            name_str = f'\n  name: {self.name} control_id: {self.control_id}'
        parent_model_str: str = '\n None'
        if self.parent is not None:
            parent_model_str = f'\n  parent.control_id: {self.parent.control_id}'

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
        if self.flows_to_expr != '':
            flows_to_str = f'\n  flows_to: {self.flows_to_expr}'

        flow_from_str: str = ''
        if self.flows_from_expr != '':
            flow_from_str = f'\n  flows_from: {self.flows_from_expr}'

        # topic_heading_str: str = ''
        # if self.topic_heading != '':
        #     topic_heading_str = f'\n  topic_heading: {self.topic_heading}'

        heading_label_str: str = ''
        if self.heading_label != '':
            heading_label_str = f'\n  heading_label: {self.heading_label}'

        heading_labeled_by_str: str = ''
        if self.heading_labeled_by != '':
            heading_labeled_by_str = f'\n  heading_labeled_by: {self.heading_labeled_by}'

        heading_next_str: str = ''
        if self.heading_label != '':
            heading_next_str = f'\n  heading_next: {self.heading_next}'

        topic_up_str: str = ''
        if self.topic_up != '':
            topic_up_str = f'\n  topic_up: {self.topic_up}'

        topic_down_str: str = ''
        if self.topic_down != '':
            topic_down_str = f'\n  topic_down: {self.topic_down}'

        topic_left_str: str = ''
        if self.topic_left != '':
            topic_left_str = f'\n  topic_left: {self.topic_left}'

        topic_right_str: str = ''
        if self.topic_right != '':
            topic_right_str = f'\n  topic_right: {self.topic_right}'

        topic_type_str: str = ''
        if self.topic_type != '':
            topic_type_str = f'\n  topic_type: {self.topic_type}'

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
            units_str = f'\n {self.units}'

        value_from_str: str = ''
        if self.value_from != '':
            value_from_str = f'\n  value_from: {self.value_from}'

        value_format_str: str = ''
        if self.value_format != '':
            value_format_str = f'\n  value_format: {self.value_format}'

        results: List[str] = []
        result: str = (f'\n{class_name}:  {name_str}'
                       f'{parent_model_str}'
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
                       f'{topic_type_str}'
                       f'{topic_up_str}'
                       f'{topic_down_str}'
                       f'{topic_left_str}'
                       f'{topic_right_str}'
                       #  f'{topic_heading_str}'
                       f'{heading_label_str}'
                       f'{heading_labeled_by_str}'
                       f'{heading_next_str}'
                       f'{alt_type_str}'
                       f'{rank_str}'
                       f'{read_next_expr_str}'
                       f'{true_msg_id_str}'
                       f'{false_msg_id_str}'
                       f'{units_str}'
                       f'{value_format_str}'
                       f'{value_from_str}'

                       f'\n  # children: {len(self.children)}'
                       )
        results.append(result)

        for child in self.children:
            child: BaseModel
            results.append(child.to_string(False))
        results.append(f'END {class_name}')

        return '\n'.join(results)
