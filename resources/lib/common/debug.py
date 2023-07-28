# -*- coding: utf-8 -*-

"""
Created on Feb 19, 2019

@author: Frank Feuerbacher
"""
import datetime
import faulthandler
import inspect
import io
import sys
import threading
import traceback
from collections import deque
from io import StringIO
from itertools import chain
from sys import getsizeof

import simplejson as json
import xbmcvfs

from common.critical_settings import CriticalSettings

try:
    from reprlib import repr
except ImportError:
    pass

import xbmc
from common.constants import Constants
from common.logger import *
from common.typing import *

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class Debug:
    """
        Define several methods useful for debugging
    """
    _logger: BasicLogger = module_logger.getChild('Debug')
    _currentAddonName = CriticalSettings.get_plugin_name()

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
        if cls._logger.isEnabledFor(level):
            if data is None:
                cls._logger.log('json None', level=level)
            else:
                dump = json.dumps(data, ensure_ascii=False,
                                  encoding='unicode', indent=4,
                                  sort_keys=True)
                cls._logger.log(f'{text} {dump}', level=level)

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
            cls._logger.exception('')

    @classmethod
    def _dump_all_threads(cls) -> None:
        """
            Worker method that dumps all threads.

        :return:
        """
        try:
            addon_prefix = f'{Constants.ADDON_ID}/'
            xbmc.log('dump_all_threads', xbmc.LOGDEBUG)
            sio = StringIO()
            sio.write('\n*** STACKTRACE - START ***\n\n')
            code = []
            #  Monitor.dump_wait_counts()
            #  for threadId, stack in sys._current_frames().items():
            for th in threading.enumerate():
                frame = sys._current_frames().get(th.ident, None)
                cls._logger.debug(f'isframe: {inspect.isframe(frame)}')
                cls._logger.debug(f'istraceback: {inspect.istraceback(frame)}')
                try:
                    tracebackx  = inspect.getframeinfo(frame)
                    cls._logger.debug(f'frameinfo: {tracebackx.filename}')
                    traceback.print_tb(tracebackx, file=sio)

                except Exception as e:
                    cls._logger.exception('')
                try:
                    tb = traceback.extract_stack(f=frame)
                    cls._logger.debug(f'extract_stack {traceback.print_tb(tb, file=sio)}')
                except Exception as e:
                    cls._logger.exception('') 
                try:
                    frameinfos: List[inspect.FrameInfo] = inspect.getouterframes(frame)
                    cls._logger.debug(f'# frameinfos: {len(frameinfos)}')
                except Exception as e:
                    cls._logger.exception('')

                sio.write(f'\n# ThreadID: {th.name} Daemon: {th.daemon}\n\n')
                if frame:
                    sio.write(f'{traceback.format_stack(frame)}')
                else:
                    sio.write(f'No traceback available for {th.name}')

                # Remove the logger's frames from it's thread.
                # frames: List[inspect.FrameInfo] = inspect.stack(context=1)
                # for frame in frames:
                #     frame: inspect.FrameInfo
                #     sio.write(f'File: "{frame.filename}" line {frame.lineno}. '
                #               f'in {frame.function}\n')
                #     sio.write(f'  {frame.code_context}\n')

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
            except AbortException:
                reraise(*sys.exc_info())
            except Exception as e:
                cls._logger.exception(msg='')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')


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

        all_handlers = {tuple: iter,
                        list: iter,
                        deque: iter,
                        dict: dict_handler,
                        set: iter,
                        frozenset: iter,
                        }
        all_handlers.update(handlers)     # user handlers take precedence
        seen = set()                      # track which object id's have already been seen
        default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

        def sizeof(o):
            if id(o) in seen:       # do not double count the same object
                return 0
            seen.add(id(o))
            s = getsizeof(o, default_size)

            if verbose:
                cls._logger.debug_verbose(f'size: {s} type: {type(o)} repr: {repr(o)}')

            for typ, handler in all_handlers.items():
                if isinstance(o, typ):
                    s += sum(map(sizeof, handler(o)))
                    break
            return s

        return sizeof(o)
