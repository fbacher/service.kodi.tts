# -*- coding: utf-8 -*-
import time
from .base import WindowReaderBase
from common import utils


class BusyDialogReader(WindowReaderBase):
    ID = 'busydialog'

    def init(self):
        self.next = 0
        self.play()

    def play(self):
        duration = utils.playSound('busy',return_duration=True)
        self.next = time.time() + duration

    def getMonitoredText(self,isSpeaking=False):
        now = time.time()
        if now > self.next:
            self.play()

    def close(self):
        utils.stopSounds()