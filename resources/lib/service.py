# -*- coding: utf-8 -*-
#
import io
import signal
import sys
import faulthandler
from time import sleep

import xbmc

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
    xbmc.log(f'About to PythonDebugger.enable from tts service', xbmc.LOGINFO)
    xbmc.log(f'PYTHONPATH: {sys.path}', xbmc.LOGINFO)
    PythonDebugger.enable('kodi.tts')
    sleep(1)
try:
    pass
    # import web_pdb;

    # web_pdb.set_trace()
except Exception as e:
    pass


# TODO Remove after eliminating util.getCommand

import re
import time
import queue
import json
import xbmcgui

from common.typing import *

from utils import addoninfo
from backends import audio
from common.settings import Settings
from backends.backend_info_bridge import BackendInfoBridge
from backends.i_tts_backend_base import ITTSBackendBase
from backends.backend_info import BackendInfo
from backends.backend_index import BackendIndex

import windows
from windows import playerstatus, notice, backgroundprogress
from windowNavigation.custom_settings_ui import SettingsGUI
from common.exceptions import AbortException
from common.logger import *
from common.messages import Messages
from common.constants import Constants
from common.configuration_utils import ConfigUtils
from common.system_queries import SystemQueries
from common import utils
import enabler
from utils import util

module_logger = BasicLogger.get_module_logger(module_path=__file__)

__version__ = Constants.VERSION

module_logger.info(__version__)
module_logger.info('Platform: {0}'.format(sys.platform))

if audio.PLAYSFX_HAS_USECACHED:
    module_logger.info('playSFX() has useCached')
else:
    module_logger.info('playSFX() does NOT have useCached')

# util.initCommands()
addoninfo.initAddonsData()

BackendInfo.init()
BackendIndex.init()

DO_RESET = False


def resetAddon():
    global DO_RESET
    if DO_RESET:
        return
    DO_RESET = True
    module_logger.info('Resetting addon...')
    xbmc.executebuiltin(
        'RunScript(special://home/addons/service.kodi.tts/resources/lib/tools/enabler.py,RESET)')


class TTSClosedException(Exception):
    pass


class Commands:
    TOGGLE_ON_OFF: Final[str] = 'TOGGLE_ON_OFF'
    RESET: Final[str] = 'RESET'
    REPEAT: Final[str] = 'REPEAT'
    EXTRA: Final[str] = 'EXTRA'
    ITEM_EXTRA: Final[str] = 'ITEM_EXTRA'
    VOL_UP: Final[str] = 'VOL_UP'
    VOL_DOWN: Final[str] = 'VOL_DOWN'
    STOP: Final[str] = 'STOP'
    SHUTDOWN: Final[str] = 'SHUTDOWN'
    SAY: Final[str] = 'SAY'
    PREPARE_TO_SAY: Final[str] = 'PREPARE_TO_SAY'
    RELOAD_ENGINE: Final[str] = 'RELOAD_ENGINE'
    SETTINGS_BACKEND_GUI: Final[str] = 'SETTINGS.BACKEND_GUI'
    SETTINGS_BACKEND_DIALOG: Final[str] = 'SETTINGS.BACKEND_DIALOG'
    SETTINGS_PLAYER_DIALOG: Final[str] = 'SETTINGS.PLAYER_DIALG'
    SETTINGS_SETTING_DIALOG: Final[str] = 'SETTINGS.SETTING_DIALOG'
    SETTINGS_SETTING_SLIDER: Final[str] = 'SETTINGS.SETTING_SLIDER'


