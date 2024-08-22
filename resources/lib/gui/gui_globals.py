# coding=utf-8

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
