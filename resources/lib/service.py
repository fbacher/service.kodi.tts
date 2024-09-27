# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import faulthandler
import io
import logging
from typing import Dict, Final
#
import os
import signal
import sys

import xbmc
import xbmcaddon
import xbmcvfs

from common.debug import Debug

'''
addon = xbmcaddon.Addon('service.kodi.tts')
all_settings: xbmcaddon.Settings = addon.getSettings()
# an_int: int = all_settings.getInt('background_progress_interval.tts')
# xbmc.log(f'background_progress_interval value: {an_int}')
a_string = all_settings.getString('engine')
xbmc.log(f'engine: {a_string}')
all_settings.setString('engine', 'Google')
a_string = all_settings.getString(f'engine')
xbmc.log(f'new engine value: {a_string}')
addon.setSettingString('engine', 'Festival')
'''

#   C O N F I G U R E   L O G G E R

#  MUST be done BEFORE importing BasicLogger
from common.critical_settings import CriticalSettings

CriticalSettings.set_plugin_name('tts')

definitions: Dict[str, int]

# Goal: to reduce logging in every section except gui and windows family of
# loggers. Also, leave logging of gui.parser family as default


from common.logger import BasicLogger


DEBUG_VERBOSE: Final[int] = 8
DEBUG_EXTRA_VERBOSE: Final[int] = 6


# Default logging is info, otherwise debug_v
definitions = {
    'tts': logging.INFO,
    'tts.backends': logging.DEBUG,
    'tts.gui': DEBUG_VERBOSE,
    'tts.windows': logging.DEBUG,
    'tts.windows.custom_tts': DEBUG_VERBOSE,
    'tts.gui.parser': DEBUG_VERBOSE,
    'tts.service_worker': DEBUG_VERBOSE,
    'tts.windowNavigation.help_dialog': logging.DEBUG
            }
xbmc.log(f'configuring debug_levels INFO: {logging.INFO} DEBUG: {logging.DEBUG} '
         f'VERBOSE: {DEBUG_VERBOSE} EXTRA_VERBOSE: '
         f'{DEBUG_EXTRA_VERBOSE}')
BasicLogger.config_debug_levels(replace=False, default_log_level=logging.INFO,
                                definitions=definitions)
xbmc.log(f'Using service_worker')
service_worker_logger: BasicLogger = BasicLogger.get_logger(f'tts.service_worker')
service_worker_logger.info('hi info')
service_worker_logger.debug(f'hi debug')
service_worker_logger.debug_v(f'hi verbose')
service_worker_logger.debug_xv(f'hi extra verbose')
other_logger: BasicLogger = BasicLogger.get_logger(f'tts.gui.group_list_model')
other_logger.info('hi info')
other_logger.debug(f'hi debug')
other_logger.debug_v(f'hi verbose')
other_logger.debug_xv(f'hi extra verbose')

from common import *
from common.minimal_monitor import MinimalMonitor
from common.python_debugger import PythonDebugger

DEVELOPMENT_BUILD: Final[bool] = True
CRASH_FILE_ENABLED: Final[bool] = False
REMOTE_DEBUG: bool = False

addon_id: str = CriticalSettings.ADDON_ID

if DEVELOPMENT_BUILD:
    if CRASH_FILE_ENABLED:
        crash_path: str = xbmcvfs.translatePath("special://home/temp/kodi.crash")
        debug_file = io.open(crash_path, mode='w', buffering=1,
                             newline=None,
                             encoding='ASCII')
        faulthandler.register(signal.SIGUSR1, file=debug_file, all_threads=True)

if REMOTE_DEBUG:
    xbmc.log(f'About to PythonDebugger.enable from tts service', xbmc.LOGINFO)
    xbmc.log(f'PYTHONPATH: {sys.path}', xbmc.LOGINFO)
    # if not PythonDebugger.is_enabled():
    PythonDebugger.enable(addon_id)
    xbmc.sleep(500)
    if MinimalMonitor.abort_requested():
        PythonDebugger.disable()
        xbmc.log('shutdown initializing debugger', xbmc.LOGDEBUG)
        sys.exit(0)

