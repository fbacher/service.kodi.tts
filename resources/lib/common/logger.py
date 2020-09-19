# -*- coding: utf-8 -*-

"""
Created on Apr 17, 2019

@author: Frank Feuerbacher
"""

from functools import wraps
import inspect
import logging
import os
import sys
import threading
import traceback
from io import StringIO

import six
import xbmc

from common.exceptions import AbortException
from common.constants import Constants
from common.critical_settings import CriticalSettings
from common.imports import *

TOP_PACKAGE_PATH = Constants.PYTHON_ROOT_PATH
INCLUDE_THREAD_INFO = False

if hasattr(sys, '_getframe'):
    def current_frame(ignore_frames: int = 0) -> traceback:
        """

        : ignore_frames: By default, ignore the first frame since it is the line
                         here that captures the frame. When called by logger
                         code, it will probably set to ignore 2 or more frames.
        :return:
        """
        ignore_frames += 1
        frame = None
        try:
            raise Exception
        except:
            frame = sys._getframe(ignore_frames)

        return frame
else:
    def current_frame(ignore_frames: int = 0) -> traceback:
        """

        : ignore_frames: Specifies how many frames to ignore.
        :return:
        """
        ignore_frames += 1
        try:
            raise Exception
        except:
            return sys.exc_info()[2].tb_frame.f_back
# done filching

#
# _srcfile is used when walking the stack to check when we've got the first
# caller stack frame.
#
_srcfile = os.path.normcase(current_frame.__code__.co_filename)


