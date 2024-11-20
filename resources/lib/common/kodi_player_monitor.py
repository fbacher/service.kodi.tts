# coding=utf-8
from __future__ import annotations  # For union operator |

import sys

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from xbmc import Player

from common import *

from common.monitor import *
from utils.util import runInThread

module_logger = BasicLogger.get_logger(__name__)


class KodiPlayerState(StrEnum):
    '''
    Possible states of interest for Kodi movie/audio player
    '''

    UNINITALIZED = 'uninitialized'  # Indicates monitoring code yet to start
    # initialization
    INITIALIZING = 'initializing'  # Initialization of monitor in progress
    PLAYING_VIDEO = 'playing_video'  # Actively playing audio/video/picture
    #  PLAYING_STARTED = 'started'
    VIDEO_PLAYER_IDLE = 'video_player_idle'  # Kodi player is idle


class KodiPlayerMonitorListener:

    def __init__(self, listener: Callable[[KodiPlayerState], bool]):
        self.listener: Callable[[KodiPlayerState], bool] = listener
        # self.delete_after_call: bool = delete_after_call


class KodiPlayerMonitor(Player):
    _player_status_listeners: Dict[str, KodiPlayerMonitorListener] = {}
    _player_status_lock: threading.RLock = threading.RLock()
    _player_state: KodiPlayerState = KodiPlayerState.VIDEO_PLAYER_IDLE
    _logger: BasicLogger = None
    _instance: 'KodiPlayerMonitor' = None

    def __init__(self) -> None:
        super().__init__()
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
        self.playing: bool = False

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = KodiPlayerMonitor()
            args = []
            runInThread(cls._instance.poll_for_change, args, name='plyrMon',
                        delay=0.0)
        return cls._instance

    def poll_for_change(self) -> None:
        clz = type(self)
        was_playing: bool | None = None
        while not Monitor.wait_for_abort(0.2):
            try:
                playing: bool = self.isPlaying()
                if playing != was_playing:
                    video_player_state: KodiPlayerState
                    if playing:
                        video_player_state = KodiPlayerState.PLAYING_VIDEO
                    else:
                        video_player_state = KodiPlayerState.VIDEO_PLAYER_IDLE
                    clz._inform_player_status_listeners(video_player_state)
                    was_playing = playing
            except AbortException:
                return  # Let thread die

    @classmethod
    def stop_audio(cls):
        cls._inform_player_status_listeners(KodiPlayerState.VIDEO_PLAYER_IDLE)

    @classmethod
    def register_player_status_listener(cls, listener: Callable[[KodiPlayerState], bool],
                                        listener_id: str) -> None:
        """

        :param listener:
        :param listener_id:
        :return:
        """
        with cls._player_status_lock:
            if not (
                    Monitor.is_abort_requested() or listener_id in
                    cls._player_status_listeners):
                kodi_player_listener = KodiPlayerMonitorListener(listener)
                cls._player_status_listeners[listener_id] = kodi_player_listener

    @classmethod
    def unregister_player_status_listener(cls, listener_id: str) -> None:
        """

        :param listener_id:
        :return:
        """
        with cls._player_status_lock:
            try:
                if listener_id in cls._player_status_listeners:
                    del cls._player_status_listeners[listener_id]
            except ValueError:
                pass

    @classmethod
    def _inform_player_status_listeners(cls, status: KodiPlayerState) -> None:
        """

        :return:
        """
        cls._player_state = status

        with cls._player_status_lock:
            if Monitor.is_abort_requested():
                cls._player_status_listeners.clear()
                return
            listeners = copy.copy(cls._player_status_listeners)

        listener_id: str
        listener: KodiPlayerMonitorListener
        for listener_id, listener in listeners.items():
            if cls._logger.isEnabledFor(DEBUG_V):
                cls._logger.debug_v(f'Notifying listener: {listener_id} '
                                          f'status: {status}',
                                    trace=Trace.TRACE_AUDIO_START_STOP)
            try:
                Monitor.exception_on_abort()
                delete_after_call = listener.listener(status)
                with cls._player_status_lock:
                    if delete_after_call:
                        del cls._player_status_listeners[listener_id]

            except AbortException:
                reraise(*sys.exc_info())
            except Exception as e:
                cls._logger.exception('')

    @classmethod
    @property
    def player_status(cls) -> KodiPlayerState:
        return cls._player_state

    @property
    def play_state(self) -> str:
        clz = type(self)

        if xbmc.getCondVisibility('Player.Playing'):
            play_state = 'playing'
        elif xbmc.getCondVisibility('Player.Paused'):
            play_state = 'paused'
        else:
            play_state = 'stopped'
        clz._logger.debug_xv('play_state: ' + play_state)
        # self._dump_state()  # TODO: remove
        return play_state

    def isPlaying(self) -> bool:
        """
        Check Kodi is playing something.

        :return: True if Kodi is playing a file.
        """
        return super().isPlaying()

    def onPlayBackStarted(self) -> None:
        """
        onPlayBackStarted method.

        Will be called when Kodi player starts. Video or audio might not be available at
        this point.

        @python_v18 Use `onAVStarted()` instead if you need to detect if Kodi is actually
        playing a media file (i.e, if a stream is available)
        """
        clz = type(self)
        clz._logger.debug(f'onPlayBackStarted')

    def onAVStarted(self) -> None:
        """
        onAVStarted method.

        Will be called when Kodi has a video or audiostream.

        @python_v18 New function added.
        """
        clz = type(self)
        clz._logger.debug(f'onAVStarted')
        clz._inform_player_status_listeners(KodiPlayerState.PLAYING_VIDEO)

    def onAVChange(self) -> None:
        """
        onAVChange method.

        Will be called when Kodi has a video, audio or subtitle stream. Also happens
        when the stream changes.

        @python_v18 New function added.
        """
        clz = type(self)
        clz._logger.debug(f'onAVChange')
        clz._inform_player_status_listeners(KodiPlayerState.PLAYING_VIDEO)


instance: KodiPlayerMonitor = KodiPlayerMonitor.instance()
