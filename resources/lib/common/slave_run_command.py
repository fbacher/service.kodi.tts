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

    def __init__(self, args, thread_name: str = '',
                 post_start_callback: Callable[[None], None] = None) -> None:
        """

        :param args: arguments to be passed to exec command
        """
        clz = type(self)
        SlaveRunCommand.logger = module_logger.getChild(clz.__name__)

        self.args: List[str] = args
        # self.phrase_serial: int = phrase_serial
        self.thread_name = thread_name
        self.rc = 0
        self.run_state: RunState = RunState.NOT_STARTED
        self.cmd_finished: bool = False
        self._thread: threading.Thread | None = None
        self.fifo_in = None;
        self.fifo_out = None
        self.fifo_initialized: bool = False
        self.fifo_reader_thread: threading.Thread | None = None
        self.filename_sequence_number: int = 0
        self.playlist_playing_pos: int = 0
        self.process: Popen | None = None
        self.run_thread: threading.Thread | None = None
        self.fifo_sequence_number: int = 0
        self.observer_sequence_number: int = 0
        self.stdout_thread: threading.Thread | None = None
        self.stdout_lines: List[str] = []
        self.play_count: int = 0
        self.post_start_callback: Callable[[None], None] = post_start_callback

        Monitor.register_abort_listener(self.abort_listener, name=thread_name)

    def quit(self, now: bool):
        """
        Quit the player
        :param now: if True, then quit the player immediately
                    if False, then stop accepting items for playlist and quit
                    once playlist is empty
        """
        clz = type(self)
        try:
            self.cmd_finished = True
        except Exception as e:
            clz.logger.exception('')
        clz.logger.debug(f'Quit')

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
        try:
            self.process.stdout.close()
            self.process.stdout = None
        except:
            pass
        try:
            self.process.stdin.close()
            self.process.stdin = None
        except:
            pass
        self.process.wait(0.5)
        clz.logger.debug('Destroyed')

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
        clz.logger.debug(f'run_service started')
        env = os.environ.copy()
        try:
            if Constants.PLATFORM_WINDOWS:
                # Prevent console for mpv from opening
                #
                # Here, we keep stdout & stderr separate and combine the output in the
                # log. Need to change to be configurable: separate, combined at
                # process level (stderr = subprocess.STDOUT), devnull or pass through
                # via pipe and don't log

                clz.logger.debug(f'Cond_Visibility: '
                                 f'{xbmc.getCondVisibility("System.Platform.Windows")} '
                                 f'mpv_path: {Constants.MPV_PATH} '
                                 f'args: {self.args} ')
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
            if self.post_start_callback:
                self.post_start_callback()

            #  self.stderr_thread = threading.Thread(target=self.stderr_reader,
            #                                        name=f'{
            #                                        self.thread_name}_stderr_rdr')
            # self.stderr_thread.start()
            Monitor.exception_on_abort(timeout=1.0)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz.logger.exception('')
        return

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
