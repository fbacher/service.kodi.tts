# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import faulthandler
import io
import subprocess
from pathlib import Path
from typing import Dict, Final
#
import os
import signal
import sys

import xbmc
import xbmcaddon
import xbmcvfs

from common.debug import Debug
from common.message_ids import MessageId
from common.phrases import PhraseList
from utils.keymapeditor import Status
from utils.utils_ll import UtilsLowLevel

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


from common.logger import *

# Default logging is info, otherwise debug_v
if False:
    definitions = {'tts': INFO}
else:
    definitions = {
        'tts': INFO,
        'tts.backends': INFO,
        'tts.backends.driver': DEBUG,
        'tts.backends.google': INFO,
        'tts.backends.espeak': DEBUG,
        'tts.backends.espeak_settings': DEBUG,
        'tts.backends.no_engine': INFO,
        'tts.backends.no_engine_settings': INFO,
        'tts.backends.engines.google_downloader': INFO,
        'tts.backends.engines.google_settings': INFO,
        'tts.backends.engines.speech_generator': INFO,
        'tts.backends.engines.windows.powershell': DEBUG_V,
        'tts.backends.engines.windows.powershell_settings': DEBUG,
        'tts.backends.settings.language_info': INFO,
        'tts.backends.settings.langcodes_wrapper': INFO,
        'tts.backends.settings.service_types': INFO,
        'tts.backends.settings.settings_helper': INFO,
        'tts.backends.settings.settings_map': DEBUG,
        'tts.backends.settings.validators': INFO,
        'tts.backends.base': DEBUG,
        'tts.backends.audio.base_audio': INFO,
        'tts.backends.audio.mpv_audio_player': INFO,
        'tts.backends.audio.mplayer_audio_player': INFO,
        'tts.backends.audio.sfx_audio_player': DEBUG,
        'tts.backends.players.sfx_settings': INFO,
        'tts.backends.audio.sound_capabilities': INFO,
        'tts.backends.audio.worker_thread': INFO,
        'tts.backends.transcoders.trans': INFO,
        'tts.cache.voicecache': INFO,
        'tts.common.base_services': INFO,
        'tts.common.garbage_collector': INFO,
        'tts.common.logger': INFO,
        'tts.common.monitor': INFO,
        'tts.common.phrases': INFO,
        'tts.common.phrase_manager': INFO,
        'tts.common.settings_cache': DEBUG,
        'tts.common.settings_low_level': DEBUG,
        'tts.common.settings': DEBUG,
        'tts.common.simple_run_command': INFO,
        'tts.common.simple_pipe_command': INFO,
        'tts.common.slave_communication': INFO,
        'tts.common.slave_run_command': INFO,
        'tts.common.utils': INFO,
        'tts.utils.util': INFO,
        'tts.windows': INFO,
        'tts.windows.backgroundprogress': INFO,
        'tts.windows.base': INFO,
        'tts.windows.busydialog': INFO,
        'tts.windows.contextmenu': INFO,
        'tts.windows.custom_tts': INFO,
        'tts.windows.guitables': INFO,
        'tts.windows.homedialog': INFO,
        'tts.windows.libraryviews': INFO,
        'tts.windows.notice': DEBUG,
        'tts.windows.playerstatus': INFO,
        'tts.windows.progressdialog': INFO,
        'tts.windows.pvr': INFO,
        'tts.windows.pvrguideinfo': INFO,
        'tts.windows.selectdialog': INFO,
        'tts.windows.settings': INFO,
        'tts.windows.skintables': INFO,
        'tts.windows.subtitlesdialog': INFO,
        'tts.windows.textviewer': INFO,
        'tts.windows.ui_constants': INFO,
        'tts.windows.videoinfodialog': INFO,
        'tts.windows.virtualkeyboard': INFO,
        'tts.windows.weather': INFO,
        'tts.windows.window_state_monitor': INFO,
        'tts.windows.yesnodialog': INFO,
        'tts.windows.windowparser': INFO,
        'tts.gui': INFO,
        'tts.gui.window_structure': INFO,
        'tts.gui.parser': INFO,
        'tts.service': DEBUG,
        'tts.service_worker': DEBUG,
        'tts.startup.bootstrap_engines': INFO,
        'tts.startup.bootstrap_converters': INFO,
        'tts.backends.audio.bootstrap_players': INFO,
        'tts.backends.players.mpv_player_settings': INFO,
        'tts.backends.players.mplayer_settings': INFO,
        'tts.windowNavigation.choice': INFO,
        'tts.windowNavigation.configure': DEBUG,
        'tts.windowNavigation.help_dialog': INFO,
        'tts.windowNavigation.selection_dialog': INFO,
        'tts.windowNavigation.settings_dialog': DEBUG,
        'utils.keymapeditor': DEBUG
    }
