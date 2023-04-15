# -*- coding: utf-8 -*-
import sys, subprocess, os

from common.constants import Constants
from common.setting_constants import Languages, Players, Genders, Misc
from common.logger import *
from common.messages import Messages
from common.settings import Settings
from common.system_queries import SystemQueries
from common import utils

from .base import ThreadedTTSBackend


module_logger = BasicLogger.get_module_logger(module_path=__file__)


class OSXSayTTSBackend_Internal(ThreadedTTSBackend):
    provider = 'OSXSay'
    displayName = 'OSX Say (OSX Internal)'
    canStreamWav = True
    volumeConstraints = (0,100,100,True)
    speedConstraints = (80, 200, 450, True)

    volumeExternalEndpoints = (0,100)
    volumeStep = 5
    volumeSuffix = '%'
    voicesPath = os.path.join(Constants.PROFILE_PATH,'{0}.voices'.format(provider))
    settings = {
                'speed': 0,
                'voice': '',
                'volume': 100
                }

    #  def __new__(cls):
    #      try:
    #          import xbmc #analysis:ignore
    #          return super().__new__()
    #      except:
    #          pass
    #      return # OSXSayTTSBackend_SubProcess() #  TODO: does not exist!

    def __init__(self):
        super().__init__()
        from . import cocoapy
        self.cocoapy = cocoapy
        self.pool = cocoapy.ObjCClass('NSAutoreleasePool').alloc().init()
        self.synth = cocoapy.ObjCClass('NSSpeechSynthesizer').alloc().init()
        voices = self.longVoices()
        self.saveVoices(voices) #Save the voices to file, so we can get provide them for selection without initializing the synth again
        self.update()

    def threadedSay(self,text):
        if not text: return
        self.synth.startSpeakingString_(self.cocoapy.get_NSString(text))
        while self.synth.isSpeaking():
            utils.sleep(10)

    def getWavStream(self,text):
        wav_path = os.path.join(utils.getTmpfs(),'speech.wav')
        subprocess.call(['say', '-o', wav_path,
                         '--file-format','WAVE','--data-format','LEI16@22050',text],
                        universal_newlines=True)
        return open(wav_path,'rb')

    def isSpeaking(self):
        return self.synth.isSpeaking()

    def longVoices(self):
        vNSCFArray = self.synth.availableVoices()
        voices = [self.cocoapy.cfstring_to_string(
            vNSCFArray.objectAtIndex_(i,self.cocoapy.get_NSString('UTF8String')))
            for i in range(vNSCFArray.count())]
        return voices

    def update(self):
        self.voice = self.setting('voice')
        self.volume = self.setting('volume') / 100.0
        self.rate = self.setting('speed')
        if self.voice: self.synth.setVoice_(self.cocoapy.get_NSString(self.voice))
        if self.volume: self.synth.setVolume_(self.volume)
        if self.rate: self.synth.setRate_(self.rate)

    def stop(self):
        self.synth.stopSpeaking()

    def close(self):
        self.pool.release()

    @classmethod
    def settingList(cls,setting,*args):
        if setting == 'voice':
            lvoices = cls.loadVoices()
            if not lvoices: return None
            voices = [(v,v.rsplit('.',1)[-1]) for v in lvoices]
            return voices

    @classmethod
    def saveVoices(cls,voices):
        if not voices: return
        out = '\n'.join(voices)
        with open(cls.voicesPath,'w') as f: f.write(out)

    @classmethod
    def loadVoices(cls):
        if not os.path.exists(cls.voicesPath): return None
        with open(cls.voicesPath,'r') as f:
            return f.read().splitlines()

    @staticmethod
    def available():
        return sys.platform == 'darwin' and not SystemQueries.isATV2()

#OLD
class OSXSayTTSBackend(ThreadedTTSBackend):
    provider = 'OSXSay'
    displayName = 'OSX Say (OSX Internal)'
    canStreamWav = True

    def __init__(self):
        #util.LOG('OSXSay using subprocess method class')
        self.process = None
        ThreadedTTSBackend.__init__(self)

    @staticmethod
    def isSupportedOnPlatform():
        return SystemQueries.isOSX()

    @staticmethod
    def isInstalled():
        return OSXSayTTSBackend.isSupportedOnPlatform()

    def threadedSay(self,text):
        if not text: return
        self.process = subprocess.Popen(['say', text], universal_newlines=True)
        while self.process.poll() is None and self.active: utils.sleep(10)

    def getWavStream(self,text):
        wav_path = os.path.join(utils.getTmpfs(),'speech.wav')
        subprocess.call(['say', '-o', wav_path,
                         '--file-format','WAVE','--data-format','LEI16@22050',
                         text], universal_newlines=True)
        return open(wav_path,'rb')

    def isSpeaking(self):
        return (self.process and self.process.poll() is None) or ThreadedTTSBackend.isSpeaking(self)

    def stop(self):
        if not self.process: return
        try:
            self.process.terminate()
        except:
            pass

    @staticmethod
    def available():
        return sys.platform == 'darwin' and not SystemQueries.isATV2()
