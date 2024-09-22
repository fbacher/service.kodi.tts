# -*- coding: utf-8 -*-

"""
Created on Feb 10, 2019

@author: Frank Feuerbacher
"""

import threading

import xbmc

from common import *

#  from common.get import *
from common.monitor import Monitor


class GarbageCollector:
    """

    """
    _lock = threading.RLock()
    _stopped = False
    _threads_to_join: List[threading.Thread] = []
    GARBAGE_COLLECTOR_THREAD_NAME: Final[str] = 'thrd_gc'
    garbage_collector: threading.Thread = None

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
                    xbmc.log(f'garbage_collector adding {thread.name}')
                    # if cls._logger.isEnabledFor(DISABLED):
                    #     cls._logger.debug_xv(f'Adding thread: {thread.name} '
                    #                                     f'{thread.ident}')
                else:
                    pass
                    # if cls._logger.isEnabledFor(DEBUG_XV):
                    #     cls._logger.debug_xv(
                    #         f'Duplicate thread: {thread.name} '
                    #         f'{thread.ident}')

    @classmethod
    def init_class(cls):
        # if cls._logger is None:
        #     cls._logger = module_logger

        cls.garbage_collector = threading.Thread(
                target=cls.join_dead_threads,
                name=cls.GARBAGE_COLLECTOR_THREAD_NAME,
                daemon=False)

        cls.garbage_collector.start()

        # Did not see thread name while using debugger.
        cls.garbage_collector.name = cls.GARBAGE_COLLECTOR_THREAD_NAME

    @classmethod
    def join_dead_threads(cls) -> None:
        finished = False
        # Sometimes thread name doesn't get set.
        threading.current_thread.__name__ = cls.GARBAGE_COLLECTOR_THREAD_NAME
        try:
            while Monitor.exception_on_abort(timeout=2.0):
                cls.reap_the_dead()
        except AbortException:
            cls.abort_notification()

    @classmethod
    def reap_the_dead(cls) -> int:
        live_threads: int = 0
        with cls._lock:
            joined_threads: List[threading.Thread] = []
            for thread in cls._threads_to_join:
                if not thread.is_alive() and thread.name != cls.GARBAGE_COLLECTOR_THREAD_NAME:
                    # if cls._logger.isEnabledFor(DISABLED):
                    #     cls._logger.debug_xv(
                    #             f'Purging dead thread: {thread.name} '
                    #             f'{thread.ident}')
                    thread.join(timeout=0.001)
                    joined_threads.append(thread)
                else:
                    live_threads += 1
            for thread in joined_threads:
                # if cls._logger.isEnabledFor(DISABLED):
                #     cls._logger.debug_xv(f'Removing dead thread: '
                #                                     f'{thread.name} '
                #                                     f'{thread.ident}')
                xbmc.log(f'garbage_collector joined: {thread.name} live: {live_threads}',
                         xbmc.LOGDEBUG)
                cls._threads_to_join.remove(thread)
        return live_threads

    @classmethod
    def abort_notification(cls):
        """
        ABORT HAS OCCURRED. Shut down fast and capture dump of stragglers
        :return:
        """
        xbmc.log(f'In GarbageCollector abort_notification')
        with cls._lock:
            cls.reap_the_dead()
            for thread in cls._threads_to_join:
                xbmc.log(f'garbage_collector remaining thread: {thread.name}')
        # cls._stopped = True
        finished = True
        # del cls._threads_to_join


GarbageCollector.init_class()
