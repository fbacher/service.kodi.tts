# coding=utf-8
from __future__ import annotations  # For union operator |

import io
import os
import shutil
import subprocess
import threading
from enum import Enum
from subprocess import Popen

import xbmc

from common import *

from common.garbage_collector import GarbageCollector
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.monitor import Monitor
from common.phrases import PhraseList

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class RunState(Enum):
    NOT_STARTED = 0
    RUNNING = 1
    COMPLETE = 2
    KILLED = 3
    TERMINATED = 4


class SimplePipeCommand:
    """

    """
    player_state: str = KodiPlayerState.PLAYING_STOPPED
    logger: BasicLogger = None

    def __init__(self, args: List[str],
                 stdin: BinaryIO | int | None = subprocess.DEVNULL,
                 stdout: TextIO | int | None = subprocess.DEVNULL,
                 stderr: TextIO | int | None = subprocess.DEVNULL,
                 phrase_serial: int = 0, name: str = '',
                 stop_on_play: bool = False) -> None:
        """

        :param args: arguments to be passed to exec command
        """
        self.stdin: BinaryIO | int | None = stdin
        self.stderr: TextIO | int | None = stderr
        self.stdout: TextIO | int | None = stdout
        clz = type(self)
        SimplePipeCommand.logger = module_logger.getChild(clz.__name__)
        self.args: List[str] = args
        self.phrase_serial: int = phrase_serial
        self.thread_name = name
        self.rc = 0
        self.run_state: RunState = RunState.NOT_STARTED
        self.stop_on_play: bool = stop_on_play
        self.cmd_finished: bool = False
        self.process: Popen = None
        self.run_thread: threading.Thread | None = None
        self.capture_output: bool = False
        self.stdout_thread: threading.Thread | None = None
        self.stderr_thread: threading.Thread | None = None
        self.stdout_lines: List[str] = []
        self.stderr_lines: List[str] = []
        Monitor.register_abort_listener(self.abort_listener, name=name)

        if self.stop_on_play:
            KodiPlayerMonitor.register_player_status_listener(
                    self.kodi_player_status_listener,
                    f'{self.thread_name}_Kodi_Player_Monitor')
        return

    def terminate(self):
        if self.process is not None and self.run_state.value <= RunState.RUNNING.value:
            self.process.terminate()

    def kill(self):
        pass

    def get_state(self) -> RunState:
        return self.run_state

    def abort_listener(self) -> None:
        pass

    def kodi_player_status_listener(self, player_state: KodiPlayerState) -> bool:
        clz = type(self)
        clz.player_state = player_state
        clz.logger.debug(f'PlayerStatus: {player_state} stop_on_play: '
                         f'{self.stop_on_play} args: {self.args} '
                         f'serial: {self.phrase_serial}')
        if player_state == KodiPlayerState.PLAYING and self.stop_on_play:
            clz.logger.debug(f'PLAYING terminating command: '
                             f'args: {self.args} ')
            self.terminate()
            return True  # Unregister listener

    def run_cmd(self) -> int:
        """

        :return:
        """
        clz = type(self)
        self.rc = None
        input_bytes: bytes | None = None
        if isinstance(self.stdin, bytes):
            input_bytes = self.stdin

        self.run_thread = threading.Thread(target=self.run_worker, name=self.thread_name)
        try:
            Monitor.exception_on_abort()
            if self.phrase_serial < PhraseList.expired_serial_number:
                clz.logger.debug(f'EXPIRED before start {self.phrase_serial} '
                                 f'{self.args[0]}',
                                 trace=Trace.TRACE_AUDIO_START_STOP)
                self.run_state = RunState.TERMINATED
                self.rc = 11
                return self.rc

            self.run_thread.start()
            self.cmd_finished = False
            self.process: Popen
            check_serial: bool = True
            countdown: bool = False
            kill_countdown: int = 2

            # First, wait until process has started. Should be very quick
            while not Monitor.wait_for_abort(timeout=0.0):
                if self.process is not None:
                    self.run_state = RunState.RUNNING
                    break

            next_state = RunState.COMPLETE
            while not Monitor.wait_for_abort(timeout=0.1):
                try:
                    rc: int | None = self.process.poll()
                    if rc is not None:
                        self.run_state = next_state
                        self.rc = rc
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
                        clz.logger.debug(
                            f'Terminate not working, Killing {self.phrase_serial} '
                            f'{self.args[0]}',
                            trace=Trace.TRACE_AUDIO_START_STOP)
                        self.process.kill()
                        break
                except subprocess.TimeoutExpired:
                    #  Only indicates the timeout is expired, not the run state
                    pass
                except Exception as e:
                    clz.logger.exception('')

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
                except Exception as e:
                    clz.logger.exception('')

            if not self.cmd_finished or self.process.poll() is None:
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
                    except Exception as e:
                        clz.logger.exception('')
                self.rc = 99

            if self.run_thread.is_alive():
                self.run_thread.join(timeout=0.5)
            if self.capture_output:
                if self.stdout_thread.is_alive():
                    self.stdout_thread.join(timeout=0.1)
                if self.stderr_thread.is_alive():
                    self.stderr_thread.join(timeout=0.1)
            Monitor.exception_on_abort(timeout=0.0)
            # If abort did not occur, then process finished

            if self.capture_output:
                if self.rc is None or self.rc != 0:
                    self.log_output()
        except AbortException:
            self.rc = 99  # Thread will exit very soon

        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            clz.logger.exception('')

        finally:
            Monitor.unregister_abort_listener(self.abort_listener)
            KodiPlayerMonitor.unregister_player_status_listener(
                self.kodi_player_status_listener)
        return self.rc

    def run_worker(self) -> None:
        clz = type(self)
        self.rc = 0
        GarbageCollector.add_thread(self.run_thread)
        env = os.environ.copy()
        clz.logger.debug(f'args: {self.args}')

        try:
            if xbmc.getCondVisibility('System.Platform.Windows'):
                # Prevent console for ffmpeg from opening
                #
                # Here, we keep stdout & stderr separate and combine the output in the
                # log. Need to change to be configurable: separate, combined at
                # process level (stderr = subprocess.STDOUT), devnull or pass through
                # via pipe and don't log

                self.process = subprocess.Popen(self.args, stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE, shell=False,
                                                universal_newlines=False,
                                                env=env,
                                                close_fds=True,
                                                creationflags=subprocess.DETACHED_PROCESS)
            else:
                self.process = subprocess.Popen(self.args, stdin=subprocess.PIPE,
                                                stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL,
                                                shell=False,
                                                env=env,
                                                close_fds=True)
            stdout_data, stderr_data = self.process.communicate(input=self.stdin.read(),
                                                                timeout=10.0)
            self.run_state = RunState.RUNNING
            if self.capture_output:
                self.stdout_thread = threading.Thread(target=self.stdout_reader,
                                                      name=f'{self.thread_name}_stdout_rdr')
                Monitor.exception_on_abort()
                self.stdout_thread.start()
                self.stderr_thread = threading.Thread(target=self.stderr_reader,
                                                      name=
                                                      f'{self.thread_name}_stderr_rdr')
                self.stderr_thread.start()
        except AbortException as e:
            self.rc = 99  # Let thread die
        except Exception as e:
            clz.logger.exception('')
            self.rc = 10
        return

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
            return
        except Exception as e:
            clz.logger.exception('')
            return

    def stdout_reader(self):
        clz = type(self)
        GarbageCollector.add_thread(self.stdout_thread)
        finished = False

        try:
            while not Monitor.exception_on_abort():
                try:
                    if finished or self.cmd_finished:
                        break
                    line = self.process.stdout.readline()
                    if len(line) > 0:
                        self.stdout_lines.append(line)
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
            return
        except Exception as e:
            clz.logger.exception('')
        return

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
                    stderr = '\n'.join(self.stderr_lines)
                    clz.logger.debug_verbose(f'STDERR: {stderr}')
        except AbortException as e:
            return
        except Exception as e:
            clz.logger.exception('')
        return
