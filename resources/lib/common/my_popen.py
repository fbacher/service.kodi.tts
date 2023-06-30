# coding=utf-8
from subprocess import Popen

from cache.prefetch_movie_data.seed_cache import SeedCache
from common.critical_settings import CriticalSettings
from common.logger import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class MyPopen(Popen):
    _logger: BasicLogger = None

    """
    Also Python 3 adds new semantic (refer PEP 3102):

    def func(arg1, arg2, arg3, *, kwarg1, kwarg2):
        pass
        
        Such function accepts only 3 positional arguments, and everything after *
         can only be passed as keyword arguments.
    """
    def __init__(self, args, bufsize=- 1, executable=None, stdin=None, stdout=None,
                 stderr=None, preexec_fn=None, close_fds=True, shell=False, cwd=None,
                 env=None, universal_newlines=None, startupinfo=None, creationflags=0,
                 restore_signals=True, start_new_session=False, pass_fds=(), *,
                 group=None, extra_groups=None, user=None, umask=- 1, encoding=None,
                 errors=None, text=None, pipesize=- 1, process_group=None):
        super.__init__(args, bufsize=bufsize, executable=executable, stdin=stdin,
                       stdout=stdout, stderr=stderr, preexec_fn=preexec_fn,
                       close_fds=close_fds, shell=shell, cwd=cwd, env=env,
                       universal_newlines=universal_newlines, startupinfo=startupinfo,
                       creationflags=creationflags, restore_signals=restore_signals,
                       start_new_session=start_new_session, pass_fds=pass_fds,
                       # *,
                       # The following MUST be passed as keyword args-
                       group=group, extra_groups=extra_groups, user=user, umask=umask,
                       encoding=encoding, errors=errors, text=text, pipesize=pipesize,
                       process_group=process_group)
        clz = type(self)
        if clz._logger is None:
            self._logger: BasicLogger = module_logger.getChild(clz.__name__)

    @classmethod
    def run(cls, args, *, stdin=None, input=None, stdout=None, stderr=None,
            capture_output=False, shell=False, cwd=None, timeout=None, check=False,
            encoding=None, errors=None, text=None, env=None, universal_newlines=None,
            **other_popen_kwargs) -> 'MyPopen':
        """

        :param args:
        :param stdin:
        :param input:
        :param stdout:
        :param stderr:
        :param capture_output:
        :param shell:
        :param cwd:
        :param timeout:
        :param check:
        :param encoding:
        :param errors:
        :param text:
        :param env:
        :param universal_newlines:
        :param other_popen_kwargs:
        :return:

        If capture_output is true, stdout and stderr will be captured. When used,
        the internal Popen object is automatically created with stdout=PIPE and
        stderr=PIPE. The stdout and stderr arguments may not be supplied at the same
        time as capture_output. If you wish to capture and combine both streams into
        one, use stdout=PIPE and stderr=STDOUT instead of capture_output.

        The timeout argument is passed to Popen.communicate(). If the timeout expires,
        the child process will be killed and waited for. The TimeoutExpired exception will be
        re-raised after the child process has terminated.

        The input argument is passed to Popen.communicate() and thus to the subprocess’s stdin.
        If used it must be a byte sequence, or a string if encoding or errors is specified or
        text is true. When used, the internal Popen object is automatically created with
        stdin=PIPE, and the stdin argument may not be used as well.

        If check is true, and the process exits with a non-zero exit code, a CalledProcessError
        exception will be raised. Attributes of that exception hold the arguments, the exit
        code, and stdout and stderr if they were captured.

        If encoding or errors are specified, or text is true, file objects for stdin,
        stdout and stderr are opened in text mode using the specified encoding and errors or
        the io.TextIOWrapper default. The universal_newlines argument is equivalent to text and
        is provided for backwards compatibility. By default, file objects are opened in binary
        mode.

        If env is not None, it must be a mapping that defines the environment variables for the
        new process; these are used instead of the default behavior of inheriting the current
        process’ environment. It is passed directly to Popen. This mapping can be str to str on
        any platform or bytes to bytes on POSIX platforms much like os.environ or os.environb.
        """
        return MyPopen(args, stdin=stdin, stdout=stdout, stderr=stderr, shell=shell,
                       cwd=cwd, encoding=encoding, errors=errors, text=text,
                       env=env, universal_newlines=universal_newlines)
