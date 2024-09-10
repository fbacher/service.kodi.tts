# coding=utf-8
from typing import Any, Dict


class GuiGlobals:
    """
    Contains global variables
    """
    # Controls whether monitored window events without a change in focus are
    # discarded or not.
    # Set by the screen scraper (SliderTopic, for one)
    # Read by GuiWorker
    # Reset by screen scraper when a focus_change occurs after this is set to
    # True

    require_focus_change: bool = True

    # TopicModels are free to save previous values so that they can
    # suppress duplicate voicings This is meant to be used by controls
    # which change value even without focus changes (List container,
    # Slider, etc.). This (hopefully) simplifies the management of these
    # values.
    #
    # NOTE: ALL of the saved_states are removed whenever there is a focus change.
    #
    # Suggested key name prefixes are topic_name or control_id. Suffixes are
    # only needed when multiple values are saved for the same control. Note
    # that the control is not necessarily the one that the setting belongs to,
    # rather it is the control which requires it as part of its value (and linked
    # by a "flows_to" or similar.
    #
    # It is quite possible that this will change to be a two-level Dict with
    # the first level for the different Windows and the second level for the
    # values on a Window.

    saved_states: Dict[str, Any] = {}

    @staticmethod
    def clear() -> None:
        """
        Clears all saved values. Called when the focus has changed. Will be
        called from CustomTTS.direct_voicing_topics just before evaluating
        the next state of a window's controls.

        :return:
        """
        GuiGlobals.saved_states.clear()
