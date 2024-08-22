# coding=utf-8
import re
from enum import Enum
from typing import Dict, ForwardRef

import xbmc
import xbmcgui

from common.critical_settings import CriticalSettings
from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui import ControlType

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class AltCtrlType(Enum):
    NONE = 0
    UNKNOWN = 32700
    WINDOW = 32701
    BUTTON = 32702
    CONTROL = 1
    CONTROLS = 1
    EDIT = 32710
    EPG_GRID = 1
    FIXED_LIST = 1
    FADE_LABEL = 1
    GAME_CONTROLLER = 1
    GAME_CONTROLLER_LIST = 1
    GAME_WINDOW = 1
    GROUP = 32711
    GROUP_LIST = 32712
    IMAGE = 1
    LIST = 1
    MENU_CONTROL = 1
    MOVER = 1
    MULTI_IMAGE = 1
    PANEL = 1
    PROGRESS = 1
    RANGES = 1
    RESIZE = 1
    RSS = 1
    SCROLL_BAR = 32713
    SLIDER_EX = 1
    SPIN_CONTROL_EX = 1
    SPIN_CONTROL = 32710
    TOGGLE_BUTTON = 1
    VIDEO_WINDOW = 1
    VISUALISATION = 1
    WRAP_LIST = 1
    LABEL = 32703
    RADIO_BUTTON = 32704
    TEXT_BOX = 32705
    SLIDER = 32706
    TOGGLE = 32707
    BUTTON_LIST = 32708
    DIALOG = 32709

    @staticmethod
    def get_ctrl_type_for_control(ctrl: xbmcgui.Control) -> ForwardRef('AltCtrlType'):
        ctrl_type: str = f'{type(ctrl)}'
        # module_logger.debug(f'ctrl_type: {ctrl_type}')

    @staticmethod
    def alt_ctrl_type_for_ctrl_name(ctrl_name: str) -> ForwardRef('AltCtrlType'):
        ctrl_type: AltCtrlType
        # module_logger.debug(f'ctrl_name: {ctrl_name}')
        try:
            ctrl_type = AltCtrlType(ctrl_name)
            # module_logger.debug(f'ctrl_type: {ctrl_type} value: {ctrl_type.value}')
        except Exception as e:
            try:
                ctrl_type = AltCtrlType[ctrl_name]
                # module_logger.debug(f'ctrl_type: {ctrl_type} {ctrl_type.value}')
            except Exception as e:
                ctrl_type = AltCtrlType.UNKNOWN
                # module_logger.debug(f'ctrl_type: {ctrl_type} {ctrl_type.value}')
        return ctrl_type

    @staticmethod
    def get_message(ctrl: ForwardRef('AltCtrlType'),
                    phrases: PhraseList) -> bool:
        text: str = Messages.get_msg_by_id(ctrl.value)
        if text == '':
            return False
        phrases.append(Phrase(text=text))
        return True


class UIConstants:

    TAG_RE = re.compile(r'\[/?(?:B|I|COLOR|UPPERCASE|LOWERCASE)[^]]*]',
                        re.IGNORECASE)
    VAR_RE = re.compile(r'\$VAR\[([^]]*)]')
    LOCALIZE_RE = re.compile(r'\$LOCALIZE\[([^]]*)]')
    ADDON_RE = re.compile(r'\$ADDON\[[\w+.]+ (\d+)]')
    INFOLABEL_RE = re.compile(r'\$INFO\[([^]]*)]')
    FORMAT_TAG_RE = re.compile(r'\[/?(?:CR|B|I|UPPERCASE|LOWERCASE)]',
                               re.IGNORECASE)
    COLOR_TAG_RE = re.compile(r'\[/?COLOR[^]\[]*?]', re.IGNORECASE)
    OK_TAG_RE = re.compile(r'(^|\W|\s)OK($|\s|\W)')  # Prevents saying Oklahoma
    PUNCTUATION_PATTERN = re.compile(r'([.,:])', re.DOTALL)

    VERTICAL = 'vertical'

    alt_ctrl_type_for_ctrl_type: Dict[ControlType, ForwardRef('AltCtrlType')] = {
        ControlType.BUTTON: AltCtrlType.BUTTON,
        ControlType.CONTROLS: AltCtrlType.CONTROLS,
        ControlType.CONTROL: AltCtrlType.CONTROL,
        ControlType.DIALOG: AltCtrlType.DIALOG,
        ControlType.EDIT                : AltCtrlType.EDIT,
        ControlType.EPG_GRID            : AltCtrlType.EPG_GRID,
        ControlType.FADE_LABEL          : AltCtrlType.FADE_LABEL,
        ControlType.FIXED_LIST          : AltCtrlType.FIXED_LIST,
        ControlType.GAME_CONTROLLER     : AltCtrlType.GAME_CONTROLLER,
        ControlType.GAME_CONTROLLER_LIST: AltCtrlType.GAME_CONTROLLER_LIST,
        ControlType.GAME_WINDOW         : AltCtrlType.GAME_WINDOW,
        ControlType.GROUP               : AltCtrlType.GROUP,
        ControlType.GROUP_LIST          : AltCtrlType.GROUP_LIST,
        ControlType.IMAGE               : AltCtrlType.IMAGE,
        ControlType.LABEL               : AltCtrlType.LABEL,
        ControlType.LIST                : AltCtrlType.LIST,
        ControlType.MENU_CONTROL        : AltCtrlType.MENU_CONTROL,
        ControlType.MOVER               : AltCtrlType.MOVER,
        ControlType.MULTI_IMAGE         : AltCtrlType.MULTI_IMAGE,
        ControlType.PANEL               : AltCtrlType.PANEL,
        ControlType.PROGRESS            : AltCtrlType.PROGRESS,
        ControlType.RADIO_BUTTON        : AltCtrlType.RADIO_BUTTON,
        ControlType.RANGES              : AltCtrlType.RANGES,
        ControlType.RESIZE              : AltCtrlType.RESIZE,
        ControlType.RSS                 : AltCtrlType.RSS,
        ControlType.SCROLL_BAR: AltCtrlType.SCROLL_BAR,
        ControlType.SLIDER_EX: AltCtrlType.SLIDER_EX,
        ControlType.SLIDER: AltCtrlType.SLIDER,
        ControlType.SPIN_CONTROL_EX: AltCtrlType.SPIN_CONTROL_EX,
        ControlType.SPIN_CONTROL: AltCtrlType.SPIN_CONTROL,
        ControlType.TEXT_BOX: AltCtrlType.TEXT_BOX,
        ControlType.TOGGLE_BUTTON: AltCtrlType.TOGGLE_BUTTON,
        ControlType.UNKNOWN: AltCtrlType.UNKNOWN,
        ControlType.VIDEO_WINDOW: AltCtrlType.VIDEO_WINDOW,
        ControlType.VISUALISATION: AltCtrlType.VISUALISATION,
        ControlType.WINDOW: AltCtrlType.WINDOW,
        ControlType.WRAP_LIST: AltCtrlType.WRAP_LIST}
