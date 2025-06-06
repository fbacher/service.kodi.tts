# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys

from common import *

from backends import base
from backends.settings.setting_properties import SettingProp
from common.logger import *
from common.setting_constants import Mode, PlayerMode
from common.system_queries import SystemQueries

module_logger = BasicLogger.get_logger(__name__)


def getStartupInfo():
    if hasattr(subprocess, 'STARTUPINFO'):  # Windows
        startupinfo = subprocess.STARTUPINFO()
        try:
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # Suppress terminal
            # window
        except AbortException:
            reraise(*sys.exc_info())
        except:
            startupinfo.dwFlags |= 1
        return startupinfo

    return None


class CepstralTTSOEBackend(base.SimpleTTSBackend):
    engine_id = 'Cepstral_OE'
    displayName = 'Cepstral OpenElec'
    canStreamWav = True
    pitchConstraints = (-6, 0, 14, True)
    speedConstraints = (80, 170, 450, True)
    volumeConstraints = (12, 0, 12, True)

    settings = {
        SettingProp.PITCH,
        SettingProp.SPEED,
        'use_aoss',
        SettingProp.VOICE,
        SettingProp.VOLUME}

    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger: BasicLogger = None
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger

        self.process = None
        self.aplayProcess = None
        self.set_player_mode(PlayerMode.ENGINE_SPEAK)
        self.restartProcess()

    def runCommand(self, text, outFile):
        args = ['/lib/ld-linux.so.3', '--library-path', '/storage/music/callie/lib',
                '/storage/music/callie/bin/swift.bin', '-d',
                '/storage/music/callie/voices/Callie', '-o', outFile, text]
        subprocess.call(args)
        return True

    def runCommandAndPipe(self, text):
        args = ['/lib/ld-linux.so.3', '--library-path', '/storage/music/callie/lib',
                '/storage/music/callie/bin/swift.bin', '-d',
                '/storage/music/callie/voices/Callie', '-o', '-', text]
        self.process = subprocess.Popen(args, stdout=subprocess.PIPE, encoding='utf-8',
                                        universal_newlines=True)
        return self.process.stdout

    def runCommandAndSpeak(self, text):
        self.process.stdin.write(text + '\n\n')

    def restartProcess(self):
        self.stopProcess()
        args = ['/lib/ld-linux.so.3', '--library-path', '/storage/music/callie/lib',
                '/storage/music/callie/bin/swift.bin', '-d',
                '/storage/music/callie/voices/Callie', '-f', '-', '-o', '-']
        self.process = subprocess.Popen(args, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=(open(os.path.devnull, 'w')),
                                        universal_newlines=True, encoding='utf-8')
        self.aplayProcess = subprocess.Popen(['aplay', '-q'], stdin=self.process.stdout,
                                             stdout=(open(os.path.devnull, 'w')),
                                             stderr=subprocess.STDOUT,
                                             universal_newlines=True, encoding='utf-8')

    def stopProcess(self):
        if self.process:
            try:
                self.process.terminate()
            except AbortException:
                reraise(*sys.exc_info())
            except:
                pass
        if self.aplayProcess:
            try:
                self.aplayProcess.terminate()
            except AbortException:
                reraise(*sys.exc_info())
            except:
                pass

    #    def stop(self):
    #        if not self.process: return
    #        try:
    #            self.process.terminate()
    #        except:
    #            pass

    def stop(self):
        self.restartProcess()

    def close(self):
        self.stopProcess()

    @staticmethod
    def available():
        return True


class CepstralTTSBackend(base.SimpleTTSBackend):
    engine_id = 'Cepstral'
    displayName = 'Cepstral'
    canStreamWav = False
    settings = {SettingProp.VOICE : '',
                'use_aoss'        : False,
                SettingProp.SPEED : 170,
                SettingProp.VOLUME: 0,
                SettingProp.PITCH : 0

                }
    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger

        self.set_player_mode(PlayerMode.ENGINE_SPEAK)
        self.startupinfo = getStartupInfo()
        self.update()
        self.process = None
        self.restartProcess()

    @staticmethod
    def isSupportedOnPlatform():
        return (SystemQueries.isLinux() or SystemQueries.isWindows() or
                SystemQueries.isOSX())

    @staticmethod
    def isInstalled():
        installed = False
        if CepstralTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def restartProcess(self):
        self.stopProcess()
        args = ['swift']
        if self.useAOSS:
            args.insert(0, 'aoss')
        if self.voice:
            args.extend(('-n', self.voice))
        args.extend(('-p',
                     'audio/volume={0},speech/rate={1},speech/pitch/shift={2}'.format(
                         self.volume, self.rate, self.pitch)))
        args.extend(('-f', '-'))
        self.process = subprocess.Popen(args, startupinfo=self.startupinfo,
                                        stdin=subprocess.PIPE,
                                        stdout=(open(os.path.devnull, 'w')),
                                        stderr=subprocess.STDOUT,
                                        universal_newlines=True, encoding='utf-8')

    def stopProcess(self):
        if self.process:
            try:
                self.process.terminate()
            except AbortException:
                reraise(*sys.exc_info())
            except:
                pass

    def runCommandAndSpeak(self, text):
        self.process.stdin.write(text + '\n\n')

    def update(self):
        self.voice = self.setting(SettingProp.VOICE)
        self.rate = self.setting(SettingProp.SPEED)
        self.useAOSS = self.setting('use_aoss')
        if self.useAOSS and not SystemQueries.commandIsAvailable('aoss'):
            self._logger.info(
                'Cepstral: Use aoss is enabled, but aoss is not found. Disabling.')
            self.useAOSS = False
        volume = self.setting(SettingProp.VOLUME)
        self.volume = int(
            round(100 * (10 ** (volume / 20.0))))  # convert from dB to percent
        pitch = self.setting(SettingProp.PITCH)
        self.pitch = 0.4 + ((
                                        pitch + 6) / 20.0) * 2  # Convert from (-6 to
        # +14) value to (0.4 to 2.4)

    def stop(self):
        self.restartProcess()

    def close(self):
        self.stopProcess()

    @classmethod
    def getVoiceLines(cls):
        import re
        ret = []
        out = subprocess.check_output(['swift', '--voices'],
                                      startupinfo=getStartupInfo(),
                                      universal_newlines=True).splitlines()
        for l in reversed(out):
            if l.startswith(' ') or l.startswith('-'):
                break
            ret.append(re.split('\s+\|\s+', l.strip(), 6))
        return ret

    @classmethod
    def voices(cls):
        ret = []
        for v in cls.getVoiceLines():
            voice = v[0]
            ret.append((voice, voice))
        return ret

    @classmethod
    def settingList(cls, setting, *args):
        if setting == SettingProp.VOICE:
            return cls.voices()
        return None

    @staticmethod
    def available():
        try:
            subprocess.call(['swift', '-V'], startupinfo=getStartupInfo(),
                            stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT,
                            universal_newlines=True, encoding='utf-8')
        except (OSError, IOError):
            return False
        return True
