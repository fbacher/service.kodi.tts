# coding=utf-8
from __future__ import annotations  # For union operator |

#  import simplejson as json
import json
import os
import queue
import socket
import sys
import threading
from pathlib import Path

import xbmc

from common import *
from common.garbage_collector import GarbageCollector
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import Channels
from common.simple_run_command import RunState
from common.slave_run_command import SlaveRunCommand
from common.strenum import StrEnum
from common.utils import sleep

module_logger = BasicLogger.get_logger(__name__)
LINE_BUFFERING: int = 1


class PhraseQueueEntry:
    def __init__(self, phrase: Phrase, volume: float, speed: float):
        self._phrase: Phrase = phrase
        self._volume: float = volume
        self._speed: float = speed
        self.data: Dict[str, str] = {}

    @property
    def phrase(self) -> Phrase:
        return self._phrase

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def speed(self) -> float:
        return self._speed


class AudioType(StrEnum):
    VOICE_FILE = 'voice_file'
    PRE_PAUSE = 'pre_pause'
    POST_PAUSE = 'post_pause'


class PlayerState:
    logger: BasicLogger = module_logger
    data: Dict[str, str | int] | None = None
    _in_player: List[AudioType] = []
    # For our purposes, the current played item is always the first thing to
    # play in the list.
    _current_playing_idx: int | None = 0
    _last_played_idx: int | None = None

    # Number of silent things to play
    _remaining_voiced: int = 0
    _remaining_post_pause: int = 0
    _remaining_pre_pause: int = 0
    _is_idle: bool = False

    @classmethod
    def update_data(cls, data: str):
        cls.data = json.loads(data)
        #  clz.get.debug(f'data: {data}')
        #  Debug.dump_json('line_out:', data, DEBUG)
        event = cls.data.get('event', None)
        mpv_error = cls.data.get('error', None)
        reason = cls.data.get('reason', None)
        entry_id: int = cls.data.get('playlist_entry_id', None)

        # playing_entry
        if event is not None:
            # Event can be one of:
            #  end-file | start_file | idle | file-loaded
            #  start-file | end_file
            if event == 'end-file':
                #  {"event":"end-file","reason":"eof","playlist_entry_id":4}
                if reason == 'eof':
                    #
                    cls._last_played_idx = entry_id
                    cls._current_playing_idx = None  # Unknown
                    cls.remove_played_file(playlist_entry_idx=entry_id)

                    cls._is_idle = False
            if event == 'start_file':
                # {"event":"start-file","playlist_entry_id":17}
                cls._current_playing_idx = entry_id
                cls._is_idle = False
            if event == 'idle':
                cls._is_idle = True
                cls._current_playing_idx = 0
        total_remaining: int = (cls._remaining_voiced +
                                cls._remaining_pre_pause +
                                cls._remaining_post_pause)
        cls.logger.debug(f'current_play_idx: {cls._current_playing_idx}\n'
                         f'last_play_idx: {cls._last_played_idx}\n'
                         f'remaining_voiced: {cls._remaining_voiced}\n'
                         f'pre_pause: {cls._remaining_pre_pause}\n'
                         f'post_pause: {cls._remaining_post_pause}\n'
                         f'tottle_remain: {total_remaining}\n'
                         f'idle: {cls._is_idle}')

        """
             bacher@smeagol$ (cat gonzo2.mpv; echo '{ "command": [
             "observe_property_string", 1, "filename"] }'; echo '{
             "command": ["observe_property_string", 2,
             "playlist_playing_pos"] }'; sleep 60) | socat - ./slave.input
             {"request_id":0,"error":"success"}
             {"request_id":0,"error":"success"}
             {"event":"start-file","playlist_entry_id":2}
             * {"event":"property-change","id":1,"name":"filename",
             "data":"foo.wav"}
             * {"event":"property-change","id":2,"name":"playlist_playing_pos"}
             {"event":"audio-reconfig"}
             {"event":"file-loaded"}
             {"event":"audio-reconfig"}
             {"event":"playback-restart"}
             {"event":"audio-reconfig"}
             {"event":"end-file","reason":"eof","playlist_entry_id":2}
             {"event":"start-file","playlist_entry_id":3}
             {"event":"property-change","id":1,"name":"filename",
             "data":"x.wav"}
             {"event":"audio-reconfig"}
             {"event":"audio-reconfig"}
             {"event":"file-loaded"}
             {"event":"playback-restart"}
             {"event":"audio-reconfig"}
             {"event":"end-file","reason":"eof","playlist_entry_id":3}
             {"event":"start-file","playlist_entry_id":4}
             {"event":"audio-reconfig"}
             {"event":"audio-reconfig"}
             {"event":"file-loaded"}
             {"event":"playback-restart"}
             {"event":"audio-reconfig"}
             {"event":"end-file","reason":"eof","playlist_entry_id":4}
             {"event":"start-file","playlist_entry_id":5}
             {"event":"property-change","id":1,"name":"filename",
             "data":"foo.wav"}
             {"event":"audio-reconfig"}
             {"event":"audio-reconfig"}
             {"event":"file-loaded"}
             {"event":"playback-restart"}
             {"event":"audio-reconfig"}
             {"event":"end-file","reason":"eof","playlist_entry_id":5}
             {"event":"audio-reconfig"}
             {"event":"idle"}
             {"event":"property-change","id":1,"name":"filename"}
        """

    @classmethod
    def playing_idx(cls) -> int | None:
        return cls._current_playing_idx

    @classmethod
    def last_played_idx(cls) -> int | None:
        return cls._last_played_idx

    @classmethod
    def remaining_to_play(cls) -> int | None:
        """
           Gets the number of remaining phrases to play
       :return:
       """
        return cls._remaining

    @classmethod
    def is_idle(cls) -> bool:
        return cls._is_idle

    @classmethod
    def add_voiced_file(cls) -> None:
        cls._remaining_voiced += 1
        cls._in_player.append(AudioType.VOICE_FILE)

    @classmethod
    def add_pre_pause(cls) -> None:
        cls._remaining_pre_pause += 1
        cls._in_player.append(AudioType.PRE_PAUSE)

    @classmethod
    def add_post_pause(cls) -> None:
        cls._remaining_post_pause += 1
        cls._in_player.append(AudioType.POST_PAUSE)

    @classmethod
    def remove_played_file(cls, playlist_entry_idx: int) -> None:
        cls.logger.debug(f'Removing idx: {playlist_entry_idx} from play list')
        # It should remove the entries in order.
        entry_type: AudioType = cls._in_player[0]  #  playlist_entry_idx]
        if entry_type == AudioType.VOICE_FILE:
            cls._remaining_voiced -= 1
        elif entry_type == AudioType.PRE_PAUSE:
            cls._remaining_pre_pause -= 1
        elif entry_type == AudioType.POST_PAUSE:
            cls._remaining_post_pause -= 1
        del cls._in_player[0]


