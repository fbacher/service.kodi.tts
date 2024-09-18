# -*- coding: utf-8 -*-
"""

"""
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
from common.message_ids import MessageId
from common.phrases import Phrase, PhraseList
from utils.util import runInThread
from windowNavigation.help_manager import HelpManager
from windows.notice import NoticeDialog
from windows.ui_constants import UIConstants
from windows.window_state_monitor import WinDialog, WinDialogState, WindowStateMonitor

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


class TTSLogger:
    module_logger: BasicLogger = None
    module_change_cnt: int = 0

    @classmethod
    def logger(cls) -> BasicLogger:
        """

        :return:
        """
        if BasicLogger.change_cnt > cls.module_change_cnt:
            BasicLogger.change_cnt = cls.module_change_cnt
            cls.module_logger = BasicLogger.get_logger(__name__)
        return cls.module_logger


TTSLogger.logger().info(__version__)
TTSLogger.logger().info('Platform: {0}'.format(sys.platform))

if audio.PLAYSFX_HAS_USECACHED:
    TTSLogger.logger().info('playSFX() has useCached')
else:
    TTSLogger.logger().info('playSFX() does NOT have useCached')

# util.initCommands()
BaseServiceSettings()
addoninfo.initAddonsData()

BackendInfo.init()
# BootstrapEngines.init()

DO_RESET = False


def resetAddon():
    """

    :return:
    """
    global DO_RESET
    if DO_RESET:
        return
    DO_RESET = True
    TTSLogger.logger().info('Resetting addon...')
    xbmc.executebuiltin(
            'RunScript(special://home/addons/service.kodi.tts/resources/lib/tools'
            '/enabler.py,RESET)')


class TTSClosedException(Exception):
    """

    """
    pass


