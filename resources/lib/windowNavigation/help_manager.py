# coding=utf-8
from __future__ import annotations
import queue
import threading
from typing import ForwardRef, Tuple

import xbmc

from common import AbortException
from common.constants import Constants
from common.garbage_collector import GarbageCollector
from common.logger import BasicLogger
from common.monitor import Monitor
from windowNavigation.help_dialog import HelpDialog


if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_logger(__name__)
else:
    module_logger = BasicLogger.get_logger(__name__)


class HelpManager(threading.Thread):

    instance: ForwardRef('HelpManager') = None
    logger: BasicLogger = None

    HELP: str = 'help'
    HELP_DIALOG: str = 'help_dialog'

    DIALOG_VISIBLE: str = 'visible'
    DIALOG_NOTIFY: str = 'notify'
    DIALOG_MODAL: str = 'modal'

    def __init__(self):
        """
        Constructor
        """
        clz = type(self)
        clz.logger = module_logger
        HelpManager.instance = self
        self.gui: HelpDialog = None
        self.dialog_ready: bool = False
        self.do_modal: bool = False
        self.help_queue = queue.SimpleQueue()
        #  self.do_modal_queue = queue.SimpleQueue()
        self.is_modal: threading.Condition = threading.Condition()
        self.wants_modal: bool = False
        self.thread: threading.Thread | None = None
        self.help_dialog_thread: threading.Thread | None = None

        clz.logger.debug(f'Initialized HelpManager')
        self.thread = threading.Thread(target=self.help_queue_processor,
                                       name=f'help_q')
        self.thread.start()
        GarbageCollector.add_thread(self.thread)

    def help_queue_processor(self):
        """
        It seems that dialog.doModal MUST be called in the same thread that it
        was instantiated, or onInit is not called.

        :return:
        """
        clz = type(self)

        # Launch and doModal
        try:
            self.help_dialog_thread = threading.Thread(target=self.launch,
                                                       name=f'help_dlg')
            self.help_dialog_thread.start()
            GarbageCollector.add_thread(self.help_dialog_thread)
        except AbortException:
            return   # Let thread die
        except Exception:
            self.logger.exception('')

        try:
            while not Monitor.exception_on_abort(timeout=0.20):
                try:
                    cmd: Tuple[str, str, str] = self.help_queue.get_nowait()
                    if cmd[0] != 'blah':  # clz.DIALOG_VISIBLE:
                        self.logger.debug(f'About to go Modal')
                        if self.gui is None:
                            #  TODO FIXME!
                            self.logger.debug('Dialog not running')
                        elif self.is_modal.acquire(blocking=False):
                            # NOT modal
                            self.wants_modal = True
                            self.is_modal.release()
                        # Dialog will add to queue and handle properly with or
                        # without it being modal
                        self.gui.notify(cmd[0], cmd[1])
                except queue.Empty:
                    pass
                except AbortException:
                    return  # Let thread die
                except Exception as e:
                    self.logger.exception('')
        except AbortException:
            return  # Let thread die
        except Exception as e:
            self.logger.exception('')

    '''
    def dialog_baby_sitter(self):
        clz = type(self)
        while not Monitor.exception_on_abort(timeout=0.20):
            try:
                cmd: str
                text: str
                cmd, text = self.help_queue.get_nowait()
                if not self.dialog_ready:
                    self.dialog_queue.put((clz.DIALOG_VISIBLE, None, None))
                    while not Monitor.exception_on_abort(timeout=0.5):
                        self.dialog_ready = True
                        if self.dialog_ready:
                            break
                    self.gui.notify(cmd, text)
            except queue.Empty:
                pass
            except AbortException:
                return  # Let thread die
            except Exception:
                self.get.exception('')
        '''

    def gui_callback(self, **kwargs):
        clz = type(self)
        cmd: str = kwargs.get('cmd', None)
        if cmd is None:
            return
        if cmd == clz.DIALOG_MODAL:
            self.dialog_ready = True

    @staticmethod
    def notify(cmd: str, text: str):

        module_logger.debug(f'In notify: {cmd} {text}')

        if HelpManager.instance is None:
            if HelpManager.instance is None:
                module_logger.debug(f'creating instance')
                HelpManager()
        module_logger.debug(f'Setting cmd: {cmd} {text}')
        HelpManager.instance.help_queue.put_nowait((cmd, text))

    def launch(self):
        clz = self.__class__
        try:
            self.logger.debug(f'In launch')
            if self.gui is None:
                self.logger.debug(f'creating gui')
                script_path = Constants.ADDON_PATH
                self.gui = HelpDialog('tts-help-dialog.xml',
                                      str(script_path),
                                      'Custom',
                                      defaultRes='1080i',
                                      callback=self.gui_callback)
                self.logger.debug(f'launched HelpManager.gui')
                self.dialog_ready = False
                # HelpManager.instance.gui.doModal()
        except AbortException:
            return  # Let thread die
        except Exception as e:
            self.gui = None
            self.logger.exception('')

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
                            if first_time:
                                self.gui.doModal()
                                #  first_time = False
                            else:
                                self.gui.show()
                                first_time = True
                            self.is_modal.notify()
                except queue.Empty:
                    pass
                except AbortException:
                    return  # Let thread die
                except Exception:
                    self.logger.exception('')
        except AbortException:
            return  # Let thread die
        except Exception:
            self.logger.exception('')
