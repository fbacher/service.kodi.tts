# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmc

from common import *
from common.logger import *
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from . import guitables
from .base import WindowReaderBase

str_or_int: str | int
module_logger = BasicLogger.get_logger(__name__)


class PVRWindowReaderBase(WindowReaderBase):

    def controlIsOnView(self, control_id) -> bool:
        return not xbmc.getCondVisibility('ControlGroup(9000).HasFocus(0)')

    def init(self):
        self.mode = False

    def updateMode(self, control_id):
        if self.controlIsOnView(control_id):
            self.mode = 'VIEW'
        else:
            self.mode = None
        return self.mode

    def getControlDescription(self, control_id, phrases: PhraseList) -> bool:
        old = self.mode
        new = self.updateMode(control_id)
        if new is None and old is not None:
            phrases.add_text(texts='View Options')
            return True
        return False


class PVRGuideWindowReader(PVRWindowReaderBase):
    ID = 'pvrguide'
    timelineInfo: Tuple[str_or_int, ...]
    timelineInfo = (Messages.get_msg(Messages.CHANNEL),  # PVR
                    '$INFO[ListItem.ChannelNumber]',
                    '$INFO[ListItem.ChannelName]',
                    '$INFO[ListItem.StartTime]',
                    19160,
                    '$INFO[ListItem.EndTime]',
                    '$INFO[ListItem.Plot]'
                    )

    nowNextInfo: Tuple[str_or_int, ...]
    nowNextInfo = (Messages.get_msg(Messages.CHANNEL),
                   '$INFO[ListItem.ChannelNumber]',
                   '$INFO[ListItem.ChannelName]',
                   '$INFO[ListItem.StartTime]',
                   '$INFO[ListItem.Plot]'
                   )

    def getControlText(self, control_id: int | None, phrases: PhraseList) -> bool:
        cls = type(self)
        compare: str
        text: str
        if not control_id:
            return False
        if self.slideoutHasFocus():
            return self.getSlideoutText(control_id, phrases)
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text:
            return False
        text_id: str = (f"{text}{xbmc.getInfoLabel('ListItem.StartTime')}"
                        f"{xbmc.getInfoLabel('ListItem.EndTime')}")
        phrases.add_text(texts=text, text_id=text_id)
        return True

    def getItemExtraTexts(self, control_id: int, phrases: PhraseList) -> bool:
        success: bool = False
        if self.controlIsOnView(control_id):
            if control_id == 10:  # EPG: Timeline
                success = guitables.convertTexts(self.winID, self.timelineInfo, phrases)
            elif control_id == 11 or control_id == 12 or control_id == 13:  # EPG:
                # Now/Next/Channel
                next_info = list(self.nowNextInfo)
                if xbmc.getCondVisibility('ListItem.IsRecording'):
                    next_info.append(19043)
                elif xbmc.getCondVisibility('ListItem.HasTimer'):
                    next_info.append(31510)
                success = guitables.convertTexts(self.winID, tuple(next_info), phrases)

        return success


class PVRChannelsWindowReader(PVRWindowReaderBase):
    ID = 'pvrchannels'

    channelInfo = ('$INFO[ListItem.StartTime]',
                   19160,
                   '$INFO[ListItem.EndTime]',
                   '$INFO[ListItem.Plot]'
                   )

    def getControlText(self, control_id, phrases: PhraseList) -> bool:
        cls = type(self)
        if cls._logger.isEnabledFor(DEBUG_XV):
            cls._logger.debug_xv(f'control_id: {control_id}')
        compare: str
        text: str
        if not control_id:
            return False
        if self.slideoutHasFocus():
            return self.getSlideoutText(control_id, phrases)
        text = f'{xbmc.getInfoLabel("ListItem.ChannelNumber")}... ' \
               f'{xbmc.getInfoLabel("ListItem.Label")}... ' \
               f'{xbmc.getInfoLabel("ListItem.Title")}'
        if not text:
            return False
        text_id: str = text + xbmc.getInfoLabel('ListItem.StartTime') + xbmc.getInfoLabel(
            'ListItem.EndTime')
        phrases.add_text(texts=text, text_id=text_id)
        return True

    def getItemExtraTexts(self, control_id: int, phrases: PhraseList) -> bool:
        success: bool = False
        if self.controlIsOnView(control_id):
            if control_id == 50:  # Channel (TV or Radio)
                info_text = list(self.channelInfo)
                if xbmc.getCondVisibility('ListItem.IsRecording'):
                    info_text.insert(0, 19043)
                success = guitables.convertTexts(self.winID, info_text, phrases)
        return success


class PVRRecordingsWindowReader(PVRWindowReaderBase):
    ID = 'pvrrecordings'

    def getControlText(self, control_id, phrases: PhraseList) -> bool:
        clz = type(self)
        if not control_id:
            return False
        if self.slideoutHasFocus():
            return self.getSlideoutText(control_id, phrases)
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text:
            return False
        return True

    def getItemExtraTexts(self, control_id, phrases: PhraseList) -> bool:
        if self.controlIsOnView(control_id):
            return guitables.convertTexts(self.winID, ('$INFO[ListItem.Plot]',),
                                          phrases)
        return False


