from __future__ import annotations  # For union operator |

# TODO: NOT WORKING AND NOT USED CURRENTLY

# -*- coding: utf-8 -*-
import xbmcgui

from common import *
from common.logger import BasicLogger

from common.messages import Messages
from common.monitor import Monitor
from utils import addoninfo
from .base import WindowHandlerBase

module_logger = BasicLogger.get_logger(__name__)


class NoticeDialog(WindowHandlerBase):
    ID = 'info'

    def __init__(self, win_id=None,
                 service: ForwardRef('TTSService') = None) -> None:
        super().__init__(win_id, service)
        self.notices = []
        self._visible = True  # Pretend info was shown so we check stuff on startup
        self.lastHeading = ''  # 401
        self.lastMessage = ''  # 402

    def init(self):
        self.notices = []
        self._visible = True  # Pretend info was show so we check stuff on startup
        self.lastHeading = ''  # 401
        self.lastMessage = ''  # 402
        self.setWindow()
        return self

    def visible(self):
        visible = WindowHandlerBase.visible(self)
        if visible:
            self._visible = True
            return True
        elif self._visible:
            self._visible = False
            return True
        return False

    def setWindow(self):
        self.win = xbmcgui.Window(10107)

    def addNotice(self, heading, message):
        if heading == self.lastHeading and message == self.lastMessage:
            return False
        self.lastHeading = heading
        self.lastMessage = message
        self.notices.append((heading, message))
        return True

    def takeNoticesForSpeech(self):
        # print 'y'
        if not self.notices:
            return None
        ret = []
        for n in self.notices:
            ret.append(
                '{0}: {1}... {2}'.format(Messages.get_msg(Messages.NOTICE), n[0], n[1]))
        self.init()
        # print ret
        return ret

    def getMonitoredText(self,
                         isSpeaking: bool = False) -> str | None:
        # getLabel() Doesn't work currently with FadeLabels
        Monitor.exception_on_abort()
        if self._visible:
            return None
        if not addoninfo.checkForNewVersions():
            return None
        details = addoninfo.getUpdatedAddons()
        if not details:
            return None
        ret = ['{0}... '.format(Messages.get_msg(Messages.ADDONS_UPDATED))]
        for d in details:
            item = '{0} {1} {2}'.format(d['name'], Messages.get_msg(Messages.VERSION),
                                        d['version'])
            if not item in ret:
                ret.append(item)
        # print ret
        return ret
#        #print 'x'
#        heading = self.win.getControl(401).getLabel()
#        message = self.win.getControl(402).getLabel()
#        #print repr(message)
#        self.addNotice(heading,message)
#        if not is_speaking: return self.takeNoticesForSpeech()
#        return None


# class NoticeDialogReader(NoticeHandler,WindowReaderBase): pass
