# coding=utf-8
from __future__ import annotations  # For union operator |

#  import json as json
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

MY_LOGGER = BasicLogger.get_logger(__name__)


class SlaveRunCommand:
    """

    """
    #  player_state: str = KodiPlayerState.VIDEO_PLAYER_IDLE

    def __init__(self, args, thread_name: str = 'slv_run_cmd', count: int = 0,
                 post_start_callback: Callable[[None], bool] = None) -> None:
        """

        :param args: arguments to be passed to exec command
        """
        clz = type(self)
        self.args: List[str] = args
        #  args.append('--log-file=/tmp/mpv.log')
        #  args.append('--msg-level=all=debug')
        thread_name = f'{thread_name}_{count}'
        self.thread_name = thread_name
        self.rc = 0
        self.run_state: RunState = RunState.NOT_STARTED
        self.cmd_finished: bool = False
        self.stdin_closed: bool = False
        self.stdout_closed: bool = False
        self.process: Popen | None = None
        self.run_thread: threading.Thread | None = None
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Calling post_start_callback')
        self.post_start_callback: Callable[[], bool] = post_start_callback
        Monitor.register_abort_listener(self.abort_listener, name=thread_name)

    def terminate(self):
        if self.process is not None and self.run_state.value <= RunState.RUNNING.value:
            self.process.kill()
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'slave terminate')

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
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'slave destroy, cmd_finished')
            return

        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'In slave destroy')
        self.cmd_finished = True
        killed: bool = False

        if self.process is not None:
            self.close_files()
            try:
                self.process.poll()
                if self.process.returncode is not None:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'RC: {self.process.returncode}')
                    return
            except:
                MY_LOGGER.exception('')
            # self.process.wait(0.1)
            try:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'slave process.kill')
                self.process.kill()
                killed = True
            except:
                MY_LOGGER.exception('')
        try:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Slave Destroyed:stdin: {self.stdin_closed} '
                                f'stdout: {self.stdout_closed} killed: {killed} '
                                f'RC: {self.process.returncode}')
        except:
            MY_LOGGER.exception('')

    def close_files(self) -> None:
        """
        Closing the process's files frequently kills the process and needs to
        be done for clean up

        :return:
        """
        try:
            if not self.stdin_closed:
                self.process.stdin.close()
                self.stdin_closed = True
        except:
            pass
        try:
            if not self.stdout_closed:
                self.process.stdout.close()
                self.stdout_closed = True
        except:
            pass
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'slave closed files')

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
        rc: int = self.process.poll()
        if rc is not None:
            self.cmd_finished = True
        return rc

    def run_service(self) -> None:
        clz = type(self)
        self.rc = 0
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'run_service started')
        env = os.environ.copy()
        try:
            if Constants.PLATFORM_WINDOWS:
                # Prevent console for mpv from opening
                #
                # Here, we keep stdout & stderr separate and combine the output in the
                # log. Need to change to be configurable: separate, combined at
                # process level (stderr = subprocess.STDOUT), devnull or pass through
                # via pipe and don't log

                # Process will block until reader for stdout PIPE opens
                # Be sure to close self.process.stdout AFTER second process starts
                # ex:
                # p1 = Popen(["dmesg"], stdout=PIPE)
                # p2 = Popen(["grep", "hda"], stdin=p1.stdout, stdout=PIPE)
                # p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
                # output = p2.communicate()[0]
                #
                # The p1.stdout.close() call after starting the p2 is important in order
                # for p1 to receive a SIGPIPE if p2 exits before p1.

                # self.args.append('/home/fbacher/.kodi/userdata/addon_data/service.kodi.tts/cache/goo/df/df16f1fee15ac535aed684fab4a54fd4.mp3')
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Running command: Windows')
                    MY_LOGGER.debug(f'mpv_path: {Constants.MPV_PATH} '
                                    f'args: {self.args} ')
                self.process = subprocess.Popen(self.args, stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, shell=False,
                                                text=True,
                                                encoding='utf-8', env=env,
                                                close_fds=True,
                                                creationflags=subprocess.DETACHED_PROCESS)
            else:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.info(f'Running command: Linux')
                self.process = subprocess.Popen(self.args, stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, shell=False,
                                                text=True,
                                                encoding='utf-8', env=env,
                                                close_fds=True)
            Monitor.exception_on_abort()
            if self.post_start_callback is not None:
                if self.post_start_callback():
                    self.run_state = RunState.PIPES_CONNECTED
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'pipes connected')
                    # Now that remote process is connected to stdout, we can close
                    # our local stdout. This allows our process to die if the other
                    # process dies.
                    self.process.stdout.close()
                    self.stdout_closed = True

            Monitor.exception_on_abort(timeout=1.0)
        except AbortException:
            return  # We are in the top of the thread
        except Exception as e:
            MY_LOGGER.exception('')
        Monitor.unregister_abort_listener(listener=self.abort_listener)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'slave returning from run_service')
        return