class PVRTimersWindowReader(PVRWindowReaderBase):
    ID = 'pvrtimers'

    timerInfo = ('$INFO[ListItem.ChannelName]',
                 '$INFO[ListItem.Label]',
                 '$INFO[ListItem.Date]',
                 '$INFO[ListItem.Comment]'
                 )

    def getControlText(self, control_id: int | None, phrases: PhraseList) -> bool:
        clz = type(self)
        text: str
        compare: str
        if not control_id:
            return False
        if self.slideoutHasFocus():
            return self.getSlideoutText(control_id, phrases)
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text:
            return False
        text_id: str = text + xbmc.getInfoLabel('ListItem.StartTime') + xbmc.getInfoLabel(
            'ListItem.EndTime')
        phrases.add_text(texts=text, text_id=text_id)
        return True

    def getItemExtraTexts(self, control_id: int| None, phrases: PhraseList) -> bool:
        if self.controlIsOnView(control_id):
            return guitables.convertTexts(self.winID, self.timerInfo, phrases)


class PVRSearchWindowReader(PVRWindowReaderBase):
    ID = 'pvrsearch'

    searchInfo = ('$INFO[ListItem.ChannelNumber]',
                  '$INFO[ListItem.ChannelName]',
                  '$INFO[ListItem.Date]'
                  )

    def getControlText(self, control_id: int | None, phrases: PhraseList) -> bool:
        clz = type(self)
        if not control_id:
            return False
        if self.slideoutHasFocus():
            return self.getSlideoutText(control_id, phrases)
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text:
            return False
        text_id: str = text + xbmc.getInfoLabel('ListItem.Date')
        phrases.add_text(texts=text, text_id=text_id)
        return True

    def getItemExtraTexts(self, control_id: int | None, phrases: PhraseList) -> bool:
        if self.controlIsOnView(control_id):
            text_info = list(self.searchInfo)
            if xbmc.getCondVisibility('ListItem.IsRecording'):
                text_info.append(19043)
            elif xbmc.getCondVisibility('ListItem.HasTimer'):
                text_info.append(31510)
            return guitables.convertTexts(self.winID, tuple(text_info), phrases)
        return False


class PVRWindowReader(PVRWindowReaderBase):
    ID = 'pvr'
    timelineInfo = (Messages.get_msg(Messages.CHANNEL),
                    '$INFO[ListItem.ChannelNumber]',
                    '$INFO[ListItem.ChannelName]',
                    '$INFO[ListItem.StartTime]',
                    19160,
                    '$INFO[ListItem.EndTime]',
                    '$INFO[ListItem.Plot]'
                    )

    channelInfo = ('$INFO[ListItem.StartTime]',
                   19160,
                   '$INFO[ListItem.EndTime]',
                   '$INFO[ListItem.Plot]'
                   )

    nowNextInfo = (Messages.get_msg(Messages.CHANNEL),
                   '$INFO[ListItem.ChannelNumber]',
                   '$INFO[ListItem.ChannelName]',
                   '$INFO[ListItem.StartTime]',
                   '$INFO[ListItem.Plot]'
                   )

    def controlIsOnView(self, control_id: int) -> bool:
        return 9 < control_id < 18

    def getControlText(self, control_id: int, phrases: PhraseList) -> bool:
        clz = type(self)
        phrases: PhraseList = PhraseList(check_expired=False)
        if not control_id:
            return False
        success: bool = False
        text: str = ''
        all_texts: str = ''
        orig_phrase_count: int = len(phrases)
        if control_id == 11 or control_id == 12:  # Channel (TV or Radio)
            text = f"{xbmc.getInfoLabel('ListItem.ChannelNumber')}"
            all_texts = text
            phrases.add_text(texts=text,
                             post_pause_ms=Phrase.PAUSE_SHORT)
            text = "{xbmc.getInfoLabel('ListItem.Label')'}"
            all_texts += text
            phrases.add_text(texts=text,
                             post_pause_ms=Phrase.PAUSE_SHORT)
            text = "{xbmc.getInfoLabel('ListItem.Title')}"
            all_texts += text
            phrases.add_text(texts=text)
        else:
            text = xbmc.getInfoLabel('System.CurrentControl')
            all_texts = text
            phrases.add_text(texts=text)

        text_id: str = (f"{all_texts} {xbmc.getInfoLabel('ListItem.StartTime')} "
                        f"{xbmc.getInfoLabel('ListItem.EndTime')}")
        phrases[orig_phrase_count].set_text_id(text_id)
        return True

    def getItemExtraTexts(self, control_id, phrases: PhraseList) -> bool:
        if self.controlIsOnView(control_id):
            if control_id == 10:  # EPG: Timeline
                return guitables.convertTexts(self.winID, self.timelineInfo, phrases)
            elif control_id == 11 or control_id == 12:  # Channel (TV or Radio)
                return guitables.convertTexts(self.winID, self.channelInfo, phrases)
            elif control_id == 16:  # EPG: Now/Next
                return guitables.convertTexts(self.winID, self.nowNextInfo, phrases)
        return False
