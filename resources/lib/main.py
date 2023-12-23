# -*- coding: utf-8 -*-

from common.critical_settings import *
from common.logger import BasicLogger
from common.minimal_monitor import MinimalMonitor
from common.python_debugger import PythonDebugger

REMOTE_DEBUG: bool = False

# PATCH PATCH PATCH
# Monkey-Patch a well known, embedded Python problem
#
# from common.strptime_patch import StripTimePatch
# StripTimePatch.monkey_patch_strptime()

addon_id: str = CriticalSettings.ADDON_ID

# debug_file = io.open("/home/fbacher/.kodi/temp/kodi.crash", mode='w', buffering=1,
#                     newline=None,
#                     encoding='ASCII')

# faulthandler.register(signal.SIGUSR1, file=debug_file, all_threads=True)

if REMOTE_DEBUG:
    xbmc.log('About to PythonDebugger.enable from tts main', xbmc.LOGINFO)
    PythonDebugger.enable(addon_id)
    from time import sleep

    sleep(5)

import sys
import xbmcvfs

# import faulthandler

module_logger = BasicLogger.get_module_logger(module_path=__file__)

try:
    pass
    # import web_pdb;

    # web_pdb.set_trace()
except Exception as e:
    pass


class MainThreadLoop(xbmc.Monitor):
    """
        Kodi's Monitor class has some quirks in it that strongly favors creating
        it from the main thread as well as calling xbmc.sleep/xbmc.wait_for_abort.
        The main issue is that a Monitor event can not be received until
        xbmc.sleep/xbmc.wait_for_abort is called FROM THE SAME THREAD THAT THE
        MONITOR WAS INSTANTIATED FROM. Further, it may be the case that
        other plugins may be blocked as well. For this reason, the main thread
        should not be blocked for too long.
    """

    profiler = None

    @classmethod
    def event_processing_loop(cls) -> None:
        """

        :return:
        """
        try:
            if os.path.exists(os.path.join(xbmcvfs.translatePath('special://profile'),
                                           'addon_data', 'service.kodi.tts', 'DISABLED')):
                xbmc.log('service.kodi.tts: DISABLED - NOT STARTING')
                return

            worker_thread_initialized = False

            # For the first 10 seconds use a short timeout so that initialization
            # stuff is handled quickly. Then revert to less frequent checks

            initial_timeout = 0.05
            switch_timeouts_count = 10 * 20  # 10 seconds

            # Don't start backend for about one second after start if
            # debugging is enabled in order for it to start.

            if REMOTE_DEBUG:
                # Wait two seconds for debugger to do its thing
                start_backend_count_down = 2.0 / initial_timeout
            else:
                start_backend_count_down = 0.0

            i = 0
            timeout = initial_timeout

            # Using real_waitForAbort to
            # cause Monitor to query Kodi for Abort on the main thread.
            # If this is not done, then Kodi will get constipated
            # sending/receiving events to plugins.

            while not MinimalMonitor.real_waitForAbort(timeout=timeout):
                i += 1
                if i == switch_timeouts_count:
                    timeout = CriticalSettings.LONG_POLL_DELAY

                if start_backend_count_down > 0:
                    start_backend_count_down -= 1.0
                else:
                    if not worker_thread_initialized:
                        worker_thread_initialized = True
                        cls.start_main_thread()

            MinimalMonitor.exception_on_abort(timeout=timeout)

        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            # xbmc.log('xbmc.log Exception: ' + str(e), xbmc.LOGERROR)
            module_logger.exception(e)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        """
        onNotification method.

        :param sender: Sender of the notification
        :param method: Name of the notification
        :param data: JSON-encoded data of the notification

        :return:

        Will be called when Kodi receives or sends a notification
        """
        clz = type(self)
        xbmc.log(f'main.py: sender: {sender} method: {method}', xbmc.LOGDEBUG)
        # clz._inform_notification_listeners(sender, method, data)

    @classmethod
    def start_main_thread(cls) -> None:
        try:
            thread = threading.Thread(
                    target=MainThreadLoop.main,
                    name='tts_service',
                    daemon=False)
            thread.start()
        except Exception as e:
            xbmc.log('Exception: ' + str(e), xbmc.LOGERROR)
            # module_logger# .exception('')

    @staticmethod
    def main():
        # from startup.bootstrap_engines import BootstrapEngines
        # BootstrapEngines.init()
        from common.configuration_utils import ConfigUtils
        arg = None
        if len(sys.argv) > 1:
            arg = sys.argv[1] or False
        extra = sys.argv[2:]

        if arg and arg.startswith('keymap.'):
            command = arg[7:]
            from utils import keymapeditor
            keymapeditor.processCommand(command)
        elif arg == 'settings_dialog':
            ConfigUtils.selectSetting(*extra)
        xbmc.sleep(30 * 60 * 1000)


def bootstrap_plugin() -> None:
    """
    First function called at startup.

    Note this means that this is running on the main thread

    :return:
    """

    try:
        xbmc.log('Starting event processing loop', xbmc.LOGDEBUG)

        MainThreadLoop.main()
        # MainThreadLoop.event_processing_loop()
    except AbortException as e:
        pass
    except Exception as e:
        xbmc.log('Exception: ' + str(e), xbmc.LOGERROR)
        # module_logger.exception('')
    finally:
        exit_plugin()


def exit_plugin():
    if PythonDebugger.is_enabled():
        PythonDebugger.disable()
    sys.exit(0)


if __name__ == '__main__':
    import threading

    threading.current_thread().name = "tts_main"
    bootstrap_plugin()
    exit_plugin()
