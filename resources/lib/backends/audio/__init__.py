# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import wave
import hashlib
import threading
import shutil
import errno
from typing import Any, cast, List, Union, Type

from cache.voicecache import VoiceCache
from common.constants import Constants
from common.settings import Settings
from common.setting_constants import Players
from common.logger import LazyLogger
from common.old_logger import OldLogger
from common import utils

try:
    import xbmc
except:
    xbmc = None

module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)
PLAYSFX_HAS_USECACHED = False

try:
    voidWav = os.path.join(Constants.ADDON_DIRECTORY, 'resources', 'wavs',
                           'void.wav')
    xbmc.playSFX(voidWav, False)
    PLAYSFX_HAS_USECACHED = True
except:
    pass


def check_snd_bm2835():
    try:
        return 'snd_bcm2835' in subprocess.check_output(['lsmod'],
                                                        universal_newlines=True)
    except:
        module_logger.error('check_snd_bm2835(): lsmod filed', hide_tb=True)
    return False


def load_snd_bm2835():
    try:
        if not xbmc or not xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi'):
            return
    except:  # Handles the case where there is an xbmc module installed system wide and we're not running xbmc
        return
    if check_snd_bm2835():
        return
    import getpass
    # TODO: Maybe use util.raspberryPiDistro() to confirm distro
    if getpass.getuser() == 'root':
        module_logger.info(
            'OpenElec on RPi detected - loading snd_bm2835 module...')
        module_logger.info(os.system('modprobe snd-bcm2835')
                      and 'Load snd_bm2835: FAILED' or 'Load snd_bm2835: SUCCESS')
        # subprocess.call(['modprobe','snd-bm2835']) #doesn't work on OpenElec
        # (only tested) - can't find module
    elif getpass.getuser() == 'pi':
        module_logger.info('RaspBMC detected - loading snd_bm2835 module...')
        # Will just fail if sudo needs a password
        module_logger.info(os.system('sudo -n modprobe snd-bcm2835')
                      and 'Load snd_bm2835: FAILED' or 'Load snd_bm2835: SUCCESS')
    else:
        module_logger.info(
            'UNKNOWN Raspberry Pi - maybe loading snd_bm2835 module...')
        # Will just fail if sudo needs a password
        module_logger.info(os.system('sudo -n modprobe snd-bcm2835')
                      and 'Load snd_bm2835: FAILED' or 'Load snd_bm2835: SUCCESS')


class AudioPlayer:
    ID = Players.NONE
    # name = ''

    _advanced = False
    types = ('wav',)
    _logger: LazyLogger = None

    def __init__(self):
        cls = type(self)
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)

    def canSetSpeed(self): return False

    def setSpeed(self, speed): pass

    def canSetPitch(self): return False

    def setPitch(self, pitch): pass

    def canSetVolume(self): return False

    def setVolume(self, volume): pass

    def canSetPipe(self): return False

    def pipe(self, source): pass

    def play(self, path): pass

    def isPlaying(self): return False

    def stop(self): pass

    def close(self): pass

    @staticmethod
    def available(ext=None): return False

    @classmethod
    def is_builtin(cls):
        #
        # Is this Audio Player built-into the voice engine (i.e. espeak).
        #
        return False


class PlaySFXAudioPlayer(AudioPlayer):
    ID = Players.SFX
    # name = 'XBMC PlaySFX'
    _logger: LazyLogger = None

    def __init__(self):
        super().__init__()
        cls = type(self)
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)

        self._isPlaying = False
        self.event = threading.Event()
        self.event.clear()

    def doPlaySFX(self, path):
        xbmc.playSFX(path, False)

    def play(self, path):
        if not os.path.exists(path):
            type(self)._logger.info('playSFXHandler.play() - Missing wav file')
            return
        self._isPlaying = True
        self.doPlaySFX(path)
        f = wave.open(path, 'r')
        frames = f.getnframes()
        rate = f.getframerate()
        f.close()
        duration = frames / float(rate)
        self.event.clear()
        self.event.wait(duration)
        self._isPlaying = False

    def isPlaying(self):
        return self._isPlaying

    def stop(self):
        self.event.set()
        xbmc.stopSFX()

    def close(self):
        self.stop()

    @staticmethod
    def available(ext=None):
        return xbmc and hasattr(xbmc, 'stopSFX') and PLAYSFX_HAS_USECACHED


