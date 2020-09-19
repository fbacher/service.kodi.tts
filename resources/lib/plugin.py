import os
import sys

import xbmc

from common.constants import Constants
REMOTE_DEBUG: bool = False

if REMOTE_DEBUG:
    try:
        import pydevd

        # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
        try:
            xbmc.log('Trying to attach to debugger', xbmc.LOGDEBUG)
            '''
                If the server (your python process) has the structure
                    /user/projects/my_project/src/package/module1.py

                and the client has:
                    c:\my_project\src\package\module1.py

                the PATHS_FROM_ECLIPSE_TO_PYTHON would have to be:
                    PATHS_FROM_ECLIPSE_TO_PYTHON = \
                          [(r'c:\my_project\src', r'/user/projects/my_project/src')
                # with the addon script.module.pydevd, only use `import pydevd`
                # import pysrc.pydevd as pydevd
            '''
            addons_path = os.path.join(Constants.ADDON_PATH, '..',
                                       'script.module.pydevd', 'lib', 'pydevd.py')

            sys.path.append(addons_path)
            # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse
            # console
            try:
                pydevd.settrace('localhost', stdoutToServer=True,
                                stderrToServer=True)
            except AbortException:
                exit(0)
            except Exception as e:
                xbmc.log(
                    ' Looks like remote debugger was not started prior to plugin start',
                    xbmc.LOGDEBUG)
        except BaseException:
            xbmc.log('Waiting on Debug connection', xbmc.LOGDEBUG)
    except ImportError:
        REMOTE_DEBUG = False
        pydevd = None


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
