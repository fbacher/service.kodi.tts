# coding=utf-8

"""
    Module responsible for configuring Kodi TTS. Works with SettingsDialog,
    Settings, SettingsHelper and others to maintain settings. Primary
    Objectives:
        * Maintain a working system. Able to switch to a fail-safe
          mode that can minimally operate with no TTS engine nor player_key.
          Have sufficient functionality to guide user through configuring
          a usable system.
        * Users will interact through SettingsDialog, but also work
         in a limited way 'headless', without user intervention in support
         of the first objective
        * The UI (SettingsDialog) is concerned with presentation while
          this module is responsible for configuration, validation and
          maintaing the settings.
"""
from __future__ import annotations


import xbmc

import langcodes
from backends.backend_info import BackendInfo
from backends.base import *
from backends.settings.i_validators import (IBoolValidator, INumericValidator,
                                            IStringValidator)
from backends.settings.language_info import LanguageInfo
from backends.settings.service_types import (GENERATE_BACKUP_SPEECH, PlayerType,
                                             ServiceKey, ServiceID)
from backends.settings.service_unavailable_exception import ServiceUnavailable
from backends.settings.settings_helper import FormatType, SettingsHelper
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (AllowedValue, BoolValidator, StringValidator)
from common.exceptions import ConfigurationError
from common.logger import *
from common.setting_constants import (AudioType, Genders, GenderSettingsMap,
                                      Players)
from common.settings import Settings
from common.settings_low_level import SettingsLowLevel, SettingsManager
from backends.settings.service_types import ServiceID
from windowNavigation.choice import Choice

MY_LOGGER = BasicLogger.get_logger(__name__)


class EngineConfig:
    """
    Contains engine configuration
    """
    def __init__(self, engine_key: ServiceID, lang_info: LanguageInfo,
                 use_cache: bool | None = None,
                 player_id: str | None = None, engine_audio: AudioType | None = None,
                 player_mode: PlayerMode | None = None, transcoder: str | None = None,
                 trans_audio_in: AudioType | None = None,
                 trans_audio_out: AudioType | None = None,
                 volume: float | None = None,
                 speed: float | None = None,
                 repair_mode: bool = False,
                 repairs_made: bool = False) -> None:
        self._engine_key: ServiceID = engine_key
        self._lang_info: LanguageInfo = lang_info
        self._use_cache: bool | None = use_cache
        self._player_id: str | None = player_id
        self._engine_audio: AudioType | None = engine_audio
        self._player_mode: PlayerMode | None = player_mode
        self._transcoder: str | None = transcoder
        self._trans_audio_in: AudioType | None = trans_audio_in
        self._trans_audio_out: AudioType | None = trans_audio_out
        self._volume: float | None = volume
        self._speed: float | None = speed
        self._repair_mode: bool = repair_mode
        self._repairs_made: bool = repairs_made

    @property
    def engine_id(self) -> str:
        return self._engine_key.service_id

    @engine_id.setter
    def engine_id(self, engine_id: str) -> None:
        self._engine_key = ServiceID(ServiceType.ENGINE, engine_id)

    @property
    def engine_key(self) -> ServiceID:
        return self._engine_key

    @property
    def lang_info(self) -> LanguageInfo:
        return self._lang_info

    @lang_info.setter
    def lang_info(self, lang_info: LanguageInfo) -> None:
        self._lang_info = lang_info

    @property
    def use_cache(self) -> bool | None:
        return self._use_cache

    @use_cache.setter
    def use_cache(self, use_cache: bool | None) -> None:
        self._use_cache = use_cache

    @property
    def player_id(self) -> str | None:
        return self._player_id

    @player_id.setter
    def player_id(self, player_id: str | None) -> None:
        self._player_id = player_id

    @property
    def engine_audio(self) -> AudioType | None:
        return self._engine_audio

    @engine_audio.setter
    def engine_audio(self, engine_audio: AudioType | None) -> None:
        self._engine_audio = engine_audio

    @property
    def player_mode(self) -> PlayerMode | None:
        return self._player_mode

    @player_mode.setter
    def player_mode(self, player_mode: PlayerMode | None) -> None:
        self._player_mode = player_mode

    @property
    def transcoder(self) -> str | None:
        return self._transcoder

    @transcoder.setter
    def transcoder(self, transcoder: str) -> None:
        self._transcoder = transcoder

    @property
    def trans_audio_in(self) -> AudioType | None:
        return self._trans_audio_in

    @trans_audio_in.setter
    def trans_audio_in(self, trans_audio_in: str | None) -> None:
        self._trans_audio_in = trans_audio_in

    @property
    def trans_audio_out(self) -> AudioType | None:
        return self._trans_audio_out

    @trans_audio_out.setter
    def trans_audio_out(self, trans_audio_out: str | None) -> None:
        self._trans_audio_out = trans_audio_out

    @property
    def volume(self) -> float | None:
        return self._volume

    @volume.setter
    def volume(self, volume: float | None) -> None:
        self._volume = volume

    @property
    def speed(self) -> float | None:
        return self._speed

    @speed.setter
    def speed(self, speed: float | None) -> None:
        self._speed = speed

    @property
    def repair_mode(self) -> bool:
        return self._repair_mode

    @repair_mode.setter
    def repair_mode(self, repair_mode: bool) -> None:
        self._repair_mode = repair_mode

    @property
    def repairs_made(self) -> bool:
        return self._repairs_made

    @repairs_made.setter
    def repairs_made(self, repairs_made: bool) -> None:
        self._repairs_made = repairs_made


