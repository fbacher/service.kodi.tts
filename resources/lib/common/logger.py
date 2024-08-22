# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

"""
Created on 2/3/22

@author: Frank Feuerbacher
"""

import inspect
import logging
import os
import sys
import threading
import traceback
import warnings
from io import StringIO
from logging import *
from pathlib import Path

import xbmc
import xbmcaddon
import xbmcvfs

from common import *

__all__ = ['BASIC_FORMAT', 'CRITICAL', 'DEBUG', 'DEBUG_VERBOSE',
           'DEBUG_EXTRA_VERBOSE', 'ERROR', 'DISABLED',
           'FATAL', 'FileHandler', 'Filter', 'Formatter', 'Handler', 'INFO',
           'LogRecord', 'BasicLogger', 'LoggerAdapter', 'NOTSET', 'NullHandler',
           'StreamHandler', 'WARN', 'WARNING', 'addLevelName', 'basicConfig',
           'captureWarnings', 'critical', 'debug', 'disable', 'error',
           'exception', 'fatal', 'getLevelName', 'getLogger', 'getLoggerClass',
           'info', 'log', 'makeLogRecord', 'setLoggerClass', 'shutdown',
           'warn', 'warning', 'getLogRecordFactory', 'setLogRecordFactory',
           'lastResort', 'raiseExceptions', 'Trace']

from common.critical_settings import CriticalSettings

ADDON_ID: str = CriticalSettings.ADDON_ID
ADDON: xbmcaddon = CriticalSettings.ADDON

# If you have a setting that controls whether to log, then specify the
# setting name here. Otherwise, define DEFAULT_INCLUDE_THREAD_INFO

DEFAULT_LOG_LEVEL: int = CriticalSettings.get_logging_level()

# Controls what is printed by logging formatter

INCLUDE_THREAD_INFO: bool = CriticalSettings.is_debug_include_thread_info()
INCLUDE_THREAD_LABEL: bool = True
INCLUDE_DEBUG_LEVEL: bool = True

# Define extra log levels in between predefined values.

DISABLED = NOTSET  # Simply to be able to use DISABLED to clearly mark non-logged code
# DEBUG_VERBOSE = 8
# DEBUG_EXTRA_VERBOSE = 6
NOTSET = logging.NOTSET  # 0

#  XBMC levels
LOGDEBUG: Final[int] = xbmc.LOGDEBUG
LOGINFO: Final[int] = xbmc.LOGINFO
LOGWARNING: Final[int] = xbmc.LOGWARNING
LOGERROR: Final[int] = xbmc.LOGERROR
LOGFATAL: Final[int] = xbmc.LOGFATAL
LOGNONE: Final[int] = xbmc.LOGNONE

#  Kodi BasicLogger values (in addition to those defined in logging)

DEBUG_VERBOSE: Final[int] = 8
DEBUG_EXTRA_VERBOSE: Final[int] = 6

INCLUDE_MODULE_PATH_IN_LOGGER: bool = True

# DEBUG, DEBUG_VERBOSE AND DEBUG_EXTRA_VERBOSE will all print as xbmc.DEBUG
# messages, however the message text will indicate their debug level.

logging_to_kodi_level = {DISABLED: 100,
                         FATAL: xbmc.LOGFATAL,
                         ERROR: xbmc.LOGERROR,
                         WARNING: xbmc.LOGWARNING,
                         INFO: xbmc.LOGINFO,
                         DEBUG_EXTRA_VERBOSE: xbmc.LOGDEBUG,
                         DEBUG_VERBOSE: xbmc.LOGDEBUG,
                         DEBUG: xbmc.LOGDEBUG}


def get_kodi_level(logging_level: int) -> int:
    """
    Transforms logger logging level to Kodi log level

    :param logging_level:
    :return:
    """
    return logging_to_kodi_level.get(logging_level, None)


