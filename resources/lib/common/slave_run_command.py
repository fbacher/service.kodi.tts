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

module_logger = BasicLogger.get_logger(__name__)


class SlaveRunCommand:
    """

    """
    #  player_state: str = KodiPlayerState.VIDEO_PLAYER_IDLE
    logger: BasicLogger = None

    def __init__(self, args, thread_name: str = 'slave_run_cmd',
                 post_start_callback: Callable[[None], bool] = None) -> None:
        """

        :param args: arguments to be passed to exec command
        """
        clz = type(self)
        SlaveRunCommand.logger = module_logger

        self.args: List[str] = args
        #  args.append('--log-file=/tmp/mpv.log')
        #  args.append('--msg-level=all=debug')
        self.thread_name = thread_name
        self.rc = 0
        self.run_state: RunState = RunState.NOT_STARTED
        self.cmd_finished: bool = False
        self.process: Popen | None = None
        self.run_thread: threading.Thread | None = None
        clz.logger.debug(f'Calling post_start_callback')
        self.post_start_callback: Callable[[None], bool] = post_start_callback
        clz.logger.debug(f'Returned from post_start_callback')
        Monitor.register_abort_listener(self.abort_listener, name=thread_name,
                                        garbage_collect=False)

    def terminate(self):
        if self.process is not None and self.run_state.value <= RunState.RUNNING.value:
            self.process.kill()
        clz = type(self)
        clz.logger.debug(f'terminate')

    def kill(self):
        pass

    def get_state(self) -> RunState:
        clz = type(self)
        # clz.get.debug(f'run_state: {self.run_state}')
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
        self.run_state = RunState.COMPLETE
        if self.cmd_finished:
            return

        clz = type(self)
        clz.logger.debug(f'In destroy')
        self.cmd_finished = True
        if self.process is not None:
            try:
                self.process.poll()
                if self.process.returncode is not None:
                    return
            except:
                return  # Probably dead
            try:
                self.process.stdin.close()
            except:
                pass
            try:
                self.process.stdout.close()
            except:
                pass
            # self.process.wait(0.1)
            try:
                self.process.kill()
            except:
                pass
        clz.logger.debug('Slave Destroyed')

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
            GarbageCollector.add_thread(self.run_thread)
            self.cmd_finished = False
            self.process: Popen

            # First, wait until process has started. Should be very quick
            attempts: int = 300  # Approx one second
            while not Monitor.wait_for_abort(timeout=0.02):
                if self.run_state == RunState.PIPES_CONNECTED or attempts < 0:
                    # clz.get.debug(f'attempts: {attempts} state: {self.run_state}')
                    self.run_state = RunState.RUNNING
                    break
                attempts -= 1
        except AbortException:
            # abort_listener will do the kill
            self.rc = 99  # Thread will exit very soon
            self.run_state = RunState.TERMINATED

        return 0

    def poll(self) -> int | None:
        return self.process.poll()

    def run_service(self) -> None:
        clz = type(self)
        self.rc = 0
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

                # self.args.append('/home/fbacher/.kodi/userdata/addon_data/service.kodi.tts/cache/goo/df/df16f1fee15ac535aed684fab4a54fd4.mp3')
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
            Monitor.exception_on_abort()
            if self.post_start_callback:
                if self.post_start_callback():
                    self.run_state = RunState.PIPES_CONNECTED
                    clz.logger.debug(f'pipes connected')
            Monitor.exception_on_abort(timeout=1.0)
        except AbortException:
            return  # We are in the top of the thread
        except Exception as e:
            clz.logger.exception('')
        clz.logger.debug(f'returning from run_service')
        return
