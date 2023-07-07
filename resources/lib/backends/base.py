# -*- coding: utf-8 -*-
import os
import queue
import sys
import threading
from pathlib import Path

import xbmc

from backends import audio
from backends.__init__ import *
from backends.audio.sound_capabilties import ServiceType, SoundCapabilities
from backends.i_tts_backend_base import ITTSBackendBase
from backends.players.iplayer import IPlayer
from backends.players.player_index import PlayerIndex
from backends.settings.constraints import Constraints
from common.base_services import BaseServices
from backends.settings.validators import BoolValidator, ConstraintsValidator
from backends.tts_backend_bridge import TTSBackendBridge
from cache.voicecache import VoiceCache
from common import utils
from common.constants import Constants
from common.exceptions import ExpiredException
from common.logger import *
from common.messages import Messages
from common.minimal_monitor import MinimalMonitor
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import Genders, Mode, Players
from common.settings import Settings
from common.settings_low_level import SettingsProperties

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class BaseEngineService(BaseServices):
    """The base class for all speech engine backends

    Subclasses must at least implement the say() method, and can use whatever
    means are available to speak text.
    """
    interval = 100
    broken = False

    #  TODO: Remove
    # Volume scale as presented to the user

    volumeExternalEndpoints = (-12, 12)
    volumeStep = 1
    volumeSuffix = 'dB'
    speedInt = True
    _logger = module_logger.getChild('BaseEngineService')  # type: BasicLogger
    _current_engine: ITTSBackendBase = None

    _class_name: str = None
    initialized_static: bool = False
    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    _engine_id: str = None
    _baseEngine: 'BaseEngineService' = None

    def __init__(self, *args, **kwargs):
        super(BaseEngineService, self).__init__(*args, **kwargs)

        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(type(self)._class_name)
        self.initialized = False
        self.dead = False  # Backend should flag this true if it's no longer usable
        self.deadReason = ''  # Backend should set this reason when marking itself dead
        self._closed = False
        self.voice: str | None = None
        self.volume: float = 0.0
        self.rate: float = 0.0
        self.player: IPlayer | None = None
        self.stop_msg: str | None = None
        BaseServices.register(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._close()

    def re_init(self):
        self.initialized = False
        self.init()

    def init(self):
        pass

    def get_player(self) -> IPlayer:
        # Gets the player instance for the given engine. If settings are changed
        # then the new player will be instantiated.

        clz = type(self)
        current_player_id: str = Settings.get_player_id(clz._engine_id)
        if self.player is None or current_player_id != self.player.ID:
            self.player = BaseServices.getService(current_player_id)
        return self.player

    def say(self, phrase: PhraseList):
        """Method accepting text to be spoken

        Must be overridden by subclasses.
        text is unicode and the text to be spoken.
        If interrupt is True, the subclass should interrupt all previous speech.

        """
        raise Exception('Not Implemented')

    def getConverter_for(self, engine_id: str) -> str | None:
        """
        Finds a audio converter (typically a player or specialized tool)
        which can convert between the audio formats producable by the engine
        and a player.

        SoundCapabilities are used to make the negotiation

        :param engine_id:
        :return:
        """
        Monitor.exception_on_abort(0.05)
        converter_id: str = Settings.get_setting_str(SettingsProperties.CONVERTER,
                                                     engine_id, ignore_cache=False,
                                                     default=None)
        if converter_id is None or len(converter_id) == 0:
            engine_output_formats: List[str] = SoundCapabilities.get_output_formats(engine_id)
            if SoundCapabilities.MP3 in engine_output_formats:
                # No converter needed, need to check player
                return None

            player_input_formats: List[str] = [SoundCapabilities.MP3]
            candidate_converters: List[str] = \
                SoundCapabilities.get_capable_services(ServiceType.CONVERTER,
                                                       engine_output_formats,
                                                       player_input_formats)
            converter_id = None
            if len(candidate_converters) > 0:
                converter_id = candidate_converters[0]

        return converter_id

    '''
    @classmethod
    def get_validator(cls, service_id: str,
                      property_id: str) -> ConstraintsValidator | IValidator:
        return SettingsMap.get_validator(service_id=service_id,
                                         property_id=property_id)

    @classmethod
    def get_bool_validator(cls, service_id, str,
                           property_id: str) -> BoolValidator | IValidator:
        return SettingsMap.get_validator(service_id=service_id,
                                         property_id=property_id)
    '''

    def volumeUp(self) -> str:
        clz = type(self)
        if not self.settings or not SettingsProperties.VOLUME in self.settings:
            return Messages.get_msg(Messages.CANNOT_ADJUST_VOLUME)
        vol = clz.getSettingConstraints(SettingsProperties.VOLUME)
        max_volume: int = self.volumeExternalEndpoints[1]
        volume_step: int = self.volumeStep
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug(f'Volume UP: {vol} Upper Limit: {max_volume} '
                              f'step {self.volumeStep}')
        vol += volume_step
        if vol > max_volume:
            volume_step = volume_step - (vol - max_volume)
            vol = max_volume
        self.setSetting(SettingsProperties.VOLUME, vol)
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug('Volume UP: {0}'.format(vol))
        return f'Volume Up by {volume_step} now {vol} {self.volumeSuffix}'

    def volumeDown(self) -> str:
        clz = type(self)
        if not self.settings or not SettingsProperties.VOLUME in self.settings:
            return Messages.get_msg(Messages.CANNOT_ADJUST_VOLUME)
        min_volume: int = self.volumeExternalEndpoints[0]
        volume_step: int = self.volumeStep
        vol = clz.getSetting(SettingsProperties.VOLUME)
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug(f'Volume Down: {vol} Lower Limit: {min_volume} '
                              f'step {volume_step}')
        vol -= volume_step
        if vol < min_volume:
            volume_step = volume_step - (min_volume - vol)
            vol = min_volume
        self.setSetting(SettingsProperties.VOLUME, vol)
        if type(self)._logger.isEnabledFor(DEBUG):
            type(self)._logger.debug('Volume DOWN: {0}'.format(vol))
        return f'Volume Down by {volume_step} now {vol} {self.volumeSuffix}'

    def flagAsDead(self, reason=''):
        self.dead = True
        self.deadReason = reason or self.deadReason

    @classmethod
    def get_constraints(cls, setting: str) -> Constraints | None:
        """

        @param setting:
        @return:
        """
        constraints: Constraints | None = cls.TTSConstraints.get(setting)
        return constraints

    @classmethod
    def isSettingSupported(cls, setting_id: str):
        return cls.is_valid_property(cls.service_ID, setting_id)

    @classmethod
    def getSettingNames(cls) -> List[str]:
        """
        Gets a list of all of the setting names/keys that this backend uses

        :return:
        """
        settingNames: List[str] = []
        for settingName in cls.settings.keys():
            settingNames.append(settingName)

        return settingNames

    @classmethod
    def get_setting_default(cls, setting) ->\
            int | float | bool | str | float | List[int] | List[str] | List[bool] \
            | List[float] | None:
        default = None
        #if setting in cls.settings.keys():
        #    setting: str
        #    default = cls.settings.get(setting, None)
        if isinstance(default, Constraints):
            constraints: Constraints = default
            default = constraints.default
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

    @classmethod
    def getLanguage(cls):
        default_locale = Constants.LOCALE.lower().replace('_', '-')
        return cls.getSetting(SettingsProperties.LANGUAGE, default_locale)

    @classmethod
    def getGender(cls):
        gender = cls.getSetting(SettingsProperties.GENDER, Genders.UNKNOWN)

        return gender

    @classmethod
    def getVoice(cls):
        voice = cls.getSetting(SettingsProperties.VOICE, SettingsProperties.UNKNOWN_VALUE)

        return voice

    @classmethod
    def getSpeed(cls) -> float:
        engine_speed_validator: ConstraintsValidator
        engine_speed_validator = cls.get_validator(cls.service_ID,
                                                   property_id=SettingsProperties.SPEED)
        speed = engine_speed_validator.getValue()
        return speed

    @classmethod
    def getPitch(cls) -> float:
        engine_pitch_validator: ConstraintsValidator
        engine_pitch_validator = cls.get_validator(cls.service_ID,
                                                           property_id=SettingsProperties.PITCH)
        pitch: float = engine_pitch_validator.getValue()
        return pitch

    @classmethod
    def getVolume(cls) -> float:
        engine_volume_validator: ConstraintsValidator
        engine_volume_validator = cls.get_validator(cls.service_ID,
                                                            property_id=SettingsProperties.VOLUME)
        volume: float = engine_volume_validator.getValue()
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
        Settings.setSetting(SettingsProperties.PLAYER_SPEED, int_player_speed,
                            cls._engine_id)

    @classmethod
    def getSetting(cls, key, default=None):
        """
        Gets a setting from addon's settings.xml

        A convenience method equivalent to Settings.getSetting(key + '.'. + cls._engine_id,
        default, useFullSettingName).

        :param key:
        :param default:
        :return:
        """
        if default is None:
            default = cls.get_setting_default(key)

        return Settings.getSetting(key, cls._engine_id, default)

    '''
    @classmethod
    def setSettingConstraints(cls,
                   setting_id: str,
                   constraints: Constraints
                   ) -> bool:
        """
        Saves a setting to addon's settings.xml

        A convenience method for Settings.setSetting(key + '.' + cls._engine_id, value)

        :param constraints:
        :param setting_id:
        :return:
        """
        if not isinstance(constraints, Constraints):
            cls._logger.error(f'setSettingConstrants with non-constraint: '
                              f'{type(constraints)}')
            return False
        return Settings.setSettingConstraints(setting_id, constraints)
        
        if (not cls.isSettingSupported(setting_id)
                and cls._logger.isEnabledFor(WARNING)):
            cls._logger.warning(f'Setting: {setting_id}, not supported by voicing '
                                f'engine: {cls.get_engine_id()}')
        previous_value = Settings.getSetting(setting_id, cls.get_engine_id(),  None)
        changed = False
        if previous_value != value:
            changed = True
        Settings.setSetting(setting_id, value, cls._engine_id)
        return changed
        '''

    @classmethod
    def set_player_setting(cls, value: str) -> bool:
        engine_id: str = cls.get_backend_id()
        if (not cls.isSettingSupported(SettingsProperties.PLAYER)
                and cls._logger.isEnabledFor(WARNING)):
            cls._logger.warning(f'{SettingsProperties.PLAYER}, not supported by voicing engine: '
                                f'{engine_id}')
        previous_value = Settings.get_player_id(engine_id=engine_id)
        changed = previous_value != value
        Settings.set_player(value, engine_id)
        return changed

    @classmethod
    def get_backend_id(cls) -> str:
        """

        @return:
        """
        return cls._engine_id

    @classmethod
    def insertPause(cls, ms=500):
        """Insert a pause of ms milliseconds

        May be overridden by sublcasses. Default implementation sleeps for ms.
        """
        Monitor.exception_on_abort(ms/1000.0)

    def isSpeaking(self):
        """Returns True if speech engine is currently speaking, False if not
        and None if unknown

        Subclasses should override this accordingly
        """
        return None

    '''
    def getWavStream(self, text:str):
        """Returns an open file like object containing wav data

        Subclasses should override this to provide access to functions
        that require this functionality
        """
        return None
    '''

    def notify_engine(self, msg: str, now: bool = False) -> None:
        clz = type(self)
        if clz._current_engine is not None:
            clz._current_engine.notify(msg, now)
        else:
            clz._logger.debug(f'_current_engine not set')
        self.notify_player(msg, now)

    @classmethod
    def notify_player(self, msg: str, now: bool = False) -> None:
        clz = type(self)
        player: IPlayer = self.get_player()
        player.notify(msg, now)

    def update(self):
        """Called when the user has changed a setting for this backend

        Subclasses should override this to react to user changes.
        """
        pass

    def stop(self, msg: str = None):
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

    def _stop(self, msg: str = None):
        self.stop()

    def _close(self, msg: str = None):
        self._closed = True
        self._stop()

    @classmethod
    def is_available_and_usable(cls):
        """

        @return:
        """
        return cls._available()

    @classmethod
    def _available(cls):
        if cls.broken and Settings.getSetting(SettingsProperties.DISABLE_BROKEN_SERVICES,
                                              SettingsProperties.TTS_SERVICE, True):
            return False
        return cls.available()

    @staticmethod
    def available():
        """Static method representing the speech engines availability

        Subclasses should override this and return True if the speech engine is
        capable of speaking text in the current environment.
        Default implementation returns False.
        """
        return False

    @classmethod
    def getSettingConstraints(cls, VOLUME):
        pass


class ThreadedTTSBackend(BaseEngineService):
    """A threaded speech engine backend

    Handles all the threading mechanics internally.
    Subclasses must at least implement the threadedSay() method, and can use
    whatever means are available to speak text.
    The say() method is not meant to be overridden.
    """
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)
        self.active: bool = True
        self.engine_id: str = None
        self._queue_high_water_mark: int = 0
        self.queue = queue.Queue(50)
        self.queueCount: int = 0
        self.queueFullCount: int = 0
        self._threadedIsSpeaking = False
        self.thread: threading.Thread | None = None
        self.process = None
        self.initialized: bool = False
        BaseServices.register(self)

    def init(self):
        """

        @return:
        """
        super().init()
        if self.initialized:
            return

        self.initialized = True
        clz = type(self)
        self.thread = threading.Thread(
                target=self._handleQueue, name=f'TTSThread: {clz._engine_id}')
        xbmc.log(f'Starting thread TTSThread: {clz._engine_id}', xbmc.LOGINFO)
        self.thread.start()

    def _handleQueue(self):
        clz = type(self)
        if type(self)._logger.isEnabledFor(DEBUG):
            self._logger.debug(
                f'Threaded TTS Started: {clz._engine_id} thread_name: '
                f'{threading.current_thread().name}')

        while self.active and not Monitor.wait_for_abort(timeout=3.5):
            try:
                phrase: Phrase = self.queue.get(timeout=0.1)
                self.queue.task_done()     #  TODO: Change this to use phrase delays
                self._threadedIsSpeaking = True
                self.threadedSay(phrase)
                self._threadedIsSpeaking = False
            except queue.Empty:
                # self._logger.debug_verbose('queue empty')
                pass
            except ExpiredException:
                clz._logger.debug(f'Expired')
        if type(self)._logger.isEnabledFor(DEBUG):
            self._logger.debug(
                'Threaded TTS Finished: {0}'.format(clz._engine_id))

    def _emptyQueue(self):
        clz = type(self)
        clz._logger.debug(f'emptyQueue')
        try:
            while True:
                self.queue.get_nowait()
                self.queue.task_done()
        except queue.Empty:
            return

    def say(self, phrases: PhraseList):
        """

        @param phrases:
        @return:
        """
        clz = type(self)
        if not self.active or self.stop_msg is not None:
            self.stop_msg = None
            return
        try:
            clz._logger.debug(f'base.say phrase: {phrases[0].get_text()}')
            interrupt: bool = phrases[0].get_interrupt()
            if interrupt:
                clz._logger.debug(f'INTERRUPT: base engine {phrases[0].get_text()}')
                self._stop(msg='from engine.say')
        except ExpiredException:
            clz._logger.debug('EXPIRED')
        # If voice file caching is used, check to see if voiced file already
        # exists, or what path to use if it doesn't exist.

        use_cache: bool = Settings.is_use_cache(self.engine_id)
        try:
            phrase: Phrase
            for phrase in phrases:
                if self.stop_msg is not None:
                    self.stop_msg = None
                    break
                cache_path: Path
                # if phrase.get_cache_path() is None:
                #     VoiceCache.get_path_to_voice_file(phrase, use_cache=True)
                if phrase.is_exists():
                    #  TODO: Add ability to deal with converter
                    #  Bypass engine and go straight to playing
                    player_id: str = Settings.get_player_id(self.engine_id)
                    self.say_file(phrase, player_id)
                    continue

                self.queue.put_nowait(phrase)
                self.queueCount += 1
                if self.queue.full():
                    self.queueFullCount += 1

                queue_size = self.queue.qsize()
                if queue_size > self._queue_high_water_mark:
                    clz._logger.debug(f'queue_size now: {queue_size}')
                    self._queue_high_water_mark = queue_size
        except ExpiredException:
            clz._logger.debug('EXPIRED')

    def say_file(self, phrase: Phrase, player_id: str) -> None:
        clz = type(self)
        try:
            player: IPlayer = PlayerIndex.get_player(player_id)
            player.init(self.engine_id)
            player.play(phrase)
        except AbortException as e:
            reraise(*sys.exc_info())
        except ExpiredException:
            clz._logger.debug('EXPIRED')
        except Exception as e:
            clz._logger.exception('')
        return


    def isSpeaking(self):
        """

        @return:
        """
        clz = type(self)

        try:
            speaking: bool = self.active and (self._threadedIsSpeaking or not self.queue.empty())
        except AttributeError as e:
            clz._logger.exception('')
            speaking = False
        return speaking

    def _stop(self, msg: str = None):
        self.stop_msg = msg
        if self.process is not None:
            try:
                self.process.terminate()
            except Exception as e:
                pass
            finally:
                self.process = None

        self._emptyQueue()
        super()._stop(msg)

    '''
    def insertPause(self, ms=500):
        """

        @param ms:
        """
        if self.queue.full():
            self.queueFullCount += 1
        self.queue.put(ms)
        self.queueCount += 1
    '''

    def threadedSay(self, phrase: Phrase):
        """Method accepting text to be spoken

        Subclasses must override this method and should speak the unicode text.
        Speech interruption is implemented in the stop() method.
        """
        raise Exception('Not Implemented')

    def _close(self):
        self.active = False
        super()._close()
        self._emptyQueue()