class BasicLogger(Logger):
    """
          Provides logging capabilities that are more convenient than
          xbmc.log.

          Typical usage:

          class abc:
              def __init__(self):
                  self._debug_logger = BasicLogger(self.__class__.__name__)

              def method_a(self):
                  local_logger = self._debug_logger('method_a')
                  local_logger.debug('enter')
                  ...
                  local_logger.debug(f'something happenedL value1: '
                                     f'{value1}')
                  local_logger.debug()

          In addition, there is the Trace class which provides more granularity
          for controlling what messages are logged as well as tagging of the
          messages for searching the logs.

      """

    @classmethod
    def _class_init_(cls):
        setLoggerClass(cls)
        Logger.manager.setLoggerClass(cls)

    def __init__(self, name, level=DEFAULT_LOG_LEVEL):
        super().__init__(name, level)

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """
            Creates a log entry

            Note, the default xbmc.log logging level is xbmc.LOGDEBUG. This can
            be overridden by including the kwarg {'level' : xbmc.<level>}

        :param level: Debugging level
        :param msg: Message to print
        :param args: Arbitrary arguments.
        :param kwargs: str Some possible values:
                        'exc_info'
                        'notify=true'
                        'start_frame'
                        'trace'
                        'test_expected_stack_top'
                        'test_expected_stack_file'
                        'test_expected_stack_method'

        :return:
        """
        """
        Log 'msg % args' with the integer severity 'level'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.log(level, "We have a %s", "mysterious problem", exc_info=1)
        """
        if not isinstance(level, int):
            if raiseExceptions:
                raise TypeError("level must be an integer")
            else:
                return
        if self.isEnabledFor(level):
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs.pop('ignore_frames') + 2  # 1
            trace = kwargs.pop('trace', None)
            notify: str = kwargs.pop('notify', None)

            extra: Dict[str, Any] = kwargs.setdefault('extra', {})
            extra['addon_name'] = CriticalSettings.get_plugin_name()
            extra['trace'] = trace
            if notify is not None:
                extra['notify'] = notify
            #  extra['start_file'] = start_file,
            extra['ignore_frames'] = ignore_frames
            if extra is not None:
                kwargs['extra'] = extra
            kwargs['stacklevel'] = ignore_frames  # - 1

            # Call super._log directly to avoid having to compensate for
            # ignore_frames count going through two methods...

            super()._log(level, msg, args, **kwargs)

    @classmethod
    def get_logger(cls,
                   file_path: str = None,
                   class_name: str = None,
                   clz=None) -> ForwardRef('BasicLogger'):
        module_logger: BasicLogger = cls.get_module_logger(module_path=file_path)
        if module_logger is None:
            return None
        elif clz is not None:
            return module_logger.getChild(clz.__name__)
        elif class_name is not None:
            return module_logger.getChild(class_name)
        else:
            return module_logger

    @staticmethod
    def get_addon_logger() -> ForwardRef('BasicLogger'):
        root_logger: BasicLogger | Logger = getLogger()
        addon_logger: BasicLogger = root_logger.getChild(
            CriticalSettings.get_plugin_name())
        return addon_logger

    @staticmethod
    def set_log_level(log_level: int) -> None:
        # root_logger: BasicLogger | Logger = getLogger()
        # root_logger.setLevel(log_level)
        addon_logger: BasicLogger = BasicLogger.get_addon_logger()
        addon_logger.setLevel(log_level)
        for my_handler in addon_logger.handlers:
            my_handler.setLevel(log_level)

    @classmethod
    def get_module_logger(cls,
                          module_path: str | Path = None) -> ForwardRef('BasicLogger'):
        """
            Creates a logger based upon something like the python module naming
            convention. Ex: lib.common.playlist.<classname>

            module_path is path to the module (typically use value of __file__)
            addon_name only needs to be supplied as the very first
        :return:
        """
        logger: BasicLogger = None

        root_logger = getLogger()
        addon_logger: BasicLogger | Logger = root_logger.getChild(
            CriticalSettings.get_plugin_name())

        # Calculate the module path relative to the TOP_PACKAGE_PATH

        if INCLUDE_MODULE_PATH_IN_LOGGER:
            if module_path is not None:
                file_path: str = str(module_path).replace('.py', '', 1)
                # xbmc.log(f'TOP_PACKAGE_PATH: {TOP_PACKAGE_PATH} '
                #          f'file_path: {file_path}')
                suffix = file_path.replace(str(CriticalSettings.TOP_PACKAGE_PATH), '', 1)
                suffix = suffix.replace('/', '.')
                if suffix.startswith('.'):
                    suffix = suffix.replace('.', '', 1)
                    # xbmc.log(f'suffix: {suffix}')

                logger = addon_logger.getChild(suffix)
                #  xbmc.log(f'Created logger: {logger}')
            else:
                root_logger.debug('Expected file_path')

            # xbmc.log(f'Returning logger: {logger}')
        return logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log 'msg % args' with severity 'DEBUG'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.debug("Houston, we have a %s", "thorny problem", exc_info=1)
        """
        if self.isEnabledFor(DEBUG):
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames
            self.log(DEBUG, msg, *args, **kwargs)

    def debug_verbose(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
            Convenience method for log(xxx kwargs['level' : xbmc.LOGDEBUG)
        :param msg: Message to log
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        if self.isEnabledFor(DEBUG_VERBOSE):
            ignore_frames: int = kwargs.setdefault('ignore_frames', 0) + 1
            kwargs['ignore_frames'] = ignore_frames

        self.log(DEBUG_VERBOSE, msg, *args, **kwargs)

    def debug_extra_verbose(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
            Convenience method for log(xxx kwargs['level' : xbmc.LOGDEBUG)
        :param msg: Message to log
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        if self.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames

            self.log(DEBUG_EXTRA_VERBOSE, msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log 'msg' with severity 'INFO'.

        :param msg: Message to log

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.info("Houston, we have a %s", "interesting problem", exc_info=1)
        """
        if self.isEnabledFor(INFO):
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames
            self.log(INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log 'msg % args' with severity 'WARNING'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.warning("Houston, we have a %s", "bit of a problem", exc_info=1)
        """
        if self.isEnabledFor(WARNING):
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames
            self.log(WARNING, msg, *args, **kwargs)

    def warn(self, msg: str, *args: Any, **kwargs: Any) -> None:
        warnings.warn("The 'warn' method is deprecated, "
                      "use 'warning' instead", DeprecationWarning, 2)
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames
        self.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log 'msg % args' with severity 'ERROR'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.error("Houston, we have a %s", "major problem", exc_info=1)
        """
        if self.isEnabledFor(ERROR):
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames
            self.log(ERROR, msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, exc_info: bool = True,
                  **kwargs: Any):
        """
        Convenience method for logging an ERROR with exception information.
        """
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames
        kwargs['stack_info'] = True
        if msg is None:
            msg = ''
        self.error(msg, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any):
        """
        Log 'msg % args' with severity 'CRITICAL'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.critical("Houston, we have a %s", "major disaster", exc_info=1)
        """
        if self.isEnabledFor(CRITICAL):
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames
            self._log(CRITICAL, msg, *args, **kwargs)

    fatal = critical

    @classmethod
    def dump_stack(cls, msg: str = '', level: int = DEBUG, all_threads: bool = False,
                   heading: str = '',
                   ignore_frames: int = 0, limit: int = None) -> None:
        """
        Dumps the stack for the current thread.

        :param msg: Message text to include
        :param level: Debug level. Will not be printed unless enabled
        for this level of debug.
        :param all_threads: Dumps the stack for all threads
        :param heading:
        :param ignore_frames: Indicates how many stack frames to ignore
        :param limit:
        :return:

        ignore_frames is used to adjust for how many method/function
        calls are added to the stack between when the stack-dump was
        originally requested and when it is actually processed. For
        each intermedia call, ignore_frames is incremented by 1.
        """

        if get_addon_logger().isEnabledFor(level):
            for th in threading.enumerate():
                print(th)
                traceback.print_stack(sys._current_frames()[th.ident])
                print()

            ignore_frames += 1
            sio: StringIO = StringIO()
            sio.write('LEAK Traceback StackTrace StackDump\n')
            sio.write(f'{msg}\n')

            current_thread = threading.current_thread()
            if all_threads:
                threads_to_dump = threading.enumerate()
            else:
                threads_to_dump = [current_thread]

            for th in threads_to_dump:
                th: threading.Thread
                sio.write(f'\n# ThreadID: {th.name} Daemon: {th.daemon}\n\n')
                traceback.print_stack(th, file=sio)

            '''
            # Remove the logger's frames from it's thread.
                # frames: List[inspect.FrameInfo] = inspect.stack(context=1)

                if th == current_thread:
                    frames_to_ignore = ignore_frames
                else:
                    frames_to_ignore = 0

                for frame in frames[ignore_frames::]:
                    frame: inspect.FrameInfo
                    sio.write(f'File: "{frame.filename}" line {frame.lineno}. '
                              f'in {frame.function}\n')
                    sio.write(f'  {frame.code_context}\n')
            '''
            kwargs: Any = {}
            msg: str = sio.getvalue()
            sio.close()
            del sio
            get_addon_logger().debug(msg=msg, **kwargs)

    @classmethod
    def showNotification(cls, message, time_ms=3000, icon_path=None,
                         header=CriticalSettings.ADDON_ID):
        try:
            icon_path = icon_path or xbmcvfs.translatePath(
                    xbmcaddon.Addon(CriticalSettings.ADDON_ID).getAddonInfo('icon'))
            xbmc.executebuiltin('Notification({0},{1},{2},{3})'.format(
                    header, message, time_ms, icon_path))
        except RuntimeError:  # Happens when disabling the addon
            pass

    @staticmethod
    def on_settings_changed() -> None:
        """

        :return:
        """
        logging_level = CriticalSettings.get_logging_level()
        get_addon_logger().setLevel(logging_level)


BasicLogger._class_init_()


class KodiHandler(logging.Handler):
    """
      Defines a handler for writing to Kodi's logging system.
    """

    def __init__(self, level: int = logging.NOTSET,
                 trace: Set[str] = None) -> None:
        """

        :param level:
        :param trace:
        """

        self._trace = trace
        self._ignore_frames: int = 0

        super().__init__(level=level)
        self.setFormatter(KodiFormatter())

    def handle(self, record):
        try:
            super().handle(record)
        except Exception as e:
            self.handleError(record)

    def emit(self, record: logging.LogRecord) -> None:
        """

        :param record:
        :return:
        """

        try:
            if record.exc_info is not None:
                self._ignore_frames = record.__dict__.get('ignore_frames', 0) + 4
                msg = self.formatter.formatException(record.exc_info)
                record.exc_text = msg
            msg = self.formatter.format(record)
            if record.__dict__.get('notify', False):
                self.showNotification(msg)
            kodi_level = get_kodi_level(record.levelno)
            xbmc.log(msg, kodi_level)
        except Exception as e:
            self.handleError(record)

    def showNotification(self, message, time_ms=3000, icon_path=None,
                         header=CriticalSettings.ADDON_ID):
        try:
            icon_path = icon_path or xbmcvfs.translatePath(
                    xbmcaddon.Addon(CriticalSettings.ADDON_ID).getAddonInfo('icon'))
            xbmc.executebuiltin('Notification({0},{1},{2},{3})'.format(
                    header, message, time_ms, icon_path))
        except RuntimeError:  # Happens when disabling the addon
            pass

    def handleError(self, record):
        """
        Handle errors which occur during an emit() call.

        (Lifted from logging and modified to write to kodi log
        instead of stderr. This avoids annoying formatting).

        This method should be called from handlers when an exception is
        encountered during an emit() call. If raiseExceptions is false,
        exceptions get silently ignored. This is what is mostly wanted
        for a logging system - most users will not care about errors in
        the logging system, they are more interested in application errors.
        You could, however, replace this with a custom handler if you wish.
        The record which was being processed is passed in to this method.
        """
        if raiseExceptions:  # see issue 13807
            t, v, tb = sys.exc_info()
            sio = StringIO()
            try:
                sio.write('--- Logging error ---\n')
                traceback.print_exception(t, v, tb, None, sys.stderr)
                sio.write('Call stack:\n')
                # Walk the stack frame up until we're out of logging,
                # so as to print the calling context.
                frame = tb.tb_frame
                while (frame and os.path.dirname(frame.f_code.co_filename) ==
                       __file__[0]):
                    frame = frame.f_back
                if frame:
                    traceback.print_stack(frame, file=sio)
                else:
                    # couldn't find the right stack frame, for some reason
                    sio.write('Logged from file %s, line %s\n' % (
                        record.filename, record.lineno))
                # Issue 18671: output logging message and arguments
                try:
                    sio.write('Message: %r\n'
                              'Arguments: %s\n' % (record.msg,
                                                   record.args))
                except RecursionError:  # See issue 36272
                    raise
                except Exception:
                    sio.write('Unable to print the message and arguments'
                              ' - possible formatting error.\nUse the'
                              ' traceback above to help find the error.\n'
                              )
            except OSError:  # pragma: no cover
                pass  # see issue 5971
            finally:
                xbmc.log(sio.getvalue(), xbmc.LOGDEBUG)
                sio.close()
                del sio
                del t, v, tb


class KodiFormatter(logging.Formatter):
    """

    """

    def __init__(self, fmt=None, datefmt=None, style='%', validate=True):
        """
        Initialize the formatter with specified format strings.

        Initialize the formatter either with the specified format string, or a
        default as described above. Allow for specialized date formatting with
        the optional datefmt argument. If datefmt is omitted, you get an
        ISO8601-like (or RFC 3339-like) format.

        Use a style parameter of '%', '{' or '$' to specify that you want to
        use one of %-formatting, :meth:`str.format` (``{}``) formatting or
        :class:`string.Template` formatting in your format string.

        .. versionchanged:: 3.2
           Added the ``style`` parameter.
        """
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)

    def format(self, record: logging.LogRecord) -> str:
        """

        :param record:
        :return:
        """

        """
            Attribute name 	Format 	Description
            args 	You shouldn’t need to format this yourself. 	The tuple of 
            arguments merged into msg to produce message, or a dict whose values are 
            used for the merge (when there is only one argument, and it is a dictionary).
            asctime 	%(asctime)s 	Human-readable time when the LogRecord was 
            created. By default this is of the form ‘2003-07-08 16:49:45,896’ (the 
            numbers after the comma are millisecond portion of the time).
            created 	%(created)f 	Time when the LogRecord was created (as returned 
            by time.time()).
            exc_info 	You shouldn’t need to format this yourself. 	Exception tuple 
            (à la sys.exc_info) or, if no exception has occurred, None.
            filename 	%(filename)s 	Filename portion of pathname.
            funcName 	%(funcName)s 	Name of function containing the logging call.
            levelname 	%(levelname)s 	Text logging level for the message ('DEBUG', 
            'INFO', 'WARNING', 'ERROR', 'CRITICAL').
            levelno 	%(levelno)s 	Numeric logging level for the message (DEBUG, 
            INFO, WARNING, ERROR, CRITICAL).
            lineno 	%(lineno)d 	Source line number where the logging call was issued (if 
            available).
            module 	%(module)s 	Module (name portion of filename).
            msecs 	%(msecs)d 	Millisecond portion of the time when the LogRecord was 
            created.
            message 	%(message)s 	The logged message, computed as msg % args. This 
            is set when Formatter.format() is invoked.
            msg 	You shouldn’t need to format this yourself. 	The format string 
            passed in the original logging call. Merged with args to produce message, 
            or an arbitrary object (see Using arbitrary objects as messages).
            name 	%(name)s 	Name of the config_logger used to log the call.
            pathname 	%(pathname)s 	Full pathname of the source file where the 
            logging call was issued (if available).
            process 	%(process)d 	Process ID (if available).
            processName 	%(processName)s 	Process name (if available).
            relativeCreated 	%(relativeCreated)d 	Time in milliseconds when the 
            LogRecord was created, relative to the time the logging module was loaded.
            stack_info 	You shouldn’t need to format this yourself. 	Stack frame 
            information (where available) from the bottom of the stack in the current 
            thread, up to and including the stack frame of the logging call which 
            resulted in the creation of this record.
            thread 	%(thread)d 	Thread ID (if available).
            threadName 	%(threadName)s 	Thread name (if available).

            [service.randomtrailers.backend:DiscoverTmdbMovies:process_page] 
            [service.randomtrailers.backend:FolderMovieData:add_to_discovered_movies  
            TRACE_DISCOVERY]
        """
        # threadName Constants.CURRENT_ADDON_SHORT_NAME funcName:lineno
        # [threadName name funcName:lineno]

        text = ''
        clz = Logger
        try:
            '''
            start_file = record.__dict__.get('start_file', None)
            try:
                pathname, lineno, func = start_file
            except ValueError:
                pathname, lineno, func = "(unknown file)", 0, "(unknown function)"

            record.pathname = pathname
            try:
                record.filename = os.path.basename(pathname)
                record.module = os.path.splitext(record.filename)[0]
            except (TypeError, ValueError, AttributeError):
                record.filename = pathname
                record.module = "Unknown module"
            record.lineno = lineno
            record.funcName = func
            '''

            addon_name: str = record.__dict__.get('addon_name', None)

            suffix = super().format(record)
            thread_field: str = ''
            if INCLUDE_THREAD_INFO:
                if INCLUDE_THREAD_LABEL:
                    thread_label = 'T:'
                else:
                    thread_label = ''
                thread_field = f'{thread_label}{record.threadName} '

            if INCLUDE_DEBUG_LEVEL:
                level = record.levelname
            else:
                level = ''

            module_path: str = ''
            addon_label: str = ''
            if addon_name is not None:
                addon_label = f'{addon_name} '

                # In addition to having addon_name to print, the addon_name
                # is also the first level node name of the record.name.
                # To keep from looking stupid, and to reduce line length,
                # remove the addon_name from the record.name.

                if record.name.startswith(addon_name):
                    module_path = record.name[len(addon_name) + 1:]  # Add 1 for '.'
            else:
                module_path = record.name

            func_name: str = ''
            if record.funcName != '<module>':
                func_name = f'.{record.funcName}'

            passed_traces = record.__dict__.get('trace_string', None)
            if passed_traces is not None:
                passed_traces = f' Trace: {passed_traces}'
            else:
                passed_traces = ''

            prefix = (f'[{thread_field}{addon_label}{module_path}{func_name}:'
                      f'{record.lineno}:{level}{passed_traces}]')

            text = f'{prefix} {suffix}'

        # Let emit handle exceptions
        #
        #  except Exception as e:
        #     pass
        finally:
            pass

        return text

    def formatException(self, ei: List[Any] = None,
                        ignore_frames: int = 0) -> str:
        """

        :param ei:
        :param ignore_frames:
        :return:
        """
        ignore_frames += 1
        if ei is not None:
            thread_name = threading.current_thread().getName()

            sio = StringIO()
            '''
            xtraceback.print_exception(etype, value, tb, limit=None, file=log_file, 
            chain=True)
print_exception(etype: Type = None,
                    value: Any = None,
                    tb: Any = None,
                    thread_name: str = '',
                    limit: int = None,
                    ignore_frames: int = 0,
                    log_file: StringIO = None '''

            traceback.print_exception(ei[0], ei[1], ei[2], limit=None, file=sio)
            s = sio.getvalue()
            sio.close()
            return s


