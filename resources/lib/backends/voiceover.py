# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import subprocess
import sys

from common import *

from backends.base import SimpleTTSBackend
from common.logger import *
from common.setting_constants import Mode
from common.system_queries import SystemQueries

module_logger = BasicLogger.get_logger(__name__)


class VoiceOverBackend(SimpleTTSBackend):
    backend_id = 'voiceover'
    displayName = 'VoiceOver'
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__

    def init(self):
        self.setMode(Mode.ENGINESPEAK)

    def runCommandAndSpeak(self, text):
        subprocess.call(['osascript', '-e',
                         'tell application "voiceover" to output "{0}"'.format(
                                 text.replace('"', ''))], universal_newlines=True)

    def stop(self):
        subprocess.call(['osascript', '-e',
                         'tell application "voiceover" to output ""'],
                        universal_newlines=True)

    @staticmethod
    def available():
        return sys.platform == 'darwin' and not SystemQueries.isATV2()

# on isVoiceOverRunning()
#	set isRunning to false
#	tell application "System Events"
#		set isRunning to (name of processes) contains "VoiceOver"
#	end tell
#	return isRunning
# end isVoiceOverRunning
#
# on isVoiceOverRunningWithAppleScript()
#	if isVoiceOverRunning() then
#		set isRunningWithAppleScript to true
#
#		-- is AppleScript enabled on VoiceOver --
#		tell application "VoiceOver"
#			try
#				set x to bounds of vo cursor
#			on error
#				set isRunningWithAppleScript to false
#			end try
#		end tell
#		return isRunningWithAppleScript
#	end if
#	return false
# end isVoiceOverRunningWithAppleScript
