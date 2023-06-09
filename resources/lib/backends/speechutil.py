# -*- coding: utf-8 -*-

import os
import shutil
import sys
import textwrap
import urllib.error
import urllib.error
import urllib.parse
import urllib.parse
import urllib.request
import urllib.request

from backends import asyncconnections, audio
# from backends.audio.player_handler import WavAudioPlayerHandler
from backends.base import SimpleTTSBackendBase
from common import utils
from common.logger import *
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SpeechUtilComTTSBackend(SimpleTTSBackendBase):
    """

    """
    backend_id = 'speechutil'
    displayName = 'speechutil.com'
    ttsURL = 'http://speechutil.com/convert/wav?text={0}'
    headers = { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36' }
    canStreamWav = True
    _class_name: str = None
    _logger: BasicLogger = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(type(self)._class_name)

    def init(self):
        self.process = None

    def threadedSay(self,text):
        if not text: return
        sections = textwrap.wrap(text,100)
        for text in sections:
            #  outFile = self.player_handler.getOutFile(text, use_cache=False)
            if not self.runCommand(text,outFile): return
            # self.player_handler.play()

    def runCommand(self,text,outFile):
        h = asyncconnections.Handler()
        o = urllib.request.build_opener(h)
        url = self.ttsURL.format(urllib.parse.quote(text))
        req = urllib.request.Request(url, headers=self.headers)
        try:
            resp = o.open(req)
        except AbortException:
            reraise(*sys.exc_info())
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
        # return WavAudioPlayerHandler.canPlay()
        pass
