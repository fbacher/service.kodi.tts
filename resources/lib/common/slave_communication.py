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
from common.debug import Debug
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

MINIMUM_PHRASES_IN_QUEUE: Final[int] = 5
AVERAGE_ENGLISH_WORDS_PER_MINUTE: int = 130
AVERAGE_ENGLISH_CHARS_PER_WORD: int = 6  # Five plus Space
TARGET_PLAYER_QUEUED_SECONDS: int = 10
words_per_interval: float = (float(AVERAGE_ENGLISH_WORDS_PER_MINUTE) /
                             float(TARGET_PLAYER_QUEUED_SECONDS))
chars_per_interval: float = words_per_interval * float(AVERAGE_ENGLISH_CHARS_PER_WORD)
# Approx characters to have queued in player to achieve ~ 10 seconds of speech.
TARGET_PLAYER_CHAR_LIMIT: int = int(chars_per_interval + 0.5)


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


class PlayerState:
    """
    The mpv player allows sound files to be queued up into a playlist. To improve
    response time and smooth playing, TTS tries to keep a minimum 10-15 seconds of
    voice queued in the playlist. Having much more in the queue is avoided since
    voicings are frequently canceled by user activity. The playlist is purged
    when a voicing is canceled.

    The playlist is always played in order. Every item in the playlist is
    identified by a montomic index. The index is used to determine how many
    played and unplayed entries in the list. Otherwise, TTS does not care about
    the index of individual voicings.
    """
    logger: BasicLogger = module_logger
    data: Dict[str, str | int] | None = None

    # Note. mpv does NOT reset any player position indexes when it is stopped
    # (drained). playlist_base_idx gives the index of the first item
    # in the playlist. It is adjusted after every STOP command.
    # NOTE: mpv uses ONE-based indices
    # Initialized to one, even though there are 0 entries. Makes consistent
    # with what happens when a STOP event arrives. It is a bit of a lie, but
    # should do no harm.
    _first_playlist_entry_idx: int = 1

    # Index of the last item added to playlist.
    _last_playlist_entry_idx: int = 0

    # All phrases and silent pauses in a PhraseList are added to player's
    # playlist as a group. The phrases in a PhraseList share the same serial number.
    _current_phrase_serial_num: int = -1
    _last_played_idx: int = 0
    _is_idle: bool = False
    # Player Hungry is used to limit how many phrases to fed to the
    # player at a time. Phrases are fed to the player in PhraseList units.
    _player_hungry: bool = True
    # A count of the characters that have been queued up to play in the
    # current 'batch'of phrases. Some may already have been played, but
    # usually they are fed to the player much faster than they can be played.
    chars_queued_to_play: int = 0

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
                    # Just finished playing a file
                    cls._last_played_idx = entry_id
                    cls._is_idle = False
                if reason == 'stop':
                    # After a stop request, mpv clears its playlist
                    # playing_idx does not get reset.
                    cls._last_played_idx = cls._last_playlist_entry_idx
                    cls._first_playlist_entry_idx = cls._last_played_idx + 1
                    cls._is_idle = True
                if reason == 'quit':
                    # Shutting down player
                    cls.logger.debug(f'QUIT')
                    cls._is_idle = True
            if event == 'start_file':
                # Starting to play a file
                # {"event":"start-file","playlist_entry_id":17}
                cls._last_played_idx = entry_id
                cls._is_idle = False
            if event == 'idle':
                cls._is_idle = True
        cls.logger.debug(f'last_played: {cls._last_played_idx}\n'
                         f'last_entry: {cls._last_playlist_entry_idx}\n'
                         f'idle: {cls._is_idle}')

    @classmethod
    def check_play_limits(cls) -> bool:
        """
        Determine if an additional PhraseList should be added to the play_list
        or if a different PhraseList should be chosen due to the current one
        being expired.

        :return:
        """
        more_needed: bool = False
        cls.logger.debug(f'current_serial#: {cls._current_phrase_serial_num} '
                         f'Expired #: {PhraseList.expired_serial_number}')
        cls.logger.debug(f'chars_queued: {cls.chars_queued_to_play} '
                         f'remaining: {cls.remaining_to_play()}')
        if cls._current_phrase_serial_num < PhraseList.expired_serial_number:
            # Dang, expired, Move up to an unexpired one. After return,
            # caller will note expired phrase and start over
            cls.current_phrase_serial_num = PhraseList.expired_serial_number + 1
            more_needed = True
        elif (cls.chars_queued_to_play < TARGET_PLAYER_CHAR_LIMIT or
                cls.remaining_to_play() < MINIMUM_PHRASES_IN_QUEUE):
            #  Add another PhraseList
            cls._current_phrase_serial_num += 1
            more_needed = True
        return more_needed

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
    def first_playlist_entry_idx(cls) -> int:
        return cls._first_playlist_entry_idx

    @classmethod
    def last_played_idx(cls) -> int | None:
        return cls._last_played_idx

    @classmethod
    def remaining_to_play(cls) -> int | None:
        """
           Gets the number of remaining sound files to play
           Frequently voice files have pre and/or post silent files
       :return:
       """
        return cls._last_playlist_entry_idx - cls._last_played_idx

    @classmethod
    def is_idle(cls) -> bool:
        return cls._is_idle

    @classmethod
    def is_player_hungry(cls) -> bool:
        """
        The player becomes hungry when there are not enough phrases queued to
        keep it  busy.
        :return:
        """
        return cls.check_play_limits()

    @classmethod
    def is_phraselist_complete(cls, phrase: Phrase) -> bool:
        """
        Determines if this phrase is from the same (or earlier) group of phrases
        (PhraseList)  that is allowed to voice.

        CALLER MUST CHECK FOR EXPIRATION OF PHRASE.

        :param phrase:
        :return:
        """
        ok_to_play: bool = phrase.serial_number <= cls._current_phrase_serial_num
        if not ok_to_play or phrase.is_expired():
            cls.check_play_limits()
            cls.logger.debug(f'ok_to_play: {ok_to_play}')
        return ok_to_play

    @classmethod
    def add_voiced_file(cls) -> None:
        cls._last_playlist_entry_idx += 1

    @classmethod
    def add_pre_pause(cls) -> None:
        cls._last_playlist_entry_idx += 1

    @classmethod
    def add_post_pause(cls) -> None:
        cls._last_playlist_entry_idx += 1


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
        self.socket = None  # Socket output from mpv
        self.fifo_out = None   # FIFO input to mpv
        #  self.socket_out = None  # Socket input to mpv
        self.fifo_initialized: bool = False
        self.fifo_reader_thread: threading.Thread | None = None
        self.speak_thread: threading.Thread | None = None
        self.filename_sequence_number: int = 0
        self.playlist_playing_pos: int = 0
        self.slave: SlaveRunCommand | None = None
        self.default_speed: float = float(default_speed)
        self.next_speed: float | None = None
        self.fifo_path: Path = fifo_path
        self.default_volume: float = float(default_volume)
        self.next_volume: float | None = None
        self.channels: Channels = channels
        self.phrase_queue: queue.Queue = queue.Queue(maxsize=200)
        self.previous_phrase_serial_num: int = -1
        # Request id of most recent config/option transaction sent to mpv
        self.latest_config_transaction_num: int = 0
        self.observer_sequence_number: int = 0
        # Request_id of most recent completed item from mpv
        self._previous_entry: PhraseQueueEntry | None = None

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
        if clz.logger.isEnabledFor(DEBUG_V):
            clz.logger.debug_v(f'Slave started, in callback')
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(None)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,
                               LINE_BUFFERING)
        finished: bool = False
        limit: int = 30

        while limit > 0:
            try:
                if clz.logger.isEnabledFor(DEBUG_V):
                    clz.logger.debug_v(f'self.socket.connect path: {self.fifo_path}')
                self.socket.connect(str(self.fifo_path))
                if clz.logger.isEnabledFor(DEBUG_V):
                    clz.logger.debug_v(f'self.socket Connected')
                try:
                    self.fifo_out = self.socket.makefile(mode='w',
                                                         buffering=LINE_BUFFERING,
                                                         encoding='utf-8',
                                                         errors=None,
                                                         newline=None)
                    self.fifo_in = self.socket.makefile(mode='r',
                                                        buffering=LINE_BUFFERING,
                                                        encoding='utf-8', errors=None,
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
        self.fifo_reader_thread = threading.Thread(target=self.fifo_reader,
                                                   name=f'{self.thread_name}_fifo_rdr')
        self.fifo_reader_thread.start()
        GarbageCollector.add_thread(self.fifo_reader_thread)
        xbmc.sleep(250)
        self.send_speed()
        self.send_volume()
        # self.send_opt_channels()
        self.speak_thread = threading.Thread(target=self.process_phrase_queue,
                                             name='speak')
        self.speak_thread.start()
        GarbageCollector.add_thread(self.speak_thread)
        clz.logger.debug(f'Returning from create_slave_pipes')
        return True

    def add_phrase(self, phrase: Phrase, volume: float = None,
                   speed: float = None) -> None:
        """
        Adds a phrase that needs to be voiced.

        Since:
            1) Phrases can be prepared to be voiced much faster than they are
              voiced
            2) The vocing of phrases is frequently canceled due to 1.
        Pharses are placed into a Queue to be voiced and given to the player
        in hopefully logical chunks or thoughts. The minimum chunk are the
        phrases of a PhraseList, or ~20 phrases (you don't want the player to
        starve).

        When an 'abort_voicing' is received, the queue will be drained. The
        player most likely will also be cleared. Voicing will proceed with the
        newest phrases.

        :param phrase:
        :param volume:
        :param speed:
        :return:
        """

        """
           Discard any incoming phrases which are expired.
           The remaining are put into the queue. Let receiver of queue entries
           decide what to do with them.            
        """
        clz = type(self)
        try:
            speed = float(speed)
            volume = float(volume)
            clz._current_phrase_serial_num = phrase.serial_number
            clz.logger.debug(f'phrase serial: {phrase.serial_number} '
                             f'{phrase.get_short_text()}')
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
                clz.logger.debug(f'check_expired is enabled')
                expired_check_str = 'CHECK'
                if phrase.is_expired():
                    expired_check_str = f'{expired_check_str} EXPIRED'
            else:
                clz.logger.debug(f'check_expired is NOT enabled')

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

    def get_valid_entry(self) -> PhraseQueueEntry | None:
        """
        Returns an unexpired Phrase by first checking for a possibly unused saved
        entry and then the PhraseQueue until either one is found, or it is empty.

        :return: An unexpired Phrase or None
        """
        clz = SlaveCommunication
        entry: PhraseQueueEntry = self._previous_entry
        while entry is None or entry.phrase.is_expired():
            try:
                if entry is not None and entry.phrase.is_expired():
                    clz.logger.debug(f'EXPIRED: {entry.phrase.get_short_text()}')
                entry = self.phrase_queue.get_nowait()
                self._previous_entry = entry
            except queue.Empty:
                self._previous_entry = None
                return None
        return entry

    def process_phrase_queue(self):
        """
        Thread to dispatch phrases to mpv from the phrase_queue.
        Also discards expired or interrupted phrases.
        Regulates the rate which phrases are fed to mpv so that not too many are
        stacked in mpv's queue causing it to become non-responsive.

        :return:
        """
        clz = SlaveCommunication
        try:
            while not Monitor.exception_on_abort(0.1):
                try:
                    #  If there is no previous entry, or if it is expired,
                    # then get another one.
                    entry: PhraseQueueEntry | None = self.get_valid_entry()
                    if entry is None:
                        continue
                    # Now that there is a usable entry, see if it is needed
                    # or if we should wait until the player needs it.
                    # Keep PhraseLists together.
                    if (not PlayerState.is_player_hungry() and
                            PlayerState.is_phraselist_complete(entry.phrase)):
                        clz.logger.debug(f'Not hungry')
                        # Usable or None  phrase kept in self._previous_entry
                        continue
                    self.play_phrase(entry.phrase, entry.volume, entry.speed)
                    entry = None
                    self._previous_entry = entry
                except queue.Empty:
                    pass
        except AbortException:
            return
        clz.logger.debug('process_phrase_queue exiting')

    def empty_queue(self) -> None:
        """
        Drains the phrase_queue. Called when voiced text has expired.
        :param self:
        """
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
            clz._is_idle = False
            if phrase.get_pre_pause() != 0:
                pre_silence_path: Path = phrase.get_pre_pause_path()
                if pre_silence_path.suffix == '.mp3':
                    self.send_line(f'loadfile {str(pre_silence_path)} {suffix}',
                                   pre_pause=True)
                    clz.logger.debug(f'LOADFILE pre_silence {phrase.get_pre_pause()} ms' )

            if speed != self.default_speed:
                clz.logger.debug(f'speed: {speed} default:'
                                 f' {self.default_speed}')
                self.set_next_speed(speed)   # Speed, Volume is reset to initial values on each
            #  else:
            #      self.set_next_speed(speed)  # HACK ALWAYS set unless defaults changed
            if volume != self.default_volume:
                self.logger.debug(f'volume: {volume} default: {self.default_volume}')
                self.set_next_volume(volume)  # file played
           #   else:
           #       self.set_next_volume(volume)  # HACK ALWAYS send volume or change defaults
            self.send_line(f'loadfile {str(phrase.get_cache_path())} {suffix}',
                           voiced=True)
            clz.logger.debug(f'LOADFILE {phrase.get_short_text()}')

            if phrase.get_post_pause() != 0:
                post_silence_path: Path = phrase.get_post_pause_path()
                if post_silence_path.suffix == '.mp3':
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
            self.latest_config_transaction_num += 1
            speed_str: str = (f'{{ "command": ["set_property", '
                              f'"speed", {self.next_speed}], "request_id": '
                              f'"{self.latest_config_transaction_num}" }}')
            self.send_line(speed_str)
            self.next_speed = None

    def send_volume(self) -> None:
        """
        Sets the volume for the next played file. Note that the scale is in
        percent. 100% is the original volume of file.
        :return:
        """
        if self.next_volume is not None:
            self.latest_config_transaction_num += 1
            volume_str: str = (f'{{ "command": ["set_property", "volume", {self.next_volume}],'
                               f' "request_id": "{self.latest_config_transaction_num}" }}')
            self.send_line(volume_str)
            self.next_volume = None

    def send_opt_channels(self) -> None:
        return

        '''
        self.latest_config_transaction_num += 1
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
                                     f' "request_id": "{self.latest_config_transaction_num}" }}')
                self.send_line(channels_str)
        '''
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
        self.latest_config_transaction_num += 1
        self.observer_sequence_number += 1
        observer_str: str
        observer_str = (f'{{ "command": ["observe_property_string", '
                        f'{self.observer_sequence_number}, "filename"], '
                        f'"request_id": '
                        f'"{self.latest_config_transaction_num}" }}')
        self.latest_config_transaction_num += 1
        self.observer_sequence_number += 1
        self.send_line(observer_str)
        observer_str = (f'{{"command": ["observe_property_string", '
                        f'{self.observer_sequence_number}, "playlist_playing_pos"], '
                        f'"request_id": '
                        f'"{self.latest_config_transaction_num}" }}')
        # self.playlist_playing_pos = self.latest_config_transaction_num
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
                    clz.logger.debug(f'FIFO_OUT: {text}| last_played_idx: '
                                     f'{PlayerState.last_played_idx()} '
                                     f'delta: {PlayerState.remaining_to_play()} '
                                     'transaction # : '
                                     f'{self.latest_config_transaction_num}')
                self.fifo_out.write(f'{text}\n')
                self.fifo_out.flush()
                if voiced:
                    PlayerState.add_voiced_file()
                elif pre_pause:
                    PlayerState.add_pre_pause()
                elif post_pause:
                    PlayerState.add_post_pause()
                #  clz.logger.debug(f'FLUSHED')
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
                    #  self.socket_out.shutdown()
                    #  self.socket_out.close()
                except:
                    pass
                self.fifo_out = None
                if self.fifo_in is not None:
                    try:
                        self.fifo_in.close()
                        self.socket.shutdown()
                        self.socket.close()
                    except:
                        pass
                    self.fifo_in = None
                    # del self.socket
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