class WindowsAudioPlayer(AudioPlayer):
    ID = Players.WINDOWS
    # name = 'Windows Internal'
    types = ('wav', 'mp3')
    _logger: LazyLogger = None

    @classmethod
    def init_class(cls):
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)

    def __init__(self, *args, **kwargs):
        super().__init__()

        from . import winplay
        self._player = winplay
        self.audio = None
        self.event = threading.Event()
        self.event.clear()

    def play(self, path):
        if not os.path.exists(path):
            type(self)._logger.info('WindowsAudioPlayer.play() - Missing wav file')
            return
        self.audio = self._player.load(path)
        self.audio.play()
        self.event.clear()
        self.event.wait(self.audio.milliseconds() / 1000.0)
        if self.event.isSet():
            self.audio.stop()
        while self.audio.isplaying():
            utils.sleep(10)
        self.audio = None

    def isPlaying(self):
        return not self.event.isSet()

    def stop(self):
        self.event.set()

    def close(self):
        self.stop()

    @staticmethod
    def available(ext=None):
        if not sys.platform.startswith('win'):
            return False
        try:
            from . import winplay  # @analysis:ignore
            return True
        except:
            WindowsAudioPlayer._logger.error('winplay import failed')
        return False


WindowsAudioPlayer.init_class()


class SubprocessAudioPlayer(AudioPlayer):
    _availableArgs = None
    _playArgs = None
    _speedArgs = None
    _speedMultiplier = 1
    _volumeArgs = None
    _pipeArgs = None
    kill = False

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger
        self._wavProcess = None
        self.speed = 0
        self.volume = None
        self.active = True

    def speedArg(self, speed):
        return str(speed * self._speedMultiplier)

    def baseArgs(self, path):
        args = []
        args.extend(self._playArgs)
        args[args.index(None)] = path
        return args

    def playArgs(self, path):
        base_args = self.baseArgs(path)
        self._logger.debug_verbose('args: {}'.format(' '.join(base_args)))
        return base_args

    def get_pipe_args(self):
        base_args = self._pipeArgs
        return base_args

    def canSetPipe(self):
        return bool(self._pipeArgs)

    def pipe(self, source):
        pipe_args = self.get_pipe_args()
        self._logger.debug_verbose('pipeArgs: {}'
                                   .format(' '.join(pipe_args)))

        with subprocess.Popen(pipe_args, stdin=subprocess.PIPE,
                              stdout=(
                                  open(os.path.devnull, 'w')),
                              stderr=subprocess.STDOUT) as self._wavProcess:
            try:
                shutil.copyfileobj(source, self._wavProcess.stdin)
            except IOError as e:
                if e.errno != errno.EPIPE:
                    self._logger.ERROR('Error piping audio', hide_tb=True)
            except:
                self._logger.ERROR('Error piping audio', hide_tb=True)

            finally:
                source.close()

        self._wavProcess = None

    def setSpeed(self, speed):
        self.speed = speed

    def setVolume(self, volume):
        self.volume = volume

    def play(self, path):
        args = self.playArgs(path)
        self._logger.debug_verbose('args: {}'.format(' '.join(args)))
        with subprocess.Popen(args, stdout=(open(os.path.devnull, 'w')),
                              stderr=subprocess.STDOUT) as self._wavProcess:
            pass

        self._wavProcess = None

    def isPlaying(self):
        return self._wavProcess and self._wavProcess.poll() is None

    def stop(self):
        if not self._wavProcess or self._wavProcess.poll():
            return
        try:
            if self.kill:
                self._wavProcess.kill()
            else:
                self._wavProcess.terminate()
        except:
            pass
        finally:
            self._wavProcess = None

    def close(self):
        self.active = False
        if not self._wavProcess or self._wavProcess.poll():
            return
        try:
            self._wavProcess.kill()
        except:
            pass
        finally:
            self._wavProcess = None

    @classmethod
    def available(cls, ext=None):
        try:
            subprocess.call(cls._availableArgs, stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT, universal_newlines=True)
        except:
            return False
        return True


