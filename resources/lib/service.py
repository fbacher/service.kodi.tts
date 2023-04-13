# -*- coding: utf-8 -*-
#

from utils import util
import enabler
from common import utils
from common.system_queries import SystemQueries
from common.settings import Settings
from common.configuration_utils import ConfigUtils
from common.constants import Constants
from common.messages import Messages
from common.logger import LazyLogger
from common.exceptions import AbortException
from windowNavigation.custom_settings_ui import SettingsGUI
from windows import playerstatus, notice, backgroundprogress
import windows
from backends import audio, TTSBackendBase
import backends
from utils import addoninfo
import xbmcgui
from typing import ClassVar, Type
import os
import json
import queue
import time
import re
import sys
import xbmc
import io
import signal
import faulthandler
from time import sleep
from common.python_debugger import PythonDebugger

REMOTE_DEBUG: bool = True

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
    xbmc.log('About to PythonDebugger.enable from tts service', xbmc.LOGINFO)
    PythonDebugger.enable('kodi.tts')
    sleep(1)
try:
    pass
    # import web_pdb;

    # web_pdb.set_trace()
except Exception as e:
    pass


# TODO Remove after eliminating util.getCommand


module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)

__version__ = Constants.VERSION
module_logger.info(__version__)
module_logger.info('Platform: {0}'.format(sys.platform))

if audio.PLAYSFX_HAS_USECACHED:
    module_logger.info('playSFX() has useCached')
else:
    module_logger.info('playSFX() does NOT have useCached')

# util.initCommands()
addoninfo.initAddonsData()

RESET = False


def resetAddon():
    global RESET
    if RESET:
        return
    RESET = True
    module_logger.info('Resetting addon...')
    xbmc.executebuiltin(
        'RunScript(special://home/addons/service.kodi.tts/resources/lib/tools/enabler.py,RESET)')


class TTSClosedException(Exception):
    pass


class TTSService(xbmc.Monitor):
    instance = None

    def __init__(self):
        self._logger = module_logger.getChild(
            self.__class__.__name__)  # type: LazyLogger
        super().__init__()  # Appears to not do anything
        self.readerOn = True
        self.stop: bool = False
        self.disable: bool = False
        self.noticeQueue: queue.Queue = queue.Queue()
        self.initState()
        self._tts: Type[TTSBackendBase] = None
        self.backendProvider = None
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
        self.initTTS()
        module_logger.info(
            'SERVICE STARTED :: Interval: %sms' % self.tts.interval)
        TTSService.instance = self

    @staticmethod
    def get_instance():  # type: () -> TTSService
        return TTSService.instance

    def onAbortRequested(self):
        self.stop = True
        try:
            self._tts._close()
        except TTSClosedException:
            pass

    @property
    def tts(self):
        if self._tts._closed:
            raise TTSClosedException()
        return self._tts

    def onSettingsChanged(self):
        try:
            self.tts._update()
        except TTSClosedException:
            return
        self.checkBackend()
        self.reloadSettings()
        self.updateInterval()
        # Deprecated for the addon starting with Gotham - now using NotifyAll
        # (Still used for SHUTDOWN until I figure out the issue when using
        # NotifyAll with that)
        command = util.getCommand()
        if not command:
            return
        self.processCommand(command)

    def processCommand(self, command, data=None):
        from utils import util  # Earlier import apparently not seen when called via NotifyAll
        self._logger.debug(f'command: {command} toggle_on: {self.toggle_on}')
        if command == 'TOGGLE_ON_OFF':
            if self.toggle_on:
                self.toggle_on = False
                utils.playSound('off')
            else:
                self.toggle_on = True
                utils.playSound('on')
        if not self.toggle_on:
            return
        elif command == 'RESET':
            pass
        elif command == 'REPEAT':
            self.repeatText()
        elif command == 'EXTRA':
            self.sayExtra()
        elif command == 'ITEM_EXTRA':
            self.sayItemExtra()
        elif command == 'VOL_UP':
            self.volumeUp()
        elif command == 'VOL_DOWN':
            self.volumeDown()
        elif command == 'STOP':
            self.stopSpeech()
        elif command == 'SHUTDOWN':
            self.shutdown()
        elif command == 'SAY':
            if not data:
                return
            args = json.loads(data)
            if not args:
                return
            text = args.get('text')
            if text:
                self.queueNotice(text, args.get('interrupt'))
        if command == 'PREPARE_TO_SAY':
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
        elif command == 'SETTINGS.BACKEND_GUI':
            util.runInThread(SettingsGUI.launch,
                             name='SETTINGS.BACKEND_GUI')
        elif command == 'SETTINGS.BACKEND_DIALOG':
            util.runInThread(ConfigUtils.selectBackend,
                             name='SETTINGS.BACKEND_DIALOG')
        elif command == 'SETTINGS.PLAYER_DIALOG':
            # if not data:
            #     return
            # args = json.loads(data)
            # if not args:
            #     return
            # backend = args.get('backend')

            provider = Settings.getSetting('backend')

            ConfigUtils.selectPlayer(provider)
        elif command == 'SETTINGS.SETTING_DIALOG':
            if not data:
                return
            provider = Settings.getSetting('backend')
            args = json.loads(data)
            if args[0] == 'voice':
                voice = args[0]
                ConfigUtils.selectSetting(provider, voice)
            elif args[0] == 'language':
                language = args[0]
                ConfigUtils.selectSetting(provider, language)
            elif args[0] == 'gender':
                ConfigUtils.selectGenderSetting(provider)
        elif command == 'SETTINGS.SETTING_SLIDER':
            if not data:
                return
            args = json.loads(data)
            provider = Settings.getSetting('backend')
            if args[0] == 'volume':
                ConfigUtils.selectVolumeSetting(provider, *args)

        elif command == 'RELOAD_ENGINE':
            self.checkBackend()

