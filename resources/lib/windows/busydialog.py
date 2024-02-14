# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import time

from common import *

from common import utils
from .base import WindowReaderBase


class BusyDialogReader(WindowReaderBase):
    ID = 'busydialog'

    def __init__(self, win_id: str = None,
                 service: ForwardRef('TTSService') = None) -> None:
        super().__init__(win_id, service)
        pass

    def init(self):
        self.next = 0
        self.play()

    def play(self):
        duration = utils.playSound('busy', return_duration=True)
        self.next = time.time() + duration

    def getMonitoredText(self, isSpeaking=False):
        now = time.time()
        if now > self.next:
            self.play()

    def close(self):
        utils.stopSounds()
