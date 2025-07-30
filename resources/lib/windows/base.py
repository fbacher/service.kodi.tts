# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc
import xbmcgui

from common import *

from common.constants import Constants
from common.logger import *
from common.logger import BasicLogger
from common.message_ids import MessageId
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from . import guitables, skintables, windowparser
from .window_state_monitor import WinDialogState

CURRENT_SKIN = skintables.CURRENT_SKIN

MY_LOGGER = BasicLogger.get_logger(__name__)


def parseItemExtra(control_id, excludes: PhraseList, phrases: PhraseList) -> bool:
    """
    Finds text other than the most common related to the given control.
    Common text is a control's InfoLabel, InfoLabel2, Label control, etc..
    Here we hunt for more labels from the window's xml that are visible
    and children of the control.

    :param control_id:
    :param excludes: 'common' text that has already been found and voiced
                     elsewhere
    :param phrases: results are appended to
    :return:
    """
    success: bool = False
    texts: List[str] = windowparser.getWindowParser().getListItemTexts(control_id)
    if excludes is not None and texts is not None and not excludes.is_empty():
        phrase: Phrase
        for phrase in excludes:
            texts.pop(texts.index(phrase.get_text()))

    if len(texts) == 0:
        return False
    for text in texts:
        phrases.add_text(texts=text)
    return success


class WindowHandlerBase:
    ID = None

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None,
                 windialog_state: WinDialogState = None):
        self.service_prop: ForwardRef('TTSService') = service
        self.winID = win_id
        self._reset(win_id)

    @property
    def service(self) -> ForwardRef('TTSService'):
        from service_worker import TTSService
        self.service_prop = TTSService.instance
        return self.service_prop

    def _reset(self, win_id):
        self.winID = win_id
        self.init()

    def window(self):
        return xbmcgui.Window(self.winID)

    def visible(self):
        return xbmc.getCondVisibility(f'Window.IsVisible({self.winID})')

    def init(self): pass

    def getMonitoredText(self, isSpeaking=False): return None

    def close(self): pass


class WindowReaderBase(WindowHandlerBase):
    _slideoutGroupID = 9000

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None,
                 windialog_state: WinDialogState = None) -> None:
        cls = type(self)
        super().__init__(win_id, service)

    def getName(self) -> str:
        return guitables.getWindowName(self.winID)

    def getHeading(self, phrases: PhraseList) -> bool:
        return False

    def getWindowTexts(self, phrases: PhraseList) -> bool:
        return False

    def getControlDescription(self, control_id, phrases: PhraseList) -> bool:
        clz = type(self)
        return False

    def getControlText(self, control_id, phrases: PhraseList) -> bool:
        clz = type(self)
        text: str
        text = xbmc.getInfoLabel('System.CurrentControl')
        phrases.add_text(texts=text)
        return True

    def getControlPostfix(self, control_id, phrases: PhraseList) -> bool:
        cls = type(self)
        if not self.service.speakListCount:
            return False

        numItems: str = xbmc.getInfoLabel(f'Container'
                                          f'({self.service.current_control_id}).NumItems')
        if numItems:
            tmp: str = ''
            if numItems == 1:
                tmp = MessageId.ITEM_WITH_NUMBER.get_formatted_msg(numItems)
            else:
                tmp = MessageId.ITEMS_WITH_NUMBER.get_formatted_msg(numItems)
            phrase: Phrase = Phrase(text=tmp, pre_pause_ms=Phrase.PAUSE_NORMAL,
                                    check_expired=False)
            phrases.append(phrase)
        return True

    def getSecondaryText(self, phrases: PhraseList) -> bool:
        return False

    def getItemExtraTexts(self, phrases: PhraseList, control_id: int) -> bool:
        return False

    def getWindowExtraTexts(self, phrases: PhraseList) -> bool:
        old_phrase_count: int = len(phrases)
        success: bool = guitables.getExtraTexts(self.winID, phrases)
        if old_phrase_count == len(phrases):
            success = windowparser.getWindowParser().getWindowTexts(phrases)
        if old_phrase_count == len(phrases):
            return False
        return True

    def slideoutHasFocus(self) -> bool:
        visible: bool = xbmc.getCondVisibility(f'ControlGroup({self._slideoutGroupID})'
                                               f'.HasFocus({self._slideoutGroupID})')
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug(f'slideoutGroupID: {self._slideoutGroupID} visible: '
                            f'{visible}')
        return visible

    def getSettingControlText(self, control_id) -> str:
        cls = type(self)
        text: str = xbmc.getInfoLabel('System.CurrentControl')
        if text is None:
            return ''
        # text = f'control_id: {control_id} {text}'
        if text.endswith(')'):  # Skip this most of the time
            # For boolean settings
            new_text: str = text.replace('( )', f'{Constants.PAUSE_INSERT} '
                                                f'{Messages.get_msg(Messages.NO)}')
            new_text = new_text.replace('(*)', f'{Constants.PAUSE_INSERT} '
                                        f'{Messages.get_msg(Messages.YES)}')
            MY_LOGGER.debug(f'BOOLEAN control_id: {control_id} text: {new_text}')
            text = new_text
        return text

    def getSlideoutText(self, control_id, phrases: PhraseList) -> bool:
        text: str = self.getSettingControlText(control_id)
        if text != '':
            phrases.append(Phrase(text=text,
                                  debug_info='WindowReaderBase.getSlideoutText',
                                  check_expired=False))
            return True
        return False


