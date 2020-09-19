# -*- coding: utf-8 -*-

import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse,\
    shutil, os, subprocess, textwrap

import xbmc

from backends import base, audio
from common.logger import LazyLogger
from common.system_queries import SystemQueries
from common.old_logger import OldLogger
from common import utils

module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)


LANGUAGES = [    ('af', 'Afrikaans'),
                ('sq', 'Albanian'),
                ('ca', 'Catalan'),
                ('zh', 'Chinese (Mandarin)'),
                ('hr', 'Croatian'),
                ('cs', 'Czech'),
                ('da', 'Danish'),
                ('nl', 'Dutch'),
                ('en', 'English'),
                ('fi', 'Finnish'),
                ('fr', 'French'),
                ('de', 'German'),
                ('el', 'Greek'),
                ('ht', 'Haitian Creole'),
                ('hu', 'Hungarian'),
                ('is', 'Icelandic'),
                ('id', 'Indonesian'),
                ('it', 'Italian'),
                ('lv', 'Latvian'),
                ('mk', 'Macedonian'),
                ('no', 'Norwegian'),
                ('pl', 'Polish'),
                ('pt', 'Portuguese'),
                ('ro', 'Romanian'),
                ('ru', 'Russian'),
                ('sr', 'Serbian'),
                ('sk', 'Slovak'),
                ('sw', 'Swahili'),
                ('sv', 'Swedish'),
                ('tr', 'Turkish'),
                ('vi', 'Vietnamese'),
                ('cy', 'Welsh')
]

class GoogleTTSBackend(base.SimpleTTSBackendBase):
    provider = 'Google'
    displayName = 'Google'
    # ttsURL = 'http://translate.google.com/translate_tts?client=t&tl={0}&q={1}'
    ttsURL='https://translate.google.com/translate_tts?&q={1}&tl={0}&client=tw-ob'
    canStreamWav = SystemQueries.commandIsAvailable('mpg123')
    playerClass = audio.MP3AudioPlayerHandler
    settings = {
                'language': 'en',
                'pipe': False,
                'player': 'mpg123',
                'volume': 0
                }

    def init(self):
        self.process = None
        self.update()

    @staticmethod
    def isSupportedOnPlatform():
        return (SystemQueries.isLinux() or SystemQueries.isWindows() or
                SystemQueries.isOSX())

    @staticmethod
    def isInstalled():
        installed = False
        if GoogleTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def threadedSay(self,text):
        if not text: return
        sections = textwrap.wrap(text,100)
        if self.mode == self.PIPE:
            for text in sections:
                source = self.runCommandAndPipe(text)
                if not source: continue
                self.player_handler.pipeAudio(source)
        else:
            for text in sections:
                outFile = self.player_handler.getOutFile(text, use_cache=False)
                if not self.runCommand(text,outFile): return
                self.player_handler.play()

    def runCommand(self,text,outFile):
        url = self.ttsURL.format(self.language,urllib.parse.quote(text))
        LazyLogger.debug_verbose('Google url: ' + url)
        #

        # local IFS = +; /usr/bin/mplayer -ao alsa -really -quiet -noconsolecontrols "http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q=$*&tl=en";
        headers = {'Referer': 'http://translate.google.com',
                   'User-Agent': 'stagefright/1.2 (Linux;Android 5.0)'
                   }
        req = urllib.request.Request(url, headers=headers)
        try:
            resp = urllib.request.urlopen(req)
        except:
            OldLogger.ERROR('Failed to open Google TTS URL',hide_tb=True)
            return False

        with open(outFile,'wb') as out:
            shutil.copyfileobj(resp,out)
        return True

    def runCommandAndPipe(self,text):
        url = self.ttsURL.format(self.language,urllib.parse.quote(text))
        LazyLogger.debug_verbose('Google url: ' + url)
        #req = urllib.request.Request(url) #, headers={ 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36' })
        headers = {'Referer': 'http://translate.google.com/',
                   'User-Agent': 'stagefright/1.2 (Linux;Android 5.0)'
                   }
        req = urllib.request.Request(url, headers=headers)
        try:
            resp = urllib.request.urlopen(req)
            LazyLogger.debug_verbose('url: ' + req.get_full_url())
            LazyLogger.debug_verbose('headers: ' + str(req.header_items()))
        except:
            OldLogger.ERROR('Failed to open Google TTS URL',hide_tb=True)
            return None
        return resp

    def getWavStream(self,text):

        wav_path = os.path.join(utils.getTmpfs(),'speech.wav')
        mp3_path = os.path.join(utils.getTmpfs(),'speech.mp3')
        self.runCommand(text,mp3_path)
        self.process = subprocess.Popen(['mpg123','-w',wav_path,mp3_path],
                                        stdout=(open(os.path.devnull, 'w')),
                                        stderr=subprocess.STDOUT,
                                        universal_newlines=True)
        while self.process.poll() is None and self.active: xbmc.sleep(10)
        os.remove(mp3_path)
        return open(wav_path,'rb')

    def update(self):
        self.language = self.setting('language')
        self.setPlayer(self.setting('player'))
        self.setVolume(self.setting('volume'))
        self.setMode(self.getMode())

    def getMode(self):
        if self.setting('pipe'):
            return base.SimpleTTSBackendBase.PIPE
        else:
            return base.SimpleTTSBackendBase.WAVOUT

    def stop(self):
        if not self.process: return
        try:
            self.process.terminate()
        except:
            pass

    @classmethod
    def settingList(cls,setting,*args):
        if setting == 'language':
            return LANGUAGES
        return None

    @staticmethod
    def available():
        return audio.MP3AudioPlayerHandler.canPlay()
