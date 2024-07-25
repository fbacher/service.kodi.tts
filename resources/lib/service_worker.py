# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import datetime
import sys

import xbmc

from common import *

from cache.prefetch_movie_data.seed_cache import SeedCache
from common.critical_settings import CriticalSettings
from common.exceptions import ExpiredException
from common.globals import Globals
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.phrases import Phrase, PhraseList
from utils.util import runInThread
from windows.notice import NoticeDialog
from windows.ui_constants import UIConstants
from windows.window_state_monitor import WinDialog, WinDialogState, WindowStateMonitor

module_logger = BasicLogger.get_module_logger(module_path=__file__)

# TODO Remove after eliminating util.getCommand

import re
import time
import queue
import json
import xbmcgui

from backends.background_driver import BackgroundDriver
from backends.driver import Driver
from backends.settings.base_service_settings import BaseServiceSettings
from common.base_services import BaseServices
from common.debug import Debug

from utils import addoninfo
from backends import audio
from common.monitor import Monitor
from common.settings import Settings
from backends.backend_info_bridge import BackendInfoBridge
from backends.i_tts_backend_base import ITTSBackendBase
from backends.backend_info import BackendInfo
from backends.settings.setting_properties import SettingsProperties

import windows
from windows import (playerstatus, backgroundprogress,
                     WindowReaderBase)
from windowNavigation.custom_settings_ui import SettingsGUI
from common.messages import Messages
from common.constants import Constants
from common import utils
import enabler

__version__ = Constants.VERSION

module_logger.info(__version__)
module_logger.info('Platform: {0}'.format(sys.platform))

if audio.PLAYSFX_HAS_USECACHED:
    module_logger.info('playSFX() has useCached')
else:
    module_logger.info('playSFX() does NOT have useCached')

# util.initCommands()
BaseServiceSettings()
addoninfo.initAddonsData()

BackendInfo.init()
# BootstrapEngines.init()

DO_RESET = False


def resetAddon():
    global DO_RESET
    if DO_RESET:
        return
    DO_RESET = True
    module_logger.info('Resetting addon...')
    xbmc.executebuiltin(
            'RunScript(special://home/addons/service.kodi.tts/resources/lib/tools'
            '/enabler.py,RESET)')


class TTSClosedException(Exception):
    pass


class Commands:
    DUMP_THREADS: Final[str] = 'DUMP_THREADS'
    TOGGLE_ON_OFF: Final[str] = 'TOGGLE_ON_OFF'
    CYCLE_DEBUG: Final[str] = 'CYCLE_DEBUG'
    VOICE_HINT: Final[str] = 'VOICE_HINT'
    HELP: Final[str] = 'HELP'
    INTRODUCTION: Final[str] = 'INTRODUCTION'
    HELP_CONFIG: Final[str] = 'HELP_CONFIG'
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
    #  SETTINGS_BACKEND_DIALOG: Final[str] = 'SETTINGS.BACKEND_DIALOG'
    #  SETTINGS_PLAYER_DIALOG: Final[str] = 'SETTINGS.PLAYER_DIALOG'
    #  SETTINGS_SETTING_DIALOG: Final[str] = 'SETTINGS.SETTING_DIALOG'
    #  SETTINGS_SETTING_SLIDER: Final[str] = 'SETTINGS.SETTING_SLIDER'


