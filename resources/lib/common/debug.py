# -*- coding: utf-8 -*-

"""
Created on Feb 19, 2019

@author: Frank Feuerbacher
"""
import datetime
import faulthandler
import io
import sys
import threading
import traceback
from collections import deque
from io import StringIO
from itertools import chain
from sys import getsizeof

import xbmcvfs

import json as json
from common import *

from common.critical_settings import CriticalSettings

try:
    from reprlib import repr
except ImportError:
    pass

import xbmc
from common.constants import Constants
from common.logger import *

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class Debug:
    """
        Define several methods useful for debugging
    """
    _currentAddonName = CriticalSettings.get_plugin_name()
    _debug_file = None

    @classmethod
    def dump_json(cls, text: str = '', data: Any = '',
                  level: int = DISABLED) -> None:
        """
            Log Json values using the json.dumps utility

        :param text:
        :param data: Any json serializable object
        :param level:
        :return:
        """
        if MY_LOGGER.isEnabledFor(level):
            if data is None:
                MY_LOGGER.log(level=level, msg='json None')
            else:
                dump = json.dumps(data, ensure_ascii=False,
                                  encoding='unicode', indent=4,
                                  sort_keys=True)
                MY_LOGGER.log(level=level, msg=f'{text} {dump}')

    @classmethod
    def dump_all_threads(cls, delay: float = None) -> None:
        """
            Dumps all Python stacks, including those in other plugins

        :param delay:
        :return:
        """
        try:
            if delay is None or delay == 0:
                cls._dump_all_threads()
            else:
                dump_threads = threading.Timer(delay, cls._dump_all_threads)
                dump_threads.name = 'dump_threads'
                dump_threads.start()
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

    @classmethod
    def dump_current_thread(cls) -> None:
        debug_file = StringIO()
        '''
        debug_file = io.open("/home/fbacher/.kodi/temp/kodi.threads", mode='a',
                             buffering=1,
                             newline=None,
                             encoding='ASCII')
        '''
        #  faulthandler.dump_traceback(file=debug_file, all_threads=False)
        #  xbmc.log(debug_file.getvalue())
        #  debug_file.close()
        sio = StringIO()
        sio.write('\n*** STACKTRACE - START ***\n\n')
        th: threading.Thread = threading.current_thread()
        sio.write(f'\n# ThreadID: {th.name} Daemon: {th.daemon}\n\n')
        stack = sys._current_frames().get(th.ident, None)
        if stack is not None:
            traceback.print_stack(stack, file=sio)

        xbmc.log(sio.getvalue() + '\n*** STACKTRACE - END ***\n')

    @classmethod
    def _dump_all_threads(cls) -> None:
        """
            Worker method that dumps all threads.

        :return:
        """
        addon_prefix = f'{Constants.ADDON_ID}/'
        xbmc.log('dump_all_threads', xbmc.LOGDEBUG)
        sio = StringIO()
        sio.write('\n*** STACKTRACE - START ***\n\n')
        code = []
        #  Monitor.dump_wait_counts()
        #  for threadId, stack in sys._current_frames().items():
        for th in threading.enumerate():
            sio.write(f'\n# ThreadID: {th.name} Daemon: {th.daemon}\n\n')
            stack = sys._current_frames().get(th.ident, None)
            if stack is not None:
                traceback.print_stack(stack, file=sio)

        string_buffer: str = sio.getvalue() + '\n*** STACKTRACE - END ***\n'
        sio.close()
        msg = Debug._currentAddonName + ' : dump_all_threads'
        xbmc.log(msg, xbmc.LOGDEBUG)
        xbmc.log(string_buffer, xbmc.LOGDEBUG)

        try:
            dump_path = f'{xbmcvfs.translatePath("special://temp")}' \
                        f'{CriticalSettings.get_plugin_name()}_thread_dump.txt'

            with io.open(dump_path.encode('utf-8'), mode='at', buffering=1,
                         newline=None) as dump_file:

                dump_file.write(f'\n{datetime.datetime.now()}'
                                f'   *** STACKTRACE - START ***\n\n')
                faulthandler.dump_traceback(file=dump_file, all_threads=True)
                dump_file.write(f'\n{datetime.datetime.now()}'
                                f'   *** STACKTRACE - END ***\n\n')

        except Exception as e:
            MY_LOGGER.exception(msg='')

    @classmethod
    def total_size(cls, o, handlers: Dict[Any, Any] = None, verbose: bool = False):
        """ Returns the approximate memory footprint an object and all of its contents.

        Automatically finds the contents of the following builtin containers and
        their subclasses:  tuple, list, deque, dict, set and frozenset.
        To search other containers, add handlers to iterate over their contents:

            handlers = {SomeContainerClass: iter,
                        OtherContainerClass: OtherContainerClass.get_elements}

        """
        if handlers is None:
            handlers = {}

        dict_handler = lambda d: chain.from_iterable(d.items())

        all_handlers = {tuple    : iter,
                        list     : iter,
                        deque    : iter,
                        dict     : dict_handler,
                        set      : iter,
                        frozenset: iter,
                        }
        all_handlers.update(handlers)  # user handlers take precedence
        seen = set()  # track which object id's have already been seen
        default_size = getsizeof(0)  # estimate sizeof object without __sizeof__

        def sizeof(o):
            if id(o) in seen:  # do not double count the same object
                return 0
            seen.add(id(o))
            s = getsizeof(o, default_size)

            if verbose:
                MY_LOGGER.debug_v(f'size: {s} type: {type(o)} repr: {repr(o)}')

            for typ, handler in all_handlers.items():
                if isinstance(o, typ):
                    s += sum(map(sizeof, handler(o)))
                    break
            return s

        return sizeof(o)
