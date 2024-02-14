# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import queue
import sys
import threading
from pathlib import Path

from common import *

from backends import audio
from backends.audio.sound_capabilties import ServiceType, SoundCapabilities
from backends.i_tts_backend_base import ITTSBackendBase
from backends.players.iplayer import IPlayer
from backends.settings.constraints import Constraints
from backends.settings.i_validators import IValidator
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator
from backends.tts_backend_bridge import TTSBackendBridge
from cache.voicecache import VoiceCache
from common.base_services import BaseServices
from common.constants import Constants
from common.exceptions import ExpiredException
from common.garbage_collector import GarbageCollector
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.messages import Messages
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import Genders, Mode, Players
from common.settings import Settings
from common.settings_low_level import SettingsProperties

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class EngineQueue:
    '''
    There is a single EngineQueue which all voiced text must flow through.
    The queue can be purged when text expires (when a movie starts to play or
    due to user input, etc.).
    '''

    class QueueItem:

        def __init__(self, phrase: Phrase, engine: 'BaseEngineService'):
            self._phrase: Phrase = phrase
            self._engine: 'BaseEngineService' | 'SimpleTTSBackend' = engine

        @property
        def phrase(self) -> Phrase:
            return self._phrase

        @property
        def engine(self) -> 'SimpleTTSBackend':
            return self._engine

    kodi_player_state: KodiPlayerState = None
    _instance: 'EngineQueue' = None
    _logger: BasicLogger = None

    def __init__(self):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(self.__class__.__name__)

        # active_queue is True as long as there is a configured active_queue engine

        self.active_queue: bool = False
        self.tts_queue = queue.Queue(50)
        self._threadedIsSpeaking = False  # True if engine is ThreadedTTSBackend
        self.queue_processor: threading.Thread | None = None

    @classmethod
    def kodi_player_status_listener(cls, player_state: KodiPlayerState) -> None:
        cls._logger.debug(f'PLAYER_STATE: {player_state}')
        cls.get_kodi_player_state(player_state)

    @classmethod
    def init(cls):
        """

        @return:
        """
        if cls._instance is None:
            cls._instance = EngineQueue()
            cls._instance.active_queue = True
        if cls._instance.queue_processor is None:
            cls._instance.queue_processor = threading.Thread(
                    target=cls._instance._handleQueue, name=f'EngineQueue')
            cls._instance._logger.debug(f'Starting queue_processor EngineQueue')
            cls._instance.queue_processor.start()
            GarbageCollector.add_thread(cls._instance.queue_processor)

    @classmethod
    @property
    def queue(cls) -> 'EngineQueue':
        return cls._instance

    def _handleQueue(self):
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG):
            self._logger.debug(f'Threaded EngineQueue started')

        while self.active_queue and not Monitor.wait_for_abort(timeout=0.1):
            try:
                item: EngineQueue.QueueItem = self.tts_queue.get(timeout=0.0)
                self.tts_queue.task_done()  # TODO: Change this to use phrase delays
                phrase: Phrase = item.phrase
                if (clz.kodi_player_state == KodiPlayerState.PLAYING and not
                        phrase.speak_while_playing):
                    clz._logger.debug(f'skipping play of {phrase.debug_data()} '
                                      f'speak while playing: '
                                      f'{phrase.speak_while_playing}',
                                      trace=Trace.TRACE_AUDIO_START_STOP)
                    continue
                clz._logger.debug(f'Start play of {phrase.debug_data()} '
                                  f'on {item.engine.service_ID}',
                                  trace=Trace.TRACE_AUDIO_START_STOP)
                self._threadedIsSpeaking = True
                engine: 'SimpleTTSBackend' = item.engine
                clz._logger.debug(f'queue.get {phrase.get_text()} '
                                  f'engine: {item.engine.service_ID}')
                engine.threadedSay(phrase)
                clz._logger.debug(f'Return from threadedSay {phrase.debug_data()}',
                                  trace=Trace.TRACE_AUDIO_START_STOP)
                self._threadedIsSpeaking = False
            except queue.Empty:
                # self._logger.debug_verbose('queue empty')
                pass
            except ValueError as e:
                clz._logger.exception('')
            except ExpiredException:
                clz._logger.debug(f'Expired {item.phrase.debug_data} ',
                                  trace=Trace.TRACE_AUDIO_START_STOP)
        self.active_queue = False

    @classmethod
    def empty_queue(cls):
        cls._logger.debug(f'empty_queue')
        try:
            while True:
                cls._instance.tts_queue.get_nowait()
                cls._instance.tts_queue.task_done()
        except queue.Empty:
            return

    @classmethod
    def say(cls, phrases: PhraseList, engine: 'BaseEngineService'):
        """
        @param phrases:
        @param engine:
        @return:
        :param engine:
        """
        zelf = cls._instance
        if not engine.is_active_engine():
            return
        try:
            cls._logger.debug(f'phrase: {phrases[0].get_text()} '
                              f'Engine: {engine.service_ID} '
                              f'Interrupt: {phrases[0].get_interrupt()}')
        except ExpiredException:
            cls._logger.debug('EXPIRED')
        try:
            phrase: Phrase
            for phrase in phrases:
                cls.say_phrase(phrase, engine)
        except ExpiredException:
            cls._logger.debug('EXPIRED')

    @classmethod
    def say_phrase(cls, phrase: Phrase, engine: 'BaseEngineService') -> None:
        """
            Say a single phrase. This is a separate method just so that
            when an expensive speech engine does not have the voiced phrase
            already cached, another engine can be used to say the phrase

        :param engine:
        :param phrase:
        :return:
        """
        zelf = cls._instance
        try:
            interrupt: bool = phrase.get_interrupt()
            if interrupt:
                cls._logger.debug(f'INTERRUPT: {phrase.get_text()}')
                cls.empty_queue()

            zelf.tts_queue.put_nowait(EngineQueue.QueueItem(phrase, engine))
            '''
            cls._logger.debug(f'phrase: {phrase.get_text()} ' 
                              f'Engine: {engine.service_ID}')
            cache_path: Path
            if phrase.exists():
                #  TODO: Add ability to deal with converter
                #  Bypass engine and go straight to playing
                player_id: str = Settings.get_player_id(engine.service_ID)
                zelf.say_file(phrase, player_id, engine)
            else:
                cls._logger.debug(f'queue.put {phrase.get_text()}')
                zelf.tts_queue.put_nowait(EngineQueue.QueueItem(phrase, engine))
            cls._logger.debug(f'Put on queue')
            '''
        except ExpiredException:
            cls._logger.debug('EXPIRED')

    @classmethod
    def say_file(cls, phrase: Phrase, player_id: str,
                 engine: 'BaseEngineService') -> None:
        """
        :param phrase:
        :param player_id:
        :param engine:
        :return:
        """
        zelf = cls._instance
        try:
            cls._logger.debug(f'phrase: {phrase.get_text()} '
                              f'Engine: {engine.service_ID}')
            cls.say_phrase(phrase, engine)
            '''
            player: IPlayer = PlayerIndex.get_player(player_id)
            player.init(engine.service_ID)
            player.play(phrase)
            '''
        except AbortException as e:
            reraise(*sys.exc_info())
        except ExpiredException:
            cls._logger.debug('EXPIRED')
        except Exception as e:
            cls._logger.exception(f'Exception {phrase.debug_data}'
                                  f' engine: {engine.service_ID}',
                                  trace=Trace.TRACE_AUDIO_START_STOP)
        return

    @classmethod
    def isSpeaking(cls) -> bool:
        """

        @return:
        """
        try:
            speaking: bool
            speaking = (cls._instance.active_queue and
                        (cls._instance._threadedIsSpeaking or not
                        cls._instance.tts_queue.empty()))
        except AttributeError as e:
            cls._logger.exception('')
            speaking = False
        return speaking

    @classmethod
    def get_kodi_player_state(cls, kodi_player_state: KodiPlayerState) -> None:
        cls._logger.debug(f'EngineQueue SET_KODI_PLAYER_STATE: {kodi_player_state}')
        cls.kodi_player_state = kodi_player_state

    @classmethod
    def stop(cls) -> None:
        pass
        # cls._instance.empty_queue()

    @classmethod
    def close(cls) -> None:
        cls._instance.active_queue = False
        cls._instance.empty_queue()


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
    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    engine_id: str = None
    _baseEngine: 'BaseEngineService' = None

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(*args, **kwargs)

        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)
        self.initialized: bool = False
        self.dead: bool = False  # Backend should flag this true if it's no longer usable
        self.deadReason = ''  # Backend should set this reason when marking itself dead
        self._closed = False
        self.voice: str | None = None
        self.volume: float = 0.0
        self.rate: float = 0.0
        self.player: IPlayer | None = None
        BaseServices.register(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._close()

    def re_init(self):
        self.init()

    def init(self):
        pass

    def destroy(self):
        """
        Destroy this engine and any dependent players, etc. Typically done
        when either stopping TTS (F12) or shutdown, or switching engines, etc.

        :return:
        """
        pass

    def get_player(self, engine_id: str) -> IPlayer:
        # Gets the player instance for the given engine. If settings are changed
        # then the new player will be instantiated.

        clz = type(self)
        player_id: str = Settings.get_player_id(engine_id)
        if self.player is None or player_id != self.player.ID:
            self.player = BaseServices.getService(player_id)
        return self.player

    def say(self, phrase: PhraseList):
        """Method accepting text to be spoken

        Must be overridden by subclasses.
        text is unicode and the text to be spoken.
        If interrupt is True, the subclass should interrupt all previous speech
        as well as interrupt what is currently being voiced and anything pending
        voicing (in player).

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
            engine_output_formats: List[str] = SoundCapabilities.get_output_formats(
                engine_id)
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
        if clz._logger.isEnabledFor(DEBUG):
            clz._logger.debug('Volume DOWN: {0}'.format(vol))
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
    def get_setting_default(cls, setting) -> \
            int | float | bool | str | float | List[int] | List[str] | List[bool] \
            | List[float] | None:
        default = None
        # if setting in cls.settings.keys():
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
        return True, True, True

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
    def getVolume(cls) -> float:
        engine_volume_validator: ConstraintsValidator
        engine_volume_validator = cls.get_validator(cls.service_ID,
                                                    property_id=SettingsProperties.VOLUME)
        volume: float = engine_volume_validator.get_tts_value()
        return volume

    @classmethod
    def getVolumeDb(cls) -> float | None:
        # Get the converter from TTS volume scale to the Engine's Scale
        # Get the Engine validator/converter

        # The engine can also act as player.
        # if engine is player, then set volume via engine
        # otherwise, fix volume to 'TTS standard volume' of 0db and let
        # player adjust it from there.

        volume_validator: ConstraintsValidator | IValidator
        volume_validator = SettingsMap.get_validator(cls.service_ID,
                                                     property_id=SettingsProperties.VOLUME)
        volume, _, _, _ = volume_validator.get_tts_values()
        return volume  # Find out if used

    @classmethod
    def getEngineVolume(cls) -> float:
        """
        The Engine's job is to make sure that it's output volume is equal to
        the TTS standard volume. Get the TTS volume from Settings
        service_id=Services.TTS, setting_id='volume'. Then use the validators
        and converters to adjust the engine's volume to match what TTS has
        in the settings.

        The same is true for every stage: engine, player, converter, etc.
        """

        return cls.getVolumeDb()

    @classmethod
    def getEngineVolume_str(cls) -> str:
        volume_validator: ConstraintsValidator
        volume_validator = cls.get_validator(cls.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume: str = volume_validator.getUIValue()
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
            player_speed = player_speed * 1.5  # 2 * 1.5 = 3.0

        int_player_speed: int = int(player_speed * 10)
        Settings.setSetting(SettingsProperties.PLAYER_SPEED, int_player_speed,
                            cls.engine_id)

    @classmethod
    def getSetting(cls, key, default=None):
        """
        Gets a setting from addon's settings.xml

        A convenience method equivalent to Settings.getSetting(key + '.'. + cls.engine_id,
        default, useFullSettingName).

        :param key:
        :param default:
        :return:
        """
        if default is None:
            default = cls.get_setting_default(key)

        return Settings.getSetting(key, cls.engine_id, default)

    '''
    @classmethod
    def setSettingConstraints(cls,
                   setting_id: str,
                   constraints: Constraints
                   ) -> bool:
        """
        Saves a setting to addon's settings.xml

        A convenience method for Settings.setSetting(key + '.' + cls.engine_id, value)

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
        Settings.setSetting(setting_id, value, cls.engine_id)
        return changed
        '''

    @classmethod
    def set_player_setting(cls, value: str) -> bool:
        engine_id: str = cls.get_current_engine_id()
        if (not cls.isSettingSupported(SettingsProperties.PLAYER)
                and cls._logger.isEnabledFor(WARNING)):
            cls._logger.warning(
                f'{SettingsProperties.PLAYER}, not supported by voicing engine: '
                f'{engine_id}')
        previous_value = Settings.get_player_id(engine_id=engine_id)
        changed = previous_value != value
        Settings.set_player(value, engine_id)
        return changed

    @classmethod
    def get_current_engine_id(cls) -> str:
        """

        @return:
        """
        return Settings.get_engine_id()

    @classmethod
    def is_current_engine(cls, engine: ForwardRef('BaseEngineService')) -> bool:
        return engine.engine_id == cls.get_current_engine_id()

    @classmethod
    def get_alternate_engine_id(cls) -> str:
        """
        The alternate engine is used when the current engine cannot voice
        text in a timely fashion. Typicaly  this is when the current engine
        is slower, higher quality, possibly from a remote service.

        :return:
        """
        return Settings.get_alternate_engine_id()

    @classmethod
    def is_alternate_engine(cls, engine: ForwardRef('BaseEngineService')) -> bool:
        return engine.engine_id == cls.get_alternate_engine_id()

    @classmethod
    def is_active_engine(cls, engine: ForwardRef('BaseEngineService')) -> bool:
        return cls.is_current_engine(engine) or cls.is_alternate_engine(engine)

    def is_current_engine(self) -> bool:
        clz = type(self)
        return clz.is_current_engine(self)

    def is_alternate_engine(self) -> bool:
        clz = type(self)
        return clz.is_alternate_engine(self)

    def is_active_engine(self) -> bool:
        clz = type(self)
        return clz.is_active_engine(self)

    @classmethod
    def insertPause(cls, ms=500):
        """Insert a pause of ms milliseconds

        May be overridden by sublcasses. Default implementation sleeps for ms.
        """
        Monitor.exception_on_abort(ms / 1000.0)

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
        #    new = clz.getSetting(s)
        #    if old is not None and new != old:
        #        changed = True
        return changed

    def _stop(self):
        self.stop()

    def _close(self):
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
    kodi_player_state: KodiPlayerState = KodiPlayerState.PLAYING_STOPPED

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)
        # self.active: bool = False
        self.process = None
        BaseServices.register(self)
        KodiPlayerMonitor.register_player_status_listener(
                self.kodi_player_state_listener,
                f'{clz.service_ID}_Player_Monitor')

    def init(self):
        """

        @return:
        """
        super().init()
        clz = type(self)
        # self.active = True

    def destroy(self):
        """
        Destroy this engine and any dependent players, etc. Typically done
        when either stopping TTS (F12) or shutdown, or switching engines, etc.

        :return:
        """
        pass
        clz = type(self)
        # KodiPlayerMonitor.unregister_player_status_listener(f'{
        # clz.service_ID}_Player_Monitor')

    def kodi_player_state_listener(self, kodi_player_state: KodiPlayerState) -> None:
        clz = type(self)
        clz.kodi_player_state = kodi_player_state
        clz._logger.debug(f'KODI_PLAYER_STATE: {kodi_player_state}')
        if kodi_player_state == KodiPlayerState.PLAYING:
            self._stop()

    def say(self, phrases: PhraseList):
        """

        @param phrases:
        @return:
        """
        EngineQueue.say(phrases, self)

    def say_phrase(self, phrase: Phrase) -> None:
        """
            Say a single phrase. This is a separate method just so that
            when an expensive speech engine does not have the voiced phrase
            already cached, another engine can be used to say the phrase

        :param phrase:
        :return:
        """
        EngineQueue.say_phrase(phrase, self)

    def say_file(self, phrase: Phrase, player_id: str) -> None:
        EngineQueue.say_file(phrase, player_id, self)

    def isSpeaking(self) -> bool:
        """

        @return:
        """
        return EngineQueue.isSpeaking()

    def _stop(self):
        EngineQueue.stop()
        super()._stop()

    def threadedSay(self, phrase: Phrase):
        """Method accepting text to be spoken

        Subclasses must override this method and should speak the unicode text.
        Speech interruption is implemented in the stop() method.
        """
        raise Exception('Not Implemented')

    def _close(self):
        # self.active = False
        super()._close()
        EngineQueue.empty_queue()


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
        super().init()

    def destroy(self):
        """
        Destroy this engine and any dependent players, etc. Typicaly done
        when either stopping TTS (F12) or shutdown, or switching engines, etc.

        :return:
        """
        pass
        clz = type(self)

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
        clz = type(self)
        assert isinstance(mode, int), 'Bad mode'
        if mode == Mode.PIPE:
            pass
        if mode == Mode.FILEOUT:
            if clz._logger.isEnabledFor(DEBUG):
                clz._logger.debug('Mode: FILEOUT')
        elif mode == Mode.ENGINESPEAK:
            audio.load_snd_bm2835()
            if clz._logger.isEnabledFor(DEBUG):
                clz._logger.debug('Mode: ENGINESPEAK')

        self.mode: Mode = mode

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

        volume = Settings.getSetting(SettingsProperties.VOLUME,
                                     self.get_current_engine_id())
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

    def runCommandAndPipe(self, phrase: Phrase) -> BinaryIO:
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
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose('tmpfile: ' + fpath)

        self.runCommand(text, fpath)
        return open(fpath, 'rb')
    '''

    def config_mode(self):
        """

        """
        clz = type(self)
        clz._logger.debug(f'In base.config_mode')

        player_id: str = Settings.get_player_id(clz.engine_id)

        if player_id == Players.INTERNAL:
            mode = Mode.ENGINESPEAK
        elif Settings.uses_pipe(clz.engine_id):
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
            self.initialize_player()
            self.config_mode()
            text: str = phrase.get_text()
            if phrase.get_interrupt():
                self.stop_player(now=True)

            clz._logger.debug(f'mode: {self.mode}')
            if self.mode == Mode.FILEOUT:
                outFile: str
                exists: bool
                use_cache: bool = Settings.is_use_cache(clz.engine_id)
                VoiceCache.get_path_to_voice_file(phrase, use_cache=use_cache)
                out_file: Path = phrase.get_cache_path()
                if not self.runCommand(phrase):
                    return

                player: IPlayer = self.get_player(self.engine_id)
                if player:  # if None, then built-in
                    player.play(phrase)
            elif self.mode == Mode.PIPE:
                source: BinaryIO = self.runCommandAndPipe(phrase)
                if not source:
                    return
                player: IPlayer = self.get_player(self.engine_id)
                if player:
                    player.pipe(source, phrase)
            else:
                clz._simpleIsSpeaking = True
                self.runCommandAndSpeak(phrase)
                clz._simpleIsSpeaking = False
        except ExpiredException:
            clz._logger.debug('EXPIRED')
        except Exception as e:
            clz._logger.exception('')

    def initialize_player(self):
        """
        Ensure that player is initialized before playing. Some engines
        may want to override this method, particularly if they use a built-in
        player.

        :return:
        """
        clz = type(self)
        try:
            player: IPlayer = self.get_player(self.engine_id)
            if player:
                player.init(clz.engine_id)
        except Exception as e:
            clz._logger.exception('')

    def stop_player(self, now: bool = True):
        """
        Stop player (most likely because current text is expired)
        Engines may wish to override this method, particularly when
        the player is built-in.

        :return:
        """
        clz = type(self)
        try:
            player: IPlayer = self.get_player(self.engine_id)
            if player:
                player.stop(now=now)
        except Exception as e:
            clz._logger.exception('')

    def isSpeaking(self) -> bool:
        """

        @return:
        """
        clz = type(self)
        speaking: bool = (clz._simpleIsSpeaking
                          or ThreadedTTSBackend.isSpeaking(self))
        return speaking

    def _stop(self):
        ThreadedTTSBackend._stop(self)

    def _close(self):
        #  super()._close()
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


EngineQueue.init()
TTSBackendBridge.setBaseBackend(BaseEngineService)
