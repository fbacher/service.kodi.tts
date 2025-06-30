# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import queue
import sys
import tempfile
import threading
from pathlib import Path

from backends.ispeech_generator import ISpeechGenerator
from backends.settings.service_types import ServiceID, ServiceKey, Services, TTS_Type
from backends.settings.service_unavailable_exception import ServiceUnavailable
from cache.cache_file_state import CacheFileState
from common import *

from backends.audio.sound_capabilities import ServiceType, SoundCapabilities
from backends.i_tts_backend_base import ITTSBackendBase
from backends.players.iplayer import IPlayer
from backends.settings.constraints import Constraints
from backends.settings.i_validators import INumericValidator, IValidator, UIValues
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import TTSNumericValidator
from backends.tts_backend_bridge import TTSBackendBridge
from cache.voicecache import VoiceCache
from common.base_services import BaseServices
from common.constants import Constants
from common.deprecated import deprecated
from common.exceptions import ExpiredException
from common.garbage_collector import GarbageCollector
from common.kodi_player_monitor import KodiPlayerMonitor, KodiPlayerState
from common.logger import *
from common.message_ids import MessageId
from common.messages import Messages
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import AudioType, Genders, PlayerMode, Players
from common.settings import Settings
from common.settings_low_level import SettingProp
from common.utils import TempFileUtils

MY_LOGGER = BasicLogger.get_logger(__name__)


