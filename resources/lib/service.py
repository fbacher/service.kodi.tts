# -*- coding: utf-8 -*-
#
import os
import sys

import xbmc
import xbmcvfs

from common.critical_settings import CriticalSettings
from common.minimal_monitor import MinimalMonitor
from common.python_debugger import PythonDebugger

REMOTE_DEBUG: bool = True

addon_id: str = CriticalSettings.ADDON_ID

# PATCH PATCH PATCH
# Monkey-Patch a well known, embedded Python problem
#
# from common.strptime_patch import StripTimePatch
# StripTimePatch.monkey_patch_strptime()

# debug_file = io.open("/home/fbacher/.kodi/temp/kodi.crash", mode='w', buffering=1,
#                      newline=None,
#                     encoding='ASCII')

# faulthandler.register(signal.SIGUSR1, file=debug_file, all_threads=True)

if REMOTE_DEBUG:
    xbmc.log(f'About to PythonDebugger.enable from tts service', xbmc.LOGINFO)
    xbmc.log(f'PYTHONPATH: {sys.path}', xbmc.LOGINFO)
    # if not PythonDebugger.is_enabled():
    PythonDebugger.enable(addon_id)
    xbmc.sleep(500)
    if MinimalMonitor.abort_requested():
        PythonDebugger.disable()
        sys.exit()

import datetime
import faulthandler
import io
import signal
try:
    pass
    # import web_pdb;

    # web_pdb.set_trace()
except Exception as e:
    pass

from common.logger import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)

from common.typing import *


from backends import audio
from common.settings import Settings
from backends.backend_info import BackendInfo
from backends.settings.setting_properties import SettingsProperties

from common.constants import Constants
from common.system_queries import SystemQueries
import enabler


__version__ = Constants.VERSION

module_logger.info(__version__)
module_logger.info('Platform: {0}'.format(sys.platform))

if audio.PLAYSFX_HAS_USECACHED:
    module_logger.info('playSFX() has useCached')
else:
    module_logger.info('playSFX() does NOT have useCached')


def resetAddon():
    global DO_RESET
    if DO_RESET:
        return
    DO_RESET = True
    module_logger.info('Resetting addon...')
    xbmc.executebuiltin(
            'RunScript(special://home/addons/service.kodi.tts/resources/lib/tools'
            '/enabler.py,RESET)')


def preInstalledFirstRun():
    if not SystemQueries.isPreInstalled():  # Do as little as possible if there is no
        # pre-install
        if SystemQueries.wasPreInstalled():
            module_logger.info('PRE INSTALL: REMOVED')
            # Set version to 0.0.0 so normal first run will execute and fix the
            # keymap
            Settings.setSetting(SettingsProperties.VERSION, '0.0.0', None)
            enabler.markPreOrPost()  # Update the install status
        return False

    lastVersion = Settings.getSetting(SettingsProperties.VERSION, None)

    if not enabler.isPostInstalled() and SystemQueries.wasPostInstalled():
        module_logger.info('POST INSTALL: UN-INSTALLED OR REMOVED')
        # Add-on was removed. Assume un-installed and treat this as a
        # pre-installed first run to disable the addon
    elif lastVersion:
        enabler.markPreOrPost()  # Update the install status
        return False

    # Set version to 0.0.0 so normal first run will execute on first enable
    Settings.setSetting(SettingsProperties.VERSION, '0.0.0', None)

    module_logger.info('PRE-INSTALLED FIRST RUN')
    module_logger.info('Installing basic keymap')

    # Install keymap with just F12 enabling included
    from utils import keymapeditor
    keymapeditor.installBasicKeymap()

    module_logger.info('Pre-installed - DISABLING')

    enabler.disableAddon()
    return True


def startService():
    if preInstalledFirstRun():
        return
    xbmc.log('starting service.startservice thread', xbmc.LOGDEBUG)

    from startup.bootstrap_engines import BootstrapEngines
    try:
        from backends.audio.bootstrap_players import BootstrapPlayers

        from service_worker import TTSService
        TTSService().start()
        xbmc.log('started service.startService thread', xbmc.LOGDEBUG)
    except AbortException:
        pass  # About to exit thread
    except Exception as e:
        xbmc.log(f'Exception {repr(e)}. Exiting')
        module_logger.exception('')
    # while True:
    #     if xbmc.abortRequested(100):
    #         break
    #  xbmc.log(f'AbortRequested. Exiting startService', xbmc.LOGDEBUG)


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

            initial_timeout = CriticalSettings.SHORT_POLL_DELAY
            switch_timeouts_count = initial_timeout / 10.0 # 10 seconds

            # Don't start backend for about one second after start if
            # debugging is enabled in order for it to start.

            if REMOTE_DEBUG:
                # Wait one second for debugger to do its thing
                start_backend_count_down = 1.0 / initial_timeout
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
                        cls.start_worker_thread()

            MinimalMonitor.exception_on_abort(timeout=timeout)

        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            # xbmc.log('xbmc.log Exception: ' + str(e), xbmc.LOGERROR)
            module_logger.exception(e)

    @classmethod
    def start_worker_thread(cls) -> None:
        try:
            thread = threading.Thread(
                    target=startService,
                    name='tts_service',
                    daemon=False)
            thread.start()
        except Exception as e:
            xbmc.log('Exception: ' + str(e), xbmc.LOGERROR)
            module_logger.exception('')


if __name__ == '__main__':
    import threading
    module_logger.debug('starting service.py service.kodi.tts service thread')
    # sys.exit()
    #
    try:
        MainThreadLoop().event_processing_loop()
        PythonDebugger.disable()
    except AbortException:
        PythonDebugger.disable()
    except Exception as e:
       module_logger.exception('')
       PythonDebugger.disable()
    sys.exit()
