import errno
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from backends.players.iplayer import IPlayer
from backends.settings.setting_properties import SettingsProperties
from common import utils
from common.constants import Constants
from common.exceptions import ExpiredException
from common.logger import BasicLogger
from common.base_services import BaseServices
from common.minimal_monitor import MinimalMonitor
from common.monitor import Monitor
from common.phrases import Phrase
from common.setting_constants import Players
from common.settings import Settings
from common.simple_run_command import RunState, SimpleRunCommand

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
            #  cls._logger.debug_extra_verbose(f'Using tmpfs at: {tmpfs}')
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

    def notify(self, msg: str, now: bool = False) -> None:
        module_logger.debug(f'Can not notify player')

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

    def __init__(self):
        super().__init__()
        clz = type(self)
        clz._logger = module_logger.getChild(
                self.__class__.__name__)
        self._player_busy: bool = False
        self._simple_player_busy: bool = False
        self.speed: float = 0.0
        self.volume: float | None = None
        self.active = True
        self._player_process: subprocess.Popen = None
        self._simple_player_process: SimpleRunCommand = None
        self._time_of_previous_play_ended: datetime = datetime.now()
        self._post_play_pause_ms: int = 0
        self.kill: bool = False
        self.stop_urgent: bool = False
        self.reason: str = ''
        self.failed: bool | None = None
        self.rc: int | None = None


    def speedArg(self, speed: float) -> str:
        #  self._logger.debug(f'speedArg speed: {speed} multiplier: {self._speedMultiplier}')
        return f'{(speed * self._speedMultiplier):.2f}'

    def baseArgs(self, phrase: Phrase) -> List[str]:
        # Can raise ExpiredException
        args = []
        args.extend(self._playArgs)
        args[args.index(None)] = str(phrase.get_cache_path())
        return args

    def playArgs(self, phrase: Phrase) -> List[str]:
        # Can raise ExpiredException
        clz = type(self)
        base_args: List[str] = self.baseArgs(phrase)
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
        Monitor.exception_on_abort()

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
                self.stop(now=True)
                reraise(*sys.exc_info())
            except IOError as e:
                if e.errno != errno.EPIPE:
                    self._logger.error('Error piping audio')
            except:
                self._logger.error('Error piping audio')
            finally:
                source.close()
                self._player_busy = False

    def getSpeed(self) -> float:
        speed: float | None = \
            Settings.getSetting(SettingsProperties.SPEED, Settings.get_engine_id())
        self.setSpeed(speed)
        return speed

    def getVolumeDb(self) -> float:
        engine: BaseServices = BaseServices.getService(Settings.get_engine_id())
        volumeDb: float | None = engine.getVolumeDb()
        self.setVolume(volumeDb)
        return volumeDb

    def setSpeed(self, speed: float):
        clz = type(self)
        self.speed = speed

    def setVolume(self, volume: float):
        self.volume = volume

    def play(self, phrase: Phrase):
        clz = type(self)
        args: List[str]
        phrase_serial_number: int = phrase.serial_number
        try:
            clz._logger.debug(f'PHRASE: {phrase.get_text()}')
            phrase.test_expired()  # Throws ExpiredException
            delay_ms = max(phrase.get_pre_pause(), self._post_play_pause_ms)
            self._post_play_pause_ms = phrase.get_post_pause()
            waited: timedelta = datetime.now() - self._time_of_previous_play_ended
            waited_ms =  waited / timedelta(microseconds=1000)
            delta_ms = delay_ms - waited_ms
            if delta_ms > 0.0:
                additional_wait_needed_s: float = delta_ms / 1000.0
                clz._logger.debug(f'pausing {additional_wait_needed_s} ms')
                Monitor.exception_on_abort(timeout=float(additional_wait_needed_s))

            Monitor.exception_on_abort()
            args = self.playArgs(phrase)
        except AbortException:
            self.stop(now=True)
            reraise(*sys.exc_info())
        except ExpiredException:
            clz._logger.debug('EXPIRED')
            return
        except Exception as e:
            clz._logger.exception('')
            return
        try:
            self._simple_player_busy = True
            self._simple_player_process = SimpleRunCommand(args,
                                                           phrase_serial=phrase_serial_number,
                                                           name='mplayer')
            self._simple_player_process.run_cmd()
            clz._logger.debug_verbose(f'Running player to voice NOW args: {" ".join(args)}')
        except subprocess.CalledProcessError:
            clz._logger.exception('')
            self.reason = 'mplayer failed'
            self.failed = True
        finally:
            self._time_of_previous_play_ended = datetime.now()
            self._simple_player_busy = False

    def isPlaying(self) -> bool:
        self.set_state()
        return self._player_busy

    def notify(self, msg: str, now: bool = False):
        self.stop_urgent = now
        self.stop()


    def stop(self, now: bool = False):
        clz = type(self)
        self.stop_processes(now)

    def stop_processes(self, now: bool = False):
        clz = type(self)
        if now:
            self.kill = True
        clz._logger.debug(f'STOP received is_playing: {self.isPlaying()} kill: '
                          f'{self.kill}')
        if not self.isPlaying():
            return
        if self._player_process is not None:
            if self._player_process.poll is not None:
                self._player_process = None
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
                self.set_state()

        if self._simple_player_process is not None:
            if self._simple_player_process.get_state() >= RunState.COMPLETE:
                return
            self._simple_player_process.terminate()

        try:
            while Monitor.exception_on_abort(timeout = 0.5):
                if self._simple_player_process.get_state() >= RunState.COMPLETE:
                    return
                # Null until command starts running
        except AbortException:
            self._simple_player_process.process.kill()
            reraise(*sys.exc_info())
        except:
            pass
        finally:
            self.set_state()

    def close(self):
        self.stop_processes()

    def set_state(self):
        clz = type(self)
        if self._player_process is None or self._player_process.poll() is not None:
            if self._player_process is not None:
                self.rc = self._player_process.returncode
            self._player_busy = False
            self._player_process = None
        clz._logger.debug(f'Player busy: {self._player_busy}')
        if self._simple_player_process is not None:
            self.rc = self._simple_player_process.process.returncode
            self._player_busy = False
            self._simple_player_busy = False
            self._simple_player_process = None
            clz._logger.debug(f'SimplePlayer busy: {self._simple_player_busy}')


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
