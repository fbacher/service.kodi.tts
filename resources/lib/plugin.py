
from common.logger import *
import xbmc
import io
import signal
import faulthandler
from time import sleep
from common.python_debugger import PythonDebugger

REMOTE_DEBUG: bool = False

# PATCH PATCH PATCH
# Monkey-Patch a well known, embedded Python problem
#
# from common.strptime_patch import StripTimePatch
# StripTimePatch.monkey_patch_strptime()

debug_file = io.open("/home/fbacher/.kodi/temp/kodi.crash", mode='w', buffering=1,
                     newline=None,
                     encoding='ASCII')

faulthandler.register(signal.SIGUSR1, file=debug_file, all_threads=True)

if REMOTE_DEBUG:
    xbmc.log('About to PythonDebugger.enable from tts.plugin', xbmc.LOGINFO)
    PythonDebugger.enable('kodi.tts')
    sleep(1)


module_logger = LazyLogger.get_module_logger(module_path=__file__)


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
    main()
