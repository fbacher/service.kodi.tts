# -*- coding: utf-8 -*-
from . import base
import subprocess
import ctypes
import ctypes.util
import os
from lib import util


class ESpeakTTSBackend(base.SimpleTTSBackendBase):
    provider = 'eSpeak'
    displayName = 'eSpeak'
    speedConstraints = (80, 175, 450, True)
    pitchConstraints = (0, 50, 99, True)
    settings = {'voice': '',
                'speed': 0,
                'pitch': 0,
                'output_via_espeak': False,
                'player': None,
                'volume': 0,
                'pipe': False
                }
    voice_map = dict()

    def init(self):
        self.process = None
        self.update()

    def addCommonArgs(self, args, text):
        if self.voice:
            args.extend(
                ('-v', ESpeakTTSBackend.get_voice_id_for_name(self.voice)))
        if self.speed:
            args.extend(('-s', str(self.speed)))
        if self.pitch:
            args.extend(('-p', str(self.pitch)))
        if self.volume != 100:
            args.extend(('-a', str(self.volume)))
        args.append(text)

    def runCommand(self, text, outFile):
        util.VERBOSE_LOG('espeak.runCommand outFile: ' + outFile)
        args = ['espeak', '-w', outFile]
        self.addCommonArgs(args, text)
        try:
            rc = subprocess.call(args)
        except (Exception) as e:
            util.VERBOSE_LOG('espeak.runCommand Exception: ' + str(e))
        return True

    def runCommandAndSpeak(self, text):
        args = ['espeak']
        self.addCommonArgs(args, text)
        self.process = subprocess.Popen(args, universal_newlines=True)
        while self.process.poll() is None and self.active:
            util.sleep(10)

    def runCommandAndPipe(self, text):
        args = ['espeak', '--stdout']
        self.addCommonArgs(args, text)
        self.process = subprocess.Popen(args, stdout=subprocess.PIPE)
        return self.process.stdout

    def update(self):
        self.setPlayer(self.setting('player'))
        self.setMode(self.getMode())
        self.voice = self.setting('voice')
        self.speed = self.setting('speed')
        self.pitch = self.setting('pitch')
        volume = self.setting('volume')
        self.volume = int(round(100 * (10**(volume / 20.0)))
                          )  # convert from dB to percent

    def getMode(self):
        if self.setting('output_via_espeak'):
            return base.SimpleTTSBackendBase.ENGINESPEAK
        elif self.setting('pipe'):
            return base.SimpleTTSBackendBase.PIPE
        else:
            return base.SimpleTTSBackendBase.WAVOUT

    def stop(self):
        if not self.process:
            return
        try:
            self.process.terminate()
        except:
            pass

    @classmethod
    def settingList(cls, setting, *args):
        if setting == 'voice':
            import re
            ret = []
            out = subprocess.check_output(['espeak', '--voices'],
                                          universal_newlines=True).splitlines()
            out.pop(0)
            cls.voice_map = dict()
            for l in out:
                voice_properties = re.split('\s+', l.strip(), 5)
                voice_name = voice_properties[3]
                voice_file = voice_properties[4]
                ret.append((voice_file, voice_name))
                cls.voice_map[voice_name] = voice_file
            return ret
        return None

    @classmethod
    def get_voice_id_for_name(cls, name):
        if len(cls.voice_map) == 0:
            cls.settingList('voice')
        return cls.voice_map[name]

    @staticmethod
    def available():
        try:
            subprocess.run(['espeak', '--version'], stdout=(open(os.path.devnull, 'w')),
                           universal_newlines=True, stderr=subprocess.STDOUT)
        except:
            return False
        return True


class espeak_VOICE(ctypes.Structure):
    _fields_ = [
        ('name', ctypes.c_char_p),
        ('languages', ctypes.c_char_p),
        ('identifier', ctypes.c_char_p),
        ('gender', ctypes.c_byte),
        ('age', ctypes.c_byte),
        ('variant', ctypes.c_byte),
        ('xx1', ctypes.c_byte),
        ('score', ctypes.c_int),
        ('spare', ctypes.c_void_p),
    ]


######### BROKEN ctypes method ############
class ESpeakCtypesTTSBackend(base.TTSBackendBase):
    provider = 'eSpeak-ctypes'
    displayName = 'eSpeak (ctypes)'
    settings = {'voice': ''}
    broken = True
    _eSpeak = None

    @property
    def eSpeak(self):
        if ESpeakCtypesTTSBackend._eSpeak:
            return ESpeakCtypesTTSBackend._eSpeak
        libname = ctypes.util.find_library('espeak')
        ESpeakCtypesTTSBackend._eSpeak = ctypes.cdll.LoadLibrary(libname)
        ESpeakCtypesTTSBackend._eSpeak.espeak_Initialize(0, 0, None, 0)
        return ESpeakCtypesTTSBackend._eSpeak

    def __init__(self):
        self.voice = self.setting('voice')

    def say(self, text, interrupt=False):
        if not self.eSpeak:
            return
        if self.voice:
            self.eSpeak.espeak_SetVoiceByName(self.voice)
        if interrupt:
            self.eSpeak.espeak_Cancel()
        sb_text = ctypes.create_string_buffer(text)
        size = ctypes.sizeof(sb_text)
        self.eSpeak.espeak_Synth(sb_text, size, 0, 0, 0, 0x1000, None, None)

    def update(self):
        self.voice = self.setting('voice')

    def stop(self):
        if not self.eSpeak:
            return
        self.eSpeak.espeak_Cancel()

    def close(self):
        if not self.eSpeak:
            return
        # self.eSpeak.espeak_Terminate() #TODO: Removed because broke, uncomment if fixed
        # ctypes.cdll.LoadLibrary('libdl.so').dlclose(self.eSpeak._handle)
        # del self.eSpeak #TODO: Removed because broke, uncomment if fixed
        # self.eSpeak = None #TODO: Removed because broke, uncomment if fixed

    @staticmethod
    def available():
        return bool(ctypes.util.find_library('espeak'))

    @classmethod
    def settingList(cls, setting, *args):
        return None
        if setting == 'voice':
            if not ESpeakCtypesTTSBackend._eSpeak:
                return None
            voices = ESpeakCtypesTTSBackend._eSpeak.espeak_ListVoices(None)
            aespeak_VOICE = ctypes.POINTER(ctypes.POINTER(espeak_VOICE))
            pvoices = ctypes.cast(voices, aespeak_VOICE)
            voiceList = []
            index = 0
            while pvoices[index]:
                voiceList.append(os.path.basename(
                    pvoices[index].contents.identifier))
                index += 1
            return voiceList
        return None
