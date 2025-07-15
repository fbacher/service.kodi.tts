# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import faulthandler
import io
import sys

"""
Created on Feb 19, 2019

@author: Frank Feuerbacher

"""

import copy
import threading

import xbmc

from common import *

from common.constants import Constants
from common.critical_settings import CriticalSettings
from common.logger import *
from common.minimal_monitor import MinimalMonitor

MY_LOGGER = BasicLogger.get_logger(__name__)
DEBUG_LOG: bool = MY_LOGGER.isEnabledFor(DEBUG)


class Monitor(MinimalMonitor):
    """
        Provides a number of customizations to xbmc.monitor

        MinimalMonitor text_exists simply to not drag in logging dependencies
        at startup.
    """
    FOREVER = 24 * 60 * 60 * 365  # A year, in seconds

    # Give unique name to notification thread so that garbage collector can be
    # happier
    _thread_count: int = 0

    class NotificationMonitor(xbmc.Monitor):

        def onNotification(self, sender: str, method: str, data: str) -> None:
            """
            onNotification method.

            :param sender: Sender of the notification
            :param method: Name of the notification
            :param data: JSON-encoded data of the notification

            :return:

            Will be called when Kodi receives or sends a notification
            """
            if sender not in ('xbmc', Constants.ADDON_ID):
                return
            if not data:
                data = ''
            Monitor._inform_notification_listeners(sender, method, data)

        def onScanStarted(self, database):
            sender: str = 'kodi'
            method = 'onScanStarted'
            data: str = database
            Monitor._inform_notification_listeners(sender, method, data)

        def onScanFinished(self, database):
            sender: str = 'kodi'
            method = 'onScanFinished'
            data: str = database
            Monitor._inform_notification_listeners(sender, method, data)

        def onCleanStarted(self, database):
            sender: str = 'kodi'
            method = 'onCleanStarted'
            data: str = database
            Monitor._inform_notification_listeners(sender, method, data)

        def onCleanFinished(self, database):
            sender: str = 'kodi'
            method = 'onCleanFinished'
            data: str = database
            Monitor._inform_notification_listeners(sender, method, data)

        def onScreensaverActivated(self) -> None:
            """
            onScreensaverActivated method.

            Will be called when screensaver kicks in
            """
            sender: str = 'kodi'
            method = 'onScreensaverActivated'
            data: str = ''
            Monitor._inform_notification_listeners(sender, method, data)

        def onScreensaverDeactivated(self) -> None:
            """
            onScreensaverDeactivated method.

            Will be called when screensaver goes off
            """
            sender: str = 'kodi'
            method = 'onScreensaverDeactivated'
            data: str = ''
            Monitor._inform_notification_listeners(sender, method, data)

    # End class NotificationMonitor

    _initialized: bool = False
    _NotificationMonitor = NotificationMonitor()
    startup_complete_event: threading.Event = None
    _monitor_changes_in_settings_thread: threading.Thread = None
    _notification_listeners: Dict[Callable[[Dict[str, Any]], None], str] = None
    _notification_listener_lock: threading.RLock = None
    _screen_saver_listeners: Dict[str, Callable[[Dict[str, Any]], None]] = None
    _screen_saver_listener_lock: threading.RLock = None
    _settings_changed_listeners: Dict[Callable[[None], None], str] = None
    _settings_changed_listener_lock: threading.RLock = None
    _abort_listeners: Dict[Callable[[None], None], str] = None
    _abort_listener_lock: threading.RLock = None
    _abort_listeners_informed: bool = False
    #  _wait_return_count_map: Dict[str, int] = {}  # thread_id, returns from wait
    #  _wait_call_count_map: Dict[str, int] = {}  # thread_id, calls to wait
    _inform_abort_listeners_thread: threading.Thread = None

    """
      Can't get rid of __init__
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def class_init(cls) -> None:
        """

        """
        if not cls._initialized:
            cls._initialized = True
            # Weird problems with recursion if we make requests to the super

            cls._screen_saver_listeners = {}
            cls._screen_saver_listener_lock = threading.RLock()
            cls._settings_changed_listeners = {}
            cls._settings_changed_listener_lock = threading.RLock()
            cls._abort_listeners: Dict[Callable[[None], None], str] = {}
            cls._abort_listener_lock = threading.RLock()
            cls._abort_listeners_informed: bool = False
            cls._notification_listeners = {}
            cls._notification_listener_lock = threading.RLock()
            #
            # These events are prioritized:
            #
            # _wait_for_abort_thread waits until a Kodi Abort occurs,
            # once it happens it will set the lower priority event:
            # startup_complete_event. This is done so that
            # anything waiting on
            # them will stop waiting. They should be sure to check why they
            # woke up, in case they need to take more drastic action.
            #
            # The same scheme is used for wait_for_startup_complete,

            cls.startup_complete_event = threading.Event()
            super().register_abort_callback(cls._inform_abort_listeners)

            cls._monitor_changes_in_settings_thread = threading.Thread(
                    target=cls._monitor_changes_in_settings,
                    name='mntr_chng_setngs')
            cls._monitor_changes_in_settings_thread.start()
            from common.garbage_collector import GarbageCollector
            GarbageCollector.add_thread(cls._monitor_changes_in_settings_thread)

    @classmethod
    def _monitor_changes_in_settings(cls) -> None:
        """

        :return:
        """
        pass
        '''
        try:
            # Add one minute delay
            change_file = xbmcvfs.translatePath(
               f'special://userdata/addon_data/{
               Constants.ADDON_ID}/settings_changed.pickle')
            settings_file = xbmcvfs.translatePath(
                f'special://userdata/addon_data/{Constants.ADDON_ID}/settings.xml')

            with io.open(settings_file, mode='rb') as settings_file_fd:
                settings = settings_file_fd.read()
                new_settings_digest = hashlib.md5(settings).hexdigest()

            changed = False
            change_record = dict()
            if not os.path.text_exists(change_file):
                changed = True
            else:
                if not os.access(change_file, os.R_OK | os.W_OK):
                    MY_LOGGER.error('No rw access: {}'.format(change_file))
                    changed = True
                    try:
                        os.remove(change_file)
                    except Exception as e:
                        MY_LOGGER.error('Can not delete {}'.format(change_file))

            if not changed:
                try:
                    settings_digest = None
                    with io.open(change_file, mode='rb') as settings_changed_fd:
                        change_record = pickle.load(settings_changed_fd)
                        settings_digest = change_record.get(
                            SettingProp.SETTINGS_DIGEST, None)

                    if new_settings_digest != settings_digest:
                        changed = True

                except (IOError) as e:
                    MY_LOGGER.error('Error reading {} or {}'.format(
                        change_file, settings_file))
                    changed = True
                except (Exception) as e:
                    MY_LOGGER.error('Error processing {} or {}'.format(
                        change_file, settings_file))
                    changed = True

            if changed:
                try:
                    change_record[SettingProp.SETTINGS_DIGEST] = 
                    new_settings_digest
                    with io.open(change_file, mode='wb') as change_file_fd:
                        pickle.dump(change_record, change_file_fd)

                #  TODO: Change to callback

                    from cache.voicecache import VoiceCache
                    VoiceCache.clean_cache(changed)
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception:
                    MY_LOGGER.exception('')
            else:
                from cache.voicecache import VoiceCache
                VoiceCache.clean_cache(changed)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

        """
        last_time_changed: datetime.datetime
        settings_path = os.path.join(
            Constants.FRONTEND_DATA_PATH, 'settings.xml')
        try:
            file_stat = os.stat(settings_path)
            last_time_changed = datetime.datetime.fromtimestamp(file_stat.st_mtime)
        except Exception as e:
            MY_LOGGER.debug("Failed to read settings.xml")
            last_time_changed = datetime.datetime.now()

        # It seems that if multiple xbmc.WaitForAborts are pending, xbmc
        # Does not inform all of them when an abort occurs. So, instead
        # of waiting for 60 seconds per iteration, we wait 0.1 seconds
        # and act when 600 calls has been made. Not exactly 60 seconds, but
        # close enough for this

        thread_name = CriticalSettings.get_plugin_name() + "_monitorSettingsChanges"
        threading.current_thread().setName(thread_name)
        iterations: int = 600

        # We know that settings have not changed when we first start up,
        # so ignore first false change.

        while not cls.wait_for_abort(timeout=0.1):
            iterations -= 1
            if iterations < 0:
                iterations = 600
                try:
                    file_stat = os.stat(settings_path)
                    mod_time: datetime.datetime = datetime.datetime.fromtimestamp(
                        file_stat.st_mtime)
                except Exception as e:
                    MY_LOGGER.debug("Failed to read settings.xml")
                    mod_time: datetime.datetime = datetime.datetime.now()

                # Wait at least a minute after settings changed, just in case there
                # are multiple changes.
                #
                # Note that when settings are changed via kodi config that this
                # will cause a second settings changed event a minute or two
                # after the initial one. However, the Settings code should
                # detect that nothing has actually changed and no harm should be
                # done.

                if last_time_changed == mod_time:
                    continue

                now: datetime.datetime = datetime.datetime.now()

                #
                # Was file modified at least a minute ago?
                #

                delta: datetime.timedelta = now - mod_time

                if delta.total_seconds() > 60:
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v('Settings Changed!')
                    last_time_changed = mod_time
                    cls.on_settings_changed()

                    # Here we go again
        """
        '''

    @classmethod
    def runInThread(cls, func: Callable, args: List[Any] = None, name: str = '?',
                    delay: float = 0.0, **kwargs) -> None:
        cls._thread_count += 1
        import threading
        if args is None:
            args = []
        thread = threading.Thread(target=cls.thread_wrapper,
                                  name=f'MonHlpr_{cls._thread_count}:{name}',
                                  args=args, kwargs={'target': func,
                                                     'delay': delay, **kwargs})
        if DEBUG_LOG:
            xbmc.log(f'monitor.runInThread starting thread {name}', xbmc.LOGINFO)
        thread.start()
        from common.garbage_collector import GarbageCollector
        GarbageCollector.add_thread(thread)

    @classmethod
    def thread_wrapper(cls, *args, **kwargs):
        try:
            target: Callable = kwargs.get('target')
            delay: float = kwargs.get('delay')
            if delay is not None and isinstance(delay, float):
                Monitor.exception_on_abort(timeout=delay)

            target(*args, **kwargs)
        except AbortException:
            pass  # Let thread die
        except Exception as e:
            MY_LOGGER.exception('')

    @classmethod
    def get_listener_name(cls,
                          listener: Callable[[Dict[str, Any] | None], None],
                          name: str = None) -> str:
        listener_name: str | None = None
        if name is not None:
            listener_name = name
        elif hasattr(listener, '__name__'):
            try:
                listener_name = listener.__name__
            except:
                pass
        elif hasattr(listener, 'name'):
            try:
                listener_name = listener.name
            except:
                pass
        if listener_name is None:
            raise ValueError('No listener name specified, nor does listener have '
                             '__name__ or name attribute')
        return listener_name

    @classmethod
    def register_screensaver_listener(cls,
                                      listener: Callable[[Dict[str, Any]], None],
                                      name: str = None) -> None:
        """

        :param listener:
        :param name:
        :return:
        """
        with cls._screen_saver_listener_lock:
            if not (cls.is_abort_requested()
                    or listener in cls._screen_saver_listeners):
                listener_name = cls.get_listener_name(listener, name)
                if listener_name in cls._screen_saver_listeners.keys():
                    raise ValueError(f'Duplicate listener with name: {listener_name}')
                cls._screen_saver_listeners[listener_name] = listener

    @classmethod
    def unregister_screensaver_listener(cls,
                                        listener: Callable[[Dict[str, Any]], None],
                                        name: str | None = None) -> None:
        """
        Unregisters a screensaver_listener previously registered by
        register_screensaver_listener.
        Like register_screensaver_listener, if name is not specified the listener
        MUST have a __name__ or name attribute.

        :param listener:
        :param name: Same name as used for register_screensaver_listner, or None
        :return:
        """
        with cls._screen_saver_listener_lock:
            listener_name = cls.get_listener_name(listener, name)
            if listener_name in cls._screen_saver_listeners.keys():
                raise ValueError(f'Duplicate listener with name: {listener_name}')
            try:
                if listener in cls._screen_saver_listeners:
                    del cls._screen_saver_listeners[listener_name]
            except ValueError:
                pass

    @classmethod
    def register_settings_changed_listener(cls,
                                           listener: Callable[[None], None],
                                           name: str = None) -> None:
        """

        :param name:
        :param listener:
        :return:
        """
        with cls._settings_changed_listener_lock:
            if not (cls.is_abort_requested()
                    or listener in cls._settings_changed_listeners):
                listener_name = cls.get_listener_name(listener, name)

                cls._settings_changed_listeners[listener] = listener_name

    @classmethod
    def unregister_settings_changed_listener(cls,
                                             listener: Callable[[None], None]) -> None:
        """

        :param listener:
        :return:
        """
        with cls._settings_changed_listener_lock:
            try:
                if listener in cls._settings_changed_listeners:
                    del cls._settings_changed_listeners[listener]
            except ValueError:
                pass

    @classmethod
    def register_abort_listener(cls,
                                listener: Callable[[None], None],
                                name: str = None,
                                thread: threading.Thread | None = None) -> None:
        """
        Registers a listener to be informed of an abort/shutdown.
        Before the listener is called, any non-None thread is checked to see
        if it is still alive.

        :param listener:
        :param name:
        :param thread: thread to verify that it is alive prior to calling
        :return:

        TODO: Fix the garbage collect hang problem.
        """
        with cls._abort_listener_lock:
            if not (cls.is_abort_requested()
                    or listener in cls._abort_listeners):
                listener_name = cls.get_listener_name(listener, name)

                cls._abort_listeners[listener] = listener_name
            else:
                raise AbortException()

    @classmethod
    def unregister_abort_listener(cls,
                                  listener: Callable[[None], None]) -> None:
        """

        :param listener:
        :return:

        TODO: Fix the garbage collect problem
        """
        with cls._abort_listener_lock:
            try:
                if listener in cls._abort_listeners:
                    del cls._abort_listeners[listener]
            except ValueError:
                pass

    @classmethod
    def _inform_abort_listeners(cls) -> None:
        """

        :return:
        """
        listener = cls._inform_abort_listener_worker
        xbmc.log(f'Adding listener from_inform_abort_listeners '
                 f'listener: {listener}', xbmc.LOGDEBUG)
        cls._inform_abort_listeners_thread = threading.Thread(
                target=cls._listener_wrapper, name='infrm_listnrs',
                args=(), kwargs={'listener': listener})
        cls._inform_abort_listeners_thread.start()
        from common.garbage_collector import GarbageCollector
        GarbageCollector.add_thread(cls._inform_abort_listeners_thread)

    @classmethod
    def _inform_abort_listener_worker(cls) -> None:
        with cls._abort_listener_lock:
            if cls._abort_listeners_informed:
                return
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v('Entered')
            listeners_copy = copy.copy(cls._abort_listeners)
            cls._abort_listeners.clear()  # Unregister all
            cls._abort_listeners_informed = True

        for listener, listener_name in listeners_copy.items():
            # noinspection PyTypeChecker
            listener_name: str
            xbmc.log(f'Adding listener from_inform_abort_listener_worker '
                     f'listener: {listener_name} {listener}', xbmc.LOGDEBUG)
            thread = threading.Thread(
                    target=cls._listener_wrapper, name=listener_name,
                    args=(), kwargs={'listener': listener})
            if DEBUG_LOG:
                xbmc.log(f'SHUTDOWN Informing thread {listener_name} to shutdown')
            thread.start()
            from common.garbage_collector import GarbageCollector
            GarbageCollector.add_thread(thread)

        if DEBUG_LOG:
            xbmc.log(f'SHUTDOWN finished informing threads of shutdown')
        cls.startup_complete_event.set()
        if DEBUG_LOG:
            xbmc.log(f'SHUTDOWN startup_complete_event.set')
        with cls._settings_changed_listener_lock:
            if DEBUG_LOG:
                xbmc.log(f'SHUTDOWN about to clear settings_changed_listeners')
            cls._settings_changed_listeners.clear()
        if DEBUG_LOG:
            xbmc.log(f'SHUTDOWN finished settings_changed_listeners.clear()')

        with cls._screen_saver_listener_lock:
            if DEBUG_LOG:
                xbmc.log(f'SHUTDOWN About to clear screen_saver_listeners')
            cls._screen_saver_listeners.clear()
        if DEBUG_LOG:
            xbmc.log(f'SHUTDOWN LISTENER FINISHED')

    @classmethod
    def _listener_wrapper(cls, listener):
        try:
            if listener is not None:
                xbmc.log(f'_listener_wrapper listener type: {type(listener)} '
                         f'listener: {listener}',
                         xbmc.LOGDEBUG)
                xbmc.log(f'listener: {listener}', xbmc.LOGDEBUG)
                listener()
        except AbortException:
            pass
        except Exception as e:
            xbmc.log(f'Exception in _listener_wrapper listener: {listener} '
                     f'{e}', xbmc.LOGINFO)

    @classmethod
    def _inform_settings_changed_listeners(cls) -> None:
        """

        :return:
        """
        with cls._settings_changed_listener_lock:
            listeners = copy.copy(cls._settings_changed_listeners)
            if cls.is_abort_requested():
                cls._settings_changed_listeners.clear()

        for listener, listener_name in listeners.items():
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(
                        f'Notifying listener: {listener_name}')
            thread = threading.Thread(
                    target=listener, name=f'nform_{listener_name}')
            thread.start()
            from common.garbage_collector import GarbageCollector
            GarbageCollector.add_thread(thread)

    @classmethod
    def _inform_screensaver_listeners(cls,
                                      activated: bool = True) -> None:
        """

        :param activated:
        :return:
        """
        with cls._screen_saver_listener_lock:
            listeners_copy = copy.copy(cls._screen_saver_listeners)
            if cls.is_abort_requested():
                cls._screen_saver_listeners.clear()

        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'Screensaver activated: {activated}')
        for listener, listener_name in listeners_copy.items():
            thread = threading.Thread(
                    target=listener, name=f'nform_{listener_name}',
                    args=(activated,))
            thread.start()
            from common.garbage_collector import GarbageCollector
            GarbageCollector.add_thread(thread)

    def onSettingsChanged(self) -> None:
        """
        This method is called by xbmc when any settings have changed.

        Don't rely on xbmc.onSettingsChanged because we want to avoid changes to
        app settings based upon a user's incomplete changes. Instead, rely
        on _monitor_changes_in_settings, which waits a minute after settings.xml
        file is stable before notification.

        Real settings changed notification caused by on_settings_changed method.

        :return:
        """
        # type(self).on_settings_changed()
        pass

    @classmethod
    def on_settings_changed(cls) -> None:
        cls._inform_settings_changed_listeners()

    def onScreensaverActivated(self) -> None:
        """
        onScreensaverActivated method.

        Will be called when screensaver kicks in

        :return:
        """
        type(self)._inform_screensaver_listeners(activated=True)

        # return super().onScreensaverActivated()

    def onScreensaverDeactivated(self) -> None:
        """
        onScreensaverDeactivated method.

        Will be called when screensaver goes off

        :return:
        """
        type(self)._inform_screensaver_listeners(activated=False)

        # return super().onScreensaverDeactivated()

    @classmethod
    def register_notification_listener(cls,
                                       listener: Callable[[Dict[str, Any]], None],
                                       name: str = None) -> None:
        """

        :param listener:
        :param name:
        :return:
        """
        with cls._notification_listener_lock:
            if not (listener in cls._notification_listeners):
                listener_name = cls.get_listener_name(listener, name)
                cls._notification_listeners[listener] = listener_name

    @classmethod
    def _inform_notification_listeners(cls,
                                       sender: str, method: str,
                                       data: str = None) -> None:
        """
        Relays several "on" events: onNotification, onScreensaver*, onClean*,
        and onScan*.
        :param sender: Tags the message source. Usually ignored
        :param method: Tags the message type, informs how to process
        :param data: Holds the content of the message. May be json, or plain text
        :return:
        """

        with cls._notification_listener_lock:
            listeners_copy = copy.copy(cls._notification_listeners)
            if cls.is_abort_requested():
                cls._notification_listeners.clear()

        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'Notification received sender: {sender}'
                                      f' method: {method} data: {data}')
        for listener, listener_name in listeners_copy.items():
            try:
                cls.runInThread(listener, [], name=listener_name,
                                **{'sender': sender, 'method': method, 'data': data})
            except Exception as e:
                MY_LOGGER.exception('')

    def waitForAbort(self, timeout: float | None = None) -> bool:
        """
        #
        # Provides signature of super class (xbmc.Monitor)
        #
        # Only real_waitForAbort() calls xbmc.Monitor.waitForAbort, which is
        # called only by back_end_service, front_end_service or screensaver and
        # only from the main thread.
        #
        # WaitForAbort and wait_for_abort depend upon _abort_received
         :param timeout: [opt] float - timeout in seconds.
                        if -1 or None: wait forever
                        if 0: check without wait & return
                        if > 0: wait at max wait seconds
        """

        clz = type(self)
        if timeout is not None and timeout < 0.0:
            timeout = None

        #  Use xbmc wait for long timeouts so that the wait time is better
        #  shared with other threads, etc.

        if timeout is None or 0.0 < timeout > 0.2:
            abort = self.real_waitForAbort(timeout=timeout)
        else:
            abort = clz._abort_received.wait(timeout=timeout)
        #  clz.track_wait_return_counts()

        return abort

    @classmethod
    def wait_for_abort(cls, timeout: float | None = None) -> bool:
        """
        Wait for Abort

        Block until abort is requested, or until timeout occurs. If an abort
        requested have already been made, return immediately.

        :param timeout: [opt] float - timeout in seconds. Default: no timeout.
        :return: True when abort has been requested,
            False if a timeout is given and the operation times out.

        """
        if timeout is None or timeout < 0.0:
            timeout = cls.FOREVER

        #  Use xbmc wait for long timeouts so that the wait time is better
        #  shared with other threads, etc.

        abort: bool = False
        if timeout > 0.21:
            abort = cls.real_waitForAbort(timeout=timeout)
        else:
            while timeout > 0.0:
                poll_delay: float = min(timeout, CriticalSettings.SHORT_POLL_DELAY)
                if cls._abort_received.wait(timeout=poll_delay):
                    abort = True
                    break
                timeout -= poll_delay
        return abort

    @classmethod
    def is_abort_requested(cls) -> bool:
        """
        Returns True if abort has been requested.

        :return: True if requested

        New function added.
        """
        return cls._abort_received.is_set()

    @classmethod
    def set_startup_complete(cls) -> None:
        """

        :return:
        """
        cls.startup_complete_event.set()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(
                    'startup_complete_event set', trace=Trace.TRACE_MONITOR)

    @classmethod
    def is_startup_complete(cls) -> bool:
        """

        :return:
        """
        return cls.startup_complete_event.is_set()

    @classmethod
    def wait_for_startup_complete(cls, timeout: float = None) -> bool:
        """

        :param timeout:
        :return:
        """
        is_set = False
        approximate_wait_time = 0.0
        while not is_set:
            is_set = cls.startup_complete_event.wait(timeout=None)
            #  cls.track_wait_call_counts()
            Monitor.real_waitForAbort(timeout=0.2)
            # Monitor.exception_on_abort(timeout=0.2)
            #  cls.track_wait_return_counts()
            approximate_wait_time += 0.2
            if timeout is not None and approximate_wait_time >= timeout:
                break

        return is_set

    '''
    @classmethod
    def track_wait_call_counts(cls, thread_name: str = None) -> None:
        if thread_name is None:
            thread_name = threading.current_thread().name
        # xbmc.log('track_wait_call_counts thread: ' + thread_name, xbmc.LOGDEBUG)

        if thread_name is None:
            thread_name = threading.current_thread().name

        count = cls._wait_call_count_map.get(thread_name, None)
        if count is None:
            count = 1
        else:
            count += 1

        cls._wait_call_count_map[thread_name] = count
        #  cls.dump_wait_counts()

    @classmethod
    def track_wait_return_counts(cls, thread_name: str = None) -> None:
        return

        if thread_name is None:
            thread_name = threading.current_thread().name
        # xbmc.log('track_wait_return_counts thread: ' + thread_name, xbmc.LOGDEBUG)

        if thread_name is None:
            thread_name = threading.current_thread().name

        count = cls._wait_return_count_map.get(thread_name, None)
        if count is None:
            count = 1
        else:
            count += 1

        cls._wait_return_count_map[thread_name] = count
        #    cls.dump_wait_counts()

    @classmethod
    def dump_wait_counts(cls) -> None:
        return

        xbmc.log('Wait Call Map', xbmc.LOGDEBUG)
        for k, v in cls._wait_call_count_map.items():
            xbmc.log(str(k) + ': ' + str(v), xbmc.LOGDEBUG)

        xbmc.log('Wait Return Map', xbmc.LOGDEBUG)
        for k, v in cls._wait_return_count_map.items():
            xbmc.log(str(k) + ': ' + str(v), xbmc.LOGDEBUG)

    '''

# Initialize class:
#
Monitor.class_init()