class TTSService(xbmc.Monitor):
    instance = None
    _is_configuring: bool = False
    _logger: BasicLogger = None

    def __init__(self):
        clz = type(self)
        self.speakListCount = None
        clz._logger = module_logger.getChild(self.__class__.__name__)
        super().__init__()  # Appears to not do anything
        self.readerOn: bool = True
        self.stop: bool = False
        self.disable: bool = False
        self.noticeQueue: queue.Queue = queue.Queue()
        self.initState()
        self.active_backend: ITTSBackendBase | None = None
        self.toggle_on: bool = True
        utils.stopSounds()  # To kill sounds we may have started before an update
        utils.playSound('on')
        self.playerStatus = playerstatus.PlayerStatus(10115).init()
        self.bgProgress = backgroundprogress.BackgroundProgress(10151).init()
        self.noticeDialog = notice.NoticeDialog(10107).init()
        self.winID = None
        self.windowReader = None
        self.controlID = None
        self.text = None
        self.textCompare = None
        self.secondaryText = None
        self.keyboardText = ''
        self.progressPercent = ''
        self.lastProgressPercentUnixtime = 0
        self.interval = 400
        self.listIndex = None
        self.waitingToReadItemExtra = None

        # module_logger.info(f'SERVICE STARTED :: Interval: {self.tts.interval}')
        TTSService.instance = self

    @staticmethod
    def get_instance() -> 'TTSService':
        return TTSService.instance

    def onAbortRequested(self):
        self.stop = True
        try:
            self.close_tts()
        except TTSClosedException:
            pass

    @property
    def tts(self):
        if self.is_tts_closed():
            raise TTSClosedException()
        return self.active_backend

    def close_tts(self) -> None:
        if self.active_backend is not None:
            self.active_backend.close()
        else:
            pass

    def is_tts_closed(self) -> bool:
        if self.active_backend is not None:
            return self.active_backend._closed
        else:
            return True

    def onSettingsChanged(self):
        clz = type(self)
        clz._logger.debug(f'onSettingsChanged')
        # Settings.commit_settings()
        #try:
        #    self.tts._update()
        #except TTSClosedException:
        #    return
        # self.checkBackend()
        # self.reloadSettings()
        # self.updateInterval()
        # Deprecated for the addon starting with Gotham - now using NotifyAll
        # (Still used for SHUTDOWN until I figure out the issue when using
        # NotifyAll with that)
        command = util.getCommand()
        if not command:
            return
        self.processCommand(command)

    def processCommand(self, command, data=None):
        clz = type(self)
        from utils import util  # Earlier import apparently not seen when called via NotifyAll
        clz._logger.debug(f'command: {command} toggle_on: {self.toggle_on}')
        if command == Commands.TOGGLE_ON_OFF:
            if self.toggle_on:
                self.toggle_on = False
                utils.playSound('off')
            else:
                self.toggle_on = True
                utils.playSound('on')
        if not self.toggle_on:
            return
        elif command == Commands.RESET:
            pass
        elif command == Commands.REPEAT:
            self.repeatText()
        elif command == Commands.EXTRA:
            self.sayExtra()
        elif command == Commands.ITEM_EXTRA:
            self.sayItemExtra()
        elif command == Commands.VOL_UP:
            self.volumeUp()
        elif command == Commands.VOL_DOWN:
            self.volumeDown()
        elif command == Commands.STOP:
            self.stopSpeech()
        elif command == Commands.SHUTDOWN:
            self.shutdown()
        elif command == Commands.SAY:
            if not data:
                return
            args = json.loads(data)
            if not args:
                return
            text = args.get('text')
            if text:
                self.queueNotice(text, args.get('interrupt'))
        if command == Commands.PREPARE_TO_SAY:
            # Used to preload text cache when caller anticipates text will be
            # voiced
            if not data:
                return
            args = json.loads(data)
            if not args:
                return
            text = args.get('text')
            if text:
                self.queueNotice(text, interrupt=False, preload_cache=True)
        elif command == Commands.SETTINGS_BACKEND_GUI:
            if 0 == 1: # clz._is_configuring:
                clz._logger.debug("Ignoring Duplicate SETTINGS_BACKEND_GUI")
            else:
                try:
                    clz._is_configuring = True
                    util.runInThread(SettingsGUI.launch,
                                     name=Commands.SETTINGS_BACKEND_GUI)
                except:
                    clz._logger.exception("")
                finally:
                    clz._is_configuring = False

        elif command == Commands.SETTINGS_BACKEND_DIALOG:
            clz._logger.debug("Ignoring SETTINGS_BACKEND_DIALOG")

            # util.runInThread(ConfigUtils.selectBackend,
            #                  name=Commands.SETTINGS_BACKEND_DIALOG)
        elif command == Commands.SETTINGS_PLAYER_DIALOG:
            clz._logger.debug("Ignoring SETTINGS_PLAYER_DIALOG")

            # if not data:
            #     return
            # args = json.loads(data)
            # if not args:
            #     return
            # backend = args.get('backend')

            # backend_id = Settings.get_backend_id()

            # ConfigUtils.selectPlayer(backend_id)
        elif command == Commands.SETTINGS_SETTING_DIALOG:
            clz._logger.debug("Ignoring SETTINGS_DIALOG")
            '''
            if not data:
                return
            backend_id = Settings.get_backend_id()
            args = json.loads(data)
            if args[0] == 'voice':
                voice = args[0]
                ConfigUtils.selectSetting(backend_id, voice)
            elif args[0] == 'language':
                language = args[0]
                ConfigUtils.selectSetting(backend_id, language)
            elif args[0] == 'gender':
                ConfigUtils.selectGenderSetting(backend_id)
            '''
        elif command == Commands.SETTINGS_SETTING_SLIDER:
            clz._logger.debug("Ignoring SETTINGS_SLIDER")
            '''
            if not data:
                return
            args = json.loads(data)
            backend_id = Settings.get_backend_id()
            if args[0] == 'volume':
                ConfigUtils.selectVolumeSetting(backend_id, *args)
            '''
        elif command == Commands.RELOAD_ENGINE:
            clz._logger.debug("Ignoring RELOAD_ENGINE")
            # self.checkBackend()

