# coding=utf-8
from __future__ import annotations

import math
import queue
import sys
import threading
from pathlib import Path
from queue import Queue

from common import *
from common.garbage_collector import GarbageCollector

from common.logger import *
from common.minimal_monitor import MinimalMonitor
from common.monitor import Monitor
from utils.util import runInThread

MY_LOGGER = BasicLogger.get_logger(__name__)


class Delay:

    def __init__(self, bias: float = 0.0, call_scale_factor: float = 1.0,
                 scale_factor: float = 1.0) -> None:
        """
        Delay simply provides a mechanism to keep from throttling the cpu.
        The delay is designed to increase with each call (although this can
        be overridden). The wait time, in seconds, is:

           delay = bias + log10(number_of_calls * call_scale_factor) * scale_factor

        :param bias: Base amount of time to wait
        :param call_scale_factor: Increases the weight of each call
        :param scale_factor: See formula
        """

        self._bias: float = bias
        self._call_scale_factor = call_scale_factor
        self._scale_factor: float = scale_factor

        self._call_count: int = 0
        self._delay: float = 0.0

    def delay(self, bias: float = None,
              call_scale_factor: float = None,
              scale_factor: float = None,
              timeout: float = None) -> float:
        """
        Waits to keep from throttling the cpu. The wait time depends upon
        the given parameters. The time to wait is returned after the call.

        Note: Can raise AbortException

            number_of_calls += call_increase
            if timeout > 0.0:
                delay = timeout
            else:
                delay = bias + log10(number_of_calls * call_scale_factor) * scale_factor

        :param bias: Base amount of time to wait; replaces value from constructor
        :param call_scale_factor: Increases the weight of each call; replaces
               value from constructor
        :param scale_factor: See formula; replaces value from constructor
        :param timeout: If specified, this overrides the calculated delay
        :return:
        """
        clz = type(self)

        if bias is not None:
            self._bias = float(bias)
        if call_scale_factor is not None:
            self._call_scale_factor = float(call_scale_factor)
        if scale_factor is not None:
            self._scale_factor = float(scale_factor)

        self._call_count += 1

        if MY_LOGGER.isEnabledFor(DISABLED):
            MY_LOGGER.debug_xv(f' bias: {bias} call_count: '
                               f'{self._call_count} call_scale_factor: '
                               f'{self._call_scale_factor:f} scale_factor: '
                               f'{self._scale_factor}')
        _delay: float
        if timeout is not None:
            _delay = float(timeout)
        else:
            # Adding 1.0 ensures that we don't do log10(0)
            _delay = self._bias + (math.log10(1.0 + self._call_count *
                                              self._call_scale_factor)
                                   * self._scale_factor)

        MinimalMonitor.exception_on_abort(_delay)
        return _delay


class FindTextToVoice:

    _logger: BasicLogger = None

    def __init__(self, top: Path) -> None:
        self.unvoiced_files: queue.Queue = queue.Queue(maxsize=200)
        self.glob_pattern: str = '**/*.txt'
        self.finder: FindFiles = FindFiles(top, self.glob_pattern)
        self.worker = threading.Thread
        self.worker = threading.Thread(target=self.find_thread,
                                       name='fndtxt2vce', args=(), kwargs={}, daemon=None)
        self.worker.start()
        GarbageCollector.add_thread(self.worker)


    def get_next(self) -> Path:
        #  Delay one second on each call.
        delay = Delay(bias=1.0, call_scale_factor=0.0, scale_factor=0.0)
        return self.unvoiced_files.get()

    def find_thread(self) -> None:
        clz = type(self)
        path: Path
        try:
            for path in self.finder:
                voice_path: Path = path.with_suffix('.mp3')
                if not voice_path.exists():
                    Monitor.exception_on_abort(timeout=1.0)
                    try:
                        #  MY_LOGGER.debug(f'found .txt without .mp3: {voice_path}')
                        self.unvoiced_files.put_nowait(str(path))
                    except AbortException:
                        reraise(*sys.exc_info())
                    except queue.Full:
                        pass
                    except Exception:
                        MY_LOGGER.exception('')
        except AbortException:
            pass  # End Thread
        except Exception:
            MY_LOGGER.exception('')