class Configure:
    """
    Configure Kodi TTS
    """

    _instance: Union[ForwardRef('Configure'), None] = None

    def __init__(self) -> None:
        xbmc.log('In init via xbmc.log', xbmc.LOGDEBUG)
        xbmc.log(f'MY_LOGGER: {MY_LOGGER}')
        MY_LOGGER.info(f'In init')
        self.engine_instance = None
        self.saved_choices = None
        self.saved_selection_index = None
        self._original_stack_depth: int = -1
        self._saved_choices: List[Choice] | None = None
        self._saved_selection_index: int | None = None
        self._speed_val: INumericValidator | NumericValidator | None = None
        self._volume_val: INumericValidator | NumericValidator | None = None
        self.busy: bool = False

    @classmethod
    def instance(cls) -> Union[ForwardRef('Configure'), None]:
        if cls._instance is None:
            cls._instance = Configure()
            # Ensure some structures are built before we need them.
            SettingsHelper.build_allowed_player_modes()
        if cls._instance.busy:
            MY_LOGGER.debug(f'BUSY')
            return None
        cls._instance.busy = True
        MY_LOGGER.debug(f'instance None: {cls._instance is None}')
        return cls._instance

    @property
    def engine_key(self) -> ServiceID:
        """
            Gets the setting_id from Settings. If the value is invalid, substitutes
            with one designated as 'good'. If a substitution is performed, the
            substitute is stored in Settings
        TODO: Review. There should be only one method to get engine_id in consistent
              way.
        :return:
        """
        engine_key: ServiceID = Settings.get_engine_key()
        MY_LOGGER.info(f'service_key: {engine_key}')

        valid_engine: bool
        valid_engine = SettingsMap.is_available(engine_key)
        if not valid_engine:
            engine_id = BackendInfo.getAvailableBackends()[0].engine_id
            new_engine_key: ServiceID = ServiceID(ServiceType.ENGINE,
                                                  engine_id)
            MY_LOGGER.info(f'Invalid engine: {engine_key} replaced with:'
                           f' {new_engine_key}')
            Settings.set_engine(new_engine_key)
            engine_key = new_engine_key
        return engine_key

    @property
    def speed_val(self) -> INumericValidator:
        """

        :return:
        """
        if self._speed_val is None:
            self._speed_val = SettingsMap.get_validator(ServiceKey.SPEED)
            if self._speed_val is None:
                raise NotImplementedError
        return self._speed_val

    @property
    def volume_val(self) -> INumericValidator:
        """

        :return:
        """
        if self._volume_val is None:
            self._volume_val = SettingsMap.get_validator(ServiceKey.VOLUME)
            if self._volume_val is None:
                raise NotImplementedError
        return self._volume_val

    def getEngineInstance(self,
                          engine_key: ServiceID | None = None) -> ITTSBackendBase:
        """
        Gets an engine instance regardless if it is the active engine or not.
        Does NOT cause the active engine to change to a different enngine.
        :param engine_key:
        :return:
        """
        if engine_key is None:
            engine_key = self.engine_key
        MY_LOGGER.debug(f'service_key: {engine_key} type: {type(engine_key)}')
        engine_instance: ITTSBackendBase = BaseServices.get_service(engine_key)
        return engine_instance

    def configure_engine(self, choice: Choice,
                         repair: bool = False,
                         save_as_current: bool = False) -> EngineConfig | None:
        """
        Configures an engine with basic settings (player_key, etc.). Common code
        for select_engine and voice_engine.

        :param choice: Selected engine
        :param repair: Selects repair mode (See validate_repair)
        :param save_as_current: Sets the current engine as this engine
        :return:
        """
        try:
            engine_key: ServiceID = choice.engine_key
            current_engine_key: ServiceID = ServiceKey.CURRENT_ENGINE_KEY
            MY_LOGGER.debug(f'engine: {engine_key} current_engine: '
                            f'{Settings.get_engine_id()} '
                            f'repair: {repair}')
            # See if we can cfg engine
            engine_config: EngineConfig | None = None

            # This HACK provides a means to provide a limited set of
            # audio messages that is shipped with the addon. These
            # messages are used when either no engine or no player_key can
            # be configured. These messages are voiced using Kodi SFX
            # internal player_key. The messages should help the user install/
            # cfg an engine or player_key. See:
            # GENERATE_BACKUP_SPEECH, sfx_audio_player, no_engine and voicecache

            player_mode: PlayerMode | None = None
            player_id: str | None = None
            engine_audio: AudioType | None = None
            use_cache: bool | None = None
            if GENERATE_BACKUP_SPEECH:
                player_mode = PlayerMode.FILE
                player_id = PlayerType.SFX.value
                engine_audio = AudioType.WAV
                use_cache = True

            lang_info: LanguageInfo = choice.lang_info
            engine_config: EngineConfig | None = None
            try:
                MY_LOGGER.debug(f'configuring player with player_mode: {player_mode}')
                engine_config = self.configure_player(engine_key=engine_key,
                                                      lang_info=lang_info,
                                                      use_cache=use_cache,
                                                      player_id=player_id,
                                                      engine_audio=engine_audio,
                                                      player_mode=player_mode,
                                                      repair=repair)
            except ConfigurationError:
                MY_LOGGER.exception('Config Error')
                return None

            MY_LOGGER.debug(f'engine_config: engine_id: {engine_config.engine_id} '
                            f'use_cache: {engine_config.use_cache} '
                            f'player_id: {engine_config.player_id} '
                            f'engine_audio: {engine_config.engine_audio} '
                            f'player_mode: {engine_config.player_mode} '
                            f'transcoder: {engine_config.transcoder} '
                            f'trans_audio_in: {engine_config.trans_audio_in} '
                            f'trans_audio_out: {engine_config.trans_audio_out}'
                            f'lang_info: {lang_info}')
            engine_config.lang_info = lang_info
            self.set_lang_fields(engine_key=engine_key,
                                 lang_info=lang_info)
            self.set_gender_field(engine_key=engine_key)
            self.set_cache_speech_field(engine_key=engine_key,
                                        use_cache=engine_config.use_cache)
            MY_LOGGER.debug(f'Setting {engine_key}s player_mode to:'
                            f' {engine_config.player_mode}')
            self.set_player_mode_field(engine_key=engine_key,
                                       player_mode=engine_config.player_mode)
            self.set_player_field(engine_key=engine_key,
                                  player_id=engine_config.player_id)
            Settings.set_converter(engine_config.transcoder, engine_key)
            # Should not have to repair since validators should catch value
            # errors
            if not repair:
                self.set_speed_field(speed=1.0)
                self.set_volume_field(volume=0.0)
            if save_as_current:
                self.set_engine_field(engine_key=engine_key)
            return engine_config
        except Exception:
            MY_LOGGER.exception('')

    def get_player_mode_choices(self, engine_key: ServiceID,
                                player_id: str) -> Tuple[List[Choice], int]:
        """
        Determines which player_key modes are valid for the combination of engine
        and player_key.

        :param engine_key: engine to examine
        :param player_id: player_key to examine

        :return: Tuple[List[Choice], int] A list of valid choices and an index
                 to any choice matching the current player_mode.engine value,
                 or -1 if not match found
        """
        choices: List[Choice] = []
        found_idx: int = -1
        try:
            if not SettingsMap.is_valid_setting(engine_key.with_prop(
                    SettingProp.PLAYER_MODE)):
                MY_LOGGER.info(f'There are no PLAYER_MODEs for {engine_key}')
                return choices, found_idx
            current_choice: PlayerMode
            current_choice = Settings.get_player_mode(engine_key)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'current player_mode: {current_choice} '
                                f'engine: {engine_key} ')

            intersection: List[PlayerMode]
            intersection, found_idx = SettingsHelper.get_valid_player_modes(engine_key,
                                                                            player_id,
                                                                            current_choice)
            MY_LOGGER.debug(f'engine: {engine_key} '
                            f'found_idx: {found_idx} '
                            f'intersection: {intersection}')
            idx: int = 0
            for supported_mode in intersection:
                supported_mode: PlayerMode
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'supported_mode: {supported_mode.value} '
                                    f'enabled: True')
                choices.append(Choice(label=supported_mode.translated_name,
                                      value=supported_mode.value,
                                      choice_index=idx, enabled=True))

        except Exception as e:
            MY_LOGGER.exception('')
        return choices, found_idx

    def configure_player(self, engine_key: ServiceID,
                         lang_info: LanguageInfo,
                         use_cache: bool | None = None,
                         player_id: str | None = None,
                         engine_audio: AudioType | None = None,
                         player_mode: PlayerMode | None = None,
                         repair: bool = False) -> EngineConfig:
        """
        Configure a player_key and related settings for the given engine.
        The proposed configuration is returned.

        :param engine_key: REQUIRED. Specifies the engine being configured
        :param lang_info: Language information
        :param use_cache: If non-None, forces use or disuse of cache
        :param player_id: If non-None, forces to use a specific player_key
        :param engine_audio: If non-None, will cause audio to be produced in
                             the specified format (mp3 or wave) using a transcoder,
                             if needed.
        :param player_mode: If non-None, forces player_key mode to match (unless
                            invalid).
        :param repair: True preserves valid settings values. False sets some
                       settings to default values.
        :return:
        :raises ConfigurationError: if no valid configuration can be made
        """

        """
        Configuring a player_key can get messy because the engine, player_key,
        any cache, player_mode (depends on engine and player_key capabilities),
        transcoder, and audio type (wave/mp3/other). If use_cache is the default
        value None, then there is a strong bias to use caching. There is also 
        a strong bias to only cache mp3 files (due to the size of wave files). 
        If player_mode is None, then there is a bias to return PlayerMode.SLAVE_FILE
        and a player_key that can use it.
        
        This code does quite a bit of sanity checking and repair.

        Rough outline:
          If using internal engine player_mode, then your decisions are
          complete. The default is to use internal player_key if available.

          If GENERATE_BACKUP_SPEECH (not done by users) is set, then use_cache
          will be True, audio_type will be .wav and player_id will be SFX.
          This will force wave files to be generated and placed in the cache. 

          Otherwise, with use_cache and audio_type = None, then a configuration
          will be returned that specifies use_cache=True and the first player_key found
          that can accept mp3 and any specified player_mode will be returned. 
          If a transcoder is needed to convert to mp3 then one will be chosen and
          returned.

          If no match can be made, then raise ConfigurationError
        """
        repairs_made: bool = False

        # First, handle the case where the engine also voices

        MY_LOGGER.debug(f'service_key: {engine_key}')
        e_pm_val: IStringValidator
        e_pm_val = SettingsMap.get_validator(engine_key.with_prop(
                SettingProp.PLAYER_MODE))
        MY_LOGGER.debug(f'engine_player_mode_val : {e_pm_val}')
        if player_mode is not None and player_mode == PlayerMode.ENGINE_SPEAK:
            if not e_pm_val.validate(player_mode):
                # Engine does NOT support INTERNAL player_key
                MY_LOGGER.info(f'Unsupported player_key mode: {player_mode} for '
                               f'engine: {engine_key}. Ignoring')
                player_mode = None
                if repair:
                    repairs_made = True
                if player_id is not None and player_id == Players.INTERNAL:
                    MY_LOGGER.info(f'Engine: {engine_key} does not support '
                                   f'internal player_key. Ignoring.')
                    player_id = None
                    if repair:
                        repairs_made = True
            else:  # Engine supports ENGINE_SPEAK and is requested mode
                player_id = Players.INTERNAL
                engine_audio = AudioType.NONE
                use_cache = False
                engine_config = EngineConfig(engine_key=engine_key,
                                             lang_info=lang_info,
                                             use_cache=use_cache,
                                             player_id=player_id,
                                             engine_audio=engine_audio,
                                             player_mode=player_mode,
                                             transcoder=None,
                                             trans_audio_in=None,
                                             trans_audio_out=None,
                                             repair_mode=repair,
                                             repairs_made=repairs_made)
                return engine_config
        if player_id is not None and not e_pm_val.validate(PlayerMode.ENGINE_SPEAK):
            MY_LOGGER.info(f'{engine_key} does not support '
                           f'internal player_key. Ignoring.')
            if repair:
                repairs_made = True
            player_id = None
        val: IStringValidator
        val = SettingsMap.get_validator(engine_key.with_prop(SettingProp.PLAYER))
        if player_id is not None and not val.validate(player_id):
            MY_LOGGER.info(f'engine: {engine_key} does not support player_key: {player_id}. '
                           f'Ignoring playerer: {player_id}')
            player_id = None
            if repair:
                repairs_made = True

        engine_config: EngineConfig | None = None
        engine_audio_types: List[AudioType]
        engine_audio_types = SoundCapabilities.get_output_formats(engine_key)

        pm_default: PlayerMode
        pm_default = PlayerMode(e_pm_val.default)
        if player_mode is None:
            player_mode = pm_default
            if repair:
                repairs_made = True
        valid, pm_mode = e_pm_val.validate(player_mode)
        MY_LOGGER.debug(f'PlayerMode valid: {valid} pm_mode: {pm_mode} '
                        f'player_mode {player_mode} '
                        f'{engine_key}. Using default: {pm_default}')
        player_mode = pm_default

        # Second, Handle the case where the player_key is specified. Check validity
        # and possibly a need for a transcoder

        MY_LOGGER.debug(f'player_id: {player_id}')
        if player_id is not None:
            ep_val: IStringValidator
            ep_val = SettingsMap.get_validator(engine_key.with_prop(SettingProp.PLAYER))
            if not ep_val.validate(player_id)[0]:
                MY_LOGGER.debug(f'player_key {player_id} not valid for: {engine_key} '
                                f'Ignoring player_key.')
                player_id = None
                if repair:
                    repairs_made = True
            else:
                # engine_audio is NOT a saved setting. Preference is to use mp3,
                # especially with caching.
                # Use mp3 if engine produces it.
                if engine_audio is None:
                    if AudioType.MP3 in engine_audio_types:
                        engine_audio = AudioType.MP3
                    else:
                        engine_audio = AudioType.WAV
                    MY_LOGGER.debug(f'engine_audio not specified. trying {engine_audio}')
                engine_config = self.find_best_config(engine_key, engine_audio, lang_info,
                                                      player_ids=player_id,
                                                      player_mode=player_mode,
                                                      use_cache=use_cache)
                if engine_config is None:
                    # See if a transcoder helps
                    trans_id: str | None = None
                    trans_audio_out: AudioType | None = None

                    if AudioType.MP3 not in engine_audio_types:
                        trans_audio_out = AudioType.MP3
                    elif AudioType.WAV not in engine_audio_types:
                        trans_audio_out = AudioType.WAV
                    if trans_audio_out is not None:
                        trans_id = self.find_transcoder(engine_key, trans_audio_out)
                        t_ecfg: EngineConfig | None
                        t_ecfg = self.find_best_config(engine_key=engine_key,
                                                       engine_audio=engine_audio,
                                                       lang_info=lang_info,
                                                       player_ids=player_id,
                                                       player_mode=player_mode,
                                                       use_cache=use_cache,
                                                       repair_mode=repair)
                        if t_ecfg is not None:
                            # Add info about transcoder
                            engine_config = EngineConfig(engine_key=t_ecfg.engine_key,
                                                         lang_info=lang_info,
                                                         use_cache=t_ecfg.use_cache,
                                                         player_id=t_ecfg.player_id,
                                                         engine_audio=engine_audio,
                                                         player_mode=t_ecfg.player_mode,
                                                         transcoder=trans_id,
                                                         trans_audio_in=engine_audio,
                                                         trans_audio_out=trans_audio_out,
                                                         repair_mode=repair,
                                                         repairs_made=repairs_made)
        engine_id: str = engine_key.service_id
        if engine_config is None:
            # Did not work out, forget about the player_id that doesn't work,
            # then try every audio type that the engine produces, without
            # specifying player_id

            player_id = None
            MY_LOGGER.debug(f'engine_audio_types: {engine_audio_types}')
            for engine_audio_type in engine_audio_types:
                # Avoid putting .wav files in cache, unless explicitly
                # requested. Wave files require transcoder to .mp3 (except
                # GENERATE_BACKUP_SPEECH is set)
                t_use_cache: bool = use_cache
                if use_cache is None and engine_audio_type == AudioType.WAV:
                    t_use_cache = False
                MY_LOGGER.debug(f't_use_cache: {t_use_cache} audio_type: '
                                f'{engine_audio_type} {engine_key}')
                engine_config = self.find_player(engine_key, lang_info, engine_audio_type,
                                                 player_mode, t_use_cache)
                if engine_config is not None:
                    break

            if engine_config is None:
                # Perhaps a transcoder would help?
                trans_id: str | None = None
                trans_audio_out: AudioType | None = None
                if AudioType.MP3 not in engine_audio_types:
                    trans_audio_out = AudioType.MP3
                elif AudioType.WAV not in engine_audio_types:
                    trans_audio_out = AudioType.WAV
                MY_LOGGER.debug(f'trans_audio_out: {trans_audio_out}'
                                f' {engine_key}')
                if trans_audio_out is not None:
                    trans_id = self.find_transcoder(engine_key, trans_audio_out)
                    if trans_id is None:
                        raise ConfigurationError('Can not find transcoder for'
                                                 f' {engine_key}')
                    t_ecfg = self.find_player(engine_key, lang_info, trans_audio_out,
                                              player_mode, use_cache)
                    if t_ecfg is not None:
                        # Add info about transcoder
                        engine_config.use_cache = t_ecfg.use_cache
                        engine_config.player_id = t_ecfg.player_id
                        engine_config.player_mode = t_ecfg.player_mode
                        engine_config.transcoder = trans_id
                        engine_config.trans_audio_in = engine_audio
                        engine_config.trans_audio_out = trans_audio_out
                        repairs_made |= t_ecfg.repairs_made
                        engine_config.repairs_made = repairs_made
            if engine_config is None:
                MY_LOGGER.debug(f'Can\'t find player_key for: {engine_key}')
                raise ConfigurationError(f'Can not find player_key for: {engine_key}')
        return engine_config

    def find_player(self, engine_key: ServiceID, lang_info: LanguageInfo,
                    engine_audio: AudioType,
                    player_mode: PlayerMode | None,
                    use_cache: bool | None,
                    repair_mode: bool = False) -> EngineConfig | None:
        """
        Searchs all players supported by the given engine for one that supports
        the given input_audio. The default player_key is searched first, otherwise
        they are searched in the order specified by the validator.

        This method is called under two circumstances: 1) When the user changes
        engines, 2) When the user changes some option for an engine.
        In the first case, the primary focus is to get a player_key that meets the
        requirements of the engine, but also supports caching. If no player_key is
        found, then the search can be retried with use_cache=False.

        In the second case, the engine has already been picked but the user
        wants to modify caching, player_key mode, etc. In this case player_mode
        and use_cache are specified to require matches on those values, narrowing
        the criteria.

        :param engine_key:
        :param lang_info:
        :param engine_audio:
        :param player_mode: If not None,then the player_mode of player_key must match
        :param use_cache:
        :param repair_mode:
        :return:

        Assumption: At this point there is no interest in using ENGINE_SPEAK.
        """

        """
        Look for the first player_key that:
          - player_key input audio type == engine output audio type
          - if engine's player_mode is specified and supports the players player_mode
          - supports caching
          - does not support caching and use_cache is False
        """
        engine_id: str = engine_key.service_id
        MY_LOGGER.debug(f'engine_id: {engine_id} engine_audio: {engine_audio} '
                        f'player_mode: {player_mode} use_cache: {use_cache} '
                        f'repair_mode: {repair_mode}')
        if engine_audio is None:
            MY_LOGGER.debug(f'engine_audio can not be None')
            return None
        engine_config: EngineConfig | None = None
        val: IStringValidator
        val = SettingsMap.get_validator(engine_key.with_prop(SettingProp.PLAYER))
        default_player: str | None = val.default
        players: List[str] = []
        MY_LOGGER.debug(f'enabled allowed_values: {val.get_allowed_values(enabled=True)}'
                        f' default player: {default_player} type: {type(default_player)}')
        # Try default_player first
        if default_player is not None:
            players.append(default_player)
        for player in val.get_allowed_values(enabled=True):
            player: AllowedValue
            MY_LOGGER.debug(f'player: {player} type: {type(player.value)}')
            if default_player is None or (player.value != default_player):
                players.append(player.value)
        MY_LOGGER.debug(f'players_to_try: {players}')
        supported_players: List[str] = self.filter_players_on_audio_type(players,
                                                                         engine_audio)
        MY_LOGGER.debug(f'filtered_players_on_audio_type: {supported_players}')
        engine_config = self.find_best_config(engine_key=engine_key,
                                              engine_audio=engine_audio,
                                              lang_info=lang_info,
                                              player_ids=supported_players,
                                              player_mode=player_mode,
                                              use_cache=use_cache,
                                              repair_mode=repair_mode)
        return engine_config

    def find_best_config(self, engine_key: ServiceID, engine_audio: AudioType,
                         lang_info: LanguageInfo, player_ids: List[str] | str,
                         player_mode: PlayerMode | None = None,
                         use_cache: bool | None = None,
                         repair_mode: bool = False) -> EngineConfig | None:
        """
        Checks to see if the given configuration is a valid player_key for the given
        engine.

        :param engine_key: Can not be None
        :param engine_audio: Can not be None
        :param lang_info: Can not be none
        :param player_ids: List of players that support the audio output of the engine
                           Can also be a single player_key
        :param player_mode: If None, then any player_mode is acceptable, otherwise,
                            the player_mode MUST match exactly, unless it is
                            impossible to match
        :param use_cache: If None then caching will be preferred. Otherwise,
                          when False, caching will not be required
        :param repair_mode:
        :return:

        Assumption: Engines self-voicing (ENGINE_SPEAK) decisions already made
        prior to this call.
        """
        engine_id: str = engine_key.service_id
        repairs: bool = False
        if isinstance(player_ids, str):
            player_ids: List = [player_ids]
        MY_LOGGER.debug(f'engine_id: {engine_id} engine_audio: {engine_audio} '
                        f'player_ids: {player_ids} player_mode: {player_mode} '
                        f'use_cache: {use_cache}')
        if engine_audio is None:
            raise ValueError(f'Engine: {engine_id} engine_audio can not be None')

        # It does little harm to use a player_key that supports a cache if you don't
        # use it.
        for t_cache in True, False:
            t_cache: bool
            supporting_players: List[str] = self.filter_players_on_cache(player_ids,
                                                                         t_cache)
            if len(supporting_players) == 0:
                if repair_mode:
                    repairs = True
                supporting_players.extend(player_ids)

            # If given player_mode doesn't match,or is None, then all engine
            # player_key modes are tried, in preference order, until at least one player_key
            # also supports the mode.

            t_players: List[str]
            t_players, t_player_mode = self.filter_players_on_player_mode(engine_key,
                                                                          supporting_players,
                                                                          player_mode)
            if len(t_players) == 0:
                # No player_key supports any of the engine's modes.
                raise ValueError(f'Engine: {engine_id} No player_key supports any of the '
                                 f'engine\'s player_key modes.')
            if t_player_mode != player_mode:
                # Forced to change player_key mode to find a match
                if repair_mode:
                    repair = True
                player_mode = t_player_mode
            supporting_players.clear()
            supporting_players.extend(t_players)

            # supporting_players should be in order of preference.
            player_id = supporting_players[0]
            if repair_mode:
                if use_cache is None:
                    use_cache = t_cache
                    repairs = True
                elif use_cache != t_cache:
                    if use_cache:
                        # Here use_cache WAS enabled, but we can't this time.
                        use_cache = t_cache
                        repairs = True
            if use_cache is not None:
                if use_cache and use_cache != t_cache:
                    use_cache = t_cache
            engine_config = EngineConfig(engine_key=engine_key,
                                         lang_info=lang_info,
                                         use_cache=use_cache,
                                         player_id=player_id,
                                         engine_audio=engine_audio,
                                         player_mode=player_mode,
                                         transcoder=None,
                                         trans_audio_in=None,
                                         trans_audio_out=None,
                                         repair_mode=repair_mode,
                                         repairs_made=repairs)
            return engine_config

    def filter_players_on_player_mode(self, engine_key: ServiceID,
                                      player_ids: List[str],
                                      player_mode: PlayerMode) -> (
            Tuple)[List[str], PlayerMode]:
        """
        Returns all players which support the given player_mode.

        If the given player_mode doesn't match, or is None, then all engine
        player_key modes are tried, in preference order, until at least one player_key
        also supports the mode.

        :param engine_key:
        :param player_ids:
        :param player_mode:
        :return:

        Assumes that engine does not only support ENGINE_SPEAK
        """
        matching_players: List[str] = []
        e_pm_val: StringValidator | IStringValidator
        MY_LOGGER.debug(f'service_key: {engine_key}')
        t_key: ServiceID = engine_key.with_prop(SettingProp.PLAYER_MODE)
        e_pm_val = SettingsMap.get_validator(t_key)
        e_pm_values: List[AllowedValue] = e_pm_val.get_allowed_values(enabled=True)
        MY_LOGGER.debug(f'Allowed player_modes for engine: {engine_key}')

        # Search for any non_none player_key mode first, if not found, then
        # search, in preference order, all player_modes supported by the engine,
        # until at least one player_key also supports it.
        player_modes: List[PlayerMode] = []
        if player_mode is not None:
            player_modes.append(player_mode)  # Try given mode first
            for ea_pm in e_pm_values:
                ea_pm: AllowedValue
                e_pm: PlayerMode = PlayerMode(ea_pm.value)
                player_modes.append(e_pm)
        pm: PlayerMode
        MY_LOGGER.debug(f'player_ids: {player_ids}')
        for pm in player_modes:
            MY_LOGGER.debug(f'player_mode: {pm}')
            for player_id in player_ids:
                player_id: str
                player_key: ServiceID
                player_key = ServiceID(ServiceType.PLAYER, player_id)
                p_pm_val: StringValidator | IStringValidator
                p_pm_key: ServiceID = player_key.with_prop(SettingProp.PLAYER_MODE)
                p_pm_val = SettingsMap.get_validator(p_pm_key)
                MY_LOGGER.debug(f'player: {player_key} pm: {pm} valid:'
                                f' {p_pm_val.is_value_valid(pm)}')
                if p_pm_val.is_value_valid(pm):
                    matching_players.append(player_id)
            if len(matching_players) > 0:
                player_mode = pm
                break
        MY_LOGGER.debug(f'player_mode: {player_mode} matching_players: '
                        f'{matching_players}')
        return matching_players, player_mode

    def filter_players_on_cache(self, player_ids: List[str],
                                cache: bool | None) -> List[str]:
        """
        Returns all players which support the given cache setting
        :param player_ids:
        :param cache: players that match the boolean value are returned. If
                      cache is None, then all players are returned (with
                      ones supporting a cache first)
        :return: player_ids that match

        Assumes that engine does not only support ENGINE_SPEAK
        Assumes that any engine supporting a cache does not require it
        """
        matching_players: List[str] = []
        if cache is None:
            matching_players.extend(player_ids)
            return matching_players

        for player_id in player_ids:
            player_id: str
            player_key: ServiceID
            player_key = ServiceID(ServiceType.PLAYER, player_id)
            pc_val: BoolValidator | IBoolValidator
            pc_val = SettingsMap.get_validator(player_key.with_prop(
                    SettingProp.CACHE_SPEECH))
            if pc_val is None:
                MY_LOGGER.info(f'Player: {player_id} did NOT define CACHE_SPEECH '
                               f'validator')
            if (pc_val is None and not cache) or (pc_val.get_tts_value() == cache):
                matching_players.append(player_id)
        return matching_players

    def filter_players_on_audio_type(self, player_ids: List[str | PlayerType],
                                     audio_type: AudioType) -> List[str]:
        """
        Returns all players which support the given audio type.

        :param player_ids:
        :param audio_type: players that match are returned. MUST not be None
        :return: player_ids that match
        """
        matching_players: List[str] = []
        if audio_type is None:
            raise ValueError

        for player_id in player_ids:
            player_id: str
            player_key: ServiceID = ServiceID(ServiceType.PLAYER,
                                              player_id)
            player_audio_types: List[AudioType]
            player_audio_types = SoundCapabilities.get_input_formats(player_key)
            MY_LOGGER.debug(f'player: {player_id} audio_type: {audio_type}'
                            f' type: {type(audio_type)} '
                            f'player_audio_types: {player_audio_types}')
            if audio_type in player_audio_types:
                MY_LOGGER.debug(f'{audio_type} in audio_types')
                matching_players.append(player_id)
        MY_LOGGER.debug(f'matching_players: {matching_players}')
        return matching_players

    def find_transcoder(self, engine_key: ServiceID,
                        trans_audio_out: AudioType,
                        repair_mode: bool = False) -> str | None:
        """

        :param engine_key:
        :param trans_audio_out:
        :param repair_mode:
        :return: transcoder id Or None
        """
        repairs: bool = False
        MY_LOGGER.debug(f'trans_audio_out: {trans_audio_out}'
                        f' {engine_key}')
        tran_id: str | None = None
        if trans_audio_out is not None:
            try:
                tran_id = SoundCapabilities.get_transcoder(engine_key,
                                                           target_audio=trans_audio_out)
            except ValueError:
                MY_LOGGER.debug(f'Can\'t find transcoder for engine:'
                                f' {engine_key}')
                tran_id = None
        return tran_id

    def get_player_choices(self,
                           engine_key: ServiceID) -> Tuple[List[Choice], int]:
        """
            Get players which are compatible with the engine as well as player_Mode.
            The 'ranking' of players may influence the suggested player_key.

            The player_mode should be checked to see if it requires changing

        :param engine_key:
        :return: List of compatible players and an index referencing the current
                 or suggested player_key.
        """
        choices: List[Choice] = []
        current_choice_index = -1
        '''
            # We want the players which can handle what our TTS engine produces
        '''
        return self.get_compatible_players(engine_key)

    def get_compatible_players(self,
                               engine_key: ServiceID) -> Tuple[List[Choice], int]:
        """
            TODO: verify that this is needed or can't utilize other player_key
                methods (find_player, etc)

               Get players which are compatible with the engine as well as player_Mode.
               The 'ranking' of players may influence the suggested player_key.

               The player_mode should be checked to see if it requires changing

           :param engine_key: Engine to get players for
           :return: List of compatible players and an index referencing the current
                 or suggested player_key.
        """
        choices: List[Choice] = []
        current_choice_index: int = -1
        try:
            if not SettingsMap.is_valid_setting(engine_key.with_prop(
                    SettingProp.PLAYER)):
                if MY_LOGGER.isEnabledFor(INFO):
                    MY_LOGGER.info(f'There is no PLAYER for {engine_key}')
                return choices, current_choice_index

            # Make sure that any player_key complies with the engine's player_key
            # validator

            val: IStringValidator
            val = SettingsMap.get_validator(engine_key.with_prop(SettingProp.PLAYER))
            current_choice: ServiceID
            current_choice = Settings.get_player_key(engine_key)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'current player_key: {current_choice} '
                                f'engine: {engine_key} ')

            supported_players_with_enable: List[AllowedValue]
            supported_players_with_enable = val.get_allowed_values()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'supported_players_with_enable:'
                                f' {supported_players_with_enable}')
            default_choice_str: str = val.default
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'default: {val.default}')

            if supported_players_with_enable is None:
                supported_players_with_enable = []
            supported_players: List[Tuple[str, bool]] = []
            idx: int = 0
            default_choice_idx: int = -1
            current_enabled: bool = True
            default_enabled: bool = True
            for supported_player in supported_players_with_enable:
                supported_player: AllowedValue
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'player_str: {supported_player.value} '
                                    f'enabled: {supported_player.enabled}')
                player: str = supported_player.value
                supported_players.append((player, supported_player.enabled))
                if player == current_choice.setting_id:
                    current_choice_index = idx
                    current_enabled = supported_player.enabled
                if player == default_choice_str:
                    default_choice_idx = idx
                    default_enabled = supported_player.enabled
                idx += 1

            if current_choice_index < 0:
                current_choice_index = default_choice_idx
                current_enabled = default_enabled
            if not current_enabled:  # Must pick something else
                current_choice_index = 0
            idx: int = 0
            for player_id, enabled in supported_players:
                player_id: str
                label: str = Players.get_msg(player_id)
                choices.append(Choice(label=label, value=player_id,
                                      choice_index=idx, enabled=enabled))
        except Exception as e:
            MY_LOGGER.exception('')
        return choices, current_choice_index

    def get_module_choices(self,
                           engine_key: ServiceID) -> Tuple[List[Choice], int]:
        """

        :return:
        """
        choices: List[Choice] = []
        current_choice_index: int = -1
        try:
            current_value = self.get_module()
            if not SettingsMap.is_valid_setting(engine_key.with_prop(
                    SettingProp.MODULE)):
                return [], -1

            supported_modules: List[Choice]
            default_module: str
            supported_modules, default_module = BackendInfo.getSettingsList(
                    engine_key, SettingProp.MODULE)
            if supported_modules is None:
                supported_modules = []

            default_choice_index = -1
            idx: int = 0
            for module_name, module_id in supported_modules:
                module_label = module_name  # TODO: Fix
                choices.append(Choice(label=module_label, value=module_id,
                                      choice_index=idx))
                if module_id == current_value:
                    current_choice_index = len(choices) - 1
                if module_id == default_module:
                    default_choice_index = len(choices) - 1
                idx += 1

            if current_choice_index < 0:
                current_choice_index = default_choice_index
        except Exception as e:
            MY_LOGGER.exception('')
        return choices, current_choice_index

    def get_gender_choices(self,
                           engine_key: ServiceID) -> Tuple[List[Choice], int]:
        """
        Gets gender choices for the given engine_id, if any

        :param engine_key: Identifies which engine's settings to work with
        :return:
        """
        MY_LOGGER.debug('FOOO get_gender_choices')

        current_value: Genders = Settings.get_gender(engine_key)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'gender: {current_value}')
        current_choice_index = -1
        choices: List[Choice] = []
        try:
            if not SettingsMap.is_valid_setting(engine_key.with_prop(
                    SettingProp.GENDER)):
                return choices, current_choice_index

            engine: ITTSBackendBase = self.getEngineInstance(engine_key)
            gender_choices, _ = engine.settingList(SettingProp.GENDER)
            gender_choices: List[Choice]
            # supported_genders = BackendInfo.getSettingsList(engine,
            #                                               SettingProp.GENDER)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'genders: {gender_choices}')
            genders: List[Choice] = []

            if gender_choices is None:
                supported_genders = []
            idx: int = 0
            for choice in gender_choices:
                choice: Choice
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'choice: {choice.value}')
                display_value = GenderSettingsMap.get_label(choice.value)
                choices.append(Choice(label=display_value, value=choice.value,
                                      choice_index=idx))
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Gender choice: {choices[-1]}')
                if choice.value == current_value:
                    current_choice_index = len(choices) - 1
                idx += 1
        except Exception as e:
            MY_LOGGER.exception('')

        return choices, current_choice_index

    def get_voice_choices(self,
                          engine_key: ServiceID) -> Tuple[List[Choice], int]:
        """
            Creates a list of voices for the current language and engine
            in a format suitable for the SelectionDialog
        :param engine_key: engine_id to get voice choices for
        :return:
        """
        choices: List[Choice] = []
        current_choice_index: int = -1
        MY_LOGGER.debug('FOOO get_voice_choices')

        try:
            # current_value: str = self.getSetting(SettingProp.VOICE)
            # MY_LOGGER.debug(f'engine: {self.setting_id} voice: {current_value}')
            voices: List[Choice]
            # Request match closet to current lang settings, not kodi_locale
            voices, current_choice_index = SettingsHelper.get_language_choices(
                    engine_key,
                    get_best_match=False,
                    format_type=FormatType.LONG)
            # voices = BackendInfo.getSettingsList(
            #         self.setting_id, SettingProp.VOICE)
            #  MY_LOGGER.debug(f'voices: {voices}')
            if voices is None:
                voices = []

            # voices = sorted(voices, key=lambda entry: entry.label)
            voices: List[Choice]
            for choice in voices:
                choice: Choice
                choices.append(choice)
        except Exception as e:
            MY_LOGGER.exception('')

        return choices, current_choice_index

    def select_defaults(self, engine_key: ServiceID) -> None:
        """
        Configures TTS with reasonable Default values

        :param engine_key: Engine to configure
        :return:
        """
        clz = type(self)
        standalone: bool = False
        try:
            # Can be called from SettingsDialog or during initial load of an engine,
            # or when problem detected. If from SettingsDialog, then the Settings
            # stack has already been set up, otherwise, we have to do it ourselves.

            if self._original_stack_depth == -1:
                standalone = True
                self.save_settings(msg='enter select_defaults', initial_frame=True)
            else:
                self.restore_settings('enter select_defaults')
            # Ensure settings for engine are loaded
            BaseServices.get_service(engine_key)
            MY_LOGGER.debug(f'got service: {engine_key}')
            choices, current_choice_index = self.get_engine_choices(
                    engine_key=engine_key)
            choices: List[Choice]
            if current_choice_index < 0:
                current_choice_index = 0
            MY_LOGGER.debug(f'# choices: {choices} len: {len(choices)}'
                            f' current_choice_idx: '
                            f'{current_choice_index}')

            choice: Choice = choices[current_choice_index]
            if choice is not None:
                self.configure_engine(choice, save_as_current=True)
                self.commit_settings()
        except Exception as e:
            MY_LOGGER.exception('')
        finally:
            if standalone:
                self.restore_settings(msg='exit select_defaults', initial_frame=True)
            else:
                standalone = True
                self.restore_settings(msg='exit select_defaults', initial_frame=False)

    def validate_repair(self, engine_key: ServiceID) -> None:
        """
        Verifies that the given engine's configuration is valid and repair as
        needed.

        Looks for conflicting settings or for use of broken or missing services.
        Repairs problems as needed to produce a usable configuration.

        :param engine_key: Engine to examine
        :return:

        :raises ServiceUnavailable: When engine is broken/unavailable
        """
        clz = type(self)
        standalone: bool = False
        try:
            # Can be called from SettingsDialog or during initial load of an engine,
            # or when problem detected. If from SettingsDialog, then the Settings
            # stack has already been set up, otherwise, we have to do it ourselves.

            if self._original_stack_depth == -1:
                standalone = True
                self.save_settings(msg='enter validate_repair', initial_frame=True)
            else:
                self.restore_settings('enter validate_repair')
            # Ensure settings for engine are loaded
            try:
                BaseServices.get_service(engine_key)
                MY_LOGGER.debug(f'got service: {engine_key}')
            except ServiceUnavailable as e:
                active: bool = False
                if engine_key.service_id == SettingsLowLevel.get_engine_id_ll(
                        ignore_cache=True).service_id:
                    active = True
                MY_LOGGER.debug(f'Service Unavailable: {e}')
                MY_LOGGER.exception('')
                raise ServiceUnavailable(service_key=engine_key,
                                         reason=e.reason,
                                         active=active)
            choices, current_choice_index = self.get_engine_choices(
                    engine_key=engine_key)
            choices: List[Choice]
            if current_choice_index < 0:
                current_choice_index = 0
            MY_LOGGER.debug(f'# choices: {choices} len: {len(choices)}'
                            f' current_choice_idx: '
                            f'{current_choice_index}')

            choice: Choice = choices[current_choice_index]
            if choice is not None:
                self.configure_engine(choice, repair=True, save_as_current=False)
                self.commit_settings()
        except ServiceUnavailable:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        finally:
            if standalone:
                self.restore_settings(msg='exit select_defaults', initial_frame=True)
            else:
                standalone = True
                self.restore_settings(msg='exit select_defaults', initial_frame=False)

    def set_engine_field(self, engine_key: ServiceID | None = None) -> None:
        """
        Saves the given engine_id in Settings and restarts TTS engine.

        :param engine_key: If None, then engine_id is populated with the current
        engine_id from Settings.get_service_key. Updates Settings with the value
        of engine_id (yeah, it can just update Settings with the same engine_id
        that it just read).
        :return:
        """
        MY_LOGGER.debug(f'set_engine_field engine: {engine_key}')
        if engine_key is None:
            engine_key = Settings.get_engine_key()
            MY_LOGGER.debug(f'Got back: {engine_key}')

        # Do NOT try to skip initTTS by using:
        # current_engine_id: str = TTSService.get_instance().tts.engine_id
        # if engine_id != current_engine_id:
        # The reason is that TTSService's engine instance may NOT be
        # the same as Settings engine_id. In particular, this occurs when:
        #   voice_engine is giving a pre-view of how an engine sounds
        #   The user likes the engine and selects it (presses enter or OK)
        #   voice_engine returns to select_engine, which pops the temporary
        #   settings stack causing all settings to revert to their previous
        #   values. However, TTS engine instance is still running with the
        #   same engine that the user selected.
        # In short: don't depend on the TTSService engine instance to be the
        # same as what is in Settings

        PhraseList.set_current_expired()  # Changing engines
        MY_LOGGER.debug(f'setting: {engine_key} type: {type(engine_key)}')
        Settings.set_engine(engine_key)
        MY_LOGGER.debug(f'About to start TTS')
        # Sets the engine id and switch to use it. Expensive
        from service_worker import TTSService
        tts_instance: TTSService = TTSService.get_instance()
        if tts_instance is None:  # Not yet started
            return
        TTSService.checkBackend()

    def set_player_field(self,
                         engine_key: ServiceID,
                         player_id: str) -> None:
        """
        Updates player_id.engine_id Settings.

        :param engine_key: identifies which engine the settings belong to. If
                           None, then the current engine is used
        :param player_id: identifies the player_id to set. If None, then
                          the current player_id for engine_id will be 'updated'
        :return:
        """
        try:

            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting {engine_key} player_key to {player_id}')
            Settings.set_player(value=player_id, engine_key=engine_key)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_module_field(self, module_id: str) -> None:
        """
          Updates module.engine_id Settings.

          :return:
          """
        try:
            Settings.set_module(value=module_id)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_player_mode_field(self, engine_key: ServiceID | None = None,
                              player_mode: PlayerMode | None = None) -> None:
        """
        Updates player_mode.engine_id Settings

        :param engine_key: identifies which engine the settings belong to. If
                          None, then the current engine is used
        :param player_mode: identifies the player_mode to set. If None, then
                          the current player_mode for engine_id will be 'updated'
        :return:
        """
        try:
            if player_mode is None:
                player_mode = Settings.get_player_mode(engine_key)
            if MY_LOGGER.isEnabledFor(DEBUG):
                player_mode_str: str = player_mode.translated_name
                MY_LOGGER.debug(f'Setting {engine_key} mode to {player_mode}')
            Settings.set_player_mode(player_mode=player_mode, service_key=engine_key)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_lang_fields(self, engine_key: ServiceID,
                        lang_info: LanguageInfo) -> None:
        """
        Configures the Language and voice settings.  No validation is performed

        :param engine_key:
        :param lang_info:
        :return:
        """
        try:
            MY_LOGGER.debug('FOOO set_lang_field')
            if engine_key is None:
                raise ValueError('engine_id value required')
            if lang_info is None:
                raise ValueError('lang_info value required')
            lang_id: str = lang_info.engine_lang_id
            voice_id: str = lang_info.engine_voice_id

            Settings.set_language(lang_id, engine_key)
            Settings.set_voice(voice_id, engine_key)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_voice_field(self,
                        engine_key: ServiceID,
                        voice_id: str) -> None:
        """
        Updates the voice field with the value that the current engine is
        using. The voice can be changed by the user selecting the asociated
        button.
        :param engine_key: Identifies the engine that will have its voice modified
        :param voice_id: New value to assign to the engine's voice
        :return:
        """
        clz = type(self)
        try:
            MY_LOGGER.debug('FOOO set_voice_field')
            has_voice: bool
            has_voice = SettingsMap.is_valid_setting(engine_key.with_prop(
                    SettingProp.VOICE))
            if has_voice:
                has_voice = SettingsMap.is_setting_available(engine_key,
                                                             SettingProp.VOICE)
            choices: List[Choice] = []
            if voice_id is None:
                choices, current_choice_index = self.get_voice_choices(engine_key)
                if current_choice_index < 0:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'choice out of range: {current_choice_index} '
                                        f'# choices: {len(choices)}')
                    current_choice_index = 0
                choice: Choice = choices[current_choice_index]
                voice_id = choice.lang_info.engine_voice_id
            Settings.set_voice(voice_id, engine_key)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting voice to: {voice_id}')
        except Exception as e:
            MY_LOGGER.exception('')

    def set_cache_speech_field(self,
                               engine_key: ServiceID,
                               use_cache: bool) -> None:
        """
        Propagates cache_speech setting to Settings
        :param engine_key: Specifies the engine_id to update. If None, then the
                          current Settings.engine_id will be used
        :param use_cache: Specifies whether the engine is using a cache. If None,
                          then the current Settings.use_cache.engine_id value will
                          be used
        """
        try:
            Settings.set_use_cache(use_cache, engine_key)

        except NotImplementedError:
            MY_LOGGER.exception('')
        except Exception as e:
            MY_LOGGER.exception('')

    def set_speed_field(self, speed: float) -> None:
        """
        Configures Settings.speed. Note that the speed setting applies to ALL
        TTS engines, so engine_id is not required for this setting.

        :param speed: float value to set the speed to.
        """
        try:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Setting speed to: {speed}')
            self.speed_val.set_value(speed)
        except Exception as e:
            MY_LOGGER.exception('')

    def set_pitch_field(self, engine_key: ServiceID,
                        pitch: float) -> None:
        """
        Updates Settings.pitch

        :param engine_key: Identifies the engine which to update the pitch
        :param pitch: value to set
        :return:
        """
        pass  # TODO: Patch adjustments temporarily disabled. eSpeak supports pitch

    def set_volume_field(self, volume: float) -> None:
        """
        Configures Settings.volume. Note that the volume setting applies to ALL
        TTS engines, so engine_id is not required for this setting.

        :param volume: float value to set the volume to.
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Setting volume to {volume}')
        self.volume_val.set_value(volume)

    def set_gender_field(self, engine_key: ServiceID):
        """
        Sets the given engine's Gender field, if it has one.
        :param engine_key: Identifies which engine's settings to work with

        Note that the current gender is calculated by choices made from selecting
        the voice (SUBJECT TO CHANGE).
        :return:
        """
        try:
            choices: List[Choice]
            valid: bool = SettingsMap.is_valid_setting(engine_key.with_prop(
                    SettingProp.GENDER))
            MY_LOGGER.debug(f'setting_id: {engine_key} GENDER valid: {valid}')
            if not valid:
                return
            choices, current_choice_index = self.get_gender_choices(
                    engine_key)
            if current_choice_index < 0:
                current_choice_index = 0
            if current_choice_index < 0 or current_choice_index > len(choices) - 1:
                return
            choice: Choice = choices[current_choice_index]
        except Exception as e:
            MY_LOGGER.exception('')

    def set_api_field(self, engine_key: ServiceID) -> None:
        """
        TODO:  This is largely a no-op
        """
        try:
            if not SettingsMap.is_setting_available(engine_key,
                                                    SettingProp.API_KEY):
                return

            if (SettingsMap.get_validator(engine_key.with_prop(SettingProp.API_KEY)),
                                                               None):
                api_key: str = Settings.get_api_key(engine_key)
                #  self.engine_api_key_edit.setText(api_key)
        except Exception as e:
            MY_LOGGER.exception('')

    def get_module(self) -> str:
        """

        :return:
        """
        module = 'bad'
        try:
            module: str | None = self.get_module_setting()
            if module is None:
                engine: ITTSBackendBase
                engine = BackendInfo.getBackend(self.engine_key.service_id)
                module = engine.get_setting_default(SettingProp.PLAYER)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return module

    def get_module_setting(self, default: str | None = None):
        """
            TODO: Almost certainly broken. Used by AudioDispatcher.
                  Fix at that time. Don't share with Player setting anymore.
        :param default:
        :return:
        """
        engine: ITTSBackendBase = self.getEngineInstance(self.engine_key)
        if default is None:
            default = engine.get_setting_default(SettingProp.MODULE)
        value = engine.getSetting(SettingProp.MODULE, default)
        return value

    def commit_settings(self) -> None:
        """

        """
        SettingsLowLevel.commit_settings()
        MY_LOGGER.info(f'Settings saved/committed')
        #  TTSService.get_instance().checkBackend()
        MY_LOGGER.debug(f'original_depth: {self._original_stack_depth} stack_depth: '
                        f'{SettingsManager.get_stack_depth()}')

    def save_settings(self, msg: str, initial_frame: bool = False) -> None:
        """
        Pushes a copy of the current settings 'frame' onto the stack of settings.
        restore_settings pops the stack frame, discarding all changes and reverting
        to the settings prior to save_settings

        :param msg: Text to add to debug msgs to give context
        :param initial_frame: When True, this creates the initial frame on each entry
                        to this class via doModal or show.
        :return:
        """
        try:
            if initial_frame:
                if self._original_stack_depth != -1:
                    MY_LOGGER.debug('INVALID initial state.')
                self._original_stack_depth = SettingsManager.get_stack_depth()
            MY_LOGGER.debug(f'{msg}\nBEFORE save_settings original_depth: '
                            f'{self._original_stack_depth} '
                            f'stack_depth: {SettingsManager.get_stack_depth()}')
            SettingsLowLevel.save_settings()
            MY_LOGGER.debug(f'{msg}\nAFTER save_settings original_depth: '
                            f'{self._original_stack_depth} '
                            f'stack_depth: {SettingsManager.get_stack_depth()}')
        except Exception as e:
            MY_LOGGER.exception('')

    def restore_settings(self, msg: str, initial_frame: bool = False,
                         settings_changes: Dict[str, Any] | None = None) -> None:
        """
        Wrapper around SettingsManager.restore_settings. The purpose is to
        get extra debug information reported in this module to make easier to spot
        in logs.

        Restore the Settings Stack by poping one or more frames.

        :param msg: Text to add to debug messages to give context
        :param initial_frame: True when this is the for the first frame created on entry
                              to this class via doModal or show. Otherwise,
                              a secondary frame is created/destroyed
        :param settings_changes: If not None, then apply these changes
                                 to stack_top
        """
        stack_depth: int = 0
        msg_1: str = ''
        msg_2: str = ''
        if initial_frame:
            # Remove all frames created by SettingsDialog
            msg_1 = f'{msg}\nExiting SettingsDialog BEFORE restore'
            msg_2 = f'{msg}\nExiting SettingsDialog AFTER restore'
            stack_depth = self._original_stack_depth
            if (SettingsManager.get_stack_depth() <
                    self._original_stack_depth):
                MY_LOGGER.warn(f'INVALID stack_depth:')
                return
            self._original_stack_depth = -1  # Ready for next call
        else:
            msg_1 = f'{msg}\nBEFORE restore'
            msg_2 = f'{msg}\nAFTER restore'
            stack_depth = self._original_stack_depth + 1
            # Don't let stack go below the original frame created when
            # entering SettingsDialog.
            if stack_depth == SettingsManager.get_stack_depth():
                # This occurs because a check is made before modifying
                # any setting to make sure that the stack is at the proper
                # depth.
                MY_LOGGER.debug(f'{msg}  already at the proper stack_depth: '
                                f'{stack_depth}')
                return
            if (stack_depth > SettingsManager.get_stack_depth() or
                    stack_depth < self._original_stack_depth):
                MY_LOGGER.warn(f'INVALID stack_depth: '
                               f'{SettingsManager.get_stack_depth()}')
                return
        MY_LOGGER.debug(f'{msg_1} to stack_depth: {stack_depth} current: '
                        f'{SettingsManager.get_stack_depth()}')
        SettingsManager.restore_settings(stack_depth=stack_depth)

        MY_LOGGER.debug(f'{msg_2} with stack_depth: '
                        f' {SettingsManager.get_stack_depth()}')
        if initial_frame:
            type(self)._instance.busy = False

    def get_engine_choices(self,
                           engine_key: ServiceID | None) -> Tuple[List[Choice], int]:
        """
            Generates a list of choices for TTS engine that
            can be used by select_engine.

            The choices will be based on the engines which are
            capable of voicing the current Kodi locale and sorted by
            the best langauge match score for each engine.

        :param engine_key: Optional. If supplied, the index to that engine in
               the list of choices is returned, otherwise the returned index is -1.
        :return: A list of all the choices as well as an index to the
                 current engine
        """
        try:
            MY_LOGGER.debug(f'target engine: {engine_key}')
            _, _, _, kodi_language = LanguageInfo.get_kodi_locale_info()
            kodi_language: langcodes.Language
            current_engine_idx: int
            choices: List[Choice]
            choices, current_engine_idx = SettingsHelper.get_engines_supporting_lang(
                    engine_key)
            # if engine_id is None, or not found, then current_engine_idx == -1
            idx: int = 0
            for choice in choices:
                choice: Choice
                MY_LOGGER.debug(f'engine: {choice.engine_key} '
                                f'lang_info: {choice.lang_info}')
                choice.label = SettingsHelper.get_formatted_label(
                        choice.lang_info,
                        kodi_language=kodi_language,
                        format_type=FormatType.DISPLAY)
                MY_LOGGER.debug(f'lang_info: {choice.lang_info}')
                choice.hint = f'choice {idx}'
                idx += 1
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'choices: {choices}')
            self.save_current_choices(choices, current_engine_idx)
            # auto_choice_label: str = Messages.get_msg(Messages.AUTO)
            # current_value = Settings.get_service_key()
            return choices, current_engine_idx
        except Exception as e:
            MY_LOGGER.exception('')

    def save_current_choices(self, choices: List[Choice], selection_index: int) -> None:
        """
        Simple mechanism to save SelectionDialog's list of choices as well
        as selected index. Used to save results beteween calls. Should change
        to something a bit less crude.

        Use retrieve_current_choices to, um, retrieve the values

        :param choices: List[Choice] choices presented to user
        :param selection_index: Index into choices indicating what user chose
        :return:
        """
        self.saved_choices = choices
        self.saved_selection_index = selection_index

    def retrieve_current_choices(self) -> Tuple[List[Choice], int]:
        """
           Simple mechanism to retrieve SelectionDialog's list of choices as well
           as selected index. Used to save results beteween calls. Should change
           to something a bit less crude.

           Use save_current_choices to, um, retrieve the values
           :return:
           """
        return self.saved_choices, self.saved_selection_index
