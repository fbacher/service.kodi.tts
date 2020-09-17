# -*- coding: utf-8 -*-
import os, subprocess
from . import base
from lib.cache.voicecache import VoiceCache
from lib import util

class Pico2WaveTTSBackend(base.SimpleTTSBackendBase):
    provider = 'pico2wave'
    displayName = 'pico2wave'
    speedConstraints = (20,100,200,True)
    settings = {'language': '',
                    'speed': 0,
                    'player': None,
                    'volume': 0
    }

    def __init__(self):
        super().__init__()
        self.stop_processing = False

    def init(self):
        self.setMode(base.SimpleTTSBackendBase.WAVOUT)
        self.update()

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
            util.VERBOSE_LOG('pico2wave.runCommand text: ' + text_to_voice +
                             ' language: ' + self.language)
            args = ['pico2wave']
            if self.language:
                args.extend(['-l', self.language])
            args.extend(['-w', '{0}'.format(outFile), '{0}'.format(text_to_voice)])
            try:
                if not self.stop_processing:
                    subprocess.call(args, universal_newlines=True)
            except Exception as e:
                util.ERROR('Failed to download voice file: {}'.format(str(e)))
                try:
                    os.remove(outFile)
                except Exception as e2:
                    pass
                return False

            return True



        if self.stop_processing:
            util.VERBOSE_LOG('runCommand stop_processing')
            return False

        return True

    def update(self):
        self.language = self.setting('language')
        self.setPlayer(self.setting('player'))
        self.setSpeed(self.setting('speed'))
        self.setVolume(self.setting('volume'))

    @classmethod
    def settingList(cls,setting,*args):
        if setting == 'language':
            try:
                out = subprocess.check_output(['pico2wave','-l','NONE','-w','/dev/null','X'],
                                              stderr=subprocess.STDOUT,
                                              universal_newlines=True)
            except subprocess.CalledProcessError as e:
                out = e.output
            if not 'languages:' in out: return None

        return [ (v,v) for v in out.split('languages:',1)[-1].split('\n\n')[0].strip('\n').split('\n')]

    @staticmethod
    def available():
        try:
            subprocess.call(['pico2wave', '--help'],  universal_newlines=True,
                            stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        except (OSError, IOError):
            return False
        return True