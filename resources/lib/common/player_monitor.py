# coding=utf-8
from enum import auto

from xbmc import Player

from common.monitor import *
from utils.util import runInThread

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class PlayerState:
    PLAYING = 'playing'
    #  PLAYING_STARTED = 'started'
    PLAYING_STOPPED = 'stopped'


class PlayerMonitor(Player):
    _player_status_listeners: Dict[Callable[[None], PlayerState], str] = {}
    _player_status_lock: threading.RLock = threading.RLock()
    _player_state: str = PlayerState.PLAYING_STOPPED

    _logger: BasicLogger = None
    _instance: 'PlayerMonitor' = None

    def __init__(self) -> None:
        super().__init__()
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.playing: bool = False

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = PlayerMonitor()
            args = []
            runInThread(cls._instance.poll_for_change, args, name='player_monitor',
                        delay=0.0)
        return cls._instance

    def poll_for_change(self) -> None:
        clz = type(self)
        old_seconds: float = 0.0
        was_playing: bool = False
        while True:
            Monitor.exception_on_abort(0.2)
            changed: bool = False
            playing = self.isPlaying()
            if playing != was_playing:
                player_state: str
                if playing:
                    player_state = PlayerState.PLAYING
                else:
                    player_state = PlayerState.PLAYING_STOPPED
                clz._inform_player_status_listeners(player_state)
                was_playing = playing


    @classmethod
    def get_listener_name(cls, listener: Callable[[None], None], name: str = None) -> str:
        listener_name: str = 'unknown'
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

        return listener_name

    @classmethod
    def register_player_status_listener(cls, listener: Callable[[PlayerState], None],
                                        name: str = None) -> None:
        """

        :param listener:
        :param name:
        :return:
        """
        with cls._player_status_lock:
            if not (
                    Monitor.is_abort_requested() or listener in
                    cls._player_status_listeners):
                listener_name = cls.get_listener_name(listener, name)

                cls._player_status_listeners[listener] = listener_name

    @classmethod
    def unregister_player_status_listener(cls, listener: Callable[
        [PlayerState], None]) -> None:
        """

        :param listener:
        :return:
        """
        with cls._player_status_lock:
            try:
                if listener in cls._player_status_listeners:
                    del cls._player_status_listeners[listener]
            except ValueError:
                pass

    @classmethod
    def _inform_player_status_listeners(cls, status: str) -> None:
        """

        :return:
        """
        cls._player_state = status

        with cls._player_status_lock:
            listeners = copy.copy(cls._player_status_listeners)
            if Monitor.is_abort_requested():
                cls._player_status_listeners.clear()

        for listener, listener_name in listeners.items():
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug_verbose(f'Notifying listener: {listener_name} '
                                          f'status: {status}',
                                          trace=Trace.TRACE_AUDIO_START_STOP)
                listener(status)

    @classmethod
    @property
    def player_status(cls):
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
        clz._logger.debug_extra_verbose('play_state: ' + play_state)
        # self._dump_state()  # TODO: remove
        return play_state

    '''
    def play(self, item: Union[str,  'PlayList'] = "",
             listitem: Optional['xbmcgui.ListItem'] = None,
             windowed: bool = False,
             startpos: int = -1) -> None:
    
        Play an item.

        :param item: [opt] string - filename, url or playlist
        :param listitem: [opt] listitem - used with setInfo() to set different infolabels.
        :param windowed: [opt] bool - true=play video windowed, false=play users
            preference.(default)
        :param startpos: [opt] int - starting position when playing a playlist. Default 
        = -1

        .. note::
            If item is not given then the `Player` will try to play the current
            item in the current playlist.   You can use the above as keywords
            for arguments and skip certain optional arguments.  Once you use a
            keyword, all following arguments require the keyword.

        Example::

            ...
            listitem = xbmcgui.ListItem('Ironman')
            listitem.setInfo('video', {'Title': 'Ironman', 'Genre': 'Science Fiction'})
            xbmc.Player().play(url, listitem, windowed)
            xbmc.Player().play(playlist, listitem, windowed, startpos)
            ...
        """
        pass

    def stop(self) -> None:
        """
        Stop playing.
        """
        pass

    def pause(self) -> None:
        """
        Pause or resume playing if already paused.
        """
        pass

    def playnext(self) -> None:
        """
        Play next item in playlist.
        """
        pass

    def playprevious(self) -> None:
        """
        Play previous item in playlist.
        """
        pass

    def playselected(self, selected: int) -> None:
        """
        Play a certain item from the current playlist.

        :param selected: Integer - Item to select
        """
        pass
    '''

    def isPlaying(self) -> bool:
        """
        Check Kodi is playing something.

        :return: True if Kodi is playing a file.
        """
        return super().isPlaying()

    '''
    def isPlayingAudio(self) -> bool:
        """
        Check for playing audio.

        :return: True if Kodi is playing an audio file.
        """
        return True

    def isPlayingVideo(self) -> bool:
        """
        Check for playing video.

        :return: True if Kodi is playing a video.
        """
        return True

    def isPlayingRDS(self) -> bool:
        """
        Check for playing radio data system (RDS).

        :return: True if kodi is playing a radio data system (RDS).
        """
        return True

    def isExternalPlayer(self) -> bool:
        """
        Check for external player.

        :return: True if kodi is playing using an external player.

        @python_v18 New function added.
        """
        return True

    def getPlayingFile(self) -> str:
        """
        Returns the current playing file as a string.

        .. note::
            For LiveTV, returns a **pvr://** url which is not translatable to
            an OS specific file or external url.

        :return: Playing filename
        :raises Exception: If player is not playing a file.
        """
        return ""

    def getPlayingItem(self) -> 'xbmcgui.ListItem':
        """
        Returns the current playing item.

        :return: Playing item
        :raises Exception: If player is not playing a file.

        @python_v20 New function added.
        """
        from xbmcgui import ListItem
        return ListItem()

    def getTime(self) -> float:
        """
        Get playing time.

        Returns the current time of the current playing media as fractional seconds.

        :return: Current time as fractional seconds
        :raises Exception: If player is not playing a file.
        """
        return 0.0

    def seekTime(self, seekTime: float) -> None:
        """
        Seek time.

        Seeks the specified amount of time as fractional seconds. The time specified is
        relative to the beginning of the currently. playing media file.

        :param seekTime: Time to seek as fractional seconds
        :raises Exception: If player is not playing a file.
        """
        pass

    def setSubtitles(self, subtitleFile: str) -> None:
        """
        Set subtitle file and enable subtitles.

        :param subtitleFile: File to use as source ofsubtitles
        """
        pass

    def showSubtitles(self, bVisible: bool) -> None:
        """
        Enable / disable subtitles.

        :param visible: [boolean] True for visible subtitles.

        Example::

            ...
            xbmc.Player().showSubtitles(True)
            ...
        """
        pass

    def getSubtitles(self) -> str:
        """
        Get subtitle stream name.

        :return: Stream name
        """
        return ""

    def getAvailableSubtitleStreams(self) -> List[str]:
        """
        Get Subtitle stream names.

        :return: `List` of subtitle streams as name
        """
        return [""]

    def setSubtitleStream(self, iStream: int) -> None:
        """
        Set Subtitle Stream.

        :param iStream: [int] Subtitle stream to select for play

        Example::

            ...
            xbmc.Player().setSubtitleStream(1)
            ...
        """
        pass

    def updateInfoTag(self, item: 'xbmcgui.ListItem') -> None:
        """
        Update info labels for currently playing item.

        :param item: ListItem with new info
        :raises Exception: If player is not playing a file

        @python_v18 New function added.

        Example::

            ...
            item = xbmcgui.ListItem()
            item.setPath(xbmc.Player().getPlayingFile())
            item.setInfo('music', {'title' : 'foo', 'artist' : 'bar'})
            xbmc.Player().updateInfoTag(item)
            ...
        """
        pass

    def getVideoInfoTag(self) -> InfoTagVideo:
        """
        To get video info tag.

        Returns the VideoInfoTag of the current playing Movie.

        :return: Video info tag
        :raises Exception: If player is not playing a file or current file is not a 
        movie file.
        """
        return InfoTagVideo()

    def getMusicInfoTag(self) -> InfoTagMusic:
        """
        To get music info tag.

        Returns the MusicInfoTag of the current playing 'Song'.

        :return: Music info tag
        :raises Exception: If player is not playing a file or current file is not a 
        music file.
        """
        return InfoTagMusic()

    def getRadioRDSInfoTag(self) -> InfoTagRadioRDS:
        """
        To get Radio RDS info tag

        Returns the RadioRDSInfoTag of the current playing 'Radio Song if. present'.

        :return: Radio RDS info tag
        :raises Exception: If player is not playing a file or current file is not a rds 
        file.
        """
        return InfoTagRadioRDS()
    '''

    def getTotalTime(self) -> float:
        """
        To get total playing time.

        Returns the total time of the current playing media in seconds. This is only
        accurate to the full second.

        :return: Total time of the current playing media
        :raises Exception: If player is not playing a file.
        """
        clz = type(self)
        result: float = super().getTotalTime()
        clz._logger.debug(f'getTotalTime: {result:d}')

    '''
    def getAvailableAudioStreams(self) -> List[str]:
        """
        Get Audio stream names

        :return: `List` of audio streams as name
        """
        return [""]

    def setAudioStream(self, iStream: int) -> None:
        """
        Set Audio Stream.

        :param iStream: [int] Audio stream to select for play

        Example::

            ...
            xbmc.Player().setAudioStream(1)
            ...
        """
        pass

    def getAvailableVideoStreams(self) -> List[str]:
        """
        Get Video stream names

        :return: `List` of video streams as name
        """
        return [""]

    def setVideoStream(self, iStream: int) -> None:
        """
        Set Video Stream.

        :param iStream: [int] Video stream to select for play

        Example::

            ...
            xbmc.Player().setVideoStream(1)
            ...
        """
        pass
    '''

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
        clz._inform_player_status_listeners(PlayerState.PLAYING)

    def onAVChange(self) -> None:
        """
        onAVChange method.

        Will be called when Kodi has a video, audio or subtitle stream. Also happens
        when the stream changes.

        @python_v18 New function added.
        """
        clz = type(self)
        clz._logger.debug(f'onAVChange')
        clz._inform_player_status_listeners(PlayerState.PLAYING)

    '''
    def onPlayBackEnded(self) -> None:
        """
        onPlayBackEnded method.

        Will be called when Kodi stops playing a file.
        """
        clz = type(self)
        clz._logger.debug(f'onPlaybackEnded')

    def onPlayBackStopped(self) -> None:
        """
        onPlayBackStopped method.

        Will be called when user stops Kodi playing a file.
        """
        clz = type(self)
        clz._logger.debug(f'onPlayBackStopped')


    def onPlayBackError(self) -> None:
        """
        onPlayBackError method.

        Will be called when playback stops due to an error.
        """
        pass

    def onPlayBackPaused(self) -> None:
        """
        onPlayBackPaused method.

        Will be called when user pauses a playing file.
        """
        pass

    def onPlayBackResumed(self) -> None:
        """
        onPlayBackResumed method.

        Will be called when user resumes a paused file.
        """
        pass

    def onQueueNextItem(self) -> None:
        """
        onQueueNextItem method.

        Will be called when user queues the next item.
        """
        pass

    def onPlayBackSpeedChanged(self, speed: int) -> None:
        """
        onPlayBackSpeedChanged method.

        Will be called when players speed changes (eg. user FF/RW).

        :param speed: [integer] Current speed of player

        .. note::
            Negative speed means player is rewinding, 1 is normal playback
            speed.
        """
        pass

    def onPlayBackSeek(self, time: int, seekOffset: int) -> None:
        """
        onPlayBackSeek method.

        Will be called when user seeks to a time.

        :param time: [integer] Time to seek to
        :param seekOffset: [integer] ?
        """
        pass

    def onPlayBackSeekChapter(self, chapter: int) -> None:
        """
        onPlayBackSeekChapter method.

        Will be called when user performs a chapter seek.

        :param chapter: [integer] Chapter to seek to
        """
        pass
    '''


instance: PlayerMonitor = PlayerMonitor.instance()