try:
    pass
    # import web_pdb;

    # web_pdb.set_trace()
except Exception as e:
    pass

from common.logger import *

module_logger = BasicLogger.get_logger(__name__)
module_logger = BasicLogger.get_logger(__name__)

from backends import audio
from common.settings import Settings
from backends.settings.setting_properties import SettingsProperties

from common.constants import Constants
from common.system_queries import SystemQueries
import enabler

__version__ = Constants.VERSION

module_logger.info(__version__)
module_logger.info('Platform: {0}'.format(sys.platform))

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
    """
    This is a separate thread that runs the service_worker

    :return:
    """
    try:
        if preInstalledFirstRun():
            return
        # Will crash with these lines

        xbmc.log('starting service.startservice thread', xbmc.LOGDEBUG)
        # Core dumps
        # xbmcaddon.Addon().getSettings().setString('engine', 'google')
        # setSettingString('engine', 'google')
        # settings: xbmcaddon.Settings = xbmcaddon.Addon().getSettings()
        # settings.setString('engine', 'zorgo')
        # xbmcaddon.Addon().setSettingString('engine', 'google')
        # xbmc.sleep(5000)
        # xbmc.log(f'service.setting zorgo', xbmc.LOGDEBUG)
        #  Do NOT remove import!!
        from startup.bootstrap_engines import BootstrapEngines
        BootstrapEngines.init()
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


class MainThreadLoop:
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
    thread: threading.Thread = None

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
            switch_timeouts_count = initial_timeout / 10.0  # 10 seconds

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
            return
        except Exception as e:
            # xbmc.log('xbmc.log Exception: ' + str(e), xbmc.LOGERROR)
            module_logger.exception(e)

    @classmethod
    def start_worker_thread(cls) -> None:
        try:
            cls.thread = threading.Thread(
                    target=startService,
                    name='tts_svc',
                    daemon=False)
            cls.thread.start()
            from common.garbage_collector import GarbageCollector
            GarbageCollector.add_thread(cls.thread)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            xbmc.log('Exception: ' + str(e), xbmc.LOGERROR)
            module_logger.exception('')


if __name__ == '__main__':
    import threading
    from common.garbage_collector import GarbageCollector

    module_logger.debug('starting service.py service.kodi.tts service thread')
    # sys.exit()
    #
    try:
        MainThreadLoop().event_processing_loop()
    except:
        pass
    try:
        PythonDebugger.disable()
    except Exception as e:
        module_logger.exception('')
    try:
        #  Debug.dump_all_threads()
        pending_threads: int = GarbageCollector.reap_the_dead()
        tmp_path: str = xbmcvfs.translatePath("special://home/temp/kodi.threads")
        debug_file = io.open(tmp_path,
                             mode='w',
                             buffering=1,
                             newline=None,
                             encoding='ASCII')
        for tries in range(0, 10):
            #  Debug.dump_all_threads()
            #  pending_threads: int = GarbageCollector.reap_the_dead()
            pending_threads: int = 0
            for a_thread in threading.enumerate():
                if a_thread.is_alive():
                    pending_threads += 1
                    xbmc.log(f'Still alive thread: {a_thread.name}')
                else:
                    a_thread.join()
                    xbmc.log(f'Joined thread: {a_thread.name}')
            unaccounted_for_threads: int = threading.active_count()
            if unaccounted_for_threads > 0:  # Main
                xbmc.log(f'Threads remaining: {unaccounted_for_threads} '
                         f'pending: {pending_threads}', xbmc.LOGDEBUG)
                faulthandler.dump_traceback(file=debug_file, all_threads=True)
            if pending_threads < 2:  # Main will still be present
                break
        debug_file.close()
    except Exception as e:
        xbmc.log(f'Exception occured shutting down MainThreadLoop {e}')
        PythonDebugger.disable()
    xbmc.log('TTS Execution Done', xbmc.LOGDEBUG)
    sys.exit(0)
