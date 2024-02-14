# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmcgui
from xbmcgui import (Control, ControlButton, ControlEdit, ControlGroup, ControlLabel,
                     ControlRadioButton, ControlSlider, ListItem)

from common import *

from common.constants import Constants
from common.logger import *
from common.messages import Messages

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)

else:
    module_logger = BasicLogger.get_module_logger()


class SelectionDialog(xbmcgui.WindowXMLDialog):
    _logger: BasicLogger

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """

        :param args:
        """
        super().__init__(*args, **kwargs)
        clz = type(self)
        self.exit_dialog: bool = False
        clz._logger = module_logger.getChild(self.__class__.__name__)
        clz._logger.debug_verbose('SelectionDialog.__init__')
        self.initialized: bool = False
        empty_list_items: List[xbmcgui.ListItem] = []
        self.list_position: int = 0
        self.selection_index: int = -1
        self.title: str = kwargs.get('title', 'No Heading')
        self._init_list_items = kwargs.get('choices', empty_list_items)
        self._initial_choice: int = kwargs.get('initial_choice', -1)
        if self._initial_choice < 0:
            self._initial_choice = 0

        self.heading_control: ControlLabel | None = None
        self.choices_group: ControlGroup | None = None
        self.cancel_radio_button: ControlRadioButton | None = None
        self.ok_radio_button: ControlRadioButton | None = None

    def onInit(self):
        """

        :return:
        """
        # super().onInit()
        clz = type(self)
        clz._logger.debug_verbose('SelectionDialog.onInit enter')
        # control 1 heading label
        # control 3 list of available options
        # control 5 radio_button OK
        # control 7 radio_button cancel
        #

        # type: Union[None, xbmcgui.ControlLabel]

        try:
            if not self.initialized:
                self.heading_control = self.getControlLabel(1)
                self.heading_control.setLabel(self.title)
                # unused_control = self.getControl(3)
                '''def __init__(self, x, y, width, height, font=None, textColor=None,
                        radio_buttonTexture=None, radio_buttonFocusTexture=None,
                        selectedColor=None, _imageWidth=10, _imageHeight=10,
                        _itemTextXOffset=10, _itemTextYOffset=2, _itemHeight=27,
                        _space=2, _alignmentY=4):
                '''

                # self.list_control = xbmcgui.ControlList(x=unused_control.getX(),
                #                                        y=unused_control.getY(),
                #                                        width=unused_control.getWidth(),
                #                                        height=unused_control.getHeight())
                '''
                                                        font='font13',
                                                        textColor='white',
                                                        radio_buttonTexture='radio_button-focus2.png',
                                                        selectedColor='red',
                                                        _imageWidth=10,
                                                        _imageHeight=27,
                                                        _itemTextXOffset=10,
                                                        _itemTextYOffset=2,
                                                        _itemHeight=27,
                                                        _space=2,
                                                        _alignmentY=4)
                '''
                # unused_control.setVisible(False)
                # self.addControl(self.list_control)

                # self.list_control = self.getControl(3)  # type:
                # xbmcgui.ControlList
                idx = 0
                # for list_item in self._init_list_items:
                # clz._logger.debug_verbose('SelectionDialog.onInit passed size: {:d}
                # list size: {:d}'
                #                 .format(len(self._init_list_items),
                #                         self.list_control.size()))
                self.selection_index = self._initial_choice

                try:
                    for idx in range(0, min(len(self._init_list_items),
                                            201)):  # self.list_control.size() - 1):
                        # list_item = self.list_control.getListItem(idx)
                        list_item = self._init_list_items[idx]
                        # list_item.setLabel2(str(idx))
                        list_item.setPath('')
                        if idx == self.selection_index:
                            list_item.select(True)
                        else:
                            list_item.select(False)
                        radio_button_control: ControlRadioButton = \
                            self.getControlRadioButton(
                                    101 + idx)
                        label = list_item.getLabel()
                        radio_button_control.setLabel(label)
                        radio_button_control.setRadioDimension(
                                x=0, y=0, width=530, height=20)
                        radio_button_control.setVisible(True)
                        clz._logger.debug_verbose(
                                'SelectionDialog.onInit radio_button: {:d} label: {}'
                                .format(radio_button_control.getId(),
                                        label))

                    for idx in range(min(len(self._init_list_items), 201),
                                     201):  # self.list_control.size() - 1):
                        radio_button_control: ControlRadioButton = \
                            self.getControlRadioButton(
                                    101 + idx)
                        radio_button_control.setVisible(False)
                except Exception as e:
                    clz._logger.exception('Setting up List and evaluating response')

                radio_button_control: ControlRadioButton = self.getControlRadioButton(
                        101 + self.selection_index)

                label: str = self._init_list_items[self._initial_choice].getLabel()
                clz._logger.debug_verbose(
                        'SelectionDialog.onInit setting focus on control: {:d} value: {}'
                        .format(101 + self._initial_choice, label))

                # Focus on group control, should in turn focus on selected item
                radio_button_control.setSelected(True)
                self.setFocusId(radio_button_control.getId())

                # self._init_list_items[self._initial_choice].setPath('true')
                # self._init_list_items[self._initial_choice].select(True)

                # self.list_control.setStaticContent(self._init_list_items)
                # self.list_control.addItems(self._init_list_items)

                # self.choices_group = self.getControl(
                #    1000)  # type: xbmcgui.ControlGroup
                # self.choices_group.setVisible(True)
                self.initialized = True

            self.ok_radio_button = self.getControlRadioButton(5)
            self.ok_radio_button.setLabel(Messages.get_msg(Messages.OK))
            self.ok_radio_button.setVisible(True)

            self.cancel_radio_button = self.getControlRadioButton(7)
            self.cancel_radio_button.setLabel(Messages.get_msg(Messages.CANCEL))
            self.cancel_radio_button.setVisible(True)

        except Exception as e:
            clz._logger.exception("Failed to initialize")
            self.close()

        clz._logger.debug_verbose('SelectionDialog.onInit exiting')

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

    def doModal(self):
        # type: () -> None
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

    def show(self):
        # type: () -> None
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

    def getFocus(self):
        # type: () -> None
        """

        :return:
        """
        clz = type(self)
        clz._logger.debug_verbose('SelectionDialog.getFocus')
        super().getFocus()

    def onAction(self, action: xbmcgui.Action) -> None:
        """

        :param action:
        :return:
        """
        clz = type(self)
        try:
            action_id = action.getId()
            if action_id == 107:  # Mouse Move
                return

            buttonCode: int = action.getButtonCode()
            clz._logger.debug_verbose(
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
        # list_item = self.list_control.getSelectedItem()
        # if list_item is not None:
        #    clz._logger.debug_verbose('SelectionDialog.onAction selectedItem: {}'.
        #                     format(list_item.getLabel()))

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

            elif (controlId > 100) and (controlId < (101 + len(self._init_list_items))):
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
    
                list_item = self.list_control.getListItem(selected_position)
                # list_item = self._init_list_items[selected_position]
                if list_item is not None:
                    clz._logger.debug_verbose('SelectionDialog.onClick(100) list 
                    selectedItem: {} selected: {:b}'.
                                     format(list_item.getLabel(), list_item.isSelected()))
                    # Clear prior selections. Storing selection in ListItem is used by
                    # selection-dialog.xml to show selection
    
                    for idx in range(0, self.list_control.size() - 1):
                        self.list_control.getListItem(idx).select(False)
                        self.list_control.getListItem(idx).setPath('')
    
                    list_item.select(True)
                    list_item.setPath('true')
                '''
        except Exception as e:
            clz._logger.exception('')

    def onDoubleClick(self, controlId):
        clz = type(self)
        clz._logger.debug_verbose(
                f'SelectionDialog.onDoubleClick controlId: {controlId:d}')

    def onFocus(self, controlId: int):
        clz = type(self)
        clz._logger.debug_verbose(
                f'SelectionDialog.onFocus controlId: {controlId:d}')

    def setProperty(self, key, value):
        clz = type(self)
        clz._logger.debug_verbose(f'SelectionDialog.setProperty key: {key} '
                                  f'value: {value}')
        super(key, value)

    def addItem(self, item: str | xbmcgui.ListItem, position: int = 20000) -> None:
        """
        Add a new item to this WindowList.

        :param item: string, unicode or ListItem - item to add.
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
                f'SelectionDialog.addItem unexpected call item: {item.getLabel()}'
        )
        '''
        self.list_control.addItem(item)
        if position is None:
            self.list_items.append(item)
            self.list_position = len(self.list_items) - 1
        else:
            self.list_items.insert(position, item)
            self.list_position = position

        self.debug_list_items('addItem')
        '''

    def addItems(self, items: List[Union[str, xbmcgui.ListItem]]) -> None:
        """
        Add a list of items to to the window list.

        :param items: List - list of strings, unicode objects or ListItems to add.

        Example::

            self.addItems(['Reboot Kodi', 'Restart Kodi'])
        """
        clz = type(self)
        clz._logger.debug_verbose(
                f'SelectionDialog.addItems unexpected call item length: {len(items)}')
        '''
        # self.list_control.addItems(items)

        if len(items) > 0:
            self.list_items.extend(items)
            # self.list_position = len(self.list_items)
        self.debug_list_items('addItems')
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

        if self.list_items.get(position, None) is not None:
            del self.list_items[position]
            if self.list_position > len(self.list_items):
                self.list_position = max(len(self.list_items) - 1, 0)
        self.debug_list_items('removeItem')
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

        # self.debug_list_items('SelectionDialog.getCurrentListPosition # selected: {:d}'
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
        self.debug_list_items(
                f'SelectionDialog.setCurrentListPosition unexpected call: {position}')
        '''
        self.list_control.selectItem(position)
        self.getListItem(position).select(True)

        self.selected_item_index = self.getCurrentListPosition()
        self.selected_item = self.getListItem(self.selected_item_index).getLabel()

        if position > max(len(self.list_items) - 1, 0):
            position = 0
        self.list_position = position
        self.debug_list_items('setCurrentListPosition')
        '''

    def getListItem(self, position: int) -> ListItem:
        """
        Returns a given ListItem in this WindowList.

        :param position: integer - position of item to return.

        Example::

            listitem = self.getListItem(6)
        """
        self.debug_list_items('getListItem position: ' + str(position))

        # return self.list_items[position]
        # return self.list_control.getListItem(position)
        return None

    def getListSize(self) -> int:
        """
        Returns the number of items in this WindowList.

        Example::

            listSize = self.getListSize()
        """
        self.debug_list_items('getListSize')

        # return len(self.list_items)
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
        self.debug_list_items('clearList')

    def debug_list_items(self, text: str) -> None:
        pass
        # clz._logger.debug_verbose('{} len list_items: {:d}'
        #                 .format(text, self.list_control.size()))