#        elif command.startswith('keymap.'): #Not using because will import keymapeditor into running service. May need if RunScript is not working as was my spontaneous experience
#            command = command[7:]
#            from lib import keymapeditor
#            util.runInThread(keymapeditor.processCommand,(command,),name='keymap.INSTALL_DEFAULT')

    def reloadSettings(self):
        self.readerOn = not Settings.getSetting(Settings.READER_OFF, False)
        # OldLogger.reload()
        self.speakListCount = Settings.getSetting(Settings.SPEAK_LIST_COUNT,
                                                  True)
        self.autoItemExtra = False
        if Settings.getSetting(Settings.AUTO_ITEM_EXTRA, False):
            self.autoItemExtra = Settings.getSetting(
                Settings.AUTO_ITEM_EXTRA_DELAY, 2)

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
        self._logger.debug('onNotification: sender: {} method: {}'
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

    def initTTS(self, backendClass: Type[TTSBackendBase] = None,
                changed: bool = False):
        if not backendClass:
            backendClass = backends.getBackend()
        provider = self.setBackend(backendClass())
        self.backendProvider = provider
        self.updateInterval()
        module_logger.info('Backend: %s' % provider)

    def fallbackTTS(self, reason=None):
        if reason == 'RESET':
            return resetAddon()
        backend: Type[TTSBackendBase] = backends.getBackendFallback()
        module_logger.info(
            'Backend falling back to: {0}'.format(backend.provider))
        self.initTTS(backend)
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
                        module_logger.error('start()', notify=True)
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
            self._tts._close()
            self.end()
            utils.playSound('off')
            module_logger.info('SERVICE STOPPED')
            if self.disable:
                enabler.disableAddon()

    def end(self):
        if module_logger.isEnabledFor(LazyLogger.DEBUG):
            xbmc.sleep(500)  # Give threads a chance to finish
            import threading
            module_logger.info('Remaining Threads:')
            for t in threading.enumerate():
                module_logger.debug('  {0}'.format(t.name))

    def shutdown(self):
        self.stop = True
        self.disable = True

    def updateInterval(self):
        if Settings.getSetting(Settings.OVERRIDE_POLL_INTERVAL, False):
            self.interval = Settings.getSetting(
                Settings.POLL_INTERVAL, self.tts.interval)
        else:
            self.interval = self.tts.interval

    def setBackend(self, backend: Type[TTSBackendBase]):
        if self._tts:
            self._tts._close()
        self._tts = backend
        return backend.provider

    def checkBackend(self):
        provider = Settings.getSetting('backend', None)
        if provider == self.backendProvider:
            return
        self.initTTS(changed=True)

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
        if module_logger.isEnabledFor(LazyLogger.DEBUG):
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
        if module_logger.isEnabledFor(LazyLogger.DEBUG):
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
            Settings.setSetting('version', '0.0.0')
            enabler.markPreOrPost()  # Update the install status
        return False

    lastVersion = Settings.getSetting('version')

    if not enabler.isPostInstalled() and SystemQueries.wasPostInstalled():
        module_logger.info('POST INSTALL: UN-INSTALLED OR REMOVED')
        # Add-on was removed. Assume un-installed and treat this as a
        # pre-installed first run to disable the addon
    elif lastVersion:
        enabler.markPreOrPost()  # Update the install status
        return False

    # Set version to 0.0.0 so normal first run will execute on first enable
    Settings.setSetting('version', '0.0.0')

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
    startService()