class Logger(logging.Logger):
    """
        Provides logging capabilities that are more convenient than
        xbmc.log.

        Typical usage:

        class abc:
            def __init__(self):
                self._logger = LazyLogger(self.__class__.__name__)

            def method_a(self):
                local_logger = self._logger('method_a')
                local_logger.enter()
                ...
                local_logger.debug('something happened', 'value1:',
                                    value1, 'whatever', almost_any_type)
                local_logger.exit()

        In addition, there is the Trace class which provides more granularity
        for controlling what messages are logged as well as tagging of the
        messages for searching the logs.

    """
    _addon_name = None
    _logger = None
    _trace_groups = {}
    _log_handler_added = False
    _root_logger = None
    _addon_logger = None

    def __init__(self,
                 name,  # type: str
                 level=logging.NOTSET  # type : Optional[int]
                 ):
        # type: (...) -> None
        """
            Creates a config_logger for (typically) a class.

        :param name: label to be printed on each logged entry
        :param level:
        """
        # noinspection PyRedundantParentheses
        try:
            super().__init__(name, level=level)

        except AbortException:
            six.reraise(*sys.exc_info())
        except Exception:
            Logger.log_exception()

    @staticmethod
    def set_addon_name(name):
        # type: (str) ->None
        """
            Sets the optional addon name to be added to each log entry

        :param name: str
        :return:
        """
        Logger._addon_name = name

    @staticmethod
    def get_addon_name():
        # type:() -> str
        """

        :return:
        """
        if Logger._addon_name is None:
            Logger._addon_name = Constants.ADDON_SHORT_NAME

        return Logger._addon_name

    @staticmethod
    def get_root_logger():
        # type: () -> Logger
        """

        :return:
        """
        if Logger._root_logger is None:
            logging.setLoggerClass(LazyLogger)
            root_logger = logging.RootLogger(Logger.DEBUG)
            root_logger = logging.root
            root_logger.addHandler(MyHandler())
            logging_level = CriticalSettings.get_logging_level()
            xbmc.log('get_root_logger logging_level: ' +
                     str(logging_level), xbmc.LOGDEBUG)
            root_logger.setLevel(logging_level)
            Trace.enable_all()
            root_logger.addFilter(
                MyFilter(enabled_traces=Trace.get_enabled_traces()))
            Logger._root_logger = root_logger
        return Logger._root_logger

    @staticmethod
    def get_addon_module_logger(file_path: str = None,
                                addon_name: str = None):
        #  type () -> Logger
        """

        :return:
        """

        logger = None
        if Logger._addon_logger is None:
            if addon_name is None:
                addon_name = Constants.ADDON_SHORT_NAME
            Logger._addon_logger = Logger.get_root_logger().getChild(addon_name)
            xbmc.log('get_addon_module_logger', xbmc.LOGDEBUG)

        logger = Logger._addon_logger
        if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
            if file_path is not None:
                file_path = file_path.replace('.py', '', 1)
                suffix = file_path.replace(TOP_PACKAGE_PATH, '', 1)
                suffix = suffix.replace('/', '.')
                if suffix.startswith('.'):
                    suffix = suffix.replace('.', '', 1)

                logger = Logger._addon_logger.getChild(suffix)
            else:
                logger.debug('Expected file_path')

        return logger

    def log(self, *args, **kwargs):
        # type: ( *Any, **str) -> None
        """
            Creates a log entry

            *args are printed in the log, comma separated. Values are
            converted to strings.

            **Kwargs Optional Trace tags. Message is logged only if tracing
            is enabled for one or more of the tags. Further, the tag is also
            logged.

            Note, the default xbmc.log logging level is xbmc.LOGDEBUG. This can
            be overridden by including the kwarg {'log_level' : xbmc.<log_level>}

        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str Possible values:
                        'log_level'
                        'separator'
                        'exc_info'
                        'start_frame'
                        'trace'
                        'lazy_logger'
                        'test_expected_stack_top'
                        'test_expected_stack_file'
                        'test_expected_stack_method'

        :return:
        """
        # noinspection PyRedundantParentheses
        self._log(*args, **kwargs)

    def _log(self, *args, **kwargs):
        # type: ( *Any, **str) -> None
        """
            Creates a log entry

            *args are printed in the log, comma separated. Values are
            converted to strings.

            **Kwargs Optional Trace tags. Message is logged only if tracing
            is enabled for one or more of the tags. Further, the tag is also
            logged.

            Note, the default xbmc.log logging level is xbmc.LOGDEBUG. This can
            be overridden by including the kwarg {'log_level' : xbmc.<log_level>}

        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        # noinspection PyRedundantParentheses
        start_frame = None
        try:
            kwargs.setdefault('log_level', Logger.DEBUG)
            log_level = kwargs['log_level']
            if not self.isEnabledFor(log_level):
                return

            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames
            kwargs.setdefault('separator', ' ')

            exc_info = kwargs.get('exc_info', None)
            if exc_info is not None:
                start_frame = exc_info[2].tb_frame
                frame_info = inspect.getframeinfo(exc_info[2], context=1)
                # start_file = (pathname, lineno, func)

                start_file = (frame_info[0], frame_info[1], frame_info[2])
            else:
                start_file = tuple()
                start_frame = kwargs.get('start_frame', None)
                if start_frame is None:
                    start_frame = current_frame(ignore_frames=ignore_frames)
                # On some versions of IronPython, current_frame() returns None if
                # IronPython isn't run with -X:Frames.
                if start_frame is not None:
                    #     start_frame = start_frame.f_back
                    rv = "(unknown file)", 0, "(unknown function)"
                    while hasattr(start_frame, "f_code"):
                        co = start_frame.f_code
                        filename = os.path.normcase(co.co_filename)
                        if filename == _srcfile:
                            start_frame = start_frame.f_back
                            continue
                        start_file = (co.co_filename,
                                      start_frame.f_lineno, co.co_name)
                        break

            log_level = kwargs['log_level']
            separator = kwargs['separator']
            trace = kwargs.pop('trace', None)
            lazy_logger = kwargs.pop('lazy_logger', False)

            # The first argument is a string format, unless 'lazy_logger' is set.
            # With lazy_logger, a simple string format is generated based upon
            # the number of other args.

            format_str = ''
            if lazy_logger:
                format_proto = []  # ['[%s]']
                format_proto.extend(['%s'] * len(args))
                format_str = separator.join(format_proto)
            else:
                # Extract the format string from the first arg, then delete
                # the first arg.

                if len(args) > 0:
                    format_str = args[0]
                if len(args) > 1:
                    args = args[1:]
                else:
                    args = []

            args = tuple(args)  # MUST be a tuple

            my_trace = None
            if trace is None:
                my_trace = set()
            elif isinstance(trace, list):
                my_trace = set(trace)
            elif isinstance(trace, str):  # Single trace keyword
                my_trace = {trace, }  # comma creates set

            extra = {'trace': my_trace, 'start_file': start_file,
                     'ignore_frames': ignore_frames}

            super()._log(log_level, format_str, args, exc_info=exc_info,
                         extra=extra)

        except AbortException:
            six.reraise(*sys.exc_info())
        except Exception:
            Logger.log_exception()
        finally:
            del start_frame
            if 'start_frame' in kwargs:
                del kwargs['start_frame']

    def debug(self, format, *args, **kwargs):
        # type: ( str, *Any, **str ) -> None
        # TODO: Get rid of format arg
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.LOGDEBUG)
        :param format: Format string for args
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        if self.isEnabledFor(Logger.DEBUG):
            kwargs['log_level'] = Logger.DEBUG
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames

            self._log(format, *args, **kwargs)

    def debug_verbose(self, text, *args, **kwargs):
        # type: ( str, *Any, **str ) -> None
        # TODO: Get rid of text arg
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.LOGDEBUG)
        :param text: Arbitrary text to include in log
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        if self.isEnabledFor(Logger.DEBUG_VERBOSE):
            kwargs['log_level'] = Logger.DEBUG_VERBOSE
            if kwargs.get('start_frame', None) is None:
                kwargs.setdefault('start_frame', current_frame())

            self._log(text, *args, **kwargs)

    def debug_extra_verbose(self, text, *args, **kwargs):
        # type: ( str, *Any, **str ) -> None
        # TODO: Get rid of text arg
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.LOGDEBUG)
        :param text: Arbitrary text to include in log
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        if self.isEnabledFor(Logger.DEBUG_EXTRA_VERBOSE):
            kwargs['log_level'] = Logger.DEBUG_EXTRA_VERBOSE
            if kwargs.get('start_frame', None) is None:
                kwargs.setdefault('start_frame', current_frame())

            self._log(text, *args, **kwargs)

    def info(self, text, *args, **kwargs):
        # type: ( str, *Any, **str ) -> None
        # TODO: Get rid of text arg
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.LOGINFO)
        :param text: Arbitrary text
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        if self.isEnabledFor(Logger.INFO):
            kwargs['log_level'] = Logger.INFO
            if kwargs.get('start_frame', None) is None:
                kwargs.setdefault('start_frame', current_frame())

            self._log(text, *args, **kwargs)

    def warning(self, text, *args, **kwargs):
        # type: ( str, *Any, **str ) -> None
        # TODO: Get rid of text arg
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.LOGWARN)
        :param text: Arbitrary text to add to log
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        if self.isEnabledFor(Logger.WARNING):
            kwargs['log_level'] = Logger.WARNING
            if kwargs.get('start_frame', None) is None:
                kwargs.setdefault('start_frame', current_frame())

            self._log(text, *args, **kwargs)

    def error(self, text, *args, **kwargs):
        # type: ( str, *Any, **str ) -> None
        # TODO: Get rid of text arg
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.ERROR)
        :param text: Arbitrary text to add to log
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        if self.isEnabledFor(Logger.ERROR):
            kwargs['log_level'] = Logger.ERROR
            if kwargs.get('start_frame', None) is None:
                kwargs.setdefault('start_frame', current_frame())

            self._log(text, *args, **kwargs)

    def enter(self, *args, **kwargs):
        # type: ( *Any, **str ) -> None
        """
            Convenience method to log an "Entering" method entry

        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return: None
        """
        if self.isEnabledFor(Logger.DEBUG):
            if kwargs.get('start_frame', None) is None:
                kwargs.setdefault('start_frame', current_frame())

            self.debug('Entering', *args, **kwargs)

    def exit(self, *args, **kwargs):
        # type: ( *Any, **str ) -> None
        """
               Convenience method to log an "Exiting" method entry

        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return: None
        """

        if kwargs.get('start_frame', None) is None:
            kwargs.setdefault('start_frame', current_frame())

        self.debug('Exiting', *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """
        Convenience method for logging an ERROR with exception information.
        """
        kwargs.setdefault('exc_info', sys.exc_info())
        kwargs['log_level'] = Logger.ERROR
        if kwargs.get('start_frame', None) is None:
            kwargs.setdefault('start_frame', current_frame())
        self.error(msg, *args, **kwargs)

    def fatal(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'FATAL'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        config_logger.critical("Houston, we have a %s", "major disaster", exc_info=1)
        """
        if self.isEnabledFor(Logger.FATAL):
            kwargs['log_level'] = Logger.FATAL
            if kwargs.get('start_frame', None) is None:
                kwargs.setdefault('start_frame', current_frame())

            self._log(msg, *args, **kwargs)

    @classmethod
    def dump_stack(cls, msg='', ignore_frames=0):
        # type (str, Union[int, newint]) -> None
        """
            Logs a stack dump of all Python threads

        :param msg: Optional message
        :param ignore_frames: Specifies stack frames to dump
        :return: None
        """
        ignore_frames += 1
        trace_back, thread_name = cls.capture_stack(
            ignore_frames=ignore_frames)
        cls.log_stack(msg, trace_back, thread_name)

    @classmethod
    def capture_stack(cls, ignore_frames=0):
        # type (Union[int, newint]) -> List[Any]
        """
        :param ignore_frames:
        :return:
        """
        ignore_frames += 1
        return cls._capture_stack(ignore_frames=ignore_frames)

    @classmethod
    def _capture_stack(cls, ignore_frames=0):
        # type (Union[int, newint]) -> List[Any]
        """
        :param ignore_frames: Specifies stack frames to skip
        :return:
        """
        ignore_frames += 1
        frame = current_frame(ignore_frames=int(ignore_frames))

        limit = 15
        # frame = frame.f_back
        trace_back = traceback.extract_stack(frame, limit)
        thread_name = threading.current_thread().getName()
        return trace_back, thread_name

    @staticmethod
    def log_stack(msg, trace_back, thread_name=''):
        # type: (str, List[Any], str) -> None
        """

        :param msg:
        :param trace_back:
        :param thread_name:
        :return:
        """

        try:
            msg = Constants.ADDON_ID + ': ' + msg + ' thread:' + thread_name
            # msg = utils.py2_decode(msg)

            string_buffer = msg
            string_buffer = string_buffer + '\n' + Constants.TRACEBACK
            lines = traceback.format_list(trace_back)
            for line in lines:
                string_buffer = string_buffer + '\n' + line

            xbmc.log(string_buffer, xbmc.LOGERROR)
        except Exception as e:
            Logger.log_exception()

        # XBMC levels

    FATAL = logging.CRITICAL  # 50
    SEVERE = 45
    ERROR = logging.ERROR  # 40
    WARNING = logging.WARNING  # 30
    NOTICE = 25
    INFO = logging.INFO  # 20
    DEBUG = logging.DEBUG  # 10
    DEBUG_VERBOSE = 8
    DEBUG_EXTRA_VERBOSE = 6
    NOTSET = logging.NOTSET  # 0

    # XBMC levels
    LOGDEBUG = xbmc.LOGDEBUG
    LOGINFO = xbmc.LOGINFO
    LOGWARNING = xbmc.LOGWARNING
    LOGERROR = xbmc.LOGERROR
    # LOGSEVERE = 5 Removed in Kodi 19
    LOGFATAL = xbmc.LOGFATAL
    LOGNONE = xbmc.LOGNONE

    logging_to_kodi_level = {FATAL: xbmc.LOGFATAL,
                             SEVERE: xbmc.LOGERROR,
                             ERROR: xbmc.LOGERROR,
                             WARNING: xbmc.LOGWARNING,
                             NOTICE: xbmc.LOGINFO,
                             INFO: xbmc.LOGINFO,
                             DEBUG_EXTRA_VERBOSE: xbmc.LOGDEBUG,
                             DEBUG_VERBOSE: xbmc.LOGDEBUG,
                             DEBUG: xbmc.LOGDEBUG}

    kodi_to_logging_level = {xbmc.LOGDEBUG: DEBUG,
                             xbmc.LOGINFO: INFO,
                             xbmc.LOGWARNING: WARNING,
                             xbmc.LOGERROR: ERROR,
                             xbmc.LOGFATAL: FATAL}

    @staticmethod
    def get_python_log_level(kodi_log_level):
        # type: (int) -> int
        """

        :param kodi_log_level:
        :return:
        """
        return Logger.kodi_to_logging_level.get(kodi_log_level, None)

    @staticmethod
    def get_kodi_level(logging_log_level):
        # type: (int) -> int
        """

        :param logging_log_level:
        :return:
        """
        return Logger.logging_to_kodi_level.get(logging_log_level, None)

    @staticmethod
    def on_settings_changed():
        # type: () -> None
        """

        :return:
        """
        logging_level = CriticalSettings.get_logging_level()
        root_logger = Logger.get_root_logger()
        root_logger.setLevel(logging_level)

    @staticmethod
    def log_exception(exc_info=None, msg=None):
        # type: (BaseException, str) -> None
        """
            Logs an exception.

        :param exc_info: BaseException optional Exception. Not used at this time
        :param msg: str optional msg
        :return: None
        """
        # noinspection PyRedundantParentheses
        try:
            if not isinstance(exc_info, tuple):
                frame = current_frame(ignore_frames=1)
            else:
                frame = sys.exc_info()[2].tb_frame.f_back

                # stack = LazyLogger._capture_stack(ignore_frames=0)
            thread_name = threading.current_thread().getName()

            sio = StringIO()
            LazyLogger.print_full_stack(
                frame=frame, thread_name=thread_name, log_file=sio)

            s = sio.getvalue()
            sio.close()
        except AbortException:
            six.reraise(*sys.exc_info())
        except Exception as e:
            msg = 'Logger.log_exception raised exception during processing'
            xbmc.log(msg, xbmc.LOGERROR)

    @staticmethod
    def print_full_stack(frame=None, thread_name='', limit=None,
                         log_file=None):
        # type: ( Any, str, int, cStringIO.StringIO) -> None
        """

        :param frame:
        :param thread_name:
        :param limit:
        :param log_file:
        :return:
        """

        if frame is None:
            try:
                raise ZeroDivisionError
            except ZeroDivisionError:
                f = sys.exc_info()[2].tb_frame.f_back

        if log_file is None:
            log_file = sys.stderr

        lines = []
        lines.append('LEAK Traceback StackTrace StackDump\n')

        for item in reversed(inspect.getouterframes(frame)[1:]):
            lines.append('File "{1}", line {2}, in {3}\n'.format(*item))
            for line in item[4]:
                lines.append(' ' + line.lstrip())
        if hasattr(frame, 'tb_frame'):
            for item in inspect.getinnerframes(frame):
                lines.append(' File "{1}", line {2}, in {3}\n'.format(*item))
                for line in item[4]:
                    lines.append(' ' + line.lstrip())

        for line in lines:
            log_file.write(line)


