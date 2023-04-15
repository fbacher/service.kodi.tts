# -*- coding: utf-8 -*-

import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse, shutil, os

import textwrap


from common.constants import Constants
from common.setting_constants import Languages, Players, Genders, Misc
from common.logger import *
from common.messages import Messages
from common.settings import Settings
from common.system_queries import SystemQueries
from common import utils
from backends import asyncconnections
from backends.base import SimpleTTSBackendBase
from backends import audio


module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SpeechUtilComTTSBackend(SimpleTTSBackendBase):
    provider = 'speechutil'
    displayName = 'speechutil.com'
    ttsURL = 'http://speechutil.com/convert/wav?text={0}'
    headers = { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36' }
    canStreamWav = True


    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(self.__class__.__name__)  # type: BasicLogger

    def init(self):
        self.process = None

    def threadedSay(self,text):
        if not text: return
        sections = textwrap.wrap(text,100)
        for text in sections:
            outFile = self.player_handler.getOutFile(text, use_cache=False)
            if not self.runCommand(text,outFile): return
            self.player_handler.play()

    def runCommand(self,text,outFile):
        h = asyncconnections.Handler()
        o = urllib.request.build_opener(h)
        url = self.ttsURL.format(urllib.parse.quote(text))
        req = urllib.request.Request(url, headers=self.headers)
        try:
            resp = o.open(req)
        except (asyncconnections.StopRequestedException, asyncconnections.AbortRequestedException):
            return False
        except:
            self._logger.error('Failed to open speechutil.com TTS URL',hide_tb=True)
            return False

        with open(outFile,'wb') as out:
            shutil.copyfileobj(resp,out)
        return True

    def getWavStream(self,text):
        wav_path = os.path.join(utils.getTmpfs(),'speech.wav')
        if not self.runCommand(text,wav_path): return None
        return open(wav_path,'rb')

    def stop(self):
        asyncconnections.StopConnection()

    @staticmethod
    def available():
        return audio.WavAudioPlayerHandler.canPlay()
