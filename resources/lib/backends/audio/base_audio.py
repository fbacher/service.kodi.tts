# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys
import tempfile
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
        super().__init__()

    @classmethod
    def set_sound_dir(cls) -> None:
        """
        Controls the tempfile and tempfile.NamedTemporaryFile 'dir' entry
        used to create temporary audio files. A None value allows tempfile
        to decide.
        :return:
        """
        cls.sound_dir = TempFileUtils.temp_dir()

    @classmethod
    def get_sound_dir(cls) -> Path:
        return cls.sound_dir

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

    def slave_play(self, phrase: Phrase):
        pass

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
        super().__init__()
        clz = type(self)
        self._player_busy: bool = False
        self.player_mode: PlayerMode | None = None
        self._simple_player_busy: bool = False
        self.engine: BaseServices | None = None
        self.engine_key: ServiceID | None = None
        self.speed: float = 0.0
        self.volume: float | None = None
        self.active = True
        self._speedMultiplier: int = 1
        self._player_process: SimpleRunCommand | None = None
        #  HACK!
        self.slave_player_process: SlaveCommunication | None = None
        self.kill: bool = False
        self.stop_urgent: bool = False
        self.reason: str = ''
        self.failed: bool | None = None
        self.rc: int | None = None

    def init(self, engine_key: ServiceID):
        self.engine_key = engine_key
        try:
            self.engine = BaseServices.get_service(self.engine_key)
        except ServiceUnavailable:
            MY_LOGGER.warning(f'Can not load {self.engine_key}')
            self.engine = None

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
        MY_LOGGER.debug(f'Player play status: {kodi_player_state}')
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
        try:
            self.player_mode = Settings.get_player_mode(engine_key=self.engine_key)
            if self.player_mode == PlayerMode.SLAVE_FILE:
                #  MY_LOGGER.debug(f'SLAVE_PLAYER')
                return True
        except NotImplementedError:
            pass
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'NOT SLAVE')
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
        # MY_LOGGER.debug_v(f'pipeArgs: {" ".join(pipe_args)}
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Running {clz.ID} via pipe')
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
            # MY_LOGGER.debug_v(
            #         f'START Running player to voice PIPE args: {" ".join(pipe_args)}')
            self._player_process.run_cmd()
        except subprocess.CalledProcessError as e:
            MY_LOGGER.exception('')
            self.reason = f'{clz.ID} failed'
            self.failed = True
        except Exception as e:
            MY_LOGGER.exception('')
        finally:
            self._time_of_previous_play_ended = datetime.now()
            self._simple_player_busy = False

    def getSpeed(self) -> float:
        speed: float | None = \
            Settings.get_speed()
        self.setSpeed(speed)
        return speed

    def getVolumeDb(self) -> float:
        #  All volumes are relative to the TTS volume -12db .. +12db.
        # the setting_id is Services.TTS_Service_id.  We therefore
        # don't care what changes the engine, etc. have made.
        # We just trust that the volume in the source input matches
        # the tts 'line-input' or '0' tts volume level.
        return self.get_player_volume(as_decibels=True)

    def setSpeed(self, speed: float):
        return self.get_player_speed()

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
            self._simple_player_busy = True
            delete_after_run: Path | None = None
            if VoiceCache.is_tmp_file(phrase.get_cache_path()):
                delete_after_run = phrase.get_cache_path()
            self._player_process = SimpleRunCommand(args,
                                                    phrase_serial=phrase_serial,
                                                    delete_after_run=delete_after_run,
                                                    name='plyr',
                                                    stop_on_play=stop_on_play)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(
                        f'START Running player to voice NOW args: {" ".join(args)}')
            self._player_process.run_cmd()
        except subprocess.CalledProcessError:
            MY_LOGGER.exception('')
            self.reason = 'failed'
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
        if not self.is_slave_player():
            return

        # MY_LOGGER.debug(f'In slave_play phrase: {phrase}'
        # Do we need to kill a stale player?
        if self._player_process is not None:
            # Will stop pending voicings
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('player process running. switching to slave')
            self.destroy_player_process()

        try:
            if self.slave_player_process is None:
                try:
                    args: List[str] = self.get_slave_play_args()
                    self._simple_player_busy = True
                    p_path = self.get_slave_pipe_path()
                    volume: float = self.get_player_volume(as_decibels=False)
                    speed: float = self.get_player_speed()
                    s_num: int = phrase.serial_number
                    #  play_channels: Channels = self.get_player_channels()
                    clz.slave_player_count += 1
                    slave_count: int = clz.slave_player_count
                    self.slave_player_process = SlaveCommunication(args,
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
                    self.slave_player_process.start_service()
                except subprocess.CalledProcessError:
                    MY_LOGGER.exception('')
                    self.reason = 'mpv failed'
                    self.failed = True
                finally:
                    self._time_of_previous_play_ended = datetime.now()
                    self._simple_player_busy = False

        except Exception as e:
            MY_LOGGER.exception('')

        phrase_serial: int = phrase.serial_number
        try:
            phrase.test_expired()  # Throws ExpiredException
            volume: float = self.get_player_volume(as_decibels=False)
            speed: float = self.get_player_speed()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'volume: {volume} speed: {speed}')
            self.slave_player_process.set_channels(Channels.STEREO)
            self.slave_player_process.add_phrase(phrase, volume, speed)
            # MY_LOGGER.debug(f'slave state: {self.slave_player_process.get_state()}')
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

    def isPlaying(self) -> bool:
        self.set_state()
        return self._player_busy

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
        if self.slave_player_process is not None:
            if kill:
                self.destroy_slave_process()
            else:
                self.slave_player_process.stop_player(purge=purge,
                                                      keep_silent=keep_silent,
                                                      kill=kill)
        if self._player_process is not None:
            self.destroy_simple_process(kill=True)

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
        self.destroy_player_process()

    def destroy_player_process(self):
        """
        Destroy the ployer process (ex. mpv, mplayer, etc.). Typicaly done
        when stopping TTS, or when long-running player (one which text_exists for
        multiple voicings) needs to shutdown the process.

        :return:
        """
        self.destroy_slave_process()
        self.destroy_simple_process(kill=True)

    def destroy_slave_process(self):
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'DESTROY_player_process')
        if self.slave_player_process is not None:
            try:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v('DESTROY SLAVE')
                self.player_mode = Settings.get_player_mode(self.engine_key)
                if self.is_slave_player():
                    self.player_mode = None
                self.slave_player_process.destroy()
            except Exception as e:
                MY_LOGGER.exception('')
            self.slave_player_process = None
            return

    def destroy_simple_process(self, kill: bool = True):
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'DESTROY {clz.ID}')
        self._simple_player_busy = False
        if self._player_process is not None:
            if self._player_process.poll() is not None:
                self._player_process = None
                return
            try:
                if kill:
                    self._player_process.kill()
                else:
                    self._player_process.terminate()
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
        clz = type(self)
        if self._player_process is None:
            self._player_busy = False
        elif self._player_process.process.poll() is not None:
            self.rc = self._player_process.process.returncode
            self._player_busy = False
            self._player_process = None
        else:
            #  MY_LOGGER.debug(f'Player busy: {self._player_busy}')
            if (self._player_process is not None and
                    self._player_process.process is not None and
                    self._player_process.process.returncode is not None):
                self.rc = self._player_process.process.returncode
                self._player_busy = False
                self._simple_player_busy = False
                self._player_process = None
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'SimplePlayer busy: {self._simple_player_busy}')
            else:
                self._player_busy = True

    @classmethod
    def available(cls, ext=None) -> bool:
        #  player_id: str = Settings.get_player()
        raise NotImplementedError('base class')