class Trace(logging.Filter):
    """

    """
    TRACE: Final[str] = 'TRACE'
    TRACE_STATS: Final[str] = 'STATS'
    TRACE_CONFIG: Final[str] = 'UI'
    STATS_UI: Final[str] = 'STATS_UI'
    TRACE_DISCOVERY: Final[str] = 'DISCOVERY'
    TRACE_FETCH: Final[str] = 'FETCH'
    TRACE_AUDIO_START_STOP: Final[str] = 'TRACE_AUDIO_START_STOP'
    TRACE_PROCESS: Final[str] = 'TRACE_PROCESS'
    # TRACE_GENRE: Final[str] = 'GENRE'
    # TRACE_CERTIFICATION: Final[str] = 'CERTIFICATION'
    TRACE_CACHE_GARBAGE_COLLECTION: Final[str] = 'CACHE_GC'
    # TRACE_TFH: Final[str] = 'TFH'
    STATS_DISCOVERY: Final[str] = 'STATS_DISCOVERY'
    STATS_CACHE: Final[str] = 'STATS_CACHE'
    TRACE_MONITOR: Final[str] = 'MONITOR'
    TRACE_JSON: Final[str] = 'JSON'
    # TRACE_SCREENSAVER: Final[str] = 'SCREENSAVER'
    TRACE_UI_CONTROLLER: Final[str] = 'UI_CONTROLLER'
    TRACE_CACHE_MISSING: Final[str] = 'CACHE_MISSING'
    TRACE_CACHE_UNPROCESSED: Final[str] = 'CACHE_UNPROCESSED'
    # TRACE_CACHE_PAGE_DATA: Final[str] = 'CACHE_PAGE_DATA'
    TRACE_TRANSLATION: Final[str] = 'TRANSLATION'
    TRACE_SHUTDOWN: Final[str] = 'SHUTDOWN'
    # TRACE_PLAY_STATS: Final[str] = 'PLAY_STATISTICS'
    # TRACE_NETWORK: Final[str] = 'TRACE_NETWORK'

    TRACE_ENABLED: Final[bool] = True
    TRACE_DISABLED: Final[bool] = False

    _trace_map: Final[Dict[str, bool]] = {
        TRACE: TRACE_DISABLED,
        TRACE_STATS: TRACE_DISABLED,
        # TRACE_UI: TRACE_DISABLED,
        TRACE_DISCOVERY: TRACE_DISABLED,
        TRACE_FETCH: TRACE_DISABLED,
        TRACE_AUDIO_START_STOP: TRACE_DISABLED,
        # TRACE_PROCESS: TRACE_DISABLED,
        # TRACE_GENRE: TRACE_DISABLED,
        # TRACE_CERTIFICATION: TRACE_DISABLED,
        TRACE_CACHE_GARBAGE_COLLECTION: TRACE_DISABLED,
        # TRACE_TFH: TRACE_DISABLED,
        STATS_DISCOVERY: TRACE_DISABLED,
        STATS_CACHE: TRACE_DISABLED,
        TRACE_MONITOR: TRACE_DISABLED,
        TRACE_JSON: TRACE_DISABLED,
        # TRACE_SCREENSAVER: TRACE_DISABLED,
        TRACE_UI_CONTROLLER: TRACE_DISABLED,
        TRACE_CACHE_MISSING: TRACE_DISABLED,
        TRACE_CACHE_UNPROCESSED: TRACE_DISABLED,
        # TRACE_CACHE_PAGE_DATA: TRACE_DISABLED,
        TRACE_TRANSLATION: TRACE_DISABLED,
        TRACE_SHUTDOWN: TRACE_DISABLED,
        # TRACE_PLAY_STATS: TRACE_DISABLED,
        # TRACE_NETWORK: TRACE_DISABLED
    }

    _trace_exclude = {
        # TRACE_NETWORK: TRACE_DISABLED,
        TRACE_STATS: TRACE_DISABLED,
        STATS_DISCOVERY: TRACE_DISABLED,
        STATS_CACHE: TRACE_DISABLED,
        TRACE_JSON: TRACE_DISABLED,
        TRACE_MONITOR: TRACE_DISABLED,
        # TRACE_SCREENSAVER: TRACE_DISABLED,
        TRACE_TRANSLATION: TRACE_DISABLED,
        # TRACE_PLAY_STATS: TRACE_DISABLED,
        TRACE_SHUTDOWN: TRACE_DISABLED
    }

    _logger = None

    def __init__(self, name: str = '') -> None:
        """
        Dummy
        """
        super().__init__(name=name)

    @classmethod
    def enable(cls, *flags: str) -> None:
        """

        :param flags:
        :return:
        """
        for flag in flags:
            if flag in cls._trace_map:
                cls._trace_map[flag] = cls.TRACE_ENABLED
            else:
                cls._logger.debug(f'Invalid TRACE flag: {flag}')

    @classmethod
    def enable_all(cls) -> None:
        """

        :return:
        """
        for flag in cls._trace_map.keys():
            if flag not in cls._trace_exclude.keys():
                cls._trace_map[flag] = cls.TRACE_ENABLED

    @classmethod
    def disable(cls, *flags: str) -> None:
        """

        :param flags:
        :return:
        """
        for flag in flags:
            if flag in cls._trace_map:
                cls._trace_map[flag] = cls.TRACE_DISABLED
            else:
                cls._logger.debug(f'Invalid TRACE flag: {flag}')

    @classmethod
    def is_enabled(cls, trace_flags: Union[str, List[str]]) -> bool:
        try:
            if not isinstance(trace_flags, list):
                trace_flags = [trace_flags]

            if len(trace_flags) == 0:
                return False

            for trace in trace_flags:
                enabled = cls._trace_map.get(trace, None)
                if enabled is None:
                    cls._logger.warn(f'Invalid TRACE flag: {trace}')
                elif enabled:
                    return True

            return False
        except Exception:
            BasicLogger.exception(msg='')

        return False

    def filter(self, record: logging.LogRecord) -> int:
        """

        :param record:
        :return:
        """
        cls = Trace
        try:
            passed_traces = record.__dict__.get('trace', [])
            if passed_traces is None or len(passed_traces) == 0:
                return 1

            filtered_traces = []
            for trace in passed_traces:
                is_enabled = cls._trace_map.get(trace, None)
                if is_enabled is None:
                    cls._logger.debug(f'Invalid TRACE flag: {trace}')
                elif is_enabled:
                    filtered_traces.append(trace)

            if len(filtered_traces) > 0:
                filtered_traces.sort()

                trace_string = ', '.join(filtered_traces)
                trace_string = f'[{trace_string}]'
                record.__dict__['trace_string'] = trace_string

                return 1  # Docs say 0 and non-zero
        except Exception:
            BasicLogger.exception(msg='')

        return 0


