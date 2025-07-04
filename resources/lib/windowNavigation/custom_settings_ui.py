# coding=utf-8
from __future__ import annotations  # For union operator |

from pathlib import Path

from windowNavigation.settings_dialog import SettingsDialog

'''
import xbmc

from common.phrases import PhraseList


import threading

from common import *

from common.constants import Constants
from common.get import (BasicLogger)
from windowNavigation.settings_dialog import SettingsDialog

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_logger(__name__)
else:
    module_logger = BasicLogger.get_logger(__name__)


class SettingsGUI:
    """
    classdocs
    """

    gui: SettingsDialog = None

    def __init__(self, params):
        """
        Constructor
        """
        clz = type(self)
        self._logger = module_logger
        clz.gui = None

    @staticmethod
    def launch():
        threading.current_thread.name = 'SettingsGUI'
        script_path = Constants.ADDON_PATH
        # Settings.save_settings()
        if SettingsGUI.gui is None:
            SettingsGUI.gui = SettingsDialog('script-tts-settings-dialog.xml',
                                             script_path,
                                             'Custom',
                                             defaultRes='1080i')
        xbmc.log(f'SettingsGUI.gui.')
        SettingsGUI.gui.doModal()
        PhraseList.set_current_expired()
        # SettingsGUI.gui = None


'''
# coding=utf-8

'''
Created on Jul 7, 2020

@author: fbacher
'''

import queue
import threading
from typing import ForwardRef, Tuple

from common import AbortException
from common.constants import Constants
from common.garbage_collector import GarbageCollector
from common.logger import *
from common.monitor import Monitor


MY_LOGGER = BasicLogger.get_logger(__name__)


class SettingsGUI(threading.Thread):

    instance: ForwardRef('HelpManager') = None

    #  HELP: str = 'help'
    #  ELP_DIALOG: str = 'help_dialog'

    VISIBLE: str = 'visible'
    START: str = 'start'
    MODAL: str = 'modal'

    def __init__(self):
        """
        Constructor
        """
        SettingsGUI.instance = self
        self.gui: SettingsDialog = None
        self.dialog_ready: bool = False
        self.do_modal: bool = False
        self.dialog_queue = queue.SimpleQueue()
        #  self.do_modal_queue = queue.SimpleQueue()
        self.is_modal: threading.Condition = threading.Condition()
        self.wants_modal: bool = False
        self.thread: threading.Thread | None = None
        self.launch_thread: threading.Thread | None = None

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Initialized SettingsGUI')
        self.thread = threading.Thread(target=self.dialog_queue_processor,
                                       name=f'dialg_Q')
        self.thread.start()
        GarbageCollector.add_thread(self.thread)

    def dialog_queue_processor(self):
        """
        It seems that dialog.doModal MUST be called in the same thread that it
        was instantiated, or onInit is not called.

        :return:
        """
        clz = type(self)

        # Launch and doModal
        try:
            self.launch_thread = threading.Thread(target=self.launch,
                                                  name=f'setng_dialg')
            self.launch_thread.start()
            GarbageCollector.add_thread(self.launch_thread)
        except AbortException:
            return   # Let thread die
        except Exception:
            MY_LOGGER.exception('')

        try:
            while not Monitor.exception_on_abort(timeout=0.20):
                try:
                    cmd: Tuple[str, str, str] = self.dialog_queue.get_nowait()
                    if cmd[0] != 'blah':  # clz.VISIBLE:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'About to go Modal')
                        if self.gui is None:
                            #  TODO FIXME!
                            if MY_LOGGER.isEnabledFor(DEBUG):
                                MY_LOGGER.debug('Dialog not running')
                        elif self.is_modal.acquire(blocking=False):
                            # NOT modal
                            self.wants_modal = True
                            self.is_modal.release()
                        # Dialog will add to queue and handle properly with or
                        # without it being modal
                        #  self.gui.notify(cmd[0], cmd[1])
                except queue.Empty:
                    pass
                except AbortException:
                    return  # Let thread die
                except Exception as e:
                    MY_LOGGER.exception('')
        except AbortException:
            return  # Let thread die
        except Exception as e:
            MY_LOGGER.exception('')

    '''
    def gui_callback(self, **kwargs):
        clz = type(self)
        cmd: str = kwargs.get('cmd', None)
        if cmd is None:
            return
        if cmd == clz.DIALOG_MODAL:
            self.dialog_ready = True
    '''

    @staticmethod
    def notify(cmd: str, text: str = ''):
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'In notify: {cmd} {text}')

        if SettingsGUI.instance is None:
            if SettingsGUI.instance is None:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'creating instance')
                SettingsGUI()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Setting cmd: {cmd} {text}')
        SettingsGUI.instance.dialog_queue.put_nowait((cmd, text))

    def launch(self):
        clz = self.__class__
        try:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'In launch')
            if self.gui is None:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'creating gui')
                script_path: Path = Constants.ADDON_PATH
                self.gui = SettingsDialog('script-tts-settings-dialog.xml',
                                          str(script_path),
                                          'Custom',
                                          defaultRes='1080i')
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'launched SettingsDialog.gui')
                self.dialog_ready = False
        except AbortException:
            del SettingsGUI.instance
            return  # Let thread die
        except Exception as e:
            self.gui = None
            MY_LOGGER.exception('')

        # Loop that simply calls doModal (and waits) whenever needed.
        first_time: bool = True
        try:
            while not Monitor.exception_on_abort(timeout=0.20):
                try:
                    cmd: str
                    text: str
                    if self.wants_modal:
                        with self.is_modal:
                            self.wants_modal = False
                            if True:  # first_time:
                                self.gui.doModal()
                                # Blocked until no longer modal
                            self.is_modal.notify()
                except queue.Empty:
                    pass
                except AbortException:
                    return  # Let thread die
                except Exception:
                    MY_LOGGER.exception('')
        except AbortException:
            return  # Let thread die
        except Exception:
            MY_LOGGER.exception('')
