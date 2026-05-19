# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys
from enum import Enum

import xbmc
import xbmcgui
from xbmcgui import (Control, ControlButton, ControlEdit, ControlGroup, ControlLabel,
                     ControlRadioButton, ControlSlider, ControlList, ListItem)

from backends.settings.engine_voice import EngineVoice
from backends.settings.engine_voice_manager import EngineVoiceManager
from backends.settings.i_engine_voice_group import IEngineVoiceGroup
from common import *

from common.logger import *
from common.message_ids import MessageId
from common.monitor import Monitor
from common.setting_constants import DialogSubj
from welcome.subjects import (Load, MessageRef)
from windowNavigation.action_debug import Action
from windowNavigation.choice import (Choice, ChoiceDict, Choices, EngineChoice,
                                     EngineChoices,
                                     VGChoice, VGChoices,
                                     VoiceChoice, VoiceChoices)

MY_LOGGER = BasicLogger.get_logger(__name__)


class PopContextException(Exception):

    def __init__(self, msg: str = '',
                 sel_object: Choice | EngineChoice | VGChoice | VoiceChoice | None = None,
                 sel_idx: int | None = None):
        super().__init__(msg)
        self._sel_object: Choice | EngineChoice | VGChoice | VoiceChoice | None
        self._sel_object = sel_object
        self._sel_idx: int | None = sel_idx

    @property
    def sel_object(self) -> Choice | EngineChoice | VGChoice | VoiceChoice | None:
        return self._sel_object

    @property
    def sel_idx(self) -> int | None:
        return self._sel_idx


class ConfigStackEnum(Enum):
    POP = -1
    NONE = 0
    PUSH = 1