class EngineQueue:
    """
    There is a single EngineQueue which all voiced text must flow through.
    The queue can be purged when text expires (when a movie starts to play or
    due to user input, etc.).
    """

    class QueueItem:

        def __init__(self, phrase: Phrase, engine: 'BaseEngineService'):
            self._phrase: Phrase = phrase
            self._engine: Union[ForwardRef('BaseEngineService'), ForwardRef('SimpleTTSBackend')]
            self._engine = engine

        @property
        def phrase(self) -> Phrase:
            return self._phrase

        @property
        def engine(self) -> 'SimpleTTSBackend':
            return self._engine

    kodi_player_state: KodiPlayerState = None
    _instance: 'EngineQueue' = None

    def __init__(self):
        clz = type(self)
        # active_queue is True as long as there is a configured active_queue engine

        self.active_queue: bool = False
        self.tts_queue: queue.Queue = queue.Queue(100)
        self._threadedIsSpeaking = False  # True if engine is ThreadedTTSBackend
        self.queue_processor: threading.Thread | None = None

    @classmethod
    def kodi_player_status_listener(cls, player_state: KodiPlayerState) -> None:
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'PLAYER_STATE: {player_state}')
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
                    target=cls._instance._handleQueue, name=f'EngnQue')
            #  MY_LOGGER.debug(f'Starting queue_processor EngineQueue')
            cls._instance.queue_processor.start()
            GarbageCollector.add_thread(cls._instance.queue_processor)

    '''
    @classmethod
    def queue(cls) -> 'EngineQueue':
        return cls._instance
    '''

    def _handleQueue(self):
        clz = type(self)
        #  if MY_LOGGER.isEnabledFor(DEBUG):
        #      MY_LOGGER.debug(f'Threaded EngineQueue started')
        try:
            while self.active_queue and not Monitor.wait_for_abort(timeout=0.02):
                item: EngineQueue.QueueItem | None = None
                try:
                    item = self.tts_queue.get(timeout=0.0)
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Queue item phrase: {item.phrase}')
                    self.tts_queue.task_done()  # TODO: Change this to use phrase delays
                    phrase: Phrase = item.phrase
                    if (clz.kodi_player_state == KodiPlayerState.PLAYING_VIDEO and not
                            phrase.speak_over_kodi):
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'skipping play of {phrase.debug_data()} '
                                            f'speak while playing: '
                                            f'{phrase.speak_over_kodi}',
                                            trace=Trace.TRACE_AUDIO_START_STOP)
                        continue
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Start play of {phrase.debug_data()} '
                                        f'on {item.engine.service_id}')
                                        #  trace=Trace.TRACE_AUDIO_START_STOP)
                    self._threadedIsSpeaking = True
                    engine: 'SimpleTTSBackend' = item.engine
                    # MY_LOGGER.debug(f'queue.get {phrase.get_text()} '
                    #                   f'engine: {item.engine.setting_id}')
                    engine.threadedSay(phrase)
                    #  MY_LOGGER.debug(f'Return from threadedSay {phrase.debug_data()}',
                    #                    trace=Trace.TRACE_AUDIO_START_STOP)
                    self._threadedIsSpeaking = False
                except queue.Empty:
                    # MY_LOGGER.debug_v('queue empty')
                    pass
                except AbortException:
                    return  # Let thread die
                except ValueError as e:
                    MY_LOGGER.exception('')
                except ExpiredException:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'EXPIRED {item.phrase.debug_data} ',
                                          trace=Trace.TRACE_AUDIO_START_STOP)
                except Exception:
                    MY_LOGGER.exception('')
        except AbortException:
            return  # Let thread die

        self.active_queue = False

    @classmethod
    def empty_queue(cls):
        # MY_LOGGER.debug(f'empty_queue')
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
        # if not engine.is_active_engine():
        #     return
        try:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'phrase: {phrases[0].get_text()} '
                                f'Engine: {engine.service_id} '
                                f'Interrupt: {phrases.interrupt}'
                                f' debug: {phrases[0].debug_data()}')
        except ExpiredException:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('EXPIRED')
        if phrases[0].interrupt:
            phrases.set_expired()
            return
        try:
            phrase: Phrase
            for phrase in phrases:
                if not phrase.is_empty():
                    cls.say_phrase(phrase, engine)
        except ExpiredException:
            MY_LOGGER.debug('EXPIRED')

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
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'{phrase.debug_data()}')
            interrupt: bool = phrase.get_interrupt()
            if interrupt:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'INTERRUPTED discarding any phrases prior to:'
                                    f' {phrase.short_text()}')
                cls.empty_queue()
            engine.stop_current_phrases()

            zelf.tts_queue.put_nowait(EngineQueue.QueueItem(phrase, engine))
            '''
            MY_LOGGER.debug(f'phrase: {phrase.get_text()} ' 
                              f'Engine: {engine.setting_id}')
            cache_path: Path
            if phrase.text_exists():
                #  TODO: Add ability to deal with converter
                #  Bypass engine and go straight to playing
                player_id: str = Settings.get_player(engine.setting_id)
                zelf.say_file(phrase, player_id, engine)
            else:
                MY_LOGGER.debug(f'queue.put {phrase.get_text()}')
                zelf.tts_queue.put_nowait(EngineQueue.QueueItem(phrase, engine))
            MY_LOGGER.debug(f'Put on queue')
            '''
        except ExpiredException:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('EXPIRED')

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
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'phrase: {phrase.get_text()} '
                                  f'Engine: {engine.service_id}')
            cls.say_phrase(phrase, engine)
            '''
            player: IPlayer = PlayerIndex.get_player(player_id)
            player.init(engine.setting_id)
            player.play(phrase)
            '''
        except AbortException as e:
            reraise(*sys.exc_info())
        except ExpiredException:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('EXPIRED')
        except Exception as e:
            MY_LOGGER.exception(f'Exception {phrase.debug_data}'
                                  f' engine: {engine.service_id}',
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
            MY_LOGGER.exception('')
            speaking = False
        return speaking

    @classmethod
    def get_kodi_player_state(cls, kodi_player_state: KodiPlayerState) -> None:
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'EngineQueue SET_KODI_PLAYER_STATE: {kodi_player_state}')
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
    _current_engine: ITTSBackendBase = None

    _class_name: str = None
    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    service_key: ServiceID
    _baseEngine: 'BaseEngineService' = None
    tmp_dir: Path | None = None

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(*args, **kwargs)

        clz._class_name = self.__class__.__name__
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

    def get_output_audio_type(self) -> AudioType:
        raise NotImplementedError('')

    def get_player(self, service_key: ServiceID) -> IPlayer:
        """
         Gets the player instance for the given engine. If settings are changed
         then the new player will be instantiated.

         :param service_key: key for identifying the engine Settings.get_player
                             will adjust the engine's service_key appropriately.
        """

        clz = type(self)
        player_key: ServiceID = Settings.get_player(service_key)
        #  MY_LOGGER.debug(f'player_key: {player_key}')
        if self.player is not None and player_key != self.player.service_key:
            # Stop old player
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Killing player(s) because player_id changed '
                                f'from {self.player.service_key} to {player_key}')
            self.player.destroy()

        #  MY_LOGGER.debug(f'player_key: {player_key}')
        if self.player is None or player_key != self.player.service_key:
            try:
                self.player = BaseServices.get_service(player_key)
            except ServiceUnavailable:
                self.player = None
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

    def get_transcoder(self, service_key: ServiceID, target_audio) -> ServiceID | None:
        """
        Finds a audio converter (typically a player or specialized tool)
        which can convert between the audio formats producable by the engine
        and a player.

        SoundCapabilities are used to make the negotiation

        :param service_key:
        :param target_audio:
        :return:
        """
        Monitor.exception_on_abort(0.05)
        transcoder_key: ServiceID = ServiceID(ServiceType.TRANSCODER,
                                              service_id=service_key.service_id)
        converter_key: str | None = Settings.get_setting_str(transcoder_key,
                                                             ignore_cache=False,
                                                             default=None)
        if converter_key is None:
            engine_output_formats: List[AudioType]
            engine_output_formats = SoundCapabilities.get_output_formats(service_key)
            if AudioType.MP3 in engine_output_formats:
                # No converter needed, need to check player
                return None
            # Shouldn't get here with this
            if (len(engine_output_formats) == 1 and
                    AudioType.BUILT_IN in engine_output_formats):
                return None

            player_input_formats: List[AudioType] = [AudioType.MP3]
            candidate_converters: List[ServiceID] = \
                SoundCapabilities.get_capable_services(ServiceType.TRANSCODER,
                                                       engine_output_formats,
                                                       player_input_formats)
            converter_id = None
            if len(candidate_converters) > 0:
                converter_id = candidate_converters[0]

        return transcoder_key

    @classmethod
    def create_speech_generator(self) -> ISpeechGenerator | None:
        return None

    @classmethod
    def has_speech_generator(cls) -> bool:
        return False

    '''
    @classmethod
    def get_validator(cls, setting_id: str,
                      setting_id: str) -> ConstraintsValidator | IValidator:
        return SettingsMap.get_validator(setting_id=setting_id,
                                         setting_id=setting_id)

    @classmethod
    def get_bool_validator(cls, setting_id, str,
                           setting_id: str) -> BoolValidator | IValidator:
        return SettingsMap.get_validator(setting_id=setting_id,
                                         setting_id=setting_id)
    '''
    def change_speed(self, faster: bool) -> str:
        """
        Increases/decreases speed by one unit. The change is immediate and not
        persisted.

        :param faster:
        :return:
        """
        speed_val: INumericValidator | TTSNumericValidator
        speed_val = SettingsMap.get_validator(ServiceKey.SPEED)
        if speed_val is None:
            raise NotImplementedError
        orig_speed: float = speed_val.get_value()
        new_speed: float = speed_val.adjust(faster)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'orig_speed: {orig_speed} NEW_SPEED: {new_speed}')
        msg_id: MessageId = MessageId.SPEED_UP
        if not faster:
            msg_id = MessageId.SLOW_DOWN
        label: str = msg_id.get_formatted_msg(f'{new_speed:.1f}')
        return label

    def change_volume(self, louder: bool) -> str:
        """
          Decreases the TTS volume. Does NOT impact Kodi's volume (not persisted)

          :louder: If True, then increase the volume by one unit, otherwise decrease
                   the volume
          :return: Translated message describing what was done
          """
        volume_val: INumericValidator | TTSNumericValidator
        volume_val = SettingsMap.get_validator(ServiceKey.VOLUME)
        if volume_val is None:
            raise NotImplementedError
        new_value: float = volume_val.adjust(louder)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Volume louder: {louder}: {new_value}')
        if louder:
            label: str = MessageId.VOLUME_UP_DB.get_formatted_msg(f'{new_value:.1f}')
        else:
            label: str = MessageId.VOLUME_DOWN_DB.get_formatted_msg(f'{new_value:.1f}')
        return label

    def flagAsDead(self, reason=''):
        self.dead = True
        self.deadReason = reason or self.deadReason

    '''
    @classmethod
    def get_constraints(cls, setting: str) -> Constraints | None:
        """

        @param setting:
        @return:
        """
        transcoder_key: ServiceID = ServiceID(ServiceType.TRANSCODER,
                                              service_id=cls.service_key.service_id)
        converter_key: str | None = Settings.get_setting_str(transcoder_key,
                                                             ignore_cache=False,
                                                             default=None)
        constraints: Constraints | None = cls.TTSConstraints.get(setting)
        return constraints
    '''
    '''
    @classmethod
    def isSettingSupported(cls, setting_id: str):
        return cls.is_valid_property(cls.service_id, setting_id)
    '''
    '''
    @classmethod
    def getSettingNames(cls) -> List[str]:
        """
        Gets a list of setting names/keys that this backend uses

        :return:
        """
        settingNames: List[str] = []
        for settingName in cls.settings.keys():
            settingNames.append(settingName)

        return settingNames
    '''

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

    '''
    @classmethod
    def getConstraints(cls, setting_id: str) -> Constraints | None:

        return cls.constraints.get(setting_id)
    '''

    @classmethod
    def negotiate_engine_config(cls, engine_key: ServiceID, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        """
        Player is informing engine what it is capable of controlling
        Engine replies what it is allowing player to control
        """
        return True, True, True

    '''
    @classmethod
    def settingList(cls, setting, *args):
        """Returns a list of options for a setting

        May be overridden by subclasses. Default implementation returns None.
        """
        return None
    '''

    @classmethod
    @deprecated  # Use validator
    def setting(cls, setting):

        #  TODO: Replace with getSetting
        """Returns a backend setting, or default if not set
        """
        return cls.getSetting(setting, cls.get_setting_default(setting))

    @classmethod
    @deprecated  # Use validator
    def getLanguage(cls):
        default_locale = Constants.LOCALE.lower().replace('_', '-')
        return cls.getSetting(SettingProp.LANGUAGE, default_locale)

    @classmethod
    @deprecated  # Use validator
    def getGender(cls):
        gender = cls.getSetting(SettingProp.GENDER, Genders.UNKNOWN)

        return gender

    @classmethod
    @deprecated  # Use validator
    def getVoice(cls):
        voice = cls.getSetting(SettingProp.VOICE, '')
        return voice

    @classmethod
    def temp_dir(cls) -> Path:
        """
        Controls the tempfile and tempfile.NamedTemporaryFile 'dir' entry
        used to create temporary audio files. A None value allows tempfile
        to decide.
        :return:
        """
        if cls.tmp_dir is None:
            tmpfs: Path | None = None
            tmpfs = TempFileUtils.getTmpfs()
            if tmpfs is None:
                tmpfs = Path(Constants.PROFILE_PATH)
                tmpfs = tmpfs / 'kodi_speech'
                #  tempfile.TemporaryDirectory(dir=tmpfs, delete=True)
            if not tmpfs.exists():
                tmpfs.mkdir(parents=True)
            cls.tmp_dir = tmpfs
        return cls.tmp_dir

    @classmethod
    def tmp_file(cls, file_type: str) -> tempfile.NamedTemporaryFile:
        tmp_dir: Path = cls.temp_dir()
        tmp_file = tempfile.NamedTemporaryFile(mode='w+b', buffering=-1,
                                               suffix=file_type,
                                               prefix=None,
                                               dir=tmp_dir,
                                               delete=False)
        return tmp_file

    def get_voice_cache(self) -> VoiceCache:
        raise NotImplementedError()

    @classmethod
    def update_voice_path(cls, phrase: Phrase) -> None:
        raise NotImplementedError(f'active_engine: {Settings.get_engine_key()} \n'
                                  f'alt: {Settings.get_alternate_engine_id()}')
    '''
    @classmethod
    def getVolumeDb(cls) -> float | None:
        # Get the converter from TTS volume scale to the Engine's Scale
        # Get the Engine validator/converter

        # The engine can also act as player.
        # if engine is player, then set volume via engine
        # otherwise, fix volume to 'TTS standard volume' of 0db and let
        # player adjust it from there.

        volume_validator: ConstraintsValidator | IValidator
        volume_validator = SettingsMap.get_validator(cls.setting_id,
                                                     setting_id=SettingProp.VOLUME)
        volume, _, _, _ = volume_validator.get_tts_values()
        return volume  # Find out if used
    '''
    '''
    @classmethod
    def getEngineVolume(cls) -> float:
        """
        The Engine's job is to make sure that it's output volume is equal to
        the TTS standard volume. Get the TTS volume from Settings
        setting_id=Services.TTS, setting_id='volume'. Then use the validators
        and converters to adjust the engine's volume to match what TTS has
        in the settings.

        The same is true for every stage: engine, player, converter, etc.
        """

        return cls.getVolumeDb()
    '''
    '''
    @classmethod
    def getEngineVolume_str(cls) -> str:
        volume_validator: ConstraintsValidator
        volume_validator = cls.get_validator(cls.service_id,
                                             property_id=SettingProp.VOLUME)
        volume: str = volume_validator.getUIValue()
        return volume
    '''

    @classmethod
    def getSetting(cls, setting_id: str,  default=None):
        """
        Gets a setting from addon's settings.xml

        A convenience method equivalent to
        Settings.getSetting(key + '.'. + cls.setting_id,
        default, useFullSettingName).

        :param setting_id:
        :param default:
        :return:
        """
        if default is None:
            default = cls.get_setting_default(setting_id)

        return Settings.getSetting(cls.service_key.with_prop(setting_id),
                                   default)

    '''
    @classmethod
    def setSettingConstraints(cls,
                   setting_id: str,
                   constraints: Constraints
                   ) -> bool:
        """
        Saves a setting to addon's settings.xml

        A convenience method for Settings.setSetting(key + '.' + cls.setting_id, value)

        :param constraints:
        :param setting_id:
        :return:
        """
        if not isinstance(constraints, Constraints):
            MY_LOGGER.error(f'setSettingConstrants with non-constraint: '
                              f'{type(constraints)}')
            return False
        return Settings.setSettingConstraints(setting_id, constraints)
        
        if (not cls.isSettingSupported(setting_id)
                and MY_LOGGER.isEnabledFor(WARNING)):
            MY_LOGGER.warning(f'Setting: {setting_id}, not supported by voicing '
                                f'engine: {cls.get_service_key()}')
        previous_value = Settings.getSetting(setting_id, cls.get_service_key(),  None)
        changed = False
        if previous_value != value:
            changed = True
        Settings.setSetting(setting_id, value, cls.setting_id)
        return changed
        '''
    '''
    @classmethod
    def set_player_setting(cls, value: str) -> bool:
        setting_id: str = cls.get_current_engine_id()
        if (not cls.isSettingSupported(SettingProp.PLAYER)
                and MY_LOGGER.isEnabledFor(WARNING)):
            MY_LOGGER.warning(
                f'{SettingProp.PLAYER}, not supported by voicing engine: '
                f'{setting_id}')
        previous_value = Settings.get_player(setting_id=setting_id)
        changed = previous_value != value
        Settings.set_player(value, setting_id)
        return changed
    '''

    @classmethod
    @deprecated
    def get_current_engine_id(cls) -> str:
        """

        @return:
        """
        return Settings.get_engine_key().service_key

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
    def is_active_engine(cls, engine: ForwardRef('BaseEngineService') = None) -> bool:
        return cls.is_current_engine(engine) or cls.is_alternate_engine(engine)

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

    def stop_current_phrases(self):
        pass

    def close(self):
        """Close the speech engine

        Subclasses should override this to clean up after themselves.
        Default implementation does nothing.
        """
        pass

    '''
    def _update(self):
        changed = self._updateSettings()
        if changed:
            return self.update()
    '''
    '''
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
    '''

    def _stop(self):
        self.stop()

    def _close(self):
        self._closed = True
        self._stop()

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
    kodi_player_state: KodiPlayerState = KodiPlayerState.VIDEO_PLAYER_IDLE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        self.process = None
        BaseServices.register(self)
        KodiPlayerMonitor.register_player_status_listener(
                self.kodi_player_state_listener,
                f'{clz.service_id}_Player_Monitor')

    def init(self):
        """

        @return:
        """
        super().init()
        clz = type(self)

    def destroy(self):
        """
        Destroy this engine and any dependent players, etc. Typically done
        when either stopping TTS (F12) or shutdown, or switching engines, etc.

        :return:
        """
        pass
        clz = type(self)
        # KodiPlayerMonitor.unregister_player_status_listener(f'{
        # clz.setting_id}_Player_Monitor')

    def kodi_player_state_listener(self, kodi_player_state: KodiPlayerState) -> None:
        clz = type(self)
        clz.kodi_player_state = kodi_player_state
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'KODI_PLAYER_STATE: {kodi_player_state}')
        if kodi_player_state == KodiPlayerState.PLAYING_VIDEO:
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
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        clz._simpleIsSpeaking = False
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

    '''
    def set_player_mode(self, player_mode: PlayerMode) -> None:
        """

        @param player_mode:
        """
        clz = type(self)
        assert isinstance(player_mode, PlayerMode), 'Bad mode'
        if player_mode == PlayerMode.PIPE:
            pass
        if player_mode == PlayerMode.FILE:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Mode: {player_mode.value()}')
        elif player_mode == PlayerMode.ENGINE_SPEAK:
            audio.load_snd_bm2835()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Mode: {player_mode.value()}')

        self.player_mode = player_mode
    '''

    def get_voice_cache(self) -> VoiceCache:
        raise NotImplementedError

    @classmethod
    def get_voice(cls) -> str:
        voice: str = Settings.get_voice(cls.service_key)
        return voice

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
        volume_key: ServiceID = Settings.get_engine_key().with_prop(SettingProp.VOLUME)
        volume = Settings.getSetting(volume_key)
        return volume

    def runCommand(self, phrase: Phrase):
        """Convert text to speech and output to a .wav file

        If using PlayerMode.FILE, subclasses must override this method
        and output a .wav or .mp3 file to outFile (depending upon player capability),
         returning True if a file was
        successfully written and False otherwise.
        """
        raise NotImplementedError()

    def say_phrase(self, phrase: Phrase) -> None:
        return super().say_phrase(phrase)

    def get_cached_voice_file(self, phrase: Phrase,
                              generate_voice: bool = True) -> CacheFileState:
        """
        Assumes that cache is used. Normally missing voiced files are placed in
        the cache by an earlier step, but can be initiated here as well.

        Very similar to runCommand, except that the cached files are expected
        to be sent to a slave player, or some other player than can play a sound
        file.
        :param phrase: Contains the text to be voiced as wll as the path that it
                       is or will be located.
        :param generate_voice: If true, then wait a bit to generate the speech
                               file.
        :return: True if the voice file was handed to a player, otherwise False
        """
        raise NotImplementedError()

    def runCommandAndSpeak(self, phrase: Phrase):
        """Convert text to speech and output directly

        If using PlayerMode.ENGINE_SPEAK, subclasses must override this method
        and speak text and should block until speech is complete.
        """
        raise NotImplementedError('runCommandAndSpeak')

    def runCommandAndPipe(self, phrase: Phrase) -> BinaryIO:
        """Convert text to speech and pipe to audio player

        If using PlayersModes.PIPE, subclasses must override this method
        and return an open pipe to wav or mp3 data, depending upon player
        capability
        """
        raise NotImplementedError()

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
            #  self.config_mode()
            player_mode: PlayerMode = Settings.get_player_mode(self.service_key)
            if phrase.get_interrupt():
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'stop_player phrase prior to: {phrase}')
                kill: bool = True
                if player_mode in (PlayerMode.SLAVE_FILE, PlayerMode.SLAVE_PIPE):
                    kill = False
                self.stop_player(purge=True)

            #  MY_LOGGER.debug(f'player_mode: {player_mode} engine: {self.service_id}')
            if player_mode == PlayerMode.FILE:
                # MY_LOGGER.debug('runCommand')
                # outFile: str
                # text_exists: bool
                # use_cache: bool = Settings.is_use_cache(clz.setting_id)
                # VoiceCache.get_path_to_voice_file(phrase, use_cache=use_cache)
                # out_file: Path = phrase.get_cache_path()

                # phrase contains the text to voice as well as the path to
                # write the voiced file to and whether the file already text_exists
                # in a cache, etc.

                if not self.runCommand(phrase):
                    return

                player: IPlayer = self.get_player(clz.service_key)
                if player:  # if None, then built-in
                    phrase.add_event('About to play')
                    player.play(phrase)
            elif player_mode == PlayerMode.SLAVE_FILE:
                # Typically used with caching. If the voiced file does not
                # yet exist, then it is created using the path and other info
                # in the Phrase. Then the Slave Player is given the phrase via
                # pipe or other file so that it can play the file. Slaves avoid
                # the cost of Python I/O on the voiced file as well as the cost
                # of exec'ing the player.
                if Settings.is_use_cache():  # or not Settings.is_use_cache():
                    if not self.get_cached_voice_file(phrase, generate_voice=True):
                        return
                else:
                    if not self.runCommand(phrase):
                        return
                player: IPlayer = self.get_player(clz.service_key)
                player.slave_play(phrase)

            elif player_mode == PlayerMode.PIPE:
                source: BinaryIO = self.runCommandAndPipe(phrase)
                if not source:
                    return
                player: IPlayer = self.get_player(clz.service_key)
                if player:
                    player.pipe(source, phrase)
            else:   # PlayerMode.EngineSpeak
                clz._simpleIsSpeaking = True
                self.runCommandAndSpeak(phrase)
                clz._simpleIsSpeaking = False
        except AbortException as e:
            reraise(*sys.exc_info())
        except ExpiredException:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('EXPIRED')
        except Exception as e:
            MY_LOGGER.exception('')

    def initialize_player(self):
        """
        Ensure that player is initialized before playing. Some engines
        may want to override this method, particularly if they use a built-in
        player.

        :return:
        """
        clz = type(self)
        try:
            player: IPlayer = self.get_player(clz.service_key)
            if player:
                player.init(clz.service_key)
        except AbortException as e:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

    def stop_player(self, purge: bool = True,
                    keep_silent: bool = False,
                    kill: bool = False):
        """
        Stop player (most likely because current text is expired)
        Engines may wish to override this method, particularly when
        the player is built-in.

        :param purge: if True, then purge any queued vocings
                      if False, then only stop playing current phrase
        :param keep_silent: if True, ignore any new phrases until restarted
                            by resume_player.
                            If False, then play any new content
        :param kill: If True, kill any player processes. Implies purge and
                     keep_silent.
                     If False, then the player will remain ready to play new
                     content, depending upon keep_silent
        :return:
        """
        clz = type(self)
        try:
            player: IPlayer = self.get_player(clz.service_key)
            if player:
                player.stop_player(purge=purge, keep_silent=keep_silent,
                                   kill=kill)
        except AbortException as e:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

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
    engine_id = 'log'
    displayName = 'Log'
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
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