#        elif command.startswith('keymap.'): #Not using because will import keymapeditor into running service. May need if RunScript is not working as was my spontaneous experience
#            command = command[7:]
#            from lib import keymapeditor
#            util.runInThread(keymapeditor.processCommand,(command,),name='keymap.INSTALL_DEFAULT')

    def reloadSettings(self):
        self.readerOn = not Settings.get_reader_off(False)
        self.speakListCount = Settings.get_speak_list_count(True)
        self.autoItemExtra = False
        if Settings.get_auto_item_extra(False):
            self.autoItemExtra = Settings.get_auto_item_extra_delay(2)

    def onDatabaseScanStarted(self, database):
        module_logger.info(
            'DB SCAN STARTED: {0} - Notifying...'.format(database))
        self.queueNotice('{0}: {1}'
                         .format(database,
                                 Messages.get_msg(Messages.DATABASE_SCAN_STARTED)))

    def onDatabaseUpdated(self, database):
        module_logger.info(
            'DB SCAN UPDATED: {0} - Notifying...'.format(database))
        self.queueNotice('{0}: {1}'
                         .format(database,
                                 Messages.get_msg(Messages.DATABASE_SCAN_STARTED)))

    def onNotification(self, sender, method, data):
        clz = type(self)
        clz._logger.debug('onNotification: sender: {} method: {}'
                           .format(sender, method))
        if not sender == Constants.ADDON_ID:
            return
        # Remove the "Other." prefix
        self.processCommand(method.split('.', 1)[-1], data)
