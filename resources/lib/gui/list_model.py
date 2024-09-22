# coding=utf-8

from typing import Callable, List

import xbmc
import xbmcgui

from common.logger import BasicLogger, DEBUG_XV
from common.messages import Messages
from common.phrases import Phrase
from gui.base_model import BaseModel
from gui.base_parser import BaseParser
from gui.base_tags import (control_elements, ControlElement, Item)
from gui.element_parser import (ElementHandler)
from gui.focused_layout_model import FocusedLayoutModel
from gui.item_layout_model import ItemLayoutModel
from gui.list_topic_model import ListTopicModel
from gui.no_topic_models import NoListTopicModel
from gui.parser.parse_list import ParseList
from gui.statements import Statements
from utils import util
from windows.ui_constants import UIConstants
from windows.window_state_monitor import WinDialogState

module_logger = BasicLogger.get_logger(__name__)


class ListModel(BaseModel):

    _logger: BasicLogger = module_logger
    item: Item = control_elements[ControlElement.LIST]

    def __init__(self, parent: BaseModel, parsed_list: ParseList) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
        super().__init__(window_model=parent.window_model, parser=parsed_list)
        self.parent: BaseModel = parent
        self.visible_expr: str = ''
        self.description: str = ''
        # self.on_click
        self.on_focus_expr: str = ''
        self.on_unfocus_expr: str = ''
        self.page_control: int = -1
        self.enable_expr: str = ''
        self.orientation_expr: str = 'vertical'
        self.viewtype: str = ''  # Probably of no interest
        self.item_layouts: List[ItemLayoutModel] = []
        self.focused_layouts: List[FocusedLayoutModel] = []
        self.convert(parsed_list)

    def convert(self, parsed_list: ParseList) -> None:
        """
            Convert Parsed Controls, etc. to a model.

        :param parsed_list: A ParseList instance that
               needs to be converted to a ListModel
        :return:
        """
        clz = type(self)
        self.visible_expr = parsed_list.visible_expr
        self.description = parsed_list.description
        self.on_focus_expr = parsed_list.on_focus_expr
        self.on_unfocus_expr = parsed_list.on_unfocus_expr
        self.enable_expr = parsed_list.enable_expr
        self.orientation_expr = parsed_list.orientation_expr
        self.page_control: int = parsed_list.page_control
        self.viewtype: str = parsed_list.viewtype

        if parsed_list.topic is not None:
            self.topic = ListTopicModel(self, parsed_list.topic)
        else:
            self.topic = NoListTopicModel(self)

        for item_layout in parsed_list.item_layouts:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(item_layout.item)
            child_model: ItemLayoutModel = model_handler(self, item_layout)
            clz._logger.debug(f'item model handler: {model_handler} class: ')
            clz._logger.debug(f'Appending item_layout {item_layout} '
                               f'now child_model: {child_model}')
            self.item_layouts.append(child_model)

        for item_layout in parsed_list.focused_layouts:
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(item_layout.item)
            child_model: FocusedLayoutModel = model_handler(self, item_layout)
            clz._logger.debug(f'Appending focused_layout {item_layout} '
                              f'now child_model: {child_model}')
            self.focused_layouts.append(child_model)

        clz._logger.debug(f'# parsed children: {len(parsed_list.get_children())}')

        for child in parsed_list.children:
            child: BaseParser
            model_handler: Callable[[BaseModel, BaseModel, BaseParser], BaseModel]
            model_handler = ElementHandler.get_model_handler(child.item)
            child_model: BaseModel = model_handler(self, child)
            self.children.append(child_model)

    @property
    def supports_label(self) -> bool:
        # ControlCapabilities.LABEL
        return True

    @property
    def supports_heading_label(self) -> bool:
        """
        Indicates whether this control provides a label which explains what it
        is for. For example, a button's label almost certainly is to explain
        why you should press it. On the other hand a label control does not.
        A label control may be displaying a date or the result of an action.
        More information is needed for controls like labels in order to know
        what to do with them.

        :return:
        """
        return False

    @property
    def supports_container(self) -> bool:
        """
           Only a few controls are containers and even then, some don't fully
           support containers.

           Known Containers
               FixedList?, List, Panel, WrapList
           Known semi-containers
               GroupList
           :return:
        """
        return True

    @property
    def supports_item_count(self) -> bool:
        """
           Indicates if the container supports item_count. List type containers/
           controls, such as GroupList and List control/container do

           :return:
        """
        return True

    @property
    def supports_change_without_focus_change(self) -> bool:
        """
            Indicates if the control supports changes that can occur without
            a change in Focus. Slider is an example. User modifies value without
            leaving the container. Further, you only want to voice the value,
            not the control name, etc.
        :return:
        """
        return True

    def get_orientation(self) -> str:
        clz = ListModel
        msg_id: int = 32809
        if self.orientation_expr == UIConstants.VERTICAL:
            msg_id = 32808
        orientation: str = Messages.get_msg_by_id(msg_id=msg_id)
        if clz._logger.isEnabledFor(DEBUG_XV):
            clz._logger.debug_xv(f'Orientation: {orientation}')
        return orientation

    def voice_active_item(self, stmts: Statements) -> bool:
        """
        Only used when chain of Topics are not available from Window to
         focused/active control.

        :param stmts:
        :return:
        """
        clz = ListModel
        # Ignore voicing some non-focused text at the moment
        # focused_control_id: int = self.window_model.win_or_dialog.
        if not self.focus_changed:
            return False

        container_id = self.control_id
        if container_id > 0:
            #  position is zero-based
            # pos_str: str = xbmc.getInfoLabel(f'Container({container_id}).Position')
            # pos: int = util.get_non_negative_int(pos_str)
            # pos += 1  # Convert to one-based item #
            # clz._logger.debug(f'container position: {pos} container_id: {container_id}')
            current_item: str = xbmc.getInfoLabel(f'Container({container_id}).CurrentItem')
            clz._logger.debug(f'current_item: {current_item}')
            stmts.last.phrases.append(Phrase(text=f'Item: {current_item}'))
            win: xbmcgui.Window = self.windialog_state.window_instance
            focused_control: int = win.getFocusId()
            clz._logger.debug(f'Focused control: {focused_control}')
            return True

        # TODO START HERE!!
        return False

    def get_item_number(self, control_id: int | None = None) -> int:
        """
        Used to get the current item number from a List type topic. Called from
        a child topic of the list

        :param control_id: optional id of the control to query. Defaults to
                           the currently focused control
        :return: Current topic number, or -1
        """
        clz = ListModel
        #  TODO: Open defect against kodi. There is no means to get the absolute
        #        position (row) of a list control via info label. Instead you
        #        get the item number of the VISIBLE items in whatever space is
        #        the list allows. Useless for my purpose.
        container_id = self.control_id
        pos_str: str = xbmc.getInfoLabel(f'Container({container_id}).Position')
        # num_all_items: str = xbmc.getInfoLabel(f'Container({container_id}).NumAllItems')
        # num_items: str = xbmc.getInfoLabel(f'Container({container_id}).NumItems')
        # num_pages: str = xbmc.getInfoLabel(f'Container({container_id}).NumPages')

        pos: int = util.get_non_negative_int(pos_str)
        pos += 1  # Convert to one-based item #
        clz._logger.debug(f'container position: {pos} container_id: {container_id}')
        #  clz._logger.debug(f'num_all_items: {num_all_items} num_items: {num_items} '
        #                    f'')
        return pos

    def get_working_value(self, item_number: int = 0) -> float | List[str]:
        """
            Gets the intermediate value of this control. Used for controls where
            the value is entered over time, such as a list container where
            you can scroll through your choices (via cursor up/down, etc.)
            without changing focus.

            The control's focus does not change so the value must be checked
            as long as the focus remains on the control. Further, the user wants
            to hear changes as they are being made and does not want to hear
            extra verbage, such as headings.

        :param item_number: Used to check for change
        :return: List of values from the current item_number and from the
                 first item_layout and focused_layout with a passing condition.
        """
        clz = ListModel
        #  clz._logger.debug(f'{windialog_state}')

        #   if self.focus_changed:
            # clz._logger.debug(f'value was: {self.value} changed: {self.value_changed}'
            #                   f' control_id: {self.control_id}')
            # clz._logger.debug(f'value_id: {hex(id(self.value))} '
            #                   f'changed: {hex(id(self.value_changed))}')
        # clz._logger.debug(f'value was: {self.value} changed: {self.value_changed} ')
        # clz._logger.debug(f'value_id: {hex(id(self.value))} '
        #                   f'changed: {hex(id(self.value_changed))}')
        """
          A List container is basically a single column or row of labels and/or
          images that can be scrolled through using the cursor up/down keys.
          You can see only one row/column at a time. You select an item by 
          clicking or pressing enter (TODO: VERIFY THIS). As long as you don't 
          change the focus to another control you can continue to scroll
          and select. The semantics of selecting or selecting more than one
          item is up to the dialog. Here, we just care about voicing what
          appears on the screen and what is selected/deselected.
          
          There are two layouts: one for focused items and another for the
          other items. We only voice what is focused (at least for now).
          Further, there can be more than one of each of these layouts, 
          each with a condition that will select only one (one focused and
          one regular) layout to be in effect at any moment.
          
          The basic idea here is to track the changes in the active
          focused layout and revoice them as they change.
          
          In addition... selecting an item may cause some other control to
          change. By using 'flows_to' any change in value at the other control
          will also be voiced. One trick is to NOT voice its initial value, only
          values that change while this control is focused.
          
          This will be a bit of an adventure.
        """

        # First, find the 'active' "item_layout" and "focused_Layout"
        # using the associated condition. The first found that passes
        # the condition wins.

        clz._logger.debug(f'In get_working_value')
        # active_item_layout: ItemLayoutModel | None = None
        active_focused_layout: FocusedLayoutModel | None = None
        # winner: int = -1
        '''
            Don't voice unfocused items. This may change in future
            
        clz._logger.debug(f'# item_layouts: {len(self.item_layouts)}')
        for layout_item in self.item_layouts:
            winner += 1
            layout_item: ItemLayoutModel
            query: str = layout_item.condition_expr
            clz._logger.debug(f'layout_item: {layout_item} \n query: {query}')
            if query == '':   # Passes
                break
            if xbmc.getCondVisibility(query):
                clz._logger.debug('query passed')
                break

        if -1 < winner < len(self.item_layouts):
            active_item_layout = self.item_layouts[winner]
        else:
            clz._logger.debug(f'All item layouts FAILED the condition')
        '''
        winner: int = -1
        clz._logger.debug(f'# focusedlayouts: {len(self.focused_layouts)}')
        failed: bool = True
        for layout_item in self.focused_layouts:
            winner += 1
            layout_item: ItemLayoutModel
            query: str = layout_item.condition_expr
            if query == '':
                failed = False
                break  # Passes
            if xbmc.getCondVisibility(query):
                failed = False
                break

        if -1 < winner < len(self.item_layouts):
            active_focused_layout = self.focused_layouts[winner]
        else:
            clz._logger.debug('All focused layouts FAILED the condition')

        #  info_labels: List[str] = active_item_layout.get_info_labels()
        focused_info_labels: List[str] = active_focused_layout.get_info_labels()
        # clz._logger.debug(f'# info_labels: {len(info_labels)} '
        #                  f'# focused_info_labels: {len(focused_info_labels)}')

        values: List[str] = []
        '''
        for info_label in info_labels:
            clz._logger.debug(f'info_label: {info_label}')
            query: str
            query = (f'Container({self.control_id}).ListItemAbsolute({position}).'
                     f'[{info_label}]')
            value: str = self.get_info_label(query)
            clz._logger.debug(f'query: {query}  value: {value}')
            values.append(value)
        '''
        for info_label in focused_info_labels:
            value: str | None = self.get_info_label(info_label)
            clz._logger.debug(f'info_label: {info_label} value: {value}')
            if value is not None:
                values.append(value)
        return values

    def __repr__(self) -> str:
        return self.to_string(include_children=False)

    def to_string(self, include_children: bool = False) -> str:
        """
        Convert self to a string.

        :param include_children:
        :return:
        """
        clz = type(self)
        description_str: str = ''

        if self.description != '':
            description_str = f'\n  description: {self.description}'

        visible_expr: str = ''
        if self.visible_expr is not None and len(self.visible_expr) > 0:
            visible_expr = f'\n  visible_expr: {self.visible_expr}'

        enable_str: str = ''
        if self.enable_expr != '':
            enable_str = f'\n  enable_expr: {self.enable_expr}'

        if self.on_focus_expr is not None and (len(self.on_focus_expr) > 0):
            on_focus_expr: str = f'\n  on_focus_expr: {self.on_focus_expr}'
        else:
            on_focus_expr: str = ''
        if self.on_unfocus_expr is not None and (len(self.on_unfocus_expr) > 0):
            on_unfocus_expr: str = f'\n  on_unfocus_expr: {self.on_unfocus_expr}'
        else:
            on_unfocus_expr: str = ''

        orientation_str: str = ''
        if self.orientation_expr != '':
            orientation_str = f'\n  orientation: {self.orientation_expr}'

        page_control_str: str = ''
        if self.page_control != -1:
            page_control_str = f'\n  page_control: {self.page_control}'

        topic_str: str = ''
        if self.topic is not None:
            topic_str = f'\n  {self.topic}'

        viewtype_str: str = ''
        if self.viewtype != '':
            viewtype_str = f'\n  view_type: {self.viewtype}'

        item_layouts_str: str = ''
        item_layouts: List[str] = []
        for item_layout in self.item_layouts:
            tmp_str: str = f' \n {item_layout}'
            item_layouts.append(tmp_str)
        item_layouts_str = '\n'.join(item_layouts)

        focused_item_layouts_str: str = ''
        item_layouts.clear()
        for focused_item_layout in self.focused_layouts:
            tmp_str: str = f'\n {focused_item_layout}'
            item_layouts.append(tmp_str)
        focused_item_layouts_str = '\n'.join(item_layouts)

        results: List[str] = []
        result: str = (f'\nListModel type: {self.control_type} '
                       f'id: {self.control_id} '
                       f'{enable_str}'
                       f'{description_str}'
                       f'{visible_expr}'
                       f'{orientation_str}'
                       f'{page_control_str}'
                       f'{viewtype_str}'
                       f'{on_focus_expr}'
                       f'{on_unfocus_expr}'
                       f'{topic_str}'
                       f'{item_layouts_str}'
                       f'{focused_item_layouts_str}'
                       f'\n#children: {len(self.children)}')
        results.append(result)

        if include_children:
            for child in self.children:
                child: BaseModel
                result: str = child.to_string(include_children=include_children)
                results.append(result)
        results.append('END ListModel')
        return '\n'.join(results)