class AplayAudioPlayer(SubprocessAudioPlayer):
    #
    # ALSA player. amixer could be used for volume, etc.
    #
    ID = Players.APLAY
    # name = 'aplay'
    _availableArgs = ('aplay', '--version')
    _playArgs = ('aplay', '-q', None)
    _pipeArgs = ('aplay', '-q')
    kill = True

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger

    def canSetPipe(self):  # Input and output supported
        return True


class PaplayAudioPlayer(SubprocessAudioPlayer):
    #
    # Pulse Audio player
    #
    # Has ability to play on remote server
    #
    ID = Players.PAPLAY
    # name = 'paplay'
    _availableArgs = ('paplay', '--version')
    _playArgs = ('paplay', None)
    _pipeArgs = ('paplay',)
    _volumeArgs = ('--volume', None)

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger

    def playArgs(self, path):
        args = self.baseArgs(path)
        if self.volume:
            args.extend(self._volumeArgs)
            # Convert dB to paplay value
            args[args.index(None)] = str(
                int(65536 * (10**(self.volume / 20.0))))
            self._logger.debug_verbose('args: {}'.format(' '.join(args)))
        return args

    def canSetVolume(self):
        return True


class AfplayPlayer(SubprocessAudioPlayer):  # OSX
    ID = Players.AFPLAY
    # name = 'afplay'
    _availableArgs = ('afplay', '-h')
    _playArgs = ('afplay', None)
    _speedArgs = ('-r', None)  # usable values 0.4 to 3.0
    # 0 (silent) 1.0 (normal/default) 255 (very loud) db
    _volumeArgs = ('-v', None)
    kill = True
    types = ('wav', 'mp3')

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger

    def setVolume(self, volume):
        self.volume = min(int(100 * (10**(volume / 20.0))),
                          100)  # Convert dB to percent

    def setSpeed(self, speed):
        self.speed = speed * 0.01

    def playArgs(self, path):
        args = self.baseArgs(path)
        if self.volume:
            args.extend(self._volumeArgs)
            args[args.index(None)] = str(self.volume)
        if self.speed:
            args.extend(self._speedArgs)
            args[args.index(None)] = str(self.speed)
            self._logger.debug_verbose('args: {}'.format(' '.join(args)))
        return args

    def canSetSpeed(self):
        return True

    def canSetVolume(self):
        return True


class SOXAudioPlayer(SubprocessAudioPlayer):
    ID = Players.SOX
    # name = 'SOX'
    _availableArgs = ('sox', '--version')
    _playArgs = ('play', '-q', None)
    _pipeArgs = ('play', '-q', '-')
    _speedArgs = ('tempo', '-s', None)
    _speedMultiplier = 0.01
    _volumeArgs = ('vol', None, 'dB')
    kill = True
    types = ('wav', 'mp3')

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger

    def playArgs(self, path):
        args = self.baseArgs(path)
        if self.volume:
            args.extend(self._volumeArgs)
            args[args.index(None)] = str(self.volume)
        if self.speed:
            args.extend(self._speedArgs)
            args[args.index(None)] = self.speedArg(self.speed)
        self._logger.debug_verbose('args: {}'.format(' '.join(args)))
        return args

    def canSetVolume(self):
        return True

    def canSetPitch(self):  # Settings implies false, but need to test
        return True

    def canSetPipe(self):
        return True

    @classmethod
    def available(cls, ext=None):
        try:
            if ext == 'mp3':
                if 'mp3' not in subprocess.check_output(['sox', '--help'],
                                                        universal_newlines=True):
                    return False
            else:
                subprocess.call(cls._availableArgs, stdout=(open(os.path.devnull, 'w')),
                                stderr=subprocess.STDOUT, universal_newlines=True)
        except:
            return False
        return True


