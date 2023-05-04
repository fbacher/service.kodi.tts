# -*- coding: utf-8 -*-
import locale, os
from typing import Any, List, Union, Type

from backends.audio import BasePlayerHandler, WavAudioPlayerHandler
from backends.base import SimpleTTSBackendBase, ThreadedTTSBackend
from backends import base
from backends.audio import BuiltInAudioPlayer, BuiltInAudioPlayerHandler
from backends.speechd import Speaker, SSIPCommunicationError
from common.constants import Constants
from common.setting_constants import Backends, Languages, Players, Genders, Misc
from common.logger import *
from common.messages import Messages
from common.settings import Settings
from common.system_queries import SystemQueries
from common import utils

module_logger = BasicLogger.get_module_logger(module_path=__file__)

'''
    Speech Dispatcher is a Linux TTS abstraction layer. It allows for programs
    to interact with a speech engine using a consistent interface. It also allows
    the user to conveniently change which speech engine that they want to use system
    wide without having to go modify settings everywhere.
    
    Speech Dispatcher is long in the tooth, but still useful.
'''

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)
else:
    module_logger = BasicLogger.get_module_logger()


def getSpeechDSpeaker(test=False) -> Speaker:
    try:
        return Speaker('kodi', 'kodi')
    except:
        try:
            socket_path = os.path.expanduser('~/.speech-dispatcher/speechd.sock')
            so = Speaker('kodi', 'kodi', socket_path=socket_path)
            try:
                so.set_language(locale.getdefaultlocale()[0][:2])
            except (KeyError, IndexError):
                pass
            return so
        except:
            if not test:
                module_logger.error('Speech-Dispatcher: failed to create Speaker',
                                    hide_tb=True)
    return None


class SpeechDispatcherTTSBackend(ThreadedTTSBackend):
    """Supports The speech-dispatcher on linux"""

    backend_id = Backends.SPEECH_DISPATCHER_ID
    displayName = 'Speech Dispatcher'
    _class_name: str = None
    _logger: BasicLogger = None
    volumeExternalEndpoints = (0, 200)
    volumeStep = 5
    volumeSuffix = '%'
    pitchConstraints = (0, 0, 100, True)
    speedConstraints = (-100, 0, 100, True)
    volumeConstraints = (-100, 0, 100, True)

    settings = {
        'module': None,
        'pitch' : 0,
        'speed' : 0,
        'voice' : None,
        'volume': 100
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(type(self)._class_name)

        self.speechdObject: Speaker = None
        self.updateMessage: str | None = None

    def init(self):
        self.updateMessage = None
        self.connect()

    @staticmethod
    def isSupportedOnPlatform():
        return SystemQueries.isLinux()

    @staticmethod
    def isInstalled():
        installed = False
        if SpeechDispatcherTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def connect(self) -> None:
        self.speechdObject = getSpeechDSpeaker()
        if not self.speechdObject:
            return
        self.update()

    def threadedSay(self, text, interrupt=False):
        if not self.speechdObject:
            return
        try:
            self.speechdObject.speak(text)
        except SSIPCommunicationError:
            self.reconnect()
        except AttributeError:  # Happens on shutdown
            pass

    def stop(self):
        try:
            self.speechdObject.cancel()
        except SSIPCommunicationError:
            self.reconnect()
        except AttributeError:  # Happens on shutdown
            pass

    def reconnect(self):
        self.close()
        if self.active:
            self._logger.debug('Speech-Dispatcher reconnecting...')
            self.connect()

    def volumeUp(self) -> None:
        # Override because returning the message (which causes speech) causes the
        # backend to hang, not sure why... threading issue?
        self.updateMessage = ThreadedTTSBackend.volumeUp(self)

    def volumeDown(self) -> None:
        # Override because returning the message (which causes speech) causes the
        # backend to hang, not sure why... threading issue?
        self.updateMessage = ThreadedTTSBackend.volumeDown(self)

    def getUpdateMessage(self):
        msg = self.updateMessage
        self.updateMessage = None
        return msg

    def update(self):
        try:
            module = self.setting('module')
            if module:
                self.speechdObject.set_output_module(module)
            voice = self.setting('voice')
            if voice:
                self.speechdObject.set_language(self.getVoiceLanguage(voice))
                self.speechdObject.set_synthesis_voice(voice)
            self.speechdObject.set_rate(self.setting('speed'))
            self.speechdObject.set_pitch(self.setting('pitch'))
            vol = self.setting('volume')
            self.speechdObject.set_volume(vol - 100)  # Covert from % to (-100 to 100)
        except SSIPCommunicationError:
            self._logger.error('SpeechDispatcherTTSBackend.update()', hide_tb=True)
        msg = self.getUpdateMessage()
        if msg:
            self.say(msg, interrupt=True)

    def getVoiceLanguage(self, voice):
        res = None
        voices = self.speechdObject.list_synthesis_voices()
        for v in voices:
            if voice == v[0]:
                res = v[1]
                break
        return res

    @classmethod
    def settingList(cls, setting, *args):
        so = getSpeechDSpeaker()
        if setting == 'voice':
            module = cls.setting('module')
            if module:
                so.set_output_module(module)
            voices = so.list_synthesis_voices()
            return [(v[0], v[0]) for v in voices]
        elif setting == 'module':
            return [(m, m) for m in so.list_output_modules()]

    def close(self):
        if self.speechdObject:
            self.speechdObject.close()
        del self.speechdObject
        self.speechdObject = None

    @staticmethod
    def available():
        return bool(getSpeechDSpeaker(test=True))