class TTSService:
    autoItemExtra: int = 0
    instance_count: int = 0
    instance: ForwardRef('TTSService') = None
    _is_configuring: bool = False
    _logger: BasicLogger = None
    msg_timestamp: datetime.datetime = None
    _initialized: bool = False
    speakListCount = None
    readerOn: bool = True
    stop: bool = False
    disable: bool = False
    noticeQueue: queue.Queue[PhraseList] = queue.Queue(20)
    noticeQueueCount: int = 0
    noticeQueueFullCount: int = 0
    active_backend: ITTSBackendBase | None = None
    toggle_on: bool = True
    playerStatus = playerstatus.PlayerStatus(10115).init()
    bgProgress = backgroundprogress.BackgroundProgress(10151).init()
    noticeDialog: NoticeDialog = NoticeDialog(10107).init()
    winID = None
    dialogID = None
    windowReader: WindowReaderBase | None = None
    current_control_id = None
    _previous_primary_text: str | None = None
    _previous_secondary_text: str = ''
    keyboardText = ''
    progressPercent = ''
    lastProgressPercentUnixtime = 0
    interval: int = 200
    listIndex = None
    waitingToReadItemExtra = None
    driver: Driver = None
    background_driver: BackgroundDriver = None
    background_driver_instance: BackgroundDriver = None

    def __init__(self):
        clz = type(self)
        super().__init__()  # Appears to not do anything
        if not clz._initialized:
            clz._initialized = True
            clz.instance = self
            clz.init()

    @classmethod
    def init(cls):
        cls.instance_count += 1
        cls.speakListCount = None
        cls._logger = module_logger.getChild(cls.__class__.__class__.__name__)
        cls.readerOn: bool = True
        cls.stop: bool = False
        cls.disable: bool = False
        del cls.noticeQueue
        cls.noticeQueue: queue.Queue = queue.Queue(20)
        cls.noticeQueueFullCount: int = 0
        cls.noticeQueueCount: int = 0
        cls.initState()
        cls.active_backend: ITTSBackendBase | None = None
        cls.toggle_on: bool = True
        utils.stopSounds()  # To kill sounds we may have started before an update
        utils.playSound('on')
        cls.playerStatus = playerstatus.PlayerStatus(10115).init()
        cls.bgProgress = backgroundprogress.BackgroundProgress(10151).init()
        cls.noticeDialog = NoticeDialog(10107).init()
        cls.winID = None
        cls.windowReader = None
        cls.current_control_id = None
        cls._previous_primary_text = None
        cls._previous_secondary_text = ''
        cls.keyboardText = ''
        cls.progressPercent = ''
        cls.lastProgressPercentUnixtime = 0
        cls.interval = 200
        cls.listIndex = None
        cls.waitingToReadItemExtra = None
        cls.driver: Driver = None
        # Monitor.register_settings_changed_listener(TTSService.onSettingsChanged,
        #                                            'tts_service changed')
        # Monitor.register_abort_listener(TTSService.onAbortRequested,
        #                                            'tts_service aborting')

        # module_logger.info(f'SERVICE STARTED :: Interval: {cls.get_tts().interval}')
        # cls._logger.info(f'TTSService.init instance_count: {cls.instance_count}')
        # Debug.dump_all_threads()

    @classmethod
    def interval_ms(cls):
        return cls.interval / 1000.0

    @staticmethod
    def get_instance() -> 'TTSService':
        return TTSService.instance

    @classmethod
    def onAbortRequested(cls):
        cls.stop = True
        try:
            xbmc.log('Received AbortRequested', xbmc.LOGINFO)
            cls.close_tts()
        except TTSClosedException:
            pass

    @property
    def tts(self) -> ITTSBackendBase:
        clz = type(self)
        if clz.is_tts_closed():
            raise TTSClosedException()
        return clz.active_backend

    @classmethod
    def get_tts(cls) -> ITTSBackendBase:
        if cls.is_tts_closed():
            raise TTSClosedException()
        return cls.active_backend

    '''
    def tts_getter(self) ->ITTSBackendBase:
        clz = type(self)
        if clz.is_tts_closed():
            raise TTSClosedException()
        return clz.active_backend
    '''

    @classmethod
    def close_tts(cls) -> None:
        if cls.active_backend is not None:
            cls.active_backend.close()
        else:
            pass

    @classmethod
    def is_tts_closed(cls) -> bool:
        if cls.active_backend is not None:
            return cls.active_backend._closed
        else:
            return True

    @classmethod
    def processCommand(cls, command, data=None):
        from utils import util
        cls._logger.debug(f'command: {command} toggle_on: {cls.toggle_on}')
        if command == Commands.TOGGLE_ON_OFF:
            if cls.toggle_on:
                cls.toggle_on = False
                utils.playSound('off')
            else:
                cls.toggle_on = True
                utils.playSound('on')
        if not cls.toggle_on:
            return
        elif command == Commands.RESET:
            pass
        elif command == Commands.REPEAT:
            cls.repeatText()
        elif command == Commands.EXTRA:
            cls.sayExtra()
        elif command == Commands.ITEM_EXTRA:  # What is this?
            cls.sayItemExtra()
        elif command == Commands.VOL_UP:
            cls.volumeUp()
        elif command == Commands.VOL_DOWN:
            cls.volumeDown()
        elif command == Commands.STOP:
            cls.stopSpeech()
        elif command == Commands.SHUTDOWN:
            cls.shutdown()
        elif command == Commands.CYCLE_DEBUG:
            cls.cycle_debug()
        elif command == Commands.VOICE_HINT:
            cls.voice_hint()
        elif command == Commands.HELP:
            cls.help()
        elif command == Commands.INTRODUCTION:
            cls.introduction()
        elif command == Commands.HELP_CONFIG:
            cls.help_config()
        elif command == Commands.SAY:
            if not data:
                return

            # It is important to create PhraseList before
            # creating it's phrases, otherwise serial #s will be
            # incorrect

            phrases: PhraseList = PhraseList()
            phrase_args: Dict[str, List[Phrase]]
            phrase_args = json.loads(data, object_hook=Phrase.from_json)
            if not phrase_args:
                return
            try:
                phrase: Phrase
                for phrase in phrase_args.get('phrases'):
                    phrases.append(phrase)
                cls.queueNotice(phrases)
            except ExpiredException:
                cls._logger.debug(f'incoming phrases expired on arrival')
                pass
        elif command == Commands.DUMP_THREADS:
            Debug.dump_all_threads()
        elif command == Commands.PREPARE_TO_SAY:
            # Used to preload text cache when caller anticipates text will be
            # voiced
            if not data:
                return
            str_args: Dict[str, str | List[str]] = json.loads(data)
            if not str_args:
                return
            if not str_args.get('text'):
                return
            try:
                phrases: PhraseList = PhraseList.create(str_args.get('text'),
                                                        interrupt=False,
                                                        preload_cache=True)
                cls.queueNotice(phrases)
            except AbortException:
                reraise(*sys.exc_info())
            except ExpiredException:
                cls._logger.debug(f'incoming text expired on arrival')
        elif command == Commands.SETTINGS_BACKEND_GUI:
            if cls._is_configuring:
                if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                    cls._logger.debug_verbose("Ignoring Duplicate SETTINGS_BACKEND_GUI")
            else:
                try:
                    cls._is_configuring = True
                    cls._logger.debug('Starting Backend_GUI')
                    util.runInThread(SettingsGUI.launch,
                                     name=Commands.SETTINGS_BACKEND_GUI)
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception:
                    cls._logger.exception("")
                finally:
                    cls._is_configuring = False

            # if not data:
            #     return
            # args = json.loads(data)
            # if not args:
            #     return
            # backend = args.get('backend')

            # backend_id = Settings.get_engine_id()

            # ConfigUtils.selectPlayer(backend_id)

        elif command == Commands.RELOAD_ENGINE:
            # cls._logger.debug("Ignoring RELOAD_ENGINE")
            cls.checkBackend()

    @classmethod
    def reloadSettings(cls):
        cls.readerOn = Settings.get_reader_on(True)
        cls._logger.debug(f'readerOn: {cls.readerOn}')
        cls.speakListCount = Settings.get_speak_list_count(True)
        cls.autoItemExtra = 0

        # if Settings.get_auto_item_extra(False):
        #     cls.autoItemExtra = Settings.get_auto_item_extra_delay(2)

    @classmethod
    def voice_hint(cls):
        """
        Toggle voicing hint-info for voiced controls.

        :return:
        """
        Globals.voice_hint = not Globals.voice_hint

    @classmethod
    def help(cls):
        pass

    @classmethod
    def introduction(cls):
        pass

    @classmethod
    def help_config(cls):
        pass

    '''
    @classmethod
    def onDatabaseScanStarted(cls, database):
        module_logger.info(
                'DB SCAN STARTED: {0} - Notifying...'.format(database))
        cls.queueNotice('{0}: {1}'
                        .format(database,
                                Messages.get_msg(Messages.DATABASE_SCAN_STARTED)))

    @classmethod
    def onDatabaseUpdated(cls, database):
        module_logger.info(
                'DB SCAN UPDATED: {0} - Notifying...'.format(database))
        cls.queueNotice('{0}: {1}'
                        .format(database,
                                Messages.get_msg(Messages.DATABASE_SCAN_STARTED)))
    '''

    @classmethod
    def onNotification(cls, **kwargs):
        kwargs.setdefault('sender', 'invalid')
        kwargs.setdefault('method', 'invalid')
        kwargs.setdefault('data', 'invalid')
        sender: str = kwargs['sender']
        method: str = kwargs['method']
        data: str = kwargs['data']
        try:
            if sender != Constants.ADDON_ID:
                return
            # Remove the "Other." prefix
            cls.processCommand(method.split('.', 1)[-1], data)
        except AbortException:
            pass  # run in separate thread that is going to exit
        except Exception as e:
            cls._logger.exception('')

    @classmethod
    def queueNotice(cls, phrases: PhraseList):
        try:
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug_verbose(f'phrases: {len(phrases)} phrase: {phrases[0]}')
            if phrases[0].get_interrupt():
                if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                    cls._logger.debug_verbose(f'INTERRUPT: clearNoticeQueue')
                cls.clearNoticeQueue()
            while not Monitor.exception_on_abort(timeout=0.01):
                try:
                    cls.noticeQueue.put_nowait(phrases)
                    break
                except queue.Full:
                    cls._logger.debug(f'queueNotice full')
        except ExpiredException:
            cls._logger.debug('Expired msg from queue')

    @classmethod
    def clearNoticeQueue(cls):
        try:
            while not cls.noticeQueue.empty():
                cls.noticeQueue.get()
                cls.noticeQueue.task_done()
        except queue.Empty:
            return

    @classmethod
    def checkNoticeQueue(cls):
        if cls.noticeQueue.empty():
            return False
        while not cls.noticeQueue.empty():
            try:
                phrases: PhraseList
                phrases = cls.noticeQueue.get()
                if phrases.is_expired():
                    continue
                if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    cls._logger.debug_extra_verbose(
                        f'# phrases: {len(phrases)} {phrases}')
                cls.sayText(phrases)
            except ExpiredException:
                cls._logger.debug(f'Expired just before sayText')
            finally:
                cls.noticeQueue.task_done()
        return True

    @classmethod
    def initState(cls):
        if Monitor.is_abort_requested() or cls.stop:
            return
        cls.winID = None
        cls.windowReader = None
        cls.current_control_id = None
        cls._previous_primary_text = None
        cls._previous_secondary_text = ''
        cls.keyboardText = ''
        cls.progressPercent = ''
        cls.lastProgressPercentUnixtime = 0
        cls.interval = 400
        cls.listIndex = None
        cls.waitingToReadItemExtra = None
        cls.reloadSettings()
        cls.background_driver: BackgroundDriver | None = None

    @classmethod
    def initTTS(cls, backend_id: str = None) -> TTSService:
        clz = type(cls)
        if backend_id is None:
            backend_id = Settings.get_engine_id()
            cls._logger.debug(f'backend_id: {backend_id}')
        else:
            Settings.set_backend_id(backend_id)
        new_active_backend = BaseServices.getService(backend_id)
        if (cls.get_active_backend() is not None
                and cls.get_active_backend().backend_id == backend_id):
            return cls.get_instance()

        backend_id = cls.set_active_backend(new_active_backend)
        cls.updateInterval()  # Poll interval
        cls._logger.info(f'New active backend: {backend_id}')
        cls.start_background_driver()
        return cls.get_instance()

    @classmethod
    def fallbackTTS(cls, reason=None):
        if reason == Commands.RESET:
            return resetAddon()
        backend: Type[ITTSBackendBase | None] = BackendInfoBridge.getBackendFallback()
        cls._logger.info(f'Backend falling back to: {backend.backend_id}')
        cls.initTTS(backend.backend_id)
        try:
            phrases: PhraseList = PhraseList()
            phrase: Phrase
            phrase = Phrase(text=Messages.get_msg(Messages.SPEECH_ENGINE_FALLING_BACK_TO)
                            .format(backend.displayName), interrupt=True)
            phrases.append(phrase)
            if reason:
                phrase = Phrase(f'{Messages.get_msg(Messages.Reason)}: {reason}',
                                interrupt=False)
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired just before SayText in FallbackTTS')

    @classmethod
    def firstRun(cls):
        from utils import keymapeditor
        module_logger.info('FIRST RUN')
        module_logger.info('Installing default keymap')
        keymapeditor.installDefaultKeymap(quiet=True)

    @classmethod
    def start(cls):
        cls._logger.debug(f'starting TTSService.start. '
                          f'instance_count: {cls.instance_count}')
        cls.initTTS()
        seed_cache: bool = False  # True
        engine_id: str = cls.get_active_backend().backend_id
        Monitor.register_notification_listener(cls.onNotification,
                                               'service.notify')
        Monitor.register_abort_listener(cls.onAbortRequested)
        if seed_cache and Settings.is_use_cache(engine_id):
            call: callable = SeedCache.discover_movie_info
            runInThread(call, args=[engine_id],
                        name='seed_cache', delay=360)

        WindowStateMonitor.register_window_state_listener(cls.handle_window_changes,
                                                          "main")

    @classmethod
    def handle_window_changes(cls, changed: int) -> bool:
        # cls._logger.debug(f'TTSService initialized. Now waiting for events'
        #                   f'stop: {cls.stop} readerOn: {cls.readerOn}')
        try:
            current_windialog_id: int
            if WinDialogState.current_windialog == WinDialog.WINDOW:
                current_windialog_id = WinDialogState.current_window_id
            else:
                current_windialog_id = WinDialogState.current_dialog_id

            # cls._logger.debug(f'current_windialog_id: {current_windialog_id}')
            # focus_id: str = f'{WinDialogState.current_dialog_focus_id}'
            # if focus_id == '0':  # No control on dialog has focus (Kodi may not have focus)
            #     return False

            if cls.stop:
                pass
            # if cls.readerOn:
            #    try:
            cls.checkForText()
            return True

        except RuntimeError:
            module_logger.exception('start()')
        except SystemExit:
            module_logger.info('SystemExit: Quitting')
        except TTSClosedException:
            module_logger.info('TTSCLOSED')
        except Exception as e:
            # Because we don't want to kill speech on an error
            cls._logger.exception("")
            cls.initState()  # To help keep errors from repeating on the loop

        """
            # Idle mode
            while ((not cls.readerOn) and
                   (not Monitor.exception_on_abort(timeout=cls.interval_ms())) and (
                           not cls.stop)):
                try:
                    phrases: PhraseList = cls.noticeQueue.get_nowait()
                    cls.sayText(phrases)
                    cls.noticeQueue.task_done()
                except AbortException:
                    reraise(*sys.exc_info())
                except queue.Empty:
                    pass
                except RuntimeError:
                    module_logger.error('start()')
                except SystemExit:
                    module_logger.info('SystemExit: Quitting')
                    break
                except TTSClosedException:
                    module_logger.info('TTSCLOSED')
                except:  # Because we don't want to kill speech on an error
                    module_logger.error('start()', notify=True)
                    cls.initState()  # To help keep errors from repeating on the loop
                for x in range(
                        5):  # Check the queue every 100ms, check state every 500ms
                    if cls.noticeQueue.empty():
                        Monitor.wait_for_abort(timeout=0.1)
                break
        

        finally:
            cls.close_tts()
            cls.end()
            utils.playSound('off')
            module_logger.info('SERVICE STOPPED')
            if cls.disable:
                enabler.disableAddon()
        """

    @classmethod
    def end(cls):
        if module_logger.isEnabledFor(DEBUG):
            xbmc.sleep(200)  # Give threads a chance to finish
            import threading
            module_logger.info('Remaining Threads:')
            for t in threading.enumerate():
                module_logger.debug(f'  {t.name}')

    @classmethod
    def shutdown(cls):
        cls.stop = True
        cls.disable = True

    @classmethod
    def updateInterval(cls):
        if Settings.getSetting(SettingsProperties.OVERRIDE_POLL_INTERVAL,
                               service_id=SettingsProperties.TTS_SERVICE,
                               default_value=False):
            engine: ITTSBackendBase = cls.tts
            cls.interval = Settings.getSetting(
                    SettingsProperties.POLL_INTERVAL,
                    service_id=SettingsProperties.TTS_SERVICE,
                    default_value=engine.interval)
        else:
            cls.interval = cls.get_tts().interval

    @classmethod
    def get_active_backend(cls) -> ITTSBackendBase:
        return cls.active_backend

    @classmethod
    def set_active_backend(cls, backend: ITTSBackendBase) -> str:
        if isinstance(backend, str):
            module_logger.debug(f'backend is string: {backend}')
        else:
            backend.init()
            pass
        if cls.active_backend:
            cls.close_tts()

        #  backend.init()
        # module_logger.debug(f'setting active_backend: {str(backend)}')
        # module_logger.debug(f'backend_id: {backend.backend_id}')
        cls.active_backend = backend
        if cls.driver is None:
            cls.driver = Driver()
        return backend.backend_id

    @classmethod
    def start_background_driver(cls) -> None:
        if cls.background_driver_instance is None:
            cls.background_driver_instance = BackgroundDriver()
            cls.background_driver = type(cls.background_driver_instance)

    @classmethod
    def checkBackend(cls) -> None:
        backend_id = Settings.get_engine_id()
        if (cls.active_backend is not None
                and backend_id == cls.active_backend.backend_id):
            return
        cls.initTTS()

    @classmethod
    def is_primary_text_changed(cls, phrases: PhraseList) -> bool:
        # cls._logger.debug(f'phrases: {phrases} empty: {phrases.is_empty()} '
        #                   f'previous_primary_text: {cls._previous_primary_text}')
        if phrases.is_empty():
            return cls._previous_primary_text is None
        #  cls._logger.debug(f'equals: {phrases[0].text_equals(cls._previous_primary_text)}')
        return not phrases[0].text_equals(cls._previous_primary_text)

    @classmethod
    def set_previous_primary_text(cls, phrases: PhraseList) -> None:
        if phrases is not None and not phrases.is_empty():
            cls._previous_primary_text = phrases[0].get_text()
        else:
            cls._previous_primary_text = None

    @classmethod
    def is_secondary_text_changed(cls, phrases: PhraseList) -> bool:
        result: bool
        if phrases.is_empty():
            result = cls._previous_secondary_text != ''
        else:
            result = not phrases[0].text_equals(cls._previous_secondary_text)
        if cls._logger.isEnabledFor(DEBUG_VERBOSE):
            cls._logger.debug_verbose(f'previous_secondary_text:'
                                      f' {cls._previous_secondary_text} '
                                      f'phrases: {phrases} result: {result}')
        return result

    @classmethod
    def set_previous_secondary_text(cls, phrases: PhraseList) -> None:
        if phrases.is_empty():
            cls._previous_secondary_text = ''
        else:
            cls._previous_secondary_text = phrases[0].get_text()

    @classmethod
    def checkForText(cls):
        #  cls._logger.debug(f'In checkForText')
        cls.checkAutoRead()  # Readers seem to flag text that they want read after the
                             # the current reading. Perhaps more cpu required?
                             # Perhaps to give user a chance to skip? Also seems
                             # to be able to be triggered externally.
        newN = cls.checkNoticeQueue()  # Any incoming notifications from cmd line or addon?
        newW = cls.checkWindow(newN)   # Window changed?
        newC = cls.checkControl(newW)  # Control Changed?
        #
        # Read Description of the control, or any other context prior to reading
        # the actual text in any changed control.

        newD = newC and cls.checkControlDescription(newW) or False
        #  cls._logger.debug(f'Calling windowReader')
        phrases: PhraseList = PhraseList()
        success: bool = cls.windowReader.getControlText(cls.current_control_id, phrases)
        if not success or phrases.is_empty():
            compare = ''
        else:
            cls._logger.debug(f'CHECK getControlText: {phrases}'
                              f' reader: {cls.windowReader.__class__.__name__}')
            compare: str = phrases[0].get_text()
        # Secondary text is typically some detail (like progress status) that
        # is not related to the focused text. Therefore, you don't want it to
        # mess with the history of the primary text, causing it to be
        # unnecessarily re-voiced.

        secondary: PhraseList = PhraseList()
        success = cls.windowReader.getSecondaryText(secondary)
        if not cls.is_secondary_text_changed(secondary):
            if not secondary.is_empty():
                cls._logger.debug(f'CHECK: secondaryText {secondary} not changed '
                                  f'reader: {cls.windowReader.__class__.__name__}')
            secondary.clear()

        if cls._logger.isEnabledFor(DEBUG_VERBOSE):
            if not phrases.is_empty() or compare != '' or len(secondary) > 0:
                cls._logger.debug_verbose(f'control_id: {cls.current_control_id} '
                                          f'phrases: {phrases} '
                                          f'compare: {compare} secondary: {secondary} '
                                          f'previous_secondaryText: '
                                          f'{cls._previous_secondary_text}')

        # Sometimes, secondary contains a label which is already in our
        # primary voice stream

        if (not phrases.is_empty()
                and phrases.ends_with(secondary)):
            cls._logger.debug(f'ends_with')
            secondary.clear()

        if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            cls._logger.debug_extra_verbose(f'newN: {newN} newW: {newW} newC: {newC}'
                                            f' newD: {newD}')

        if cls.is_primary_text_changed(phrases) or newC:
            # Any new secondary text also voiced
            cls.voiceText(compare, phrases, newD, secondary)
        elif cls.is_secondary_text_changed(secondary):
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug(f'voice secondary: {secondary}')
            cls.voiceSecondaryText(secondary)
        else:
            cls.checkMonitored()

    @classmethod
    def checkMonitored(cls):
        #  cls._logger.debug(f'checkMonitored')
        monitored: str | None = None

        if cls.playerStatus.visible():
            monitored = cls.playerStatus.getMonitoredText(
                    cls.get_tts().isSpeaking())
        if cls.bgProgress.visible():
            monitored = cls.bgProgress.getMonitoredText(cls.get_tts().isSpeaking())
        if cls.noticeDialog.visible():
            monitored = cls.noticeDialog.getMonitoredText(
                    cls.get_tts().isSpeaking())
        if not monitored:
            monitored = cls.windowReader.getMonitoredText(
                    cls.get_tts().isSpeaking())
        if monitored:
            try:
                phrases: PhraseList = PhraseList.create(monitored, interrupt=True)
                if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    cls._logger.debug_extra_verbose(
                        f'# phrases: {len(phrases)} texts: {phrases}')
                cls.sayText(phrases)
            except ExpiredException:
                cls._logger.debug(f'Expired before sayText')

    @classmethod
    def checkAutoRead(cls):
        #  cls._logger.debug('checkAutoRead')
        if not cls.waitingToReadItemExtra:
            return
        if cls.get_tts().isSpeaking():
            cls.waitingToReadItemExtra = time.time()
            return
        if time.time() - cls.waitingToReadItemExtra > cls.autoItemExtra:
            cls.waitingToReadItemExtra = None
            cls.sayItemExtra(interrupt=False)

    @classmethod
    def repeatText(cls):
        cls.winID = None
        cls.current_control_id = None
        cls.checkForText()

    @classmethod
    def sayExtra(cls):
        phrases: PhraseList = PhraseList()
        success: bool = cls.windowReader.getWindowExtraTexts(phrases)
        try:
            if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                cls._logger.debug_extra_verbose(
                    f'# texts: {len(phrases)} phrases: {phrases}')
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired at sayText')

    @classmethod
    def sayItemExtra(cls, interrupt=True):
        # See if window readers have anything that it wanted to say after the
        # current text spoke. Perhaps due to cost of generating it?

        phrases: PhraseList = PhraseList()
        success: bool = cls.windowReader.getItemExtraTexts(cls.current_control_id, phrases)
        if not success:
            return
        phrases.set_interrupt(interrupt)
        try:
            if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                cls._logger.debug_extra_verbose(f'# phrases: {len(phrases)} '
                                                f'phrase: {phrases}')
            if not phrases.is_empty():
                cls._logger.debug(f'CHECK phrases: {phrases} '
                                  f'reader: {cls.windowReader.__class__.__name__}')
            cls.sayText(phrases)
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            cls._logger.debug(f'Expired at sayText')
        except Exception as e:
            cls._logger.exception('')

    @classmethod
    def sayText(cls, phrases: PhraseList, preload_cache=False):
        Monitor.exception_on_abort()
        # cls._logger.debug(f'engine: {cls.instance.active_backend.backend_id}')
        # cls._logger.debug(f'engine from settings: {Settings.get_engine_id()}')
        if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug_verbose('Ignoring text, PLAYING_VIDEO')
            return
        if phrases.is_empty():
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug_verbose('Empty phrases')
            return

        if cls.get_tts().dead:
            return cls.fallbackTTS(cls.get_tts().deadReason)
        try:
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug_verbose(f'sayText # phrases: {len(phrases)} '
                                          f'{phrases} '
                                          f'interrupt: {str(phrases[0].get_interrupt())} '
                                          f'preload: {str(preload_cache)}')
                cls._logger.debug_verbose(phrases[0].get_debug_info())

            phrases.set_all_preload_cache(preload_cache)
            phrases.enable_check_expired()
            cls.driver.say(phrases)
        except ExpiredException:
            cls._logger.debug(f'Before driver.say')

    @classmethod
    def volumeUp(cls) -> None:
        msg: str | None = cls.get_tts().volumeUp()
        if not msg:
            return
        msg: str
        try:
            phrases: PhraseList = PhraseList.create(texts=msg, interrupt=True)
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired at VolumeUp')

    @classmethod
    def volumeDown(cls) -> None:
        msg: str | None = cls.get_tts().volumeDown()
        if not msg:
            return
        msg: str
        try:
            phrases: PhraseList = PhraseList.create(texts=msg, interrupt=True)
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired at VolumeDown')

    @classmethod
    def stopSpeech(cls) -> None:
        cls.get_tts()._stop()
        PhraseList.set_current_expired()

    @classmethod
    def cycle_debug(cls) -> None:
        level_setting: int = CriticalSettings.get_log_level()
        level_setting += 1
        if level_setting > 4:
            level_setting = 0
        phrases: PhraseList = PhraseList()
        if level_setting <= 0:  # Use DEFAULT value
            phrases.append(Phrase(text="Debug level DEFAULT"))
        elif level_setting == 1:  # Info
            phrases.append(Phrase(text="Debug level INFO"))
        elif level_setting == 2:  # Debug
            phrases.append(Phrase(text="Debug level DEBUG"))
        elif level_setting == 3:  # Verbose Debug
            phrases.append(Phrase(text="Debug level DEBUG VERBOSE"))
        elif level_setting >= 4:  # Extra Verbose Debug
            phrases.append(Phrase(text="Debug level DEBUG EXTRA VERBOSE"))
        TTSService.sayText(phrases)
        CriticalSettings.set_log_level(level_setting)
        python_log_level: int = CriticalSettings.get_logging_level()
        BasicLogger.set_log_level(python_log_level)

    @classmethod
    def updateWindowReader(cls) -> None:
        #  if module_logger.isEnabledFor(DEBUG):
        #      cls._logger.debug(f'winID: {cls.winID}')
        readerClass: Type[WindowReaderBase] = windows.getWindowReader(cls.winID)
        if cls.windowReader:
            cls.windowReader.close()
            if readerClass.ID == cls.windowReader.ID:
                cls.windowReader._reset(cls.winID)
                return
        try:
            cls.windowReader = readerClass(cls.winID, cls.get_instance())
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')

    @classmethod
    def window(cls):
        try:
            return WindowStateMonitor.get_window(cls.winID)
        except AbortException:
            reraise(*sys.exc_info())
        except RuntimeError as e:
            cls._logger.exception(f'Invalid winID: {cls.winID}')
        return None

    @classmethod
    def checkWindow(cls, newN: bool) -> bool:
        """
        Detect if window has changed, if so, read the basic
        window info ('Window <window_name>...'). Also update ids, etc.

        :param newN:
        :return:
        """
        #  cls._logger.debug(f'checkWindow: {newN}')
        Monitor.exception_on_abort()
        winID: int = xbmcgui.getCurrentWindowId()
        dialogID: int = xbmcgui.getCurrentWindowDialogId()
        if dialogID != 9999:
            winID = dialogID
        if winID == cls.winID:
            #  cls._logger.debug(f'Same winID: {winID} newN:{newN}')
            return newN
        xml_file = xbmc.getInfoLabel('Window.Property(xmlfile)')
        # cls._logger.debug(f'winID: {winID} previous winID {cls.winID} '
        #                   f'dialogID: {dialogID} xml_file: {xml_file}')
        cls.winID = winID
        cls.dialogID = dialogID
        cls.updateWindowReader()
        TTSService.msg_timestamp = datetime.datetime.now()
        try:
            success: bool = False
            name: str = cls.windowReader.getName()
            phrases: PhraseList = PhraseList()
            phrase: Phrase
            if name:
                phrase = Phrase(f'{Messages.get_msg(Messages.WINDOW)}: {name}',
                                post_pause_ms=Phrase.PAUSE_NORMAL, interrupt=not newN)
            else:
                phrase = Phrase(text=' ', post_pause_ms=Phrase.PAUSE_NORMAL,
                                interrupt=not newN, )
            phrases.append(phrase)
            success = cls.windowReader.getHeading(phrases)

            numb_phrases: int = len(phrases)
            success = cls.windowReader.getWindowTexts(phrases)
            if success:
                phrases[numb_phrases].set_pre_pause(Phrase.PAUSE_NORMAL)
            if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                cls._logger.debug_extra_verbose(
                        f'# phrases: {len(phrases)} texts: {phrases}')
                cls._logger.debug_extra_verbose(phrases[0].get_debug_info())
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired about to say window texts')
        return True

    @classmethod
    def checkControl(cls, newW) -> bool:
        """
            Determine if the control has changed. If so, update the id and
            return True.
        :param newW: True if the window has changed.
        :return: True if newW or if the control has changed
        """
        if not cls.winID:
            return newW
        control_id: int = cls.current_control_id
        try:
            control_id = abs(cls.window().getFocusId())
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug_verbose(f'CHECK Focus control_id: {control_id}')
            control = xbmc.getInfoLabel("System.CurrentControl()")
            # cls._logger.debug(f'winID: {cls.winID} control_id: {control_id} '
            #                   f'info label: {control}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')

        if control_id == cls.current_control_id:
            # cls._logger.debug(f'control_id: {control_id}')
            return newW
        cls.current_control_id = control_id
        if not control_id:
            return newW
        return True

    @classmethod
    def checkControlDescription(cls, newW: bool) -> bool:
        """
           See if anything needs to be said before the contents of the
           control (control name, context).

        :param newW: True if anything else has changed requiring reading
                     prior to this. (window, control, etc.)
        :return:   True if anything required voicing here, or prior to
                   this call (window, control, control's description, etc.)
        """
        #  cls._logger.debug(f'windowReader: {cls.windowReader}')
        try:
            phrases: PhraseList = PhraseList()
            success = cls.windowReader.getControlDescription(
                    cls.current_control_id, phrases)
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug_verbose(f'CHECK: checkControlDescription: {phrases} '
                                          f'reader:'
                                          f' {cls.windowReader.__class__.__name__}')
            success: bool = cls.windowReader.getControlPostfix(cls.current_control_id,
                                                               phrases)
            if not success:
                if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                    cls._logger.debug_verbose(f'CHECK ControlPostfix: {phrases}   '
                                  f'reader: {cls.windowReader.__class__.__name__}')
            if phrases.is_empty():
                return newW

            if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                cls._logger.debug_extra_verbose(
                    f'previous_control_id: {cls.current_control_id} '
                    f'# phrases: {len(phrases)} '
                    f'texts: {phrases}')
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired')
        return True

    @classmethod
    def voiceText(cls, compare: str, phrases: PhraseList, newD: bool,
                  secondary: PhraseList):
        # cls._logger.debug(f'primary: {phrases}\nsecondary: {secondary}')
        cls.set_previous_primary_text(phrases)
        cls.set_previous_secondary_text(secondary)

        try:
            label2: str = xbmc.getInfoLabel(
                    f'Container({cls.current_control_id}).ListItem.Label2')
            seasEp: str = xbmc.getInfoLabel(
                    f'Container({cls.current_control_id}).ListItem.Property(SeasonEpisode)')
            if seasEp is None:
                seasEp = ''
            if label2 is not None and len(seasEp) > 0:
                phrase = Phrase(text=f'{label2}:')
                phrases.insert(0, phrase)
                phrase = Phrase(text=f'{cls.formatSeasonEp(seasEp)}',
                                pre_pause_ms=Phrase.PAUSE_NORMAL)
                phrases.append(phrase)
            elif not secondary.is_empty():
                cls._previous_secondary_text = secondary[0].get_text()
                secondary[0].set_pre_pause(Phrase.PAUSE_LONG)
                phrases.extend(secondary)
            if not phrases.is_empty():
                phrases.set_interrupt(not newD)
                try:
                    if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                        cls._logger.debug_extra_verbose(
                            f'# phrases: {len(phrases)} phrase[0]: {phrases[0]}')
                    cls.sayText(phrases)
                except ExpiredException:
                    cls._logger.debug(f'Expired in voiceText')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
        if cls.autoItemExtra:
            cls.waitingToReadItemExtra = time.time()

    @classmethod
    def voiceSecondaryText(cls, phrases: PhraseList) -> None:
        cls.set_previous_secondary_text(phrases)
        if (phrases.is_empty() or (len(phrases[0].get_text()) == 0)
                or cls.get_tts().isSpeaking()):
            return
        try:
            phrase: Phrase = phrases[0]
            if phrase.get_text().endswith('%'):
                # Get just the percent part, so we don't keep saying downloading
                if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                    cls._logger.debug_verbose(f'secondary text with %: {phrase.get_text()}')
                text: str = phrase.get_text().rsplit(' ', 1)[-1]
                phrase.set_text(text)
            try:
                if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    cls._logger.debug_extra_verbose(
                        f'# phrases: {len(phrases)} texts: {phrases}')
                cls.sayText(phrases)
            except ExpiredException:
                cls._logger.debug(f'Expired in voiceSecondaryText')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            cls._logger.exception('')

    @classmethod
    def formatSeasonEp(cls, seasEp: str) -> str:
        if not seasEp:
            return ''
        return seasEp.replace('S', f'{Messages.get_msg(Messages.SEASON)}')\
            .replace('E', f'{Messages.get_msg(Messages.EPISODE)}')

    @classmethod
    def _cleanText(cls, text):
        text = UIConstants.FORMAT_TAG_RE.sub('', text)
        text = UIConstants.COLOR_TAG_RE.sub('', text)
        # Some speech engines say OK as Oklahoma
        text = UIConstants.OK_TAG_RE.sub(r'\1O K\2', text)
        # getLabel() on lists wrapped in [] and some speech engines have
        # problems with text starting with -
        text = text.strip('-[]')
        text = text.replace('XBMC', 'Kodi')
        if text == '..':
            text = Messages.get_msg(Messages.PARENT_DIRECTORY)
        return text

    @classmethod
    def cleanText(cls, text):
        if isinstance(text, str):
            return cls._cleanText(text)
        else:
            return [cls._cleanText(t) for t in text]


WindowStateMonitor.class_init()
