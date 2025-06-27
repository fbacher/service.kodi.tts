# coding=utf-8
from __future__ import annotations  # For union operator |

#  import json as json
import json
import os
import queue
import socket
import sys
import threading
from pathlib import Path

import xbmc

from common import *
from common.constants import Constants
from common.debug import Debug
from common.exceptions import ExpiredException
from common.garbage_collector import GarbageCollector
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import Channels
from common.simple_run_command import RunState
from common.slave_run_command import SlaveRunCommand

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

MY_LOGGER = BasicLogger.get_logger(__name__)
DEBUG_LOG: bool = MY_LOGGER.isEnabledFor(DEBUG)
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

    The playlist is played in order. Every item in the playlist is
    identified by a monatomic index. The index is used to determine how many
    played and unplayed entries are in the list. Otherwise, TTS does not care about
    the index of individual voicings.
    """

    def __init__(self) -> None:
        self.data: Dict[str, str | int] | None = None

        # Note. mpv does NOT reset any player position indexes when it is stopped
        # (drained). playlist_base_idx gives the index of the first item
        # in the playlist. It is adjusted after every STOP command.
        # NOTE: mpv uses ONE-based indices
        # Initialized to one, even though there are 0 entries. Makes consistent
        # with what happens when a STOP event arrives. It is a bit of a lie, but
        # should do no harm.
        self._first_playlist_entry_idx: int = 1

        # Index of the last item added to playlist.
        self._last_playlist_entry_idx: int = 0

        # All phrases and silent pauses in a PhraseList are added to player's
        # playlist as a group. The phrases in a PhraseList share the same serial number.
        self._current_phrase_serial_num: int = -1
        self._last_played_idx: int = 0
        self._is_idle: bool = False
        # Player Hungry is used to limit how many phrases to fed to the
        # player at a time. Phrases are fed to the player in PhraseList units.
        self._player_hungry: bool = True
        # A count of the characters that have been queued up to play in the
        # current 'batch'of phrases. Some may already have been played, but
        # usually they are fed to the player much faster than they can be played.
        self.chars_queued_to_play: int = 0

    def update_data(self, data: str):
        self.data = json.loads(data)
        #  clz.get.debug(f'data: {data}')
        #  Debug.dump_json('line_out:', data, DEBUG)
        event = self.data.get('event', None)
        mpv_error = self.data.get('error', None)
        reason = self.data.get('reason', None)
        entry_id: int = self.data.get('playlist_entry_id', None)

        # playing_entry
        if event is not None:
            # Event can be one of:
            #  end-file | start_file | idle | file-loaded
            #  start-file | end_file
            if event == 'end-file':
                #  {"event":"end-file","reason":"eof","playlist_entry_id":4}
                if reason == 'eof':
                    # Just finished playing a file
                    self._last_played_idx = entry_id
                    self._is_idle = False
                if reason == 'stop':
                    # After a stop request, mpv clears its playlist
                    # playing_idx does not get reset.
                    self._last_played_idx = self._last_playlist_entry_idx
                    self._first_playlist_entry_idx = self._last_played_idx + 1
                    self._is_idle = True
                if reason == 'quit':
                    # Shutting down player
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug('QUIT')
                    self._is_idle = True
            if event == 'start_file':
                # Starting to play a file
                # {"event":"start-file","playlist_entry_id":17}
                self._last_played_idx = entry_id
                self._is_idle = False
            if event == 'idle':
                self._is_idle = True
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'last_played: {self._last_played_idx}\n'
                            f'last_entry: {self._last_playlist_entry_idx}\n'
                            f'idle: {self._is_idle}')

    def check_play_limits(self) -> bool:
        """
        Determine if an additional PhraseList should be added to the play_list
        or if a different PhraseList should be chosen due to the current one
        being expired.

        :return:
        """
        more_needed: bool = False
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'current_serial#: {self._current_phrase_serial_num} '
                            f'Expired #: {PhraseList.expired_serial_number}')
            MY_LOGGER.debug(f'chars_queued: {self.chars_queued_to_play} '
                            f'remaining: {self.remaining_to_play()}')
        if self._current_phrase_serial_num < PhraseList.expired_serial_number:
            # Dang, expired, Move up to an unexpired one. After return,
            # caller will note expired phrase and start over
            self._current_phrase_serial_num = PhraseList.expired_serial_number + 1
            more_needed = True
        elif (self.chars_queued_to_play < TARGET_PLAYER_CHAR_LIMIT or
                self.remaining_to_play() < MINIMUM_PHRASES_IN_QUEUE):
            #  Add another PhraseList
            self._current_phrase_serial_num += 1
            more_needed = True
        return more_needed

    def first_playlist_entry_idx(self) -> int:
        return self._first_playlist_entry_idx

    def last_played_idx(self) -> int | None:
        return self._last_played_idx

    def remaining_to_play(self) -> int | None:
        """
           Gets the number of remaining sound files to play
           Frequently voice files have pre and/or post silent files
       :return:
       """
        return self._last_playlist_entry_idx - self._last_played_idx

    def is_idle(self) -> bool:
        return self._is_idle

    def is_player_hungry(self) -> bool:
        """
        The player becomes hungry when there are not enough phrases queued to
        keep it  busy.
        :return:
        """
        return self.check_play_limits()

    def is_phraselist_complete(self, phrase: Phrase) -> bool:
        """
        Determines if this phrase is from the same (or earlier) group of phrases
        (PhraseList)  that is allowed to voice.

        CALLER MUST CHECK FOR EXPIRATION OF PHRASE.

        :param phrase:
        :return:
        """
        ok_to_play: bool = phrase.serial_number <= self._current_phrase_serial_num
        if not ok_to_play or phrase.is_expired():
            self.check_play_limits()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'ok_to_play: {ok_to_play}')
        return ok_to_play

    def add_voiced_file(self) -> None:
        self._last_playlist_entry_idx += 1

    def add_pre_pause(self) -> None:
        self._last_playlist_entry_idx += 1

    def add_post_pause(self) -> None:
        self._last_playlist_entry_idx += 1


class SlaveCommunication:
    """

    """

    video_player_state: str = KodiPlayerState.VIDEO_PLAYER_IDLE

    def __init__(self, args: List[str], phrase_serial: int = 0,
                 thread_name: str = 'slav_commo', count: int = 0,
                 stop_on_play: bool = True, fifo_path: Path = None,
                 default_speed: float = 1.0, default_volume: float = 100.0,
                 channels: Channels = Channels.NO_PREF) -> None:
        """

        :param args: arguments to be passed to exec command
        :param phrase_serial: Serial Number of the initial phrase
        :param thread_name: What to name the worker thread
        :param count: Number of instances of Slavecommunication have
                      occurred. Appended to thread names.
        :param stop_on_play: True if voicing is to stop when video is playing
        :param fifo_path: Path to use for FIFO pipe (if available) to
               communicate with mpv command
        :param default_speed: The speed (tempo) which to play the audio, in %
        :param default_volume: Expressed in % to play. 100% is the recorded audio level
        :param channels: The number of audio channels to use for play

        """
        self._player_state: PlayerState = PlayerState()
        if default_volume < 0:  # mplayer interpreted -1 as no-change
            default_volume = 100  # mpv interprets it as 0 (no volume). Set to default

        self.args: List[str] = args
        self.phrase_serial: int = phrase_serial
        self.count = count
        self.thread_name = f'{thread_name}_{count}'

        # Too many state variables

        self.rc = 0
        self.run_state: RunState = RunState.NOT_STARTED
        self.fifo_initialized: bool = False

        # clz.get.debug(f'run_state now NOT_STARTED')
        self.idle_on_play_video: bool = stop_on_play
        # This player is inactive due to Kodi exclusive access (ex: playing movie)
        self.tts_player_idle: bool = False
        self.fifo_in = None    # FIFO output from mpv
        self.socket = None  # Socket output from mpv
        self.fifo_out = None   # FIFO input to mpv
        #  self.socket_out = None  # Socket input to mpv
        self.fifo_reader_thread: threading.Thread | None = None
        self.speak_thread: threading.Thread | None = None
        self.filename_sequence_number: int = 0
        self.playlist_plafying_pos: int = 0
        self.slave: SlaveRunCommand | None = None
        self.default_speed: float = float(default_speed)
        self.current_speed: float = self.default_speed
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

        Monitor.register_abort_listener(self.abort_listener, name=self.thread_name)
        # clz.get.debug(f'Starting slave player args: {args}')
        if self.idle_on_play_video:
            KodiPlayerMonitor.register_player_status_listener(
                    self.kodi_player_status_listener,
                    f'{self.thread_name}_Kodi_Plyr_Mon')
        if not Constants.PLATFORM_WINDOWS:
            try:
                os.mkfifo(fifo_path, mode=0o777)
            except OSError as e:
                MY_LOGGER.exception(f'Failed to create FIFO: {fifo_path}')

        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'Starting SlaveRunCommand args: {args}')
        self.slave = SlaveRunCommand(args, thread_name='slv_run_cmd',
                                     count=count,
                                     post_start_callback=self.create_slave_pipe)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'Back from starting SlaveRunCommand')

    def create_slave_pipe(self) -> bool:
        """
        Call-back function for SlaveRuncommand to initialize pipes at the right time.

        :return:
        """
        clz = type(self)
        Monitor.exception_on_abort(timeout=1.0)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'Slave started, in callback')
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(None)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,
                               LINE_BUFFERING)
        finished: bool = False
        limit: int = 30

        while limit > 0:
            try:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'self.socket.connect path: {self.fifo_path}')
                if Constants.PLATFORM_WINDOWS:
                    # The current Kodi python on Windows does not support fifo/named pipes
                    # Instead, create a Unix socket
                    self.socket = socket.socket(socket.AF_UNIX)
                self.socket.connect(str(self.fifo_path))
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'self.socket Connected')
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
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'RC: {self.rc}')
                    if self.rc == 0:
                        self.run_state = RunState.PIPES_CONNECTED
                        if MY_LOGGER.isEnabledFor(DEBUG_V):
                            MY_LOGGER.debug_v(f'Set run_state PIPES_CONNECTED')
                        self.run_state = RunState.RUNNING
                except AbortException:
                    reraise(*sys.exc_info())
                except:
                    MY_LOGGER.exception('')
                break
            except TimeoutError:
                limit -= 1
            except FileNotFoundError:
                limit -= 1
                if limit == 0:
                    MY_LOGGER.warning(f'FIFO does not exist: '
                                      f'{self.fifo_path}')
            except AbortException:
                self.abort_listener()
                return False
            except Exception as e:
                MY_LOGGER.exception('')
                break
            Monitor.exception_on_abort(timeout=0.1)
        try:
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'unlink {self.fifo_path}')
            self.fifo_path.unlink(missing_ok=True)
            pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        fifo_rdr_thread_name: str = f'{self.thread_name}_fifo_rdr_{self.count}'
        self.fifo_reader_thread = threading.Thread(target=self.fifo_reader,
                                                   name=fifo_rdr_thread_name)
        self.fifo_reader_thread.start()
        GarbageCollector.add_thread(self.fifo_reader_thread)
        xbmc.sleep(250)
        self.send_speed()
        self.send_volume()
        # self.send_opt_channels()
        self.speak_thread = threading.Thread(target=self.process_phrase_queue,
                                             name=f'speak_{self.count}')
        self.speak_thread.start()
        GarbageCollector.add_thread(self.speak_thread)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'Returning from create_slave_pipes')
        return True

    def add_phrase(self, phrase: Phrase, volume: float = None,
                   speed: float = None) -> None:
        """
        Adds a phrase that needs to be voiced.

        Since:
            1) Phrases can be prepared to be voiced much faster than they are
              voiced
            2) The vocing of phrases is frequently canceled due to 1.
        Phrases are placed into a Queue to be voiced and given to the player
        in hopefully logical chunks or thoughts. The minimum chunk are the
        phrases of a PhraseList, or ~20 phrases (you don't want the player to
        starve).

        When 'stop_player' is called, the queue will be drained. The
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
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'phrase serial: {phrase.serial_number} '
                                f'{phrase.short_text()}')
            if Monitor.abort_requested():
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(F'ABORT_REQUESTED')
                self.empty_queue()
                return

            # Ignore while kodi owns audio
            interrupted_str: str = ''
            if phrase.interrupt:
                interrupted_str = 'INTERRUPT'
            expired_check_str: str = ''
            if phrase.check_expired:
                #  MY_LOGGER.debug(f'check_expired is enabled')
                expired_check_str = 'CHECK'
                if phrase.is_expired():
                    expired_check_str = f'{expired_check_str} EXPIRED'
            else:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'check_expired is NOT enabled')

            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'FIFO-ish {phrase.short_text()} '
                                  f'# {phrase.serial_number} expired #: '
                                  f'{PhraseList.expired_serial_number}'
                                  f' {expired_check_str} {interrupted_str}')
            if self.tts_player_idle and not phrase.speak_over_kodi:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'player is IDLE')
                return
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'run_state.value: {self.run_state.value}'
                                f' < RUNNING.value: {RunState.RUNNING.value}')
            entry: PhraseQueueEntry = PhraseQueueEntry(phrase, volume, speed)
            self.phrase_queue.put(entry)
        except AbortException:
            reraise(*sys.exc_info())
        except:
            MY_LOGGER.exception('')

    def get_valid_entry(self) -> PhraseQueueEntry | None:
        """
        Returns an unexpired Phrase by first checking for a possibly unused saved
        entry and then the PhraseQueue until either one is found, or it is empty.

        :return: An unexpired Phrase or None
        """
        clz = SlaveCommunication
        entry: PhraseQueueEntry = self._previous_entry
        idle_counter: int = 0
        while entry is None or entry.phrase.is_expired():
            try:
                idle_counter += 1
                if entry is not None and entry.phrase.is_expired():
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'EXPIRED: {entry.phrase.short_text()}')
                entry = self.phrase_queue.get_nowait()
                self._previous_entry = entry
            except queue.Empty:
                self._previous_entry = None
                return None
            if idle_counter == 1000:
                MY_LOGGER.ERROR('idle counter is crazy')
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
                    if (not self._player_state.is_player_hungry() and
                            self._player_state.is_phraselist_complete(entry.phrase)):
                        if MY_LOGGER.isEnabledFor(DEBUG_V):
                            MY_LOGGER.debug_v(f'Not hungry')
                        # Usable or None  phrase kept in self._previous_entry
                        continue
                    self.play_phrase(entry.phrase, entry.volume, entry.speed)
                    entry = None
                    self._previous_entry = entry
                except queue.Empty:
                    pass
        except AbortException:
            return
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('process_phrase_queue exiting')

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
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'FIFO-ish {phrase.short_text()} '
                                f'# {phrase.serial_number} expired #: '
                                f'{PhraseList.expired_serial_number}'
                                f' {expired_check_str} {interrupted_str}')
            if self.tts_player_idle and not phrase.speak_over_kodi:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'player is IDLE')
                return
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'run_state.value: {self.run_state.value}'
                                  f' < RUNNING.value: {RunState.RUNNING.value}')
            if Monitor.abort_requested():
                return
            suffix: str
            suffix = 'append-play'
            clz._is_idle = False
            if phrase.get_pre_pause() != 0:
                pre_silence_path: Path = phrase.pre_pause_path()
                self.send_line(f'loadfile {str(pre_silence_path)} {suffix}',
                               pre_pause=True)
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug(f'LOADFILE pre_silence {phrase.get_pre_pause()} ms' )

            if speed != self.current_speed:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'speed: {speed} current: {self.current_speed}')
                self.set_next_speed(speed)   # Speed, Volume is reset to initial values on each
            #  else:
            #      self.set_next_speed(speed)  # HACK ALWAYS set unless defaults changed
            if volume != self.default_volume:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'volume: {volume} default: {self.default_volume}')
                self.set_next_volume(volume)  # file played
           #   else:
           #       self.set_next_volume(volume)  # HACK ALWAYS send volume or change defaults
            self.send_line(f'loadfile {str(phrase.get_cache_path())} {suffix}',
                           voiced=True)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'LOADFILE {phrase.short_text(max_len=60)}')

            if phrase.get_post_pause() != 0 and phrase.post_pause_path() is not None:
                post_silence_path: Path = phrase.post_pause_path()
                self.send_line(f'loadfile {str(post_silence_path)} {suffix}',
                               post_pause=True)
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'LOADFILE post_silence {phrase.get_post_pause()}'
                                      f' ms' )
        except ExpiredException:
            pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

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
            self.current_speed = self.next_speed
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
        try:
            if kill:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'STOP KILL')
                quit_str: str = f'quit'
                self.run_state = RunState.DIE
                self.send_line(quit_str)
                Monitor.wait_for_abort(0.05)
                # self.slave.terminate()
                self.slave.destroy()
            elif purge:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    go_idle: str = ''
                    if keep_silent:
                        go_idle = 'GO IDLE'
                    MY_LOGGER.debug(f'STOP, PURGE {go_idle}')
                stop_str: str = f'stop'
                self.send_line(stop_str)
                self.current_speed = None
                self.next_speed = self.default_speed
                if keep_silent:
                    self.tts_player_idle = True
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

    def resume_voicing(self) -> None:
        clz = SlaveCommunication
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v('RESUME')
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
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'FIFO_OUT: {text}| last_played_idx: '
                                      f'{self._player_state.last_played_idx()} '
                                      f'delta: {self._player_state.remaining_to_play()} '
                                      'transaction # : '
                                      f'{self.latest_config_transaction_num}')
                self.fifo_out.write(f'{text}\n')
                self.fifo_out.flush()
                if pre_pause:
                    self._player_state.add_pre_pause()
                elif voiced:
                    self._player_state.add_voiced_file()
                elif post_pause:
                    self._player_state.add_post_pause()
                #  MY_LOGGER.debug(f'FLUSHED')
        except AbortException:
            reraise(*sys.exc_info())
        except BrokenPipeError:
            if self.run_state > RunState.RUNNING:
                pass
            else:
                MY_LOGGER.exception('')
        except Exception as e:
            MY_LOGGER.exception('')

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
        engines, etc.

        :return:
        """
        clz = type(self)
        if DEBUG_LOG:
            xbmc.log(f'In {self.thread_name} destroy', xbmc.LOGDEBUG)

        self.stop_player(kill=True)
        xbmc.sleep(10)

        self.close_slave_files()

    def close_slave_files(self) -> None:
        """
        Shut down files with slave. SlaveRunCommand.stop_player(kill) will cause
        it to close the process files, which will kill the player.

        :return:
        """
        #  NOTE: it is the job of SlaveRunCommand to
        #  die on abort. Doing so here ends up causing the
        # thread killer try to kill it twice, which hangs.
        # Will address that problem later
        try:
            self.run_state = RunState.DIE
            # Close the INPUT to slave first.
            if self.fifo_out is not None:
                try:
                    self.fifo_out.close()
                except:
                    pass
                try:
                    self.fifo_in.close()
                except:
                    pass
                try:
                    self.socket.shutdown()
                except:
                    pass
                try:
                    self.socket.close()
                except:
                    pass
                self.fifo_out = None
                self.fifo_in = None
                self.slave.destroy()
        except Exception as e:
            MY_LOGGER.exception('')

    def kodi_player_status_listener(self, video_player_state: KodiPlayerState) -> bool:
        clz = type(self)
        clz.video_player_state = video_player_state
        # clz.get.debug(f'PlayerStatus: {video_player_state} idle_tts_player: '
        #                  f'{self.idle_tts_player} args: {self.args} '
        #                 f'serial: {self.phrase_serial}')
        if self.idle_on_play_video:
            if video_player_state == KodiPlayerState.PLAYING_VIDEO:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug('STOP playing TTS while Kodi player active')
                self.stop_player(purge=True, keep_silent=True)
            elif video_player_state != KodiPlayerState.PLAYING_VIDEO:
                self.resume_voicing()  # Resume playing TTS content
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug('Start playing TTS (Kodi not playing)')
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
                if finished or self.run_state.value > RunState.RUNNING.value:
                    break
                line: str = ''
                try:
                    line = self.fifo_in.readline()
                    if len(line) > 0:
                        self.fifo_initialized = True
                        if MY_LOGGER.isEnabledFor(DEBUG_V):
                            MY_LOGGER.debug_v(f'FIFO_IN: {line}')
                except ValueError as e:
                    rc = self.slave.rc
                    if rc is not None:
                        self.rc = rc
                        # Command complete
                        finished = True
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'mpv process ended')
                        break
                    else:
                        MY_LOGGER.exception('')
                        finished = True
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    MY_LOGGER.exception('')
                    finished = True
                    line: str = ''
                try:
                    if line and len(line) > 0:
                        self._player_state.update_data(line)
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    MY_LOGGER.exception('')

        except AbortException as e:
            self.destroy()
            return
        except Exception as e:
            MY_LOGGER.exception('')
        # Any way that we exit, we are done, done, done
        self.destroy()
