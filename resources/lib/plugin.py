# coding=utf-8
from __future__ import annotations  # For union operator |

import faulthandler
import io
import signal
from time import sleep

from common import *

from common.critical_settings import *
from common.python_debugger import PythonDebugger

REMOTE_DEBUG: bool = False
addon_id: str = CriticalSettings.ADDON_ID
debug_file = io.open("/home/fbacher/.kodi/temp/kodi.crash", mode='w', buffering=1,
                     newline=None,
                     encoding='utf-8')

faulthandler.register(signal.SIGUSR1, file=debug_file, all_threads=True)

if REMOTE_DEBUG:
    xbmc.log('About to call PythonDebugger.enable from tts plugin', xbmc.LOGINFO)
    PythonDebugger.enable(addon_id)
    sleep(1)
try:
    pass
    # import web_pdb;

    # web_pdb.set_trace()
except Exception as e:
    pass

import sys
from common.logger import *
import xbmc

module_logger = BasicLogger.get_logger(__name__)


def main():

    arg = None
    if len(sys.argv) > 1:
        arg = sys.argv[1] or False
    extra = sys.argv[2:]

    '''
    addon_handle = int(sys.argv[1])
    xbmcplugin.setContent(addon_handle, 'executable')

    settingsList = backends.getSettingsList('ResponsiveVoice', 'language')
    idx = 0
    for setting in settingsList:
        label = setting[0]
        label2 = str(idx)
        item = xbmcgui.ListItem(label)
        item.setLabel2(label2)
        # item.setPath('')
        idx += 1
        xbmcplugin.addDirectoryItem(handle=addon_handle, url='a', listitem=item,
                                    isFolder=False, totalItems=len(settingsList))

    xbmcplugin.endOfDirectory(addon_handle)
    '''


if __name__ == '__main__':
    import threading

    threading.current_thread().name = "plugin.py"
    xbmc.log('plugin.py service.kodi.tts starting', xbmc.LOGDEBUG)
    main()
