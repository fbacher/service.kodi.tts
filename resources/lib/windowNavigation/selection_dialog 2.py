# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc
import xbmcgui
from xbmcgui import (Control, ControlButton, ControlEdit, ControlGroup, ControlLabel,
                     ControlRadioButton, ControlSlider)

from common import *

from common.constants import Constants
from common.logger import *
from common.messages import Messages
from windowNavigation.choice import Choice

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_logger(__name__)

else:
    module_logger = BasicLogger.get_logger(__name__)


class SelectionDialog(xbmcgui.WindowXMLDialog):
    _logger: BasicLogger
    initialized: bool = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """

        :param args:
        """
        super().__init__(*args, **kwargs)
        clz = type(self)
        self.exit_dialog: bool = False
        clz._logger = module_logger
        clz._logger.debug('SelectionDialog.__init__')
        empty_display_values: List[Choice] = []
        self.list_position: int = 0
        self.selection_index: int = -1
        self.title: str = kwargs.get('title', 'No Heading')
        self._choices: List[Choice]
        self._choices = kwargs.get('choices', empty_display_values)
        self._initial_choice: int = kwargs.get('initial_choice', -1)
        if self._initial_choice < 0:
            self._initial_choice = 0
        self._call_on_focus: Callable[Choice, None] | None
        self._call_on_focus = kwargs.get('call_on_focus', None)
        self.group_list: xbmcgui.Control = None
        self.heading_control: ControlLabel | None = None
        self.choices_group: ControlGroup | None = None
        # GroupList's radio_controls
        self.radio_controls: List[ControlRadioButton] = []
        self.cancel_radio_button: ControlRadioButton | None = None
        self.number_of_radio_controls: int = 0
        self.ok_radio_button: ControlRadioButton | None = None
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
            if True:
                self.heading_control = self.getControlLabel(1)
                self.heading_control.setLabel(self.title)
                self.group_list = self.getControl(3)
                self.group_list.setVisible(False)
                self.selection_index = self._initial_choice

                clz = SelectionDialog
                # self.title: str = title
                # self._choices = choices
                # self._initial_choice = initial_choice
                if self._initial_choice < 0:
                    self._initial_choice = 0
                # self._call_on_focus = call_on_focus
                xbmc.log(f'len radio_controls 3: {len(self.radio_controls)}',
                         xbmc.LOGINFO)
                for idx in range(0, min(len(self._choices),
                                        301)):
                    clz._logger.debug(f'{len(self.radio_controls)} idx: {idx}')
                    radio_button_control = self.radio_controls[idx]
                    choice: Choice = self._choices[idx]
                    radio_button_control.setLabel(choice.label)
                    radio_button_control.setVisible(True)
                    radio_button_control.setEnabled(choice.enabled)

                choice: Choice = self._choices[self._initial_choice]
                radio_button_control = self.radio_controls[self._initial_choice + 101]
                radio_button_control.setSelected(True)
                self.setFocusId(radio_button_control.getId())
                label: str = choice.label
                clz._logger.debug_verbose(f'SelectionDialog.onInit setting focus on'
                                          f' control: {101 + self._initial_choice:d}'
                                          f' value: {label}')

                for idx in range(min(len(self._choices + 1), 302), 301):
                    radio_button_control = self.radio_controls[idx]
                    radio_button_control.setVisible(False)

                self.ok_radio_button.setLabel(Messages.get_msg(Messages.OK))
                self.ok_radio_button.setVisible(True)

                self.cancel_radio_button.setLabel(Messages.get_msg(Messages.CANCEL))
                self.cancel_radio_button.setVisible(True)
                clz._logger.debug(f'len(radio_controls): {len(self.radio_controls)}',
                                  xbmc.LOGINFO)
                clz.initialized = True

        except Exception as e:
            clz._logger.exception("Failed to initialize")
            self.close()

        clz._logger.debug_verbose('SelectionDialog.onInit exiting')

    def update_choices(self, title: str,
                       choices: List[Choice], initial_choice: int,
                       call_on_focus: Callable[Choice, None] | None = None):
        clz = SelectionDialog
        self.title: str = title
        self._choices = choices
        self._initial_choice = initial_choice
        if self._initial_choice < 0:
            self._initial_choice = 0
        self._call_on_focus = call_on_focus
        xbmc.log(f'len radio_controls 3: {len(self.radio_controls)}', xbmc.LOGINFO)
        for idx in range(0, min(len(self._choices),
                                301)):
            clz._logger.debug(f'{len(self.radio_controls)} idx: {idx}')
            radio_button_control = self.radio_controls[idx]
            choice: Choice = self._choices[idx]
            radio_button_control.setLabel(choice.label)
            radio_button_control.setVisible(True)
            radio_button_control.setEnabled(choice.enabled)

        choice: Choice = self._choices[self._initial_choice]
        radio_button_control = self.radio_controls[self._initial_choice + 101]
        radio_button_control.setSelected(True)
        self.setFocusId(radio_button_control.getId())
        label: str = choice.label
        clz._logger.debug_verbose(f'SelectionDialog.onInit setting focus on'
                                  f' control: {101 + self._initial_choice:d}'
                                  f' value: {label}')

        for idx in range(min(len(self._choices + 1), 302), 301):
            radio_button_control = self.radio_controls[idx]
            radio_button_control.setVisible(False)

        self.ok_radio_button.setLabel(Messages.get_msg(Messages.OK))
        self.ok_radio_button.setVisible(True)

        self.cancel_radio_button.setLabel(Messages.get_msg(Messages.CANCEL))
        self.cancel_radio_button.setVisible(True)
        self.show()

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
            self.group_list.setVisible(True)
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
        # control 1 heading label
        # control 3 list of available options
        # control 5 radio_button OK
        # control 7 radio_button cancel
        #

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
            clz._logger.debug_verbose('SelectionDialog.onClick FocusId: ' + str(focus_id))

            # if controlId == self.list_control.getId():
            #    clz._logger.debug_verbose('SelectionDialog List control 3 pressed')
            # x = xbmc.executebuiltin('Skin.String(category)',True)

            if controlId == 5:
                # OK radio_button
                self.close()

            elif controlId == 7:
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
                '''
                # Invisible radio_button that relays onClick from list control 3,
                clz._logger.debug_verbose('SelectionDialog.onClick list size: {:d}'
                                 .format(self.list_control.size()))
                selected_position = -1
                try:
                    clz._logger.debug_verbose('selected index: {}'.format(
                    self.getProperty('selected')))
                    selected_position = int(self.getProperty('selected'))
                except Exception as e:
                    pass
                clz._logger.debug_verbose('Skin.String(selected: {})'
                                 .format(xbmc.getInfoLabel('Skin.String(selected)')))
    
                display_value = self.list_control.getListItem(selected_position)
                # display_value = self._choices[selected_position]
                if display_value is not None:
                    clz._logger.debug_verbose('SelectionDialog.onClick(100) list 
                    selectedItem: {} selected: {:b}'.
                                     format(display_value.getLabel(), display_value.isSelected()))
                    # Clear prior selections. Storing selection in ListItem is used by
                    # selection-dialog.xml to show selection
    
                    for idx in range(0, self.list_control.size() - 1):
                        self.list_control.getListItem(idx).select(False)
                        self.list_control.getListItem(idx).setPath('')
    
                    display_value.select(True)
                    display_value.setPath('true')
                '''
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
