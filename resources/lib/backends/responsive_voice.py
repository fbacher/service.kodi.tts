# -*- coding: utf-8 -*-

import urllib.request
import urllib.parse
import urllib.error
import urllib.request
import urllib.error
import urllib.parse
import re
import shutil
import os
import subprocess
import tempfile

from lib.backends import base, audio
from lib.cache.voicecache import VoiceCache
from lib.responsive_voice import ResponsiveVoice, get_voices
from lib import util
import textwrap


class ResponsiveVoiceTTSBackend(base.SimpleTTSBackendBase):
    # Only returns .mp3 files

    provider = 'ResponsiveVoice'
    displayName = 'ResponsiveVoice'
    canStreamWav = util.commandIsAvailable('mpg123')
    playerClass = audio.MP3AudioPlayerHandler
    settings = {
        'language': 'en_US',
        'player': 'mpg123',
        'volume': 0,
        'pipe': False
    }

    def __init__(self):
        super().__init__()
        self.process = None
        self.pitch = None
        self.language = None
        self.volume = None
        self.gender = None
        self.speed = None
        self.update()
        self.stop_processing = False
        self.api_key = None

    def init(self):
        pass
        # self.update()

    def threadedSay(self, text):
        util.VERBOSE_LOG('threadedSay {}'.format(text))
        self.stop_processing = False
        if not text:
            return
        if self.mode == self.PIPE:
            source = self.runCommandAndPipe(text)
            if not self.stop_processing:
                self.player.pipeAudio(source)
        else:
            outFile = self.player.getOutFile(text)
            if not self.runCommand(text, outFile):
                return
            if not self.stop_processing:
                self.player.play()
            else:
                util.VERBOSE_LOG('stop_processing')

    def runCommand(self, text_to_voice, outFile):
        voiced_text = None
        if VoiceCache.is_cache_sound_files():

            # TODO: Remove HACK

            _, extension = os.path.splitext(outFile)
            self.player.outFile = VoiceCache.get_path_to_voice_file(
                text_to_voice, extension)
            outFile = self.player.outFile

            voiced_text = VoiceCache.get_sound_file(text_to_voice, extension)

        if voiced_text is None:
            util.VERBOSE_LOG('ResponsiveVoice.runCommand text: ' + text_to_voice +
                             ' language: ' + self.language)
            # self.speed = None
            # self.pitch = None
            engine = ResponsiveVoice(key=self.api_key, lang=self.language,
                                     gender=self.gender,
                                     pitch=self.pitch, rate=self.speed,
                                     vol=self.volume)
            # voice_name=self.voice, service="")
            try:
                if not self.stop_processing:
                    engine.get_mp3(text_to_voice, mp3_file=outFile)
            except Exception as e:
                util.ERROR('Failed to download voice file: {}'.format(str(e)))
                try:
                    os.remove(outFile)
                except Exception as e2:
                    pass
                return False

        if self.stop_processing:
            util.VERBOSE_LOG('runCommand stop_processing')
            return False

        return True

    def getWavStream(self, text_to_voice):
        wav_path = os.path.join(util.getTmpfs(), 'speech.wav')
        mp3_path = os.path.join(util.getTmpfs(), 'speech.mp3')
        self.runCommand(text_to_voice, mp3_path)
        self.process = subprocess.Popen(['mpg123', '-w', wav_path, mp3_path],
                                        stdout=(open(os.path.devnull, 'w')),
                                        stderr=subprocess.STDOUT,
                                        universal_newlines=True)
        while self.process.poll() is None and self.active:
            util.sleep(10)
        self.process = None

        os.remove(mp3_path)
        return open(wav_path, 'rb')

    def update(self):
        self.language = self.setting('language')
        self.setPlayer(self.setting('player'))
        self.setVolume(self.setting('volume'))
        self.setPitch(self.setting('pitch'))
        self.setSpeed(self.setting('speed'))
        # self.setVoice(self.setting('voice'))
        self.setGender(self.setting('gender'))
        self.setMode(self.getMode())
        self.process = None
        self.stop_processing = False
        self.api_key = util.getSetting('api_key.ResponsiveVoice', None)

    def getMode(self):
        if self.setting('pipe'):
            return base.SimpleTTSBackendBase.PIPE
        else:
            return base.SimpleTTSBackendBase.WAVOUT

    def stop(self):
        util.VERBOSE_LOG('stop')
        self.stop_processing = True
        if not self.process:
            return
        try:
            util.VERBOSE_LOG('terminate')
            self.process.terminate() # Could use self.process.kill()
        except:
            pass

    @classmethod
    def settingList(cls, setting, *args):
        if setting == 'language':
            voices = get_voices()
            langs = set()
            for voice in voices:
                voice_entry = voices[voice]
                langs.add(voice_entry().lang)

            sorted_langs = sorted(langs)
            languages = []
            # Returned value expected to be list(ID, display_value)
            for language in sorted_langs:
                languages.append((language, language))

            return languages
        #
        # Underlying lib does not specify any voice names
        #
        # if setting == 'voice':
        #    voices = get_voices()
        #    voices_for_language = []
        #    language = util.getSetting('language.ResponsiveVoice', None)
        #    language = re.sub(r'[^a-zA-Z]', '', language)
        #    for voice in voices:
        #        voice_entry = voices[voice]()
        #        lang = re.sub(r'[^a-zA-Z]', '', voice_entry.lang)
        #        if language.casefold() == lang.casefold():
        #            voices_for_language.append(voice_entry.name)

        #    sorted_voices = sorted(voices_for_language)
        #    returned_voices = []
        #    # Returned value expected to be list(ID, display_value)
        #    for voice_name in sorted_voices:
        #        returned_voices.append((voice_name, voice_name))

        #    return returned_voices
        # return None

    # def setPlayer(self, setting('player'))

    def setVolume(self, volume):
        # Range -12 .. +12, 0 default
        # API 0.1 .. 2.0. 1.0 default
        # self.volume = float(volume) / 12.0 + 1.0
        pass

    def setPitch(self, pitch):
        # Range 0 .. 99, 50 default
        # API 0.1 .. 2.0. 1.0 default
        self.pitch = float(pitch) / 100.0
        pass

    def setSpeed(self, speed):
        # Range 0 .. 99, 50 default
        # API 0.1 .. 2.0. 1.0 default
        self.speed = float(speed) / 100.0
        pass

    def setGender(self, gender_enum):
        if gender_enum == 0:
            self.gender = 'male'
        else:
            self.gender = 'female'

    # All voices are empty strings
    # def setVoice(self, voice):
    #    self.voice = voice

    @staticmethod
    def available():
        return audio.MP3AudioPlayerHandler.canPlay()