class MPlayerAudioPlayer(SubprocessAudioPlayer):
    ID = Players.MPLAYER
    # name = 'MPlayer'
    # MPlayer supports -idle and -slave which keeps player from exiting
    # after files played. When in slave mode, commands are read from stdin.

    _availableArgs = ('mplayer', '--help')
    _playArgs = ('mplayer', '-really-quiet', None)
    _pipeArgs = ('mplayer', '-', '-really-quiet', '-cache', '8192')
    _speedArgs = 'scaletempo=scale={0}:speed=none'
    #  _speedMultiplier = 0.01
    _speedMultiplier = 1
    _volumeArgs = 'volume={0}'  # Volume in db -200db .. +40db Default 0
    types = ('wav', 'mp3')

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger

    def playArgs(self, path):
        args = self.baseArgs(path)
        if self.speed or self.volume:
            args.append('-af')
            filters = []
            if self.speed:
                filters.append(self._speedArgs.format(
                    self.speedArg(self.speed)))
            if self.volume is not None:
                filters.append(self._volumeArgs.format(self.volume))
            args.append(','.join(filters))
            self._logger.debug_verbose('args: {}'.format(' '.join(args)))
        return args

    def get_pipe_args(self):
        args = []
        args.extend(self._pipeArgs)
        if self.speed or self.volume:
            args.append('-af')
            filters = []
            if self.speed:
                filters.append(self._speedArgs.format(
                    self.speedArg(self.speed)))
            if self.volume is not None:
                filters.append(self._volumeArgs.format(self.volume))
            args.append(','.join(filters))
            self._logger.debug_verbose('args: {}'.format(' '.join(args)))
        return args

    def canSetSpeed(self):
        return True

    def canSetVolume(self):
        return True

    def canSetPitch(self):
        return True

    def canSetPipe(self):
        return True


class Mpg123AudioPlayer(SubprocessAudioPlayer):
    ID = Players.MPG123
    # name = 'mpg123'
    _availableArgs = ('mpg123', '--version')
    _playArgs = ('mpg123', '-q', None)
    _pipeArgs = ('mpg123', '-q', '-')
    types = ('mp3',)

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger

    def canSetVolume(self):  # (1-100)
        return False

    def canSetPitch(self):  # Depends upon hardware used.
        return False

    def canSetPipe(self):  # Can read to/from pipe
        return True


class Mpg321AudioPlayer(SubprocessAudioPlayer):
    ID = Players.MPG321
    # name = 'mpg321'
    _availableArgs = ('mpg321', '--version')
    _playArgs = ('mpg321', '-q', None)
    _pipeArgs = ('mpg321', '-q', '-')
    types = ('mp3',)

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger

    def canSetVolume(self):
        return True

    def canSetPitch(self):
        return False

    def canSetPipe(self):  # Can read/write to pipe
        return True


class Mpg321OEPiAudioPlayer(SubprocessAudioPlayer):
    #
    #  Plays using ALSA
    #
    ID = Players.MPG321_OE_PI
    # name = 'mpg321 OE Pi'

    types = ('mp3',)

    def __init__(self):
        super().__init__()
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger
        self._wavProcess = None
        try:
            import OEPiExtras
            OEPiExtras.init()
            self.env = OEPiExtras.getEnvironment()
            self.active = True
        except ImportError:
            self._logger.debug('Could not import OEPiExtras')

    def canSetVolume(self):
        return True

    def canSetPitch(self):  # Settings implies false, but need to test
        return False

    def canSetPipe(self):
        return True

    def pipe(self, source):  # Plays using ALSA
        self._wavProcess = subprocess.Popen('mpg321 - --wav - | aplay',
                                            stdin=subprocess.PIPE,
                                            stdout=(
                                                open(os.path.devnull, 'w')),
                                            stderr=subprocess.STDOUT,
                                            env=self.env, shell=True,
                                            universal_newlines=True)
        try:
            shutil.copyfileobj(source, self._wavProcess.stdin)
        except IOError as e:
            if e.errno != errno.EPIPE:
                module_logger.ERROR('Error piping audio', hide_tb=True)
        except:
            module_logger.ERROR('Error piping audio', hide_tb=True)
        source.close()
        self._wavProcess.stdin.close()
        while self._wavProcess.poll() is None and self.active:
            utils.sleep(10)

    def play(self, path):  # Plays using ALSA
        self._wavProcess = subprocess.Popen('mpg321 --wav - "{0}" | aplay'.format(path),
                                            stdout=(
                                                open(os.path.devnull, 'w')),
                                            stderr=subprocess.STDOUT, env=self.env,
                                            shell=True, universal_newlines=True)

    @classmethod
    def available(cls, ext=None):
        try:
            import OEPiExtras  # analysis:ignore
        except:
            return False
        return True


