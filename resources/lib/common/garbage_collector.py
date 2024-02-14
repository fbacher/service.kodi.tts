# -*- coding: utf-8 -*-

"""
Created on Feb 10, 2019

@author: Frank Feuerbacher
"""

import threading

from common import *

from common.logger import *
from common.monitor import Monitor

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class GarbageCollector:
    """

    """
    _lock = threading.RLock()
    _stopped = False
    _threads_to_join: List[threading.Thread] = []
    _logger: BasicLogger = None

    def __init__(self) -> None:
        raise NotImplemented()

    @classmethod
    def add_thread(cls, thread: threading.Thread) -> None:
        if thread is None:
            return
        with cls._lock:
            if not cls._stopped:
                if thread not in cls._threads_to_join:
                    cls._threads_to_join.append(thread)
                    if cls._logger.isEnabledFor(DISABLED):
                        cls._logger.debug_extra_verbose(f'Adding thread: {thread.name} '
                                                        f'{thread.ident}')
                else:
                    if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                        cls._logger.debug_extra_verbose(
                            f'Duplicate thread: {thread.name} '
                            f'{thread.ident}')

    @classmethod
    def init_class(cls):
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)

        garbage_collector = threading.Thread(
                target=cls.join_dead_threads,
                name='thread_gc',
                daemon=False)

        garbage_collector.start()

        # Did not see thread name while using debugger.
        garbage_collector.name = 'Thread garbage collection'

    @classmethod
    def join_dead_threads(cls) -> None:
        finished = False
        # Sometimes thread name doesn't get set.
        threading.current_thread.__name__ = 'Thread garbage collection'
        while not finished:
            with cls._lock:
                joined_threads: List[threading.Thread] = []
                for thread in cls._threads_to_join:
                    if not thread.is_alive():
                        if cls._logger.isEnabledFor(DISABLED):
                            cls._logger.debug_extra_verbose(
                                    f'Purging dead thread: {thread.name} '
                                    f'{thread.ident}')
                        joined_threads.append(thread)
                    else:
                        if cls._logger.isEnabledFor(DISABLED):
                            cls._logger.debug_extra_verbose(
                                    f'Joining thread: {thread.name} '
                                    f'{thread.ident}')
                        thread.join(timeout=0.2)
                        if not thread.is_alive():
                            if cls._logger.isEnabledFor(DISABLED):
                                cls._logger.debug_extra_verbose(
                                        f'Purging dead thread: {thread.name} '
                                        f'{thread.ident}')
                            joined_threads.append(thread)

                for thread in joined_threads:
                    if cls._logger.isEnabledFor(DISABLED):
                        cls._logger.debug_extra_verbose(f'Removing dead thread: '
                                                        f'{thread.name} '
                                                        f'{thread.ident}')
                    cls._threads_to_join.remove(thread)

            if Monitor.wait_for_abort(timeout=1.0):
                cls._stopped = True
                finished = True
                del cls._threads_to_join


GarbageCollector.init_class()
