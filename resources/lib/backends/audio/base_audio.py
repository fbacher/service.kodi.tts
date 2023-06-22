import errno
import os
import shutil
import subprocess
import sys

from backends.players.iplayer import IPlayer
from backends.settings.setting_properties import SettingsProperties
from common import utils
from common.constants import Constants
from common.logger import BasicLogger
from common.base_services import BaseServices
from common.minimal_monitor import MinimalMonitor
from common.monitor import Monitor
from common.setting_constants import Players
from common.settings import Settings

from common.typing import *
module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class AudioPlayer(IPlayer, BaseServices):
    ID = Players.NONE
    # name = ''

    _advanced: bool = False
    sound_file_types: List[str] = ['.wav']
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None
    _logger: BasicLogger = None

    def __init__(self) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)

        clz.set_sound_dir()
        super().__init__()

    @classmethod
    def set_sound_dir(cls):
        tmpfs = utils.getTmpfs()
        if Settings.getSetting(SettingsProperties.USE_TEMPFS,
                               SettingsProperties.TTS_SERVICE, True) and tmpfs:
            cls._logger.debug_extra_verbose(f'Using tmpfs at: {tmpfs}')
            cls.sound_dir = os.path.join(tmpfs, 'kodi_speech')
        else:
            cls.sound_dir = os.path.join(Constants.PROFILE_PATH, 'kodi_speech')
        if not os.path.exists(cls.sound_dir):
            os.makedirs(cls.sound_dir)

    @classmethod
    def get_tmp_path(cls, speech_file_name: str, sound_file_type: str) -> str:
        sound_file_base = '{speech_file_name}{sound_file_type}'

        filename: str = cls.sound_file_base.format(speech_file_name=speech_file_name,
                                                   sound_file_type=sound_file_type)
        sound_file_path: str = os.path.join(cls.sound_dir, filename)
        return sound_file_path

    def canSetSpeed(self) -> bool:
        """

        @return:
        """
        return False

    def setSpeed(self, speed: float) -> None:
        """

        @param speed:
        """
        pass

    def canSetPitch(self) -> bool:
        """

        @return:
        """
        return False

    def setPitch(self, pitch: float) -> None:
        pass

    def canSetVolume(self) -> bool:
        return False

    def setVolume(self, volume: float) -> None:
        pass

    def canSetPipe(self) -> bool:
        return False

    def pipe(self, source) -> None:
        pass

    def play(self, path: str) -> None:
        pass

    def isPlaying(self) -> bool:
        return False

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass

    @staticmethod
    def available(ext=None) -> bool:
        return False

    @classmethod
    def is_builtin(cls) -> bool:
        #
        # Is this Audio Player built-into the voice engine (i.e. espeak).
        #
        return False


class SubprocessAudioPlayer(AudioPlayer):
    _logger: BasicLogger = None
    _availableArgs = None
    _playArgs = None
    _speedArgs = None
    _speedMultiplier: int = 1
    _volumeArgs = None
    _volumeMultipler = 1
    _pipeArgs = None
    kill = False

    def __init__(self):
        super().__init__()
        clz = type(self)
        clz._logger = module_logger.getChild(
                self.__class__.__name__)
        self._player_busy: bool = False
        self.speed: float = 0.0
        self.volume: float | None = None
        self.active = True
        self._player_process = None

    def speedArg(self, speed: float) -> str:
        self._logger.debug(f'speedArg speed: {speed} multiplier: {self._speedMultiplier}')
        return f'{(speed * self._speedMultiplier):.2f}'

    def baseArgs(self, path: str) -> List[str]:
        args = []
        args.extend(self._playArgs)
        args[args.index(None)] = path
        return args

    def playArgs(self, path: str) -> List[str]:
        clz = type(self)
        base_args: List[str] = self.baseArgs(path)
        clz._logger.debug_verbose(f'args: {" ".join(base_args)}')
        return base_args

    def get_pipe_args(self):
        clz = type(self)
        base_args = self._pipeArgs
        clz._logger.debug(f'playArgs: {self.playArgs("xxx")} pipeArgs: {self._pipeArgs}')
        return base_args

    def canSetPipe(self) -> bool:
        return bool(self._pipeArgs)

    def pipe(self, source):
        Monitor.throw_exception_if_abort_requested()

        clz = type(self)
        pipe_args = self.get_pipe_args()
        clz._logger.debug_verbose(f'pipeArgs: {" ".join(pipe_args)}')
        self._player_busy = True
        with subprocess.Popen(pipe_args, stdin=subprocess.PIPE,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.STDOUT) as self._player_process:
            try:
                shutil.copyfileobj(source, self._player_process.stdin)
            except AbortException:
                self._player_process.kill()
                reraise(*sys.exc_info())
            except IOError as e:
                if e.errno != errno.EPIPE:
                    self._logger.error('Error piping audio', hide_tb=True)
            except:
                self._logger.error('Error piping audio', hide_tb=True)

            finally:
                source.close()
                self._player_busy = False

    def getSpeed(self) -> float:
        speed: float | None = \
            Settings.getSetting(SettingsProperties.SPEED, Settings.get_engine_id())
        self.setSpeed(speed)
        return speed

    def getVolumeDb(self) -> float:
        volumeDb: float | None = \
            Settings.getSetting(SettingsProperties.VOLUME, Settings.get_engine_id())
        self.setVolume(volumeDb)
        return volumeDb

    def setSpeed(self, speed: float):
        clz = type(self)
        clz._logger.debug(f'setSpeed: {speed}')
        self.speed = speed

    def setVolume(self, volume: float):
        self._logger.debug(f'setVolume: {volume}')
        self.volume = volume

    def play(self, path: str):
        clz = type(self)
        Monitor.throw_exception_if_abort_requested()
        args = self.playArgs(path)
        clz._logger.debug_verbose(f'args: {" ".join(args)}')
        try:
            self._player_busy = True
            subprocess.run(args, shell=False, text=True, check=True)
        except subprocess.CalledProcessError:
            clz._logger.exception('')
            reason = 'mplayer failed'
            failed = True
        finally:
            self._player_busy = False

    def isPlaying(self) -> bool:
        return self._player_busy

    def stop(self):
        if not self.isPlaying():
            return
        try:
            if self.kill:
                self._player_process.kill()
            else:
                self._player_process.terminate()
        except AbortException:
            self._player_process.kill()
            reraise(*sys.exc_info())
        except:
            pass
        finally:
            self._player_busy = None

    def close(self):
        self.active = False
        if not self._player_process or self._player_process.poll():
            return
        try:
            self._player_process.kill()
        except AbortException:
            reraise(*sys.exc_info())
        except:
            pass
        finally:
            self._player_process = None

    @classmethod
    def available(cls, ext=None) -> bool:
        try:
            subprocess.call(cls._availableArgs, stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT, universal_newlines=True)
        except AbortException:
            reraise(*sys.exc_info())
        except:
            return False
        return True
