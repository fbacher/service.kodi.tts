# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import queue
import sys
from collections import namedtuple

import xbmc
import xbmcgui
from xbmcgui import (Control, ControlButton, ControlEdit, ControlGroup, ControlLabel,
                     ControlRadioButton, ControlSlider, ControlList, ListItem)

import utils.util
from common import *

from common.constants import Constants
from common.logger import *
from common.message_ids import MessageId, MessageUtils
from common.messages import Messages
from common.monitor import Monitor
from welcome.subjects import (Category, CategoryRef, Load, MessageRef, Subject,
                              SubjectRef,
                              Utils)
from windowNavigation.choice import Choice

MY_LOGGER = BasicLogger.get_logger(__name__)


class SelectionDialog(xbmcgui.WindowXMLDialog):
    HEADING_CONTROL_ID: Final[int] = 1
    SUB_HEADING_CONTROL_ID: Final[int] = 4
    HEADER_SUB_HEADER_GROUP_ID: Final[int] = 1001
    OPTIONS_GROUP_LIST: Final[int] = 3

    FULL_SCREEN_GROUP_ID: Final[int] = 1000
    SELECTION_LIST_GROUP_ID: Final[int] = 1003
    LIST_CONTROL_ID: Final[int] = 3
    RETURN_TO_PREVIOUS_MENU: str = MessageRef.RETURN_TO_PREVIOUS_MENU.get_msg()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """

        :param args:
        """
        super().__init__(*args, **kwargs)
        self.abort: bool = False  # Set to True after abort received
        self.initialized: bool = False
        clz = type(self)
        Load.load_help()
        MY_LOGGER.debug('SelectionDialog.__init__')
        Monitor.register_abort_listener(self.on_abort_requested)
        self.EMPTY_DISPLAY_VALUES: Final[List[Choice]] = []
        self.list_position: int = 0
        self.full_window_group: xbmcgui.ControlGroup | None = None
        self.selection_index: int = -1
        self.title: str = kwargs.get('title', 'No Heading')
        self.sub_title: str | None = kwargs.get('sub_title', None)
        MY_LOGGER.debug(f'sub_title: {self.sub_title}')
        self._choices: List[Choice]
        self._choices = kwargs.get('choices', self.EMPTY_DISPLAY_VALUES)
        MY_LOGGER.debug(f'# choices: {len(self._choices)}')
        self._selected_idx: int = kwargs.get('initial_choice', -1)
        if self._selected_idx < 0:
            self._selected_idx = 0
        MY_LOGGER.debug(f'selected_idx: {self._selected_idx}')

        self.is_modal: bool = False
        self._call_on_focus: Callable[Choice, None] | None
        self._call_on_focus = kwargs.get('call_on_focus', None)
        self._call_on_select: Callable[Choice, None] | None
        self._call_on_select = kwargs.get('call_on_select', None)

        # True when it is safe to update the gui.
        # You can not update when not in doModal or show until OnInit is complete.
        # OnInit is run each time doModal is run. Show doesn't or does not
        # reliably run OnInit. Odd.

        self.disable_tts: bool = kwargs.get('disable_tts', False)
        self.heading_control: ControlLabel | None = None
        self.sub_heading_control: ControlLabel | None = None

        self.gui_updates_allowed: bool = False
        self._callback:  Callable[[Any], None] | None = kwargs.get('callback', None)
        self.heading_group_control: ControlGroup | None = None
        self.selection_list_group: ControlGroup | None = None
        self.list_control: ControlList | None = None
        self.list_items: List[ListItem] = []
        self.close_selected_idx: int = -1

    def onInit(self):
        """

        :return:
        """
        # super().onInit()
        clz = type(self)
        MY_LOGGER.debug('SelectionDialog.onInit enter')
        self.initialized = False
        try:
            Monitor.exception_on_abort(timeout=0.01)
            self.configure_heading()
            self.configure_selection_list()
            self.update_choices(title=self.title,
                                choices=self._choices,
                                sub_title=self.sub_title,
                                initial_choice=self._selected_idx,
                                call_on_focus=self._call_on_focus,
                                disable_tts=self.disable_tts)
            self.initialized = True
        except AbortException:
            self.abort = True
            self.close()
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception("Failed to initialize")
            self.close()
        MY_LOGGER.debug_v('SelectionDialog.onInit EXIT')

    def configure_heading(self) -> None:
        """
        Called by OnInit to configure the Window heading

        :return:
        """
        clz = SelectionDialog
        self.full_window_group = self.getControlGroup(SelectionDialog.FULL_SCREEN_GROUP_ID)
        #  DON'T completely blank screen. Impacts voicing and flickers screen.
        # self.full_window_group.setVisible(False)

        self.heading_group_control = self.getControlGroup(
                clz.HEADER_SUB_HEADER_GROUP_ID)
        self.heading_control = self.getControlLabel(clz.HEADING_CONTROL_ID)
        MY_LOGGER.debug(f'Got heading ctrl: 1')
        self.sub_heading_control = (self.getControlLabel
                                    (SelectionDialog.SUB_HEADING_CONTROL_ID))
        MY_LOGGER.debug(f'Got heading ctrl: 4')
        Monitor.exception_on_abort(timeout=0.01)

    def configure_selection_list(self) -> None:
        """
        Called by onInit to configure the list control for selecting subjects
        to view.

        :return:
        """
        clz = SelectionDialog
        self.selection_list_group = self.getControlGroup(
                clz.SELECTION_LIST_GROUP_ID)
        #  Can't Lose focus on this control
        self.list_control = self.getControlList(clz.LIST_CONTROL_ID)

    def update_choices(self, title: str,
                       choices: List[Choice],
                       initial_choice: int,
                       sub_title: str | None = None,
                       call_on_focus: Callable[Choice, None] | None = None,
                       call_on_select: Callable[Choice, None] | None = None,
                       disable_tts: bool = False):
        """
        Provides a means for SelectionDialog to be a single, reusable instance

        :param title:  Heading for the dialog
        :param choices:  List of available choices to present
        :param initial_choice:  Index of the current choice in choices
        :param sub_title:  Optional Sub-Heading for the dialog
        :param call_on_focus:  Optional call-back function for on-focus events
                              useful for hearing the difference immediately
        :param call_on_select: Optional call-back function for on-click events
                              useful for voicing the selected item immediately
        :param disable_tts: When True TTS screen-scraping is disabled until this
                            dialog text_exists. See Notes
        :return: Returns the underlying SelectionDialog so that methods can be
                called such as doModal

        Note: Any changes made in SettingsDialog are either committed or undone
        on exit. Selecting any choice commits the changes in to the settings
        cache. Only when the changes are committed in SettingsDialog are
        the committed to settings.xml.
        Leaving SelectionDialog via the 'Back' button reverts all changes
        using a backup-copy.

        Note: disable_tts is used when the language and engine need to be switched
        while voicing the dialog.
        """
        clz = SelectionDialog
        # Used to convey the selection when DONE. Set to -1 on exit without
        # saving (BACK button).
        if choices is None:
            choices = []

        # Choices can have zero length
        self._choices = choices
        self._selected_idx = initial_choice
        if self._selected_idx < 0:
            self._selected_idx = 0

        MY_LOGGER.debug(f'# choices: {len(self._choices)}')
        new_list_items: List[ListItem] = []
        for choice in self._choices:
            choice: Choice
            list_item: ListItem
            list_item = ListItem(label=f'{choice.label}', label2=f'hint{choice.hint}')
            new_list_items.append(list_item)

        self.list_control.reset()
        self.list_control.addItems(new_list_items)
        self.list_items = new_list_items
        self.list_control.selectItem(self._selected_idx)
        self.list_control.setVisible(True)
        self.selection_list_group.setVisible(True)
        self.setFocus(self.list_control)
        self._call_on_focus = call_on_focus
        self.update_heading(title=title, sub_title=sub_title)

        self.full_window_group.setVisible(True)
        self.gui_updates_allowed = True
        Monitor.exception_on_abort(timeout=0.01)

    def update_heading(self, title: str, sub_title: str = ''):
        """
        Called during onInit to update the heading values and make visible

        :param title:
        :param sub_title:
        :return:
        """
        clz = SelectionDialog
        self.title = title
        self.sub_title = sub_title
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'sub_title: {sub_title}')
        self.heading_control.setLabel(self.title)
        self.heading_control.setVisible(True)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'HEADING set to title: {self.title}')
        if self.sub_title is not None:
            self.sub_heading_control.setLabel(self.sub_title)
            self.sub_heading_control.setVisible(True)
        else:
            self.sub_heading_control.setVisible(False)
        self.heading_group_control.setVisible(True)
        Monitor.exception_on_abort(timeout=0.01)

    def process_selection(self, select_idx: int) -> None:
        """
        Called when a user selects something from the subject/category list.

        :param select_idx: Item selected
        :return:
        """
        clz = SelectionDialog
        # Voice the text for this selection
        choice: int = self.list_control.getSelectedPosition()
        MY_LOGGER.debug(f'list_control position: {choice}')
        choice_value: str = ''
        choice_type: str = ''
        """
         
        """
        Monitor.exception_on_abort(timeout=0.01)

    def setProperty(self, key, value):
        """
        Sets Window properties so that the screen scraper can detect and
        use the values.

        :param key:
        :param value:
        :return:
        """
        clz = type(self)
        MY_LOGGER.debug_v(f'SelectionDialog.setProperty key: {key} '
                          f'value: {value}')
        super().setProperty(key, value)

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

    def getControlList(self, iControlId: int) -> ControlList:
        clz = type(self)
        list_control: Control = super().getControl(iControlId)
        list_control: ControlList
        return list_control

    def doModal(self) -> None:
        """

        :return:
        """
        clz = type(self)
        try:
            Monitor.exception_on_abort(timeout=0.01)
            MY_LOGGER.debug('SelectionDialog.doModal about to call super')
            self.is_modal = True
            super().doModal()
            MY_LOGGER.debug(f'No longer Modal')
            self.is_modal = False
        except Exception as e:
            MY_LOGGER.exception('SelectionDialog.doModal')
        return

    def show(self) -> None:
        """

        :return:
        """
        clz = type(self)
        if self.abort:
            return
        MY_LOGGER.debug('SelectionDialog.show about to call super')
        super().show()

        MY_LOGGER.debug('SelectionDialog.show exiting')

    def close(self) -> None:
        """

        :return:
        """
        clz = type(self)
        if not self.abort:
            MY_LOGGER.debug('SelectionDialog.close')
        self.gui_updates_allowed = True
        self.is_modal = False
        super().close()

    def getFocus(self) -> None:
        """

        :return:
        """
        clz = type(self)
        MY_LOGGER.debug('SelectionDialog.getFocus')
        super().getFocus()

    def on_abort_requested(self):
        try:
            xbmc.log('Received AbortRequested', xbmc.LOGINFO)
            self.close()
        except Exception:
            pass

    def onAction(self, action: xbmcgui.Action) -> None:
        """

        :param action:
        :return:
        """
        clz = type(self)
        try:
            if not self.initialized:
                return

            Monitor.exception_on_abort(timeout=0.01)

            action_id = action.getId()
            if action_id == 107:  # Mouse Move
                return

            buttonCode: int = action.getButtonCode()
            # MY_LOGGER.debug(
            #         f'SelectionDialog.onAction focus_id: {self.getFocusId()}'
            #         f' action_id: {action_id} buttonCode: {buttonCode}')
            if (action_id == xbmcgui.ACTION_PREVIOUS_MENU
                    or action_id == xbmcgui.ACTION_NAV_BACK):
                # No selection made
                self.close_selected_idx = -1
                self.close()
            if action_id == xbmcgui.ACTION_SELECT_ITEM:
                focus_id: int = self.getFocusId()
                if focus_id == self.LIST_CONTROL_ID:
                    try:
                        if not self.initialized or not self.selection_list_group.isVisible():
                            return
                        self.selection_index = self.list_control.getSelectedPosition()
                        choice: Choice = self._choices[self.selection_index]
                        self.close_selected_idx: int = self.selection_index
                        self.close()

                    except AbortException:
                        self.abort = True
                        self.close()
                        reraise(*sys.exc_info())
                    except Exception as e:
                        MY_LOGGER.exception('')

            if action_id in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_MOVE_UP):
                # Cursor up/down will almost certainly change the position
                # of the list container. Could add check to see if selected
                # position changed.
                focus_id: int = self.getFocusId()
                if focus_id == self.LIST_CONTROL_ID:
                    try:
                        if not self.initialized or not self.selection_list_group.isVisible():
                            return
                        if self._call_on_focus is not None:
                            self.selection_index = self.list_control.getSelectedPosition()
                            choice: Choice = self._choices[self.selection_index]
                            self._call_on_focus(choice, self.selection_index)
                    except AbortException:
                        self.abort = True
                        self.close()
                        reraise(*sys.exc_info())
                    except Exception as e:
                        MY_LOGGER.exception('')

        except AbortException:
            self.abort = True
            self.close()
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

        # MY_LOGGER.debug('SelectionDialog.onAction selectedPosition: {:d}'
        #                 .format(self.list_control.getSelectedPosition()))
        # display_value = self.list_control.getSelectedItem()
        # if display_value is not None:
        #    MY_LOGGER.debug('SelectionDialog.onAction selectedItem: {}'.
        #                     format(display_value.getLabel()))

    def onControl(self, controlId):
        clz = type(self)
        MY_LOGGER.debug(
                'SelectionDialog.onControl controlId: {:d}'.format(controlId))

    def onClick(self, controlId):
        """
        Called when a 'clickable' control is 'clicked' by a mouse. Typically
        a button or anything selectable.

        :param controlId:
        :return:
        """
        clz = type(self)
        try:
            MY_LOGGER.debug(
                    'SelectionDialog.onClick controlId: {:d}'.format(controlId))
            focus_id = self.getFocusId()
            MY_LOGGER.debug('SelectionDialog.onClick FocusId: ' + str(focus_id))
            # if controlId == self.list_control.getId():
            #    MY_LOGGER.debug('SelectionDialog List control 3 pressed')
            # x = xbmc.executebuiltin('Skin.String(category)',True)

            if controlId == clz.LIST_CONTROL_ID:
                self.process_selection(self.selection_index)
        except AbortException:
            self.abort = True
            self.close()
            reraise(*sys.exc_info())

        except Exception as e:
            MY_LOGGER.exception('')

    def onDoubleClick(self, controlId):
        clz = type(self)
        MY_LOGGER.debug(
                f'SelectionDialog.onDoubleClick controlId: {controlId:d}')

    def onFocus(self, controlId: int):
        clz = type(self)
        MY_LOGGER.debug(f'onFocus controlId: {controlId}')
        try:
            if not self.initialized or not self.selection_list_group.isVisible():
                return
            if self._call_on_focus is not None:
                self.selection_index = self.list_control.getSelectedPosition()
                choice: Choice = self._choices[self.selection_index]
                self._call_on_focus(choice, self.selection_index)
        except AbortException:
            self.abort = True
            self.close()
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

    def hlp_dialg_abrt(self):  # Short name that shows up in debug log
        try:
            self.abort = True
            xbmc.log('SelectionDialog Received AbortRequested', xbmc.LOGINFO)
            self.close()
        except Exception:
            pass

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
        MY_LOGGER.debug(
                f'SelectionDialog.addItem unexpected call item: {item}')

    def addItems(self, items: List[str]) -> None:
        """
        Add a list of items to the window list.

        :param items: List - list of strings to add.

        Example::

            self.addItems(['Reboot Kodi', 'Restart Kodi'])
        """
        clz = type(self)
        MY_LOGGER.debug(
                f'SelectionDialog.addItems unexpected call item length: {len(items)}')

    def removeItem(self, position: int) -> None:
        """
        Removes a specified item based on position, from the WindowList.

        :param position: integer - position of item to remove.

        Example::

            self.removeItem(5)
        """
        clz = type(self)
        MY_LOGGER.debug('SelectionDialog.removeItem unexpected call item: {:d}'
                                  .format(position))

    def getCurrentListPosition(self) -> int:
        """
        Gets the current position in the list container.

        Example:
            pos = self.getCurrentListPosition()
        """

        clz = type(self)
        MY_LOGGER.debug(
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

    def getListSize(self) -> int:
        """
        Returns the number of items in this WindowList.

        Example::

            listSize = self.getListSize()
        """
        self.debug_display_values('getListSize')

        # return len(self.display_values)
        return len(self._choices)

    def clearList(self) -> None:
        """
        Clear the WindowList.

        Example::

            self.clearList()
        """
        # self.list_control.reset()
        clz = type(self)
        MY_LOGGER.debug('SelectionDialog.clearList')
        self.debug_display_values('clearList')

    def debug_display_values(self, text: str) -> None:
        pass
        # MY_LOGGER.debug('{} len display_values: {:d}'
        #                 .format(text, self.list_control.size()))
