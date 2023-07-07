# -*- coding: utf-8 -*-

"""
Created on Feb 19, 2019

@author: Frank Feuerbacher

"""

import threading

import xbmc
from common.imports import *
from common.exceptions import AbortException
from .__init__ import *


class MinimalMonitor(xbmc.Monitor):
    """
        Provides a wrapper around waitForAbort to avoid several problems:
           1) There are issues with calling xbmc.monitor.waitForAbort on
              multiple threads. Best luck seems to be always running it on
              main thread.
           2) _abort_received Event is set once waitForAbort indicates abort
              has occured. Other threads, via Monitor.py utilize this.

        During startup, we try to reduce dependencies. So here we use xbmc.log
        instead of BasicLogger.


        See Monitor.py for higher level methods
    """
    _initialized: bool = False
    _xbmc_monitor: xbmc.Monitor = None
    _abort_received: threading.Event = None
    _abort_callback: Callable[[], None]  = None


    """
    xbmc wants to be called.
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def class_init(cls) -> None:
        """

        """
        if not cls._initialized:
            cls._initialized = True
            # Weird problems with recursion if we make requests to the super

            cls._xbmc_monitor = xbmc.Monitor()
            cls._abort_received = threading.Event()

    @classmethod
    def real_waitForAbort(cls, timeout: float = -1.0) -> bool:
        """
        Wait for Abort

        Block until abort is requested, or until timeout occurs. If an abort
        requested have already been made, return immediately.

        This method is the only one which calls xbmc.Monitor.waitForAbort. It is
        only called from the Main thread in a main module for the plugin. This is
        done because their is some weirdness about calling Monitor.waitForAbort
        from a non-main thread.

        :param timeout: [opt] float - timeout in seconds.
                        if -1 or None: wait forever
                        if 0: check without wait & return
                        if > 0: wait at max wait seconds

        :return: True when abort has been requested,
            False if a timeout is given and the operation times out.

        New function added.
        """
        abort = False
        if timeout is None or timeout < 0.0:  # Wait forever
            while not abort:
                abort = cls._xbmc_monitor.waitForAbort(timeout=0.10)
        else:
            timeout_arg = float(timeout)
            if timeout_arg == 0.0:
                timeout_arg = 0.001  # Otherwise waits forever

            # cls.track_wait_call_counts('real')
            abort = cls._xbmc_monitor.waitForAbort(timeout=timeout_arg)
            # cls.track_wait_return_counts('real')

        if abort:
            cls.set_abort_received()

        return abort

    @classmethod
    def abort_requested(cls) -> None:
        abort: bool = cls._xbmc_monitor.abortRequested()
        if abort:
            cls.set_abort_received()

    @classmethod
    def set_abort_received(cls):
        if not cls._abort_received.is_set():
            cls._abort_received.set()
            if MinimalMonitor._abort_callback is not None:
                MinimalMonitor._abort_callback()

    @classmethod
    def exception_on_abort(cls, timeout: float = 0) -> None:
        """
         Throws an AbortException if Abort has been set within the specified
          time period.

            If timeout = 0, then immediately returns without exception if
             Abort is not set, or with an AbortException if it
             is set.
            if timeout = None, then wait forever until abort is set.
            Otherwise, wait a maximum of the specified time in seconds.
        :param timeout:
        :return:

        Note: Included in minimal_monitor so that startup code can
              call without dragging in BasicLogger.
        """
        #  cls.track_wait_call_counts()
        if cls._abort_received.wait(timeout=timeout):
            raise AbortException()
        #  cls.track_wait_return_counts()

    @classmethod
    def register_abort_callback(cls, callback: Callable[[], None]) -> None:
        MinimalMonitor._abort_callback = callback


# Initialize class:
#
MinimalMonitor.class_init()
