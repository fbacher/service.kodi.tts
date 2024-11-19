# coding=utf-8
from __future__ import annotations  # For union operator |

#  import simplejson as json
import os
import subprocess
import threading
from pathlib import Path
from subprocess import Popen

from common import *
from common.constants import Constants
from common.garbage_collector import GarbageCollector
from common.kodi_player_monitor import KodiPlayerState
from common.logger import *
from common.monitor import Monitor
from common.simple_run_command import RunState

module_logger = BasicLogger.get_logger(__name__)


class Pyttsx4RunDaemon:
    """

    """
    PYTHON_PATH: Final[Path] = Path(os.environ.get('PYTHON_PATH')) / 'python.exe'
    DAEMON_PATH: Final[Path] = (Path(Constants.PYTHON_ROOT_PATH) / 'backends' /
                                'pyttsx4_daemon' / 'daemon.py')
    player_state: str = KodiPlayerState.VIDEO_PLAYER_IDLE
    logger: BasicLogger = None

    def __init__(self) -> None:
        """

        :param args: arguments to be passed to exec command
        """
        clz = type(self)
        Pyttsx4RunDaemon.logger = module_logger
        self.thread_name: str = 'pyttsx4_daemon'
        self.rc = 0
        self.run_state: RunState = RunState.NOT_STARTED
        self.cmd_finished: bool = False
        self._thread: threading.Thread | None = None
        self.process: Popen | None = None
        self.run_thread: threading.Thread | None = None
        # self.cmd_stdout_reader_thread: threading.Thread | None = None
        self.stdout_lines: List[str] = []
        self.slave_pipe: int = 0

        Monitor.register_abort_listener(self.abort_listener, name=self.thread_name)

    def send_line(self, text: str) -> None:
        clz = type(self)
        try:
            self.process.stdin.write(f'{text}\n')
            clz.logger.debug(f'About to flush')
            self.process.stdin.flush()
            clz.logger.debug(f'flushed stdin: {text}')
        except Exception as e:
            clz.logger.exception('')

    def terminate(self):
        clz = type(self)
        clz.logger.debug(f'terminating pyttsx4_run_daemon')
        if self.process is not None and self.run_state.value <= RunState.RUNNING.value:
            self.process.terminate()

    def kill(self):
        pass

    def get_state(self) -> RunState:
        return self.run_state

    def abort_listener(self) -> None:
        # Shut down mpv
        self.destroy()

    def destroy(self):
        """
        Destroy this daemon. Typicaly done
        when either stopping TTS (F12) or shutdown, or switching players,
        players, etc.

        :return:
        """
        clz = type(self)
        clz.logger.debug(f'In pyttsx4_run_daemon.destroy')
        self.process.kill()
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
        self.process.wait(0.25)

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

            # First, wait until process has started. Should be very quick
            attempts: int = 100  # Approx one second
            while not Monitor.wait_for_abort(timeout=0.01):
                if self.run_state != RunState.NOT_STARTED or attempts < 0:
                    break
                attempts -= 1

        except AbortException:
            # abort_listener will do the kill
            self.rc = 99  # Thread will exit very soon

        return 0

    def poll(self) -> int | None:
        return self.process.poll()

    def run_service(self) -> None:
        clz = type(self)
        self.rc = 0
        GarbageCollector.add_thread(self.run_thread)
        env = os.environ.copy()
        try:
            args: List[str] = [
                str(clz.PYTHON_PATH),
                str(clz.DAEMON_PATH)
            ]
            clz.logger.debug(f'args: {args}')
            creation_flags: int = 0
            if Constants.PLATFORM_WINDOWS:
                creationflags = subprocess.DETACHED_PROCESS

            self.process = subprocess.Popen(args=args, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, shell=False,
                                            universal_newlines=True,
                                            encoding='utf-8', env=env,
                                            close_fds=True,
                                            creationflags=subprocess.DETACHED_PROCESS |
                                            subprocess.CREATE_NO_WINDOW)
            Monitor.exception_on_abort()
            Monitor.exception_on_abort(timeout=1.0)
            '''
            self.cmd_stdout_reader_thread = threading.Thread(
                target=self.cmd_stdout_reader,
                name=f'{self.thread_name}_cmd_stdout_reader')
            self.cmd_stdout_reader_thread.start()
            '''
        except AbortException as e:
            self.rc = 99  # Let thread die
        except Exception as e:
            clz.logger.exception('')
            self.rc = 10
        if self.rc == 0:
            self.run_state = RunState.RUNNING
        clz.logger.debug(f'Finished starting pyttsx4 daemon')
        return

    def get_msg(self) -> str:
        clz = type(self)
        # GarbageCollector.add_thread(self.cmd_stdout_reader_thread)
        # if Monitor.is_abort_requested():
        #     self.process.kill()

        finished = False
        line: str = ''
        try:
            while not Monitor.exception_on_abort(timeout=0.1):
                try:
                    if finished or self.cmd_finished:
                        break
                    if self.process.poll() is None:
                        #  line, _ = self.process.communicate(input='', timeout=0.1)
                        line = self.process.stdout.readline()
                        clz.logger.debug(f'cmd_out: {line}')
                    else:
                        clz.logger.debug(f'process DEAD')
                    break
                except subprocess.TimeoutExpired:
                    pass
                except ValueError as e:
                    rc = self.process.poll()
                    if rc is not None:
                        self.rc = rc
                        # Command complete
                        break
                    else:
                        clz.logger.exception('')
                        finished = True
                except Exception as e:
                    clz.logger.exception('')
                    finished = True

        except AbortException as e:
            clz.logger.debug(f'AbortException, terminationg pyttsx4_run_daemon')
            self.process.stdout.close()
        except Exception as e:
            clz.logger.exception('')
        return line

    '''
    def cmd_stdout_reader(self):
        clz = type(self)
        GarbageCollector.add_thread(self.cmd_stdout_reader_thread)
        # if Monitor.is_abort_requested():
        #     self.process.kill()

        finished = False
        try:
            while not Monitor.exception_on_abort(timeout=0.1):
                line: str = ''
                try:
                    if finished or self.die:
                        break
                    line = self.process.stdout.readline()
                    clz.get.debug(f'cmd_out: {line}')
                except ValueError as e:
                    rc = self.process.poll()
                    if rc is not None:
                        self.rc = rc
                        # Command complete
                        break
                    else:
                        clz.get.exception('')
                        finished = True
                except Exception as e:
                    clz.get.exception('')
                    finished = True
                    line: str = ''

        except AbortException as e:
            self.process.stdout.close()
            return
        except Exception as e:
            clz.get.exception('')
            return
    '''
