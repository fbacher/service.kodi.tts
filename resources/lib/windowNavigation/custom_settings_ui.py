'''
Created on Jul 7, 2020

@author: fbacher
'''

from windowNavigation.settings_dialog import SettingsDialog
from common.settings import Settings
from common.constants import Constants
from common.logger import (Logger, LazyLogger)

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = LazyLogger.get_addon_module_logger(
    ).getChild('common.messages')
else:
    module_logger = LazyLogger.get_addon_module_logger()


class SettingsGUI(object):
    '''
    classdocs
    '''

    def __init__(self, params):
        '''
        Constructor
        '''
        self._logger = module_logger.getChild(self.__class__.__name__)

    @staticmethod
    def launch():

        script_path = Constants.ADDON_PATH
        Settings.begin_configuring_settings()
        gui = SettingsDialog('script-tts-settings-dialog.xml',
                             script_path,
                             'Default')
        gui.doModal()
