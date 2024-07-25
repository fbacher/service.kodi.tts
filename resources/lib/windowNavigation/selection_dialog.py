# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

from email._header_value_parser import MessageID

import xbmc
import xbmcgui
from xbmcgui import (Control, ControlButton, ControlEdit, ControlGroup, ControlLabel,
                     ControlRadioButton, ControlSlider)

from common import *

from common.constants import Constants
from common.logger import *
from common.message_ids import MessageId, MessageUtils
from common.messages import Messages
from windowNavigation.choice import Choice

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)

else:
    module_logger = BasicLogger.get_module_logger()


class SelectionDialog(xbmcgui.WindowXMLDialog):
    _logger: BasicLogger
    initialized: bool = False
    HEADING_CONTROL_ID: Final[int] = 1
    OPTIONS_GROUP_LIST: Final[int] = 3
    OK_CONTROL_ID: Final[int] = 5
    CANCEL_CONTROL_ID: Final[int] = 7

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """

        :param args:
        """
        super().__init__(*args, **kwargs)
        clz = type(self)
        self.exit_dialog: bool = False
        clz._logger = module_logger.getChild(self.__class__.__name__)
        clz._logger.debug('SelectionDialog.__init__')
        empty_display_values: List[Choice] = []
        self.list_position: int = 0
        self.selection_index: int = -1
        self.title: str = kwargs.get('title', 'No Heading')
        self.sub_title: str | None = kwargs.get('sub_title', None)
        clz._logger.debug(f'sub_title: {self.sub_title}')
        self._choices: List[Choice]
        self._choices = kwargs.get('choices', empty_display_values)
        self._initial_choice: int = kwargs.get('initial_choice', -1)
        if self._initial_choice < 0:
            self._initial_choice = 0
        self._previous_num_items: int = 200
        self._call_on_focus: Callable[Choice, None] | None
        self._call_on_focus = kwargs.get('call_on_focus', None)
        self._call_on_select: Callable[Choice, None] | None
        self._call_on_select = kwargs.get('call_on_select', None)
        self.heading_control: ControlLabel | None = None
        self.sub_heading_control: ControlLabel | None = None
        self.choices_group: ControlGroup | None = None
        # GroupList's radio_controls
        self.big_group: ControlGroup = None
        self.radio_controls: List[ControlRadioButton] = []
        self.cancel_radio_button: ControlRadioButton | None = None
        self.number_of_radio_controls: int = 0
        self.ok_radio_button: ControlRadioButton | None = None
        self.items_label: ControlLabel | None = None
        self.close_selected_idx: int = -1
        clz._logger.debug(f'choices: {len(self._choices)}')
        xbmc.log(f'choices len: {len(self._choices)}', xbmc.LOGINFO)


    def onInit(self):
        """

        :return:
        """
        # super().onInit()
        clz = type(self)
        xbmc.log('SelectionDialog.onInit enter', xbmc.LOGINFO)
        # control 1 heading label
        # control 3 list of available options
        # control 5 radio_button OK
        # control 7 radio_button cancel
        #

        try:
            self.big_group = self.getControlGroup(1000)
            self.big_group.setVisible(False)
            if not self.initialized:
                self.heading_control = self.getControlLabel(1)
                self.sub_heading_control = self.getControlLabel(4)
                try:
                    # RadioButtons for displaying and choosing choices.
                    # Defined in selection-dialog.xml as controls 101 - 301

                    for idx in range(0, 201):
                        radio_button_control: ControlRadioButton = \
                            self.getControlRadioButton(101 + idx)
                        self.radio_controls.append(radio_button_control)
                        radio_button_control.setVisible(False)
                except Exception as e:
                    clz._logger.exception('Setting up List and evaluating response')

                self.ok_radio_button = self.getControlRadioButton(clz.OK_CONTROL_ID)
                self.cancel_radio_button = self.getControlRadioButton(clz.CANCEL_CONTROL_ID)
                self.ok_radio_button.setLabel(Messages.get_msg(Messages.OK))
                self.ok_radio_button.setVisible(True)

                self.cancel_radio_button.setLabel(Messages.get_msg(Messages.CANCEL))
                self.cancel_radio_button.setVisible(True)
                self.items_label = self.getControlLabel(42)

                xbmc.log(f'len(radio_controls): {len(self.radio_controls)}',
                                  xbmc.LOGINFO)
                clz.initialized = True

            self.update_choices(title=self.title,
                                choices=self._choices,
                                sub_title=self.sub_title,
                                initial_choice=self._initial_choice,
                                call_on_focus=self._call_on_focus)

        except Exception as e:
            clz._logger.exception("Failed to initialize")
            self.close()

        clz._logger.debug_verbose('SelectionDialog.onInit exiting')

    def update_choices(self, title: str,
                       choices: List[Choice], initial_choice: int,
                       sub_title: str | None = None,
                       call_on_focus: Callable[Choice, None] | None = None):
        clz = SelectionDialog
        # Used to convey the selection when DONE. Set to -1 on CANCEL
        self.close_selected_idx = -1

        self.title: str = title
        self.sub_title: str = sub_title
        clz._logger.debug(f'sub_title: {sub_title}')
        self._choices = choices
        self._initial_choice = initial_choice
        if self._initial_choice < 0:
            self._initial_choice = 0
        self._call_on_focus = call_on_focus
        xbmc.log(f'len radio_controls 3: {len(self.radio_controls)}', xbmc.LOGINFO)
        self.heading_control.setLabel(self.title)
        if self.sub_title is not None:
            self.sub_heading_control.setLabel(self.sub_title)
            self.sub_heading_control.setVisible(True)
        else:
            self.sub_heading_control.setVisible(False)

        for idx in range(0, min(len(self._choices),
                                200)):
            radio_button_control = self.radio_controls[idx]
            choice: Choice = self._choices[idx]
            radio_button_control.setLabel(choice.label)
            radio_button_control.setVisible(True)
            radio_button_control.setEnabled(choice.enabled)

        start: int = min(len(self._choices), 200)
        stop: int = min(200, self._previous_num_items)

        for idx in range(start, stop):
            clz._logger.debug(f'idx: {idx}')
            radio_button_control = self.radio_controls[idx]
            radio_button_control.setVisible(False)

        choice: Choice = self._choices[self._initial_choice]
        clz._logger.debug_verbose(f'SelectionDialog.onInit setting focus on'
                                  f' control: {101 + self._initial_choice:d}'
                                  f' value: {choice.label}')
        label: str = MessageUtils.get_formatted_msg_by_id(MessageId.DIALOG_N_OF_M_ITEMS,
                                                          str(1),
                                                          str(len(self._choices)))
        self.items_label.setLabel(label)

        self.selection_index = self._initial_choice
        control_id: int = self._initial_choice + 101
        radio_button_control = self.radio_controls[control_id]
        radio_button_control.setSelected(True)
        self.setFocusId(control_id)

        self._previous_num_items = len(self._choices)
        self.big_group.setVisible(True)

    def getControlButton(self, iControlId: int) -> ControlButton:
        clz = type(self)
        buttonControl: Control = super().getControl(iControlId)
        buttonControl: ControlButton
        return buttonControl

    def getControlEdit(self, iControlId: int) -> ControlEdit:
        control: Control = super().getControl(iControlId)
        control: xbmcgui.ControlEdit
        return control

    def getControlGroup(self, iControlId: int) -> ControlGroup:
        control: Control = super().getControl(iControlId)
        control: ControlGroup
        return control

    def getControlLabel(self, iControlId: int) -> ControlLabel:
        control: Control = super().getControl(iControlId)
        control: ControlLabel
        return control

    def getControlRadioButton(self, iControlId: int) -> ControlRadioButton:
        control: Control = super().getControl(iControlId)
        control: ControlRadioButton
        return control

    def getControlSlider(self, iControlId: int) -> ControlSlider:
        control: Control = super().getControl(iControlId)
        control: ControlSlider
        return control

    def doModal(self) -> None:
        """

        :return:
        """
        clz = type(self)
        clz._logger.debug_verbose('SelectionDialog.doModal enter. About to call show')
        try:
            self.show()
            # xbmc.sleep(10000)
            clz._logger.debug_verbose('SelectionDialog.doModal about to call super')
            super().doModal()
        except Exception as e:
            clz._logger.exception('SelectionDialog.show')
        return

    def show(self) -> None:
        """

        :return:
        """
        clz = type(self)
        clz._logger.debug_verbose('SelectionDialog.show about to call super')
        super().show()
        clz._logger.debug_verbose('SelectionDialog.show returned from super.')

        # self.ok_radio_button.setVisible(True)
        # self.cancel_radio_button.setVisible(True)
        # clz._logger.debug_verbose('SelectionDialog.show exiting')

    def close(self) -> None:
        """

        :return:
        """
        clz = type(self)
        clz._logger.debug_verbose('SelectionDialog.close')
        super().close()

    def getFocus(self) -> None:
        """

        :return:
        """
        clz = type(self)
        clz._logger.debug('SelectionDialog.getFocus')
        super().getFocus()

    def onAction(self, action: xbmcgui.Action) -> None:
        """

        :param action:
        :return:
        """
        clz = type(self)
        try:
            if not self.initialized:
                return

            action_id = action.getId()
            if action_id == 107:  # Mouse Move
                return

            buttonCode: int = action.getButtonCode()
            clz._logger.debug(
                    'SelectionDialog.onAction action_id: {} buttonCode: {}'.
                    format(action_id, buttonCode))
            if (action_id == xbmcgui.ACTION_PREVIOUS_MENU
                    or action_id == xbmcgui.ACTION_NAV_BACK):
                exit_dialog = True
                self.close()
        except Exception as e:
            clz._logger.exception('')

        # clz._logger.debug_verbose('SelectionDialog.onAction selectedPosition: {:d}'
        #                 .format(self.list_control.getSelectedPosition()))
        # display_value = self.list_control.getSelectedItem()
        # if display_value is not None:
        #    clz._logger.debug_verbose('SelectionDialog.onAction selectedItem: {}'.
        #                     format(display_value.getLabel()))

    def onControl(self, controlId):
        clz = type(self)
        clz._logger.debug_verbose(
                'SelectionDialog.onControl controlId: {:d}'.format(controlId))

    def onClick(self, controlId):
        clz = type(self)
        try:
            clz._logger.debug_verbose(
                    'SelectionDialog.onClick controlId: {:d}'.format(controlId))

            focus_id = self.getFocusId()
            clz._logger.debug('SelectionDialog.onClick FocusId: ' + str(focus_id))

            # if controlId == self.list_control.getId():
            #    clz._logger.debug_verbose('SelectionDialog List control 3 pressed')
            # x = xbmc.executebuiltin('Skin.String(category)',True)

            if controlId == clz.OK_CONTROL_ID:
                self.close_selected_idx = self.selection_index
                # OK radio_button
                self.close()

            elif controlId == clz.CANCEL_CONTROL_ID:
                # Cancel. Reset to original choice

                # self.getControl(3).selectItem(self._initial_choice)
                self.close()

            elif (controlId > 100) and (controlId < (101 + len(self._choices))):
                # Deselect previous
                if self.selection_index >= 0:
                    radio_button: ControlRadioButton = self.getControlRadioButton(
                            101 + self.selection_index)
                    radio_button.setSelected(False)

                self.selection_index = controlId - 101
                radio_button: ControlRadioButton = self.getControlRadioButton(controlId)
                radio_button.setSelected(True)
                if self._call_on_select is not None:
                    idx: int = controlId - 101
                    choice = self._choices[idx]
                    choice: Choice
                    self._call_on_select(choice, idx)

        except Exception as e:
            clz._logger.exception('')

    def onDoubleClick(self, controlId):
        clz = type(self)
        clz._logger.debug_verbose(
                f'SelectionDialog.onDoubleClick controlId: {controlId:d}')

    def onFocus(self, controlId: int):
        clz = type(self)
        try:
            if not self.initialized:
                return
            if self._call_on_focus is not None:
                if (controlId > 100) and (controlId < (101 + len(self._choices))):
                    idx: int = controlId - 101
                    choice = self._choices[idx]
                    choice: Choice
                    self._call_on_focus(choice, idx)
        except Exception as e:
            clz._logger.exception('')

    def setProperty(self, key, value):
        clz = type(self)
        clz._logger.debug_verbose(f'SelectionDialog.setProperty key: {key} '
                                  f'value: {value}')
        super(key, value)

    def addItem(self, item: str, position: int = 20000) -> None:
        """
        Add a new item to this WindowList.

        :param item: string, item to add.
        :param position: [opt] integer - position of item to add.
            (NO Int = Adds to bottom,0 adds to top, 1 adds to one below from top,
            -1 adds to one above from bottom etc etc )
            If integer positions are greater than list size, negative positions
            will add to top of list, positive positions will add
            to bottom of list

        Example::

            self.addItem('Reboot Kodi', 0)
        """
        clz = type(self)
        clz._logger.debug_verbose(
                f'SelectionDialog.addItem unexpected call item: {item}'
        )
        '''
        self.list_control.addItem(item)
        if position is None:
            self.display_values.append(item)
            self.list_position = len(self.display_values) - 1
        else:
            self.display_values.insert(position, item)
            self.list_position = position

        self.debug_display_values('addItem')
        '''

    def addItems(self, items: List[str]) -> None:
        """
        Add a list of items to the window list.

        :param items: List - list of strings to add.

        Example::

            self.addItems(['Reboot Kodi', 'Restart Kodi'])
        """
        clz = type(self)
        clz._logger.debug_verbose(
                f'SelectionDialog.addItems unexpected call item length: {len(items)}')
        '''
        # self.list_control.addItems(items)

        if len(items) > 0:
            self.display_values.extend(items)
            # self.list_position = len(self.display_values)
        self.debug_display_values('addItems')
        '''

    def removeItem(self, position: int) -> None:
        """
        Removes a specified item based on position, from the WindowList.

        :param position: integer - position of item to remove.

        Example::

            self.removeItem(5)
        """
        clz = type(self)
        clz._logger.debug_verbose('SelectionDialog.removeItem unexpected call item: {:d}'
                                  .format(position))
        '''
        self.list_control.removeItem(position)

        if self.display_values.get(position, None) is not None:
            del self.display_values[position]
            if self.list_position > len(self.display_values):
                self.list_position = max(len(self.display_values) - 1, 0)
        self.debug_display_values('removeItem')
        '''

    def getCurrentListPosition(self) -> int:
        """
        Gets the current position in the WindowList.

        Example::

            pos = self.getCurrentListPosition()
        """
        number_selected = 0
        selected = -1
        # for idx in range(0, self.list_control.size() - 1):
        #    if self.list_control.getListItem(idx).isSelected():
        #        number_selected += 1
        #        selected = idx

        # selected_position = int(self.getProperty('selected'))

        # self.debug_display_values('SelectionDialog.getCurrentListPosition # selected: {:d}'
        #                      .format(number_selected))
        clz = type(self)
        clz._logger.debug_verbose(
                f'SelectionDialog.getCurrentListPosition selected position: '
                f'{self.selection_index}')
        return self.selection_index

    def setCurrentListPosition(self, position: int) -> None:
        """
        Set the current position in the WindowList.

        :param position: integer - position of item to set.

        Example::

            self.setCurrentListPosition(5)
        """
        self.debug_display_values(
                f'SelectionDialog.setCurrentListPosition unexpected call: {position}')
        '''
        self.list_control.selectItem(position)
        self.getListItem(position).select(True)

        self.selected_item_index = self.getCurrentListPosition()
        self.selected_item = self.getListItem(self.selected_item_index).getLabel()

        if position > max(len(self.display_values) - 1, 0):
            position = 0
        self.list_position = position
        self.debug_display_values('setCurrentListPosition')
        '''

    def getListSize(self) -> int:
        """
        Returns the number of items in this WindowList.

        Example::

            listSize = self.getListSize()
        """
        self.debug_display_values('getListSize')

        # return len(self.display_values)
        return 0

    def clearList(self) -> None:
        """
        Clear the WindowList.

        Example::

            self.clearList()
        """
        # self.list_control.reset()
        clz = type(self)
        clz._logger.debug_verbose('SelectionDialog.clearList')
        self.debug_display_values('clearList')

    def debug_display_values(self, text: str) -> None:
        pass
        # clz._logger.debug_verbose('{} len display_values: {:d}'
        #                 .format(text, self.list_control.size()))