class Commands:
    """

    """
    DUMP_THREADS: Final[str] = 'DUMP_THREADS'
    TOGGLE_ON_OFF: Final[str] = 'TOGGLE_ON_OFF'
    CYCLE_DEBUG: Final[str] = 'CYCLE_DEBUG'
    VOICE_HINT: Final[str] = 'VOICE_HINT'
    HELP_DIALOG: Final[str] = 'HELP_DIALOG'
    INTRODUCTION: Final[str] = 'INTRODUCTION'
    HELP_CONFIG: Final[str] = 'HELP_CONFIG'
    RESET: Final[str] = 'RESET'
    REPEAT: Final[str] = 'REPEAT'
    EXTRA: Final[str] = 'EXTRA'
    ITEM_EXTRA: Final[str] = 'ITEM_EXTRA'
    VOL_UP: Final[str] = 'VOL_UP'
    VOL_DOWN: Final[str] = 'VOL_DOWN'
    SPEED_UP: Final[str] = 'SPEED_UP'
    SLOW_DOWN: Final[str] = 'SLOW_DOWN'
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
    _help_running: bool = False
    msg_timestamp: datetime.datetime = None
    _initialized: bool = False
    speakListCount = None
    readerOn: bool = True
    stop: bool = False
    disable: bool = False
    notice_queue: queue.Queue[PhraseList] = queue.Queue(20)
    noticeQueueCount: int = 0
    noticeQueueFullCount: int = 0
    active_backend: ITTSBackendBase | None = None
    toggle_on: bool = True
    playerStatus = playerstatus.PlayerStatus(10115).init()
    bgProgress = backgroundprogress.BackgroundProgress(10151).init()
    noticeDialog: NoticeDialog = NoticeDialog(10107).init()
    window_state: WinDialogState | None = None
    window_id: int | None = None
    dialog_id: int | None = None
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
        """

        """
        clz = type(self)
        super().__init__()  # Appears to not do anything
        if not clz._initialized:
            clz._initialized = True
            clz.instance = self
            clz.init()

    @classmethod
    def init(cls):
        """

        :return:
        """
        cls.instance_count += 1
        cls.speakListCount = None
        cls.readerOn: bool = True
        cls.stop: bool = False
        cls.disable: bool = False
        del cls.notice_queue
        cls.notice_queue: queue.Queue = queue.Queue(20)
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
        cls.window_state = None
        cls.window_id = None
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
        # TTSLogger.logger().info(f'TTSService.init instance_count: {cls.instance_count}')
        # Debug.dump_all_threads()

    @classmethod
    def interval_ms(cls):
        """

        :return:
        """
        return cls.interval / 1000.0

    @staticmethod
    def get_instance() -> 'TTSService':
        """

        :return:
        """
        return TTSService.instance

    @classmethod
    def onAbortRequested(cls):
        """

        :return:
        """
        cls.stop = True
        try:
            xbmc.log('Received AbortRequested', xbmc.LOGINFO)
            cls.close_tts()
        except TTSClosedException:
            pass

    @property
    def tts(self) -> ITTSBackendBase:
        """

        :return:
        """
        clz = type(self)
        if clz.is_tts_closed():
            raise TTSClosedException()
        return clz.active_backend

    @classmethod
    def get_tts(cls) -> ITTSBackendBase:
        """

        :return:
        """
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
        """

        :return:
        """
        if cls.active_backend is not None:
            cls.active_backend.close()
        else:
            pass

    @classmethod
    def is_tts_closed(cls) -> bool:
        """

        :return:
        """
        if cls.active_backend is not None:
            return cls.active_backend._closed
        else:
            return True

    @classmethod
    def process_command(cls, command, data=None):
        """

        :param command:
        :param data:
        :return:
        """
        from utils import util
        if TTSLogger.logger().isEnabledFor(DEBUG):
            TTSLogger.logger().debug(f'command: {command} toggle_on: {cls.toggle_on}')
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
            #  cls.repeatText()
            WindowStateMonitor.revoice_current_focus()
        elif command == Commands.EXTRA:
            cls.sayExtra(window_state=cls.window_state)
        elif command == Commands.ITEM_EXTRA:  # What is this?
            cls.sayItemExtra(cls.window_state)
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
        elif command == Commands.HELP_DIALOG:
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
            phrase_args: Dict[str, List[Phrase]] | None = None
            try:
                phrase_args = json.loads(data, object_hook=Phrase.from_json)
                # TTSLogger.logger().debug(f'phrases: {phrase_args}')
                if not phrase_args:
                    return
                phrase: Phrase
                for phrase in phrase_args.get('phrases'):
                    phrases.append(phrase)
                if not phrases.is_empty():
                    cls.queueNotice(phrases)
            except ExpiredException:
                if TTSLogger.logger().isEnabledFor(DEBUG):
                    TTSLogger.logger().debug(f'incoming phrases EXPIRED on arrival')
            except Exception:
                TTSLogger.logger().exception(f'Bad Phrase2: {data}')
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
                if TTSLogger.logger().isEnabledFor(DEBUG):
                    TTSLogger.logger().debug(f'incoming text EXPIRED on arrival')
        elif command == Commands.SETTINGS_BACKEND_GUI:
            if cls._is_configuring:
                if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
                    TTSLogger.logger().debug_verbose(
                            "Ignoring Duplicate SETTINGS_BACKEND_GUI")
            else:
                try:
                    cls._is_configuring = True
                    if TTSLogger.logger().isEnabledFor(DEBUG):
                        TTSLogger.logger().debug('Starting Backend_GUI')
                    cls.config_settings()
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception:
                    TTSLogger.logger().exception("")
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
            # TTSLogger.logger().debug("Ignoring RELOAD_ENGINE")
            cls.checkBackend()

    @classmethod
    def reload_settings(cls):
        """

        :return:
        """
        cls.readerOn = Settings.get_reader_on(True)
        if TTSLogger.logger().isEnabledFor(DEBUG):
            TTSLogger.logger().debug(f'READER_ON: {cls.readerOn}')
        cls.speakListCount = Settings.get_speak_list_count(True)
        cls.autoItemExtra = 0

        # if Settings.get_auto_item_extra(False):
        #     cls.autoItemExtra = Settings.get_auto_item_extra_delay(2)

    @classmethod
    def voice_hint(cls):
        """

        :return:
        """
        """
        Toggle voicing hint-info for voiced controls.

        :return:
        """
        Globals.voice_hint = not Globals.voice_hint
        WindowStateMonitor.revoice_current_focus()

    @classmethod
    def config_settings(cls):
        """

        :return:
        """
        from utils import util
        SettingsGUI.notify(cmd=SettingsGUI.START)

    @classmethod
    def help(cls):
        """

        :return:
        """
        from utils import util
        HelpManager.notify(cmd=HelpManager.HELP, text='')

    @classmethod
    def introduction(cls):
        """

        :return:
        """
        pass

    @classmethod
    def help_config(cls):
        """

        :return:
        """
        pass

    @classmethod
    def onDatabaseScanStartStop(cls, start: bool, database: str):
        """

        :param start: True if this is a START operation, False is STOP
        :param database: Name of database
        """
        msg: str = ''
        if start:
            operation: str = 'STARTED'
            msg = MessageId.DATABASE_SCAN_STARTED.get_formatted_msg(database)
        else:
            operation: str = 'STOPPED'
            msg =MessageId.DATABASE_SCAN_FINISHED.get_formatted_msg(database)

        TTSLogger.logger().info(f'DB SCAN {operation}: {database} - Notifying...')
        cls.queueNotice(PhraseList.create(texts=msg))

    @classmethod
    def onLibraryCleanStartStop(cls, start: bool, database):
        """

        :param start:
        :param database:
        """
        if start:
            operation: str = 'STARTED'
            msg = MessageId.LIBRARY_CLEAN_START.get_msg()
        else:
            operation: str = 'STOPPED'
            msg = MessageId.LIBRARY_CLEAN_COMPLETE.get_msg()

        TTSLogger.logger().info(f'LIBRARY CLEAN {operation} - Notifying...')
        cls.queueNotice(PhraseList.create(texts=msg))

    @classmethod
    def onScreensaverActivated(cls, start: bool):
        """

        :param start:
        """
        if start:
            operation: str = 'STARTED'
            msg = MessageId.SCREEN_SAVER_START.get_msg()
        else:
            operation: str = 'STOPPED'
            msg = MessageId.SCREEN_SAVER_INTERRUPTED.get_msg()

        TTSLogger.logger().info(f'SCREENSAVER {operation}: - Notifying...')
        cls.queueNotice(PhraseList.create(texts=msg))

    @classmethod
    def onNotification(cls, **kwargs):
        """

        :param kwargs:
        :return:
        """
        kwargs.setdefault('sender', 'invalid')
        kwargs.setdefault('method', 'invalid')
        kwargs.setdefault('data', 'invalid')
        sender: str = kwargs['sender']
        method: str = kwargs['method']
        data: str = kwargs['data']
        try:
            if sender == 'kodi':
                if method == 'onScanStarted':
                    database: str = data
                    cls.onDatabaseScanStartStop(start=True, database=database)
                elif method == 'onScanFinished':
                    database: str = data
                    cls.onDatabaseScanStartStop(start=False, database=database)
                elif method == 'onCleanStarted':
                    database: str = data
                    cls.onLibraryCleanStartStop(start=True, database=database)
                elif method == 'onCleanFinished':
                    database: str = data
                    cls.onLibraryCleanStartStop(start=False, database=database)
                elif method == 'onScreensaverActivated':
                    cls.onScreensaverActivated(start=True)
                elif method == 'onScreensaverDeactivated':
                    cls.onScreensaverActivated(start=False)
            if sender != Constants.ADDON_ID:
                return
            # Remove the "Other." prefix
            cls.process_command(method.split('.', 1)[-1], data)
        except AbortException:
            pass  # run in separate thread that is going to exit
        except Exception as e:
            TTSLogger.logger().exception('')

    @classmethod
    def queueNotice(cls, phrases: PhraseList):
        """

        :param phrases:
        :return:
        """
        try:
            if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
                TTSLogger.logger().debug_verbose(f'phrases: {len(phrases)} phrase: '
                                                 f'{phrases[0]}')
            if phrases[0].get_interrupt():
                if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
                    TTSLogger.logger().debug_verbose(f'INTERRUPT: clearing NoticeQueue')
                cls.clearNoticeQueue()
            while not Monitor.exception_on_abort(timeout=0.01):
                try:
                    cls.notice_queue.put_nowait(phrases)
                    break
                except queue.Full:
                    if TTSLogger.logger().isEnabledFor(DEBUG):
                        TTSLogger.logger().debug(f'queueNotice full')
        except ExpiredException:
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug('EXPIRED msg from queue')

    @classmethod
    def clearNoticeQueue(cls):
        """

        :return:
        """
        try:
            while not cls.notice_queue.empty():
                cls.notice_queue.task_done()
        except queue.Empty:
            return

    @classmethod
    def checkNoticeQueue(cls, window_state: WinDialogState) -> bool:
        """

        :param window_state:
        :return:
        """
        if cls.notice_queue.empty():
            return False
        while not cls.notice_queue.empty():
            try:
                phrases: PhraseList
                phrases = cls.notice_queue.get()
                cls.notice_queue.task_done()
                if phrases.is_expired():
                    if TTSLogger.logger().isEnabledFor(DEBUG):
                        TTSLogger.logger().debug(f'Phrase EXPIRED: {phrases[0]}')
                    continue
                if TTSLogger.logger().isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    TTSLogger.logger().debug_extra_verbose(
                        f'# phrases: {len(phrases)} {phrases}')
                cls.sayText(phrases)
            except ExpiredException:
                if TTSLogger.logger().isEnabledFor(DEBUG):
                    TTSLogger.logger().debug(f'EXPIRED just before sayText')
        return True

    @classmethod
    def initState(cls):
        """

        :return:
        """
        if Monitor.is_abort_requested() or cls.stop:
            return
        cls.window_id = None
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
        cls.reload_settings()
        cls.background_driver: BackgroundDriver | None = None

    @classmethod
    def initTTS(cls, backend_id: str = None) -> TTSService:
        """

        :param backend_id:
        :return:
        """
        clz = type(cls)
        if backend_id is None:
            backend_id = Settings.get_engine_id()
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'backend_id: {backend_id}')
        else:
            Settings.set_backend_id(backend_id)
        new_active_backend = BaseServices.getService(backend_id)
        if (cls.get_active_backend() is not None
                and cls.get_active_backend().backend_id == backend_id):
            return cls.get_instance()

        backend_id = cls.set_active_backend(new_active_backend)
        cls.updateInterval()  # Poll interval
        TTSLogger.logger().info(f'New active backend: {backend_id}')
        cls.start_background_driver()
        return cls.get_instance()

    @classmethod
    def fallbackTTS(cls, reason=None):
        """

        :param reason:
        :return:
        """
        if reason == Commands.RESET:
            return resetAddon()
        backend: Type[ITTSBackendBase | None] = BackendInfoBridge.getBackendFallback()
        TTSLogger.logger().info(f'Backend falling back to: {backend.backend_id}')
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
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'EXPIRED just before SayText in FallbackTTS')

    @classmethod
    def firstRun(cls):
        """

        :return:
        """
        from utils import keymapeditor
        TTSLogger.logger().info('FIRST RUN')
        TTSLogger.logger().info('Installing default keymap')
        keymapeditor.installDefaultKeymap(quiet=True)

    @classmethod
    def start(cls):
        """

        :return:
        """
        if TTSLogger.logger().isEnabledFor(DEBUG):
            TTSLogger.logger().debug(f'starting TTSService.start. '
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

        WindowStateMonitor.register_window_state_listener(cls.handle_ui_changes,
                                                          "main",
                                                          require_focus_change=False)

    @classmethod
    def handle_ui_changes(cls, window_state: WinDialogState) -> bool:
        """

        :param window_state: Contains information about the window at the time
                             of the check for state (window_id, control_id, etc.)
        :return:
        """
        #  TTSLogger.logger().debug(f'{window_state.verbose}')
        # TTSLogger.logger().debug(f'TTSService initialized. Now waiting for events'
        #                   f'stop: {cls.stop} readerOn: {cls.readerOn}')
        try:
            current_window_id: int = window_state.window_id
            cls.window_state = window_state
            if cls.stop:
                pass
            # if cls.readerOn:
            #    try:
            if window_state.revoice:
                cls.repeatText(window_state)
            else:
                cls.checkForText(window_state)
            return True

        except RuntimeError:
            TTSLogger.logger().exception('start()')
        except SystemExit:
            TTSLogger.logger().info('SystemExit: Quitting')
        except TTSClosedException:
            TTSLogger.logger().info('TTSCLOSED')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            # Because we don't want to kill speech on an error
            TTSLogger.logger().exception("")
            cls.initState()  # To help keep errors from repeating on the loop

        """
            # Idle mode
            while ((not cls.readerOn) and
                   (not Monitor.exception_on_abort(timeout=cls.interval_ms())) and (
                           not cls.stop)):
                try:
                    phrases: PhraseList = cls.notice_queue.get_nowait()
                    cls.sayText(phrases)
                    cls.notice_queue.task_done()
                except AbortException:
                    reraise(*sys.exc_info())
                except queue.Empty:
                    pass
                except RuntimeError:
                    TTSLogger.logger().error('start()')
                except SystemExit:
                    TTSLogger.logger().info('SystemExit: Quitting')
                    break
                except TTSClosedException:
                    TTSLogger.logger().info('TTSCLOSED')
                except:  # Because we don't want to kill speech on an error
                    TTSLogger.logger().error('start()', notify=True)
                    cls.initState()  # To help keep errors from repeating on the loop
                for x in range(
                        5):  # Check the queue every 100ms, check state every 500ms
                    if cls.notice_queue.empty():
                        Monitor.wait_for_abort(timeout=0.1)
                break
        

        finally:
            cls.close_tts()
            cls.end()
            utils.playSound('off')
            TTSLogger.logger().info('SERVICE STOPPED')
            if cls.disable:
                enabler.disableAddon()
        """

    @classmethod
    def end(cls):
        """

        :return:
        """
        return

    @classmethod
    def shutdown(cls):
        """

        :return:
        """
        cls.stop = True
        cls.disable = True

    @classmethod
    def updateInterval(cls):
        """

        :return:
        """
        if Settings.getSetting(SettingsProperties.OVERRIDE_POLL_INTERVAL,
                               service_id=SettingsProperties.TTS_SERVICE,
                               default_value=False):
            engine: ITTSBackendBase = cls.get_tts()
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
        """

        :param backend:
        :return:
        """
        if isinstance(backend, str):
            TTSLogger.logger().debug(f'backend is string: {backend}')
        else:
            backend.init()
            pass
        if cls.active_backend:
            cls.close_tts()

        #  backend.init()
        # TTSLogger.logger().debug(f'setting active_backend: {str(backend)}')
        # TTSLogger.logger().debug(f'backend_id: {backend.backend_id}')
        cls.active_backend = backend
        if cls.driver is None:
            cls.driver = Driver()
        return backend.backend_id

    @classmethod
    def start_background_driver(cls) -> None:
        """

        :return:
        """
        if cls.background_driver_instance is None:
            cls.background_driver_instance = BackgroundDriver()
            cls.background_driver = cls.background_driver_instance

    @classmethod
    def checkBackend(cls) -> None:
        """

        :return:
        """
        backend_id = Settings.get_engine_id()
        if (cls.active_backend is not None
                and backend_id == cls.active_backend.backend_id):
            return
        cls.initTTS()

    @classmethod
    def is_primary_text_changed(cls, phrases: PhraseList) -> bool:
        """

        :param phrases:
        :return:
        """
        # TTSLogger.logger().debug(f'phrases: {phrases} empty: {phrases.is_empty()} '
        #                   f'previous_primary_text: {cls._previous_primary_text}')
        if phrases.is_empty():
            return cls._previous_primary_text is None
        #  TTSLogger.logger().debug(f'equals: {phrases[0].text_equals(cls._previous_primary_text)}')
        return not phrases[0].text_equals(cls._previous_primary_text)

    @classmethod
    def set_previous_primary_text(cls, phrases: PhraseList) -> None:
        """

        :param phrases:
        :return:
        """
        if phrases is not None and not phrases.is_empty():
            cls._previous_primary_text = phrases[0].get_text()
        else:
            cls._previous_primary_text = None

    @classmethod
    def is_secondary_text_changed(cls, phrases: PhraseList) -> bool:
        """

        :param phrases:
        :return:
        """
        result: bool
        if phrases.is_empty():
            result = cls._previous_secondary_text != ''
        else:
            result = not phrases[0].text_equals(cls._previous_secondary_text)
        if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
            TTSLogger.logger().debug_verbose(f'previous_secondary_text:'
                                      f' {cls._previous_secondary_text} '
                                      f'phrases: {phrases} result: {result}')
        return result

    @classmethod
    def set_previous_secondary_text(cls, phrases: PhraseList) -> None:
        """

        :param phrases:
        :return:
        """
        if phrases.is_empty():
            cls._previous_secondary_text = ''
        else:
            cls._previous_secondary_text = phrases[0].get_text()

    @classmethod
    def checkForText(cls, window_state: WinDialogState):
        """

        :param window_state:
        :return:
        """
        #  TTSLogger.logger().debug(f'In checkForText')
        cls.checkAutoRead()  # Readers seem to flag text that they want read after the
                             # the current reading. Perhaps more cpu is_required?
                             # Perhaps to give user a chance to skip? Also seems
                             # to be able to be triggered externally.
        newN = cls.checkNoticeQueue(window_state)  # Any incoming notifications from cmd line or addon?
        newW = cls.checkWindow(newN, window_state)   # Window changed?
        newC = cls.checkControl(newW, window_state)  # Control Changed?
        #
        # Read Description of the control, or any other context prior to reading
        # the actual text in any changed control.

        newD = newC and cls.checkControlDescription(newW, window_state) or False
        TTSLogger.logger().debug(f'Calling: windowReader')
        phrases: PhraseList = PhraseList()
        success: bool = cls.windowReader.getControlText(cls.current_control_id, phrases)
        if not success or phrases.is_empty():
            compare = ''
        else:
            # TTSLogger.logger().debug(f'CHECK getControlText: {phrases}'
            #                   f' reader: {cls.windowReader.__class__.__name__}')
            compare: str = phrases[0].get_text()
        # Secondary text is typically some detail (like progress status) that
        # is not related to the focused text. Therefore, you don't want it to
        # mess with the history of the primary text, causing it to be
        # unnecessarily re-voiced.

        secondary: PhraseList = PhraseList()
        success = cls.windowReader.getSecondaryText(secondary)
        if not cls.is_secondary_text_changed(secondary):
            if not secondary.is_empty():
                TTSLogger.logger().debug(f'CHECK: secondaryText {secondary} not changed '
                                  f'reader: {cls.windowReader.__class__.__name__}')
            secondary.clear()

        if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
            if not phrases.is_empty() or compare != '' or len(secondary) > 0:
                TTSLogger.logger().debug_verbose(f'control_id: {cls.current_control_id} '
                                          f'phrases: {phrases} '
                                          f'compare: {compare} secondary: {secondary} '
                                          f'previous_secondaryText: '
                                          f'{cls._previous_secondary_text}')

        # Sometimes, secondary contains a label which is already in our
        # primary voice stream

        if (not phrases.is_empty()
                and phrases.ends_with(secondary)):
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug('ends_with')
            secondary.clear()

        if TTSLogger.logger().isEnabledFor(DEBUG_EXTRA_VERBOSE):
            TTSLogger.logger().debug_extra_verbose(f'newN: {newN} newW: {newW} newC: {newC}'
                                            f' newD: {newD}')

        if cls.is_primary_text_changed(phrases) or newC:
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'secondary_text_changed')
            # Any new secondary text also voiced
            cls.voiceText(window_state, compare, phrases, newD, secondary)
        elif cls.is_secondary_text_changed(secondary):
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'voice secondary: {secondary}')
            cls.voiceSecondaryText(window_state, secondary)
        else:
            cls.checkMonitored()

    @classmethod
    def checkMonitored(cls):
        """

        :return:
        """
        #  TTSLogger.logger().debug(f'checkMonitored')
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
                if TTSLogger.logger().isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    TTSLogger.logger().debug_extra_verbose(
                        f'# phrases: {len(phrases)} texts: {phrases}')
                cls.sayText(phrases)
            except ExpiredException:
                TTSLogger.logger().debug(f'EXPIRED before sayText')

    @classmethod
    def checkAutoRead(cls):
        """

        :return:
        """
        #  TTSLogger.logger().debug('checkAutoRead')
        if not cls.waitingToReadItemExtra:
            return
        if cls.get_tts().isSpeaking():
            cls.waitingToReadItemExtra = time.time()
            return
        if time.time() - cls.waitingToReadItemExtra > cls.autoItemExtra:
            cls.waitingToReadItemExtra = None
            cls.sayItemExtra(interrupt=False)

    @classmethod
    def repeatText(cls, window_state: WinDialogState):
        """

        :param window_state:
        :return:
        """
        cls.window_id = None
        cls.current_control_id = None
        cls.checkForText(window_state)

    @classmethod
    def sayExtra(cls, window_state: WinDialogState):
        """

        :param window_state:
        :return:
        """
        phrases: PhraseList = PhraseList()
        success: bool = cls.windowReader.getWindowExtraTexts(phrases)
        try:
            if TTSLogger.logger().isEnabledFor(DEBUG_EXTRA_VERBOSE):
                TTSLogger.logger().debug_extra_verbose(
                    f'# texts: {len(phrases)} phrases: {phrases}')
            cls.sayText(phrases)
        except ExpiredException:
            TTSLogger.logger().debug(f'EXPIRED at sayText')

    @classmethod
    def sayItemExtra(cls, window_state: WinDialogState, interrupt=True):
        """

        :param window_state:
        :param interrupt:
        :return:
        """
        # See if window readers have anything that it wanted to say after the
        # current text spoke. Perhaps due to cost of generating it?

        phrases: PhraseList = PhraseList()
        success: bool = cls.windowReader.getItemExtraTexts(cls.current_control_id, phrases)
        if not success:
            return
        phrases.set_interrupt(interrupt)
        try:
            if TTSLogger.logger().isEnabledFor(DEBUG_EXTRA_VERBOSE):
                TTSLogger.logger().debug_extra_verbose(f'# phrases: {len(phrases)} '
                                                f'phrase: {phrases}')
            if not phrases.is_empty():
                if TTSLogger.logger().isEnabledFor(DEBUG):
                    TTSLogger.logger().debug(f'CHECK phrases: {phrases} '
                                  f'reader: {cls.windowReader.__class__.__name__}')
            cls.sayText(phrases)
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'EXPIRED at sayText')
        except Exception as e:
            TTSLogger.logger().exception('')

    @classmethod
    def sayText(cls, phrases: PhraseList, preload_cache=False):
        """

        :param phrases:
        :param preload_cache:
        :return:
        """
        Monitor.exception_on_abort()
        # TTSLogger.logger().debug(f'engine: {cls.instance.active_backend.backend_id}')
        # TTSLogger.logger().debug(f'engine from settings: {Settings.get_engine_id()}')
        if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING_VIDEO:
            if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
                TTSLogger.logger().debug_verbose('Ignoring text, PLAYING_VIDEO')
            return
        if phrases.is_empty():
            if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
                TTSLogger.logger().debug_verbose('Empty phrases')
            return

        if cls.get_tts().dead:
            return cls.fallbackTTS(cls.get_tts().deadReason)
        try:
            if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
                TTSLogger.logger().debug_verbose(f'sayText # phrases: {len(phrases)} '
                                          f'{phrases} '
                                          f'interrupt: {str(phrases[0].get_interrupt())} '
                                          f'preload: {str(preload_cache)}')
                TTSLogger.logger().debug_verbose(phrases[0].get_debug_info())

            phrases.set_all_preload_cache(preload_cache)
            phrases.enable_check_expired()
            cls.driver.say(phrases)
        except ExpiredException:
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'Before driver.say')

    @classmethod
    def volumeUp(cls) -> None:
        """
        Increases the TTS volume. Does NOT impact Kodi's volume
        :return:
        """
        msg: str | None = cls.get_tts().volumeUp()
        if not msg:
            return
        msg: str
        try:
            phrases: PhraseList = PhraseList.create(texts=msg, interrupt=True)
            cls.sayText(phrases)
        except ExpiredException:
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'EXPIRED at VolumeUp')

    @classmethod
    def volumeDown(cls) -> None:
        """
          Decreases the TTS volume. Does NOT impact Kodi's volume
          :return:
          """
        msg: str | None = cls.get_tts().volumeDown()
        if not msg:
            return
        msg: str
        try:
            phrases: PhraseList = PhraseList.create(texts=msg, interrupt=True)
            cls.sayText(phrases)
        except ExpiredException:
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'EXPIRED at VolumeDown')

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
        #  BasicLogger.set_log_level(python_log_level)

    @classmethod
    def updateWindowReader(cls, window_state: WinDialogState) -> None:
        """

        :param window_state:
        :return:
        """
        #  if TTSLogger.logger().isEnabledFor(DEBUG):
        #      TTSLogger.logger().debug(f'window_id: {cls.window_id}')
        readerClass: Type[WindowReaderBase] = windows.getWindowReader(cls.window_id)
        if cls.windowReader:
            cls.windowReader.close()
            if readerClass.ID == cls.windowReader.ID:
                cls.windowReader._reset(cls.window_id)
                return
        try:
            cls.windowReader = readerClass(cls.window_id, cls.get_instance())
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            TTSLogger.logger().exception('')

    @classmethod
    def window(cls, window_state: WinDialogState):
        """

        :param window_state:
        :return:
        """
        try:
            return WindowStateMonitor.get_window(window_state.window_id)
        except AbortException:
            reraise(*sys.exc_info())
        except RuntimeError as e:
            TTSLogger.logger().exception(f'Invalid winID: {cls.window_id}')
        return None

    @classmethod
    def checkWindow(cls, newN: bool, window_state: WinDialogState) -> bool:
        """
        Detect if window has changed, if so, read the basic
        window info ('Window <window_name>...'). Also update ids, etc.

        :param window_state:
        :param newN:
        :return:
        """
        #  TTSLogger.logger().debug(f'checkWindow: {newN}')
        Monitor.exception_on_abort()
        winID: int = xbmcgui.getCurrentWindowId()
        dialogID: int = xbmcgui.getCurrentWindowDialogId()
        if dialogID != 9999:
            winID = dialogID
        if winID == cls.window_id:
            #  TTSLogger.logger().debug(f'Same window_id: {window_id} newN:{newN}')
            return newN
        xml_file = xbmc.getInfoLabel('Window.Property(xmlfile)')
        # TTSLogger.logger().debug(f'window_id: {window_id} previous window_id {cls.window_id} '
        #                   f'dialog_id: {dialog_id} xml_file: {xml_file}')
        cls.window_id = winID
        cls.dialog_id = dialogID
        cls.updateWindowReader(window_state)
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
            if TTSLogger.logger().isEnabledFor(DEBUG_EXTRA_VERBOSE):
                TTSLogger.logger().debug_extra_verbose(
                        f'# phrases: {len(phrases)} texts: {phrases}')
                TTSLogger.logger().debug_extra_verbose(phrases[0].get_debug_info())
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'Say: {phrases}')
            cls.sayText(phrases)
        except ExpiredException:
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'EXPIRED about to say window texts')
        return True

    @classmethod
    def checkControl(cls, newW, window_state: WinDialogState) -> bool:
        """
            Determine if the control has changed. If so, update the id and
            return True.
        :param window_state:
        :param newW: True if the window has changed.
        :return: True if newW or if the control has changed
        """
        if not cls.window_id:
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'no winID')
            return newW
        control_id: int = cls.current_control_id
        try:
            control_id = abs(cls.window(window_state).getFocusId())
            if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
                TTSLogger.logger().debug_verbose(f'CHECK Focus control_id: {control_id}')
            control = xbmc.getInfoLabel("System.CurrentControl()")
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            TTSLogger.logger().exception('')

        if control_id == 0:
            control_id = None
        if control_id == cls.current_control_id:
            return newW
        cls.current_control_id = control_id
        if control_id is None:
            return newW
        return True

    @classmethod
    def checkControlDescription(cls, newW: bool, window_state: WinDialogState) -> bool:
        """
           See if anything needs to be said before the contents of the
           control (control name, context).

        :param window_state:
        :param newW: True if anything else has changed requiring reading
                     prior to this. (window, control, etc.)
        :return:   True if anything is_required voicing here, or prior to
                   this call (window, control, control's description, etc.)
        """
        #  TTSLogger.logger().debug(f'windowReader: {cls.windowReader}')
        try:
            phrases: PhraseList = PhraseList()
            success = cls.windowReader.getControlDescription(
                    cls.current_control_id, phrases)
            if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
                TTSLogger.logger().debug_verbose(f'CHECK: checkControlDescription: {phrases} '
                                          f'reader:'
                                          f' {cls.windowReader.__class__.__name__}')
            success: bool = cls.windowReader.getControlPostfix(cls.current_control_id,
                                                               phrases)
            if not success:
                if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
                    TTSLogger.logger().debug_verbose(f'CHECK ControlPostfix: {phrases}   '
                                  f'reader: {cls.windowReader.__class__.__name__}')
            if phrases.is_empty():
                return newW

            if TTSLogger.logger().isEnabledFor(DEBUG_EXTRA_VERBOSE):
                TTSLogger.logger().debug_extra_verbose(
                    f'previous_control_id: {cls.current_control_id} '
                    f'# phrases: {len(phrases)} '
                    f'texts: {phrases}')
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'{phrases}')
            cls.sayText(phrases)
        except ExpiredException:
            if TTSLogger.logger().isEnabledFor(DEBUG):
                TTSLogger.logger().debug(f'EXPIRED')
        return True

    @classmethod
    def voiceText(cls, window_state: WinDialogState, compare: str, phrases: PhraseList, newD: bool,
                  secondary: PhraseList):
        """

        :param window_state:
        :param compare:
        :param phrases:
        :param newD:
        :param secondary:
        :return:
        """
        # TTSLogger.logger().debug(f'primary: {phrases}\nsecondary: {secondary}')
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
                    if TTSLogger.logger().isEnabledFor(DEBUG):
                        TTSLogger.logger().debug(
                            f'# phrases: {len(phrases)} phrase[0]: {phrases[0]}')
                    cls.sayText(phrases)
                except ExpiredException:
                    if TTSLogger.logger().isEnabledFor(DEBUG):
                        TTSLogger.logger().debug(f'EXPIRED in voiceText')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            TTSLogger.logger().exception('')
        if cls.autoItemExtra:
            cls.waitingToReadItemExtra = time.time()

    @classmethod
    def voiceSecondaryText(cls, window_state: WinDialogState, phrases: PhraseList) -> None:
        """

        :param window_state:
        :param phrases:
        :return:
        """
        cls.set_previous_secondary_text(phrases)
        if (phrases.is_empty() or (len(phrases[0].get_text()) == 0)
                or cls.get_tts().isSpeaking()):
            return
        try:
            phrase: Phrase = phrases[0]
            if phrase.get_text().endswith('%'):
                # Get just the percent part, so we don't keep saying downloading
                if TTSLogger.logger().isEnabledFor(DEBUG_VERBOSE):
                    TTSLogger.logger().debug_verbose(f'secondary text with %: {phrase.get_text()}')
                text: str = phrase.get_text().rsplit(' ', 1)[-1]
                phrase.set_text(text)
            try:
                if TTSLogger.logger().isEnabledFor(DEBUG_EXTRA_VERBOSE):
                    TTSLogger.logger().debug_extra_verbose(
                        f'# phrases: {len(phrases)} texts: {phrases}')
                cls.sayText(phrases)
            except ExpiredException:
                if TTSLogger.logger().isEnabledFor(DEBUG):
                    TTSLogger.logger().debug(f'EXPIRED in voiceSecondaryText')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            TTSLogger.logger().exception('')

    @classmethod
    def formatSeasonEp(cls, seasEp: str) -> str:
        """

        :param seasEp:
        :return:
        """
        if not seasEp:
            return ''
        return seasEp.replace('S', f'{Messages.get_msg(Messages.SEASON)}')\
            .replace('E', f'{Messages.get_msg(Messages.EPISODE)}')

    @classmethod
    def _cleanText(cls, text):
        """

        :param text:
        :return:
        """
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
        text = text.strip()
        return text

    @classmethod
    def cleanText(cls, text):
        """

        :param text:
        :return:
        """
        if isinstance(text, str):
            return cls._cleanText(text)
        else:
            return [cls._cleanText(t) for t in text]


WindowStateMonitor.class_init()