"""

    %(name)s            Name of the logger (logging channel)
    %(levelno)s         Numeric logging level for the message (DEBUG, INFO,
                        WARNING, ERROR, CRITICAL)
    %(levelname)s       Text logging level for the message ("DEBUG", "INFO",
                        "WARNING", "ERROR", "CRITICAL")
    %(pathname)s        Full pathname of the source file where the logging
                        call was issued (if available)
    %(filename)s        Filename portion of pathname
    %(module)s          Module (name portion of filename)
    %(lineno)d          Source line number where the logging call was issued
                        (if available)
    %(funcName)s        Function name
    %(created)f         Time when the LogRecord was created (time.time()
                        return value)
    %(asctime)s         Textual time when the LogRecord was created
    %(msecs)d           Millisecond portion of the creation time
    %(relativeCreated)d Time in milliseconds when the LogRecord was created,
                        relative to the time the logging module was loaded
                        (typically at application startup time)
    %(thread)d          Thread ID (if available)
    %(threadName)s      Thread name (if available)
    %(process)d         Process ID (if available)
    %(message)s         The result of record.getMessage(), computed just as
                        the record is emitted
                        
BASIC_FORMAT = "%(levelname)s:%(name)s:%(message)s"

_STYLES = {
    '%': (PercentStyle, BASIC_FORMAT),
    '{': (StrFormatStyle, '{levelname}:{name}:{message}'),
    '$': (StringTemplateStyle, '${levelname}:${name}:${message}'),
}
            if clz.INCLUDE_THREAD_LABEL:
                thread_label = 'Thread'
            else:
                thread_label = ''
            if clz.INCLUDE_DEBUG_LEVEL:
                level = record.levelname
            else:
                level = ''

            if passed_traces is None:
                if clz.INCLUDE_THREAD_INFO:
                    prefix = f'[{thread_label} {record.threadName} ' \
                             f'{record.name}.{record.funcName}:{record.lineno}:{level}]'
                else:
                    prefix = f'[{record.name}.{record.funcName}:{record.lineno}:{level}]'

            text = f'{prefix} {suffix}'
"""


