import sys

import xbmc
import xbmcaddon
import xbmcvfs

from common.constants import Constants
from common.logger import LazyLogger

module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)


class OldLogger:

    DEBUG = None
    VERBOSE = None
    _logger = module_logger.getChild('Oldlogger')

    @classmethod
    def ERROR(cls, txt, hide_tb=False, notify=False):
        short = str(sys.exc_info()[1])
        if hide_tb:
            cls._logger.error('{0} - {1}'.format(txt, short))
            return short
        print("_________________________________________________________________________________")
        cls._logger.error(str(txt))
        import traceback
        tb = traceback.format_exc()
        for l in tb.splitlines():
            print('    ' + l)
        print("_________________________________________________________________________________")
        print("`")
        if notify:
            cls.showNotification('ERROR: {0}'.format(short))
        return short



    @classmethod
    def showNotification(cls, message, time_ms=3000, icon_path=None, header='XBMC TTS'):
        try:
            icon_path = icon_path or xbmcvfs.translatePath(
                xbmcaddon.Addon(Constants.ADDON_ID).getAddonInfo('icon'))
            xbmc.executebuiltin('Notification({0},{1},{2},{3})'.format(
                header, message, time_ms, icon_path))
        except RuntimeError:  # Happens when disabling the addon
            cls._logger.info(message)

    @classmethod
    def reload(cls):
        cls.DEBUG = cls.getSettingBool('debug_logging', True)
        cls.VERBOSE = cls.getSettingBool('verbose_logging', False)

    @classmethod
    def getSettingBool(cls, key, default=None):
        setting = xbmcaddon.Addon().getSettingBool(key)
        if setting is None:
            setting = None
        return setting


OldLogger.reload()