class DefaultWindowReader(WindowReaderBase):
    ID = 'default'

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None,
                 windialog_state: WinDialogState = None) -> None:
        super().__init__(win_id, service)
        pass

    def getHeading(self, phrases: PhraseList) -> bool:
        text: str | None = xbmc.getInfoLabel('Control.GetLabel(1)')
        if text is not None and text != '':
            phrases.add_text(texts=text)
            return True
        return False

    def getWindowTexts(self, phrases: PhraseList) -> bool:
        return guitables.getWindowTexts(self.winID, phrases)

    def getControlDescription(self, control_id, phrases: PhraseList) -> bool:
        clz = type(self)
        return skintables.getControlText(self.winID, control_id, phrases)

    def getControlText(self, control_id: int, phrases: PhraseList) -> bool:
        clz = type(self)
        text: str
        success: bool = False
        MY_LOGGER.debug(f'control_id: {control_id} incomming phrases:{phrases}')
        if self.slideoutHasFocus():
            success = self.getSlideoutText(control_id, phrases)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'slideoutHasFocus: {success} phrases: {phrases}')
            return True   # TODO: Change?
        if control_id is None:
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'control_id {control_id} not found')
            #  return False
        # First, see if there is a ListItem with the title of
        # the currently selected song, movie, game in a container.
        text: str | None = xbmc.getInfoLabel('ListItem.Title')
        text2: str | None = None

        if text and MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'text: |{text}|')

        if text == '':
            # No title, then try for label1 & label2 from a possible container for
            # the current focused item.
            text = xbmc.getInfoLabel(f'Container({control_id}).ListItem.Label')
            text2 = xbmc.getInfoLabel(f'Container({control_id}).ListItem.Label2')
            if text and MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'text: {text} text2: {text2}')
        if text == '':
            # No ListItem label and/or label2, try for a plain label for the
            # control
            text = xbmc.getInfoLabel(f'Control.GetLabel({control_id})')
            # text2 = xbmc.getInfoLabel(f'Control.getLabel({control_id}).index(1)')
            query: str = f'Control.GetLabel({control_id}).index(1)'
            text2: str = xbmc.getInfoLabel(query)
            if text2 is None and control_id == 6051:
                text2 = xbmc.getInfoLabel(f'Container({control_id}).ListItem.Label2')
                MY_LOGGER.debug(f'text2b: {text2}')
                text2 = xbmc.getInfoLabel('Container.Viewmode')
            if text is not None and MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'text: {text} text2: {text2}')
        if text == '':
            text = xbmc.getInfoLabel('System.CurrentControl')

            if MY_LOGGER.isEnabledFor(DEBUG_XV) and text:
                MY_LOGGER.debug_xv(f'text: {text}')
        if text == '':
            return False
        text_id: str = (f"{text}{xbmc.getInfoLabel('ListItem.StartTime')}"
                        f"{xbmc.getInfoLabel('ListItem.EndTime')}")
        if text_id and MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'text_id: {text_id}')
        texts: List[str] = [text]
        if text2 is not None:
            texts.append(text2)
        new_phrase_idx: int = len(phrases)
        phrases.add_text(texts=texts)
        phrase: Phrase
        for phrase in phrases.data[new_phrase_idx:]:
            phrase.set_text_id(text_id)
        return True

    def getSecondaryText(self, phrases: PhraseList) -> bool:
        clz = type(self)
        success: bool = guitables.getListItemProperty(self.winID, phrases)
        if MY_LOGGER.isEnabledFor(DEBUG_V) and not phrases.is_empty():
            MY_LOGGER.debug_v(f'secondaryText: {phrases}')
        return success

    def getItemExtraTexts(self, phrases: PhraseList, control_id: int) -> bool:
        """
        Following a specific order of 'extra text' sources, add the first one
        found to our phrases
        :param control_id:
        :param phrases:
        :return:
        """
        clz = type(self)
        old_phrase_count: int = len(phrases)
        success: bool = False
        success = guitables.getItemExtraTexts(self.winID, phrases)
        text: str | List[str] | None = None
        if old_phrase_count == len(phrases):
            text = xbmc.getInfoLabel('ListItem.Plot')
            if not text:
                text = xbmc.getInfoLabel('Container.ShowPlot')
            if not text:
                text = xbmc.getInfoLabel('ListItem.Property(Artist_Description)')
            if not text:
                text = xbmc.getInfoLabel('ListItem.Property(Album_Description)')
            if not text:
                text = xbmc.getInfoLabel('ListItem.Property(Addon.Description)')
            if not text:
                text = guitables.getSongInfo()
            if text:
                phrases.add_text(texts=text)
                success = True
            else:
                tmp_phrases: PhraseList = PhraseList(check_expired=False)
                self.getControlText(control_id, tmp_phrases)
                tmp_item_extras: PhraseList
                success = parseItemExtra(control_id, excludes=tmp_phrases,
                                         phrases=phrases)
        return success


class NullReader(WindowReaderBase):
    ID = 'null'

    def __init__(self, win_id=None, service: ForwardRef('TTSService') = None,
                 windialog_state: WinDialogState = None) -> None:
        super().__init__(win_id, service)
        pass

    def getName(self) -> str | None:
        return None

    def getControlText(self, control_id, phrases: PhraseList) -> bool:
        return False

    def getWindowExtraTexts(self, phrases: PhraseList) -> bool:
        return False


class KeymapKeyInputReader(NullReader):
    ID = 'keymapkeyinput'

    def getWindowTexts(self, phrases: PhraseList) -> bool:
        phrases.add_text(texts=Messages.get_msg(Messages.PRESS_THE_KEY_TO_ASSIGN))
        return True