# xbmc.log(f'configuring debug_levels INFO: {logging.INFO} DEBUG: {DEBUG} '
#          f'VERBOSE: {DEBUG_V} EXTRA_VERBOSE: '
#          f'{DEBUG_XV}')
# Explicitly set logger name to 'service' instead of __name__ since __name__
# becomes '__main__' since this is the main module.
logger_name = 'service'
MY_LOGGER = BasicLogger.get_logger('service')

BasicLogger.config_debug_levels(replace=False, default_log_level=DEBUG,
                                definitions=definitions)

from common import *
from common.minimal_monitor import MinimalMonitor
from common.python_debugger import PythonDebugger

DEVELOPMENT_BUILD: Final[bool] = False
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
from common.settings import Settings
from backends.settings.setting_properties import SettingProp, SettingType

from common.constants import Constants
from common.system_queries import SystemQueries
import enabler

__version__ = Constants.VERSION


def resetAddon():
    global DO_RESET
    if DO_RESET:
        return
    DO_RESET = True
    MY_LOGGER.info('Resetting addon...')
    xbmc.executebuiltin(
            'RunScript(special://home/addons/service.kodi.tts/resources/lib/tools'
            '/enabler.py,RESET)')


def preInstalledFirstRun() -> bool:
    """
    Performs basic configuration of:
      On Windows:
         paths to mpv, etc.
         permission to use powershell Navigator bridge script
      keymap
      initial settings for help, hint, etc.
      :return: True if something was configured requiring TTS to restart
               otherwise, False
    """
    restart: bool = False
    something_configured: bool = False
    something_failed: bool = False
    return False
    '''
    if False:
        if not Settings.is_initial_run():  # Do as little as possible if there is no
            xbmc.log('is NOT initial_run', xbmc.LOGINFO)
            MY_LOGGER.debug(f'is NOT initial_run')
            # pre-install
            if SystemQueries.wasPreInstalled():
                MY_LOGGER.info('PRE INSTALL: REMOVED')
                # Set version to 0.0.0 so normal first run will execute and fix the
                # keymap
                Settings.setSetting(SettingProp.VERSION, '0.0.0', None)
                enabler.markPreOrPost()  # Update the install status
            return False

        xbmc.log('is initial_run', xbmc.LOGINFO)
        MY_LOGGER.debug(f'is initial_run')
        lastVersion = Settings.getSetting(ServiceKey.VERSION)
        xbmc.log(f'last_version: {lastVersion}', xbmc.LOGINFO)

        if not enabler.isPostInstalled() and SystemQueries.wasPostInstalled():
            MY_LOGGER.info('POST INSTALL: UN-INSTALLED OR REMOVED')
            xbmc.log('POST INSTALL: UN-INSTALLED OR REMOVED')
            # Add-on was removed. Assume un-installed and treat this as a
            # pre-installed first run to disable the addon
        elif lastVersion:
            MY_LOGGER.debug(f'lastVersion')
            xbmc.log('lastVersion', xbmc.LOGINFO)
            enabler.markPreOrPost()  # Update the install status
            return False

        # Set version to 0.0.0 so normal first run will execute on first enable
        Settings.set_service_setting(ServiceKey.VERSION, '0.0.0')

        xbmc.log(f'PRE-INSTALLED FIRST RUN', xbmc.LOGINFO)
        MY_LOGGER.info('PRE-INSTALLED FIRST RUN')

    #
    # Detect when a newer (or older) version has been installed
    # Use two settings:
    #  * installed_version which forced to version 0.0.0 on every
    #    install or update. Then this code notices it is 0.0.0, runs config
    #    and sets the setting to the real version.
    #  To detect reinstalling the same version, the installed_version setting will
    #  still be clobbered to 0.0.0, so the same config will occur.

    # MUST be done before bootstrap engines/players

        if dependencies_configured:
            something_configured = True
            Settings.set_configure_dependencies_on_startup(False)
            Settings.commit_settings()
        else:
            something_failed = True

    if something_configured:
        pass
        #  Settings.commit_settings()
    xbmc.log(f'exiting something_configured: {something_configured}', xbmc.LOGDEBUG)
    return something_configured
    '''