def log_exit(func):
    # type: (Callable) -> None
    """

    :param func:
    :return:
    """

    @wraps(func)
    def func_wrapper(*args, **kwargs):
        # type: (*Any, **Any) -> Callable[Any]
        """

        :param args:
        :param kwargs:
        :return:
        """
        class_name = func.__class__.__name__
        method_name = func.__name__
        local_logger = LazyLogger.get_root_logger().getChild(class_name)
        func(*args, **kwargs)
        local_logger.exit()

    return func_wrapper


def log_entry(func):
    # type: (Callable) -> None
    """

    :param func:
    :return:
    """

    @wraps(func)
    def func_wrapper(*args, **kwargs):
        # type: (*Any, **Any) -> func_wrapper
        """

        :param args:
        :param kwargs:
        :return:
        """
        class_name = func.__class__.__name__
        method_name = func.__name__

        # TODO: Does not include addon name & path
        local_logger = Logger.get_addon_module_logger().getChild(class_name)
        local_logger.enter()

        func(*args, **kwargs)

    return func_wrapper


def log_entry_exit(func):
    # type: (Callable) -> None
    """

    :param func:
    :return:
    """

    @wraps(func)
    def func_wrapper(*args, **kwargs):
        # type: (*Any, **Any) -> func_wrapper
        """

        :param args:
        :param kwargs:
        :return:
        """
        class_name = func.__class__.__name__
        method_name = func.__name__

        # TODO: Does not include addon name & path

        local_logger = Logger.get_addon_module_logger().getChild(class_name)
        local_logger.enter()
        func(*args, **kwargs)
        local_logger.exit()

    return func_wrapper


