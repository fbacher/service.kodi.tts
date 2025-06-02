# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys
from enum import auto

from common import *

from backends.settings.i_validators import (AllowedValue, IBoolValidator,
                                            IEngineValidator, IGenderValidator,
                                            IIntValidator,
                                            INumericValidator, ISimpleValidator,
                                            IStringValidator,
                                            IValidator)
from backends.settings.service_types import (PlayerType, ServiceKey, Services,
                                             ServiceType,
                                             ServiceID)
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import SettingsMap
from common.exceptions import *
from common.logger import *
from common.service_broker import ServiceBroker
from common.service_status import StatusType
from common.setting_constants import AudioType, Genders, PlayerMode
from common.settings_bridge import SettingsBridge
from common.settings_low_level import SettingsLowLevel
try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from common.transient_properties import Transient

MY_LOGGER = BasicLogger.get_logger(__name__)


class Settings(SettingsLowLevel):
    """
    # The built-in Kodi settings configuration does not work well with this
    # add-on because the kodi config gui is unable to:
    #  - Adjusting the audio to reflect the changes as they occur
    #  - The UI and it's voicing does not work well with some of the
    #    complex interactions between settings
    #
    # Therefore we have our own settings gui. To support this, this settings
    # module provides the ability to make changes to a local copy of settings
    # providing the ability to roll-back or commit them atomically when the user
    # is happy with the changes.
    #
    # Each backend validates changes to settings before any changes are made here

    # working copy of settings. Changes must be validated before changes allowed
    # here
    """
    _initialized: bool = False

    @classmethod
    def init(cls):
        if not cls._initialized:
            cls._initialized = True
            SettingsBridge.set_settings_ref(cls)

    @staticmethod
    def on_settings_changed() -> None:
        """

        :return:
        """
        # Settings.load_settings()

    @classmethod
    def set_availability(cls, service_key: ServiceID, availability: StatusType) -> None:
        service_key = service_key.with_prop(SettingProp.AVAILABILITY)
        SettingsMap.set_available(service_key, availability)
        SettingsLowLevel.set_setting_str(service_key, availability)

    @classmethod
    def get_availability(cls, service_key: ServiceID) -> StatusType:
        service_key = service_key.with_prop(SettingProp.AVAILABILITY)
        availability: str = SettingsLowLevel.get_setting_str(service_key)
        return StatusType(availability)

    @classmethod
    def get_addons_md5(cls) -> str:
        service_key: ServiceID = ServiceKey.TTS_KEY
        service_key = service_key.with_prop(SettingProp.ADDONS_MD5)
        addon_md5_val: IValidator = SettingsMap.get_validator(service_key)
        addon_md5: str = addon_md5_val.get_tts_value()
        # MY_LOGGER.debug(f'addons MD5: {SettingProp.ADDONS_MD5}')
        return addon_md5

    @classmethod
    def set_addons_md5(cls, addon_md5: str) -> None:
        service_key: ServiceID = ServiceKey.TTS_KEY
        service_key = service_key.with_prop(SettingProp.ADDONS_MD5)
        addon_md5_val: IValidator = SettingsMap.get_validator(service_key)
        addon_md5_val.set_tts_value(addon_md5)
        # MY_LOGGER.debug(f'setting addons md5: {addon_md5}')
        return

    @classmethod
    def get_api_key(cls, engine_key: ServiceID = None) -> str:
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        api_service_key = engine_key.with_prop(SettingProp.API_KEY)
        # MY_LOGGER.debug(f'getting api_key for setting_id: {setting_id}')
        engine_api_key_validator: IValidator
        engine_api_key_validator = (SettingsMap.
                                    get_validator(api_service_key))
        api_key: str = engine_api_key_validator.get_tts_value()
        return api_key

    @classmethod
    def set_api_key(cls, api_key: str,
                    service_key: ServiceID | None = None) -> None:
        # MY_LOGGER.debug(f'setting api_key: {api_key}')
        if service_key is None:
            service_key = cls.get_service_key(SettingProp.API_KEY)
        else:
            service_key = service_key.with_prop(SettingProp.API_KEY)
        e_api_key_val: IValidator
        e_api_key_val = SettingsMap.get_validator(service_key)
        e_api_key_val.set_tts_value(api_key)
        return

    @classmethod
    def get_service_key(cls, property_id: str,
                        service_id: str | None = None,
                        service_type: ServiceType = ServiceType.ENGINE) -> ServiceID:
        if service_id is None:
            service_id = cls.get_engine_id()
        return ServiceID(service_type, service_id, property_id)

    @classmethod
    def get_engine_key(cls, bootstrap: bool = False) -> ServiceID | None:
        if bootstrap:
            engine_id: ServiceID
            engine_id = SettingsLowLevel.get_engine_id_ll(default=None,
                                                          ignore_cache=bootstrap)
            return engine_id
        engine_id_validator: IEngineValidator
        engine_id_validator = ServiceBroker.get_engine_validator()
        return engine_id_validator.get_service_key()

    @classmethod
    def get_engine_id(cls, bootstrap: bool = False) -> str | None:
        """
        Gets the current engine_id

        :param bootstrap: Used ONLY during the ignore_cache process
        :return:

        If the current engine_id is for an unusable engine, then a
        ServiceUnavailable exception is thrown. Remedial action is
        call Configure.validate_repair
        """
        #  MY_LOGGER.debug(f'boostrap: {ignore_cache}')
        if bootstrap:
            engine_id: ServiceID
            engine_id = SettingsLowLevel.get_engine_id_ll(default=None,
                                                          ignore_cache=bootstrap)
            return engine_id.service_id
        engine_id_validator: IEngineValidator
        engine_id_validator = ServiceBroker.get_engine_validator()
        return engine_id_validator.get_service_key().service_id

    @classmethod
    def set_engine(cls, engine_srvc_id: ServiceID) -> None:
        engine_id_validator: IEngineValidator
        engine_id_validator = ServiceBroker.get_engine_validator()
        engine_id_validator.set_service_key(engine_srvc_id)
        return

    @classmethod
    def get_alternate_engine_id(cls) -> str | None:
        """
           Returns the id of the engine to use in case the current/ctive
           engine is too slow to respond. This is typically used when the current
           engine is a remote service or is a slower, higher quality engine. The
           alternate engine should be a fast engine.

           Note that this is different from the default engine, which is used when
           the user preferred (current) engine is broken or otherwise unavailable.
           :return:
           """
        return SettingProp.ESPEAK_ID

    @classmethod
    def get_extended_help_on_startup(cls) -> bool:
        service_key: ServiceID
        service_key = ServiceKey.TTS_KEY.with_prop(
                                            SettingProp.EXTENDED_HELP_ON_STARTUP)
        return SettingsLowLevel.get_setting_bool(service_key)

    @classmethod
    def set_extended_help_on_startup(cls, extended_help_enabled: bool) -> None:
        service_key: ServiceID
        service_key = ServiceKey.TTS_KEY.with_prop(
                SettingProp.EXTENDED_HELP_ON_STARTUP)
        SettingsLowLevel.set_setting_bool(service_key,
                                          extended_help_enabled)

    @classmethod
    def get_hint_text_on_startup(cls) -> bool:
        service_key: ServiceID
        service_key = ServiceKey.TTS_KEY.with_prop(SettingProp.HINT_TEXT_ON_STARTUP)
        return SettingsLowLevel.get_setting_bool(service_key)

    @classmethod
    def set_hint_text_on_startup(cls, startup_hint_text_enabled: bool) -> bool:
        service_key: ServiceID
        service_key = ServiceKey.TTS_KEY.with_prop(SettingProp.HINT_TEXT_ON_STARTUP)
        return SettingsLowLevel.get_setting_bool(service_key)

    @classmethod
    def get_configure_on_startup(cls) -> bool:
        service_key: ServiceID
        service_key = ServiceKey.TTS_KEY.with_prop(SettingProp.CONFIGURE_ON_STARTUP)
        return SettingsLowLevel.get_setting_bool(service_key)

    @classmethod
    def set_configure_on_startup(cls, configure_on_startup: bool) -> None:
        service_key: ServiceID
        service_key = ServiceKey.TTS_KEY.with_prop(SettingProp.CONFIGURE_ON_STARTUP)
        SettingsLowLevel.set_setting_bool(service_key, configure_on_startup)

    @classmethod
    def get_introduction_on_startup(cls) -> bool:
        service_key: ServiceID
        service_key = ServiceKey.TTS_KEY.with_prop(
                SettingProp.INTRODUCTION_ON_STARTUP)
        return SettingsLowLevel.get_setting_bool(service_key)

    @classmethod
    def set_introduction_on_startup(cls, introduction_on_startup: bool) -> None:
        service_key: ServiceID
        service_key = ServiceKey.TTS_KEY.with_prop(SettingProp.INTRODUCTION_ON_STARTUP)
        SettingsLowLevel.set_setting_bool(service_key, introduction_on_startup)

    @classmethod
    def get_help_config_on_startup(cls) -> bool:
        service_key: ServiceID
        service_key = ServiceKey.TTS_KEY.with_prop(SettingProp.HELP_CONFIG_ON_STARTUP)
        return SettingsLowLevel.get_setting_bool(service_key)

    @classmethod
    def set_help_config_on_startup(cls, help_config_on_startup: bool) -> None:
        service_key: ServiceID
        service_key = ServiceKey.TTS_KEY.with_prop(SettingProp.HELP_CONFIG_ON_STARTUP)
        SettingsLowLevel.set_setting_bool(service_key, help_config_on_startup)

    @classmethod
    def get_gender(cls, engine_key: ServiceID | None = None) -> Genders:
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        gender_svc_key = engine_key.with_prop(SettingProp.GENDER)
        # MY_LOGGER.debug(f'getting gender for setting_id: {setting_id}')
        gender_val: IGenderValidator
        gender_val = SettingsMap.get_validator(gender_svc_key)
        gender: Genders = Genders(gender_val.get_tts_value())
        return gender

    @classmethod
    def set_gender(cls, gender: Genders,
                   engine_key: ServiceID | None = None) -> None:
        # MY_LOGGER.debug(f'setting gender: {gender}')
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        gender_svc_key = engine_key.with_prop(SettingProp.GENDER)
        # MY_LOGGER.debug(f'getting gender for setting_id: {setting_id}')
        gender_val: IGenderValidator
        gender_val = SettingsMap.get_validator(gender_svc_key)
        e_gender_val: IGenderValidator
        e_gender_val = SettingsMap.get_validator(gender_svc_key)
        e_gender_val.set_tts_value(gender)
        return

    @classmethod
    def is_hint_text_on_startup(cls) -> bool:
        return SettingsLowLevel.get_setting_bool(ServiceKey.HINT_TEXT_ON_STARTUP)

    @classmethod
    def set_hint_text_on_startup(cls, hint_text_enabled: bool)  -> None:
        SettingsLowLevel.set_setting_bool(ServiceKey.HINT_TEXT_ON_STARTUP,
                                          hint_text_enabled)

    @classmethod
    def is_initial_run(cls) -> bool:
        MY_LOGGER.debug(f'initial_run key: {ServiceKey.INITIAL_RUN} short_key: '
                        f'{ServiceKey.INITIAL_RUN.short_key}')
        return SettingsLowLevel.get_setting_bool(ServiceKey.INITIAL_RUN,
                                                 ignore_cache=True)

    @classmethod
    def set_initial_run(cls, initial_run: bool) -> None:
        SettingsLowLevel.set_setting_bool(ServiceKey.INITIAL_RUN,
                                          initial_run)

    @classmethod
    def get_language(cls, engine_key: ServiceID | None = None) -> str:
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        language: str | None = None
        try:
            # MY_LOGGER.debug(f'getting language for setting_id: {setting_id}')
            lang_service_key: ServiceID
            lang_service_key = engine_key.with_prop(SettingProp.LANGUAGE)
            e_lang_val: IValidator
            e_lang_val = SettingsMap.get_validator(lang_service_key)
            if e_lang_val is not None:
                language = e_lang_val.get_tts_value()
            else:
                language = cls.get_setting_str(lang_service_key, default=None)
        except Exception as e:
            MY_LOGGER.exception('')
        return language

    @classmethod
    def set_language(cls, language: str,
                     engine_key: ServiceID | None = None) -> None:
        # MY_LOGGER.debug(f'setting language: {language}')
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        try:
            # MY_LOGGER.debug(f'setting language for setting_id: {setting_id}')
            lang_service_key: ServiceID
            lang_service_key = engine_key.with_prop(SettingProp.LANGUAGE)
            e_lang_val: IValidator
            e_lang_val = SettingsMap.get_validator(lang_service_key)
            e_lang_val.set_tts_value(language)
        except Exception as e:
            MY_LOGGER.exception('')

    @classmethod
    def get_voice_path(cls, engine_key: str | ServiceID | None = None) -> str:
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        if isinstance(engine_key, str):
            engine_key = ServiceID(ServiceType.ENGINE, engine_key)
        validator: IStringValidator
        property_id: str = SettingProp.VOICE_PATH
        voice_key: ServiceID = engine_key.with_prop(property_id)
        validator = SettingsMap.get_validator(voice_key)
        value: str = validator.getInternalValue()
        return value

    @classmethod
    def set_voice_path(cls, voice_path: str = None,
                       engine_key: str | ServiceID | None  = None) -> None:
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        if isinstance(engine_key, str):
            engine_key = ServiceID(ServiceType.ENGINE, engine_key)
        engine_language_validator: IStringValidator
        property_id: str = SettingProp.VOICE_PATH
        voice_key: ServiceID = engine_key.with_prop(property_id)
        validator: IStringValidator = SettingsMap.get_validator(voice_key)
        validator.setInternalValue(voice_path)
        return

    @classmethod
    def get_volume(cls) -> float:
        volume_val: INumericValidator = SettingsMap.get_validator(ServiceKey.VOLUME)
        return volume_val.get_value()

    @classmethod
    def set_volume(cls, volume: float) -> None:
        volume_val: INumericValidator = SettingsMap.get_validator(ServiceKey.VOLUME)
        volume_val.set_value(volume)
        return

    @classmethod
    def get_speed(cls) -> float:
        speed_val: INumericValidator = SettingsMap.get_validator(ServiceKey.SPEED)
        return speed_val.get_value()

    @classmethod
    def set_speed(cls, speed: float) -> None:
        speed_val: INumericValidator = SettingsMap.get_validator(ServiceKey.SPEED)
        speed_val.set_value(speed)
        return

    @classmethod
    def get_voice(cls, engine_key: ServiceID | None) -> str:
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        voice_key: ServiceID = engine_key.with_prop(SettingProp.VOICE)
        voice_val: IValidator = SettingsMap.get_validator(voice_key)
        voice: str = voice_val.get_tts_value()
        return voice

    @classmethod
    def set_voice(cls, voice: str, engine_key: ServiceID | None) -> None:
        if engine_key is None:
            engine_id = Settings.get_engine_key()
            # setting_id = super()._current_engine
        voice_key: ServiceID = engine_key.with_prop(SettingProp.VOICE)
        voice_val: IValidator = SettingsMap.get_validator(voice_key)
        #  MY_LOGGER.debug(f'Setting voice {voice} for: {engine_key}')
        voice_val.set_tts_value(voice)
        return None

    @classmethod
    def is_use_cache(cls, engine_key: ServiceID | None = None) -> bool | None:
        result: bool | None = None
        cache_speech_key: ServiceID | None = None
        try:
            if engine_key is None:
                engine_key = cls.get_engine_key()
            cache_speech_key = engine_key.with_prop(SettingProp.CACHE_SPEECH)
            cache_validator: IBoolValidator
            cache_validator = SettingsMap.get_validator(cache_speech_key)
            if cache_validator is None:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'MISSING VALIDATOR!')
                return False
            result: bool = cache_validator.get_tts_value()
        except NotImplementedError:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'use_cache: {cache_speech_key} {result}')
        return result

    @classmethod
    def set_use_cache(cls, use_cache: bool | None,
                      engine_key: ServiceID | None = None) -> None:
        """
        Configure an engine_key use of the voice_cache

        :param use_cache: True indicates that all voicings will be cached
        :param engine_key: The id of the engine that this impacts
        :return:
        """
        result: bool | None = None
        try:
            if engine_key is None:
                engine_key = cls.get_engine_key()
            cache_speech_key: ServiceID
            cache_speech_key = engine_key.with_prop(SettingProp.CACHE_SPEECH)
            cache_validator: IBoolValidator
            cache_validator = SettingsMap.get_validator(cache_speech_key)
            cache_validator.set_tts_value(use_cache)
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'Setting {cache_speech_key} cache_speech to:'
                                   f' {use_cache}')
        except NotImplementedError:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return

    @classmethod
    def get_pitch(cls, engine_key: ServiceID) -> float | int:
        pitch_key: ServiceID
        pitch_key = engine_key.with_prop(SettingProp.PITCH)
        pitch_validator: IIntValidator
        pitch_validator = SettingsMap.get_validator(pitch_key)
        if pitch_validator is None:
            raise NotImplementedError()

        #  if cls.is_use_cache(engine_id):
        #      pitch = pitch_validator.default
        # else:
        pitch: float = pitch_validator.get_tts_value()
        if pitch_validator.integer:
            pitch = int(round(pitch))
        else:
            pitch = float(pitch)
        return pitch

    @classmethod
    def set_pitch(cls, pitch: float, service_key: ServiceID) -> None:
        pitch_key: ServiceID
        pitch_key = service_key.with_prop(SettingProp.PITCH)
        pitch_validator: IIntValidator
        pitch_validator = SettingsMap.get_validator(pitch_key)
        pitch_validator.set_tts_value(pitch)
        return

    @classmethod
    def get_player_mode(cls, engine_key: ServiceID) -> PlayerMode:
        val: IStringValidator
        # SettingsMap Validators simply check to see if the value is a valid choice
        # for this setting and engine. It does NOT check if the value is valid
        # in context with other settings.
        player_mode_key: ServiceID
        player_mode_key = engine_key.with_prop(SettingProp.PLAYER_MODE)
        val = SettingsMap.get_validator(service_id=player_mode_key)
        if val is None:
            raise NotImplemented()

        player_mode_str: str = val.get_tts_value()
        allowed_values: List[AllowedValue] = val.get_allowed_values(enabled=True)
        allowed: bool = False
        for allowed_value in allowed_values:
            allowed_value: AllowedValue
            enabled: bool
            if allowed_value.value == player_mode_str:
                allowed = allowed_value.enabled
                break
        if not allowed:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Invalid player_mode {player_mode_str} for this '
                                f'{engine_key}. Setting to default.')
            for allowed_value in allowed_values:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'Allowed_value: {allowed_value}')
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'player_mode: {player_mode_str}')
        player_mode = PlayerMode(player_mode_str)
        return player_mode

    @classmethod
    def set_player_mode(cls, player_mode: PlayerMode,
                        service_key: ServiceID | None = None) -> None:
        if service_key is None:
            service_key = cls.get_engine_key()
        player_mode_key: ServiceID
        player_mode_key = service_key.with_prop(SettingProp.PLAYER_MODE)
        val = SettingsMap.get_validator(service_id=player_mode_key)
        if val is None:
            raise NotImplemented()

        val.set_tts_value(player_mode.value)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Setting {player_mode_key} player_mode to '
                            f'{player_mode.value}')
        return

    '''
    @classmethod
    def get_pipe(cls, setting_id: str = None) -> bool:
        return False

        pipe_validator: IBoolValidator
        pipe_validator = SettingsMap.get_validator(setting_id=setting_id,
                                                   setting_id=SettingProp.PIPE)
        # MY_LOGGER.debug(f'Boolvalidator value: {pipe_validator.get_tts_value()} '
        #                   f'const: {pipe_validator.is_const()}')
        if pipe_validator is None:
            raise NotImplemented()

        pipe: bool = pipe_validator.get_tts_value()
        return pipe

    @classmethod
    def set_pipe(cls, pipe: bool, setting_id: str = None) -> None:
        return

        val: IValidator = SettingsMap.get_validator(setting_id,
                                                    SettingProp.PIPE)
        val.set_tts_value(pipe)
        return
    '''

    @classmethod
    def get_auto_item_extra(cls, default_value: bool = False) -> bool:
        value: bool = cls.get_setting_bool(ServiceKey.AUTO_ITEM_EXTRA,
                                           ignore_cache=False,
                                           default=default_value)
        # MY_LOGGER.debug(f'{SettingProp.AUTO_ITEM_EXTRA}: {value}')
        return value

    @classmethod
    def set_auto_item_extra(cls, value: bool) -> None:
        # MY_LOGGER.debug(f'setting {SettingProp.AUTO_ITEM_EXTRA}: {value}')
        cls.set_setting_bool(ServiceKey.AUTO_ITEM_EXTRA, value)
        return

    @classmethod
    def get_auto_item_extra_delay(cls, default_value: int = None) -> int:
        value: int = cls.get_setting_int(
                ServiceKey.AUTO_ITEM_EXTRA_DELAY,
                default_value=default_value)
        #  MY_LOGGER.debug(f'{SettingProp.AUTO_ITEM_EXTRA_DELAY}: {value}')
        return value

    @classmethod
    def set_auto_item_extra_delay(cls, value: int) -> None:
        # MY_LOGGER.debug(f'setting {SettingProp.AUTO_ITEM_EXTRA_DELAY}: {
        # value}')
        cls.set_setting_int(ServiceKey.AUTO_ITEM_EXTRA_DELAY, value)
        return

    @classmethod
    def get_reader_on(cls) -> bool:
        reader_on_val: IBoolValidator
        reader_on_val = SettingsMap.get_validator(ServiceKey.READER_ON)
        value: bool = reader_on_val.get_tts_value()
        # MY_LOGGER.debug(f'{SettingProp.READER_ON}.'
        #                   f'{SettingProp.TTS_SERVICE}: {value}')
        return value

    @classmethod
    def set_reader_on(cls, value: bool) -> None:
        reader_on_val: IValidator
        reader_on_val = SettingsMap.get_validator(ServiceKey.READER_ON)
        # MY_LOGGER.debug(f'{SettingProp.READER_ON}: {value}')
        reader_on_val.set_tts_value(value)
        return

    @classmethod
    def get_speak_list_count(cls, default_value: bool = None) -> bool:
        value: bool = cls.get_setting_bool(ServiceKey.SPEAK_LIST_COUNT,
                                           ignore_cache=False,
                                           default=default_value)

        # MY_LOGGER.debug(f'{SettingProp.SPEAK_LIST_COUNT}: {value}')
        return value

    @classmethod
    def set_speak_list_count(cls, value: bool) -> None:
        # MY_LOGGER.debug(f'setting {SettingProp.SPEAK_LIST_COUNT}: {value}')
        cls.set_setting_bool(ServiceKey.SPEAK_LIST_COUNT, value)
        return

    '''
    @classmethod
    def uses_pipe(cls, setting_id: str = None) -> bool:
        if setting_id is None:
            setting_id = super()._current_engine
        pipe_validator: IValidator
        pipe_validator = SettingsMap.get_validator(setting_id,
                                                   setting_id=SettingProp.PIPE)
        pipe_validator: BoolValidator
        use_pipe: bool = pipe_validator.get_tts_value()
        #  MY_LOGGER.debug(f'uses_pipe.{setting_id} = {use_pipe}')
        return use_pipe
    '''

    @classmethod
    def get_player_key(cls, engine_key: ServiceID | None = None) -> ServiceID:
        if engine_key is None:
            engine_key = cls.get_engine_key()
        # MY_LOGGER.debug(f'service_key: {engine_key} '
        #                 f'player_key: {engine_key.with_prop(SettingProp.PLAYER)}')
        player_val: IValidator
        player_val = SettingsMap.get_validator(
                engine_key.with_prop(SettingProp.PLAYER))
        player_id: str = player_val.get_tts_value()
        # MY_LOGGER.debug(f'player_id: {player_id}')
        player_key: ServiceID = ServiceID(ServiceType.PLAYER, service_id=player_id)
        # MY_LOGGER.debug(f'player_key: {player_key}')
        return player_key

    @classmethod
    def set_player(cls, value: str | PlayerType,
                   engine_key: ServiceID | None = None) -> bool:
        """
        TODO: END HIGH LEVEL
        :param value:
        :param engine_key:
        :return:
        """
        # MY_LOGGER.debug(f'setting {SettingProp.PLAYER}: {value}')
        if isinstance(value, PlayerType):
            value = value.value
        if value is None:
            value = ''
        player_key: ServiceID = engine_key.with_prop(SettingProp.PLAYER)
        return cls.set_setting_str(service_key=player_key, value=value)

    @classmethod
    def set_module(cls, value: str, service_key: ServiceID | None = None) -> bool:
        """
        TODO: END HIGH LEVEL
        :param value:
        :param service_key:
        :return:
        """
        # MY_LOGGER.debug(f'setting {SettingProp.PLAYER}: {value}')
        trans_key: ServiceID
        trans_key = service_key.with_prop(SettingProp.MODULE)
        return cls.set_setting_str(service_key=trans_key, value=value)

    @classmethod
    def get_transcoder(cls, service_key: ServiceID) -> str | None:
        trans_key: ServiceID
        trans_key = service_key.with_prop(SettingProp.TRANSCODER)
        value: str | None = cls.get_setting_str(service_key=trans_key,
                                                ignore_cache=False,
                                                default=None)
        # MY_LOGGER.debug(f'converter.{setting_id} = {value}')
        if value == '':
            value = None
        return value

    @classmethod
    def set_transcoder(cls, value: str,
                       engine_key: ServiceID | None = None) -> bool:
        """
        TODO: END HIGH LEVEL
        :param value:
        :param engine_key:
        :return:
        """
        if value is None:
            value = ''
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'setting {SettingProp.TRANSCODER}: {value} service_key: '
                            f'{engine_key}')
        trans_key: ServiceID
        trans_key = engine_key.with_prop(SettingProp.TRANSCODER)
        return cls.set_setting_str(trans_key, value)

    @classmethod
    def get_cache_base(cls, service_key: ServiceID) -> str:
        cache_base: str
        cache_base_val: ISimpleValidator = SettingsMap.get_validator(service_key)
        cache_base = cache_base_val.get_value().strip()
        return cache_base

    @classmethod
    def get_cache_suffix(cls, service_key: ServiceID) -> str:
        cache_suffix: str
        cache_suffix_val: ISimpleValidator = SettingsMap.get_validator(service_key)
        cache_suffix = cache_suffix_val.get_value().strip()
        return cache_suffix

    # No set_cache_suffix method. Don't want to allow change

    @classmethod
    def get_max_phrase_length(cls, service_key: ServiceID) -> int:
        max_length_val: ISimpleValidator = SettingsMap.get_validator(service_key)
        max_length: int = max_length_val.get_const_value()
        return max_length

    """
        NON-PERSISTED SETTINGS
        
        These settings are determined dynamically at run time. They are placed in
        this class because 1) Familiar location and mechanism
                           2) Reduces possibility of circular dependencies
    """

    _transient_settings: Dict[str, Any] = {}

    @classmethod
    def set_current_input_format(cls, service_key: ServiceID,
                                 audio_type: AudioType) -> None:
        """
          Holds the currently configured input audio_type of a particular service
          ex: MPV currently consumes only MP3 audio input.

        :param service_key:
        :param audio_type:
        :return:
        """
        audio_service: ServiceID = service_key.with_prop(Transient.AUDIO_TYPE_INPUT)
        cls._transient_settings[audio_service.service_id] = audio_type

    @classmethod
    def get_current_input_format(cls, service_key: ServiceID) -> AudioType | None:
        """
        Gets the currently configured input audio_type of a particular service

        :param service_key:
        :return:
        """
        audio_service: ServiceID = service_key.with_prop(Transient.AUDIO_TYPE_INPUT)
        return cls._transient_settings[audio_service.service_id]

    @classmethod
    def set_current_output_format(cls, service_key: ServiceID,
                                  audio_type: AudioType) -> None:
        """
        Holds the currently configured output audio_type of a particular service
          ex: MPV currently consumes only MP3 audio output

        :param service_key:
        :param audio_type:
        :return:
        """
        audio_service: ServiceID = service_key.with_prop(Transient.AUDIO_TYPE_OUTPUT)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'service: {audio_service} type: {audio_type} '
                            f'{type(audio_type)}')
        cls._transient_settings[audio_service.service_id] = audio_type

    @classmethod
    def get_current_output_format(cls, service_key: ServiceID) -> AudioType | None:
        """
        Gets the currently configured output audio_type of a particular service

        :param service_key:
        :return:
        """
        audio_service: ServiceID = service_key.with_prop(Transient.AUDIO_TYPE_OUTPUT)
        audio_type: AudioType = cls._transient_settings[audio_service.service_id]
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'service: {audio_service} type: {audio_type} '
                               f'{type(audio_type)}')
        return audio_type

    @classmethod
    def configuring_settings(cls):
        # MY_LOGGER.debug('configuring_settings hardcoded to false')
        return False

    '''
    def getBoolList(self, id: str) -> List[bool]:
    def getIntList(self, id: str) -> List[int]:
    def getNumberList(self, id: str) -> List[float]:
    def getStringList(self, id: str) -> List[str]:
    
    def setBoolList(self, id: str, values: List[bool]) -> None:
    def setIntList(self, id: str, values: List[int]) -> None:
    def setNumberList(self, id: str, values: List[float]) -> None:
    def setStringList(self, id: str, values: List[str]) -> None:
    '''


Settings.init()
