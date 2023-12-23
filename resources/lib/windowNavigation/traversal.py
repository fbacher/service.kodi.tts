import xbmcgui

import windows.guitables as guitables
from common.constants import Constants
from common.logger import (BasicLogger)

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(
    ).getChild('lib.windowNavigation')
else:
    module_logger = BasicLogger.get_module_logger()


class WindowTraversal:

    def __init__(self):
        self._logger = module_logger.getChild(self.__class__.__name__)

    def voice_focused_control(self):

        control = None
        current_window_id = None
        try:
            current_window_id = xbmcgui.getCurrentWindowId()
            window_name = guitables.getWindowName(current_window_id)
            extra_texts = guitables.getExtraTexts(current_window_id)
            self._logger.debug_extra_verbose(
                'WindowTraversal: current_window_id: {} name: {}'.
                format(str(current_window_id), window_name))
            self._logger.debug_extra_verbose(
                'window extra texts: {} '.format(extra_texts))
            item_extra_texts = guitables.getItemExtraTexts(current_window_id)
            self._logger.debug_extra_verbose(
                'window item extra texts: {item_extra_texts}')
            list_item_property = guitables.getListItemProperty(current_window_id)
            self._logger.debug_extra_verbose(
                'window list item extra property: {} '.format(list_item_property))
        except Exception as e:
            pass
            self._logger.debug_extra_verbose('WindowTraversal: no current Window ID')

        current_window_dialog_id = None
        try:
            current_window_dialog_id = xbmcgui.getCurrentWindowDialogId()
            window_name = guitables.getWindowName(current_window_dialog_id)
            extra_texts = guitables.getExtraTexts(current_window_dialog_id)
            self._logger.debug_extra_verbose(
                'WindowTraversal: current_window_dialog_id: {} name: {}'
                .format(str(current_window_dialog_id),
                        window_name))
            self._logger.debug_extra_verbose(
                'window extra texts: {} '.format(extra_texts))
            item_extra_texts = guitables.getItemExtraTexts(current_window_dialog_id)
            self._logger.debug_extra_verbose(
                'window item extra texts: {} '.format(item_extra_texts))
            list_item_property = guitables.getListItemProperty(current_window_dialog_id)
            self._logger.debug_extra_verbose(
                'window list item extra property: {} '.format(list_item_property))

        except Exception as e:
            pass
            self._logger.debug_extra_verbose(
                'WindowTraversal: no current Window Dialog ID')

        window = xbmcgui.Window(current_window_id)
        try:
            control = window.getFocus()
        except Exception as e:
            pass
            self._logger.debug_extra_verbose(
                'WindowTraversal: focused_control ID:{}'.format(control.getId()))
            self._logger.debug_extra_verbose('isVisible:{}'.format(control.isVisible()))

        if control is None:
            self._logger.debug_extra_verbose('WindowTraversal: no control with focus')
        else:
            self.voice_control(control)

    def voice_control(self, control):
        # Can't get up, down, left, right navigation
        # Can't get associated labels to controls

        if isinstance(control, xbmcgui.ControlButton):
            control_button = control  # type: xbmcgui.ControlButton
            self._logger.debug_extra_verbose(
                'WindowTraversal: ControlButton label: {}, label2: {}'
                .format(control_button.getLabel(), control_button.getLabel2()))
        elif isinstance(control, xbmcgui.ControlEdit):
            edit_control = control  # type: xbmcgui.ControlEdit
            # Can't get text type
            self._logger.debug_extra_verbose(
                'WindowTraversal: ControlEdit label: {}, text: {}'
                .format(edit_control.getLabel(),
                        edit_control.getText()))

        elif isinstance(control, xbmcgui.ControlList):
            control_list = control  # type: xbmcgui.ControlList
            # Can't get list header
            item = control_list.getSelectedItem()
            item_type = 'None'
            if item is not None:
                item_type = type(item).__name__
            self._logger.debug_extra_verbose(
                'WindowTraversal: ControlList selectedPosition: {}, selectedItem: {}, '
                'type: {}'
                .format(control_list.getSelectedPosition(),
                        control_list.getSelectedItem(),
                        item_type))
            if isinstance(item_type, xbmcgui.Control):
                self._logger.debug_extra_verbose(
                    'WindowTraversal: recursing for Control type')
                self.voice_control(item)
        elif isinstance(control, xbmcgui.ControlGroup):
            control_group = control  # type: xbmcgui.ControlGroup
            # Can't get to contents of group
            self._logger.debug_extra_verbose(
                    'WindowTraversal: ControlGroup')
        elif isinstance(control, xbmcgui.ControlFadeLabel):
            control_fade_label = control  # type: xbmcgui.ControlFadeLabel
            # Can't get to list of labels
            self._logger.debug_extra_verbose('WindowTraversal: ControlFadeLabel')
        elif isinstance(control, xbmcgui.ControlImage):
            control_image = control  # type: xbmcgui.ControlImage
            # Can't get image path
            self._logger.debug_extra_verbose('WindowTraversal: ControlImage')
        elif isinstance(control, xbmcgui.ControlProgress):
            control_progress = control  # type: xbmcgui.ControlProgress
            self._logger.debug_extra_verbose(
                'WindowTraversal: ControlProgress percent complete: {}'
                .format(control_progress.getPercent()))
        elif isinstance(control, xbmcgui.ControlRadioButton):
            control_radio_button = control  # type: xbmcgui.ControlRadioButton
            # Can't get label
            self._logger.debug_extra_verbose(
                'WindowTraversal: ControlRadioButton isSelected: {}'
                .format(control_radio_button.isSelected()))
        elif isinstance(control, xbmcgui.ControlSlider):
            control_slider: xbmcgui.ControlSlider = control
            self._logger.debug_extra_verbose(
                'WindowTraversal: ControlSlider: percent {}, int {}, float{}'
                .format(control_slider.getPercent(),
                        control_slider.getInt(),
                        control_slider.getFloat()))
        elif isinstance(control, xbmcgui.ControlTextBox):
            control_text_box = control  # type: xbmcgui.ControlTextBox
            self._logger.debug_extra_verbose('WindowTraversal: ControlTextBox text: {}'
                                             .format(control_text_box.getText()))
