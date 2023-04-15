# -*- coding: utf-8 -*-
import subprocess
import sys


from common.constants import Constants
from common.setting_constants import Languages, Players, Genders, Misc
from common.logger import *
from common.messages import Messages
from common.settings import Settings
from common.system_queries import SystemQueries
from common import utils
from common.system_queries import SystemQueries
from backends.base import SimpleTTSBackendBase

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class VoiceOverBackend(SimpleTTSBackendBase):
    provider = 'voiceover'
    displayName = 'VoiceOver'


    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(self.__class__.__name__)  # type: BasicLogger


    def init(self):
        self.setMode(SimpleTTSBackendBase.ENGINESPEAK)

    def runCommandAndSpeak(self,text):
        subprocess.call(['osascript', '-e',
                         'tell application "voiceover" to output "{0}"'.format(
                             text.replace('"',''))], universal_newlines=True)

    def stop(self):
        subprocess.call(['osascript', '-e',
                         'tell application "voiceover" to output ""'],
                        universal_newlines=True)

    @staticmethod
    def available():
        return sys.platform == 'darwin' and not SystemQueries.isATV2()

#on isVoiceOverRunning()
#	set isRunning to false
#	tell application "System Events"
#		set isRunning to (name of processes) contains "VoiceOver"
#	end tell
#	return isRunning
#end isVoiceOverRunning
#
#on isVoiceOverRunningWithAppleScript()
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
#end isVoiceOverRunningWithAppleScript