class LazyLogger(Logger):
    """
        Provides logging capabilities that are more convenient than
        xbmc.log.

        Typical usage:

        class abc:
            def __init__(self):
                self._logger = LazyLogger(self.__class__.__name__)

            def method_a(self):
                local_logger = self._logger('method_a')
                local_logger.enter()
                ...
                local_logger.debug('something happened', 'value1:',
                                    value1, 'whatever', almost_any_type)
                local_logger.exit()

        In addition, there is the Trace class which provides more granularity
        for controlling what messages are logged as well as tagging of the
        messages for searching the logs.

    """
    _addon_name = None
    _logger = None
    _trace_groups = {}
    _log_handler_added = False

    def __init__(self,
                 name='',  # type: str
                 class_name='',  # type: Optional[str]
                 level=logging.NOTSET  # type : Optional[int]
                 ):
        # type: (...) -> None
        """
            Creates a config_logger for (typically) a class.

        :param class_name: label to be printed on each logged entry
        :param level: Messages at this level and below get logged

        """
        # noinspection PyRedundantParentheses
        try:
            if name == '':
                name = class_name
            super().__init__(name, level=level)

            if LazyLogger._addon_name is None:
                LazyLogger._addon_name = Constants.ADDON_SHORT_NAME

            # self.addHandler(MyHandler())
            self.setLevel(level)
            Trace.enable_all()
            self.addFilter(
                MyFilter(enabled_traces=Trace.get_enabled_traces()))

        except AbortException:
            six.reraise(*sys.exc_info())
        except Exception:
            LazyLogger.log_exception()

    def log(self, *args, **kwargs):
        # type: ( *Any, **str) -> None
        """
            Creates a log entry

            *args are printed in the log, comma separated. Values are
            converted to strings.

            **Kwargs Optional Trace tags. Message is logged only if tracing
            is enabled for one or more of the tags. Further, the tag is also
            logged.

            Note, the default xbmc.log logging level is xbmc.LOGDEBUG. This can
            be overridden by including the kwarg {'log_level' : xbmc.<log_level>}

        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        # noinspection PyRedundantParentheses
        try:
            kwargs.setdefault('lazy_logger', True)
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames
            super()._log(*args, **kwargs)

        except AbortException:
            six.reraise(*sys.exc_info())
        except Exception:
            LazyLogger.log_exception()

    def _log(self, *args, **kwargs):
        # type: ( *Any, **str) -> None
        """
            Creates a log entry

            *args are printed in the log, comma separated. Values are
            converted to strings.

            **Kwargs Optional Trace tags. Message is logged only if tracing
            is enabled for one or more of the tags. Further, the tag is also
            logged.

            Note, the default xbmc.log logging level is xbmc.LOGDEBUG. This can
            be overridden by including the kwarg {'log_level' : xbmc.<log_level>}

        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        # noinspection PyRedundantParentheses
        try:
            kwargs.setdefault('log_level', Logger.DEBUG)
            log_level = kwargs['log_level']
            if not self.isEnabledFor(log_level):
                return

            kwargs.setdefault('lazy_logger', True)
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames

            super()._log(*args, **kwargs)

        except AbortException:
            six.reraise(*sys.exc_info())
        except Exception:
            LazyLogger.log_exception()

    def debug(self, *args, **kwargs):
        # type: ( *Any, **str ) -> None
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.LOGDEBUG)
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        kwargs['log_level'] = Logger.DEBUG
        kwargs.setdefault('lazy_logger', True)
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames

        self._log(*args, **kwargs)

    def debug_verbose(self, *args, **kwargs):
        # type: ( *Any, **str ) -> None
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.LOGDEBUG)
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        kwargs['log_level'] = Logger.DEBUG_VERBOSE
        kwargs.setdefault('lazy_logger', True)
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames

        self._log(*args, **kwargs)

    def debug_extra_verbose(self, *args, **kwargs):
        # type: ( *Any, **str ) -> None
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.LOGDEBUG)
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        kwargs['log_level'] = Logger.DEBUG_EXTRA_VERBOSE
        kwargs.setdefault('lazy_logger', True)
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames

        self._log(*args, **kwargs)

    def info(self, *args, **kwargs):
        # type: ( *Any, **str ) -> None
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.LOGINFO)
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        kwargs['log_level'] = Logger.INFO
        kwargs.setdefault('lazy_logger', True)
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames

        self._log(*args, **kwargs)

    def warning(self, *args, **kwargs):
        # type: ( *Any, **str ) -> None
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.LOGWARN)
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        kwargs['log_level'] = Logger.WARNING
        kwargs.setdefault('lazy_logger', True)
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames

        self._log(*args, **kwargs)

    def error(self, *args, **kwargs):
        # type: ( *Any, **str ) -> None
        """
            Convenience method for log(xxx kwargs['log_level' : xbmc.ERROR)
        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return:
        """
        kwargs['log_level'] = Logger.ERROR
        kwargs.setdefault('lazy_logger', True)
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames

        self._log(*args, **kwargs)

    def enter(self, *args, **kwargs):
        # type: ( *Any, **str ) -> None
        """
            Convenience method to log an "Entering" method entry

        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return: None
        """
        kwargs.setdefault('lazy_logger', True)
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames

        self.debug('Entering', *args, **kwargs)

    def exit(self, *args, **kwargs):
        # type: ( *Any, **str ) -> None
        """
               Convenience method to log an "Exiting" method entry

        :param args: Any (almost) arbitrary arguments. Typically "msg:", value
        :param kwargs: str  Meant for Trace usage:
        :return: None
        """
        kwargs.setdefault('lazy_logger', True)
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames

        self.debug('Exiting', *args, **kwargs)

    def exception(self, *args, **kwargs):
        """
        Convenience method for logging an ERROR with exception information.
        """
        kwargs.setdefault('exc_info', sys.exc_info())
        kwargs['log_level'] = Logger.ERROR
        kwargs.setdefault('lazy_logger', True)
        kwargs.setdefault('ignore_frames', 0)
        ignore_frames = kwargs['ignore_frames'] + 1
        kwargs['ignore_frames'] = ignore_frames

        self.error(*args, **kwargs)

    def fatal(self, *args, **kwargs):
        """
        Log 'msg % args' with severity 'FATAL'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        config_logger.critical("Houston, we have a %s", "major disaster", exc_info=1)
        """
        if self.isEnabledFor(Logger.FATAL):
            kwargs['log_level'] = Logger.FATAL
            kwargs.setdefault('lazy_logger', True)
            kwargs.setdefault('ignore_frames', 0)
            ignore_frames = kwargs['ignore_frames'] + 1
            kwargs['ignore_frames'] = ignore_frames

            self._log(*args, **kwargs)

    @classmethod
    def dump_stack(cls, msg='', ignore_frames=0):
        # type (str, Union[int, newint]) -> None
        """
            Logs a stack dump of all Python threads

        :param msg: Optional message
        :param ignore_frames: Specifies stack frames to dump
        :return: None
        """
        ignore_frames += 1
        trace_back, thread_name = cls._capture_stack(
            ignore_frames=ignore_frames)
        cls.log_stack(msg, trace_back, thread_name)

    @classmethod
    def capture_stack(cls, ignore_frames=0):
        # type (Union[int, newint]) -> List[Any]
        """
        :param ignore_frames:
        :return:
        """
        ignore_frames += 1
        return cls._capture_stack(ignore_frames=ignore_frames)

    @staticmethod
    def log_stack(msg, trace_back, thread_name=''):
        # type: (str, List[Any], str) -> None
        """

        :param msg:
        :param trace_back:
        :param thread_name:
        :return:
        """

        try:
            msg = Constants.ADDON_ID + ': ' + msg + ' thread:' + thread_name
            # msg = utils.py2_decode(msg)

            string_buffer = msg
            string_buffer = string_buffer + '\n' + Constants.TRACEBACK
            lines = traceback.format_list(trace_back)
            for line in lines:
                string_buffer = string_buffer + '\n' + line

            xbmc.log(string_buffer, xbmc.LOGERROR)
        except Exception as e:
            Logger.log_exception()