# Default style is:  '{': (StrFormatStyle, '{levelname}:{name}:{message}'),
# _STYLES[style][0](fmt)


def get_addon_logger() -> BasicLogger:
    root_logger: BasicLogger | Logger = getLogger()
    addon_logger: BasicLogger = root_logger.getChild(CriticalSettings.get_plugin_name())
    return addon_logger


thread_info: str = ''
if INCLUDE_THREAD_INFO:
    if INCLUDE_THREAD_LABEL:
        thread_label = 'T:'
    else:
        thread_label = ''
    thread_info = f'{thread_label}{{threadName}} '

level_field: str
if INCLUDE_DEBUG_LEVEL:
    level_field = '{levelname} '
else:
    level_field = ''

# format_str: str = f'[{thread_info}{{name}}.{{funcName}}:{{lineno}}:{level_field}]'
# format_str: str = ''  # f'[{thread_info}{{filename}}.{{funcName}}:{{lineno}}:{
# level_field}]'

handler: Handler = KodiHandler(level=CriticalSettings.get_logging_level())
handler.setFormatter(KodiFormatter(style='{'))
handlers: List[Handler] = [handler]
get_addon_logger().addHandler(handler)
get_addon_logger().setLevel(CriticalSettings.get_logging_level())
get_addon_logger().addFilter(Trace())

