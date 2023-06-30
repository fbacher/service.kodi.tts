# coding=utf-8
import subprocess
import threading
from subprocess import Popen

from cache.prefetch_movie_data.seed_cache import SeedCache
from common.critical_settings import CriticalSettings
from common.logger import *
from common.monitor import Monitor
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)

class RunCommand:
    logger: BasicLogger = None

    def __init__(self, args: List[str], movie_name: str) -> None:
        RunCommand.logger = module_logger.getChild(RunCommand.__name__)
        self.args = args
        self.movie_name = movie_name
        self.rc = 0
        self.cmd_finished = False
        self.process: Optional[Popen] = None
        self.run_thread: Union[None, threading.Thread] = None
        self.stdout_thread: Union[None, threading.Thread] = None
        self.stderr_thread: Union[None, threading.Thread] = None
        self.stdout_lines: List[str] = []
        self.stderr_lines: List[str] = []

    def run_cmd(self) -> int:
        self.rc = 0
        self.run_thread = threading.Thread(target=self.run_worker,
                                           name='normalize audio')
        Monitor.exception_on_abort()
        self.run_thread.start()

        self.cmd_finished = False
        while not Monitor.wait_for_abort(timeout=0.1):
            try:
                if self.process is not None:  # Wait to start
                    rc = self.process.poll()
                    if rc is not None:
                        self.rc = rc
                        self.cmd_finished = True
                        break  # Complete
            except subprocess.TimeoutExpired:
                pass

        if not self.cmd_finished:
            # Shutdown in process
            self.process: subprocess.Popen
            self.process.kill()  # SIGKILL. Should cause stderr & stdout to exit
            self.rc = 9

        if self.run_thread.is_alive():
            self.run_thread.join(timeout=1.0)
        if self.stdout_thread.is_alive():
            self.stdout_thread.join(timeout=0.2)
        if self.stderr_thread.is_alive():
            self.stderr_thread.join(timeout=0.2)
        Monitor.exception_on_abort(timeout=0.0)
        # If abort did not occur, then process finished

        if self.rc != 0:
            self.log_output()

        return self.rc

    def run_worker(self) -> None:
        clz = RunCommand
        rc = 0
        env = os.environ.copy()
        try:
            if xbmc.getCondVisibility('System.Platform.Windows'):
                # Prevent console for ffmpeg from opening

                self.process = subprocess.Popen(
                        self.args, stdin=None, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=False, universal_newlines=True, env=env,
                        close_fds=True, creationflags=subprocess.DETACHED_PROCESS)
            else:
                self.process = subprocess.Popen(
                        self.args, stdin=None, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, shell=False, universal_newlines=True, env=env,
                        close_fds=True)
            self.stdout_thread = threading.Thread(target=self.stdout_reader,
                                                  name='normalize stdout reader')
            Monitor.exception_on_abort()
            self.stdout_thread.start()

            self.stderr_thread = threading.Thread(target=self.stderr_reader,
                                                  name='normalize stderr reader')
            self.stderr_thread.start()
        except AbortException as e:
            pass  # Let thread die
        except Exception as e:
            clz.logger.exception(e)

    def stderr_reader(self):
        if Monitor.is_abort_requested():
            self.process.kill()

        clz = RunCommand
        finished = False
        while not (finished or self.cmd_finished):
            try:
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
                    clz.logger.exception(e)
                    finished = True
            except AbortException as e:
                finished = True
            except Exception as e:
                clz.logger.exception(e)
                finished = True

    def stdout_reader(self):
        if Monitor.is_abort_requested():
            self.process.kill()

        clz = RunCommand
        finished = False
        while not (finished or self.cmd_finished):
            try:
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
                    clz.logger.exception(e)
                    finished = True
            except AbortException as e:
                finished = True
            except Exception as e:
                clz.logger.exception(e)
                finished = True

    def log_output(self):
        if Monitor.is_abort_requested():
            return

        clz = RunCommand
        if clz.logger.isEnabledFor(DEBUG):
            if self.rc != 0:
                clz.logger.debug(
                        f'ffmpeg failed for {self.movie_name} rc: {self.rc}')
            if clz.logger.isEnabledFor(DEBUG_VERBOSE):
                stdout = '\n'.join(self.stdout_lines)
                clz.logger.debug_verbose(f'STDOUT: {stdout}')
                stderr = '\n'.join(self.stderr_lines)
                clz.logger.debug_verbose(f'STDERR: {stderr}')
