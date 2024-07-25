# coding=utf-8
from __future__ import annotations  # For union operator |

#  import simplejson as json
import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path
from subprocess import Popen

import xbmc

from common import *
from common.constants import Constants

from common.debug import Debug
from common.garbage_collector import GarbageCollector
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase
from common.setting_constants import Channels
from common.simple_run_command import RunState
from common.slave_run_command import SlaveRunCommand
from common.utils import sleep

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SlaveCommunication:
    """

    """

    video_player_state: str = KodiPlayerState.VIDEO_PLAYER_IDLE
    logger: BasicLogger = None

    def __init__(self, args: List[str], phrase_serial: int = 0, thread_name: str = '',
                 stop_on_play: bool = True, slave_pipe_path: Path = None,
                 speed: float = 1.0, volume: float = 100.0,
                 channels: Channels = Channels.NO_PREF) -> None:
        """

        :param args: arguments to be passed to exec command
        :param phrase_serial: Serial Number of the initial phrase
        :param thread_name: What to name the worker thread
        :param stop_on_play: True if voicing is to stop when video is playing
        :param slave_pipe_path: Path to use for FIFO pipe (if available) to
               communicate with mpv command
        :param speed: The speed (tempo) which to play the audio, in %
        :param volume: Expressed in % to play. 100% is the recorded audio level
        :param channels: The number of audio channels to use for play

        """
        clz = type(self)
        SlaveCommunication.logger = module_logger.getChild(clz.__name__)
        if volume < 0:  # mplayer interpreted -1 as no-change
            volume = 100  # mpv interprets it as 0 (no volume). Set to default

        self.args: List[str] = args
        self.phrase_serial: int = phrase_serial
        self.thread_name = thread_name
        self.rc = 0
        self.run_state: RunState = RunState.NOT_STARTED
        clz.logger.debug(f'run_state now NOT_STARTED')
        self.idle_on_play_video: bool = stop_on_play
        # This player is inactive due to Kodi exclusive access (ex: playing movie)
        self.tts_player_idle: bool = False
        self.cmd_finished: bool = False
        self.fifo_in = None
        self.fifo_out = None
        self.fifo_initialized: bool = False
        self.fifo_reader_thread: threading.Thread | None = None
        self.filename_sequence_number: int = 0
        self.playlist_playing_pos: int = 0
        self.slave: SlaveRunCommand | None = None
        self.speed: float = speed
        self.fifo_sequence_number: int = 0
        self.observer_sequence_number: int = 0
        self.slave_pipe_path: Path = slave_pipe_path
        self.volume: float = volume
        self.channels: Channels = channels
        self.play_count: int = 0

        Monitor.register_abort_listener(self.abort_listener, name=thread_name)
        clz.logger.debug(f'Starting slave player args: {args}')
        if self.idle_on_play_video:
            KodiPlayerMonitor.register_player_status_listener(
                    self.kodi_player_status_listener,
                    f'{self.thread_name}_Kodi_Player_Monitor')
        try:
            os.mkfifo(slave_pipe_path, mode=0o777)
        except OSError as e:
            clz.logger.exception(f'Failed to create FIFO: {slave_pipe_path}')

        clz.logger.debug(f'Starting SlaveRunCommand')
        self.slave = SlaveRunCommand(args, thread_name='name',
                                     post_start_callback=self.create_slave_pipe)
        clz.logger.debug(f'Returned from SlaveRunCommand')

    def create_slave_pipe(self) -> bool:
        clz = type(self)
        Monitor.exception_on_abort(timeout=1.0)

        # fifo_file_in = os.open(self.slave_pipe_path, os.O_RDONLY | os.O_NONBLOCK)
        # fifo_file_out = os.open(self.slave_pipe_path, os.O_WRONLY)

        clz.logger.debug(f'Slave started, in callback')
        fifo_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        fifo_sock.settimeout(0.0)
        finished: bool = False
        limit: int = 30

        while limit > 0:
            try:
                clz.logger.debug(f'fifo_sock.connect path: {self.slave_pipe_path}')
                fifo_sock.connect(str(self.slave_pipe_path))
                clz.logger.debug(f'Connected')
                break
            except TimeoutError:
                limit -= 1
            except FileNotFoundError:
                limit -= 1
                if limit == 0:
                    clz.logger.warning(f'FIFO does not exist: '
                                       f'{self.slave_pipe_path}')
            except AbortException:
                self.abort_listener()
                return False
            except Exception as e:
                clz.logger.exception('')
                break
            Monitor.exception_on_abort(timeout=0.1)
        try:
            clz.logger.debug(f'Unlinking {self.slave_pipe_path}')
            self.slave_pipe_path.unlink(missing_ok=True)
            pass
        except Exception as e:
            self.logger.exception('')

        self.fifo_in = fifo_sock.makefile(mode='r', buffering=1,
                                          encoding='utf-8', errors=None,
                                          newline=None)
        self.fifo_out = fifo_sock.makefile(mode='w', buffering=1,
                                           encoding='utf-8', errors=None,
                                           newline=None)
        self.fifo_reader_thread = threading.Thread(target=self.fifo_reader,
                                                   name=f'{self.thread_name}_fifo_reader')
        self.fifo_reader_thread.start()
        xbmc.sleep(250)
        self.send_speed()
        self.send_volume()
        # self.send_opt_channels()
        return True

    def add_phrase(self, phrase: Phrase, volume: float = None,
                   speed: float = None) -> None:
        clz = type(self)
        try:
            # Ignore while kodi owns audio
            if self.tts_player_idle and not phrase.speak_over_kodi:
                clz.logger.debug(f'player is idle')
                return
            clz.logger.debug(f'run_state.value: {self.run_state.value}'
                             f' < RUNNING.value: {RunState.RUNNING.value}')
            if (self.run_state.value < RunState.RUNNING.value
                    and self.fifo_out is None):
                #
                # Open FIFO for write AFTER starting reader (mpv). Otherwise,
                # open will block until there is a writer.
                try:
                    slave_pipe_name = self.slave_pipe_path
                except Exception as e:
                    clz.logger.exception('')
                    return
            suffix: str
            suffix = 'append-play'
            self.play_count += 1
            pre_silence_path: Path = phrase.get_pre_pause_path()
            if pre_silence_path is not None:
                self.send_line(f'loadfile {str(pre_silence_path)} {suffix}')

            self.set_speed(speed)   # Speed, Volume is reset to initial values on each
            self.set_volume(volume)  # file played
            self.send_line(f'loadfile {str(phrase.get_cache_path())} {suffix}')
            post_silence_path: Path = phrase.get_post_pause_path()
            if post_silence_path is not None:
                self.send_line(f'loadfile {str(post_silence_path)} {suffix}')

        except Exception as e:
            clz.logger.exception('')
        # clz.logger.debug(f'Exiting add_phrase: {phrase}')

    def set_speed(self, speed: float):
        self.speed = speed
        self.send_speed()

    def set_volume(self, volume: float):
        if volume == -1:
            volume = 100
        self.volume = volume
        # self.logger.debug(f'Sending FIFO volume {volume} to player')
        self.send_volume()

    def set_channels(self, channels: Channels):
        self.channels = channels
        self.send_opt_channels()

    def send_speed(self) -> None:
        self.fifo_sequence_number += 1
        speed_str: str = (f'{{ "command": ["set_property", '
                          f'"speed", {self.speed}], "request_id": '
                          f'"{self.fifo_sequence_number}" }}')
        self.send_line(speed_str)

    def send_volume(self) -> None:
        """
        Sets the volume for the next played file. Note that the scale is in
        percent. 100% is the original volume of file.
        :return:
        """
        self.fifo_sequence_number += 1
        volume_str: str = (f'{{ "command": ["set_property", "volume", {self.volume}],'
                           f' "request_id": "{self.fifo_sequence_number}" }}')
        self.send_line(volume_str)

    def send_opt_channels(self) -> None:
        return

        self.fifo_sequence_number += 1
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
                                     f' "request_id": "{self.fifo_sequence_number}" }}')
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
            clz.logger.debug(f'purge: {purge} future: {future}')
            if future:
                self.tts_player_idle = True
            if purge:
                stop_str: str = f'stop'
                self.send_line(stop_str)
        except Exception as e:
            clz.logger.exception('')

    def resume_voicing(self) -> None:
        self.tts_player_idle = False

    def config_observers(self) -> None:
        self.fifo_sequence_number += 1
        self.observer_sequence_number += 1
        observer_str: str
        observer_str = (f'{{ "command": ["observe_property_string", '
                        f'{self.observer_sequence_number}, "filename"], '
                        f'"request_id": '
                        f'"{self.fifo_sequence_number}" }}')
        self.fifo_sequence_number += 1
        self.observer_sequence_number += 1
        self.send_line(observer_str)
        observer_str = (f'{{"command": ["observe_property_string", '
                        f'{self.observer_sequence_number}, "playlist_playing_pos"], '
                        f'"request_id": '
                        f'"{self.fifo_sequence_number}" }}')
        # self.playlist_playing_pos = self.fifo_sequence_number
        self.send_line(observer_str)

    def send_line(self, text: str) -> None:
        clz = type(self)
        try:
            if self.fifo_out is not None:
                # if clz.logger.isEnabledFor(DEBUG):
                #     clz.logger.debug(f'FIFO_OUT: {text}')
                self.fifo_out.write(f'{text}\n')
                self.fifo_out.flush()
        except Exception as e:
            clz.logger.exception('')

    def terminate(self):
        if self.slave is not None and self.run_state.value <= RunState.RUNNING.value:
            self.slave.terminate()
        clz = type(self)
        clz.logger.debug(f'terminate')

    def kill(self):
        pass

    def get_state(self) -> RunState:
        return self.run_state

    def abort_listener(self) -> None:
        # Shut down mpv
        self.destroy()

    def destroy(self):
        """
        Destroy this player and any dependent player process, etc. Typicaly done
        when either stopping TTS (F12) or shutdown, or switching players,
        players, etc.

        :return:
        """
        clz = type(self)
        clz.logger.debug(f'In destroy')
        if self.cmd_finished:
            return
        try:
            # quit[<keep-playlist>]
            code: str = '0'
            quit_str: str = f'quit {code}'
            self.send_line(quit_str)
            self.slave.destroy()
        except Exception as e:
            clz.logger.exception('')

        try:
            self.cmd_finished = True
            if self.fifo_in is not None:
                try:
                    self.fifo_in.close()
                except:
                    pass
                self.fifo_in = None
            if self.fifo_out is not None:
                try:
                    self.fifo_out.close()
                except:
                    pass
                self.fifo_out = None
        except Exception as e:
            clz.logger.exception('')

    def kodi_player_status_listener(self, video_player_state: KodiPlayerState) -> bool:
        clz = type(self)
        clz.video_player_state = video_player_state
        # clz.logger.debug(f'PlayerStatus: {video_player_state} idle_tts_player: '
        #                  f'{self.idle_tts_player} args: {self.args} '
        #                 f'serial: {self.phrase_serial}')
        if self.idle_on_play_video:
            if video_player_state == KodiPlayerState.PLAYING_VIDEO:
                clz.logger.debug(f'Stop playing TTS while Kodi player active')
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

    def run_service(self) -> None:
        clz = type(self)
        try:
            Monitor.exception_on_abort(timeout=1.0)

            # fifo_file_in = os.open(self.slave_pipe_path, os.O_RDONLY | os.O_NONBLOCK)
            # fifo_file_out = os.open(self.slave_pipe_path, os.O_WRONLY)

            fifo_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            fifo_sock.settimeout(0.0)
            finished: bool = False
            limit: int = 30

            success: bool = False
            while limit > 0:
                try:
                    fifo_sock.connect(str(self.slave_pipe_path))
                    # self.logger.debug(f'Socket connected')
                    success = True
                    break
                except TimeoutError:
                    limit -= 1
                except FileNotFoundError:
                    limit -= 1
                    if limit == 0:
                        clz.logger.warning(f'FIFO does not exist: '
                                           f'{self.slave_pipe_path}')
                except AbortException:
                    self.abort_listener()
                    break
                except Exception as e:
                    clz.logger.exception('')
                    break
                Monitor.exception_on_abort(timeout=0.1)
            try:
                # self.slave_pipe_path.unlink(missing_ok=True)
                pass
            except Exception as e:
                self.logger.exception('')

            if not success:
                self.logger.debug(f'Runstate was: {self.run_state}')
                self.run_state = RunState.NOT_STARTED
                self.logger.debug(f'set to NOT_STARTED DEAD')
                return
            self.fifo_in = fifo_sock.makefile(mode='r', buffering=1,
                                              encoding='utf-8', errors=None,
                                              newline=None)
            self.fifo_out = fifo_sock.makefile(mode='w', buffering=1,
                                               encoding='utf-8', errors=None,
                                               newline=None)
            self.fifo_reader_thread = threading.Thread(target=self.fifo_reader,
                                                       name=f'{self.thread_name}_fifo_reader')
            self.fifo_reader_thread.start()
            sleep(0.25)
            self.send_speed()
            self.send_volume()
            self.config_observers()
        except AbortException as e:
            reraise(*sys.exc_info())
        except Exception as e:
            clz.logger.exception('')
            self.rc = 10
        if self.rc == 0:
            self.run_state = RunState.PIPES_CONNECTED
            clz.logger.debug(f'Set run_state PIPES_CONNECTED')
        return

    def fifo_reader(self):
        clz = type(self)
        GarbageCollector.add_thread(self.fifo_reader_thread)
        # if Monitor.is_abort_requested():
        #     self.process.kill()

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
                        if clz.logger.isEnabledFor(DEBUG_VERBOSE):
                            clz.logger.debug_verbose(f'FIFO_IN: {line}')
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
                except Exception as e:
                    clz.logger.exception('')
                    finished = True
                    line: str = ''
                try:
                    '''
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
                     '''
                    if line and len(line) > 0:
                        data: dict = json.loads(line)
                        #  clz.logger.debug(f'data: {data}')

                        #  Debug.dump_json('line_out:', data, DEBUG)
                        mpv_error: str = data.get('error', None)
                        mpv_request_id: int = data.get('request_id', None)
                        event: str = data.get('event')
                        if event:
                            if data.get('reason', None) == 'error':
                                error_reason: str = data.get('file_error', None)
                                if error_reason:
                                    clz.logger.debug(f'Bad audio file. reason:'
                                                     f' {error_reason}')

                            if data.get('id', 0) == self.filename_sequence_number:
                                filename = data.get('data', '')
                            elif data.get('id', 0) == self.playlist_playing_pos:
                                playing_position = data.get('data', 0)
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    clz.logger.exception('')

        except AbortException as e:
            self.cmd_finished = True
            self.fifo_in.close()
            return
        except Exception as e:
            clz.logger.exception('')
            return
