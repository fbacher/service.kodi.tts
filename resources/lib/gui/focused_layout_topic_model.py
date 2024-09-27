# coding=utf-8
from typing import ForwardRef, List

from common.logger import BasicLogger
from common.phrases import PhraseList
from gui.base_model import BaseModel
from gui.gui_globals import GuiGlobals
from gui.label_model import LabelModel
from gui.parser.parse_topic import ParseTopic
from gui.statements import Statement, Statements, StatementType
from gui.topic_model import TopicModel

module_logger = BasicLogger.get_logger(__name__)


class FocusedLayoutTopicModel(TopicModel):

    _logger: BasicLogger = module_logger

    def __init__(self, parent: BaseModel, parsed_focused_layout_topic: ParseTopic) -> None:
        clz = FocusedLayoutTopicModel
        if clz._logger is None:
            clz._logger = module_logger

        super().__init__(parent=parent, parsed_topic=parsed_focused_layout_topic)

    @property
    def parent(self) -> ForwardRef('FocusedLayoutTopicModel'):
        return self._parent

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

    def get_info_labels(self) -> List[str]:
        """
            Gets ListItems for this item_layout.

            List Containers can ONLY have Images and Labels. At this time we
            don't care about the images. The labels use ListItems/InfoLabels,
            so they are all that is needed to get the values.

        :return: A List of the ListItems in this ItemLayout
        """
        clz = FocusedLayoutTopicModel

        list_items: List[str] = []
        for layout_item in self.children:
            layout_item: LabelModel
            if layout_item.is_visible():
                list_items.append(layout_item.label_expr)
        return list_items

    def voice_topic_value_old(self, stmts: Statements) -> bool:
        # Get the value from here when control heading, etc. is voiced
        # But don't get the value when the control is not voiced.

        clz = self.__class__
        if self.focus_changed:
            #  clz._logger.debug(f'calling voice_working_value')
            result = self.voice_working_value(stmts)
            clz._logger.debug(f'require_focus_change = False')
            GuiGlobals.require_focus_change = False
            #  clz._logger.debug(f'Back from voice_working_value')
            return result
        return False

    def voice_working_value(self, stmts: Statements) -> bool:
        """
            Voices the value of this topic without any heading. Primarily
            used by controls, where the value is entered over time, by an
            analog slider, or multiple keystrokes, etc.... The intermediate
            changes need to be voiced without added verbage.
        :param stmts:
        :return:
        """
        clz = FocusedLayoutTopicModel
        changed: bool
        value: float
        changed, value = self.parent.get_working_value()
        if not changed:
            #  clz._logger.debug(f'No change: {value}')
            return False
        value_str: str = self.units.format_value(value)
        stmts.append(Statement(PhraseList.create(texts=value_str),
                               stmt_type=StatementType.VALUE))
        return True

    '''
    def value_changed(self, value: int | float):
        """
        Directly voices a change in value from a source, such as a slider,
        which occurs without a change in focus and not caught by main polling
        loop.

        Instead, a private listener is used to temporarily poll for value
        changes while this control has focus. This avoids the higher cost
        of running the main polling loop too often.

        See slider_model.start_monitor and poll_for_value_change.

        TODO:  CAN VOICE BEFORE HEADING READ, CAUSING HEADING TO BE CANCELED
               SO THAT USER ONLY HERES THE VALUE  "1.5" One fix is to do like
               item count. Let control query for a changed value during normal
               cycle.
        :param value:
        :return:
        """
        clz = FocusedLayoutTopicModel
        phrases: PhraseList = PhraseList(check_expired=False)
        value_str: str = self.units.format_value(value)
        phrases.add_text(texts=value_str)
        #  self.voice_topic_value_old(phrases)
        if not phrases.is_empty():
            phrases.set_interrupt(True)
            clz._logger.debug(f'{phrases}')
            stmts: Statements = Statements(Statement(phrases),
                                           topic_id=self.name)
            self.parent.sayText(stmts)
            return True
        return False
        '''