class Trace(object):
    """

    """
    TRACE = 'TRACE'
    STATS = 'STATS'
    TRACE_UI = 'UI'
    STATS_UI = 'STATS_UI'
    TRACE_DISCOVERY = 'DISCOVERY'
    STATS_DISCOVERY = 'STATS_DISCOVERY'
    TRACE_MONITOR = 'MONITOR'
    TRACE_JSON = 'JSON'
    TRACE_SCREENSAVER = 'SCREENSAVER'
    TRACE_UI_CONTROLLER = 'UI_CONTROLLER'

    _trace_all = [TRACE, STATS, TRACE_UI, STATS_UI, TRACE_DISCOVERY,
                  STATS_DISCOVERY, TRACE_MONITOR, TRACE_JSON, TRACE_SCREENSAVER,
                  TRACE_UI_CONTROLLER]

    _enabled_traces = set()
    _logger = None

    def __init__(self):
        # type:( ) -> None
        """
        Dummy
        """
        pass

    @staticmethod
    def enable(*flags):
        # type: (str) -> None
        """

        :param flags:
        :return:
        """
        for flag in flags:
            Trace._enabled_traces.add(flag)

    @staticmethod
    def enable_all():
        # type: () -> None
        """

        :return:
        """
        for flag in Trace._trace_all:
            Trace.enable(flag)

    @staticmethod
    def disable(*flags):
        # type: (*str) -> None
        """

        :param flags:
        :return:
        """
        for flag in flags:
            Trace._enabled_traces.remove(flag)

    @staticmethod
    def get_enabled_traces():
        # type: () -> Set[str]
        """

        :return:
        """
        return Trace._enabled_traces


