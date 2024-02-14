# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import datetime
import sys

import xbmc

from common import *

from cache.prefetch_movie_data.seed_cache import SeedCache
from common.exceptions import ExpiredException
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.phrases import Phrase, PhraseList
from utils.util import runInThread
from windows.windowparser import WindowParser

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
from windows import playerstatus, notice, backgroundprogress, windowparser
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


class TTSService:
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
    noticeDialog = notice.NoticeDialog(10107).init()
    winID = None
    dialogID = None
    windowReader = None
    controlID = None
    text = None
    textCompare = None
    secondaryText = None
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
        cls._logger = module_logger.getChild(cls.__class__.__name__)
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
        cls.noticeDialog = notice.NoticeDialog(10107).init()
        cls.winID = None
        cls.windowReader = None
        cls.controlID = None
        cls.text = None
        cls.textCompare = None
        cls.secondaryText = None
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
        from utils import \
            util  # Earlier import apparently not seen when called via NotifyAll
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
        elif command == Commands.ITEM_EXTRA:
            cls.sayItemExtra()
        elif command == Commands.VOL_UP:
            cls.volumeUp()
        elif command == Commands.VOL_DOWN:
            cls.volumeDown()
        elif command == Commands.STOP:
            cls.stopSpeech()
        elif command == Commands.SHUTDOWN:
            cls.shutdown()
        elif command == Commands.SAY:
            if not data:
                return

            # It is important to create PhraseList before
            # creating it's phrases, otherwise serial #s will be
            # incorrect

            phrases: PhraseList = PhraseList()
            phrase_args: Dict[str, List[Phrase]] = json.loads(data, object_hook=Phrase.from_json)
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
            except ExpiredException:
                cls._logger.debug(f'incoming text expired on arrival')
        elif command == Commands.SETTINGS_BACKEND_GUI:
            if cls._is_configuring:
                cls._logger.debug("Ignoring Duplicate SETTINGS_BACKEND_GUI")
            else:
                try:
                    cls._is_configuring = True
                    cls._logger.debug('Starting Backend_GUI')
                    util.runInThread(SettingsGUI.launch,
                                     name=Commands.SETTINGS_BACKEND_GUI)
                except:
                    cls._logger.exception("")
                finally:
                    cls._is_configuring = False

        elif command == Commands.SETTINGS_BACKEND_DIALOG:
            cls._logger.debug("Ignoring SETTINGS_BACKEND_DIALOG")

            # util.runInThread(ConfigUtils.selectBackend,
            #                  name=Commands.SETTINGS_BACKEND_DIALOG)
        elif command == Commands.SETTINGS_PLAYER_DIALOG:
            cls._logger.debug("Ignoring SETTINGS_PLAYER_DIALOG")

            # if not data:
            #     return
            # args = json.loads(data)
            # if not args:
            #     return
            # backend = args.get('backend')

            # backend_id = Settings.get_engine_id()

            # ConfigUtils.selectPlayer(backend_id)
        elif command == Commands.SETTINGS_SETTING_DIALOG:
            cls._logger.debug("Ignoring SETTINGS_DIALOG")
            '''
            if not data:
                return
            backend_id = Settings.get_engine_id()
            args = json.loads(data)
            if args[0] == SettingsProperties.VOICE:
                voice = args[0]
                ConfigUtils.selectSetting(backend_id, voice)
            elif args[0] == 'language':
                language = args[0]
                ConfigUtils.selectSetting(backend_id, language)
            elif args[0] == 'gender':
                ConfigUtils.selectGenderSetting(backend_id)
            '''
        elif command == Commands.SETTINGS_SETTING_SLIDER:
            cls._logger.debug("Ignoring SETTINGS_SLIDER")
            '''
            if not data:
                return
            args = json.loads(data)
            backend_id = Settings.get_engine_id()
            if args[0] == SettingsProperties.VOLUME:
                ConfigUtils.selectVolumeSetting(backend_id, *args)
            '''
        elif command == Commands.RELOAD_ENGINE:
            cls._logger.debug("Ignoring RELOAD_ENGINE")
            # cls.checkBackend()

    #        elif command.startswith('keymap.'): #Not using because will import
    #        keymapeditor into running service. May need if RunScript is not working as
    #        was my spontaneous experience
    #            command = command[7:]
    #            from lib import keymapeditor
    #            util.runInThread(keymapeditor.processCommand,(command,),
    #            name='keymap.INSTALL_DEFAULT')

    @classmethod
    def reloadSettings(cls):
        cls.readerOn = Settings.get_reader_on(True)
        cls.speakListCount = Settings.get_speak_list_count(True)
        cls.autoItemExtra = False
        if Settings.get_auto_item_extra(False):
            cls.autoItemExtra = Settings.get_auto_item_extra_delay(2)

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
            if not sender == Constants.ADDON_ID:
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
            if phrases[0].get_interrupt():
                cls._logger.debug(f'INTERRUPT: clearNoticeQueue')
                cls.clearNoticeQueue()
            while not Monitor.exception_on_abort(timeout=0.1):
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
                cls.sayText(phrases)
            except ExpiredException:
                cls._logger.debug(f'Expired just befor sayText')
            finally:
                cls.noticeQueue.task_done()
        return True

    @classmethod
    def initState(cls):
        if Monitor.is_abort_requested() or cls.stop:
            return
        cls.winID = None
        cls.windowReader = None
        cls.controlID = None
        cls.text = None
        cls.textCompare = None
        cls.secondaryText = None
        cls.keyboardText = ''
        cls.progressPercent = ''
        cls.lastProgressPercentUnixtime = 0
        cls.interval = 400
        cls.listIndex = None
        cls.waitingToReadItemExtra = None
        cls.reloadSettings()
        cls.background_driver: BackgroundDriver = None

    @classmethod
    def initTTS(cls, backend_id: str = None):
        clz = type(cls)
        if backend_id is None:
            backend_id = Settings.get_engine_id()
        else:
            Settings.set_backend_id(backend_id)
        new_active_backend = BaseServices.getService(backend_id)
        if (cls.get_active_backend() is not None
                and cls.get_active_backend().backend_id == backend_id):
            return

        backend_id = cls.set_active_backend(new_active_backend)
        cls.updateInterval()  # Poll interval
        cls._logger.info(f'New active backend: {backend_id}')
        cls.start_background_driver()

    @classmethod
    def fallbackTTS(cls, reason=None):
        if reason == Commands.RESET:
            return resetAddon()
        backend: Type[ITTSBackendBase | None] = BackendInfoBridge.getBackendFallback()
        module_logger.info(f'Backend falling back to: {backend.backend_id}')
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
        Monitor.register_notification_listener(cls.onNotification, 'service.notify')
        Monitor.register_abort_listener(cls.onAbortRequested)
        if seed_cache and Settings.is_use_cache(engine_id):
            call: callable = SeedCache.discover_movie_info
            runInThread(call, args=[engine_id],
                        name='seed_cache', delay=360)

        cls._logger.debug(f'TTSService initialized. Now waiting for events')
        try:
            while not cls.stop:
                # Interface reader mode
                while cls.readerOn and (
                        not Monitor.exception_on_abort(timeout=cls.interval_ms())) and (
                        not cls.stop):
                    try:
                        cls.checkForText()
                    except AbortException:
                        reraise(*sys.exc_info())
                    except RuntimeError:
                        module_logger.exception('start()')
                    except SystemExit:
                        module_logger.info('SystemExit: Quitting')
                        break
                    except TTSClosedException:
                        module_logger.info('TTSCLOSED')
                    except Exception as e:  # Because we don't want to kill speech on an error
                        cls._logger.exception("")
                        cls.initState()  # To help keep errors from repeating on the loop

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
                               backend_id=SettingsProperties.TTS_SERVICE,
                               default_value=False):
            engine: ITTSBackendBase = cls.tts
            cls.interval = Settings.getSetting(
                    SettingsProperties.POLL_INTERVAL,
                    backend_id=SettingsProperties.TTS_SERVICE,
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
        module_logger.debug(f'setting active_backend: {str(backend)}')
        module_logger.debug(f'backend_id: {backend.backend_id}')
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
    def checkForText(cls):
        cls.checkAutoRead()
        newN = cls.checkNoticeQueue()
        newW = cls.checkWindow(newN)
        newC = cls.checkControl(newW)
        newD = newC and cls.checkControlDescription(newW) or False
        text, compare = cls.windowReader.getControlText(cls.controlID)
        secondary = cls.windowReader.getSecondaryText()
        if (compare != cls.textCompare) or newC:
            cls.newText(compare, text, newD, secondary)
        elif secondary != cls.secondaryText:
            cls.newSecondaryText(secondary)
        else:
            cls.checkMonitored()

    @classmethod
    def checkMonitored(cls):
        monitored = None

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
                cls.sayText(phrases)
            except ExpiredException:
                cls._logger.debug(f'Expired before sayText')

    @classmethod
    def checkAutoRead(cls):
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
        cls.controlID = None
        cls.text = None
        cls.checkForText()

    @classmethod
    def sayExtra(cls):
        texts = cls.windowReader.getWindowExtraTexts()
        try:
            phrases: PhraseList = PhraseList.create(texts, interrupt=False)
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired at sayText')

    @classmethod
    def sayItemExtra(cls, interrupt=True):
        texts = cls.windowReader.getItemExtraTexts(cls.controlID)
        if texts is None:
            return
        try:
            phrases: PhraseList = PhraseList.create(texts, interrupt=interrupt)
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired at sayText')
        except Exception as e:
            cls._logger.exception('')

    @classmethod
    def sayText(cls, phrases: PhraseList, preload_cache=False):
        if KodiPlayerMonitor.player_status == KodiPlayerState.PLAYING:
            cls._logger.debug_verbose(f'Ignoring text, PLAYING')
            return
        if cls.get_tts().dead:
            return cls.fallbackTTS(cls.get_tts().deadReason)
        try:
            cls._logger.debug_verbose(f'sayText {repr(phrases[0].get_text())} '
                                      f'interrupt: {str(phrases[0].get_interrupt())} '
                                      f'preload: {str(preload_cache)}')
            phrases.set_all_preload_cache(preload_cache)
            cls.driver.say(phrases)
        except ExpiredException:
            cls._logger.debug(f'Before driver.say')

    '''
    @classmethod
    def sayTexts(cls, texts, interrupt=True):
        if not texts:
            return
        if cls.get_tts().dead:
            return cls.fallbackTTS(cls.get_tts().deadReason)
        module_logger.debug_verbose(repr(texts))
        cls.get_tts().sayList(cls.cleanText(texts), interrupt=interrupt)
    '''
    '''
    @classmethod
    def insertPause(cls, ms=500):
        cls.get_tts().insertPause(ms=ms)
        pass
    '''

    @classmethod
    def volumeUp(cls) -> None:
        msg = cls.get_tts().volumeUp()
        if not msg:
            return
        try:
            phrases: PhraseList = PhraseList()
            phrase: Phrase = Phrase.create(text=msg, interrupt=True)
            phrases.append(phrase)
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired at VolumeUp')

    @classmethod
    def volumeDown(cls) -> None:
        msg = cls.get_tts().volumeDown()
        if not msg:
            return
        try:
            phrases: PhraseList = PhraseList()
            phrase: Phrase = Phrase(text=msg, interrupt=True)
            phrases.append(phrase)
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired at VolumeDown')

    @classmethod
    def stopSpeech(cls) -> None:
        cls.get_tts()._stop()
        PhraseList.set_current_expired()

    @classmethod
    def updateWindowReader(cls):
        if module_logger.isEnabledFor(DISABLED):
            cls._logger.debug(f'winID: {cls.winID}')
        readerClass = windows.getWindowReader(cls.winID)
        if cls.windowReader:
            cls.windowReader.close()
            if readerClass.ID == cls.windowReader.ID:
                cls.windowReader._reset(cls.winID)
                return
        try:
            cls.windowReader = readerClass(cls.winID, cls.get_instance())
        except Exception as e:
            cls._logger.exception('')

    @classmethod
    def window(cls):
        return xbmcgui.Window(cls.winID)

    @classmethod
    def checkWindow(cls, newN):
        winID = xbmcgui.getCurrentWindowId()
        dialogID = xbmcgui.getCurrentWindowDialogId()
        changed: bool = False
        if dialogID != 9999 and dialogID != cls.dialogID:
            # winID = dialogID
            cls.dialogID = dialogID
            changed = True
        if winID != cls.winID:
            cls.winID = winID
            changed = True
        if not changed:
            if module_logger.isEnabledFor(DISABLED):
                cls._logger.debug(f'new winID: {winID} previous winID:{cls.winID}')
            return newN
        cls.updateWindowReader()
        if module_logger.isEnabledFor(DISABLED):
            module_logger.debug(f'Window ID: {winID} '
                                f'dialogID: {dialogID} '
                                f'Handler: {cls.windowReader.ID} '
                                f'File: {xbmc.getInfoLabel("Window.Property(xmlfile)")}')
        name = cls.windowReader.getName()
        TTSService.msg_timestamp = datetime.datetime.now()
        try:
            phrases: PhraseList = PhraseList()
            phrase: Phrase
            if name:
                phrase = Phrase(f'{Messages.get_msg(Messages.WINDOW)}: {name}',
                                post_pause_ms=Phrase.PAUSE_NORMAL, interrupt=not newN)
            else:
                phrase = Phrase(text=' ', post_pause_ms=Phrase.PAUSE_NORMAL,
                                interrupt=not newN, )
            phrases.append(phrase)
            heading = cls.windowReader.getHeading()
            if heading:
                phrase = Phrase(heading, post_pause_ms=Phrase.PAUSE_NORMAL)
                phrases.append(phrase)

            texts = cls.windowReader.getWindowTexts()
            if texts:
                set_pre_pause: bool = True
                for t in texts:
                    phrase = Phrase(t, post_pause_ms=Phrase.PAUSE_NORMAL)
                    if set_pre_pause:
                        phrase.set_pre_pause(Phrase.PAUSE_NORMAL)
                        set_pre_pause = False
                    phrases.append(phrase)
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired about to say window texts')
        return True

    @classmethod
    def checkControl(cls, newW):
        if not cls.winID:
            return newW
        controlID = cls.window().getFocusId()
        if controlID < 0:
            controlID = - controlID
        control = xbmc.getInfoLabel("System.CurrentControl()")
        clist = windowparser.getWindowParser().getControl(controlID)
        #  cls._logger.debug(f'windowparser.getControl: {str(control)}')
        if controlID == cls.controlID:
            return newW
        if module_logger.isEnabledFor(DEBUG):
            window = cls.window()
            #  cls._logger.debug(f'window: {type(window).__name__}')
            try:
                pass
            except Exception as e:
                cls._logger.exception('')
        cls.controlID = controlID
        if not controlID:
            return newW
        return True

    @classmethod
    def checkControlDescription(cls, newW):
        #  cls._logger.debug(f'windowReader: {cls.windowReader}')
        post = cls.windowReader.getControlPostfix(cls.controlID)
        description = cls.windowReader.getControlDescription(
                cls.controlID) or ''
        cls._logger.debug(f'newW: {newW} controlId: {cls.controlID}'
                          f' post: {post} description: {description}')
        if description or post:
            try:
                phrases: PhraseList = PhraseList()
                phrase: Phrase
                phrase = Phrase(text=f'{description}{post}',
                                post_pause_ms=Phrase.PAUSE_NORMAL,
                                interrupt=not newW)
                phrases.append(phrase)
                cls.sayText(phrases)
            except ExpiredException:
                cls._logger.debug(f'Expired')
            return True
        return newW

    @classmethod
    def newText(cls, compare, text, newD, secondary=None):
        cls.textCompare = compare
        label2 = xbmc.getInfoLabel(
                f'Container({cls.controlID}).ListItem.Label2')
        seasEp = xbmc.getInfoLabel(
                f'Container({cls.controlID}).ListItem.Property(SeasonEpisode)') or ''
        if label2 and seasEp:
            text = f'{label2}: {text}: {cls.formatSeasonEp}'
        if secondary:
            cls.secondaryText = secondary
            text = f'{text}{Constants.PAUSE_INSERT} {secondary}'
            cls._logger.debug(f'Inserting elipsis text: {text} secondary: {secondary}')
        if len(text) != 0:  # For testing
            try:
                phrases: PhraseList = PhraseList()
                phrase: Phrase = Phrase(text=text, interrupt=not newD)
                phrases.append(phrase)
                cls.sayText(phrases)
            except ExpiredException:
                cls._logger.debug(f'Expired in newText')
            if cls.autoItemExtra:
                cls.waitingToReadItemExtra = time.time()

    @classmethod
    def newSecondaryText(cls, text):
        cls.secondaryText = text
        if not text or cls.get_tts().isSpeaking():
            return
        if text.endswith('%'):
            # Get just the percent part, so we don't keep saying downloading
            text = text.rsplit(' ', 1)[-1]
        try:
            phrases: PhraseList = PhraseList()
            phrase: Phrase = Phrase(text=text, interrupt=True)
            phrases.append(phrase)
            cls.sayText(phrases)
        except ExpiredException:
            cls._logger.debug(f'Expired in newSecondaryText')

    @classmethod
    def formatSeasonEp(cls, seasEp):
        if not seasEp:
            return ''
        return seasEp.replace('S', '{0} '
                              .format(Messages.get_msg(Messages.SEASON))) \
            .replace('E', '{0} '.format(Messages.get_msg(Messages.EPISODE)))

    '''
    Original python 2 code:
    _formatTagRE = re.compile(r'\[/?(?:CR|B|I|UPPERCASE|LOWERCASE)\](?i)')
    _colorTagRE = re.compile(r'\[/?COLOR[^\]\[]*?\](?i)')
    _okTagRE = re.compile(r'(^|\W|\s)OK($|\s|\W)') #Prevents saying Oklahoma
    
    (?i) must now be at start of re. Removed redundant '\' escapes
    '''
    _formatTagRE = re.compile(r'(?i)\[/?(?:CR|B|I|UPPERCASE|LOWERCASE)]')
    _colorTagRE = re.compile(r'(?i)\[/?COLOR[^]\[]*?]')
    _okTagRE = re.compile(r'(^|\W|\s)OK($|\s|\W)')  # Prevents saying Oklahoma

    @classmethod
    def _cleanText(cls, text):
        text = cls._formatTagRE.sub('', text)
        text = cls._colorTagRE.sub('', text)
        # Some speech engines say OK as Oklahoma
        text = cls._okTagRE.sub(r'\1O K\2', text)
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
