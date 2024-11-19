# coding=utf-8
import faulthandler
import io
from typing import List

import xbmcvfs

from common.logger import BasicLogger
from common.phrases import PhraseList
from gui.base_model import BaseModel
from gui.gui_globals import GuiGlobals
from gui.parser.parse_topic import ParseTopic
from gui.statements import Statement, Statements, StatementType
from gui.topic_model import TopicModel
from windows.window_state_monitor import WinDialogState

MY_LOGGER = BasicLogger.get_logger(__name__)


class ListTopicModel(TopicModel):
    """
    Provides vocing for the List Container decorated with a Topic
    """

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = ListTopicModel

        super().__init__(parent=parent, parsed_topic=parsed_topic)

    done_once: bool = False

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
    def supports_item_count(self) -> bool:
        """
           Indicates if the control supports item_count. List type containers/
           controls, such as GroupList do

           :return:
        """
        return True

    @property
    def supports_item_number(self) -> bool:
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
        return True

    @property
    def supports_change_without_focus_change(self) -> bool:
        """
            Indicates if the control supports changes that can occur without
            changes in Focus. Slider is an example. User modifies value without
            leaving the container. Further, you only want to voice the value,
            not the control name, etc.
        :return:
        """
        return True

    def voice_working_value(self, stmts: Statements) -> bool:
        """
            Voices the value of this topic without any heading. Primarily
            used by controls, where the value is entered over time, by an
            analog slider, or multiple keystrokes, RadioButton slider,
            etc.... The intermediate changes need to be voiced without added verbage.

            Another use case is where a control (like list) allows you to
            make a selection that changes some other control's value
            via 'flows_to'. In this case, the value of the list's label
            is voiced when it is scrolled to (no focus changes) and then
            when the user presses select, a value of some other control is
            changed and requires voicing. The trick is, we DON'T want
            to voice the other control until it's value changes.

        :param stmts:
        :return:
        """
        clz = ListTopicModel
        changed: bool
        # TODO: Probably don't need two paths to the same thing. See
        #  topic_model.voice_control where either voice_topic_value or
        #  voice_working_value is called depending upon focus change.
        #  Probably just need one method.
        return self.voice_active_item_value(stmts)

    def voice_active_item_value(self, stmts: Statements) -> bool:
        """
        Voice the active/focused item(s).

        Note: an ACTIVE item can have multiple changes made to it without
        the user changing focus. Normally WindowStateMonitor filters out
        all events that don't involve a focus change (controlled by
        GuiGlobals.require_focus_change = False).

        Voicing the active item(s) for List containers can be a bit involved
        since there are multiple layouts/views to consider. Each layout can
        have a 'condition' that must be met before it applies. The first
        layout that meets the condition wins.

        Finally, selecting a value from the list may cause some other control,
        likely a label, to change value.

        :param stmts:
        :return:
        """
        clz = ListTopicModel
        success: bool = False
        # Can't get a usable item number. See get_item_number
        #  item_number: int = self.get_item_number()
        result: List[str]
        result = self.parent.get_working_value(-1)
        phrases: PhraseList = PhraseList(check_expired=False)
        #
        # There is NO usable item number
        # The voicing of an 'item' is a unit. It makes no sense to
        # voice the item number separately from its value(s). The risk
        # is that the item # would be voiced, but not its value.
        old_value_key: str = f'{self.name}_value'
        old_values: List[str] = GuiGlobals.saved_states.get(old_value_key, [])
        ignore: bool = False
        if len(result) == 0 or old_values == result:
            ignore = True
        MY_LOGGER.debug(f'ignore: {ignore} old_values: {old_values}\n '
                        f'result: {result}')
        GuiGlobals.saved_states[old_value_key] = result
        if not ignore:
            phrases = PhraseList(check_expired=False)
            phrases.add_text(f'item:')
            for item_value in result:
                phrases.add_text(item_value)
            stmts.append(Statement(phrases, stmt_type=StatementType.VALUE))
        MY_LOGGER.debug(f'phrases: {phrases}\n {stmts}')

        # Cause WindowStateMonitor to process events whether
        # there was a focus change or not. Normally only
        # focus-change events are processed.
        # This is disabled by WindowStateMonitor when another
        # focus change event occurs under the assumption that the newly
        # focused control will not need it.

        MY_LOGGER.debug(f'FOCUS CHANGED requried = False')
        GuiGlobals.require_focus_change = False

        # We want to voice any side effects to changes made here,
        # but ONLY when a change is also made in the list container's
        # selection. We can't detect an arbitrary control's Selection
        # events.
        MY_LOGGER.debug(f'flows_to_expr: {self.flows_to_expr}')
        if self.flows_to_expr != '':   # and not self.focus_changed:
            # Here we have a case where an additional
            # value(s) may need to be voiced
            success = self.voice_flows_to(stmts, stmt_type=StatementType.VALUE)
        return success

    def voice_any_additional_values(self, stmts: Statements) -> bool:
        success: bool = False

        success = self.voice_working_value(stmts)
        return success

    '''
    def get_item_number(self) -> int:
        """
        NOTE: The item number is next to useless for a list container because
              it is relative to the viewable items. There is NO way to get this
              except from List Container itself via getSelectedPosition.

        Used to get the current item number from a List type topic. Called from
        a child topic of the list

        :return: Current topic number, or -1
        """
        return self.parent.get_item_number(self.control_id)
    '''