class SlaveCommunication:
    """

    """

    video_player_state: str = KodiPlayerState.VIDEO_PLAYER_IDLE
    logger: BasicLogger = module_logger

    def __init__(self, args: List[str], phrase_serial: int = 0,
                 thread_name: str = 'slav_commo',
                 stop_on_play: bool = True, fifo_path: Path = None,
                 default_speed: float = 1.0, default_volume: float = 100.0,
                 channels: Channels = Channels.NO_PREF) -> None:
        """

        :param args: arguments to be passed to exec command
        :param phrase_serial: Serial Number of the initial phrase
        :param thread_name: What to name the worker thread
        :param stop_on_play: True if voicing is to stop when video is playing
        :param fifo_path: Path to use for FIFO pipe (if available) to
               communicate with mpv command
        :param default_speed: The speed (tempo) which to play the audio, in %
        :param default_volume: Expressed in % to play. 100% is the recorded audio level
        :param channels: The number of audio channels to use for play

        """
        clz = type(self)
        if default_volume < 0:  # mplayer interpreted -1 as no-change
            default_volume = 100  # mpv interprets it as 0 (no volume). Set to default

        self.args: List[str] = args
        self.phrase_serial: int = phrase_serial
        self.thread_name = thread_name
        self.rc = 0
        self.run_state: RunState = RunState.NOT_STARTED
        # clz.get.debug(f'run_state now NOT_STARTED')
        self.idle_on_play_video: bool = stop_on_play
        # This player is inactive due to Kodi exclusive access (ex: playing movie)
        self.tts_player_idle: bool = False
        self.cmd_finished: bool = False
        self.fifo_in = None    # FIFO output from mpv
        self.socket_in = None  # Socket output from mpv
        self.fifo_out = None   # FIFO input to mpv
        self.socket_out = None  # Socket input to mpv
        self.fifo_initialized: bool = False
        self.fifo_reader_thread: threading.Thread | None = None
        self.speak_thread: threading.Thread | None = None
        self.filename_sequence_number: int = 0
        self.playlist_playing_pos: int = 0
        self.slave: SlaveRunCommand | None = None
        self.default_speed: float = default_speed
        self.next_speed: float | None = None
        self.fifo_path: Path = fifo_path
        self.default_volume: float = default_volume
        self.next_volume: float | None = None
        self.channels: Channels = channels
        self.play_count: int = 0
        self.phrase_queue: queue.Queue = queue.Queue(maxsize=200)
        # Request id of most recent item sent to mpv
        self.latest_request_sequence_number: int = 0
        self.observer_sequence_number: int = 0
        # Request_id of most recent completed item from mpv
        self.completed_request_id: int = 0

        Monitor.register_abort_listener(self.abort_listener, name=thread_name)
        # clz.get.debug(f'Starting slave player args: {args}')
        if self.idle_on_play_video:
            KodiPlayerMonitor.register_player_status_listener(
                    self.kodi_player_status_listener,
                    f'{self.thread_name}_Kodi_Player_Monitor')
        try:
            os.mkfifo(fifo_path, mode=0o777)
        except OSError as e:
            clz.logger.exception(f'Failed to create FIFO: {fifo_path}')

        clz.logger.debug(f'Starting SlaveRunCommand args: {args}')
        self.slave = SlaveRunCommand(args, thread_name='slv_run_cmd',
                                     post_start_callback=self.create_slave_pipe)
        clz.logger.debug(f'Back from starting SlaveRunCommand')

    def create_slave_pipe(self) -> bool:
        """
        Call-back function for SlaveRuncommand to initialize pipes at the right time.

        :return:
        """
        clz = type(self)
        Monitor.exception_on_abort(timeout=1.0)

        # fifo_file_in = os.open(self.fifo_path, os.O_RDONLY | os.O_NONBLOCK)
        # fifo_file_out = os.open(self.fifo_path, os.O_WRONLY)

        if clz.logger.isEnabledFor(DEBUG_V):
            clz.logger.debug_v(f'Slave started, in callback')
        self.socket_in = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket_in.settimeout(None)
        self.socket_in.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,
                                  LINE_BUFFERING)
        finished: bool = False
        limit: int = 30

        while limit > 0:
            try:
                if clz.logger.isEnabledFor(DEBUG_V):
                    clz.logger.debug_v(f'self.socket_in.connect path: {self.fifo_path}')
                self.socket_in.connect(str(self.fifo_path))
                if clz.logger.isEnabledFor(DEBUG_V):
                    clz.logger.debug_v(f'socket_in Connected')
                try:
                    self.socket_out = socket.socket(socket.AF_UNIX,
                                                    socket.SOCK_STREAM)
                    self.socket_out.settimeout(None)
                    if clz.logger.isEnabledFor(DEBUG_V):
                        clz.logger.debug_v(
                            f'self.socket_out.connect path: {self.fifo_path}')
                    self.socket_out.connect(str(self.fifo_path))
                    if clz.logger.isEnabledFor(DEBUG_V):
                        clz.logger.debug_v(f'socket_out Connected')
                    self.fifo_out = self.socket_out.makefile(mode='w',
                                                             buffering=LINE_BUFFERING,
                                                             encoding='utf-8',
                                                             errors=None,
                                                             newline=None)
                    clz.logger.debug(f'RC: {self.rc}')
                    if self.rc == 0:
                        self.run_state = RunState.PIPES_CONNECTED
                        clz.logger.debug(f'Set run_state PIPES_CONNECTED')
                        self.run_state = RunState.RUNNING
                except AbortException:
                    reraise(*sys.exc_info())
                except:
                    clz.logger.exception('')
                break
            except TimeoutError:
                limit -= 1
            except FileNotFoundError:
                limit -= 1
                if limit == 0:
                    clz.logger.warning(f'FIFO does not exist: '
                                       f'{self.fifo_path}')
            except AbortException:
                self.abort_listener()
                return False
            except Exception as e:
                clz.logger.exception('')
                break
            Monitor.exception_on_abort(timeout=0.1)
        try:
            if clz.logger.isEnabledFor(DEBUG):
                clz.logger.debug(f'Unlinking {self.fifo_path}')
            self.fifo_path.unlink(missing_ok=True)
            pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            self.logger.exception('')

        self.fifo_in = self.socket_in.makefile(mode='r', buffering=LINE_BUFFERING,
                                               encoding='utf-8', errors=None,
                                               newline=None)
        self.fifo_reader_thread = threading.Thread(target=self.fifo_reader,
                                                   name=f'{self.thread_name}_fifo_rdr')
        self.fifo_reader_thread.start()
        GarbageCollector.add_thread(self.fifo_reader_thread)
        xbmc.sleep(250)
        self.send_speed()
        self.send_volume()
        # self.send_opt_channels()
        self.speak_thread = threading.Thread(target=self.speak, name='speak')
        self.speak_thread.start()
        GarbageCollector.add_thread(self.speak_thread)
        clz.logger.debug(f'Returning from create_slave_pipes')
        return True

    def add_phrase(self, phrase: Phrase, volume: float = None,
                   speed: float = None) -> None:
        clz = type(self)
        try:
            if Monitor.abort_requested():
                clz.logger.debug(F'ABORT_REQUESTED')
                self.empty_queue()
                return
            # Ignore while kodi owns audio
            interrupted_str: str = ''
            if phrase.interrupt:
                interrupted_str = 'INTERRUPT'
            expired_check_str: str = ''
            if phrase.check_expired:
                expired_check_str = 'CHECK'
            clz.logger.debug(f'FIFO-ish {phrase.get_short_text()} '
                             f'# {phrase.serial_number} expired #: '
                             f'{PhraseList.expired_serial_number}'
                             f' {expired_check_str} {interrupted_str}')
            if self.tts_player_idle and not phrase.speak_over_kodi:
                if clz.logger.isEnabledFor(DEBUG):
                    clz.logger.debug(f'player is IDLE')
                return
            if clz.logger.isEnabledFor(DEBUG):
                clz.logger.debug(f'run_state.value: {self.run_state.value}'
                                 f' < RUNNING.value: {RunState.RUNNING.value}')
            entry: PhraseQueueEntry = PhraseQueueEntry(phrase, volume, speed)
            self.phrase_queue.put(entry)
            clz.logger.debug(f'Added entry')
        except AbortException:
            reraise(*sys.exc_info())
        except:
            clz.logger.exception('')

    def speak(self):
        """
        Thread to dispatch phrases to mpv from the phrase_queue.
        Also discards expired or interrupted phrases.
        Regulates the rate which phrases are fed to mpv so that not too many are
        stacked in mpv's queue causing it to become non-responsive.

        :return:
        """
        clz = SlaveCommunication
        clz.logger.debug(f'SPEAK Started')
        try:
            while not Monitor.exception_on_abort(0.1):
                try:
                    entry: PhraseQueueEntry = self.phrase_queue.get_nowait()
                    clz.logger.debug(f'Got phrase')
                    self.play_phrase(entry.phrase, entry.volume, entry.speed)
                except queue.Empty:
                    pass
        except AbortException:
            return
        clz.logger.debug('SPEAK exiting')

    def empty_queue(self) -> None:
        while not self.phrase_queue.empty():
            try:
                self.phrase_queue.get(block=False, timeout=0.01)
            except queue.Empty:
                break

    def play_phrase(self, phrase: Phrase, volume: float | None,
                    speed: float | None) -> None:
        clz = type(self)
        try:
            # Ignore while kodi owns audio
            interrupted_str: str = ''
            if phrase.interrupt:
                interrupted_str = 'INTERRUPT'
            expired_check_str: str = ''
            if phrase.check_expired:
                expired_check_str = 'CHECK'
            clz.logger.debug(f'FIFO-ish {phrase.get_short_text()} '
                             f'# {phrase.serial_number} expired #: '
                             f'{PhraseList.expired_serial_number}'
                             f' {expired_check_str} {interrupted_str}')
            if self.tts_player_idle and not phrase.speak_over_kodi:
                if clz.logger.isEnabledFor(DEBUG):
                    clz.logger.debug(f'player is IDLE')
                return
            if clz.logger.isEnabledFor(DEBUG_V):
                clz.logger.debug_v(f'run_state.value: {self.run_state.value}'
                                   f' < RUNNING.value: {RunState.RUNNING.value}')
            if Monitor.abort_requested():
                return
            suffix: str
            suffix = 'append-play'
            self.play_count += 1
            pre_silence_path: Path = phrase.get_pre_pause_path()
            if pre_silence_path is not None:
                self.send_line(f'loadfile {str(pre_silence_path)} {suffix}',
                               pre_pause=True)
                clz.logger.debug(f'LOADFILE pre_silence {phrase.get_pre_pause()} ms' )

            if speed != self.default_speed:
                self.set_next_speed(speed)   # Speed, Volume is reset to initial values on each
            if volume != self.default_volume:
                self.set_next_volume(volume)  # file played
            self.send_line(f'loadfile {str(phrase.get_cache_path())} {suffix}',
                           voiced=True)
            clz.logger.debug(f'LOADFILE {phrase.get_short_text()}')

            post_silence_path: Path = phrase.get_post_pause_path()
            if post_silence_path is not None:
                self.send_line(f'loadfile {str(post_silence_path)} {suffix}',
                               post_pause=True)
                clz.logger.debug(f'LOADFILE post_silence {phrase.get_post_pause()} ms' )

        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz.logger.exception('')

    def set_next_speed(self, speed: float):
        self.next_speed = speed
        self.send_speed()

    def set_next_volume(self, volume: float):
        if volume == -1:
            volume = 100
        self.next_volume = volume
        # self.get.debug(f'Sending FIFO volume {volume} to player')
        self.send_volume()

    def set_channels(self, channels: Channels):
        self.channels = channels
        self.send_opt_channels()

    def send_speed(self) -> None:
        if self.next_speed is not None:
            self.latest_request_sequence_number += 1
            speed_str: str = (f'{{ "command": ["set_property", '
                              f'"speed", {self.next_speed}], "request_id": '
                              f'"{self.latest_request_sequence_number}" }}')
            self.send_line(speed_str)
            self.next_speed = None

    def send_volume(self) -> None:
        """
        Sets the volume for the next played file. Note that the scale is in
        percent. 100% is the original volume of file.
        :return:
        """
        if self.next_volume is not None:
            self.latest_request_sequence_number += 1
            volume_str: str = (f'{{ "command": ["set_property", "volume", {self.next_volume}],'
                               f' "request_id": "{self.latest_request_sequence_number}" }}')
            self.send_line(volume_str)
            self.next_volume = None

    def send_opt_channels(self) -> None:
        return

        self.latest_request_sequence_number += 1
        if self.channels != Channels.NO_PREF:
            channel_str: str | None = None
            if self.channels == Channels.STEREO:
                channel_str = 'stereo'
            if self.channels == Channels.MONO:
                channel_str = 'mono'
                # --audio-channels=<stereo|mono>
            if channel_str:
                channels_str: str = (f'{{ "af-command": ['
                                     f'"format", "channels", "{channel_str}"],'
                                     f' "request_id": "{self.latest_request_sequence_number}" }}')
                self.send_line(channels_str)

    def abort_voicing(self, purge: bool = True, future: bool = False) -> None:
        """
        Stop voicing pending speech and/or future speech.
        Vocing can be resumed using resume_voicing

        :param purge: if True, then abandon playing all pending speech
        :param future: if True, then ignore future voicings.
        :return: None
        """
        clz = type(self)
        try:
            clz.logger.debug(f'STOP PURGE: {purge} future: {future}')
            if future:
                self.tts_player_idle = True
            if purge:
                stop_str: str = f'stop'
                self.send_line(stop_str)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz.logger.exception('')

    def resume_voicing(self) -> None:
        clz = SlaveCommunication
        clz.logger.debug_v('RESUME')
        self.tts_player_idle = False

    '''
    def config_observers(self) -> None:
        self.latest_request_sequence_number += 1
        self.observer_sequence_number += 1
        observer_str: str
        observer_str = (f'{{ "command": ["observe_property_string", '
                        f'{self.observer_sequence_number}, "filename"], '
                        f'"request_id": '
                        f'"{self.latest_request_sequence_number}" }}')
        self.latest_request_sequence_number += 1
        self.observer_sequence_number += 1
        self.send_line(observer_str)
        observer_str = (f'{{"command": ["observe_property_string", '
                        f'{self.observer_sequence_number}, "playlist_playing_pos"], '
                        f'"request_id": '
                        f'"{self.latest_request_sequence_number}" }}')
        # self.playlist_playing_pos = self.latest_request_sequence_number
        self.send_line(observer_str)
    '''
    
    def send_line(self, text: str, voiced: bool = False,
                  pre_pause: bool = False, post_pause: bool = False) -> None:
        clz = type(self)
        try:
            if self.get_state() != RunState.RUNNING:
                return
            if self.fifo_out is not None:
                if clz.logger.isEnabledFor(DEBUG):
                    delta: int = (self.latest_request_sequence_number -
                                  self.completed_request_id)
                    clz.logger.debug(f'FIFO_OUT: {text}| completed_request_id: '
                                     f'{self.completed_request_id} current: '
                                     f'{self.latest_request_sequence_number} '
                                     f'delta: {delta}')
                self.fifo_out.write(f'{text}\n')
                self.fifo_out.flush()
                if voiced:
                    PlayerState.add_voiced_file()
                elif pre_pause:
                    PlayerState.add_pre_pause()
                elif post_pause:
                    PlayerState.add_post_pause()
                clz.logger.debug(f'FLUSHED')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz.logger.exception('')

    def terminate(self):
        pass

    def kill(self):
        pass

    def get_state(self) -> RunState:
        return self.run_state

    def abort_listener(self) -> None:
        # Shut down mpv
        #  Debug.dump_all_threads()
        self.destroy()
        #  Debug.dump_all_threads()

    def destroy(self):
        """
        Destroy this player and any dependent player process, etc. Typicaly done
        when either stopping TTS (F12) or shutdown, or switching players,
        players, etc.

        :return:
        """
        clz = type(self)
        xbmc.log(f'In destroy', xbmc.LOGDEBUG)
        if self.cmd_finished:
            return
        #  NOTE: it is the job of SlaveRunCommand to
        #  die on abort. Doing so here ends up causing the
        # thread killer try to kill it twice, which hangs.
        # Will address that problem later
        try:
            self.run_state = RunState.COMPLETE
            self.cmd_finished = True
            if self.fifo_out is not None:
                try:
                    self.fifo_out.close()
                    self.socket_out.shutdown()
                    self.socket_out.close()
                    # del self.socket_out
                    # del self.slave
                except:
                    pass
                self.fifo_out = None
                if self.fifo_in is not None:
                    try:
                        self.fifo_in.close()
                        self.socket_in.shutdown()
                        self.socket_in.close()
                    except:
                        pass
                    self.fifo_in = None
                    # del self.socket_in
                #  self.slave.destroy()
        except Exception as e:
            clz.logger.exception('')

    def kodi_player_status_listener(self, video_player_state: KodiPlayerState) -> bool:
        clz = type(self)
        clz.video_player_state = video_player_state
        # clz.get.debug(f'PlayerStatus: {video_player_state} idle_tts_player: '
        #                  f'{self.idle_tts_player} args: {self.args} '
        #                 f'serial: {self.phrase_serial}')
        if self.idle_on_play_video:
            if video_player_state == KodiPlayerState.PLAYING_VIDEO:
                clz.logger.debug(f'STOP playing TTS while Kodi player active')
                self.abort_voicing(purge=True, future=True)
            elif video_player_state != KodiPlayerState.PLAYING_VIDEO:
                self.resume_voicing()  # Resume playing TTS content
                clz.logger.debug(f'Start playing TTS (Kodi not playing)')
        return False  # Don't unregister

    def start_service(self) -> int:
        """

        :return:
        """
        clz = type(self)
        self.slave.start_service()
        return 0

    def fifo_reader(self):
        clz = type(self)
        finished = False
        try:
            while not Monitor.exception_on_abort(timeout=0.1):
                line: str = ''
                try:
                    if finished or self.cmd_finished:
                        break
                    line = self.fifo_in.readline()
                    if len(line) > 0:
                        self.fifo_initialized = True
                        if clz.logger.isEnabledFor(DEBUG):
                            clz.logger.debug(f'FIFO_IN: {line}')
                except ValueError as e:
                    rc = self.slave.rc
                    if rc is not None:
                        self.rc = rc
                        # Command complete
                        finished = True
                        clz.logger.debug(f'mpv process ended')
                        break
                    else:
                        clz.logger.exception('')
                        finished = True
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    clz.logger.exception('')
                    finished = True
                    line: str = ''
                try:

                    if line and len(line) > 0:
                        PlayerState.update_data(line)

                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    clz.logger.exception('')

        except AbortException as e:
            self.destroy()
            return
        except Exception as e:
            clz.logger.exception('')
            return