def configure_dependencies_windows() -> bool:
    config_script_path: Path = Path(Constants.ADDON_DIRECTORY) / 'config_script.bat'
    something_configured: bool = False
    # TTS not functioning yet.
    #
    # show_and_say_notification(message='Configuring permissions and paths. '
    #                           'Will prompt for Admin privilege',
    #                            time_s=5.0)
    env = os.environ.copy()
    if Constants.PLATFORM_WINDOWS:
        cmdline: str = str(config_script_path)
        xbmc.log(f'Running command: Windows args: {cmdline}', xbmc.LOGINFO)
        try:
            completed: subprocess.CompletedProcess
            completed = subprocess.run(cmdline, input=' \n', capture_output=True,
                                       text=True, env=env, close_fds=True,
                                       encoding='utf-8', shell=False, check=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            if completed.returncode != 0:
                something_configured = False
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'config output: {completed.stdout}')
            else:
                something_configured = True
        except subprocess.CalledProcessError:
            MY_LOGGER.exception('')
        except OSError:
            MY_LOGGER.exception('')
        except Exception:
            MY_LOGGER.exception('')
    return something_configured

def startService():
    """
    This is a separate thread that runs the service_worker

    :return:
    """
    configure_something: bool = False
    try:
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('starting service.startservice thread')
        from backends.settings.base_service_settings import BaseServiceSettings

        BaseServiceSettings.define_settings()
        if Settings.is_initial_run():
            Settings.set_configure_dependencies_on_startup(True)
            Settings.set_configure_keymap_on_startup(True)
            Settings.set_start_config_gui_on_startup(True)

            # Hints are embedded in new screen scraper metadata, which config only
            # uses at this time.
            Settings.set_hint_text_on_startup(True)

            # Help is embedded in new screen scraper metadata
            Settings.set_config_help_on_startup(False)  # How do these
            Settings.set_extended_help_on_startup(False)  # Does not appear to do anything yet
            Settings.set_introduction_on_startup(False)

        if (Settings.is_configure_keymap_on_startup() or
            Settings.is_introduction_on_startup() or
            Settings.is_start_config_gui_on_startup() or
            #  Settings.is_configure_dependencies_on_startup() or
            Settings.is_config_help_on_startup() or
            Settings.is_introduction_on_startup()):
            configure_something = True

        something_configured: bool = False
        something_failed: bool = False
        if Settings.is_configure_dependencies_on_startup():
            # Configure dependent packages: Paths, permissions, etc.
            if Constants.PLATFORM_WINDOWS:
                something_configured = configure_dependencies_windows()

        # if preInstalledFirstRun():
        #     show_and_say_notification('Configuration changed requiring restart of Kodi.tts',
        #                               time_s=10.0)
        #     return
        #  Do NOT remove import!!
        from startup.bootstrap_engines import BootstrapEngines
        BootstrapEngines.init()
        from service_worker import TTSService
        TTSService().start()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('started service.startService thread')

        if not TTSService.is_ready_to_voice(timeout=2.0):
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Not ready to voice')
        if configure_something:
            time_s: float = 5.0
            # UtilsLowLevel.show_and_say_notification(
            #         message=MessageId.PERFORM_CONFIG_TASKS.get_msg(),
            #         time_s=time_s, block=True)

        configure_keymap: bool = Settings.is_configure_keymap_on_startup()
        if configure_keymap:
            time_s: float = 5.0
            UtilsLowLevel.show_and_say_notification(
                    message=MessageId.INSTALLING_BASIC_KEYMAP.get_msg(),
                    time_s=time_s, block=True)

            from utils import keymapeditor
            status: Status = keymapeditor.installBasicKeymap()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'keymap status: {status}')
            msg: MessageId | None = None
            if status == Status.NO_CHANGE:
                msg = MessageId.KEYMAP_NO_CHANGE
                someting_configured = True
            elif status == Status.RESTART:
                someting_configured = True
                msg = MessageId.UPDATED_KEYMAPS_IN_EFFECT
            elif status == Status.FAILED:
                something_failed = True
                msg = MessageId.FAILED_TO_UPDATE_KEYMAP
            time_s: float = 5.0
            UtilsLowLevel.show_and_say_notification(
                    message=msg.get_msg(),
                    time_s=time_s, block=True)
            Settings.set_configure_keymap_on_startup(False)
            Settings.commit_settings()

        # Normally enable extended help on the first use after installation
        # It can be set permanently by user
        if Settings.is_extended_help_on_startup():
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'extended_help on startup')
            time_s: float = 5.0
            UtilsLowLevel.show_and_say_notification(
                    message=MessageId.ENABLING_EXTENDED_HELP.get_msg(),
                    time_s=time_s, block=True)
            TTSService.help()

        if Settings.is_hint_text_on_startup():
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'hint_text on startup')
            time_s: float = 5.0
            UtilsLowLevel.show_and_say_notification(
                    message=MessageId.ENABLING_HINTS.get_msg(),
                    time_s=time_s, block=True)
            TTSService.set_voice_hint_on()
        # Save startup setting changes.
        # TODO: Consider ability to commit individual settings, such as these
        #       startup related ones.

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'is_start_config_gui_on_startup: '
                            f'{Settings.is_start_config_gui_on_startup()}')
        if Settings.is_start_config_gui_on_startup():
            time_s: float = 5.0
            UtilsLowLevel.show_and_say_notification(
                    message=MessageId.OPEN_CONFIG_DIALOG.get_msg(),
                    time_s=time_s, block=True)
            TTSService.config_settings()

        Settings.set_configure_dependencies_on_startup(False)
        Settings.set_start_config_gui_on_startup(False)
        Settings.set_hint_text_on_startup(False)
        Settings.set_config_help_on_startup(False)
        Settings.set_extended_help_on_startup(False)
        Settings.set_introduction_on_startup(False)
        Settings.set_initial_run(False)
        Settings.commit_settings()

    except AbortException:
        pass  # About to exit thread
    except Exception as e2:
        MY_LOGGER.exception('')
        MinimalMonitor.set_abort_received()

    if configure_something:
        time_s: float = 5.0
        UtilsLowLevel.show_and_say_notification(
                message=MessageId.CONFIGURATION_COMPLETE.get_msg(),
                time_s=time_s, block=True)
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
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Starting event_processing_loop')
        try:
            if os.path.exists(os.path.join(xbmcvfs.translatePath('special://profile'),
                                           'addon_data', 'service.kodi.tts', 'DISABLED')):
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug('service.kodi.tts: DISABLED - NOT STARTING')
                return

            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'initializing worker_thread')
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
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Starting worker thread')
                        cls.start_worker_thread()

            MinimalMonitor.exception_on_abort(timeout=timeout)
        except AbortException:
            return
        except Exception as e:
            MY_LOGGER.exception(e)

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
            MY_LOGGER.exception('')


