
import sys
import xbmc
import xbmcgui
import xbmcplugin
import backends

REMOTE_DBG = False

# append pydev remote debugger
if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try:
        xbmc.log('service.tts.service trying to attach to debugger', xbmc.LOGDEBUG)

        '''
            If the server (your python process) has the structure
                /user/projects/my_project/src/package/module1.py

            and the client has:
                c:\my_project\src\package\module1.py

            the PATHS_FROM_ECLIPSE_TO_PYTHON would have to be:
                PATHS_FROM_ECLIPSE_TO_PYTHON = [(r'c:\my_project\src', 
                r'/user/projects/my_project/src')
            # with the addon script.module.pydevd, only use `import pydevd`
            # import pysrc.pydevd as pydevd
        '''
        sys.path.append('/home/fbacher/.kodi/addons/script.module.pydevd/lib')
        import pydevd

        # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse
        # console
        try:
            pydevd.settrace('localhost', stdoutToServer=True,
                            stderrToServer=True)
        except (Exception) as e:
            xbmc.log(
                'Looks like remote debugger was not started prior to plugin start',
                xbmc.LOGDEBUG)
            xbmc.log(str(e), xbmc.LOGDEBUG)

    except (ImportError) as e:
        msg = 'Error:  You must add org.python.pydev.debug.pysrc to your PYTHONPATH.'
        xbmc.log(msg, xbmc.LOGDEBUG)
        xbmc.log(str(e), xbmc.LOGDEBUG)
        sys.stderr.write(msg)
        sys.exit(1)
    except (BaseException) as e:
        xbmc.log('Waiting on Debug connection', xbmc.LOGDEBUG)
        xbmc.log(str(e), xbmc.LOGDEBUG)


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