class FindFiles(Iterable[Path]):
    _logger: BasicLogger = None

    def __init__(self,
                 top: Path,
                 glob_pattern: str = '**/*'
                 ) -> None:
        """
            Gets all file paths matching the given pattern in
            the sub-tree top.

        :param top:
        :param patterns:
        :return:
        """
        self._die: bool = False
        self._top: Path = top
        self._path: Path = self._top
        self._glob_pattern: str = glob_pattern
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'top: {self._top} path: {self._path} pattern: '
                            f'{self._glob_pattern}')

        self._queue_complete: bool = False

        # Don't make queue too big, just waste lots of memory and cpu building
        # it before it can be used.

        self._file_queue: Queue = Queue(20)
        runInThread(self._run, name=f'FndFil',
                    delay=0.0)

    def _run(self) -> None:
        clz = type(self)
        try:
            # glob uses more resources than iglob since it must build entire
            # list before returning. iglob, returns one at a time.

            for path in self._path.glob(self._glob_pattern):
                path: Path
                #  MY_LOGGER.debug(f'path: {path}')
                inserted: bool = False
                while not inserted:
                    try:
                        if self._die:
                            if MY_LOGGER.isEnabledFor(DEBUG):
                                MY_LOGGER.debug(f'Die')
                            break

                        self._file_queue.put(path, block=False)
                        inserted = True
                    except queue.Full:
                        Monitor.exception_on_abort(timeout=0.25)
                if self._die:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Die')
                    break
        except AbortException:
            self._die = True  # Let thread die

        except Exception as e:
            MY_LOGGER.exception(msg='')
        finally:
            #  MY_LOGGER.debug('queue complete')
            self._queue_complete = True
            if not self._die:
                self._file_queue.put(None)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'exiting die: {self._die}')
            del self._path

    def get_next(self) -> Path | None:
        clz = type(self)
        if self._file_queue is None:
            #  MY_LOGGER.debug('get_next returning None')
            return None

        next_path: Path | None = None
        while next_path is None:
            try:
                Monitor.exception_on_abort(timeout=0.1)
                next_path: Path = self._file_queue.get(timeout=0.01)
                self._file_queue.task_done()
            except queue.Empty:
                # Empty because we are done, or empty due to timeout
                if self._queue_complete:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug('Queue empty')
                    self._file_queue = None
                    break
                    '''
                    try:
                        GarbageCollector.add_thread(self._find_thread)
                    except Exception as e:
                        MY_LOGGER.exception(msg='')
                    finally:
                    
                        self._find_thread = None
                        self._file_queue = None
                        break
                    '''
            except AbortException:
                reraise(*sys.exc_info())

            except BaseException as e:
                MY_LOGGER.exception(msg='')

        #  MY_LOGGER.debug(f'next_path: {next_path}')
        return next_path

    def kill(self):
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('In kill, die')
        self._die = True

    def __iter__(self) -> Iterator:
        clz = type(self)
        #  MY_LOGGER.debug('in __iter__')
        return FindFilesIterator(self)


class FindFilesIterator(Iterator):

    _logger: BasicLogger = None

    def __init__(self, files: FindFiles):
        #  MY_LOGGER.debug(f'In __init__')

        self._files: FindFiles = files

    def __next__(self) -> Path:
        path: Path = None
        clz = type(self)
        #  MY_LOGGER.debug('In __next__')
        try:
            path: Path = self._files.get_next()
            # MY_LOGGER.debug(f'__next__ path: {path}')
        except AbortException:
            reraise(*sys.exc_info())

        except Exception as e:
            MY_LOGGER.exception(msg='')

        if path is None:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('iterator path None raising StopIteration')
            raise StopIteration()

        return path

    def __del__(self):
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'FindFilesIterator _files.kill')
        self._files.kill()
