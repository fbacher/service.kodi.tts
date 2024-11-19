# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import difflib
import re
import time

import xbmc

from common import *

from common.constants import Constants
from common.logger import BasicLogger
from common.messages import Messages
from common.phrases import Phrase, PhraseList
from .base import WindowReaderBase
MY_LOGGER = BasicLogger.get_logger(__name__)


class VirtualKeyboardReader(WindowReaderBase):
    ID = 'virtualkeyboard'
    ip_re = re.compile('^[\d ]{3}\.[\d ]{3}\.[\d ]{3}.[\d ]{3}$')

    def init(self) -> None:
        self.editID = None
        if self.winID == 10103:  # Keyboard
            if xbmc.getCondVisibility('Control.IsVisible(310)'):  # For Gotham
                self.editID = 310
            else:
                self.editID = 312
        elif self.winID == 10109:  # Numeric?
            self.editID = 4
        elif self.winID == 10607:  # PVR Search
            self.editID = 9
        self.keyboardText = ''
        self.lastChange = time.time()
        self.lastRead = None

    def getHeading(self, phrases: PhraseList) -> bool:
        text = xbmc.getInfoLabel('Control.GetLabel(311)')
        if text is not None:
            phrases.add_text(texts=text)
            return True
        return False

    def isIP(self, text=None):
        text = text or self.getEditText()
        return self.winID == 10109 and '.' in text  # Is numeric input with . in it,
        # so must be IP

    def getEditText(self):
        info = 'Control.GetLabel({0}).index(1)'.format(self.editID)
        return xbmc.getInfoLabel(info)

    #        t = xbmc.getInfoLabel(info)
    #        if t == info: return '' #To handle pre GetLabel().index() addition
    #        return t

    def getMonitoredText(self, isSpeaking=False):
        text = self.getEditText()
        if text != self.keyboardText:
            if not self.keyboardText and len(text) > 1:
                self.keyboardText = text
                self.lastChange = time.time()
                return None
            self.lastChange = time.time()
            out = ''
            d = difflib.Differ()
            if not text and self.keyboardText:
                self.keyboardText = ''
                out = Messages.get_msg(Messages.NO_TEXT)
            elif self.isIP(text):
                if self.isIP(text) and self.isIP(self.keyboardText):  # IP Address
                    oldip = self.keyboardText.replace(' ', '').split('.')
                    newip = text.replace(' ', '').split('.')
                    for old, new in zip(oldip, newip):
                        if old == new:
                            continue
                        out = ' '.join(list(new))
                        break
            elif len(text) > len(self.keyboardText):
                for c in d.compare(self.keyboardText, text):
                    if c.startswith('+'):
                        out += ' ' + (c.strip(' +') or Messages.get_msg(Messages.SPACE))
            else:
                for c in d.compare(self.keyboardText, text):
                    if c.startswith('-'):
                        out += ' ' + (c.strip(' -') or
                                      Messages.get_msg(Messages.SPACE))
                if out:
                    out = out.strip() + ' {0}'.format(
                            Messages.get_msg(Messages.DELETED))
            self.keyboardText = text
            if out:
                return out.strip()
        else:
            now = time.time()
            if now - self.lastChange > 2:  # We haven't had input for a second,
                # read all the text
                if text != self.lastRead:
                    self.lastChange = now
                    self.lastRead = text
                    if self.isIP(text):
                        return text.replace(' ', '')
                    return text
        return None


class PVRSGuideSearchDialogReader(VirtualKeyboardReader):
    ID = 'pvrguidesearch'
    editIDs = (9, 14, 15, 16, 17)

    def init(self):
        VirtualKeyboardReader.init(self)
        self.editID = 9

    def _resetEditInfo(self):
        self.lastChange = time.time()
        self.lastRead = None
        self.keyboardText = ''

    def getControlText(self, control_id: int, phrases: PhraseList) -> bool:
        cls = type(self)
        ID = self.window().getFocusId()
        if ID == 9:
            new_text = xbmc.getLocalizedString(19133)
        else:
            text = xbmc.getInfoLabel('System.CurrentControl')
            # For boolean settings
            new_text: str = text.replace('( )',
                                         f'{Constants.PAUSE_INSERT} '
                                         f'{Messages.get_msg(Messages.NO)}')
            new_text = new_text.replace('(*)', f'{Constants.PAUSE_INSERT} '
                                               f'{Messages.get_msg(Messages.YES)}')
            MY_LOGGER.debug(f'BOOLEAN substitution orig text: {text} New: {new_text} ')
        phrases.add_text(texts=new_text)
        return True

    def getMonitoredText(self, isSpeaking=False):
        ID = self.window().getFocusId()
        if not ID in self.editIDs:
            self._resetEditInfo()
            return None
        if ID != self.editID:
            self._resetEditInfo()
        self.editID = ID
        return VirtualKeyboardReader.getMonitoredText(self, isSpeaking=isSpeaking)