xbmc.log(f'Configure.get_logging_level: {CriticalSettings.get_logging_level()}')

#  xbmc.log(f'format_str: {format_str}')
my_kwargs: Dict[str, str] = {'style'   : '{',
                             # 'format': format_str,
                             'level'   : CriticalSettings.get_logging_level(),
                             'handlers': handlers}
#  'force': True}

basicConfig(**my_kwargs)


def print_exception(etype: Type = None,
                    value: Any = None,
                    tb: Any = None,
                    thread_name: str = '',
                    limit: int = None,
                    ignore_frames: int = 0,
                    log_file: StringIO = None) -> None:
    """
    :param etype:
    :param value:
    :param tb:
    :param thread_name:
    :param limit:
    :param ignore_frames:
    :param log_file:
    :return:
    """

    if tb is None:
        tb = sys.exc_info()[2]

    log_file_created_here: bool = False
    if log_file is None:
        log_file = StringIO()
        log_file_created_here = True

    log_file.write('LEAK Traceback StackTrace StackDump (most recent call last)\n')

    log_file.write('NORMAL TB:\n')

    traceback.print_exception(etype, value, tb, limit=None, file=log_file, chain=True)

    log_file.write('PRINT_TB: \n')
    traceback.print_tb(tb, file=log_file)

    log_file.write('OUTER FRAMES:\n')
    try:
        for item in reversed(inspect.getouterframes(tb.tb_frame)[1:]):
            log_file.write('File "{1}", line {2}, in {3}\n'.format(*item))
            if item[4] is not None:
                for line in item[4]:
                    log_file.write(' ' + line.lstrip())
    except Exception as e:
        pass

    log_file.write('INNER FRAMES:\n')
    if hasattr(tb, 'tb_frame'):
        try:
            for item in inspect.getinnerframes(tb):
                log_file.write(' File "{1}", line {2}, in {3}\n'.format(*item))
                if item[4] is not None:
                    for line in item[4]:
                        log_file.write(' ' + line.lstrip())
        except Exception as e:
            pass

    # Can be None if tb only sent from a BasicLogger.dump_stack (no exception thrown)

    try:
        if etype is not None and value is not None:
            for item in traceback.format_exception_only(etype, value):
                log_file.write(item)
    except Exception as e:
        pass

    if log_file_created_here:
        xbmc.log(log_file.getvalue())
        log_file.close()
        del log_file


def info(msg: str, *args, **kwargs):
    get_addon_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    get_addon_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    get_addon_logger().error(msg, *args, **kwargs)


def exception(msg: str, *args, **kwargs):
    get_addon_logger().exception(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    get_addon_logger().critical(msg, *args, **kwargs)


def log(level: int, msg: str, *args, **kwargs):
    get_addon_logger().log(level, msg, *args, **kwargs)
