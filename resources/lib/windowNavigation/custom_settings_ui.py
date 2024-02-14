from __future__ import annotations  # For union operator |

'''
Created on Jul 7, 2020

@author: fbacher
'''
import threading

from common import *

from common.constants import Constants
from common.logger import (BasicLogger)
from windowNavigation.settings_dialog import SettingsDialog

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)
else:
    module_logger = BasicLogger.get_module_logger()


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
        threading.current_thread.name = 'SettingsGUI'
        script_path = Constants.ADDON_PATH
        # Settings.save_settings()
        gui = SettingsDialog('script-tts-settings-dialog.xml',
                             script_path,
                             'Default')
        gui.doModal()