class PlayerHandlerType:
    ID: None
    _advanced = None


class BasePlayerHandler(PlayerHandlerType):
    def __init__(self):
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger
        self.availablePlayers = None

    @classmethod
    def getAvailablePlayers(cls, include_builtin=True) -> List[Type[PlayerHandlerType]]:
        return []

    @classmethod
    def set_player(cls, player_id):
        return None

    def setSpeed(self, speed): pass

    def setVolume(self, speed): pass

    def player(self): return None

    def canSetPipe(self): return False

    def pipeAudio(self, source): pass

    def getOutFile(self, text, sound_file_type=None, use_cache=False): raise Exception(
        'Not Implemented')

    def play(self): raise Exception('Not Implemented')

    def isPlaying(self): raise Exception('Not Implemented')

    def stop(self): raise Exception('Not Implemented')

    def close(self): raise Exception('Not Implemented')

    def setOutDir(self):
        tmpfs = utils.getTmpfs()
        if Settings.getSetting(Settings.USE_TEMPFS, True) and tmpfs:
            self._logger.debug_extra_verbose(
                'Using tmpfs at: {0}'.format(tmpfs))
            self.outDir = os.path.join(tmpfs, 'kodi_speech')
        else:
            self.outDir = os.path.join(Constants.PROFILE_PATH, 'kodi_speech')
        if not os.path.exists(self.outDir):
            os.makedirs(self.outDir)


class BuiltInAudioPlayer(AudioPlayer):
    ID = Players.INTERNAL

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: module_logger

        self.volume_configurable = True
        self.pipe_configurable = True
        self.speed_configurable = True
        self.pitch_configurable = True

        types = ('mp3', 'wav')

    def set_speed_configurable(self, configurable):
        self.speed_configurable = configurable

    def canSetSpeed(self):
        return self.speed_configurable

    def set_pitch_configurable(self, configurable):
        self.pitch_configurable = configurable

    def canSetPitch(self):
        return self.pitch_configurable

    def set_volume_configurable(self, configurable):
        self.volume_configurable = configurable

    def canSetVolume(self):
        return self.volume_configurable

    def set_pipe_configurable(self, configurable):
        self.pipe_configurable = configurable

    def canSetPipe(self):
        return self.pipe_configurable

    @staticmethod
    def available(ext=None):
        return True

    @classmethod
    def is_builtin(cls):
        #
        # Is this Audio Player built-into the voice engine (i.e. espeak).
        #
        return True


