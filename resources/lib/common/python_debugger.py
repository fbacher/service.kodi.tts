# -*- coding: utf-8 -*-

"""
Created on Feb 12, 2019

@author: Frank Feuerbacher
"""

import os
import sys
import threading

import xbmc
import xbmcaddon


class PythonDebugger:
    REMOTE_DEBUG: bool = True
    START_IN_SEPARATE_THREAD: bool = True
    SUSPEND: bool = False
    WAIT_FOR_READY_TO_RUN: bool = False
    pydevd_addon_path: str = None
    plugin_name: str = ''
    remote_debug: bool = False
    thread: threading.Thread = None

    @classmethod
    def enable(cls, plugin_name: str) -> bool:
        cls.plugin_name = plugin_name
        if cls.remote_debug:
            xbmc.log(f'pydevd debugger already started', xbmc.LOGINFO)
            return cls.remote_debug

        xbmc.log(
                f'Attempting to attach to debugger python version: {sys.version}',
                xbmc.LOGINFO)
        try:
            if cls.REMOTE_DEBUG and not cls.remote_debug:
                cls.pydevd_addon_path = xbmcaddon.Addon(
                        'script.module.pydevd').getAddonInfo('path')
                addons_path = os.path.join(cls.pydevd_addon_path, 'lib')
                sys.path.append(addons_path)
                cls.remote_debug = True
                import pydevd
                xbmc.log(f'pydevd import: {pydevd.__file__}', xbmc.LOGDEBUG)
                # del pydevd
                # sys.modules.pop('pydevd')
                # addons_path = os.path.join(cls.pydevd_addon_path, 'lib')
                # import pydevd
                # xbmc.log(f'pydevd import: {pydevd.__file__}', xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(cls.plugin_name +
                     ' Debugger disabled, script.module.pydevd NOT installed',
                     xbmc.LOGDEBUG)
            # cls.remote_debug = False

        if cls.remote_debug:
            try:
                if cls.START_IN_SEPARATE_THREAD:
                    cls.thread = threading.Thread(
                            target=cls._enable,
                            name=cls.plugin_name + 'pydevd startup thread')
                    cls.thread.start()
                else:
                    cls._enable()

            except Exception as e:
                xbmc.log(str(e), xbmc.LOGDEBUG)
                cls.remote_debug = False

        return cls.remote_debug

    @classmethod
    def is_enabled(cls) -> bool:
        return cls.remote_debug

    @classmethod
    def disable(cls) -> None:
        if cls.remote_debug:
            try:
                import pydevd
                pydevd.stoptrace()
                cls.thread.join(timeout=0.1)
            except Exception:
                pass

    @classmethod
    def _enable(cls) -> bool:
        threading.current_thread().name = 'pydevd_startup'
        if cls.remote_debug:
            try:
                import pydevd
            except ImportError:
                cls.remote_debug = False
                msg = 'Error:  You must add org.python.pydev.debug.pysrc to your ' \
                      'PYTHONPATH. Plugin: ' + cls.plugin_name
                xbmc.log(msg, xbmc.LOGDEBUG)
            except Exception as e:
                cls.remote_debug = False
                msg = f'Error importing pydevd to: {cls.plugin_name} {str(e)}'
                xbmc.log(msg, xbmc.LOGDEBUG)

        if cls.remote_debug:
            # Note, besides having script.module.pydevd installed, pydevd
            # must also be on path of IDE runtime. Should be same versions!
            try:
                xbmc.log(f'{cls.plugin_name} trying to attach to debugger',
                         xbmc.LOGDEBUG)
                addons_path = os.path.join(cls.pydevd_addon_path, 'lib')
                sys.path.append(addons_path)
                # xbmc.log('sys.path appended to', xbmc.LOGDEBUG)
                # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse
                # console

                # Can't seem to register
                # enable works, but signal results in junk stack traces
                # try:
                # fault_handler_file = io.open('/tmp/kodi.fault',
                #                             mode='w',
                #                             newline=None,
                #                             encoding='utf-8')
                # faulthandler.enable(file=fault_handler_file)
                # faulthandler.register(
                #     11, file=fault_handler_file, chain=True)
                # except Exception as e:
                #     xbmc.log('FaultHandler.register exception ' +
                #             str(e), xbmc.LOGERROR)
                """
                try:
                    Debug.dump_all_threads(delay=0.1)
                    Debug.dump_all_threads(delay=0.5)
                    Debug.dump_all_threads(delay=10.0)
                    Debug.dump_all_threads(delay=20.0)
                except Exception as e:
                    xbmc.log('Debug.dump_all_threads exception ' +
                             str(e), xbmc.LOGERROR)
                """

                """
                 :param host: the user may specify another host, if the debug 
                    server is not in the same machine (default is the local
                    host)

                :param stdout_to_server: when this is true, the stdout is passed to 
                    the debug server

                :param stderr_to_server: when this is true, the stderr is passed to 
                    the debug server
                    so that they are printed in its console and not in this process 
                    console.

                :param port: specifies which port to use for communicating with the
                    server (note that the server must be started
                    in the same port). @note: currently it's hard-coded at 5678 in the 
                    client

                :param suspend: whether a breakpoint should be emulated as soon as
                    this function is called.

                :param trace_only_current_thread: determines if only the current 
                    thread will be traced or all current and future
                    threads will also have the tracing enabled.

                :param overwrite_prev_trace: deprecated

                :param patch_multiprocessing: if True we'll patch the functions which 
                    create new processes so that launched
                    processes are debugged.

                :param stop_at_frame: if passed it'll stop at the given frame,
                    otherwise it'll stop in the function which
                    called this method.

                :param wait_for_ready_to_run: if True settrace will block until the 
                    ready_to_run flag is set to True,
                    otherwise, it'll set ready_to_run to True and this function won't 
                    block.

                    Note that if wait_for_ready_to_run == False, there are no guarantees
                    that the debugger is synchronized
                    with what's configured in the client (IDE), the only guarantee is 
                    that when leaving this function
                    the debugger will be already connected.

                :param dont_trace_start_patterns: if set, then any path that starts 
                    with one the patterns in the collection will not be traced

                :param dont_trace_end_patterns: if set, then any path that ends with
                    one fo the patterns in the collection will not be traced

                :param access_token: token to be sent from the client (i.e.: IDE) to 
                    the debugger when a connection is established (verified by the 
                    debugger).

                :param client_access_token: token to be sent from the debugger to the 
                    client (i.e.: IDE) when a connection is established (verified by 
                    the client).

                :param notify_stdin:
                    If True sys.stdin will be patched to notify the client when a 
                    message is requested
                    from the IDE. This is done so that when reading the stdin the 
                    client is notified.
                    Clients may need this to know when something that is being written 
                    should be interpreted
                    as an input to the process or as a command to be evaluated.
                    Note that parallel-python has issues with this (because it tries to 
                    assert that sys.stdin
                    is of a given type instead of just checking that it has what it 
                    needs).
                """

                pydevd.settrace('localhost', stdoutToServer=True,
                                stderrToServer=True, suspend=cls.SUSPEND,
                                wait_for_ready_to_run=cls.WAIT_FOR_READY_TO_RUN)
            except Exception as e:
                xbmc.log(
                        f' Looks like remote debugger was not started prior to '
                        f'{cls.plugin_name}',
                        xbmc.LOGDEBUG)
                cls.remote_debug = False

        xbmc.log(f"PythonDebugger {cls.plugin_name}: " +
                 str(cls.remote_debug), xbmc.LOGDEBUG)