if __name__ == '__main__':
    import threading
    from common.garbage_collector import GarbageCollector

    if MY_LOGGER.isEnabledFor(DEBUG):
        MY_LOGGER.debug('starting service.py service.kodi.tts service thread')
    try:
        MainThreadLoop().event_processing_loop()
    except:
        pass
    try:
        PythonDebugger.disable()
    except Exception as e:
        MY_LOGGER.exception('')
    try:
        Debug.dump_all_threads()
        pending_threads: int = GarbageCollector.reap_the_dead()
        """
        tmp_path: str = xbmcvfs.translatePath("special://home/temp/kodi.threads")
        debug_file = io.open(tmp_path,
                             mode='w',
                             buffering=1,
                             newline=None,
                             encoding='ASCII')
        """
        for tries in range(0, 10):
            xbmc.sleep(50)
            Debug.dump_all_threads()
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
            if unaccounted_for_threads > 1:  # Main
                xbmc.log(f'Threads remaining: {unaccounted_for_threads} '
                         f'pending: {pending_threads}', xbmc.LOGDEBUG)
                #  faulthandler.dump_traceback(file=debug_file, all_threads=True)
            if pending_threads < 2:  # Main will still be present
                xbmc.log('Exiting SHUTDOWN LOOP, only MAIN thread remains')
                break
        #  debug_file.close()
        xbmc.sleep(50)
        xbmc.log(f'TTS SHUTDOWN COMPLETE')
    except Exception as e:
        xbmc.log(f'Exception occured shutting down MainThreadLoop {e}')
    if REMOTE_DEBUG:
        PythonDebugger.disable()
    xbmc.log('TTS Execution Done', xbmc.LOGDEBUG)
    # sys.exit(0)
    # sys.exit()
