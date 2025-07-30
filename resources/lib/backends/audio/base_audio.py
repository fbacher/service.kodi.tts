# coding=utf-8
from __future__ import annotations  # For union operator |

import subprocess
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

from backends.players.iplayer import IPlayer
from backends.settings.service_types import ServiceID
from backends.settings.service_unavailable_exception import ServiceUnavailable
from cache.voicecache import VoiceCache
from common import *
from common.base_services import BaseServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase
from common.setting_constants import Channels, PlayerMode, Players
from common.settings import Settings
from common.simple_pipe_command import SimplePipeCommand
from common.simple_run_command import SimpleRunCommand
from common.slave_communication import SlaveCommunication
from common.utils import TempFileUtils

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class AudioPlayer(IPlayer, BaseServices):
    """
    Base class for Audio Players.

    Players exist
    """
    ID = Players.NONE
    # name = ''
    _advanced: bool = False
    sound_file_types: List[str] = ['.wav']
    sound_dir: Path | None = None

    def __init__(self) -> None:
        clz = type(self)
        clz.set_sound_dir()
        self._post_play_pause_ms: int = 0
        self._time_of_previous_play_ended: datetime = datetime.now()
        self._failed: bool = False
        super().__init__()

    @classmethod
    def set_sound_dir(cls) -> None:
        """
        TODO: Does not appear needed. Always set to the same thing.

        Controls the tempfile and tempfile.NamedTemporaryFile 'dir' entry
        used to create temporary audio files. A None value allows tempfile
        to decide.
        :return:
        """
        cls.sound_dir = TempFileUtils.temp_dir()

    '''
    @classmethod
    def get_sound_dir(cls) -> Path:
        return cls.sound_dir
    '''

    @classmethod
    def get_tmp_path(cls, speech_file_name: str, sound_file_type: str) -> Path:
        filename: str = f'{speech_file_name}.{sound_file_type}'
        sound_file_path: Path = cls.sound_dir / filename
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

    def is_slave_player(self) -> bool:
        """
        A slave player is a long-lived process which accepts commands controlling
        which speech files are played as well as the volume, speed and other
        settings. Running as a slave may improve responsiveness.

        :return:  True if this player configured for slave mode. No check
                  is made for it running.
                  False, otherwise
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

    def play(self, phrase: Phrase):
        """
        Play the voice file for the given phrase
        :param phrase: Contains information about the spoken phrase, including
        path to .wav or .mp3 file
        :return:
        """
        stop_on_play: bool = not phrase.speak_over_kodi
        if stop_on_play:
            if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
                return

        clz = type(self)
        args: List[str] = []
        phrase_serial: int = phrase.serial_number
        try:
            phrase.test_expired()  # Throws ExpiredException
            DO_DELAY: bool = False
            if DO_DELAY:
                # Use previous phrase's post_play_pause
                delay_ms = max(phrase.get_pre_pause(), self._post_play_pause_ms)
                self._post_play_pause_ms = phrase.get_post_pause()
                #  pre_silence_path: Path = phrase.pre_pause_path()
                #  post_silence_path: Path = phrase.post_pause_path()
                waited: timedelta = datetime.now() - self._time_of_previous_play_ended
                # TODO: Get rid of this wait loop and use phrase pauses
                waited_ms = waited / timedelta(microseconds=1000)
                delta_ms = delay_ms - waited_ms
                if delta_ms > 0.0:
                    additional_wait_needed_s: float = delta_ms / 1000.0
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'pausing {additional_wait_needed_s} ms')
                    Monitor.exception_on_abort(timeout=float(additional_wait_needed_s))

            Monitor.exception_on_abort()
        except AbortException:
            self.stop(now=True)
            reraise(*sys.exc_info())
        except ExpiredException:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('EXPIRED')
            return
        except Exception as e:
            MY_LOGGER.exception('')
            return
        try:
            if stop_on_play:
                if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
                    return
            delete_after_run: Path | None = None
            if Constants.PLATFORM_WINDOWS:
                delete_after_run = phrase.get_cache_path()
        finally:
            self._time_of_previous_play_ended = datetime.now()

    def isPlaying(self) -> bool:
        return False

    def stop(self, now: bool = True) -> None:
        pass

    def close(self) -> None:
        pass

    def destroy(self) -> None:
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
    _availableArgs = None
    # Count appended to thread_name to make unique
    slave_player_count: int = 0
    std_player_count: int = 0

    def __init__(self):
        """
          Players are instantiated at startup (BootstrapPlayers) and not
          restarted. There is nothing to prevent them from being created on
          demand, as long as they are cleaned up properly.
        """
        super().__init__()
        self.player_mode: PlayerMode | None = None
        self.engine: BaseServices | None = None
        self.engine_key: ServiceID | None = None
        self.speed: float = 0.0
        self.volume: float | None = None
        self.active = True
        self._speedMultiplier: int = 1
        self._player_process: SimpleRunCommand | None = None
        self.lock: threading.RLock = threading.RLock()

    def init(self, engine_key: ServiceID):
        self.engine_key = engine_key
        try:
            self.engine = BaseServices.get_service(self.engine_key)
        except ServiceUnavailable:
            MY_LOGGER.warning(f'Can not load {self.engine_key}')
            self.engine = None

    def reset_subprocess(self) -> None:
        """
        Cleanus up between launched processes. Ensures states reset, files closed,
        processes killed and blocking until previous process stopped. Does NOT
        replace the need for explicit killing, etc. but helps guarantee that things
        don't go off the rails too much.
        """
        self._player_process: SimpleRunCommand | None = None
        self._failed = None

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
        # MY_LOGGER.debug_v(f'pipeArgs: {" ".join(pipe_args)}
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Running {clz.ID} via pipe')
        try:
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
            # MY_LOGGER.debug_v(
            #         f'START Running player to voice PIPE args: {" ".join(pipe_args)}')
            self._player_process.run_cmd()
        except subprocess.CalledProcessError as e:
            MY_LOGGER.exception('')
            self._failed = True
        except Exception as e:
            MY_LOGGER.exception('')
        finally:
            self._time_of_previous_play_ended = datetime.now()

    def getSpeed(self) -> float:
        speed: float | None = \
            Settings.get_speed()
        self.setSpeed(speed)
        return speed

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
            #  pre_silence_path: Path = phrase.pre_pause_path()
            #  post_silence_path: Path = phrase.post_pause_path()
            waited: timedelta = datetime.now() - self._time_of_previous_play_ended
            waited_ms = waited / timedelta(microseconds=1000)
            delta_ms = delay_ms - waited_ms
            if delta_ms > 0.0:
                additional_wait_needed_s: float = delta_ms / 1000.0
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'pausing {additional_wait_needed_s} ms')
                Monitor.exception_on_abort(timeout=float(additional_wait_needed_s))

            Monitor.exception_on_abort()
            args = self.playArgs(phrase)
        except AbortException:
            self.stop(now=True)
            reraise(*sys.exc_info())
        except ExpiredException:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('EXPIRED')
            return
        except Exception as e:
            MY_LOGGER.exception('')
            return
        try:
            if stop_on_play:
                if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
                    return
            delete_after_run: Path | None = None
            if VoiceCache.is_tmp_file(phrase.get_cache_path()):
                delete_after_run = phrase.get_cache_path()
            self._player_process = SimpleRunCommand(args,
                                                    phrase_serial=phrase_serial,
                                                    delete_after_run=delete_after_run,
                                                    name='plyr',
                                                    stop_on_kodi_play=stop_on_play)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(
                        f'START Running player to voice NOW args: {" ".join(args)}')
            self._player_process.run_cmd()
        except subprocess.CalledProcessError:
            MY_LOGGER.exception('')
            self._failed = True
        finally:
            self._time_of_previous_play_ended = datetime.now()

    def isPlaying(self) -> bool:
        self.set_state()
        return self._player_process is not None

    def stop_player(self, purge: bool = True,
                    keep_silent: bool = False,
                    kill: bool = False):
        """
        Stop player (most likely because current text is expired)
        Engines may wish to override this method, particularly when
        the player is built-in.

        :param purge: if True, then purge any queued vocings
                      if False, then only stop playing current phrase
        :param keep_silent: if True, ignore any new phrases until restarted
                            by resume_player.
                            If False, then play any new content
        :param kill: If True, kill any player processes. Implies purge and
                     keep_silent.
                     If False, then the player will remain ready to play new
                     content, depending upon keep_silent
        :return:
        """
        clz = type(self)

        # Only slave players have a queue of pending speech files
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'purge: {purge} keep_silent: {keep_silent} '
                            f'kill: {kill}')

        if self._player_process is not None:
            self.destroy_process()

    def destroy(self):
        """
        Destroy this player and any dependent player process, etc. Typicaly done
        when either stopping TTS (F12) or shutdown, or switching engines,
        players, etc.

        :return:
        """
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'destroy')
        self.destroy_process()

    def destroy_process(self):
        """
        Destroy (kill) the player / player manager process.
        There is no point in terminating the process in an attempt to be
        kinder to produced files, etc. since we are always in a hurry to
        stop it. As long as no corrupt files accumulate in the cache we
        are ok.
        """
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'DESTROY {clz.ID}')
        with self.lock:
            try:
                if self._player_process is not None:
                    if self._player_process.poll() is not None:
                        self._player_process = None
                        return
                    self._player_process.kill()
            except AbortException:
                self._player_process.kill()
                reraise(*sys.exc_info())
            except Exception as e:
                MY_LOGGER.exception('')
            finally:
                self.set_state()
                self._player_process = None

    def close(self):
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'In close calling destroy')
        self.destroy()

    def set_state(self):
        with self.lock:
            if (self._player_process is not None and
                    self._player_process.process is not None and
                    self._player_process.process.poll() is not None):
                self._player_process = None

    @classmethod
    def available(cls, ext=None) -> bool:
        #  player_id: str = Settings.get_player()
        raise NotImplementedError('base class')


class SubprocessSlaveAudioPlayer(SubprocessAudioPlayer):
    _availableArgs = None
    # Count appended to thread_name to make unique
    slave_player_count: int = 0
    std_player_count: int = 0

    def __init__(self):
        """
        Players are instantiated at startup (BootstrapPlayers) and not
        restarted. There is nothing to prevent them from being created on
        demand, as long as they are cleaned up properly.
        """
        super().__init__()
        clz = type(self)
        self._slave_commo: SlaveCommunication | None = None

    def ensure_slave_mode(self) -> None:
        if not self.is_slave_player():
            raise ValueError('Not in slave_mode')
        if self._player_process is not None:
            try:
                if self._player_process.cmd_finished:
                    self._player_process = None
            except:
                MY_LOGGER.exception('')
        return

    def reset_subprocess(self) -> None:
        """
        Cleanus up between launched processes. Ensures states reset, files closed,
        processes killed and blocking until previous process stopped. Does NOT
        replace the need for explicit killing, etc. but helps guarantee that things
        don't go off the rails too much.
        """
        super().__init__()
        self._slave_commo = None

    def is_slave_player(self) -> bool:
        """
        A slave player is a long-lived process which accepts commands controlling
        which speech files are played as well as the volume, speed and other
        settings. Running as a slave may improve responsiveness.

        :return:  True if this player configured for slave mode. No check
                  is made for it running.
                  False, otherwise
        """
        try:
            self.player_mode = Settings.get_player_mode(engine_key=self.engine_key)
            return self.player_mode == PlayerMode.SLAVE_FILE
        except NotImplementedError:
            pass
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'NOT SLAVE')
        return False

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
        self.ensure_slave_mode()
        if self._slave_commo is None:
            self._start_slave_player(phrase)
        phrase_serial: int = phrase.serial_number
        try:
            phrase.test_expired()  # Throws ExpiredException
            volume: float = self.get_player_volume(as_decibels=False)
            speed: float = self.get_player_speed()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'volume: {volume} speed: {speed}')
            with self.lock:
                if self._slave_commo is not None:
                    self._slave_commo.set_channels(Channels.STEREO)
                    self._slave_commo.add_phrase(phrase, volume, speed)
        except AbortException:
            self.stop(now=True)
            reraise(*sys.exc_info())
        except ExpiredException:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('EXPIRED')
            return
        except Exception as e:
            MY_LOGGER.exception('')
            return

    def _start_slave_player(self, phrase: Phrase) -> None:
        clz = type(self)
        if self._slave_commo is not None:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'slave_commo is NOT None and not started')
            return
        with self.lock:  # Is lock needed, or sufficient?
            try:
                args: List[str] = self.get_slave_play_args()
                p_path = self.get_slave_pipe_path()
                volume: float = self.get_player_volume(as_decibels=False)
                speed: float = self.get_player_speed()
                s_num: int = phrase.serial_number
                #  play_channels: Channels = self.get_player_channels()
                clz.slave_player_count += 1
                slave_count: int = clz.slave_player_count
                try:
                    self._slave_commo = SlaveCommunication(args,
                                                           phrase_serial=s_num,
                                                           thread_name='mpv',
                                                           count=slave_count,
                                                           stop_on_play=True,
                                                           fifo_path=p_path,
                                                           default_speed=speed,
                                                           default_volume=volume)
                    # MY_LOGGER.debug(
                    #         f'START Running slave player to voice NOW args: {"
                    #         ".join(args)}')
                    self._slave_commo.start_service()
                    self._failed = False
                except subprocess.CalledProcessError:
                    MY_LOGGER.exception('')
                    self._slave_commo = None
                    self._failed = True
                finally:
                    self._time_of_previous_play_ended = datetime.now()
            except:
                MY_LOGGER.exception('')
                self._slave_commo = None
                self._failed = True


    def isPlaying(self) -> bool:
        """
        Determines if player is playing anything
        """
        if not self.is_slave_player():
            return super().isPlaying()
        return self._is_playing()

    def _is_playing(self) -> bool:
        if self._slave_commo is None:
            return False
        return not self._slave_commo.is_idle

    def stop_player(self, purge: bool = True,
                    keep_silent: bool = False,
                    kill: bool = False):
        """
        Stop player (most likely because current text is expired)
        Engines may wish to override this method, particularly when
        the player is built-in.

        :param purge: if True, then purge any queued vocings
                      if False, then only stop playing current phrase
        :param keep_silent: if True, ignore any new phrases until restarted
                            by resume_player.
                            If False, then play any new content
        :param kill: If True, kill any player processes. Implies purge and
                     keep_silent.
                     If False, then the player will remain ready to play new
                     content, depending upon keep_silent
        :return:
        """
        # Only slave players have a queue of pending speech files
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'purge: {purge} keep_silent: {keep_silent} '
                            f'kill: {kill}')
        with self.lock:
            if not self.is_slave_player():
                return super().stop_player(purge=purge, keep_silent=keep_silent,
                                           kill=kill)
            self._stop_slave_player(purge=purge, keep_silent=keep_silent,
                                    kill=kill)

    def _stop_slave_player(self, purge: bool = True,
                           keep_silent: bool = False,
                           kill: bool = False):
        """
        Stop player (most likely because current text is expired)
        Engines may wish to override this method, particularly when
        the player is built-in.

        :param purge: if True, then purge any queued vocings
                      if False, then only stop playing current phrase
        :param keep_silent: if True, ignore any new phrases until restarted
                            by resume_player.
                            If False, then play any new content
        :param kill: If True, kill any player processes. Implies purge and
                     keep_silent.
                     If False, then the player will remain ready to play new
                     content, depending upon keep_silent
        :return:
        """
        # Only slave players have a queue of pending speech files
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'purge: {purge} keep_silent: {keep_silent} '
                            f'kill: {kill}')
        with self.lock:
            if self._slave_commo is not None:
                if kill:
                    self._destroy_slave_commo()
                else:
                    # Stop playing current audio and cancel all queued audio
                    # And perhaps ignore all incoming audios to play until
                    # further notice
                    self._slave_commo.stop_player(purge=purge,
                                                  keep_silent=keep_silent,
                                                  kill=kill)

    def destroy(self) -> None:
        """
        Destroy this player and any dependent player process, etc. Typicaly done
        when either stopping TTS (F12) or shutdown, or switching engines,
        players, etc.

        :return:
        """
        with self.lock:
            if not self.is_slave_player():
                return super().destroy()

            self._destroy_slave_commo()

    def _destroy_slave_commo(self) -> None:
        """
        Kill the slave player process as wll as the SlaveCommunication thread /
        'player'.
        """
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'DESTROY__slave_commo')
        with self.lock:
            if self._slave_commo is not None:
                try:
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v('DESTROY SLAVE')
                    self.player_mode = None
                    self._slave_commo.destroy()
                except Exception as e:
                    MY_LOGGER.exception('')
                finally:
                    self._slave_commo = None
                return

    def close(self):
        """
        Completely shutdown the activity of this player
        """
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'In close calling destroy')
        self.destroy()

    def set_state(self):
        with self.lock:
            if not self.is_slave_player():
                return super().set_state()

            if (self._slave_commo is not None and
                    self._slave_commo.slave.poll() is not None):
                self._slave_commo = None

    @classmethod
    def available(cls, ext=None) -> bool:
        #  player_id: str = Settings.get_player()
        raise NotImplementedError('base class')
