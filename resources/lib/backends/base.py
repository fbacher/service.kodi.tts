# -*- coding: utf-8 -*-
from backends.__init__ import *
import time
import threading
import queue
import os

from backends.i_tts_backend_base import ITTSBackendBase
from backends.tts_backend_bridge import TTSBackendBridge
from backends.constraints import Constraints
from backends import audio
from backends.audio import AudioPlayer, BuiltInAudioPlayer, PlayerHandlerType
from cache.voicecache import VoiceCache
from common.settings import Settings
from common.setting_constants import Genders
from common.constants import Constants
from common.logger import *
from common.messages import Messages
from common.monitor import my_monitor
from common import utils

import xbmc

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class TTSBackendBase(ITTSBackendBase):
    """The base class for all speech engine backends

    Subclasses must at least implement the say() method, and can use whatever
    means are available to speak text.
    """
    backend_id = 'auto'
    displayName: str = 'Auto'
    pauseInsert = '...'
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False
    # Min, Default, Max, Integer_Only (no float)
    speedConstraints: Constraints = Constraints(0, 0, 0, True)
    pitchConstraints: Constraints = Constraints(0, 0, 0, True)

    # Volume constraints imposed by the api being called

    volumeConstraints: Constraints = Constraints(-12, 0, 12, True)

    # Volume scale as presented to the user

    volumeExternalEndpoints = (-12, 12)
    volumeStep = 1
    volumeSuffix = 'dB'
    speedInt = True
    # _loadedSettings = {}
    _logger = module_logger.getChild('TTSBackendBase')  # type: BasicLogger
    dead = False  # Backend should flag this true if it's no longer usable
    deadReason = ''  # Backend should set this reason when marking itself dead
    _closed = False
    currentBackend = None
    #  currentSettings = []
    settings: Dict[str, Any | None] = {}
    constraints: Dict[str, Constraints] = {}

    _class_name: str = None
    initialized_static: bool = False
    player_handler_class: audio.BasePlayerHandler = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(type(self)._class_name)
        self.initialized = False
        self.voice: str | None = None
        self.volume: float = 0.0
        self.rate: float = 0.0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._close()

    def re_init(self):
        self.initialized = False
        self.init()

    def init(self):
        pass

    def get_player_handler(self) -> AudioPlayer:
        raise Exception('Not Implemented')

    def setWavStreamMode(self, enable=True):
        self.inWavStreamMode = enable

    def scaleSpeed(self, value, limit):  # Target is between -20 and 20
        return self.scaleValue(value, self.speedConstraints, limit)

    def scalePitch(self, value, limit):  # Target is between -20 and 20
        return self.scaleValue(value, self.pitchConstraints, limit)

    def scaleVolume(self, value, limit):
        return self.scaleValue(value, self.volumeConstraints, limit)

    # speedConstraints = (80, 175, 450, True)

    def scaleValue(self, value: float, constraints: Constraints, limit: float) -> float:
        adj: float
        scale: float
        new: float
        if value < 0:
            adj = constraints.default - constraints.minimum
            scale = (limit + value) / float(limit)
            new = scale * adj
            new += constraints.minimum
        elif value > 0:
            adj = constraints.maximum - constraints.default
            scale = value / float(limit)
            new = scale * adj
            new += constraints.default
        else:
            new = constraints.default

        if constraints.integer:
            return int(new)
        return new

    def scale_db_to_percent(self, value, lower_bound=0, upper_bound=100):
        scaled_value = int(round(100 * (10 ** (value / 20.0))))
        scaled_value = max(scaled_value, lower_bound)
        scaled_value = min(scaled_value, upper_bound)
        return scaled_value

    def volumeUp(self) -> str:
        clz = type(self)
        if not self.settings or not Settings.VOLUME in self.settings:
            return Messages.get_msg(Messages.CANNOT_ADJUST_VOLUME)
        vol = type(self).getSetting(Settings.VOLUME)
        max_volume: int = self.volumeExternalEndpoints[1]
        volume_step: int = self.volumeStep
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug(f'Volume UP: {vol} Upper Limit: {max_volume} '
                              f'step {self.volumeStep}')
        vol += volume_step
        if vol > max_volume:
            volume_step = volume_step - (vol - max_volume)
            vol = max_volume
        self.setSetting(Settings.VOLUME, vol)
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug('Volume UP: {0}'.format(vol))
        return f'Volume Up by {volume_step} now {vol} {self.volumeSuffix}'

    def volumeDown(self) -> str:
        clz = type(self)
        if not self.settings or not Settings.VOLUME in self.settings:
            return Messages.get_msg(Messages.CANNOT_ADJUST_VOLUME)
        min_volume: int = self.volumeExternalEndpoints[0]
        volume_step: int = self.volumeStep
        vol = clz.getSetting(Settings.VOLUME)
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug(f'Volume Down: {vol} Lower Limit: {min_volume} '
                              f'step {volume_step}')
        vol -= volume_step
        if vol < min_volume:
            volume_step = volume_step - (min_volume - vol)
            vol = min_volume
        self.setSetting(Settings.VOLUME, vol)
        if type(self)._logger.isEnabledFor(DEBUG):
            type(self)._logger.debug('Volume DOWN: {0}'.format(vol))
        return f'Volume Down by {volume_step} now {vol} {self.volumeSuffix}'

    def flagAsDead(self, reason=''):
        self.dead = True
        self.deadReason = reason or self.deadReason

    def say(self, text, interrupt=False, preload_cache=False):
        """Method accepting text to be spoken

        Must be overridden by subclasses.
        text is unicode and the text to be spoken.
        If interrupt is True, the subclass should interrupt all previous speech.

        """
        raise Exception('Not Implemented')

    def sayList(self, texts, interrupt=False):
        """Accepts a list of text strings to be spoken

        May be overriden by subclasses. The default implementation calls say()
        for each item in texts, calling insertPause() between each.
        If interrupt is True, the subclass should interrupt all previous speech.
        """
        self.say(texts.pop(0), interrupt=interrupt)
        for t in texts:
            self.insertPause()
            self.say(t)

    @classmethod
    def get_pitch_constraints(cls) -> Constraints:
        return cls.pitchConstraints

    @classmethod
    def get_volume_constraints(cls) -> Constraints:
        return cls.volumeConstraints

    @classmethod
    def get_speed_constraints(cls) -> Constraints:
        return cls.speedConstraints

    @classmethod
    def isSettingSupported(cls, setting):
        if setting in cls.settings.keys():
            return True
        return False

    @classmethod
    def getSettingNames(cls) -> List[str]:
        """
        Gets a list of all of the setting names/keys that this backend uses

        :return:
        """
        settingNames: List[str] = []
        for settingName in cls.settings.keys():
            # settingName = settingName + '.' + cls.backend_id
            settingNames.append(settingName)

        return settingNames

    @classmethod
    def get_setting_default(cls, setting) ->\
            int | float | bool | str | float | List[int] | List[str] | List[bool] \
            | List[float] | None:
        default = None
        if setting in cls.settings.keys():
            setting: str
            default = cls.settings.get(setting, None)
        return default

    @classmethod
    def getConstraints(cls, setting_id: str) -> Constraints | None:
        return cls.constraints.get(setting_id)

    @classmethod
    def negotiate_engine_config(cls, backend_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        """
        Player is informing engine what it is capable of controlling
        Engine replies what it is allowing engine to control
        """
        return False, False, False

    @classmethod
    def settingList(cls, setting, *args):
        """Returns a list of options for a setting

        May be overridden by subclasses. Default implementation returns None.
        """
        return None

    @classmethod
    def setting(cls, setting):

        #  TODO: Replace with getSetting
        """Returns a backend setting, or default if not set
        """
        return cls.getSetting(setting, cls.get_setting_default(setting))

        # cls._loadedSettings[setting] = cls.getSetting(
        #     setting, cls.get_setting_default(setting))
        # return cls._loadedSettings[setting]

    #  @classmethod
    #  def initSettings(cls, newSettings):
    #      if cls.currentBackend != Settings.getSetting(Settings.BACKEND):
    #          for currentSetting in TTSBackendBase.currentSettings:
    #              Settings.setSetting(currentSetting, None)
    #          TTSBackendBase.currentSettings.clear()
    #
    #          for currentSetting in newSettings:
    #              currentValue = Settings.getSetting(
    #                  currentSetting + '.' + cls.backend_id)
    #              Settings.setSetting(currentSetting, currentValue)
    #              TTSBackendBase.currentSettings.append(currentSetting)

    @classmethod
    def getLanguage(cls):
        default_locale = Constants.LOCALE.lower().replace('_', '-')
        return cls.getSetting(Settings.LANGUAGE, default_locale)

    @classmethod
    def getGender(cls):
        gender = cls.getSetting(Settings.GENDER, Genders.UNKNOWN)

        return gender

    @classmethod
    def getVoice(cls):
        voice = cls.getSetting(Settings.VOICE, Settings.UNKNOWN_VALUE)

        return voice

    @classmethod
    def getSpeed(cls):
        speed = cls.getSetting(Settings.SPEED, cls.speedConstraints.default)
        speed = int(speed)
        if speed not in range(cls.speedConstraints.minimum, cls.speedConstraints.maximum + 1):
            speed = cls.speedConstraints.default
        return speed

    @classmethod
    def getPitch(cls):
        pitch = cls.getSetting(Settings.PITCH, cls.pitchConstraints.default)
        pitch = int(pitch)
        if pitch not in range(cls.pitchConstraints.minimum, cls.pitchConstraints.maximum + 1):
            pitch = cls.pitchConstraints.default
        return pitch

    @classmethod
    def getVolume(cls) -> int:
        volume = cls.getSetting(Settings.VOLUME, cls.volumeConstraints.default)
        volume = int(volume)
        if volume not in range(cls.volumeConstraints.minimum, cls.volumeConstraints.maximum + 1):
            volume = cls.volumeConstraints.default
        return volume

    @classmethod
    def setPlayerSpeed(cls, speed: float) -> None:
        # Native ResponsiveVoice speed is 1 .. 100, with default of 50,
        # but this has been scaled to be a %, so we see 0.01 .. 1.00
        # Therefore 0.5 is a speed of 1x
        # Multiplying by 2 gives:
        #   speed : 0.5 => player_speed of 1x
        #   speed : 0.25 => player_speed of 1/2 x
        #   speed : 0.1 => player_speed of 1/10 x
        #   speed : .75 => player_seed of 1.5x
        #
        # Player_speed scale is 3 .. 30 where actual play speed is player_speed / 10

        player_speed: float = float(speed * 2.0)
        if player_speed < 0.30:
            player_speed = 0.30  # 1/3 x
        elif player_speed > 1.5:
            player_speed  = player_speed * 1.5 # 2 * 1.5 = 3.0

        int_player_speed: int = int(player_speed * 10)
        Settings.setSetting(Settings.PLAYER_SPEED, int_player_speed,
                            backend_id=cls.backend_id)

    @classmethod
    def getSetting(cls, key, default=None):
        """
        Gets a setting from addon's settings.xml

        A convenience method equivalent to Settings.getSetting(key + '.'. + cls.backend_id,
        default, useFullSettingName).

        :param key:
        :param default:
        :param useFullSettingName:
        :return:
        """
        if default is None:
            default = cls.get_setting_default(key)

        return Settings.getSetting(key, cls.backend_id, default)

        # cls._loadedSettings[fully_qualified_key] = Settings.getSetting(
        #     fully_qualified_key, default)
        # return cls._loadedSettings[fully_qualified_key]

    @classmethod
    def setSetting(cls,
                   setting_id: str,
                   value: Union[None, str, List, bool, int, float]
                   ) -> bool:
        """
        Saves a setting to addon's settings.xml

        A convenience method for Settings.setSetting(key + '.' + cls.backend_id, value)

        :param setting_id:
        :param value:
        :return:
        """
        if (not cls.isSettingSupported(setting_id)
                and cls._logger.isEnabledFor(WARNING)):
            cls._logger.warning('Setting: {}, not supported by voicing engine: {}'
                                .format(setting_id, cls.get_backend_id()))
        previous_value = Settings.getSetting(setting_id, cls.get_backend_id(),  None)
        changed = False
        if previous_value != value:
            changed = True
        Settings.setSetting(setting_id, value, cls.backend_id)
        return changed

    @classmethod
    def get_player_setting(cls, default:str | None = None) -> str | None:
        if default is None:
            default = cls.get_setting_default(Settings.PLAYER)

        player_setting: str = Settings.get_player(default, cls.backend_id)
        return player_setting

    @classmethod
    def set_player_setting(cls, value: str) -> bool:
        backend_id: str = cls.get_backend_id()
        if (not cls.isSettingSupported(Settings.PLAYER)
                and cls._logger.isEnabledFor(WARNING)):
            cls._logger.warning(f'{Settings.PLAYER}, not supported by voicing engine: '
                                f'{backend_id}')
        previous_value = Settings.get_player(default_value=None, backend_id=backend_id)
        changed = previous_value != value
        Settings.set_player(value, backend_id)
        return changed

    @classmethod
    def get_backend_id(cls) -> str:
        return cls.backend_id

    def insertPause(self, ms=500):
        """Insert a pause of ms milliseconds

        May be overridden by sublcasses. Default implementation sleeps for ms.
        """
        xbmc.sleep(ms)

    def isSpeaking(self):
        """Returns True if speech engine is currently speaking, False if not
        and None if unknown

        Subclasses should override this accordingly
        """
        return None

    def getWavStream(self, text):
        """Returns an open file like object containing wav data

        Subclasses should override this to provide access to functions
        that require this functionality
        """
        return None

    def update(self):
        """Called when the user has changed a setting for this backend

        Subclasses should override this to react to user changes.
        """
        pass

    def stop(self):
        """Stop all speech, implicitly called when close() is called

        Subclasses should override this to respond to requests to stop speech.
        Default implementation does nothing.
        """
        pass

    def close(self):
        """Close the speech engine

        Subclasses should override this to clean up after themselves.
        Default implementation does nothing.
        """
        pass

    def _update(self):
        changed = self._updateSettings()
        if changed:
            return self.update()

    def _updateSettings(self):
        if not self.settings:
            return None
        # if not hasattr(self, '_loadedSettings'):
        #    self._loadedSettings = {}
        changed = False
        # for s in self.settings:
        #    old = self._loadedSettings.get(s)
        #    new = type(self).getSetting(s)
        #    if old is not None and new != old:
        #        changed = True
        return changed

    def _stop(self):
        self.stop()

    def _close(self):
        self._closed = True
        self._stop()
        self.close()

    @classmethod
    def is_available_and_usable(cls):
        return cls._available()

    @classmethod
    def _available(cls):
        if cls.broken and Settings.getSetting(Settings.DISABLE_BROKEN_BACKENDS,
                                              cls.get_backend_id(), True):
            return False
        return cls.available()

    @staticmethod
    def available():
        """Static method representing the the speech engines availability

        Subclasses should override this and return True if the speech engine is
        capable of speaking text in the current environment.
        Default implementation returns False.
        """
        return False


class ThreadedTTSBackend(TTSBackendBase):
    """A threaded speech engine backend

    Handles all the threading mechanics internally.
    Subclasses must at least implement the threadedSay() method, and can use
    whatever means are available to speak text.
    The say() and sayList() and insertPause() methods are not meant to be overridden.
    """
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)
        self.active = True
        self._threadedIsSpeaking = False
        self.queue = queue.Queue()
        self.thread: threading.Thread | None = None
        self.process = None
        self.initialized: bool = False
        self.voice: str = self.setting('voice')
        self.volume: float = self.setting('volume') / 100.0
        self.rate = self.setting('speed')

    def init(self):
        super().init()
        if self.initialized:
            return

        self.initialized = True
        clz = type(self)
        self.thread = threading.Thread(
                target=self._handleQueue, name=f'TTSThread: {clz.backend_id}')
        self.thread.start()

    def _handleQueue(self):
        clz = type(self)
        if type(self)._logger.isEnabledFor(DEBUG):
            self._logger.debug(
                'Threaded TTS Started: {0}'.format(clz.backend_id))

        while self.active and not my_monitor.abortRequested():
            try:
                text = self.queue.get(timeout=3.5)
                self.queue.task_done()
                if isinstance(text, int):
                    time.sleep(text / 1000.0)
                else:
                    self._threadedIsSpeaking = True
                    self.threadedSay(text)
                    self._threadedIsSpeaking = False
            except queue.Empty:
                # self._logger.debug_verbose('queue empty')
                pass
        if type(self)._logger.isEnabledFor(DEBUG):
            self._logger.debug(
                'Threaded TTS Finished: {0}'.format(clz.backend_id))

    def _emptyQueue(self):
        try:
            if type(self)._logger.isEnabledFor(DEBUG_VERBOSE):
                self._logger.debug_verbose('_emptyQueue')
            while True:
                self.queue.get_nowait()
                self.queue.task_done()
        except queue.Empty:
            if type(self)._logger.isEnabledFor(DEBUG_VERBOSE):
                self._logger.debug_verbose('_emptyQueue is empty')
            return

    def say(self, text, interrupt=False, preload_cache=False):
        if not self.active:
            return
        if interrupt:
            self._stop()
        self.queue.put_nowait(text)

    def sayList(self, texts, interrupt=False):
        if interrupt:
            self._stop()
        self.queue.put_nowait(texts.pop(0))
        for t in texts:
            self.insertPause()
            self.queue.put_nowait(t)

    def isSpeaking(self):
        return self.active and (self._threadedIsSpeaking or not self.queue.empty())

    def _stop(self):
        if self.process is not None:
            try:
                self.process.terminate()
            except Exception as e:
                pass
            finally:
                self.process = None

        self._emptyQueue()
        super()._stop()

    def insertPause(self, ms=500):
        self.queue.put(ms)

    def threadedSay(self, text):
        """Method accepting text to be spoken

        Subclasses must override this method and should speak the unicode text.
        Speech interruption is implemented in the stop() method.
        """
        raise Exception('Not Implemented')

    def _close(self):
        self.active = False
        super()._close()
        self._emptyQueue()


