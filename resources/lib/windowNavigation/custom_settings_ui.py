from __future__ import annotations  # For union operator |

import xbmc

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


class SettingsGUI:
    '''
    classdocs
    '''

    gui: SettingsDialog = None

    def __init__(self, params):
        '''
        Constructor
        '''
        clz = type(self)
        self._logger = module_logger.getChild(self.__class__.__name__)
        clz.gui: SettingsDialog = None

    @staticmethod
    def launch():
        threading.current_thread.name = 'SettingsGUI'
        script_path = Constants.ADDON_PATH
        # Settings.save_settings()
        SettingsGUI.gui = SettingsDialog('script-tts-settings-dialog.xml',
                             script_path,
                             'Default')
        xbmc.log(f'SettingsGUI.gui.')
        SettingsGUI.gui.doModal()
        SettingsGUI.gui = None