class SimpleTTSBackend(ThreadedTTSBackend):
    """

    """
    canStreamWav = True
    """Handles speech engines that output sound files

    Subclasses must at least implement the runCommand() method which should
    save a sound file to outFile and/or the runCommandAndSpeak() method which
    must play the speech directly.
    """
    _simpleIsSpeaking = False

    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)
        clz._simpleIsSpeaking = False
        self.mode = None
        BaseServices.register(self)

    def init(self):
        """

        @return:
        """
        clz = type(self)
        if self.initialized:
            return

        super().init()

    #  def get_player_handler(self) -> PlayerHandlerType:
    #    """
    #
    #    @return:
    #    """
    #    clz = type(self)
    #    return self.player_handler_instance

    def setMode(self, mode: Mode) -> None:
        """

        @param mode:
        """
        assert isinstance(mode, int), 'Bad mode'
        if mode == Mode.PIPE:
            # if self.get_player_handler().canSetPipe():
            #     if type(self)._logger.isEnabledFor(DEBUG):
            #        type(self)._logger.debug('Mode: PIPE')
            #else:
                mode = Mode.FILEOUT
        self.mode: Mode = mode
        if mode == Mode.FILEOUT:
            if type(self)._logger.isEnabledFor(DEBUG):
                type(self)._logger.debug('Mode: FILEOUT')
        elif mode == Mode.ENGINESPEAK:
            audio.load_snd_bm2835()
            if type(self)._logger.isEnabledFor(DEBUG):
                type(self)._logger.debug('Mode: ENGINESPEAK')

    def setSpeed(self, speed: float):
        """

        @param speed:
        """
        #  self.get_player_handler().setSpeed(speed)

    def getSpeed(self) -> int:
        """

        @return:
        """
        # Need to convert from Kodi TTS speed to this engine's speed
        speed: int = Settings.getSetting(SettingsProperties.SPEED, self.get_backend_id())

        return speed

    def getPitch(self) -> int:
        """

        @return:
        """
        pitch: int = Settings.getSetting(SettingsProperties.PITCH, self.get_backend_id())
        return pitch

    def getVolumeDb(self) -> float:
        """
        Mechanism for player to get the volume set for the engine.  This
        function attempts to convert the native engine volume to a common
        db scale.

        Volume is best represented in decibels. Ideally we would have
        common volume settings across all engines and players, but
        since no one agrees on what value 0db or 10db is we will have to muddle
        on as best we can.

        We need a way to pass the volume set for the engine over to the player.
        The engines will attempt to convert their native volume settings to
        a common decible setting and the players will do the reverse conversion.
        It will require a lot of fiddling to get it reasonably useful.

        :return: user set engine volume in decibels -12.0 .. +12.0
        """

        volume = Settings.getSetting(SettingsProperties.VOLUME, self.get_backend_id())
        return volume

    def runCommand(self, phrase: Phrase):
        """Convert text to speech and output to a .wav file

        If using FILEOUT mode, subclasses must override this method
        and output a .wav file to outFile, returning True if a file was
        successfully written and False otherwise.
        """
        raise Exception('Not Implemented')

    def runCommandAndSpeak(self, phrase: Phrase):
        """Convert text to speech and output directly

        If using ENGINESPEAK mode, subclasses must override this method
        and speak text and should block until speech is complete.
        """
        raise Exception('Not Implemented')

    def runCommandAndPipe(self, phrase: Phrase):
        """Convert text to speech and pipe to audio player

        If using PIPE mode, subclasses must override this method
        and return an open pipe to wav data
        """
        raise Exception('Not Implemented')

    '''
    def getWavStream(self, text:str):
        """

        @param text:
        @return:
        """
        fpath = os.path.join(utils.getTmpfs(), 'speech.wav')
        if type(self)._logger.isEnabledFor(DEBUG_VERBOSE):
            type(self)._logger.debug_verbose('tmpfile: ' + fpath)

        self.runCommand(text, fpath)
        return open(fpath, 'rb')
    '''

    def config_mode(self):
        """

        """
        clz = type(self)

        player_id: str = Settings.get_player_id(self.engine_id)

        if player_id == Players.INTERNAL:
            mode = Mode.ENGINESPEAK
        elif Settings.uses_pipe(self.engine_id):
            mode = Mode.PIPE
        else:
            mode = Mode.FILEOUT

        self.setMode(mode)

    def threadedSay(self, phrase: Phrase):
        """

        @param phrase:
        @return:
        """
        clz = type(self)
        if not phrase:
            return

        try:
            player: IPlayer = self.get_player()
            self.config_mode()
            text: str = phrase.get_text()
        #  TODO: Deal with phrase.delay. Pre and Post
            if self.mode == Mode.FILEOUT:
                outFile: str
                exists: bool
                use_cache: bool = Settings.is_use_cache(clz._engine_id)
                VoiceCache.get_path_to_voice_file(phrase, use_cache=use_cache)
                voice_file: Path = phrase.get_cache_path()
                if not self.runCommand(phrase):
                    return

                try:
                    player.init(clz._engine_id)
                except Exception as e:
                    clz._logger.exception('')
                player.play(phrase)
                # player_handler: PlayerHandlerType = self.get_player_handler()
                # player_handler.play()
            elif self.mode == Mode.PIPE:
                source = self.runCommandAndPipe(phrase)
                if not source:
                    return
                # self.get_player_handler().pipeAudio(source)
            else:
                clz._simpleIsSpeaking = True
                self.runCommandAndSpeak(phrase)
                clz._simpleIsSpeaking = False
        except ExpiredException:
            clz._logger.debug('EXPIRED')
        except Exception as e:
            clz._logger.exception('')

    def isSpeaking(self):
        """

        @return:
        """
        clz = type(self)
        return (clz._simpleIsSpeaking # or self.get_player_handler().isPlaying()
                or ThreadedTTSBackend.isSpeaking(self))

    @classmethod
    def get_player_ids(cls, include_builtin: bool = True) -> List[str]:
        """

        @param include_builtin:
        @return:
        """
        player_ids: List[str] = []
        # for player in cls.player_handler_class().getAvailablePlayers(include_builtin=include_builtin):
        #     player_ids.append(player.ID)
        return player_ids

    def _stop(self, msg: str = None):
        # self.get_player_handler().stop()
        ThreadedTTSBackend._stop(self, msg)

    def _close(self, msg: str = None):
        #  super()._close()
        # self.get_player_handler().close()
        pass


class LogOnlyTTSBackend(BaseEngineService):
    """

    """
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
        BaseServices.register(self)

    @staticmethod
    def isSupportedOnPlatform():
        """

        @return:
        """
        return True

    @staticmethod
    def isInstalled():
        """

        @return:
        """
        return LogOnlyTTSBackend.isSupportedOnPlatform()

    @staticmethod
    def available():
        """

        @return:
        """
        return True

    def say(self, phrase: Phrase):
        """

        @param phrase:
        """
        pass


TTSBackendBridge.setBaseBackend(BaseEngineService)