class SimpleTTSBackendBase(ThreadedTTSBackend):
    WAVOUT = 0
    ENGINESPEAK = 1
    PIPE = 2
    canStreamWav = True
    player_handler_class: audio.BasePlayerHandler = audio.WavAudioPlayerHandler
    """Handles speech engines that output wav files

    Subclasses must at least implement the runCommand() method which should
    save a wav file to outFile and/or the runCommandAndSpeak() method which
    must play the speech directly.
    """

    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)
        self._simpleIsSpeaking = False
        self.mode = None
        self.player_handler_instance: PlayerHandlerType = None
    def init(self):
        clz = type(self)
        if self.initialized:
            return

        super().init()
        self.player_handler_instance: PlayerHandlerType = clz.player_handler_class()
        player = clz.get_player_setting()
        # self.player_handler = clz.player_handler_class(player)

    @staticmethod
    def isSupportedOnPlatform():
        """
        This O/S supports this engine/backend

        :return:
        """
        return False

    @staticmethod
    def isInstalled():
        """
        This eGngine/backend is installed and configured on the O/S.

        :return:
        """
        return False

    def get_player_handler(self) -> PlayerHandlerType:
        clz = type(self)
        return self.player_handler_instance

    def setMode(self, mode: int) -> None:
        assert isinstance(mode, int), 'Bad mode'
        if mode == self.PIPE:
            if self.get_player_handler().canSetPipe():
                if type(self)._logger.isEnabledFor(DEBUG):
                    type(self)._logger.debug('Mode: PIPE')
            else:
                mode = self.WAVOUT
        self.mode = mode
        if mode == self.WAVOUT:
            if type(self)._logger.isEnabledFor(DEBUG):
                type(self)._logger.debug('Mode: WAVOUT')
        elif mode == self.ENGINESPEAK:
            audio.load_snd_bm2835()
            if type(self)._logger.isEnabledFor(DEBUG):
                type(self)._logger.debug('Mode: ENGINESPEAK')

    def setPlayer(self, preferred=None, advanced=None):
        return self.get_player_handler().setPlayer(preferred=preferred, advanced=advanced)

    def setSpeed(self, speed: float):
        self.get_player_handler().setSpeed(speed)

    def getSpeed(self) -> int:
        speed: int = Settings.getSetting(Settings.SPEED, self.get_backend_id())
        return speed

    def getPitch(self) -> int:
        pitch: int = Settings.getSetting(Settings.PITCH, self.get_backend_id())
        return pitch

    def getVolumeDb(self) -> float:
        """
        Mechanism for player to get the volume set for the engine.  This
        function attempts to convert the native engine volume to a common
        db scale.

        Volume is best represented in decibles. Ideally we would have
        common volume settings across all engines and players, but
        since no one agrees on what value 0db or 10db is we will have to muddle
        on as best we can.

        We need a way to pass the volume set for the engine over to the player.
        The engines will attempt to convert their native volume settings to
        a common decible setting and the players will do the reverse conversion.
        It will require a lot of fiddling to get it reasonably useful.

        :return: user set engine volume in decibles -12.0 .. +12.0
        """

        volume = Settings.getSetting(Settings.VOLUME, self.get_backend_id())
        return volume

    def runCommand(self, text: str, outFile: str):
        """Convert text to speech and output to a .wav file

        If using WAVOUT mode, subclasses must override this method
        and output a .wav file to outFile, returning True if a file was
        successfully written and False otherwise.
        """
        raise Exception('Not Implemented')

    def runCommandAndSpeak(self, text):
        """Convert text to speech and output directly

        If using ENGINESPEAK mode, subclasses must override this method
        and speak text and should block until speech is complete.
        """
        raise Exception('Not Implemented')

    def runCommandAndPipe(self, text):
        """Convert text to speech and pipe to audio player

        If using PIPE mode, subclasses must override this method
        and return an open pipe to wav data
        """
        raise Exception('Not Implemented')

    def get_path_to_voice_file(self, text_to_voice, use_cache=False):
        exists = False
        voice_file = self.get_player_handler().getOutFile(
            text_to_voice, use_cache=use_cache)
        if VoiceCache.is_cache_sound_files(type(self)):

            # TODO: Remove HACK

            _, extension = os.path.splitext(voice_file)
            voice_file, exists = VoiceCache.get_sound_file_path(text_to_voice,
                                                                extension)
            self.get_player_handler().outFile = voice_file
        return voice_file, exists

    def get_voice_from_cache(self, text_to_voice, use_cache=False):
        voiced_text: bytes = None
        voice_file: str = None
        if VoiceCache.is_cache_sound_files(type(self)):
            voice_file = self.get_player_handler().getOutFile(text_to_voice,
                                                        use_cache=use_cache)

            # TODO: Remove HACK

            _, extension = os.path.splitext(voice_file)
            voice_file, voiced_text = VoiceCache.get_text_to_speech(text_to_voice,
                                                                    extension)
            self.get_player_handler().outFile = voice_file
        else:
            voice_file = ''  # Can't return a tuple with Nine
        if voiced_text is None:
            voiced_text = b''
        return voice_file, voiced_text # Can't return a tuple with None

    def getWavStream(self, text):
        fpath = os.path.join(utils.getTmpfs(), 'speech.wav')
        if type(self)._logger.isEnabledFor(DEBUG_VERBOSE):
            type(self)._logger.debug_verbose('tmpfile: ' + fpath)

        self.runCommand(text, fpath)
        return open(fpath, 'rb')

    def config_mode(self):
        clz = type(self)
        player_id: str = Settings.getSetting(Settings.PLAYER, self.backend_id)
        if player_id == BuiltInAudioPlayer.ID:
            mode = self.ENGINESPEAK
        elif Settings.getSetting(Settings.PIPE, self.backend_id,
                                 clz.getSetting(Settings.PIPE)):
            mode = self.PIPE
        else:
            mode = self.WAVOUT

        self.setMode(mode)

    def threadedSay(self, text):
        clz = type(self)
        if not text:
            return
        try:
            self.setPlayer(clz.get_player_setting())
            self.config_mode()
            if self.mode == self.WAVOUT:
                outFile = self.get_player_handler().getOutFile(text)
                if not self.runCommand(text, outFile):
                    return
                player_handler: PlayerHandlerType = self.get_player_handler()
                player_handler.play()
            elif self.mode == self.PIPE:
                source = self.runCommandAndPipe(text)
                if not source:
                    return
                self.get_player_handler().pipeAudio(source)
            else:
                self._simpleIsSpeaking = True
                self.runCommandAndSpeak(text)
                self._simpleIsSpeaking = False
        except Exception as e:
            clz._logger.exception(e)

    def isSpeaking(self):
        return (self._simpleIsSpeaking or self.get_player_handler().isPlaying()
                or ThreadedTTSBackend.isSpeaking(self))

    @classmethod
    def get_player_ids(cls, include_builtin: bool = True) -> List[str]:
        player_ids: List[str] = []
        for player in cls.player_handler_class().getAvailablePlayers(include_builtin=include_builtin):
            player_ids.append(player.ID)
        return player_ids

    def _stop(self):
        self.get_player_handler().stop()
        ThreadedTTSBackend._stop(self)

    def _close(self):
        ThreadedTTSBackend._close(self)
        self.get_player_handler().close()


class LogOnlyTTSBackend(TTSBackendBase):
    backend_id = 'log'
    displayName = 'Log'
    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)

    @staticmethod
    def isSupportedOnPlatform():
        return True

    @staticmethod
    def isInstalled():
        return LogOnlyTTSBackend.isSupportedOnPlatform()

    def say(self, text, interrupt=False, preload_cache=False):
        if type(self)._logger.isEnabledFor(DEBUG):
            type(self)._logger.debug(
                'say(Interrupt={1}): {0}'.format(repr(text), interrupt))

    @staticmethod
    def available():
        return True


TTSBackendBridge.setBaseBackend(TTSBackendBase)
