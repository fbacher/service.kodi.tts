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

module_logger = BasicLogger.get_logger(__name__)


class ListTopicModel(TopicModel):
    """
    Provides vocing for the List Container decorated with a Topic
    """
    _logger: BasicLogger = module_logger

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = ListTopicModel
        if clz._logger is None:
            clz._logger = module_logger

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
            analog slider, or multiple keystrokes, etc.... The intermediate
            changes need to be voiced without added verbage.

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
        # TODO: Revisit when multiple values returned
        values: List[str] = self.parent.get_working_value(item_number=0)
        stmts.append(Statement(PhraseList.create(texts=values),
                               stmt_type=StatementType.VALUE))
        return True

    def voice_active_item(self, stmts: Statements) -> bool:
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
        clz._logger.debug(f'In voice_active_item')
        success: bool = False
        # Can't get a usable item number. See get_item_number
        #  item_number: int = self.get_item_number()
        result: List[str]
        result = self.parent.get_working_value(-1)
        phrases: PhraseList = PhraseList(check_expired=False)
        #
        # There is NO useable item number
        # The voicing of an 'item' is a unit. It makes no sense to
        # voice the item number separately from its value(s). The risk
        # is that the item # would be voiced, but not its value.
        old_value_key: str = f'{self.name}_value'
        # old_item_number_key: str = f'{self.name}_old_item_number'
        old_values: List[str] = GuiGlobals.saved_states.get(old_value_key, [])
        same: bool = False
        if old_values == result:
            same = True
        clz._logger.debug(f'same: {same} old_values: {old_values}\n '
                          f'result: {result}')
        GuiGlobals.saved_states[old_value_key] = result
        if not same:
            phrases = PhraseList(check_expired=False)
            phrases.add_text(f'item:')
            for item_value in result:
                phrases.add_text(item_value)
            stmts.append(Statement(phrases, stmt_type=StatementType.VALUE))
        clz._logger.debug(f'phrases: {phrases}\n {stmts}')

        # Cause WindowStateMonitor to process events whether
        # there was a focus change or not. Normally only
        # focus-change events are processed.
        # This is disabled by WindowStateMonitor when another
        # focus change event occurs under the assumption that the newly
        # focused control will not need it.

        clz._logger.debug(f'FOCUS CHANGED requried = False')
        GuiGlobals.require_focus_change = False

        # We want to voice any side effects to changes made here,
        # but ONLY when a change is also made in the list container's
        # selection. We can't detect an arbitrary control's Selection
        # events.
        clz._logger.debug(f'flows_to_expr: {self.flows_to_expr}')
        if self.flows_to_expr != '':   # and not self.focus_changed:
            # Here we have a case where an additional
            # value(s) may need to be voiced
            success = self.voice_flows_to(stmts, stmt_type=StatementType.VALUE)
        return success

    def voice_any_additional_values(self, stmts: Statements) -> bool:
        success: bool = False

        success = self.voice_working_value(stmts)
        return success

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