#        module_logger.info('NOTIFY: {0} :: {1} :: {2}'.format(sender,method,data))
#        #xbmc :: VideoLibrary.OnUpdate :: {"item":{"id":1418,"type":"episode"}}

    def queueNotice(self, text, interrupt=False, preload_cache=False):
        self.noticeQueue.put((text, interrupt, preload_cache))

    def clearNoticeQueue(self):
        try:
            while not self.noticeQueue.empty():
                self.noticeQueue.get()
                self.noticeQueue.task_done()
        except queue.Empty:
            return

    def checkNoticeQueue(self):
        if self.noticeQueue.empty():
            return False
        while not self.noticeQueue.empty():
            text, interrupt, preload_cache = self.noticeQueue.get()
            self.sayText(text, interrupt, preload_cache)
            self.noticeQueue.task_done()
        return True

    def initState(self):
        if xbmc.Monitor().abortRequested() or self.stop:
            return
        self.winID = None
        self.windowReader = None
        self.controlID = None
        self.text = None
        self.textCompare = None
        self.secondaryText = None
        self.keyboardText = ''
        self.progressPercent = ''
        self.lastProgressPercentUnixtime = 0
        self.interval = 400
        self.listIndex = None
        self.waitingToReadItemExtra = None
        self.reloadSettings()

    def initTTS(self, backend_id: str = None):
        clz = type(self)
        if backend_id is None:
            backend_id = Settings.get_backend_id()
        else:
            Settings.set_backend_id(backend_id)
        new_active_backend = BackendInfoBridge.getBackend(backend_id)
        if (self.get_active_backend() is not None
                and self.get_active_backend().get_backend_id == backend_id):
            return

        backend_id = self.set_active_backend(new_active_backend)
        self.updateInterval()  # Poll interval
        clz._logger.info(f'New active backend: {backend_id}')

    def fallbackTTS(self, reason=None):
        if reason == Commands.RESET:
            return resetAddon()
        backend: Type[ITTSBackendBase | None] = BackendInfoBridge.getBackendFallback()
        module_logger.info(f'Backend falling back to: {backend.get_backend_id()}')
        self.initTTS(backend.get_backend_id())
        self.sayText(Messages.get_msg(Messages.SPEECH_ENGINE_FALLING_BACK_TO)
                     .format(backend.displayName), interrupt=True)
        if reason:
            self.sayText('{0}: {1}'.format(
                Messages.get_msg(Messages.Reason), reason), interrupt=False)

    def firstRun(self):
        from utils import keymapeditor
        module_logger.info('FIRST RUN')
        module_logger.info('Installing default keymap')
        keymapeditor.installDefaultKeymap(quiet=True)

    def start(self):
        clz = type(self)
        self.initTTS()
        monitor = xbmc.Monitor()
        try:
            while (not monitor.abortRequested()) and (not self.stop):
                # Interface reader mode
                while self.readerOn and (not monitor.abortRequested()) and (not self.stop):
                    xbmc.sleep(self.interval)
                    try:
                        self.checkForText()
                    except RuntimeError:
                        module_logger.error('start()', hide_tb=True)
                    except SystemExit:
                        module_logger.info('SystemExit: Quitting')
                        break
                    except TTSClosedException:
                        module_logger.info('TTSCLOSED')
                    except:  # Because we don't want to kill speech on an error
                        clz._logger.exception("")
                        self.initState()  # To help keep errors from repeating on the loop

                # Idle mode
                while (not self.readerOn) and (not monitor.abortRequested()) and (not self.stop):
                    try:
                        text, interrupt = self.noticeQueue.get_nowait()
                        self.sayText(text, interrupt)
                        self.noticeQueue.task_done()
                    except queue.Empty:
                        pass
                    except RuntimeError:
                        module_logger.error('start()', hide_tb=True)
                    except SystemExit:
                        module_logger.info('SystemExit: Quitting')
                        break
                    except TTSClosedException:
                        module_logger.info('TTSCLOSED')
                    except:  # Because we don't want to kill speech on an error
                        module_logger.error('start()', notify=True)
                        self.initState()  # To help keep errors from repeating on the loop
                    for x in range(5):  # Check the queue every 100ms, check state every 500ms
                        if self.noticeQueue.empty():
                            xbmc.sleep(100)
        finally:
            self.close_tts()
            self.end()
            utils.playSound('off')
            module_logger.info('SERVICE STOPPED')
            if self.disable:
                enabler.disableAddon()

    def end(self):
        if module_logger.isEnabledFor(DEBUG):
            xbmc.sleep(500)  # Give threads a chance to finish
            import threading
            module_logger.info('Remaining Threads:')
            for t in threading.enumerate():
                module_logger.debug('  {0}'.format(t.name))

    def shutdown(self):
        self.stop = True
        self.disable = True

    def updateInterval(self):
        if Settings.getSetting(Settings.OVERRIDE_POLL_INTERVAL, backend_id=None,
                               default_value=False):
            self.interval = Settings.getSetting(
                Settings.POLL_INTERVAL, backend_id=None, default_value=self.tts.interval)
        else:
            self.interval = self.tts.interval

    def get_active_backend(self) -> ITTSBackendBase:
        return self.active_backend

    def set_active_backend(self, backend: ITTSBackendBase) -> str:
        if isinstance(backend, str):
            module_logger._logger.debug(f'backend is string: {backend}')
        if self.active_backend:
            self.close_tts()
        self.active_backend = backend
        return backend.get_backend_id()

    def checkBackend(self) -> None:
        backend_id = Settings.get_backend_id()
        if (self.active_backend is not None
                and backend_id == self.active_backend.get_backend_id()):
            return
        self.initTTS()

    def checkForText(self):
        self.checkAutoRead()
        newN = self.checkNoticeQueue()
        newW = self.checkWindow(newN)
        newC = self.checkControl(newW)
        newD = newC and self.checkControlDescription(newW) or False
        text, compare = self.windowReader.getControlText(self.controlID)
        secondary = self.windowReader.getSecondaryText()
        if (compare != self.textCompare) or newC:
            self.newText(compare, text, newD, secondary)
        elif secondary != self.secondaryText:
            self.newSecondaryText(secondary)
        else:
            self.checkMonitored()

    def checkMonitored(self):
        monitored = None

        if self.playerStatus.visible():
            monitored = self.playerStatus.getMonitoredText(
                self.tts.isSpeaking())
        if self.bgProgress.visible():
            monitored = self.bgProgress.getMonitoredText(self.tts.isSpeaking())
        if self.noticeDialog.visible():
            monitored = self.noticeDialog.getMonitoredText(
                self.tts.isSpeaking())
        if not monitored:
            monitored = self.windowReader.getMonitoredText(
                self.tts.isSpeaking())
        if monitored:
            if isinstance(monitored, str):
                self.sayText(monitored, interrupt=True)
            else:
                self.sayTexts(monitored, interrupt=True)

    def checkAutoRead(self):
        if not self.waitingToReadItemExtra:
            return
        if self.tts.isSpeaking():
            self.waitingToReadItemExtra = time.time()
            return
        if time.time() - self.waitingToReadItemExtra > self.autoItemExtra:
            self.waitingToReadItemExtra = None
            self.sayItemExtra(interrupt=False)

    def repeatText(self):
        self.winID = None
        self.controlID = None
        self.text = None
        self.checkForText()

    def sayExtra(self):
        texts = self.windowReader.getWindowExtraTexts()
        self.sayTexts(texts)

    def sayItemExtra(self, interrupt=True):
        texts = self.windowReader.getItemExtraTexts(self.controlID)
        self.sayTexts(texts, interrupt=interrupt)

    def sayText(self, text, interrupt=False, preload_cache=False):
        if self.tts.dead:
            return self.fallbackTTS(self.tts.deadReason)
        module_logger.debug_verbose(repr(text))
        self.tts.say(self.cleanText(text), interrupt, preload_cache)

    def sayTexts(self, texts, interrupt=True):
        if not texts:
            return
        if self.tts.dead:
            return self.fallbackTTS(self.tts.deadReason)
        module_logger.debug_verbose(repr(texts))
        self.tts.sayList(self.cleanText(texts), interrupt=interrupt)

    def insertPause(self, ms=500):
        self.tts.insertPause(ms=ms)

    def volumeUp(self):
        msg = self.tts.volumeUp()
        if not msg:
            return
        self.sayText(msg, interrupt=True)

    def volumeDown(self):
        msg = self.tts.volumeDown()
        if not msg:
            return
        self.sayText(msg, interrupt=True)

    def stopSpeech(self):
        self.tts._stop()

    def updateWindowReader(self):
        readerClass = windows.getWindowReader(self.winID)
        if self.windowReader:
            self.windowReader.close()
            if readerClass.ID == self.windowReader.ID:
                self.windowReader._reset(self.winID)
                return
        self.windowReader = readerClass(self.winID, self)

    def window(self):
        return xbmcgui.Window(self.winID)

    def checkWindow(self, newN):
        winID = xbmcgui.getCurrentWindowId()
        dialogID = xbmcgui.getCurrentWindowDialogId()
        if dialogID != 9999:
            winID = dialogID
        if winID == self.winID:
            return newN
        self.winID = winID
        self.updateWindowReader()
        if module_logger.isEnabledFor(DEBUG):
            module_logger.debug('Window ID: {0} Handler: {1} File: {2}'.format(
                winID, self.windowReader.ID, xbmc.getInfoLabel('Window.Property(xmlfile)')))

        name = self.windowReader.getName()
        if name:
            self.sayText('{0}: {1}'.format(Messages.get_msg(Messages.WINDOW), name),
                         interrupt=not newN)
            self.insertPause()
        else:
            self.sayText(' ', interrupt=not newN)

        heading = self.windowReader.getHeading()
        if heading:
            self.sayText(heading)
            self.insertPause()

        texts = self.windowReader.getWindowTexts()
        if texts:
            self.insertPause()
            for t in texts:
                self.sayText(t)
                self.insertPause()
        return True

    def checkControl(self, newW):
        if not self.winID:
            return newW
        controlID = self.window().getFocusId()
        if controlID == self.controlID:
            return newW
        if module_logger.isEnabledFor(DEBUG):
            module_logger.debug('Control: %s' % controlID)
        self.controlID = controlID
        if not controlID:
            return newW
        return True

    def checkControlDescription(self, newW):
        post = self.windowReader.getControlPostfix(self.controlID)
        description = self.windowReader.getControlDescription(
            self.controlID) or ''
        if description or post:
            self.sayText(description + post, interrupt=not newW)
            self.tts.insertPause()
            return True
        return newW

    def newText(self, compare, text, newD, secondary=None):
        self.textCompare = compare
        label2 = xbmc.getInfoLabel(
            'Container({0}).ListItem.Label2'.format(self.controlID))
        seasEp = xbmc.getInfoLabel(
            'Container({0}).ListItem.Property(SeasonEpisode)'.format(self.controlID)) or ''
        if label2 and seasEp:
            text = '{0}: {1}: {2} '.format(
                label2, text, self.formatSeasonEp(seasEp))
        if secondary:
            self.secondaryText = secondary
            text += self.tts.pauseInsert + ' ' + secondary
        self.sayText(text, interrupt=not newD)
        if self.autoItemExtra:
            self.waitingToReadItemExtra = time.time()

    def newSecondaryText(self, text):
        self.secondaryText = text
        if not text:
            return
        if text.endswith('%'):
            # Get just the percent part, so we don't keep saying downloading
            text = text.rsplit(' ', 1)[-1]
        if not self.tts.isSpeaking():
            self.sayText(text, interrupt=True)

    def formatSeasonEp(self, seasEp):
        if not seasEp:
            return ''
        return seasEp.replace('S', '{0} '
                              .format(Messages.get_msg(Messages.SEASON)))\
            .replace('E', '{0} '.format(Messages.get_msg(Messages.EPISODE)))

    _formatTagRE = re.compile(r'\[/?(?:CR|B|I|UPPERCASE|LOWERCASE)\](?i)')
    _colorTagRE = re.compile(r'\[/?COLOR[^\]\[]*?\](?i)')
    _okTagRE = re.compile(r'(^|\W|\s)OK($|\s|\W)')  # Prevents saying Oklahoma

    def _cleanText(self, text):
        text = self._formatTagRE.sub('', text)
        text = self._colorTagRE.sub('', text)
        # Some speech engines say OK as Oklahoma
        text = self._okTagRE.sub(r'\1O K\2', text)
        # getLabel() on lists wrapped in [] and some speech engines have
        # problems with text starting with -
        text = text.strip('-[]')
        text = text.replace('XBMC', 'Kodi')
        if text == '..':
            text = Messages.get_msg(Messages.PARENT_DIRECTORY)
        return text

    def cleanText(self, text):
        if isinstance(text, str):
            return self._cleanText(text)
        else:
            return [self._cleanText(t) for t in text]


