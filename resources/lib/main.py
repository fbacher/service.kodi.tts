# -*- coding: utf-8 -*-


from common.exceptions import AbortException
from common.constants import Constants
from common.configuration_utils import ConfigUtils
import xbmcvfs
import sys
import os
import xbmc
import io
import signal
import faulthandler
from time import sleep
from common.python_debugger import PythonDebugger

REMOTE_DEBUG: bool = False

debug_file = io.open("/home/fbacher/.kodi/temp/kodi.crash", mode='w', buffering=1,
                     newline=None,
                     encoding='ASCII')

faulthandler.register(signal.SIGUSR1, file=debug_file, all_threads=True)

if REMOTE_DEBUG:
    xbmc.log('About to PythonDebugger.enable tts.main', xbmc.LOGINFO)
    PythonDebugger.enable('kodi.tts')
    sleep(1)
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
        startService()
        xbmc.log('main service thread started', xbmc.LOGDEBUG)


if __name__ == '__main__':
    main()
