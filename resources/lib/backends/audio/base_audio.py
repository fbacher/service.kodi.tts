from __future__ import annotations  # For union operator |

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from backends.players.iplayer import IPlayer
from backends.settings.i_constraints import IConstraints
from backends.settings.i_validators import IConstraintsValidator
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from common import *
from common import utils
from common.base_services import BaseServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import BasicLogger
from common.monitor import Monitor
from common.phrases import Phrase
from common.setting_constants import Channels, PlayerMode, Players
from common.settings import Settings
from common.simple_pipe_command import SimplePipeCommand
from common.simple_run_command import SimpleRunCommand
from common.slave_communication import SlaveCommunication

module_logger: BasicLogger = BasicLogger.get_logger(__name__)


class AudioPlayer(IPlayer, BaseServices):
    ID = Players.NONE
    # name = ''

    _advanced: bool = False
    sound_file_types: List[str] = ['.wav']
    sound_dir: str = None
    _logger: BasicLogger = None

    def __init__(self) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger

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
    def get_sound_dir(cls) -> str:
        return cls.sound_dir

    @classmethod
    def get_tmp_path(cls, speech_file_name: str, sound_file_type: str) -> str:
        sound_file_base = '{speech_file_name}{sound_file_type}'

        filename: str = f'{speech_file_name}{sound_file_type}'
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

    def pipe(self, source, phrase: Phrase) -> None:
        pass

    def play(self, path: str) -> None:
        pass

    def isPlaying(self) -> bool:
        return False

    def stop(self, now: bool = True) -> None:
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

    def __init__(self):
        super().__init__()
        clz = type(self)
        clz._logger = module_logger
        self._player_busy: bool = False
        self.player_mode: PlayerMode | None = None
        self._simple_player_busy: bool = False
        self.speed: float = 0.0
        self.volume: float | None = None
        self.active = True
        self._speedMultiplier: int = 1
        self._player_process: SimpleRunCommand | None = None
        self._post_play_pause_ms: int = 0
        #  HACK!
        self.slave_player_process: SlaveCommunication | None = None
        self._time_of_previous_play_ended: datetime = datetime.now()
        self.kill: bool = False
        self.stop_urgent: bool = False
        self.reason: str = ''
        self.failed: bool | None = None
        self.rc: int | None = None

    '''
    def kodi_player_status_listener(self, kodi_player_state: KodiPlayerState) -> bool:
        """
        Called when Kodi begins to start/stop playing a movie, music, display
        photos, etc....  Normally you want to cease any TTS chatter. Some
        possible actions include:
          * When engine uses a slave player that can idle until next file is to
            be played, then you just want to abort whatever is playing and have
            engine not
            send anything else to slave player until Kodi finishes its thing
            (or unless something comes in that requires voicing even if Kodi
            is doing something).
          * When engine launches a player process for every voiced phrase, then
            you want to kill the player process to abort the current voicing.
            The engine can stay alive but, as in the case before, should ignore
            most voicing requests until Kodi finishes its thing, or until some
            comes in that requires voicing even if Kodi is doing something.

        :param kodi_player_state:
        :return:
        """
        clz = type(self)
        clz.player_status = kodi_player_state
        clz._logger.debug(f'Player play status: {kodi_player_state}')
        if Monitor.is_abort_requested():
            return True

        if kodi_player_state == KodiPlayerState.PLAYING_VIDEO:
            self.stop()
            return False

        return False
    '''

    def is_slave_player(self) -> bool:
        """
        A slave player is a long-lived process which accepts commands controlling
        which speech files are played as well as the volume, speed and other
        settings. Running as a slave may improve responsiveness.

        :return:  True if this player configured for slave mode. No check
                  is made for it running.
                  False, otherwise
        """
        clz = type(self)
        self.player_mode = Settings.get_player_mode()
        if self.player_mode == PlayerMode.SLAVE_FILE:
            return True
        return False

    def speedArg(self, speed: float) -> str:
        #  self._logger.debug(f'speedArg speed: {speed} multiplier: {
        #  self._speedMultiplier}')
        return f'{(speed * self._speedMultiplier):.2f}'

    def baseArgs(self, phrase: Phrase) -> List[str]:
        # Broken
        # Can raise ExpiredException
        args = []
        args[args.index(None)] = str(phrase.get_cache_path())
        return args

    def playArgs(self, phrase: Phrase) -> List[str]:
        # Can raise ExpiredException
        clz = type(self)
        base_args: List[str] = self.baseArgs(phrase)
        return base_args

    def get_pipe_args(self):
        raise NotImplementedError

    def canSetPipe(self) -> bool:
        raise NotImplementedError

    def pipe(self, source: BinaryIO, phrase: Phrase) -> None:
        Monitor.exception_on_abort()
        clz = type(self)
        pipe_args: List[str] = list(self.get_pipe_args())
        # clz._logger.debug_verbose(f'pipeArgs: {" ".join(pipe_args)}')
        try:
            self._player_busy = True
            stop_on_play: bool = not phrase.speak_over_kodi
            stdout: TextIO
            stderr: TextIO
            name: str
            self._player_process = SimplePipeCommand(pipe_args,
                                                     phrase_serial=phrase.serial_number,
                                                     stdin=source,
                                                     stdout=subprocess.DEVNULL,
                                                     stderr=subprocess.STDOUT,
                                                     name='mplayer',
                                                     stop_on_play=stop_on_play)
            # shutil.copyfileobj(source, self._player_process.stdin)
            # clz._logger.debug_verbose(
            #         f'START Running player to voice PIPE args: {" ".join(pipe_args)}')
            self._player_process.run_cmd()
        except subprocess.CalledProcessError as e:
            clz._logger.exception('')
            self.reason = 'mplayer failed'
            self.failed = True
        except Exception as e:
            clz._logger.exception('')
        finally:
            self._time_of_previous_play_ended = datetime.now()
            self._simple_player_busy = False

        '''
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
        '''

    def getSpeed(self) -> float:
        speed: float | None = \
            Settings.getSetting(SettingsProperties.SPEED, Settings.get_player_id())
        self.setSpeed(speed)
        return speed

    def getVolumeDb(self) -> float:
        #  All volumes are relative to the TTS volume -12db .. +12db.
        # the service_id is Services.TTS_Service_id.  We therefore
        # don't care what changes the engine, etc. have made.
        # We just trust that the volume in the source input matches
        # the tts 'line-input' or '0' tts volume level.

        clz = type(self)
        final_volume: int = Settings.get_volume()
        engine_volume_val: IConstraintsValidator = SettingsMap.get_validator(
                Settings.get_engine_id(),
                SettingsProperties.VOLUME)
        engine_id: str = Settings.get_engine_id()
        engine: BaseServices = BaseServices.getService(engine_id)
        engine_vol_constraints: IConstraints = engine_volume_val.get_constraints()
        player_id: str = Settings.get_player_id()
        player_volume_val: IConstraintsValidator
        player_volume_val = SettingsMap.get_validator(clz.service_ID,
                                                      SettingsProperties.VOLUME)
        player_volume: int = player_volume_val.getValue()
        player_vol_constraints: IConstraints = player_volume_val.get_constraints()

        adjusted_player_volume = \
            engine_vol_constraints.translate_value(player_vol_constraints, player_volume)

        # self.setVolume(volumeDb)
        return adjusted_player_volume

    def setSpeed(self, speed: float):
        clz = type(self)
        self.speed = speed

    def setVolume(self, volume: float):
        self.volume = volume

    def get_player_speed(self) -> float:
        pass

    def get_player_volume(self, as_decibels: bool = True) -> float:
        pass

    def get_slave_pipe_path(self) -> Path:
        pass

    def get_player_channels(self) -> Channels:
        pass

    def play(self, phrase: Phrase):
        """
        Play the voice file for the given phrase
        :param phrase: Contains information about the spoken phrase, including
        path to .wav or .mp3 file
        :return:
        """
        clz = SubprocessAudioPlayer
        # Do we need to kill a stale player?
        if self.slave_player_process is not None:
            # Will stop pending voicings and destroy non-slave player.
            self.abort_voicing(purge=True, future=True)

        stop_on_play: bool = not phrase.speak_over_kodi
        if stop_on_play:
            if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
                return

        clz = type(self)
        args: List[str] = []
        phrase_serial: int = phrase.serial_number
        try:
            phrase.test_expired()  # Throws ExpiredException

            # Use previous phrase's post_play_pause

            delay_ms = max(phrase.get_pre_pause(), self._post_play_pause_ms)

            self._post_play_pause_ms = phrase.get_post_pause()
            #  pre_silence_path: Path = phrase.get_pre_pause_path()
            #  post_silence_path: Path = phrase.get_post_pause_path()
            waited: timedelta = datetime.now() - self._time_of_previous_play_ended
            waited_ms = waited / timedelta(microseconds=1000)
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
            if stop_on_play:
                if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
                    return
            self._simple_player_busy = True
            delete_after_run: Path = None
            if Constants.PLATFORM_WINDOWS:
                delete_after_run = phrase.get_cache_path()
            self._player_process = SimpleRunCommand(args,
                                                    phrase_serial=phrase_serial,
                                                    delete_after_run=delete_after_run,
                                                    name='mplayer',
                                                    stop_on_play=stop_on_play)
            clz._logger.debug_verbose(
                    f'START Running player to voice NOW args: {" ".join(args)}')
            self._player_process.run_cmd()
        except subprocess.CalledProcessError:
            clz._logger.exception('')
            self.reason = 'mplayer failed'
            self.failed = True
        finally:
            self._time_of_previous_play_ended = datetime.now()
            self._simple_player_busy = False

    def get_slave_play_args(self) -> List[str]:
        raise NotImplementedError

    def slave_play(self, phrase: Phrase):
        """
        Uses a slave player (such as mpv in slave mode) to play all audio
        files. This avoids the cost of repeatedly launching the player. Should
        also improve control.

        :param phrase:
        :return:
        """
        clz = type(self)
        # clz._logger.debug(f'In slave_play phrase: {phrase}'

        # Do we need to kill a stale player?
        if self._player_process is not None:
            # Will stop pending voicings
            self.abort_voicing(purge=True, future=True)

        try:
            if self.slave_player_process is None:
                try:
                    args: List[str] = self.get_slave_play_args()
                    self._simple_player_busy = True
                    slave_pipe_path = self.get_slave_pipe_path()
                    volume: float = self.get_player_volume(as_decibels=False)
                    #  play_channels: Channels = self.get_player_channels()
                    self.slave_player_process = SlaveCommunication(args,
                                                                   phrase_serial=phrase.serial_number,
                                                                   thread_name='mpv',
                                                                   stop_on_play=True,
                                                                   slave_pipe_path=slave_pipe_path,
                                                                   speed=self.get_player_speed(),
                                                                   volume=volume)
                    # clz._logger.debug(
                    #         f'START Running slave player to voice NOW args: {"
                    #         ".join(args)}')
                    self.slave_player_process.start_service()
                except subprocess.CalledProcessError:
                    clz._logger.exception('')
                    self.reason = 'mpv failed'
                    self.failed = True
                finally:
                    self._time_of_previous_play_ended = datetime.now()
                    self._simple_player_busy = False

        except Exception as e:
            clz._logger.exception('')

        phrase_serial: int = phrase.serial_number
        try:
            phrase.test_expired()  # Throws ExpiredException
            volume: float = self.get_player_volume(as_decibels=False)
            speed: float = self.get_player_speed()
            self.slave_player_process.set_volume(volume)
            self.slave_player_process.set_speed(speed)
            self.slave_player_process.set_channels(Channels.STEREO)
            self.slave_player_process.add_phrase(phrase, volume, speed)
            # clz._logger.debug(f'slave state: {self.slave_player_process.get_state()}')
        except AbortException:
            self.stop(now=True)
            reraise(*sys.exc_info())
        except ExpiredException:
            clz._logger.debug('EXPIRED')
            return
        except Exception as e:
            clz._logger.exception('')
            return

    def isPlaying(self) -> bool:
        self.set_state()
        return self._player_busy

    def abort_voicing(self, purge: bool = True, future: bool = False) -> None:
        """
        Stop voicing pending speech and/or future speech. Most often used to
        stop in order to allow a higher priority voicing to start.

        :param purge: if True, then abandon playing all pending speech
        :param future: if True, then ignore future voicings.
        :return: None
        """
        clz = type(self)

        # Only slave players have a queue of pending speech files
        if self.slave_player_process is not None:
            self.slave_player_process.abort_voicing(purge, future)
        if future:
            # Destroys any active player process (slave or non-slave)
            self.destroy_player_process()

    '''
    def stop_processes(self, now: bool = False):
        """
        Stop voicing by killing player processes
        :param now:
        :return:
        """
        clz = type(self)
        if self.is_slave_player():
            clz._logger.warning(f'stop_processes should NOT be called for'
                                f'slave players')
            return
        if now:
            self.kill = True
        clz._logger.debug(f'STOP received is_playing: {self.isPlaying()} kill: '
                          f'{self.kill}')

        if not self.isPlaying():
            return
        if self._player_process is not None:
            if self._player_process.poll() is not None:
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
            except Exception as e:
                clz._logger.exception('')
            finally:
                self.set_state()

        if self._player_process is not None:
            if self._player_process.get_state().value >= RunState.COMPLETE.value:
                return
            self._player_process.terminate()

        try:
            while Monitor.exception_on_abort(timeout = 0.5):
                if self._player_process.get_state().value >= RunState.COMPLETE.value:
                    return
                # Null until command starts running
        except AbortException:
            self._player_process.kill()
            reraise(*sys.exc_info())
        except:
            pass
        finally:
            self.set_state()
    '''

    def destroy(self):
        """
        Destroy this player and any dependent player process, etc. Typicaly done
        when either stopping TTS (F12) or shutdown, or switching engines,
        players, etc.

        :return:
        """
        clz = type(self)
        clz._logger.debug(f'destroy')
        self.destroy_player_process()

    def destroy_player_process(self):
        """
        Destroy the ployer process (ex. mpv, mplayer, etc.). Typicaly done
        when stopping TTS, or when long-running player (one which exists for
        multiple voicings) needs to shutdown the process. Note that

        :return:
        """
        clz = type(self)
        clz._logger.debug(f'destroy_player_process')
        if self.slave_player_process is not None:
            try:
                self.slave_player_process.destroy()
            except Exception as e:
                clz._logger.exception('')
            self._simple_player_busy = False
            self.slave_player_process = None
            return

        # Non-slave player

        if self._player_process is not None:
            if self._player_process.poll() is not None:
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
            except Exception as e:
                clz._logger.exception('')
            finally:
                self.set_state()
        """
        try:
            while Monitor.exception_on_abort(timeout=0.5):
                if self._player_process.get_state().value >= RunState.COMPLETE.value:
                    return
                # Null until command starts running
        except AbortException:
            self._player_process.kill()
            reraise(*sys.exc_info())
        except:
            pass
        finally:
            self.set_state()
        """
        self._player_process = None

    def close(self):
        self.destroy()

    def set_state(self):
        clz = type(self)
        if self._player_process is None:
            self._player_busy = False
        elif self._player_process.process.poll() is not None:
            self.rc = self._player_process.process.returncode
            self._player_busy = False
            self._player_process = None
        else:
            #  clz._logger.debug(f'Player busy: {self._player_busy}')
            if (self._player_process is not None and
                    self._player_process.process is not None and
                    self._player_process.process.returncode is not None):
                self.rc = self._player_process.process.returncode
                self._player_busy = False
                self._simple_player_busy = False
                self._player_process = None
                clz._logger.debug(f'SimplePlayer busy: {self._simple_player_busy}')
            else:
                self._player_busy = True

    @classmethod
    def available(cls, ext=None) -> bool:
        # This looks messed up bad
        try:
            subprocess.call(cls._availableArgs, stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT, universal_newlines=True,
                            encoding='utf-8')
        except AbortException:
            reraise(*sys.exc_info())
        except:
            return False
        return True