class MyHandler(logging.Handler):
    """

    """

    def __init__(self, level=logging.NOTSET, trace=None):
        # type: (int, Optional[Set[str]]) -> None
        """

        :param level:
        :param trace:
        """

        self._trace = trace

        super().__init__()
        self.setFormatter(MyFormatter())

    def emit(self, record):
        # type: (logging.LogRecord) -> None
        """

        :param record:
        :return:
        """

        try:
            kodi_level = Logger.get_kodi_level(record.levelno)
            if record.exc_info is not None:
                ignore_frames = record.__dict__.get('ignore_frames', 0) + 4
                msg = self.formatter.formatException(record.exc_info,
                                                     ignore_frames)
                record.exc_text = msg
            msg = self.format(record)
            xbmc.log(msg, kodi_level)
        except Exception as e:
            pass


class MyFilter(logging.Filter):
    """

    """

    def __init__(self, name='', enabled_traces=None):
        # type: (str, Union[Set[str], None]) -> None
        """

        :param name:
        :param enabled_traces:
        """
        try:
            super().__init__(name=name)
            self._enabled_traces = enabled_traces
            if self._enabled_traces is None:
                self._enabled_traces = set()
        except Exception as e:
            pass

    def filter(self, record):
        # type: (logging.LogRecord) -> int
        """


        :param record:
        :return:
        """
        try:
            passed_traces = record.__dict__.get('trace', set())
            if len(passed_traces) == 0:
                return 1

            filtered_traces = self._enabled_traces.intersection(passed_traces)
            if len(filtered_traces) > 0:
                trace_string = ', '.join(sorted(filtered_traces))
                trace_string = '[{}]'.format(trace_string)
                record.__dict__['trace_string'] = trace_string

                return 1  # Docs say 0 and non-zero
        except Exception:
            LazyLogger.log_exception()

        return 0


