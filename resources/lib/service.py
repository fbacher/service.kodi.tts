# -*- coding: utf-8 -*-
#

import sys

import xbmc
import xbmcaddon

from common.critical_settings import CriticalSettings
from common.python_debugger import PythonDebugger

REMOTE_DEBUG: bool = False

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
    xbmc.sleep(5000)

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


from backends.settings.base_service_settings import BaseServiceSettings
from common.minimal_monitor import MinimalMonitor

from utils import addoninfo
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

    # BaseServiceSettings()
    from startup.bootstrap_engines import BootstrapEngines
    try:
        BootstrapEngines.init()
        BackendInfo.init()
        addoninfo.initAddonsData()
        from backends.audio.bootstrap_players import BootstrapPlayers

        from service_worker import TTSService
        TTSService().start()
        xbmc.log('started service.startService thread', xbmc.LOGDEBUG)
    except AbortException:
        reraise(*sys.exc_info())
    except Exception as e:
        xbmc.log(f'Exception {e.msg}. Exiting')

if __name__ == '__main__':
    import threading
    threading.current_thread().name = "service.py"
    module_logger.debug('starting service.py service.kodi.tts service thread')
    # sys.exit()
    #
    try:
       startService()
    except Exception as e:
       module_logger.exception('')
