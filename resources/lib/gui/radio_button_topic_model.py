# coding=utf-8
from typing import List

from common.logger import BasicLogger
from common.phrases import PhraseList
from gui.base_model import BaseModel
from gui.gui_globals import GuiGlobals
from gui.parser.parse_topic import ParseTopic
from gui.statements import Statement, Statements, StatementType
from gui.topic_model import TopicModel
from windows.window_state_monitor import WinDialogState

MY_LOGGER = BasicLogger.get_logger(__name__)


class RadioButtonTopicModel(TopicModel):
    """
        Handles 'topic' metadata embedded in skin .xml files to help voice
        RadioButton controls.

        Notes:
            It may be possible to use the function SetProperty with onclick to
            set the state of the button in a window property and the access that
            value using an infolabel.
    """

    def __init__(self, parent: BaseModel, parsed_topic: ParseTopic) -> None:
        clz = RadioButtonTopicModel
        super().__init__(parent=parent, parsed_topic=parsed_topic)

    @property
    def supports_boolean_value(self) -> bool:
        """
        Some controls, such as RadioButton, support a boolean value
        (on/off, disabled/enabled, True/False, etc.). Such controls
        Use the value "(*)" to indicate True and "( )" to indicate False.
        :return:
        """
        return True

    @property
    def supports_value(self) -> bool:
        """
        Some controls, such as a button, radio button or label are unable to provide a value.
        I.E. it can't give any indication of what happens when pressed. If the
        topic for this control or another provides flows_from/flows_to or similar,
        then a value can be determined that way, but not using this method.
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
        result: bool = super().voice_topic_value(stmts)
        MY_LOGGER.debug(f'FOCUS CHANGED required = False')
        GuiGlobals.require_focus_change = False
        return result

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
        clz = RadioButtonTopicModel
        changed: bool
        changed = self.parent.voice_label2_value(stmts,
                                                 control_id_expr=None,
                                                 stmt_type=StatementType.VALUE)
        return changed

    '''
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
        clz = RadioButtonTopicModel
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
        # old_item_number_key: str = f'{self.name}_old_item_number'
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

        MY_LOGGER.debug(f'FOCUS CHANGED required = False')
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
    '''
