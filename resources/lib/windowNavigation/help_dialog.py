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

from common.logger import *
from common.message_ids import MessageId
from common.monitor import Monitor
from welcome.subjects import (Category, CategoryRef, Load, MessageRef, Subject,
                              SubjectRef,
                              Utils)
from windowNavigation.choice import Choice

MY_LOGGER = BasicLogger.get_logger(__name__)

ParentStack = namedtuple('ParentStack', ['cat_ref', 'item_idx'])


class HelpDialog(xbmcgui.WindowXMLDialog):
    HEADING_CONTROL_ID: Final[int] = 1
    SUB_HEADING_CONTROL_ID: Final[int] = 4
    FULL_SCREEN_GROUP_ID: Final[int] = 1000
    HEADER_SUB_HEADER_GROUP_ID: Final[int] = 1001
    SELECTION_GROUP_ID: Final[int] = 1002
    SELECTION_LIST_GROUP_ID: Final[int] = 1003
    SPIN_CONTROL_ID: Final[int] = 200
    LIST_CONTROL_ID: Final[int] = 201

    HELP_CONTROL_ID: Final[int] = 100
    OK_GROUP_ID: Final[int] = 1005
    OK_CONTROL_ID: Final[int] = 101

    RETURN_TO_PREVIOUS_MENU: str = MessageRef.RETURN_TO_PREVIOUS_MENU.get_msg()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """

        :param args:
        """
        super().__init__(*args, **kwargs)
        self.abort: bool = False  # Set to True after abort received
        self.initialized: bool = False
        Load.load_help()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('HelpDialog.__init__')
        Monitor.register_abort_listener(self.hlp_dialg_abrt, name='hlp_dialg_abrt')
        empty_display_values: List[Choice] = []
        self.list_position: int = 0
        self.full_window_group: xbmcgui.ControlGroup | None = None
        self.selection_index: int = -1
        self.title: str = kwargs.get('title', MessageId.TTS_HELP_LABEL.get_msg())
        self.sub_title: str | None
        self.sub_title = kwargs.get('sub_title',
                                    MessageId.TTS_HELP_CHOOSE_SUBJECT.get_msg())
        self.help_text: str | None = None
        self.is_modal: bool = False
        self.notification_queue: queue.SimpleQueue = queue.SimpleQueue()

        # True when it is safe to update the gui.
        # You can not update when not in doModal or show until OnInit is complete.
        # OnInit is run each time doModal is run. Show doesn't or does not
        # reliably run OnInit. Odd.

        self.gui_updates_allowed: bool = False

        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'sub_title: {self.sub_title}')
        self._choices: List[Choice]
        self._choices = kwargs.get('choices', empty_display_values)
        self._initial_choice: int = kwargs.get('initial_choice', -1)
        if self._initial_choice < 0:
            self._initial_choice = 0

        # self._previous_num_items: int = HelpDialog.NUMBER_OF_BUTTONS + 1
        self._call_on_focus: Callable[Choice, None] | None
        self._call_on_focus = kwargs.get('call_on_focus', None)
        self._call_on_select: Callable[Choice, None] | None
        self._call_on_select = kwargs.get('call_on_select', None)
        self._callback:  Callable[[Any], None] | None = kwargs.get('callback', None)
        self.heading_control: ControlLabel | None = None
        self.sub_heading_control: ControlLabel | None = None
        self.heading_group_control: ControlGroup | None = None
        # self.help_button: ControlButton | None = None
        self.help_label: ControlLabel | None = None
        self.choices_group: ControlGroup | None = None
        self.spin_control: xbmcgui.ControlSpin | None = None
        self.selection_group: ControlGroup | None = None
        self.seletion_list_group: ControlGroup | None = None
        self.ok_group: ControlGroup | None = None
        self.list_control: ControlList | None = None
        self.list_items: List[ListItem] = []
        self.button_controls: List[ControlButton] = []
        self.number_of_button_controls: int = 0
        self.ok_radio_button: ControlRadioButton | None = None
        self.items_label: ControlLabel | None = None
        self.close_selected_idx: int = -1

        self.current_category: Category = Category.get_category(CategoryRef.WELCOME_TTS)
        # When we descend into Category/Subject tree, remember where to return
        self.parent_stack: List[ParentStack]
        # Top of stack is only needed for the CategoryRef.
        entry: ParentStack = ParentStack(cat_ref=CategoryRef.WELCOME_TTS, item_idx=-1)
        self.parent_stack = [entry]
        MY_LOGGER.debug(f'top category: {self.current_category}')

    def onInit(self):
        """

        :return:
        """
        # super().onInit()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('HelpDialog.onInit enter')
        self.initialized = False
        try:
            Monitor.exception_on_abort(timeout=0.01)
            self.configure_heading()
            # self.help_button = self.getControlButton(HelpDialog.HELP_CONTROL_ID)
            self.help_label = self.getControlLabel(HelpDialog.HELP_CONTROL_ID)

            self.configure_ok()
            self.configure_selection_list()
            self.update_choices(title=self.title,
                                choices=None,
                                sub_title=self.sub_title,
                                initial_choice=-1,
                                call_on_focus=self._call_on_focus)
        except AbortException:
            self.abort = True
            self.close()
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception("Failed to initialize")
            self.close()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('HelpDialog.onInit exiting')

    def configure_heading(self) -> None:
        """
        Called by OnInit to cfg the Window heading

        :return:
        """
        clz = HelpDialog
        self.full_window_group = self.getControlGroup(HelpDialog.FULL_SCREEN_GROUP_ID)
        #  DON'T completely blank screen. Impacts voicing and flickers screen.
        # self.full_window_group.setVisible(False)

        self.heading_group_control = self.getControlGroup(
                clz.HEADER_SUB_HEADER_GROUP_ID)
        self.heading_control = self.getControlLabel(clz.HEADING_CONTROL_ID)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Got heading ctrl: 1')
        self.sub_heading_control = (self.getControlLabel
                                    (HelpDialog.SUB_HEADING_CONTROL_ID))
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Got heading ctrl: 4')
        Monitor.exception_on_abort(timeout=0.01)

    def configure_ok(self) -> None:
        """
        Called by OnInit to cfg the OK button

        :return:
        """
        clz = HelpDialog
        self.ok_group = self.getControlGroup(self.OK_CONTROL_ID)
        self.ok_group.setVisible(False)
        self.ok_radio_button = self.getControlRadioButton(clz.OK_CONTROL_ID)
        self.ok_radio_button.setLabel(MessageId.OK_BUTTON.get_msg())
        self.ok_radio_button.setVisible(True)
        self.ok_group.setVisible(True)

    def configure_selection_list(self) -> None:
        """
        Called by onInit to cfg the list control for selecting subjects
        to view.

        :return:
        """
        clz = HelpDialog
        self.selection_group = self.getControlGroup(clz.SELECTION_GROUP_ID)
        self.seletion_list_group = self.getControlGroup(
                clz.SELECTION_LIST_GROUP_ID)
        #  Can't Lose focus on this control
        #  self.selection_group.setVisible(False)
        self.list_control = self.getControlList(clz.LIST_CONTROL_ID)

    def update_choices(self, title: str,
                       choices: List[Choice] = None, initial_choice: int = -1,
                       sub_title: str | None = None,
                       call_on_focus: Callable[Choice, None] | None = None,
                       call_on_select: Callable[Choice, None] | None = None):
        """
        Called by onInit to supply data to be displayed as well as some
        optional callbacks to an external caller.

        :param title:  Heading for the dialog
        :param choices:  List of available choices to present
        :param initial_choice:  Index of the current choice in choices
        :param sub_title:  Optional Sub-Heading for the dialog
        :param call_on_focus:  Optional call-back function for on-focus events
                              useful for hearing the difference immediately
        :param call_on_select: Optional call-back function for on-click events
                              useful for voicing the selected item immediately
        :return: Returns the underlying HelpDialog so that methods can be
                called such as doModal

        """
        # Used to convey the selection when DONE. Set to -1 on CANCEL
        self.close_selected_idx = -1
        if choices is None:
            choices = []

        # Choices can have zero length
        self._choices = choices
        self._initial_choice = initial_choice
        if self._initial_choice < 0:
            self._initial_choice = 0
        self._call_on_focus = call_on_focus
        self.update_heading(title=title, sub_title=sub_title)
        idx: int = 1
        if len(self.parent_stack) == 1:
            idx = 0
        self.update_selection_list(self.current_category, idx)

        self.help_label.setLabel('')
        self.help_label.setVisible(False)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'help_label NOT visible {self.help_text}')
        self.full_window_group.setVisible(True)
        self.initialized = True
        self.gui_updates_allowed = True
        Monitor.exception_on_abort(timeout=0.01)

        #
        #  TODO: Change to be like custom_settings-ui so that new window
        #        is not created on every launch.
        #
        utils.util.runInThread(func=self.notification_queue_handler,
                               name='helpNot')

    def update_heading(self, title: str, sub_title: str = ''):
        """
        Called during onInit to update the heading values and make visible

        :param title:
        :param sub_title:
        :return:
        """
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

    def update_selection_list(self, parent_category: Category,
                              selected_idx: int = 0):
        """
            Updates the ListItems after changing the category.
            Choices changeed: at startup,
                              When a new category is selected
                              When returning from an old category
        :return:

        """
        clz = HelpDialog
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'parent_category: {parent_category.category_id} '
                            f'name: {parent_category.get_name()}')
        Monitor.exception_on_abort(timeout=0.01)

        new_list_items = []
        cat_name: str
        cat_text: str
        subject_refs: List[SubjectRef | CategoryRef]
        cat_name, cat_text, subject_refs = parent_category.get_choices()
        # If list is not at the top level, then add a list-item for
        # returning to the previous category (like parent directory)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'parent_category: {parent_category.category_id} '
                            f'stack_depth: {len(self.parent_stack)}')
        if len(self.parent_stack) != 1:
            list_item: ListItem
            list_item = ListItem(label=f'...  {clz.RETURN_TO_PREVIOUS_MENU}')
            # Add the marker for returning up a level
            # Fill out which item to return to later
            # most_recent_cat: CategoryRef =
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'pushing {parent_category.category_id} '
                                f'value: PopStack')
            list_item.setProperty(parent_category.category_id, 'PopStack')
            new_list_items.append(list_item)
        for sub_cat_ref in subject_refs:
            Monitor.exception_on_abort(timeout=0.01)
            sub_cat_ref: SubjectRef | CategoryRef
            subject_ref: SubjectRef | None = None
            cat_ref: CategoryRef | None = None
            summary: str = ''
            name: str = ''
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'sub_cat_ref: {sub_cat_ref} type: {type(sub_cat_ref)}')
            if isinstance(sub_cat_ref, SubjectRef):
                subject_ref = sub_cat_ref
                subject_ref: SubjectRef
                subject: Subject = Subject.get_subject(subject_ref)
                name: str = subject.get_name()
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'subjectRef: {name}')
            else:
                cat_ref: CategoryRef = sub_cat_ref
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'sub_cat_ref: {cat_ref}')
                category: Category = Category.get_category(cat_ref)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'category: {category.category_id}')
                name: str = category.get_name()
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'cat_ref: {cat_ref}')

            #  subj_text: str = subject.get_text()
            list_item: ListItem
            list_item = ListItem(label=name)
            # if summary != '':
            #    # MY_LOGGER.debug(f'Setting label2 to: {summary}')
            #    # list_item.setLabel2(summary)
            list_item.setProperty('key', sub_cat_ref)
            list_item.setProperty('type', sub_cat_ref.__class__.__name__)
            new_list_items.append(list_item)

        # About to change help text
        self.help_label.setVisible(False)
        self.help_text = ''  # Ensure that old contents can't be read
        self.help_label.setLabel(self.help_text)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'help_label NOT visible {self.help_text}')
        self.list_control.reset()
        self.list_control.addItems(new_list_items)
        self.list_items = new_list_items
        self.list_control.selectItem(selected_idx)
        self.list_control.setVisible(True)
        self.seletion_list_group.setVisible(True)
        self.setFocus(self.list_control)
        self.selection_group.setVisible(True)

    def process_selection(self, select_idx: int) -> None:
        """
        Called when a user selects something from the subject/category list.

        :param select_idx: Item selected
        :return:
        """
        # Voice the text for this selection
        choice: int = self.list_control.getSelectedPosition()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'list_control position: {choice}')
        choice_value: str = ''
        choice_type: str = ''
        """
         The 'help' menus are arranged hiearchecally. Catalog nodes have child nodes
         while Subject nodes are leaf nodes. Selecting a Subject node causes
         the help to displayed in a Label. Selecting a Catalog node cause the 
         menu to be replaced by the members of the Catalog node. NOTE that the
         Catalog node does NOT appear in its children's menu, rather the 
         first menu item (after 'return to parent') is the proxy node that
         contains some brief description about that category.
         
         self.parent_stack tracks how to return to the previous menu.
         All but the top menu starts with the entry ... '(Return to Parent)'.
         You can't return from the top level.
         
         TWO parent_stack entries must be used to return from a sub-menu.
         The index to the previously focused item is at parent_stack[-1],
         but the Category_id is at parent_stack[-2].
        
         parent_stack[0].cat_ref contains CategoryRef.TTS.value (top of menu structure)
         parent_stack[1].item_idx contains the item index that was selected to
         get to this menu.
         
        """
        Monitor.exception_on_abort(timeout=0.01)

        if choice == 0 and len(self.parent_stack) > 1:
            choice_type = 'PopStack'  # Special
        else:
            choice_value = self.list_items[choice].getProperty(f'key')
            choice_type = self.list_items[choice].getProperty(f'type')
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'pushing cat: {self.current_category.category_id}')
            MY_LOGGER.debug(f'choice: {choice} '
                            f'{self.list_items[choice].getLabel()} '
                            f'key: {choice_value} type: {choice_type}')
        failed: bool = False
        category_ref: CategoryRef | None = None
        subject: SubjectRef | None = None
        if choice_type == 'CategoryRef':
            # Selecting this causes the menu for the new category to be displayed
            try:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'cat_ref: {choice_value}')
                category_ref = CategoryRef(choice_value)
            except ValueError:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'failed process CategoryRef')
                failed = True
        elif choice_type == 'SubjectRef':
            # Selecting this results in displaying the help-text in the
            # help-text label
            try:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'SubjectRef: {choice_value}')
                subject = SubjectRef(choice_value)
            except ValueError:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'failed to process SubjectRef')
                failed = True
        elif choice_type == 'PopStack':
            # Results in returning to parent menu and setting focus to
            # same entry as before
            #
            # Get the reference to the previous menu. This reference is from
            # the Category of the grand-parent's node.
            choice_value: str = self.parent_stack[-2].cat_ref
            parent_item_index: int = self.parent_stack[-1].item_idx
            parent_ref: CategoryRef = CategoryRef(choice_value)
            self.parent_stack.pop()  # pops copy of current position
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'PopStack cat: {parent_ref} '
                                f'parent: {parent_ref} idx: {parent_item_index}')
                MY_LOGGER.debug(f'popped cat: {self.current_category.category_id}')
                MY_LOGGER.debug(f'Updating selection_list category: {parent_ref}')
            self.current_category = Category.get_category(parent_ref)
            self.update_selection_list(self.current_category, parent_item_index)
            category_ref = None   # Don't want any changes due to this.
        if category_ref is not None:
            # Category selected, drill down and display its choices.
            # parent_cat: ParentStack = self.parent_stack[-1]
            category: Category = Category.get_category(category_ref)
            # Set the category to show the subjects of from the stack that was
            # populated with this category's info just before calling here

            self.current_category = category
            self.parent_stack.append(ParentStack(cat_ref=category_ref,
                                                 item_idx=choice))
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'pushing cat: {category_ref}')
            self.update_selection_list(self.current_category, select_idx)
        elif subject is not None:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'ShowManual subject: {subject}')
            self.notify(cmd='ShowManual', text='',
                        subject=subject)

    def setProperty(self, key, value):
        """
        Sets Window properties so that the screen scraper can detect and
        use the values.

        :param key:
        :param value:
        :return:
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug_v(f'SelectionDialog.setProperty key: {key} '
                              f'value: {value}')
        super().setProperty(key, value)

    def notify(self, cmd: str, text: str = None,
               subject: SubjectRef | CategoryRef = None):
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Notify cmd: {cmd} text {text}')
        item: Tuple[str, str, SubjectRef | CategoryRef] = (cmd, text, subject)
        Monitor.exception_on_abort(timeout=0.01)
        self.notification_queue.put(item)

    def notification_queue_handler(self) -> None:
        """
        Processes external and internal requests

        :return:
        """
        clz = HelpDialog
        try:
            from windowNavigation.help_manager import HelpManager

            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Notification queue handler started')
            while not Monitor.exception_on_abort(timeout=0.10):
                if self.gui_updates_allowed:
                    try:
                        cmd, text, subject_ref = self.notification_queue.get(block=False)
                        if cmd == 'ShowManual':
                            # Display the details for the given subject
                            subject_ref: SubjectRef
                            subject: Subject = Subject.get_subject(subject_ref)
                            self.help_text = subject.get_text()
                            # self.help_button.setLabel(subject.get_text())
                            self.help_label.setLabel(self.help_text)
                            self.help_label.setVisible(True)
                            if MY_LOGGER.isEnabledFor(DEBUG):
                                MY_LOGGER.debug(f'help_label visible {self.help_text}')
                        elif cmd == HelpManager.HELP:
                            self.help_text = text
                            # self.help_button.setLabel(text)
                            # self.help_label.setLabel(self.help_text)
                            #  self.help_label.setVisible(True)
                            # MY_LOGGER.debug(f'help_label visible {self.help_text}')
                        # self.help_button.setVisible(True)
                    except queue.Empty:
                        pass
        except AbortException:
            self.abort = True
            self.close()
            reraise(*sys.exc_info())

            # End thread
            return

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
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('HelpDialog.doModal about to call super')
            self.is_modal = True
            super().doModal()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'No longer Modal')
            self.is_modal = False
        except Exception as e:
            MY_LOGGER.exception('HelpDialog.doModal')
        return

    def show(self) -> None:
        """

        :return:
        """
        clz = type(self)
        if self.abort:
            return
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('HelpDialog.show about to call super')
        super().show()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('HelpDialog.show returned from super.')

        if self.initialized:
            self.ok_radio_button.setVisible(True)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('HelpDialog.show exiting')

    def close(self) -> None:
        """

        :return:
        """
        clz = type(self)
        if not self.abort and MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('HelpDialog.close')
        self.gui_updates_allowed = True
        self.is_modal = False
        super().close()

    def getFocus(self) -> None:
        """

        :return:
        """
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('HelpDialog.getFocus')
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

            Monitor.exception_on_abort(timeout=0.01)

            action_id = action.getId()
            if action_id == 107:  # Mouse Move
                return

            buttonCode: int = action.getButtonCode()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'HelpDialog.onAction focus_id: {self.getFocusId()}'
                                f' action_id: {action_id} buttonCode: {buttonCode}')
            if (action_id == xbmcgui.ACTION_PREVIOUS_MENU
                    or action_id == xbmcgui.ACTION_NAV_BACK):
                self.close()
            if action_id == xbmcgui.ACTION_SELECT_ITEM:
                focus_id: int = self.getFocusId()
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'onAction select item focus: {focus_id}')
                # self.setFocus(self.help_button)

            if action_id in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_MOVE_UP):
                # Cursor up/down will almost certainly change the position
                # of the list container. Could add check to see if selected
                # position changed.
                self.help_label.setLabel('')
                self.help_label.setVisible(False)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'help_label NOT visible {self.help_text}')

        except AbortException:
            self.abort = True
            self.close()
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

        # MY_LOGGER.debug('HelpDialog.onAction selectedPosition: {:d}'
        #                 .format(self.list_control.getSelectedPosition()))
        # display_value = self.list_control.getSelectedItem()
        # if display_value is not None:
        #    MY_LOGGER.debug('HelpDialog.onAction selectedItem: {}'.
        #                     format(display_value.getLabel()))

    def onControl(self, controlId):
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'HelpDialog.onControl controlId: {controlId:d}')

    def onClick(self, controlId):
        """
        Called when a 'clickable' control is 'clicked' by a mouse. Typically
        a button or anything selectable.

        :param controlId:
        :return:
        """
        clz = type(self)
        try:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('HelpDialog.onClick controlId: {:d}'.format(controlId))
            focus_id = self.getFocusId()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('HelpDialog.onClick FocusId: ' + str(focus_id))
            # if controlId == self.list_control.getId():
            #    MY_LOGGER.debug('HelpDialog List control 3 pressed')
            # x = xbmc.executebuiltin('Skin.String(category)',True)
            if controlId == clz.OK_CONTROL_ID:
                self.close_selected_idx = self.selection_index
                # OK radio_button
                self.close()

            elif controlId == clz.LIST_CONTROL_ID:
                self.process_selection(self.selection_index)
        except AbortException:
            self.abort = True
            self.close()
            reraise(*sys.exc_info())

        except Exception as e:
            MY_LOGGER.exception('')

    def onDoubleClick(self, controlId):
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'HelpDialog.onDoubleClick controlId: {controlId:d}')

    def onFocus(self, controlId: int):
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'onFocus controlId: {controlId}')
        try:
            if not self.initialized or not self.selection_group.isVisible():
                return
            # Stop any reading of help text
            self.help_label.setLabel('')
            self.help_label.setVisible(False)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'help_label NOT visible {self.help_text}')

            if self._call_on_focus is not None:
                pass
                #  self._call_on_focus(choice, idx)
        except AbortException:
            self.abort = True
            self.close()
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

    def hlp_dialg_abrt(self):  # Short name that shows up in debug log
        try:
            self.abort = True
            if MY_LOGGER.isEnabledFor(DEBUG):
                xbmc.log('HelpDialog Received AbortRequested', xbmc.LOGINFO)
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
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'HelpDialog.addItem unexpected call item: {item}')
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
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'HelpDialog.addItems unexpected call item length: '
                            f'{len(items)}')
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
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'HelpDialog.removeItem unexpected call item: {position:d}')
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
        Gets the current position in the list container.

        Example:
            pos = self.getCurrentListPosition()
        """

        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'HelpDialog.getCurrentListPosition selected position: '
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
                f'HelpDialog.setCurrentListPosition unexpected call: {position}')
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
        return len(self._choices)

    def clearList(self) -> None:
        """
        Clear the WindowList.

        Example::

            self.clearList()
        """
        # self.list_control.reset()
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('HelpDialog.clearList')
        self.debug_display_values('clearList')

    def debug_display_values(self, text: str) -> None:
        pass
        # MY_LOGGER.debug('{} len display_values: {:d}'
        #                 .format(text, self.list_control.size()))