class WavAudioPlayerHandler(BasePlayerHandler):
    players = (BuiltInAudioPlayer, PlaySFXAudioPlayer, WindowsAudioPlayer,
               AfplayPlayer, SOXAudioPlayer,
               PaplayAudioPlayer, AplayAudioPlayer, MPlayerAudioPlayer
               )
    _logger: LazyLogger = None

    def __init__(self, preferred=None, advanced=False):
        super().__init__()
        cls = type(self)
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)
        self.preferred = None
        self.advanced = advanced
        self.sound_file_type = '.wav'
        self.setOutDir()

        # TODO: Don't like outFileBase

        self.outFileBase = os.path.join(self.outDir, 'speech{}.wav')

        # TODO: Remove the 'speech' prefix

        self.outFile = os.path.join(self.outDir, 'speech.wav')
        self._player = AudioPlayer()
        self.hasAdvancedPlayer = False
        self._getAvailablePlayers(include_builtin=True)
        self.setPlayer(preferred, advanced)

    def get_player(self, ID) -> Union[Type[AudioPlayer], None]:
        for i in self.availablePlayers:
            if i.ID == ID:
                return i
        return None

    def player(self) -> Union[Type[AudioPlayer], None]:
        return self._player and self._player.ID or None

    def canSetPipe(self):
        return self._player.canSetPipe()

    def pipeAudio(self, source):
        return self._player.pipe(source)

    def playerAvailable(self):
        return bool(self.availablePlayers)

    def _getAvailablePlayers(self, include_builtin=True):
        self.availablePlayers = type(self).getAvailablePlayers(
            include_builtin=include_builtin)
        for p in self.availablePlayers:
            if p._advanced:
                break
                # TODO: Delete, or move this statement (from original)
                self.hasAdvancedPlayer = True

    def setPlayer(self, preferred=None, advanced=None):
        if preferred == self._player.ID or preferred == self.preferred:
            return self._player
        self.preferred = preferred
        if advanced is None:
            advanced = self.advanced
        old = self._player
        player = None
        if preferred:
            player = self.get_player(preferred)
        if player:
            self._player: AudioPlayer = player()
        elif advanced and self.hasAdvancedPlayer:
            for p in self.availablePlayers:
                if p._advanced:
                    self._player = p()
                    break
        elif self.availablePlayers:
            self._player = self.availablePlayers[0]()
        else:
            self._player = AudioPlayer()

        if self._player and old.ID != self._player:
            type(self)._logger.info('Player: %s' % self._player.ID)
        if not self._player.ID == Players.SFX:
            load_snd_bm2835()  # For Raspberry Pi
        return self._player

    def _deleteOutFile(self):
        if os.path.exists(self.outFile):
            os.remove(self.outFile)

    def getOutFile(self, text, sound_file_type=None, use_cache=False):
        if use_cache:
            self.outFile = self.outFileBase.format(hashlib.md5(
                text.encode('UTF-8')).hexdigest())
            _, extension = os.path.splitext(self.outFile)
            correct_path = VoiceCache.get_path_to_voice_file(
                text, extension)

            #  TODO: Remove hack

            bad_path = VoiceCache.get_path_to_voice_file(
                self.outFile, extension)
            cls = type(self)
            cls._logger.debug('text: {} outFile: {} correct_path: {} bad_path: {}'
                               .format(text, self.outFile, correct_path, bad_path))
            if os.path.exists(bad_path):
                cls._logger.debug_extra_verbose('renamed: {} to: {}'
                                                 .format(bad_path, correct_path))
                os.rename(bad_path, correct_path)
            self.outFile = correct_path

        return self.outFile

    def canSetSpeed(self):
        return self._player.canSetSpeed()

    def setSpeed(self, speed):
        return self._player.setSpeed(speed)

    def canSetVolume(self):
        return self._player.canSetVolume()

    def setVolume(self, volume):
        return self._player.setVolume(volume)

    def play(self):
        return self._player.play(self.outFile)

    def canSetPitch(self):  # Is this needed, or desired?
        return self._player.canSetPitch()

    def setPitch(self, pitch):
        return self._player.setPitch(pitch)

    def isPlaying(self):
        return self._player.isPlaying()

    def stop(self):
        return self._player.stop()

    def close(self):
        for f in os.listdir(self.outDir):
            if f.startswith('.'):
                continue
            fpath = os.path.join(self.outDir, f)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except:
                    type(self)._logger.error('Error Removing File')
        return self._player.close()

    @classmethod
    def getAvailablePlayers(cls, include_builtin=True) -> List[Type[AudioPlayer]]:
        players: List[Type[AudioPlayer]] = cast(List[Type[AudioPlayer]],
                                                [])
        for p in cls.players:
            if p.available():
                if not p.is_builtin() or include_builtin == p.is_builtin():
                    players.append(p)
        return players

    @classmethod
    def canPlay(cls):
        for p in cls.players:
            if p.available():
                return True
        return False

class MP3AudioPlayerHandler(WavAudioPlayerHandler):
    players = (WindowsAudioPlayer, AfplayPlayer, SOXAudioPlayer,
               Mpg123AudioPlayer, Mpg321AudioPlayer, MPlayerAudioPlayer)

    _logger: LazyLogger = None

    def __init__(self, preferred=None, advanced=False):
        super().__init__(preferred, advanced)
        cls = type(self)
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)
        self.outFileBase = os.path.join(self.outDir, 'speech{}.mp3')

        # TODO: Remove the 'speech' prefix

        self.outFile = os.path.join(self.outDir, 'speech.mp3')

    @classmethod
    def canPlay(cls):
        for p in cls.players:
            if p.available('mp3'):
                return True
        return False


class BuiltInAudioPlayerHandler(BasePlayerHandler):
    def __init__(self, base_handler: BasePlayerHandler = WavAudioPlayerHandler):
        super().__init__()
        self.base_handler = base_handler
