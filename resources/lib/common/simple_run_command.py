# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess
import threading
from enum import Enum
from pathlib import Path
from subprocess import Popen

import xbmc

from common import *
from common.constants import Constants

from common.garbage_collector import GarbageCollector
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.monitor import Monitor
from common.phrases import PhraseList

MY_LOGGER = BasicLogger.get_logger(__name__)


class RunState(Enum):
    NOT_STARTED = 0
    PIPES_CONNECTED = 1
    RUNNING = 2
    COMPLETE = 3
    DIE = 4
    KILLED = 5
    TERMINATED = 6


class SimpleRunCommand:
    """

    """
    player_state: str = KodiPlayerState.VIDEO_PLAYER_IDLE
    instance_count: int = 0

    def __init__(self, args: List[str], phrase_serial: int = 0, name: str = '',
                 stop_on_kodi_play: bool = False,
                 delete_after_run: Path = None) -> None:
        """

        :param args: arguments to be passed to exec command
        :param phrase_serial: Serial Number of PhraseList containing phrase.
            Used to handle expiration of phrase
        :param name: thread_name
        :param stop_on_kodi_play If True, then exit if video is playing before, or
               during TTS audio play
        :param delete_after_run: Delete the given path after running command.
        """
        clz = type(self)
        self.args: List[str] = args
        self.phrase_serial: int = phrase_serial
        self.count: int = clz.instance_count
        clz.instance_count += 1
        self.thread_name = f'{name}_{self.count}'
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'thread_name: {self.thread_name} delete_after_run:'
                              f' {delete_after_run} args: {args}')
        self.lock: threading.RLock = threading.RLock()
        self.rc: int | None = None
        self.run_state: RunState = RunState.NOT_STARTED
        self.stop_on_kodi_play: bool = stop_on_kodi_play
        self.play_interrupted: bool = False  # True when video playing and idle_on_play_video
        self.delete_after_run: Path | None = delete_after_run
        self.cmd_finished: bool = False
        self.process: Popen | None = None
        self.run_thread: threading.Thread | None = None
        self.stdout_thread: threading.Thread | None = None
        self.stderr_thread: threading.Thread | None = None
        self.stdout_lines: List[str] = []
        self.stderr_lines: List[str] = []

        Monitor.register_abort_listener(self.abort_listener, name=name)

        if self.stop_on_kodi_play:
            if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
                self.cleanup(RunState.TERMINATED)
                return

            KodiPlayerMonitor.register_player_status_listener(
                    self.kodi_player_status_listener,
                    f'{self.thread_name}_Kodi_Player_Monitor')

    def cleanup(self, runstate: RunState | None = None) -> None:
        """
        Ensures that the subprocess ends cleanly. Called when the process
         exits, or is made to exit. Closes files, deletes files marked for
         deletion, logs outout.
        """
        clz = type(self)
        try:
            if runstate is not None and self.run_state == RunState.NOT_STARTED:
                self.run_state = runstate
            if self.delete_after_run and self.delete_after_run.exists():
                self.delete_after_run.unlink(missing_ok=True)

            if self.rc is None:
                self.rc = RunState.TERMINATED.value
            if self.rc != 0:
                self.log_output()
            self.cmd_finished = True
            # Give a tiny bit of time for other threads to shut down before we yank
            # the process object.
            Monitor.wait_for_abort(0.01)
            self.process = None
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'FINISHED COMMAND {self.phrase_serial} '
                                f'{self.args[0]} rc: {self.rc}',
                                trace=Trace.TRACE_AUDIO_START_STOP)
        except Exception as e:
            MY_LOGGER.exception('')

    def stop_player(self, purge: bool = True,
                    keep_silent: bool = False,
                    kill: bool = False):
        """
        Called externally to stop player_key (most likely because current text
         is expired).

        Pocesses may ignore parameters that don't apply.

        :param purge: if True, then purge any queued vocings
                      if False, then only stop playing current phrase
        :param keep_silent: if True, ignore any new phrases until restarted
                            by resume_player.
                            If False, then play any new content
        :param kill: If True, kill any player_key processes. Implies purge and
                     keep_silent.
                     If False, then the player_key will remain ready to play new
                     content, depending upon keep_silent
        :return:
        """
        # Choice is to kill or terminate. The only corruption we care about is
        # any produced cache files, which this process sends to temp files.
        # Therefore, kill is faster and assuming the code that moves the tmp file
        # to the cache just deletes it instead, then this should be okay.
        self.kill()

    def terminate(self):
        if self.process is not None and self.poll() is None:
            self.close_files()
            self.process.terminate()
            next_state = RunState.TERMINATED
        self.cleanup(RunState.TERMINATED)

    def kill(self):
        next_state: RunState | None = None
        if self.process is not None and self.poll() is None:
            self.close_files()
            Monitor.wait_for_abort(0.01)
            # Give some time for stdin/stdout threads to shutdown.
            self.process.kill()
            next_state = RunState.KILLED
        self.cleanup(next_state)

    def get_state(self) -> RunState:
        return self.run_state

    def poll(self) -> int | None:
        try:
            if self.process is not None:
                return self.process.poll()
            return RunState.TERMINATED.value
        except Exception:
            MY_LOGGER.exception(f'Exception in poll')

    def abort_listener(self) -> None:
        pass

    def kodi_player_status_listener(self, kodi_player_state: KodiPlayerState) -> bool:
        clz = type(self)
        clz.player_state = kodi_player_state
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'KodiPlayerState: {kodi_player_state} stop_on_play: '
                              f'{self.stop_on_kodi_play} args: {self.args} '
                              f'serial: {self.phrase_serial}')
        if kodi_player_state == KodiPlayerState.PLAYING_VIDEO and self.stop_on_kodi_play:
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'KODI_PLAYING terminating command: '
                                  f'args: {self.args} ')
            self.kill()
            return True  # Unregister
        return False

    def run_cmd(self) -> int:
        """

        :return:
        """
        clz = type(self)
        if self.cmd_finished:
            return self.rc

        self.rc = None
        self.run_thread = threading.Thread(target=self.run_worker, name=self.thread_name)
        try:
            Monitor.exception_on_abort()
            if self.phrase_serial < PhraseList.expired_serial_number:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'EXPIRED before start {self.phrase_serial} '
                                      f'{self.args[0]}',
                                      trace=Trace.TRACE_AUDIO_START_STOP)
                self.run_state = RunState.TERMINATED
                self.rc = 11
                return self.rc

            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'About to run args:{self.args[0]}')
            self.run_thread.start()

            self.process: Popen
            check_serial: bool = True

            # First, wait until process has started. Should be very quick
            attempts: int = 3
            while not Monitor.wait_for_abort(timeout=0.1):
                if self.process is not None:
                    self.run_state = RunState.RUNNING
                    break
                attempts -= 1
                if attempts < 0:
                    break
            if self.run_state != RunState.RUNNING:
                if self.process is not None:
                    self.process.kill()

            next_state: RunState = RunState.COMPLETE
            max_iterations: int = int((7.0 / 0.1) + 1)
            while not Monitor.exception_on_abort(timeout=0.1):
                max_iterations -= 1
                try:
                    # Move on if command finished
                    if self.poll() is not None:
                        if MY_LOGGER.isEnabledFor(DEBUG_XV):
                            MY_LOGGER.debug_xv(f'Process finished rc: '
                                               f'{self.process.returncode} next:'
                                               f' {next_state}')
                        self.run_state = next_state
                        break
                    # Are we trying to kill it?
                    if (check_serial and self.phrase_serial <
                            PhraseList.expired_serial_number or max_iterations < 0):
                        # Yes, initiate terminate/kill of process
                        check_serial = False
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Expired, kill {self.phrase_serial} '
                                            f'{self.args[0]}',
                                            trace=Trace.TRACE_AUDIO_START_STOP)
                        try:
                            self.kill()
                        except Exception:
                            MY_LOGGER.exception('')
                        break
                    if max_iterations <= 0:
                        self.kill()
                        break
                except subprocess.TimeoutExpired:
                    #  Only indicates the timeout is expired, not the run state
                    if max_iterations <= 0:
                        self.kill()
                        break

            # No matter how process ends, there will be a return code
            if self.run_state == RunState.COMPLETE:
                self.cleanup()
        except AbortException:
            try:
                if self.process is not None:
                    self.process.kill()  # SIGKILL. Should cause stderr & stdout to exit
            except Exception:
                pass
            self.rc = 99  # Thread will exit very soon
        finally:
            Monitor.unregister_abort_listener(self.abort_listener)
            KodiPlayerMonitor.unregister_player_status_listener(
                f'{self.thread_name}_Kodi_Player_Monitor')
        return self.rc

    def run_worker(self) -> None:
        """
        run thread that runs subprocess
        """
        clz = type(self)
        self.rc = 0
        GarbageCollector.add_thread(self.run_thread)
        env = os.environ.copy()
        try:
            if Constants.PLATFORM_WINDOWS:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'Starting Windows cmd args: {self.args}')

                # Prevent console for command from opening
                #
                # Here, we keep stdout & stderr separate and combine the output in the
                # log. Need to change to be configureable: separate, combined at
                # process level (stderr = subprocess.STDOUT), devnull or pass through
                # via pipe and don't log

                self.process = subprocess.Popen(self.args, stdin=None,  # subprocess.DEVNULL,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT,
                                                shell=False,
                                                text=True, env=env,
                                                encoding='cp1252',  # 'utf-8',
                                                close_fds=True,
                                                creationflags=subprocess.DETACHED_PROCESS)
            else:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'Starting Linux cmd args: {self.args}')
                self.process = subprocess.Popen(self.args, stdin=None,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT,
                                                shell=False,
                                                text=True, env=env,
                                                close_fds=True)
            self.run_state = RunState.RUNNING
            self.stdout_thread = threading.Thread(target=self.stdout_reader,
                                                  name=f'{self.thread_name}_stdout_rdr')
            Monitor.exception_on_abort()
            self.stdout_thread.start()
            # if not xbmc.getCondVisibility('System.Platform.Windows'):
            #     self.stderr_thread = threading.Thread(target=self.stderr_reader,
            #                                           name=f'{self.thread_name}_stderr_rdr')
            #     self.stderr_thread.start()
        except AbortException as e:
            self.rc = 99
            self.run_state = RunState.DIE
            return
        except Exception as e:
            MY_LOGGER.exception('')
            self.rc = 10
        if self.rc is None and self.run_state  in (RunState.RUNNING,
                                                   RunState.NOT_STARTED,
                                                   RunState.PIPES_CONNECTED):
            self.run_state = RunState.TERMINATED
        if self.rc == 0:
            self.run_state = RunState.COMPLETE
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
                    if self.process is None:
                        break
                    # self.process, etc. can still disappear
                    if not self.process.stdout.closed:
                        try:
                            line = self.process.stdout.readline()
                            if len(line) > 0:
                                self.stdout_lines.append(line)
                        except ValueError as e:
                            try:
                                if self.process.stdout.closed:
                                    finished = True
                                else:
                                    MY_LOGGER.exception('')
                            except:
                                MY_LOGGER.exception('')
                    try:
                        rc = self.poll()
                        if rc is not None:
                            self.rc = rc
                            # Command complete
                            finished = True
                            break
                    except Exception:
                        MY_LOGGER.exception('')
                except Exception:
                    MY_LOGGER.exception('')
                    finished = True
        except AbortException as e:
            return
        except Exception as e:
            MY_LOGGER.exception('')

        self.cmd_finished = True
        try:
            if (self.process is not None and self.process.stdout is not None
                    and not self.process.stdout.closed):
                self.process.stdout.close()
        except Exception:
            MY_LOGGER.exception('')
        return

    def close_files(self) -> None:
        """
        Close files:
           closing stdin frequently causes process to exit (if there is a read from it)
           closing stdout allows readers to complete
        """
        try:  # Closing stdin will cause command to exit (if it reads from it after
              #   close).
            if (self.process is not None and self.process.stdin is not None and
                    not self.process.stdin.closed):
                self.process.stdin.close()
        except Exception:
            MY_LOGGER.exception('')
        try:
            if (self.process is not None and self.process.stdout is not None and
                    not self.process.stdout.closed):
                self.process.stdout.close()
        except Exception:
            MY_LOGGER.exception('')

    def log_output(self):
        clz = type(self)
        try:
            if Monitor.is_abort_requested():
                return

            clz = type(self)
            if MY_LOGGER.isEnabledFor(DEBUG):
                if self.rc != 0:
                    MY_LOGGER.debug(f'Failed rc: {self.rc}')
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    stdout = '\n'.join(self.stdout_lines)
                    MY_LOGGER.debug_v(f'STDOUT: {stdout}')
                    #  stderr = '\n'.join(self.stderr_lines)
                    #  MY_LOGGER.debug_v(f'STDERR: {stderr}')
        except AbortException as e:
            return
        except Exception as e:
            MY_LOGGER.exception('')
        return
