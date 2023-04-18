# -*- coding: utf-8 -*-

import io
import os
import xbmc

from common.critical_settings import *
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
from common.configuration_utils import ConfigUtils
# import faulthandler


try:
    pass
    # import web_pdb;

    # web_pdb.set_trace()
except Exception as e:
    pass


def main():
    if os.path.exists(os.path.join(xbmcvfs.translatePath('special://profile'),
                                   'addon_data', 'service.kodi.tts', 'DISABLED')):
        xbmc.log('service.kodi.tts: DISABLED - NOT STARTING')
        return

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
    elif arg is None:
        from service import startService
        xbmc.log('main.py service.kodi.tts service thread starting', xbmc.LOGDEBUG)
        startService()


if __name__ == '__main__':
    import threading
    threading.current_thread().name = "main.py"
    main()
