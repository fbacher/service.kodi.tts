# -*- coding: utf-8 -*-
import os
import sys
import xbmc

REMOTE_DBG = False  # True

# append pydev remote debugger
if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try:
        xbmc.log('service.tts trying to attach to debugger', xbmc.LOGDEBUG)

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
    if os.path.exists(os.path.join(xbmc.translatePath('special://profile'),
                                   'addon_data', 'service.xbmc.tts', 'DISABLED')):
        xbmc.log('service.xbmc.tts: DISABLED - NOT STARTING')
        return

    arg = None
    if len(sys.argv) > 1:
        arg = sys.argv[1] or False
    extra = sys.argv[2:]
    # Deprecated in Gotham - now using NotifyAll
    if arg and arg.startswith('key.'):
        command = arg[4:]
        from lib import util
        util.sendCommand(command)
    elif arg and arg.startswith('keymap.'):
        command = arg[7:]
        from lib import keymapeditor
        keymapeditor.processCommand(command)
    elif arg == 'settings_dialog':
        from lib import util
        util.selectSetting(*extra)
    elif arg == 'player_dialog':  # Deprecated in 0.0.86 - now using NotifyAll
        from lib import util
        util.selectPlayer(*extra)
    elif arg == 'backend_dialog':  # Deprecated in 0.0.86 - now using NotifyAll
        from lib import util
        util.selectBackend()
    # No longer used, using XBMC.Addon.OpenSettings(service.xbmc.tts) in
    # keymap instead
    elif arg == 'settings':
        from lib import util
        util.xbmcaddon.Addon().openSettings()
    elif arg is None:
        from service import startService
        startService()


if __name__ == '__main__':
    main()
