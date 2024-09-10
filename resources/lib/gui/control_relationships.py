# coding=utf-8

"""
    Maintains the relationships between windows and controls. Allows quick
    determination of hierarchy of controls (window heading, topic title, item,
    etc.).  Also tracks any labeled_by, hint_text, alt_label, etc..

    Window has -> heading/title
           should have -> alt_description
                       -> hint_text

    Groups used to contain a 'topic' or 'category' of related controls/labels.
    Groups has -> label
               -> hint_text
               -> alt_label
               -> label_for <id>
    (items in the topic/category can use labeled_by <topic/category> control id)

    Label has -> label & label2
    Labels don't get focus, so won't be read unless referenced by something
    else, or manually navigated to. Therefor needs:
               -> label_for <id>
    (other controls can use -> labeled_by <label_id>)

    Non-focused items can be voiced by traversing a window, or by voicing changes.
    alt_on_left, alt_on_right, alt_on_up, alt_on_down, next_topic, previous_topic,
    parent_topic, sub_topic can be used to navigate. Should also consider 'normal'
    traversals, omitting minor details (by default).


"""
from typing import Dict, List

from gui.base_model import BaseModel
from gui.window_model import WindowModel


class ControlsForWindow:

    def __init__(self):
        pass

    def get_label_for(self, control_id: str) -> str:
        pass

    def get_hint_for(self, control_id: str) -> str:
        pass

    def get_description_for(self, control_id: str) -> str:
        pass

    def get_parent_topic(self, control_id: str) -> str:
        pass

    def get_next_topic(self, control_id: str) -> str:
        pass

    def get_previous_topic(self, control_id: str) -> str:
        pass

    def get_subtopic(self, control_id: str) -> str:
        pass

    def has_topic_changed(self, control_id: str) -> bool:
        pass

    def get_focus_topic(self) -> str:
        pass


class WindowControls:
    controls_for_window: Dict[str, ControlsForWindow] = []
    pass

    """
        Based on the currently focused control, what text and topics are candidates
        for voicing? For the control itself, candidate text includes:
           a control's label, label2, labelInfo
           alt-label, hint-text, labeled_by, menu-info
        For each containing 'topic' (typically an enclosing group or 
        window with associated label, alt-label, hint-text, labeled-by, menu-info).
    """
    def create_control_map(self, win_dialog_id: str) -> None:
        """
            Build map of each control that produces a list of enclosing 'topics'.

            Traverse every node in window, begining with the window. Track the enclosing
            topics during traversal.
        """
        window: WindowModel = self.find_window(win_dialog_id)
        topic = Topic(window)

        control_stack: List[BaseModel] = [window]

        for child in window.children:
            child: BaseModel
            control_stack.append(child)



class Topic:
    def __init__(self, control: BaseModel):
        self.control: BaseModel = control