def preInstalledFirstRun():
    if not SystemQueries.isPreInstalled():  # Do as little as possible if there is no pre-install
        if SystemQueries.wasPreInstalled():
            module_logger.info('PRE INSTALL: REMOVED')
            # Set version to 0.0.0 so normal first run will execute and fix the
            # keymap
            Settings.setSetting(Settings.VERSION, '0.0.0', None)
            enabler.markPreOrPost()  # Update the install status
        return False

    lastVersion = Settings.getSetting(Settings.VERSION, None)

    if not enabler.isPostInstalled() and SystemQueries.wasPostInstalled():
        module_logger.info('POST INSTALL: UN-INSTALLED OR REMOVED')
        # Add-on was removed. Assume un-installed and treat this as a
        # pre-installed first run to disable the addon
    elif lastVersion:
        enabler.markPreOrPost()  # Update the install status
        return False

    # Set version to 0.0.0 so normal first run will execute on first enable
    Settings.setSetting(Settings.VERSION, '0.0.0', None)

    module_logger.info('PRE-INSTALLED FIRST RUN')
    module_logger.info('Installing basic keymap')

    # Install keymap with just F12 enabling included
    from utils import keymapeditor
    keymapeditor.installBasicKeymap()

    module_logger.info('Pre-installed - DISABLING')

    enabler.disableAddon()
    return True


def startService():
    if preInstalledFirstRun():
        return

    TTSService().start()
    xbmc.log('service.startService thread started', xbmc.LOGDEBUG)


if __name__ == '__main__':
    import threading
    threading.current_thread().name = "service.py"

    module_logger.debug('service.py service.kodi.tts service thread starting')
    startService()
