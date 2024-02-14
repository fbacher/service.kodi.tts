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
from common.simple_run_command import RunState
from common.utils import sleep

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SlaveRunCommand:
    """

    """
    player_state: str = KodiPlayerState.PLAYING_STOPPED
    logger: BasicLogger = None

    def __init__(self, args: List[str], phrase_serial: int = 0, name: str = '',
                 stop_on_play: bool = True, slave_pipe_path: Path = None,
                 label: str = '',
                 speed: float = 1.0, volume: float = 100.0) -> None:
        """

        :param args: arguments to be passed to exec command
        """
        clz = type(self)
        SlaveRunCommand.logger = module_logger.getChild(clz.__name__)
        if volume < 0:  # mplayer interpreted -1 as no-change
            volume = 100  # mpv interprets it as 0 (no volume). Set to default

        self.args: List[str] = args
        self.phrase_serial: int = phrase_serial
        self.thread_name = name
        self.rc = 0
        self.run_state: RunState = RunState.NOT_STARTED
        self.stop_on_play: bool = stop_on_play
        self.cmd_finished: bool = False
        self._thread: threading.Thread | None = None
        self.fifo_in = None;
        self.fifo_out = None
        self.fifo_initialized: bool = False
        self.fifo_reader_thread: threading.Thread | None = None
        self.filename_sequence_number: int = 0
        self.flip_flop: bool = False
        self.playlist_playing_pos: int = 0
        self.process: Popen | None = None
        self.run_thread: threading.Thread | None = None
        self.speed: float = speed
        self.fifo_sequence_number: int = 0
        self.observer_sequence_number: int = 0
        self.stdout_thread: threading.Thread | None = None
        # self.stderr_thread: threading.Thread | None = None
        self.stdout_lines: List[str] = []
        # self.stderr_lines: List[str] = []
        self.slave_pipe_path: Path = slave_pipe_path
        self.volume: float = volume
        self.play_count: int = 0

        Monitor.register_abort_listener(self.abort_listener, name=name)

        if self.stop_on_play:
            KodiPlayerMonitor.register_player_status_listener(
                    self.kodi_player_status_listener,
                    f'{self.thread_name}_Kodi_Player_Monitor')
        '''            
        try:
            os.mkfifo(slave_pipe_path, mode=0o777)
        except OSError as e:
            clz.logger.exception(f'Failed to create FIFO: {slave_pipe_path}')
        '''

    def add_phrase(self, phrase: Phrase) -> None:
        clz = type(self)
        try:
            if self.fifo_out is None:
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

            self.send_speed()   # Speed, Volume is reset to initial values on each
            self.send_volume()  # file played
            self.send_line(f'loadfile {str(phrase.get_cache_path())} {suffix}')
            post_silence_path: Path = phrase.get_post_pause_path()
            if post_silence_path is not None:
                self.send_line(f'loadfile {str(post_silence_path)} {suffix}')

        except Exception as e:
            clz.logger.exception('')
        clz.logger.debug(f'Exiting add_phrase: {phrase}')

    def set_speed(self, speed: float):
        self.speed = speed
        self.send_speed()

    def set_volume(self, volume: float):
        if volume != -1:
            self.volume = volume
            self.send_volume()

    def send_speed(self) -> None:
        self.fifo_sequence_number += 1
        speed_str: str = (f'{{ "command": ["set_property", '
                          f'"speed", "{self.speed}"], "request_id": '
                          f'"{self.fifo_sequence_number}" }}')
        self.send_line(speed_str)

    def send_volume(self) -> None:
        """
        Sets the volume for the next played file. Note that the scale is in
        percent. 100% is the original volume of file.
        :return:
        """
        self.fifo_sequence_number += 1
        volume_str: str = (f'{{ "command": ["set_property", "volume", "100.0"],'  # "{self.volume}"],'
                           f' "request_id": "{self.fifo_sequence_number}" }}')
        self.send_line(volume_str)

    def stop_playing(self):
        """
        Tell mpv to abort the playing of currently queued files. --q options
        prevents mpv from exiting
        :return:
        """
        clz = type(self)
        try:
            # stop[<flags>]
            stop_str: str = f'stop'
            self.send_line(stop_str)
        except Exception as e:
            clz.logger.exception('')
        clz.logger.debug(f'Stop playing')


    def quit(self, now: bool):
        """
        Quit the player
        :param now: if True, then quit the player immediately
                    if False, then stop accepting items for playlist and quit
                    once playlist is empty
        """
        clz = type(self)
        try:
            # quit[<keep-playlist>]
            code: str = '0'
            quit_str: str = f'quit {code}'
            self.send_line(quit_str)
            self.cmd_finished = True
        except Exception as e:
            clz.logger.exception('')
        clz.logger.debug(f'Quit')

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
                clz.logger.debug(f'FIFO_OUT: {text}')
                self.fifo_out.write(f'{text}\n')
                self.fifo_out.flush()
        except Exception as e:
            clz.logger.exception('')

    def terminate(self):
        if self.process is not None and self.run_state.value <= RunState.RUNNING.value:
            self.process.terminate()
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
        self.quit(now=True)
        self.process.kill()
        if self.fifo_in is not None and self.fifo_in is not None:
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
        try:
            self.process.stdout.close()
            self.process.stdout = None
        except:
            pass
        try:
            pass
            # self.process.stderr.close()
            # self.process.stderr = None
        except:
            pass
        try:
            self.process.stdin.close()
            self.process.stdin = None
        except:
            pass
        self.process.wait(0.5)
        clz.logger.debug('Destroyed')

    def kodi_player_status_listener(self, player_state: KodiPlayerState) -> bool:
        clz = type(self)
        clz.player_state = player_state
        clz.logger.debug(f'PlayerStatus: {player_state} stop_on_play: '
                         f'{self.stop_on_play} args: {self.args} '
                         f'serial: {self.phrase_serial}')
        if player_state == KodiPlayerState.PLAYING and self.stop_on_play:
            clz.logger.debug(f'Stop playing TTS while Kodi player doing something: '
                             f'args: {self.args} ')
            self.stop_playing()
        return False  # Don't unregister

    def start_service(self) -> int:
        """

        :return:
        """
        clz = type(self)
        self.rc = None
        self.run_thread = threading.Thread(target=self.run_service,
                                           name=self.thread_name)
        try:
            Monitor.exception_on_abort()
            self.run_thread.start()
            self.cmd_finished = False
            self.process: Popen
            countdown: bool = False
            kill_countdown: int = 2

            # First, wait until process has started. Should be very quick
            attempts: int = 100  # Approx one second
            while not Monitor.wait_for_abort(timeout=0.01):
                if self.run_state != RunState.NOT_STARTED or attempts < 0:
                    break
                attempts -= 1

        except AbortException:
            # abort_listener will do the kill
            self.rc = 99  # Thread will exit very soon
        finally:
            #  Monitor.unregister_abort_listener(self.abort_listener)
            KodiPlayerMonitor.unregister_player_status_listener(
                    self.kodi_player_status_listener)
        return 0

    '''
            next_state: RunState = RunState.COMPLETE
            while not Monitor.wait_for_abort(timeout=0.1):
                try:
                    # Move on if command finished
                    if self.process.poll() is not None:
                        self.run_state = next_state
                        break
                    # Are we trying to kill it?
                    if (
                            check_serial and self.phrase_serial <
                            PhraseList.expired_serial_number):
                        # Yes, initiate terminate/kill of process
                        check_serial = False
                        countdown = True
                        clz.logger.debug(f'Expired, terminating {self.phrase_serial} '
                                         f'{self.args[0]}',
                                         trace=Trace.TRACE_AUDIO_START_STOP)
                        self.process.terminate()
                        next_state = RunState.TERMINATED
                    if countdown and kill_countdown > 0:
                        kill_countdown -= 1
                    elif kill_countdown == 0:
                        next_state = RunState.KILLED
                        module_logger.debug(f'terminate not work, KILLING')
                        clz.logger.debug(f'Terminate not working, Killing {
                        self.phrase_serial} '
                                         f'{self.args[0]}',
                                         trace=Trace.TRACE_AUDIO_START_STOP)
                        self.process.kill()
                        break
                except subprocess.TimeoutExpired:
                    #  Only indicates the timeout is expired, not the run state
                    pass

            # No matter how process ends, there will be a return code
            while not Monitor.wait_for_abort(timeout=0.1):
                try:
                    rc = self.process.poll()
                    if rc is not None:
                        self.rc = rc
                        self.cmd_finished = True
                        clz.logger.debug(f'FINISHED COMMAND {self.phrase_serial} '
                                         f'{self.args[0]} rc: {rc}',
                                         trace=Trace.TRACE_AUDIO_START_STOP)
                        break  # Complete
                except subprocess.TimeoutExpired:
                    # Only indicates the timeout is expired, not the run state
                    pass

            if not self.cmd_finished:
                # Shutdown in process
                clz.logger.debug(f'SHUTDOWN, START KILL COMMAND {self.phrase_serial} '
                                 f'{self.args[0]}',
                                 trace=Trace.TRACE_SHUTDOWN)
                self.process.kill()  # SIGKILL. Should cause stderr & stdout to exit
                while not Monitor.wait_for_abort(timeout=0.1):
                    try:
                        rc = self.process.poll()
                        if rc is not None:
                            self.rc = rc
                            self.cmd_finished = True
                            clz.logger.debug(f'KILLED COMMAND {self.phrase_serial} '
                                             f'{self.args[0]} rc: {rc}',
                                             trace=Trace.TRACE_AUDIO_START_STOP)
                            break  # Complete
                    except subprocess.TimeoutExpired:
                        pass
                self.rc = 99

            if self.run_thread.is_alive():
                self.run_thread.join(timeout=1.0)
            if self.stdout_thread.is_alive():
                self.stdout_thread.join(timeout=0.2)
            if self.stderr_thread.is_alive():
                self.stderr_thread.join(timeout=0.2)
            Monitor.exception_on_abort(timeout=0.0)
            # If abort did not occur, then process finished

            if self.rc is None or self.rc != 0:
                self.log_output()
        except AbortException:
            self.rc = 99  # Thread will exit very soon
        finally:
            Monitor.unregister_abort_listener(self.abort_listener)
            KodiPlayerMonitor.unregister_player_status_listener(
            self.kodi_player_state_listener)
        return self.rc
    '''

    def poll(self) -> int | None:
        return self.process.poll()

    def run_service(self) -> None:
        clz = type(self)
        self.rc = 0
        GarbageCollector.add_thread(self.run_thread)
        clz.logger.debug(f'run_service started')
        env = os.environ.copy()
        try:
            if xbmc.getCondVisibility('System.Platform.Windows'):
                # Prevent console for mpv from opening
                #
                # Here, we keep stdout & stderr separate and combine the output in the
                # log. Need to change to be configurable: separate, combined at
                # process level (stderr = subprocess.STDOUT), devnull or pass through
                # via pipe and don't log

                clz.logger.debug(f'Cond_Visibility: '
                                 f'{xbmc.getCondVisibility("System.Platform.Windows")} '
                                 f'mpv_path: {Constants.MPV_PATH} '
                                 f'mplayer_path: {Constants.MPLAYER_PATH}')
                self.process = subprocess.Popen(self.args, stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, shell=False,
                                                universal_newlines=True,
                                                encoding='utf-8', env=env,
                                                close_fds=True,
                                                creationflags=subprocess.DETACHED_PROCESS)
            else:
                self.process = subprocess.Popen(self.args, stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, shell=False,
                                                universal_newlines=True,
                                                encoding='utf-8', env=env,
                                                close_fds=True)
            self.stdout_thread = threading.Thread(target=self.stdout_reader,
                                                  name=f'{self.thread_name}_stdout_rdr')
            Monitor.exception_on_abort()
            self.stdout_thread.start()
            #  self.stderr_thread = threading.Thread(target=self.stderr_reader,
            #                                        name=f'{
            #                                        self.thread_name}_stderr_rdr')
            # self.stderr_thread.start()
            Monitor.exception_on_abort(timeout=1.0)

            # fifo_file_in = os.open(self.slave_pipe_path, os.O_RDONLY | os.O_NONBLOCK)
            # fifo_file_out = os.open(self.slave_pipe_path, os.O_WRONLY)

            fifo_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            fifo_sock.settimeout(0.0)
            finished: bool = False
            limit: int = 30

            while limit > 0:
                try:
                    fifo_sock.connect(str(self.slave_pipe_path))
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
                # os.unlink(self.slave_info.get_fifo_name())
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
            sleep(0.25)
            self.send_speed()
            self.send_volume()
            self.config_observers()
        except AbortException as e:
            self.rc = 99  # Let thread die
        except Exception as e:
            clz.logger.exception('')
            self.rc = 10
        if self.rc == 0:
            self.run_state = RunState.RUNNING
        clz.logger.debug(f'Finished starting mpv')
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
                        clz.logger.debug(f'FIFO_IN: {line}')
                except ValueError as e:
                    rc = self.process.poll()
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
                        clz.logger.debug(f'data: {data}')

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
            self.fifo_in.close()
            return
        except Exception as e:
            clz.logger.exception('')
            return

    '''
    def stderr_reader(self):
        GarbageCollector.add_thread(self.stderr_thread)
        if Monitor.is_abort_requested():
            self.process.kill()

        clz = type(self)
        finished = False
        try:
            while not Monitor.exception_on_abort():
                try:
                    if finished or self.cmd_finished:
                        break
                    line = self.process.stderr.readline()
                    if len(line) > 0:
                        self.stderr_lines.append(line)
                        clz.logger.debug(f'stderr: {line}')
                except ValueError as e:
                    rc = self.process.poll()
                    if rc is not None:
                        self.rc = rc
                        # Command complete
                        finished = True
                        break
                    else:
                        clz.logger.exception('')
                        finished = True

        except AbortException as e:
            self.process.stderr.close()
            self.process.stderr = None
            return
        except Exception as e:
            clz.logger.exception('')
            return
   '''

    def stdout_reader(self):
        clz = type(self)
        GarbageCollector.add_thread(self.stdout_thread)
        finished = False
        try:
            while not Monitor.exception_on_abort(timeout=0.1):
                try:
                    if finished or self.cmd_finished:
                        break
                    line: str
                    line, _ = self.process.communicate(input='',
                                                       timeout=0.0)
                    if len(line) > 0:
                        clz.logger.debug_verbose(f'STDOUT: {line}')
                except subprocess.TimeoutExpired:
                    Monitor.exception_on_abort(timeout=0.1)
                except ValueError as e:
                    rc = self.process.poll()
                    if rc is not None:
                        self.rc = rc
                        # Command complete
                        finished = True
                        break
                    else:
                        clz.logger.exception('')
                        finished = True
        except AbortException as e:
            self.process.stdout.close()
            self.process.stdout = None
            return
        except Exception as e:
            clz.logger.exception('')
        return

    '''
    def log_output(self):
        clz = type(self)
        try:
            if Monitor.is_abort_requested():
                return

            clz = type(self)
            if clz.logger.isEnabledFor(DEBUG):
                if self.rc != 0:
                    clz.logger.debug(f'Failed rc: {self.rc}')
                if clz.logger.isEnabledFor(DEBUG_VERBOSE):
                    stdout = '\n'.join(self.stdout_lines)
                    clz.logger.debug_verbose(f'STDOUT: {stdout}')
                    #  stderr = '\n'.join(self.stderr_lines)
                    # clz.logger.debug_verbose(f'STDERR: {stderr}')
        except AbortException as e:
            return
        except Exception as e:
            clz.logger.exception('')
        return
        '''
