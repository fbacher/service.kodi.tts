# coding=utf-8
import re
import sys
from enum import Enum
from typing import Dict, ForwardRef

import xbmc
import xbmcgui

from common import AbortException, reraise
from common.critical_settings import CriticalSettings
from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from gui import ControlElement

module_logger = BasicLogger.get_logger(__name__)


class AltCtrlType(Enum):
    """
    Provides default and alternative translated names for controls.
    """
    NONE = 0  # Used to suppress voicing a control_type
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
    LIST = 32717
    MENU_CONTROL = 1
    MOVER = 1
    MULTI_IMAGE = 1
    PANEL = 1
    PROGRESS = 1
    RANGES = 1
    RESIZE = 1
    RSS = 1
    SCROLL_BAR = 32713
    SLIDER = 32706
    SLIDER_EX = 32718
    SPIN_CONTROL_EX = 32719
    SPIN_CONTROL = 32710
    TOGGLE_BUTTON = 1
    VIDEO_WINDOW = 1
    VISUALISATION = 1
    WRAP_LIST = 1
    LABEL = 32703
    RADIO_BUTTON = 32704
    TEXT_BOX = 32705
    TOGGLE = 32707
    BUTTON_LIST = 32708
    DIALOG = 32709


    @classmethod
    def get_alt_type_for_name(cls, alt_type_name: str) -> ForwardRef('AltCtrlType'):
        """
        Converts the given alt_type name into an AltCtrlType
        :param alt_type_name: an AltCtrlType.name value
        :return:
        """
        try:
            module_logger.debug(f'alt_type_name: {alt_type_name}')
            result = AltCtrlType[alt_type_name]
            module_logger.debug(f'alt_type_name: {alt_type_name} AltCtrltype: '
                                f'result: {result}')
            return result
        except AbortException:
            reraise(*sys.exc_info())
        except Exception | KeyError:
            module_logger.exception(f'alt_type_name: {alt_type_name}')
            raise ValueError('Invalid alt_ctrl_type name: {alt_type_name}')

    @classmethod
    def get_default_alt_ctrl_type(cls,
                                  ctrl_element: ControlElement
                                  ) -> ForwardRef('AltCtrlType'):
        """
        Gets the default translateable AltCtlType for the given ControlElement

        :param ctrl_element: ControlElement to get the default AltCtrlType for
        :return:
        :raise ValueError: if no AltCtrlTyep can be found for the ctrl_Element
        """
        ctrl_type: AltCtrlType
        # cls.debug(f'ctrl_name: {ctrl_name}')
        ctrl_type = UIConstants.alt_ctrl_type_for_ctrl_type.get(ctrl_element, None)
        if ctrl_type is None:
            raise ValueError('Could not find equivalent AltCtrlType for '
                             'control_type: {ctrl_name}')
        # module_logger.debug(f'ctrl_type: {ctrl_type} value: {ctrl_type.value}')
        return ctrl_type

    def get_message(self, phrases: PhraseList) -> bool:
        text: str = self.get_message_str()
        if text == '':
            return False
        phrases.append(Phrase(text=text))
        return True

    def get_message_str(self) -> str:
        msg_id: int = self.value
        if msg_id == -1:
            return 'Missing -1'  # Use default
        if msg_id == 0:
            text = ''
        else:
            text: str = Messages.get_msg_by_id(msg_id)
        return text


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

    alt_ctrl_type_for_ctrl_type: Dict[ControlElement, ForwardRef('AltCtrlType')] = {
        ControlElement.BUTTON              : AltCtrlType.BUTTON,
        ControlElement.CONTROLS            : AltCtrlType.CONTROLS,
        ControlElement.CONTROL             : AltCtrlType.CONTROL,
        ControlElement.DIALOG              : AltCtrlType.DIALOG,
        ControlElement.EDIT                : AltCtrlType.EDIT,
        ControlElement.EPG_GRID            : AltCtrlType.EPG_GRID,
        ControlElement.FADE_LABEL          : AltCtrlType.FADE_LABEL,
        ControlElement.FIXED_LIST          : AltCtrlType.FIXED_LIST,
        ControlElement.GAME_CONTROLLER     : AltCtrlType.GAME_CONTROLLER,
        ControlElement.GAME_CONTROLLER_LIST: AltCtrlType.GAME_CONTROLLER_LIST,
        ControlElement.GAME_WINDOW         : AltCtrlType.GAME_WINDOW,
        ControlElement.GROUP               : AltCtrlType.GROUP,
        ControlElement.GROUP_LIST          : AltCtrlType.GROUP_LIST,
        ControlElement.IMAGE               : AltCtrlType.IMAGE,
        ControlElement.LABEL_CONTROL       : AltCtrlType.LABEL,
        ControlElement.LIST                : AltCtrlType.LIST,
        ControlElement.MENU_CONTROL        : AltCtrlType.MENU_CONTROL,
        ControlElement.MOVER               : AltCtrlType.MOVER,
        ControlElement.MULTI_IMAGE         : AltCtrlType.MULTI_IMAGE,
        ControlElement.PANEL               : AltCtrlType.PANEL,
        ControlElement.PROGRESS            : AltCtrlType.PROGRESS,
        ControlElement.RADIO_BUTTON        : AltCtrlType.RADIO_BUTTON,
        ControlElement.RANGES              : AltCtrlType.RANGES,
        ControlElement.RESIZE              : AltCtrlType.RESIZE,
        ControlElement.RSS                 : AltCtrlType.RSS,
        ControlElement.SCROLL_BAR          : AltCtrlType.SCROLL_BAR,
        ControlElement.SLIDER_EX           : AltCtrlType.SLIDER_EX,
        ControlElement.SLIDER              : AltCtrlType.SLIDER,
        ControlElement.SPIN_CONTROL_EX     : AltCtrlType.SPIN_CONTROL_EX,
        ControlElement.SPIN_CONTROL        : AltCtrlType.SPIN_CONTROL,
        ControlElement.TEXT_BOX            : AltCtrlType.TEXT_BOX,
        ControlElement.TOGGLE_BUTTON       : AltCtrlType.TOGGLE_BUTTON,
        ControlElement.UNKNOWN             : AltCtrlType.UNKNOWN,
        ControlElement.VIDEO_WINDOW        : AltCtrlType.VIDEO_WINDOW,
        ControlElement.VISUALISATION       : AltCtrlType.VISUALISATION,
        ControlElement.WINDOW              : AltCtrlType.WINDOW,
        ControlElement.WRAP_LIST           : AltCtrlType.WRAP_LIST}