class SelectionData:

    current_config: SelectionData | None = None
    config_stack: List[SelectionData] = []

    @classmethod
    def push_config(cls, sel_data: 'SelectionData') -> bool:
        cls.config_stack.append(sel_data)
        cls.current_config = sel_data
        return True

    @classmethod
    def pop_config(cls) -> 'SelectionData':
        cls.config_stack.pop()
        cls.current_config = cls.config_stack[-1]
        return cls.current_config

    @classmethod
    def get_previous_config(cls) -> 'SelectionData | None':
        """
        Adds ability to modify the state of the previous configuration.
        Typically used to alter the selected item before restoring the state.
        """
        if len(cls.config_stack) < 2:
            return None
        return cls.config_stack[-2]

    def __init__(self,
                 dialog_subject: str,
                 title: str = 'No Heading',
                 sub_title: str | None = None,
                 choices: Choices | EngineChoices | VGChoices | VoiceChoices | None =
                 None,
                 selection_idx: int = -1,
                 call_on_focus: Callable[[Choice | EngineChoice | VoiceChoice |
                                          VGChoice, int], None] | None = None,
                 call_on_select: Callable[[Choice | EngineChoice | VoiceChoice |
                                           VGChoice, int], None] | None = None,
                 disable_tts: bool = False
                 ):
        """
        Provides a means for SelectionDialog to be a single, reusable instance

       :param dialog_subject: Used to distinguish the 'virtual' dialogs from one another
       :param title:  Heading for the dialog
       :param choices:  List of available choices to present
       :param selection_idx:  Current choice index
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
        self.EMPTY_DISPLAY_VALUES: Final[EngineChoices] = EngineChoices()
        self._dialog_subject: str = dialog_subject
        if choices is None:
            choices = EngineChoices()

        self._title: str = title
        self._sub_title: str | None = sub_title
        MY_LOGGER.debug(f'sub_title: {self.sub_title}')
        if choices is None:
            choices = self.EMPTY_DISPLAY_VALUES
        self._choices: Choices | EngineChoices | VGChoices | VoiceChoices = choices
        MY_LOGGER.debug(f'# choices: {len(self.choices)}')

        self._saved_choices: Choices | EngineChoices | VGChoices | VoiceChoices | None
        self._saved_choices = None
        self._selected_idx: int = -1
        self._selected_obj: Any = None
        self.selected_idx = selection_idx
        MY_LOGGER.debug(f'# choices {len(self.choices)} selected_idx: '
                        f'{self._selected_idx}')
        self._call_on_focus: Callable[[Choice | EngineChoice | VoiceChoice |
                                      VGChoice, int], None] | None = call_on_focus
        self._call_on_select: Callable[[Choice | EngineChoice | VoiceChoice |
                                       VGChoice, int], None] | None = call_on_select
        self._disable_tts: bool = disable_tts

    @property
    def choices(self) -> Choices | EngineChoices | VGChoices | VoiceChoices:
        return self._choices

    @choices.setter
    def choices(self, value: Choices | EngineChoices | VGChoices | VoiceChoices):
        self._choices = value

    @property
    def call_on_focus(self) -> Callable[[Choice | EngineChoice | VGChoice |
                                         VoiceChoice, int], None] | None:
        return self._call_on_focus

    @call_on_focus.setter
    def call_on_focus(self, value: Callable[[Choice | EngineChoice | VGChoice |
                                         VoiceChoice, int], None] | None) -> None:
        self._call_on_focus = value

    @property
    def call_on_select(self) -> Callable[[Choice | EngineChoice | VGChoice |
                                         VoiceChoice, int], None] | None:
        return self._call_on_select

    @call_on_select.setter
    def call_on_select(self, value: Callable[[Choices | EngineChoices | VGChoices |
                                         VoiceChoices, int], None] | None) -> None:
        self._call_on_select = value

    @property
    def selected_idx(self) -> int | None:
        """
        A value of -1 indicates there is no selection. Occurs when user chooses to
        exit dialog (menu back, or escape) canceling any previous selection.
        """
        return self._selected_idx

    @selected_idx.setter
    def selected_idx(self, idx: int) -> None:
        """
       A value of -1 indicates there is no selection. Occurs when user chooses to
       exit dialog (menu back, or escape) canceling any previous selection.
       """
        self._selected_idx = max(idx, -1)
        MY_LOGGER.debug(f'selected_idx: {self._selected_idx} choices: {len(self.choices)}')
        if self._selected_idx == -1:
            self.selected_obj = None
            return
        if len(self.choices) > 0:
            self.selected_obj = self.choices[self._selected_idx]

    @property
    def selected_obj(self) -> Any:
        return self._selected_obj

    @selected_obj.setter
    def selected_obj(self, obj: Any) -> None:
        self._selected_obj = obj

    @property
    def selected_voice(self) -> VoiceChoice:
        ev: VoiceChoice = self._selected_obj
        return ev

    @property
    def dialog_subject(self) -> str:
        """
        This physical dialog is used to display different data. This tags the
        data so that you can tell what it is for
        """
        return self._dialog_subject

    @property
    def disable_tts(self) -> bool:
        return self._disable_tts

    @property
    def saved_choices(self) -> Choices | EngineChoices | VGChoices | VoiceChoices:
        return self._saved_choices

    @saved_choices.setter
    def saved_choices(self, choices: Choices | EngineChoices | VGChoices |
                                         VoiceChoices | None) -> None:
        self._saved_choices = choices

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value

    @property
    def sub_title(self) -> str:
        return self._sub_title

    @sub_title.setter
    def sub_title(self, value: str) -> None:
        self._sub_title = value


class SelectionDialog(xbmcgui.WindowXMLDialog):
    HEADING_CONTROL_ID: Final[int] = 1
    SUB_HEADING_CONTROL_ID: Final[int] = 4
    HEADER_SUB_HEADER_GROUP_ID: Final[int] = 1001
    #  OPTIONS_GROUP_LIST: Final[int] = 3

    FULL_SCREEN_GROUP_ID: Final[int] = 50
    SELECTION_LIST_GROUP_ID: Final[int] = 1003
    LIST_CONTROL_ID: Final[int] = 1103  # 3
    LIST_SCROLLBAR_ID: Final[int] = 200
    OK_CANCEL_GROUP_ID: Final[int] = 9001
    OK_BUTTON_ID: Final[int] = 28
    CANCEL_BUTTON_ID: Final[int] = 29
    DEFAULTS_BUTTON_ID: Final[int] = 30
    RETURN_TO_PREVIOUS_MENU: str = MessageRef.RETURN_TO_PREVIOUS_MENU.get_msg()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Primarily initializes the essential kodi gui-elements. In addition,
        data must be supplied and initialized through the update_data method.
        The data is kept in SelectionData. By having a stack of SelectionData
        this dialog is reentrant as a user drills down.

        :param args: Passed directly to super().__init__()
        :param kwargs: Passed to super() after extracting several values:
                        sub_title and disable_tts.
        """
        #  MY_LOGGER.debug(f'kwargs: {kwargs}')
        super().__init__(*args, **kwargs)
        self.sel_data: SelectionData = SelectionData.current_config
        self.new_sel_data: SelectionData | None = None
        self.abort: bool = False  # Set to True after abort received
        self.initialized: bool = False
        self.closing = False
        self.exit_dialog = False
        self.is_modal: bool = False
        Load.load_help()
        MY_LOGGER.debug('SelectionDialog.__init__')
        Monitor.register_abort_listener(self.on_abort_requested)
        self.full_window_group: xbmcgui.ControlGroup | None = None

        # True when it is safe to update the gui.
        # You can not update when not in doModal or show until OnInit is complete.
        # OnInit is run each time doModal is run. Show doesn't or does not
        # reliably run OnInit. Odd.

        self.disable_tts: bool = kwargs.get('disable_tts', False)
        self.voice_the_voice: Callable[[Choice | EngineChoice | VoiceChoice |
                                        VGChoice, int], int] | None
        # Access to SettingsDialog.voice_the_voice
        self.voice_the_voice = kwargs.get('voice_the_voice', None)
        self.heading_control: ControlLabel | None = None
        self.sub_heading_control: ControlLabel | None = None

        self.gui_updates_allowed: bool = False
        self.heading_group_control: ControlGroup | None = None
        self.selection_list_group: ControlGroup | None = None
        self.list_control: ControlList | None = None
        self.list_items: List[ListItem] = []
        self.ok_button: ControlButton | None = None
        self.cancel_button: ControlButton | None = None
        self.defaults_button: ControlButton | None = None

    def onInit(self):
        """

        :return:
        """
        MY_LOGGER.debug('SelectionDialog.onInit enter')
        self.closing = False
        self.exit_dialog = False
        try:
            Monitor.exception_on_abort(timeout=0.01)
            self.configure_heading()
            self.configure_selection_list()
            self.configure_OK_CANCEL()
            self.post_onInit(push_pop=ConfigStackEnum.PUSH)
        except AbortException:
            self.abort = True
            reraise(*sys.exc_info())
            self.close()
        except Exception as e:
            MY_LOGGER.exception("Failed to initialize")
            self.close()
        MY_LOGGER.debug_v('SelectionDialog.onInit EXIT')

    def configure_heading(self) -> None:
        """
        Called by OnInit to cfg the Window heading

        :return:
        """
        clz = SelectionDialog
        self.full_window_group = self.getControlGroup(
            SelectionDialog.FULL_SCREEN_GROUP_ID)
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
        Called by onInit to cfg the list control for selecting subjects
        to view.

        :return:
        """
        clz = SelectionDialog
        self.selection_list_group = self.getControlGroup(
                clz.SELECTION_LIST_GROUP_ID)
        #  Can't Lose focus on this control
        self.list_control = self.getControlList(clz.LIST_CONTROL_ID)

    def configure_OK_CANCEL(self) -> None:
        """
        Called by onInit to cfg the OK_Cancel buttons
        """
        clz = type(self)
        self.ok_button: ControlButton = self.get_control_button(
                clz.OK_BUTTON_ID)
        self.ok_button.setLabel(MessageId.OK_BUTTON.get_msg())
        self.ok_button.setVisible(True)

        self.cancel_button = self.get_control_button(
                clz.CANCEL_BUTTON_ID)
        self.cancel_button.setLabel(MessageId.CANCEL_BUTTON.get_msg())
        self.cancel_button.setVisible(True)

        self.defaults_button: ControlButton = self.get_control_button(
                clz.DEFAULTS_BUTTON_ID)
        self.defaults_button.setLabel(MessageId.DEFAULTS_BUTTON.get_msg())
        self.defaults_button.setVisible(True)

    def set_visibility(self, visibile: bool) -> None:

        self.heading_control.setVisible(visibile)
        self.sub_heading_control.setVisible(visibile)
        self.selection_list_group.setVisible(visibile)
        self.list_control.setVisible(visibile)
        self.ok_button.setVisible(visibile)
        self.cancel_button.setVisible(visibile)
        self.defaults_button.setVisible(visibile)
        # self.full_window_group.setVisible(True)

    def get_control_button(self, iControlId: int) -> xbmcgui.ControlButton:
        """

        :param iControlId:
        :return:
        """
        buttonControl: xbmcgui.Control = super().getControl(iControlId)
        buttonControl: xbmcgui.ControlButton
        return buttonControl

    def update_data(self,
                    dialog_subject: DialogSubj,
                    title: str | None = None,
                    choices: Choices | EngineChoices | VGChoices | VoiceChoices
                                | None = None,
                    sub_title: str | None = None,
                    selection_idx: int | None = None,
                    call_on_focus:
                       Callable[[Choice | EngineChoice | VoiceChoice |
                                 VGChoice, int], None] | None = None,
                    call_on_select:
                       Callable[[Choice | EngineChoice | VoiceChoice |
                                 VGChoice, int], None] | None = None,
                    disable_tts: bool = False):

        """
        Provides a means for SelectionDialog to be a single, reusable instance

        :param title:  Heading for the dialog
        :param dialog_subject: Tags data (ex: 'VGChoice' or 'VoiceChoice')
        :param choices:  List of available choices to present
        :param selection_idx: If specified, overrides 
        :param sub_title:  Optional Sub-Heading for the dialog
        :param call_on_focus:  Optional call-back function for on-focus events
                              useful for hearing the difference immediately
        :param call_on_select: Optional call-back function for on-click events
                              useful for selecting Voices within a VoiceGroup
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

        if selection_idx is None:
            selection_idx, _ = self.get_selected_position()

        if dialog_subject is None:
            raise ValueError('dialog_subject cannot be None')
        if title is None:
            raise ValueError('title cannot be None')
        self.new_sel_data = SelectionData(dialog_subject=dialog_subject,
                                          title=title,
                                          sub_title=sub_title,
                                          selection_idx=selection_idx,
                                          choices=choices,
                                          call_on_focus=call_on_focus,
                                          call_on_select=call_on_select,
                                          disable_tts=disable_tts)

    def post_onInit(self, push_pop: ConfigStackEnum) -> None:
        """
        To be run after onInit runs (during doModal, etc.)
        """
        self.gui_updates_allowed = False
        self.initialized = False
        MY_LOGGER.debug(f'push_pop: {push_pop} stack_depth: '
                        f'{len(SelectionData.config_stack)}')
        if push_pop is ConfigStackEnum.PUSH:
            if self.new_sel_data is not None:
                SelectionData.push_config(self.new_sel_data)
        elif push_pop is ConfigStackEnum.POP:
            SelectionData.pop_config()
        else:
            pass
        self.sel_data: SelectionData = SelectionData.current_config
        self.new_sel_data: SelectionData | None = None
        MY_LOGGER.debug(f'# choices: {len(self.sel_data.choices)} selected_idx: '
                        f'{self.sel_data.selected_idx} selected_obj:'
                        f'{self.sel_data.selected_obj.label}')
        new_list_items: List[ListItem] = []
        for choice in self.sel_data.choices:
            choice: Choice | EngineChoice | VGChoice | VoiceChoice
            list_item: ListItem
            list_item = ListItem(label=f'{choice.label}', label2=f'hint{choice.hint}')
            new_list_items.append(list_item)

        self.list_control.reset()
        self.list_control.addItems(new_list_items)
        self.list_items = new_list_items
        MY_LOGGER.debug(f'selected_idx: {self.sel_data.selected_idx}')
        self.update_heading(title=self.sel_data.title, sub_title=self.sel_data.sub_title)
        self.list_control.selectItem(self.sel_data.selected_idx)
        self.disable_tts = self.sel_data.disable_tts
        Monitor.exception_on_abort(timeout=0.01)
        self.gui_updates_allowed = True
        self.set_visibility(True)
        self.setFocus(self.list_control)
        self.initialized = True

    def update_heading(self, title: str, sub_title: str = ''):
        """
        Called during onInit to update the heading values and make visible

        :param title:
        :param sub_title:
        :return:
        """
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'HEADING title: {self.sel_data.title}')
            MY_LOGGER.debug_v(f'sub_title: {sub_title}')
        self.heading_control.setLabel(self.sel_data.title)
        self.heading_control.setVisible(True)
        if self.sel_data.sub_title is not None:
            self.sub_heading_control.setLabel(self.sel_data.sub_title)
            self.sub_heading_control.setVisible(True)
        else:
            self.sub_heading_control.setVisible(False)
        self.heading_group_control.setVisible(True)
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
        except AbortException:
            reraise(*sys.exc_info())
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
        try:
            MY_LOGGER.debug('SelectionDialog.show about to call super')
            super().show()

            MY_LOGGER.debug('SelectionDialog.show exiting')
        except AbortException:
            self.abort = True
            reraise(*sys.exc_info())

    def close(self) -> None:
        """

        :return:
        """
        clz = type(self)
        if not self.abort:
            MY_LOGGER.debug('SelectionDialog.close')
        self.gui_updates_allowed = False
        self.set_visibility(False)
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
            xbmc.log('Received AbortRequested: SelectionDialog', xbmc.LOGINFO)
            self.abort = True
            self.closing = True
            self.close()
        except Exception:
            pass

    def onAction(self, action: xbmcgui.Action) -> None:
        """
         (From Super)

        **onAction method.**

        This method will receive all actions that the main program will send to this
        window.

        :param self: Own base class pointer
        :param action: The action id to perform, see `Action` to get use of them

        .. note::
            By default, only the ``PREVIOUS_MENU`` and ``NAV_BACK`` actions are
            handled. Overwrite this method to let your script handle all
            actions.Don't forget to capture ``ACTION_PREVIOUS_MENU``
            or ``ACTION_NAV_BACK``, else the user can't close this window.

        Example::

            ..
            # Define own function where becomes called from Kodi
            def onAction(self, action):
            if action.getId() == ACTION_PREVIOUS_MENU:
            print('action received: previous')
            self.close()
            if action.getId() == ACTION_SHOW_INFO:
            print('action received: show info')
            if action.getId() == ACTION_STOP:
            print('action received: stop')
            if action.getId() == ACTION_PAUSE:
            print('action received: pause')
            ..
        """
        MY_LOGGER.debug(f'ACTION: onAction')
        if MY_LOGGER.isEnabledFor(DEBUG):
            msg: str = Action.dump_action(action, log_all=True)
            MY_LOGGER.debug(f'Back from call dump_action msg: {msg}')

        if self.closing:
            return
        try:
            if not self.initialized:
                return

            Monitor.exception_on_abort(timeout=0.01)
            focus_id: int = self.getFocusId()
            action_id: int = action.getId()
            # if action_id in (xbmcgui.ACTION_MOUSE_MOVE,
            #                  xbmcgui.ACTION_MOUSE_DOUBLE_CLICK):
            #     return
            button_code: int = action.getButtonCode()
            MY_LOGGER.debug(f'SelectionDialog.onAction focus_id: {self.getFocusId()}'
                            f' action_id: {action_id} buttonCode: {button_code}')
            # action 105 mouse wheel down, 104 mouse wheel up
            if (action_id == xbmcgui.ACTION_PREVIOUS_MENU
                    or action_id == xbmcgui.ACTION_NAV_BACK):
                # No selection made
                self.sel_data.selected_idx = -1
                self.sel_data.selected_obj = None
                self.close()
            if action_id == xbmcgui.ACTION_SELECT_ITEM:
                if focus_id == self.LIST_CONTROL_ID:
                    if (not self.selection_list_group.isVisible()
                            or not self.initialized):
                        return
                    sel_idx, changed = self.get_selected_position()
                    sel_idx: int
                    changed: bool
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(
                                f'sel_idx: {sel_idx} changed: {changed} choices_len: '
                                f'{len(self.sel_data.choices)}')
                        MY_LOGGER.debug(f'subject: {self.sel_data.dialog_subject}')
                    if self.sel_data.dialog_subject == DialogSubj.V_OR_VG:
                        choices = self.sel_data.choices
                        choices: VGChoices | VoiceChoices
                        self.handle_select_v_or_vg(sel_idx, choices)
                    else:
                        engine_choices = self.sel_data.choices
                        engine_voices: EngineChoices
                        self.handle_select_common(sel_idx, engine_choices)

            if action_id in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_MOVE_UP,
                             xbmcgui.ACTION_MOUSE_WHEEL_DOWN,
                             xbmcgui.ACTION_MOUSE_WHEEL_UP,
                             xbmcgui.ACTION_MOUSE_MOVE):
                # Cursor up/down will almost certainly change the position
                # of the list container. Could add check to see if selected
                # position changed.
                focus_id: int = self.getFocusId()
                if focus_id == self.LIST_CONTROL_ID:
                    try:
                        if (not self.initialized or not
                                self.selection_list_group.isVisible()):
                            return
                        if self.sel_data.call_on_focus is not None:
                            sel_idx, changed = self.get_selected_position()
                            if changed:
                                choice: Choice | EngineChoice | VGChoice | VoiceChoice
                                choice = self.sel_data.choices[sel_idx]
                                # MY_LOGGER.debug(f'choice: {choice} sel_idx: {sel_idx}')
                                self.sel_data.call_on_focus(choice, sel_idx)
                    except AbortException:
                        self.abort = True
                        reraise(*sys.exc_info())
                        self.close()
                    except Exception as e:
                        MY_LOGGER.exception('')

        except AbortException:
            self.abort = True
            reraise(*sys.exc_info())
            self.close()
        except Exception as e:
            MY_LOGGER.exception('')

        # MY_LOGGER.debug('SelectionDialog.onAction selectedPosition: {:d}'
        #                 .format(self.list_control.getSelectedPosition()))
        # display_value = self.list_control.getSelectedItem()
        # if display_value is not None:
        #    MY_LOGGER.debug('SelectionDialog.onAction selectedItem: {}'.
        #                     format(display_value.getLabel()))

    def onControl(self, controlId):
        """
           (From Super)
           **onControl method.**

           This method will receive all click events on owned and selected controls when
           the control itself doesn't handle the message.

           :param controlId:

           Example::

               ..
               # Define own function where becomes called from Kodi
               def onControl(self, control):
               print("Window.onControl(control=[%s])"%control)
               ..
        """
        clz = type(self)
        MY_LOGGER.debug(f'ACTION: onControl')

    def onClick(self, controlId) -> None:
        """
            (From Super)
            **onClick method.**

            This method will receive all click events that the main program will send to
            this window.

            :param controlId: The clicked GUI control identifier

        """
        clz = type(self)
        if self.closing:
            return
        try:
            MY_LOGGER.debug(f'ACTION: onClick')
            if MY_LOGGER.isEnabledFor(DEBUG):
                focus_id = self.getFocusId()
                MY_LOGGER.debug('ON_CLICK FocusId: ' + str(focus_id))
            if controlId == clz.OK_BUTTON_ID:
                # OK button
                self.closing = True
                MY_LOGGER.info(f'ok button closing. selected_obj: '
                               f'{self.sel_data.selected_obj} '
                               f'selected_idx: {self.sel_data.selected_idx}')
                self.close()
            elif controlId == clz.CANCEL_BUTTON_ID:
                # Cancel button
                # MY_LOGGER.debug(f'cancel button')
                self.closing = True
                self.close()
        except AbortException:
            self.abort = True
            self.closing = True
            reraise(*sys.exc_info())
            self.close()

        except Exception as e:
            MY_LOGGER.exception('')

    def onDoubleClick(self, controlId):
        """
            (From Super)

            **onDoubleClick method.**

            This method will receive all double click events that the main program will send
            to this window.

            :param controlId: The double-clicked GUI control identifier

        """
        clz = type(self)
        if not (self.initialized or self.selection_list_group.isVisible()):
            MY_LOGGER.debug(f'not initialzed or visible')
            return
        MY_LOGGER.debug(f'ACTION: onDoubleClick control_id: {controlId}')

        if controlId == clz.OK_BUTTON_ID:
            self.closing = True
            # MY_LOGGER.info(f'ok button closing')
            self.close()
        elif controlId == clz.CANCEL_BUTTON_ID:
            # MY_LOGGER.debug(f'cancel button')
            self.closing = True
            self.close()
        elif (controlId == clz.LIST_CONTROL_ID and
              self.sel_data.dialog_subject == 'VGroups'):
            # Only for list of VGroups

            sel_idx, changed = self.get_selected_position()
            sel_idx: int
            changed: bool
            MY_LOGGER.debug(f'sel_id: {sel_idx} changed: {changed} choices_len: '
                            f'{len(self.sel_data.choices)}')
            vg_choice: VGChoice = self.sel_data.choices[sel_idx]
            if isinstance(vg_choice, VGChoice) and not vg_choice.e_vg.has_single_voice:
                self.handle_voice_group(vg_choice)
                # On return, select voice (or Voice Group's voice)
                # that was selected in dialog returned from
                self.sel_data.selected_idx = sel_idx
                MY_LOGGER.debug(
                        f'DOUBLE-CLICK call_on_select SELECT_ITEM choice: {vg_choice} sel_idx: {sel_idx}')
                self.sel_data.selected_obj = vg_choice

    def onFocus(self, controlId: int):
        """
        (From Super)

        **onFocus method.**

        This method will receive all focus events that the main program will send to
        this window.

        :param self: Own base class pointer
        :param controlId: The focused GUI control identifier

        Example::

            ..
            # Define own function where becomes called from Kodi
            def onDoubleClick(self,controlId):
            if controlId == 10:
            print("The control with Id 10 is focused")
            ..
        """
        clz = type(self)
        MY_LOGGER.debug(f'ACTION: onFocus controlId: {controlId}')
        try:
            if not self.initialized or not self.selection_list_group.isVisible():
                return
            if (controlId == clz.LIST_CONTROL_ID and
                    self.sel_data.dialog_subject == 'VGroups'):
                # ONLY for list of VGroups
                sel_idx, changed = self.get_selected_position()
                sel_idx: int
                changed: bool
                MY_LOGGER.debug(f'sel_idx: {sel_idx} changed: {changed}')
                if changed:
                    choice: EngineChoice = self.sel_data.choices[sel_idx]
                    MY_LOGGER.debug(f'choice: {choice}')
                    self.sel_data.call_on_focus(choice, sel_idx)
        except AbortException:
            self.abort = True
            reraise(*sys.exc_info())
            self.close()
        except Exception as e:
            MY_LOGGER.exception('')

    def handle_select_common(self, sel_idx: int,
                             engine_choices: EngineChoices) -> None:
        try:
            self.sel_data.selected_idx = sel_idx
            if sel_idx > -1:
                self.sel_data.selected_obj = engine_choices[sel_idx]
            else:
                self.sel_data.selected_obj = None
            self.close()
        except AbortException:
            self.abort = True
            reraise(*sys.exc_info())
            self.close()
        except Exception as e:
            MY_LOGGER.exception('')

    def handle_select_v_or_vg(self, sel_idx: int,
                              v_or_vg_choices: VGChoices | VoiceChoices) -> None:
        v_or_vg_choice: VGChoice | VoiceChoice | None = None
        v_or_vg_choice = v_or_vg_choices[sel_idx]
        vg_choice: VGChoice | None = None
        v_choice: VoiceChoice | None = None
        v_idx: int = 0
        try:
            if isinstance(v_or_vg_choice, VGChoice):
                vg_choice: VGChoice = v_or_vg_choice
                MY_LOGGER.debug(f'Selecting VGChoice: {vg_choice.label}'
                                f' single:'
                                f'{vg_choice.has_single_voice}')
                vg_choice.select_vg()
                if not vg_choice.has_single_voice:
                    self.handle_voice_group(vg_choice)
                    # The above saved the current choices and other
                    # data onto sel_data stack. It also created a
                    # new stack entry containing the voices from
                    # the selected Voice Group to be displayed so that
                    # user can choose. Return since there is no more
                    # action to take until user selects.
                    return
                # This is for when user selected a VoiceGroup with only
                # one voice. Just mark VoiceGroup as selected, which also
                # sets: vg_choice.previous_v_idx and
                # vg_choice.default_voice_choice
                vg_choice.select_voice(v_idx)
                # MY_LOGGER.debug(f'vg_choice: {vg_choice.label} vg_choice.choice_idx: '
                #                 f'{vg_choice.choice_idx} v_choices: '
                #                 f'{len(vg_choice.v_choices)} v_idx: {v_idx}')
                self.sel_data.selected_idx = vg_choice.choice_idx
                self.sel_data.selected_obj = vg_choice.v_choices[v_idx]
                self.list_control.selectItem(vg_choice.choice_idx)
                self.closing = True
                MY_LOGGER.debug(f'Exiting dialog due to single voice '
                                f'selection')
                self.close()
                return
            # The only way that the user selects VoiceChoices is
            # when they chose to pick a voice from a VoiceGroup that
            # has multiple Voices (that was initiated in the first
            # scenario, above, after 'if not vg_choice.has_single_voice',
            # which caused the voices to appear).
            # We got here when user selected one of those voices.
            # So we mark appropriate voice as chosen, pop the sel_data
            # stack, after modifying stack with the selection mae here.
            v_choice = v_or_vg_choice
            if not isinstance(v_choice, VoiceChoice):
                MY_LOGGER.debug(f'Expected v_choice to be of type'
                                f' VoiceChoice not {type(v_choice)}')
            vg_choice = v_choice.vg_choice
            if not isinstance(vg_choice, VGChoice):
                MY_LOGGER.debug(f'Expected {vg_choice} to be of type'
                                f' VGChoice not {type(vg_choice)}')
            # TODO: Move more of this sel_data.selection... into vg_choice,
            #       etc.
            v_idx = v_choice.choice_idx
            # VoiceGroup.select_voice also
            # sets: vg_choice._selected_v_idx,
            # vg_choice.default_voice_idx, default_voice_choice
            vg_choice.select_voice(v_idx)
            self.sel_data.selected_idx = vg_choice.choice_idx
            self.sel_data.selected_obj = vg_choice.v_choices[v_idx]
            self.list_control.selectItem(vg_choice.choice_idx)

            MY_LOGGER.debug(f'v_choice: {v_choice.label} '
                            f'vg_choice: {vg_choice} '
                            f'voice_idx: {v_choice.choice_idx}')

            # Copy items from current to previous_config since the
            # config stack is about to be popped.
            # Translate from ViewChoice to VGChoice objects

            prev_config: SelectionData
            prev_config = SelectionData.get_previous_config()
            prev_config.selected_idx = vg_choice.choice_idx
            prev_config.selected_obj = vg_choice

            MY_LOGGER.debug(f'prev_selected_idx: {prev_config.selected_idx} '
                            f'prev_selected_obj: {prev_config.selected_obj}')
            self.post_onInit(push_pop=ConfigStackEnum.POP)
            # sel_idx is index of chosen voice within it's voice group
            # self.sel_data.selected_idx = vg
            # self.sel_data.selected_idx =
            MY_LOGGER.debug(f'selected_idx: {self.sel_data.selected_idx} '
                            f'selected_obj: {self.sel_data.selected_obj}')
            MY_LOGGER.debug(
                    f'SELECT_ITEM-2 vg_choice: {vg_choice.label} '
                    f'vg selected_idx: {vg_choice.choice_idx} '
                    f'voice : '
                    f'{vg_choice.v_choices[v_idx].label} '
                    f'voice_idx: {v_idx} '
                    f'vg selected_idx: {self.sel_data.selected_idx} '
                    f'vg selected item: {self.get_selected_position()}')
            # Note: Returning the index for the VGChoice to this
            # VoiceChoice. The selected_idx
            MY_LOGGER.debug(f'popped config has selected_idx: '
                            f'{self.sel_data.selected_idx}\n'
                            f'sel_data.choices[sel_idx]: '
                            f'{self.sel_data.choices[v_idx].label} \n'
                            f'selected_ev_idx: '
                            f'{vg_choice.selected_v_idx}\n'
                            f'voice_idx: {v_idx}')
            self.list_control.selectItem(vg_choice.choice_idx)
            MY_LOGGER.debug(f'selected item: '
                            f'{self.get_selected_position()}')
            MY_LOGGER.debug(f'push-pop stack depth: '
                            f'{len(SelectionData.config_stack)}')
            self.post_onInit(push_pop=ConfigStackEnum.NONE)
        except AbortException:
            self.abort = True
            reraise(*sys.exc_info())
            self.close()
        except Exception as e:
            MY_LOGGER.exception('')

    def handle_voice_group(self, vg_choice: VGChoice) -> None:
        """
         When a group is selected (and not a voice within it),
         then:
             If settings has a voice from this engine and voice_group selected,
             then use that voice.
             Otherwise, select the default voice from the group.

         :param vg_choice: Voice group to display the voices to select
        """
        # default_e_voice = vg_choice.e_vg.default_e_voice  # Default Voice of group
        # The current engine is always set to the one we are interested in.
        # The current engine is always set to the one we are intexbrested in.
        current_e_voice: EngineVoice = EngineVoiceManager.get_e_voice()
        e_vg: IEngineVoiceGroup = EngineVoiceManager.get_vg(current_e_voice.e_vg_id,
                                                            current_e_voice.engine_key)
        current_vg_choice: VGChoice = ChoiceDict.vg_by_uid.get(e_vg.uid)
        choice_idx: int = -1
        if current_vg_choice.uid == vg_choice.uid:
            MY_LOGGER.debug(f'Selected VG is current VG: {current_vg_choice}')
            v_choice: VoiceChoice = ChoiceDict.voice_by_uid.get(current_e_voice.uid)
            vg_choice.default_v_idx = v_choice.choice_idx
            choice_idx = v_choice.choice_idx
            MY_LOGGER.debug(f'v_choice: {v_choice} v_idx: {vg_choice.choice_idx}')
        v_choice_idx: int = vg_choice.select_voice(choice_idx)

        vg_choice.select_vg()
        vg_choice.select_voice(v_choice_idx)

        MY_LOGGER.debug(f'v_choice_idx: {v_choice_idx} '
                        f'vg_choice.selected_v_idx: {vg_choice.selected_v_idx}')
        selected_voice: VoiceChoice
        previous_v_idx: int = vg_choice.selected_v_idx
        selected_voice = vg_choice.v_choices[previous_v_idx]
        e_voice = selected_voice.e_voice
        MY_LOGGER.debug(
                f'Choice is VGChoice: {vg_choice} voice: {e_voice}\n'
                f'selected_voice: {selected_voice} '
                f'previous_v_idx: {previous_v_idx}')
        # This will call SettingsDialog.select_voice_from_group whenever
        # a VoiceGroup is selected.
        # selected_idx and vg_choice.selected_v_idx both give the voice index
        #
        MY_LOGGER.debug(f'Switching ListItems, msgs to select voices of a group.')
        if not self.sel_data.call_on_select(vg_choice, previous_v_idx):
            MY_LOGGER.debug('Setup to select voices from a group FAILED')
            return

        # Make sure that the VoiceGroup is marked as selected

        # get_previous_config

        title: str
        title = MessageId.AVAILABLE_VOICES_FOR_GROUP.get_formatted_msg(
                vg_choice.label)
        sub_title: str = MessageId.CHOOSE_VOICE_FROM_GROUP.get_msg()
        v_choices: VoiceChoices = vg_choice.v_choices

        self.update_data(dialog_subject=DialogSubj.V_OR_VG,
                         title=title,
                         choices=v_choices,
                         selection_idx=previous_v_idx,
                         sub_title=sub_title,
                         call_on_focus=self.sel_data.call_on_focus,
                         call_on_select=self.voice_the_voice,
                         disable_tts=False)
        self.post_onInit(push_pop=ConfigStackEnum.PUSH)

        # MY_LOGGER.debug(
        #         f'idx returned by call_on_select: {selected_idx} '
        #         f'selected_v_idx: {vg_choice.selected_v_idx}')

    def addItem(self, item: str, position: int = 20000) -> None:
        """
        Add a new item to this WindowList.

        :param item: string, item to add.
        :param position: [opt] integer - position of item to add.
            (NO Int = Adds to bottom,0 adds to top, 1 adds to one below from top,
            -1 adds to one above from bottom etc )
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

    '''
    def process_selection(self, select_idx: int) -> None:
        """
        TODO: Does not appear to do anything. Delete
        Called when a user selects something from the subject/category list.

        :param select_idx: Item selected
        :return:
        """
        # Voice the text for this selection
        choice: int = self.list_control.getSelectedPosition()
        MY_LOGGER.debug(f'list_control position: {choice}')
        # if isinstance(self.sel_data.choices[choice], VGChoice):
        #     self.sel_data.saved_choices = self.sel_data.choices
        Monitor.exception_on_abort(timeout=0.01)
    '''

    def get_selected_position(self) -> Tuple[int, bool]:
        """
        Gets the current selected position and whether it has changed since the
        last call
        :return: Tuple[current_position, changed]
        """
        new_position: int = self.list_control.getSelectedPosition()
        changed: bool = False
        prev_position: int = self.sel_data.selected_idx
        if self.sel_data.selected_idx != new_position:
            changed = True
            self.sel_data.selected_idx = new_position
        MY_LOGGER.debug(f'changed: {changed} '
                        f'prev_idx: {prev_position} '
                        f'new_idx: {new_position}')
        return self.sel_data.selected_idx, changed

    def getCurrentListPosition(self) -> int:
        """
        Gets the current position in the list container.

        Example:
            pos = self.getCurrentListPosition()
        """

        clz = type(self)
        MY_LOGGER.debug(f'selected_idx: {self.sel_data.selected_idx}')
        return self.sel_data.selected_idx

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
        return len(self.sel_data.choices)

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
