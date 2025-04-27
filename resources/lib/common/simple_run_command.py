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
                 stop_on_play: bool = False,
                 delete_after_run: Path = None) -> None:
        """

        :param args: arguments to be passed to exec command
        :param phrase_serial: Serial Number of PhraseList containing phrase.
            Used to handle expiration of phrase
        :param name: thread_name
        :param stop_on_play If True, then exit if video is playing before, or
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
        self.rc = 0
        self.run_state: RunState = RunState.NOT_STARTED
        self.stop_on_play: bool = stop_on_play
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

        if self.stop_on_play:
            if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
                self.cleanup()
                return

            KodiPlayerMonitor.register_player_status_listener(
                    self.kodi_player_status_listener,
                    f'{self.thread_name}_Kodi_Player_Monitor')

    def cleanup(self):
        clz = type(self)
        try:
            if self.delete_after_run and self.delete_after_run.exists():
                self.delete_after_run.unlink(missing_ok=True)

            if self.rc is None or self.rc != 0:
                self.log_output()
        except Exception as e:
            MY_LOGGER.exception('')

    def stop_player(self, purge: bool = True,
                    keep_silent: bool = False,
                    kill: bool = False):
        """
        Stop player_key (most likely because current text is expired)
        Engines may wish to override this method, particularly when
        the player_key is built-in. Players/processes may ignore parameters
        that don't apply.

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
        # The only response to any request is to kill process.
        self.terminate()

    def terminate(self):
        if self.process is not None and self.run_state.value <= RunState.RUNNING.value:
            self.close_files()
            self.process.terminate()
        self.cleanup()

    def kill(self):
        pass

    def get_state(self) -> RunState:
        return self.run_state

    def poll(self) -> int | None:
        try:
            return self.process.poll()
        except Exception:
            MY_LOGGER.debug(f'Exception in poll')

    def abort_listener(self) -> None:
        pass

    def kodi_player_status_listener(self, kodi_player_state: KodiPlayerState) -> bool:
        clz = type(self)
        clz.player_state = kodi_player_state
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'KodiPlayerState: {kodi_player_state} stop_on_play: '
                              f'{self.stop_on_play} args: {self.args} '
                              f'serial: {self.phrase_serial}')
        if kodi_player_state == KodiPlayerState.PLAYING_VIDEO and self.stop_on_play:
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'KODI_PLAYING terminating command: '
                                  f'args: {self.args} ')
            self.terminate()
            return True  # Unregister
        return False

    def run_cmd(self) -> int:
        """

        :return:
        """
        clz = type(self)
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
            countdown: bool = False
            kill_countdown: int = 2

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
            while not Monitor.wait_for_abort(timeout=0.1):
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
                            PhraseList.expired_serial_number):
                        # Yes, initiate terminate/kill of process
                        check_serial = False
                        countdown = True
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Expired, kill {self.phrase_serial} '
                                            f'{self.args[0]}',
                                            trace=Trace.TRACE_AUDIO_START_STOP)
                        try:
                            self.process.kill()
                        except Exception:
                            break
                        next_state = RunState.KILLED
                        break
                except subprocess.TimeoutExpired:
                    #  Only indicates the timeout is expired, not the run state
                    pass

            # No matter how process ends, there will be a return code
            while not Monitor.wait_for_abort(timeout=0.1):
                try:
                    rc = self.process.returncode
                    if rc is not None:
                        self.rc = rc
                        self.cmd_finished = True
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'FINISHED COMMAND {self.phrase_serial} '
                                            f'{self.args[0]} rc: {rc}',
                                            trace=Trace.TRACE_AUDIO_START_STOP)
                        break
                    else:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Should be finished, but returncode is None')
                        break  # Complete
                except subprocess.TimeoutExpired:
                    # Only indicates the timeout is expired, not the run state
                    pass

            if not self.cmd_finished:
                # Shutdown in process
                try:
                    self.process.kill()
                except Exception:
                    pass
                next_state = RunState.KILLED
                self.rc = 99

            self.cleanup()
        except AbortException:
            try:
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
            self.rc = 99  # Let thread die
        except Exception as e:
            MY_LOGGER.exception('')
            self.rc = 10
        if self.rc == 0:
            self.run_state = RunState.COMPLETE
        return

    '''
    def stderr_reader(self):
        GarbageCollector.add_thread(self.stderr_thread)
        if Monitor.is_abort_requested():
            try:
                self.process.kill()
            except Exception:
                pass
        clz = type(self)
        finished = False
        try:
            while not Monitor.exception_on_abort():
                try:
                    if finished or self.die:
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
                        MY_LOGGER.exception('')
                        finished = True

        except AbortException as e:
            return
        except Exception as e:
            MY_LOGGER.exception('')
            return

        try:
            if self.process.stderr is not None:
                self.process.stderr.close()
        except Exception:
            pass
    '''

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
                    rc = self.poll()
                    if rc is not None:
                        self.rc = rc
                        # Command complete
                        finished = True
                        break
                    else:
                        MY_LOGGER.exception('')
                        finished = True
        except AbortException as e:
            return
        except Exception as e:
            MY_LOGGER.exception('')
        try:
            if self.process.stdout is not None:
                self.process.stdout.close()
        except Exception:
            pass
        return

    def close_files(self) -> None:
        try:
            if self.process.stdout is not None:
                self.process.stdout.close()
        except Exception:
            pass
        try:
            if self.process.stdin is not None:
                self.process.stdin.close()
        except Exception:
            pass

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