class MyFormatter(logging.Formatter):
    """

    """

    def __init__(self, fmt=None, datefmt=None):
        # type: (Optional[str], Optional[str]) -> None
        """

        :param fmt:
        :param datefmt:
        :param style:
        """
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record):
        # type: (logging.LogRecord) -> str
        """

        :param record:
        :return:
        """

        """
            Attribute name 	Format 	Description
            args 	You shouldn’t need to format this yourself. 	The tuple of arguments merged into msg to produce message, or a dict whose values are used for the merge (when there is only one argument, and it is a dictionary).
            asctime 	%(asctime)s 	Human-readable time when the LogRecord was created. By default this is of the form ‘2003-07-08 16:49:45,896’ (the numbers after the comma are millisecond portion of the time).
            created 	%(created)f 	Time when the LogRecord was created (as returned by time.time()).
            exc_info 	You shouldn’t need to format this yourself. 	Exception tuple (à la sys.exc_info) or, if no exception has occurred, None.
            filename 	%(filename)s 	Filename portion of pathname.
            funcName 	%(funcName)s 	Name of function containing the logging call.
            levelname 	%(levelname)s 	Text logging level for the message ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
            levelno 	%(levelno)s 	Numeric logging level for the message (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            lineno 	%(lineno)d 	Source line number where the logging call was issued (if available).
            module 	%(module)s 	Module (name portion of filename).
            msecs 	%(msecs)d 	Millisecond portion of the time when the LogRecord was created.
            message 	%(message)s 	The logged message, computed as msg % args. This is set when Formatter.format() is invoked.
            msg 	You shouldn’t need to format this yourself. 	The format string passed in the original logging call. Merged with args to produce message, or an arbitrary object (see Using arbitrary objects as messages).
            name 	%(name)s 	Name of the config_logger used to log the call.
            pathname 	%(pathname)s 	Full pathname of the source file where the logging call was issued (if available).
            process 	%(process)d 	Process ID (if available).
            processName 	%(processName)s 	Process name (if available).
            relativeCreated 	%(relativeCreated)d 	Time in milliseconds when the LogRecord was created, relative to the time the logging module was loaded.
            stack_info 	You shouldn’t need to format this yourself. 	Stack frame information (where available) from the bottom of the stack in the current thread, up to and including the stack frame of the logging call which resulted in the creation of this record.
            thread 	%(thread)d 	Thread ID (if available).
            threadName 	%(threadName)s 	Thread name (if available).

            [service.randomtrailers.backend:DiscoverTmdbMovies:process_page] 
            [service.randomtrailers.backend:FolderMovieData:add_to_discovered_trailers  TRACE_DISCOVERY]
        """
        # threadName Constants.ADDON_SHORT_NAME funcName:lineno
        # [threadName name funcName:lineno]

        text = ''
        try:
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

            suffix = super().format(record)
            passed_traces = record.__dict__.get('trace_string', None)
            if passed_traces is None:
                if INCLUDE_THREAD_INFO:
                    prefix = '[Thread {!s} {!s}.{!s}:{!s}]'.format(
                        record.threadName, record.name, record.funcName, record.lineno)
                else:
                    prefix = '[{!s}.{!s}:{!s}]'.format(
                        record.name, record.funcName, record.lineno)
            else:
                if INCLUDE_THREAD_INFO:
                    prefix = '[Thread {!s} {!s}.{!s}:{!s} Trace:{!s}]'.format(
                        record.threadName, record.name, record.funcName,
                        record.lineno, passed_traces)
                else:
                    prefix = '[{!s}.{!s}:{!s} Trace:{!s}]'.format(
                        record.name, record.funcName,
                        record.lineno, passed_traces)
            text = '{} {}'.format(prefix, suffix)
        except Exception as e:
            pass

        return text

    def formatException(self, ei, ignore_frames=0):
        # type: (...) -> str
        """

        :param ei:
        :return:
        """
        ignore_frames += 1
        if ei is not None:
            thread_name = threading.current_thread().getName()

            sio = StringIO()
            self.print_exception(
                ei[0], ei[1], ei[2], thread_name='', limit=None, log_file=sio)

            s = sio.getvalue()
            sio.close()
            return s

    def print_exception(self, etype, value, tb, thread_name='',
                        limit=None, log_file=None):

        # type: ( Any, str, int, StringIO) -> None
        """

        :param frame:
        :param thread_name:
        :param limit:
        :param log_file:
        :return:
        """

        if tb is None:
            tb = sys.exc_info()[2]

        if log_file is None:
            log_file = sys.stderr

        lines = []
        lines.append(
            'LEAK Traceback StackTrace StackDump (most recent call last)\n')

        for item in reversed(inspect.getouterframes(tb.tb_frame)[1:]):
            lines.append('File "{1}", line {2}, in {3}\n'.format(*item))
            for line in item[4]:
                lines.append(' ' + line.lstrip())

        if hasattr(tb, 'tb_frame'):
            for item in inspect.getinnerframes(tb):
                lines.append(' File "{1}", line {2}, in {3}\n'.format(*item))
                for line in item[4]:
                    lines.append(' ' + line.lstrip())

        lines = lines + traceback.format_exception_only(etype, value)

        for line in lines:
            log_file.write(line)
