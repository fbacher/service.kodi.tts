# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys
from enum import auto

from common import *

from backends.settings.i_validators import (AllowedValue, IBoolValidator,
                                            IGenderValidator,
                                            IIntValidator,
                                            INumericValidator, IStringValidator,
                                            IValidator)
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from common.exceptions import *
from common.logger import *
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
    def get_addons_md5(cls) -> str:
        addon_md5_val: IValidator = SettingsMap.get_validator(
                SettingsProperties.TTS_SERVICE, SettingsProperties.ADDONS_MD5)
        addon_md5: str = addon_md5_val.get_tts_value()
        # MY_LOGGER.debug(f'addons MD5: {SettingsProperties.ADDONS_MD5}')
        return addon_md5

    @classmethod
    def set_addons_md5(cls, addon_md5: str) -> None:
        addon_md5_val: IValidator = SettingsMap.get_validator(
                SettingsProperties.TTS_SERVICE, SettingsProperties.ADDONS_MD5)
        addon_md5_val.set_tts_value(addon_md5)
        # MY_LOGGER.debug(f'setting addons md5: {addon_md5}')
        return

    @classmethod
    def get_api_key(cls, engine_id: str = None) -> str:
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll()
            #  service_id = super()._current_engine
        # MY_LOGGER.debug(f'getting api_key for service_id: {service_id}')
        engine_api_key_validator: IValidator
        engine_api_key_validator = (SettingsMap.
                                    get_validator(engine_id,
                                                  property_id=SettingsProperties.API_KEY))
        api_key: str = engine_api_key_validator.get_tts_value()
        return api_key

    @classmethod
    def set_api_key(cls, api_key: str, engine_id: str = None) -> None:
        # MY_LOGGER.debug(f'setting api_key: {api_key}')
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll()
            #  service_id = super()._current_engine
        engine_api_key_validator: IValidator
        engine_api_key_validator = SettingsMap.get_validator(engine_id,
                                                             property_id=SettingsProperties.API_KEY)
        engine_api_key_validator.set_tts_value(api_key)
        return

    @classmethod
    def get_engine_id(cls, bootstrap: bool = False) -> str | None:
        #  MY_LOGGER.debug(f'boostrap: {bootstrap}')
        if bootstrap:
            return SettingsLowLevel.get_engine_id_ll(default=None, bootstrap=bootstrap)

        engine_id: str = SettingsLowLevel.getSetting(SettingsProperties.ENGINE, None)
        #  MY_LOGGER.debug(f'service_id: {service_id}')
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll(default=None, bootstrap=bootstrap)
        if engine_id is None:  # Not set, use default
            # Validator only helps with default and possible values
            engine_id_validator = SettingsMap.get_validator(SettingsProperties.ENGINE,
                                                            None)
            if engine_id_validator is not None:
                engine_id: str = engine_id_validator.get_tts_value()
        return engine_id

    @classmethod
    def set_engine_id(cls, engine_id: str | StrEnum) -> None:
        engine_str: str = ''
        if isinstance(engine_id, StrEnum):
            engine_id: StrEnum
            engine_str: str = engine_id.value
        else:
            engine_str = engine_id
        engine_id_validator = SettingsMap.get_validator(SettingsProperties.ENGINE,
                                                        '')
        engine_id_validator.set_tts_value(engine_str)
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
        return SettingsProperties.ESPEAK_ID

    @classmethod
    def extended_help_on_startup(cls) -> bool:
        return SettingsLowLevel.get_setting_bool(
                SettingsProperties.EXTENDED_HELP_ON_STARTUP)

    @classmethod
    def extended_help_on_startup(cls, extended_help_enabled: bool) -> None:
        SettingsLowLevel.set_setting_bool(SettingsProperties.EXTENDED_HELP_ON_STARTUP,
                                          extended_help_enabled)

    @classmethod
    def get_gender(cls, engine_id: str = None) -> Genders:
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll()
        # MY_LOGGER.debug(f'getting gender for service_id: {service_id}')
        gender_val: IGenderValidator
        gender_val = SettingsMap.get_validator(Services.TTS_SERVICE,
                                               property_id=SettingsProperties.GENDER)
        gender: Genders = gender_val.get_tts_value()
        return gender

    @classmethod
    def set_gender(cls, gender: int, engine_id: str = None) -> None:
        # MY_LOGGER.debug(f'setting gender: {gender}')
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll()
        engine_gender_validator: IValidator
        engine_gender_validator = SettingsMap.get_validator(engine_id,
                                                            property_id=SettingsProperties.GENDER)
        engine_gender_validator.set_tts_value(gender)
        return

    @classmethod
    def is_hint_text_on_startup(cls) -> bool:
        return SettingsLowLevel.get_setting_bool(SettingsProperties.HINT_TEXT_ON_STARTUP)

    @classmethod
    def set_hint_text_on_startup(cls, hint_text_enabled: bool)  -> None:
        SettingsLowLevel.set_setting_bool(SettingsProperties.HINT_TEXT_ON_STARTUP,
                                          hint_text_enabled)

    @classmethod
    def get_language(cls, engine_id: str = None) -> str:
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll()
        language: str | None = None
        try:
            # MY_LOGGER.debug(f'getting language for service_id: {service_id}')
            engine_language_validator: IValidator
            engine_language_validator = SettingsMap.get_validator(engine_id,
                                                                  property_id=SettingsProperties.LANGUAGE)
            if engine_language_validator is not None:
                language = engine_language_validator.get_tts_value()
            else:
                language = cls.get_setting_str(SettingsProperties.LANGUAGE, engine_id,
                                               default=None)
        except Exception as e:
            MY_LOGGER.exception('')
        return language

    @classmethod
    def set_language(cls, language: str, engine_id: str = None) -> None:
        # MY_LOGGER.debug(f'setting language: {language}')
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll()
            #  service_id = super()._current_engine
        lang_val: IValidator
        lang_val = SettingsMap.get_validator(engine_id,
                                             property_id=SettingsProperties.LANGUAGE)
        lang_val.set_tts_value(language)
        return

    @classmethod
    def get_voice_path(cls, service_id: str = None) -> str:
        if service_id is None:
            service_id = SettingsLowLevel.get_engine_id_ll()  # super()._current_engine
        validator: IStringValidator
        property_id: str = SettingsProperties.VOICE_PATH
        validator = SettingsMap.get_validator(service_id,  property_id=property_id)
        value: str = validator.getInternalValue()
        return value

    @classmethod
    def set_voice_path(cls, voice_path: str = None, service_id: str = None) -> None:
        if service_id is None:
            service_id = SettingsLowLevel.get_engine_id_ll()
            #  service_id = super()._current_engine
        engine_language_validator: IStringValidator
        property_id: str = SettingsProperties.VOICE_PATH
        validator: IStringValidator = SettingsMap.get_validator(service_id,
                                                                property_id=property_id)
        validator.setInternalValue(voice_path)
        return

    @classmethod
    def get_volume(cls, engine_id: str = None) -> float:
        volume_val: INumericValidator = SettingsMap.get_validator(
            SettingsProperties.TTS_SERVICE, SettingsProperties.VOLUME)
        return volume_val.get_value()

    @classmethod
    def set_volume(cls, volume: float, engine_id: str = None) -> None:
        #  MY_LOGGER.debug(f'{super()._current_engine} {SettingsLowLevel._current_engine}')
        volume_val: INumericValidator = SettingsMap.get_validator(
                SettingsProperties.TTS_SERVICE, SettingsProperties.VOLUME)
        volume_val.set_value(volume)
        return

    @classmethod
    def get_speed(cls) -> float:
        speed_val: INumericValidator = SettingsMap.get_validator(
                SettingsProperties.TTS_SERVICE, SettingsProperties.SPEED)
        return speed_val.get_value()

    @classmethod
    def set_speed(cls, speed: float) -> None:
        speed_val: INumericValidator = SettingsMap.get_validator(
                SettingsProperties.TTS_SERVICE, SettingsProperties.SPEED)
        speed_val.set_value(speed)
        return

    @classmethod
    def get_voice(cls, engine_id: str | None) -> str:
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll()
            # service_id = super()._current_engine
        voice_val: IValidator = SettingsMap.get_validator(
                engine_id, SettingsProperties.VOICE)
        voice: str = voice_val.get_tts_value()
        return voice

    @classmethod
    def set_voice(cls, voice: str, engine_id: str | None) -> None:
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll()
            # service_id = super()._current_engine
        voice_val: IValidator = SettingsMap.get_validator(
                engine_id, SettingsProperties.VOICE)
        MY_LOGGER.debug(f'Setting voice {voice} for service_id: {engine_id}')
        voice_val.set_tts_value(voice)
        return None

    @classmethod
    def is_use_cache(cls, engine_id: str = None) -> bool | None:
        result: bool = None
        try:
            if engine_id is None:
                engine_id = cls.get_engine_id()
            cache_validator: IBoolValidator
            cache_validator = SettingsMap.get_validator(engine_id,
                                                        SettingsProperties.CACHE_SPEECH)
            if cache_validator is None:
                return False

            result: bool = cache_validator.get_tts_value()
        except NotImplementedError:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return result

    @classmethod
    def set_use_cache(cls, use_cache: bool, engine_id: str = None) -> None:
        result: bool = None
        try:
            if engine_id is None:
                engine_id = cls.get_engine_id()
            cache_validator: IBoolValidator
            cache_validator = SettingsMap.get_validator(engine_id,
                                                        SettingsProperties.CACHE_SPEECH)
            cache_validator.set_tts_value(use_cache)
        except NotImplementedError:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return

    @classmethod
    def get_pitch(cls, engine_id: str = None) -> float | int:
        pitch_validator: IIntValidator
        pitch_validator = SettingsMap.get_validator(service_id=Services.TTS_SERVICE,
                                                    property_id=SettingsProperties.PITCH)
        if pitch_validator is None:
            raise NotImplementedError()

        if cls.is_use_cache(engine_id):
            pitch = pitch_validator.default_value
        else:
            pitch: float = pitch_validator.get_tts_value()
        if pitch_validator.integer:
            pitch = int(round(pitch))
        else:
            pitch = float(pitch)
        return pitch

    @classmethod
    def set_pitch(cls, pitch: float, engine_id: str = None) -> None:
        val: IValidator = SettingsMap.get_validator(Services.TTS_SERVICE,
                                                    SettingsProperties.PITCH)
        val.set_tts_value(pitch)
        return

    @classmethod
    def get_player_mode(cls, engine_id: str = None) -> PlayerMode:

        val: IStringValidator
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll()
            #  service_id = super()._current_engine
        val = SettingsMap.get_validator(service_id=engine_id,
                                        property_id=SettingsProperties.PLAYER_MODE)
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
            MY_LOGGER.debug(f'Invalid player_mode {player_mode_str} for this '
                            f'engine: {engine_id}. Setting to default.')
            for allowed_value in allowed_values:
                MY_LOGGER.debug(f'Allowed_value: {allowed_value}')
            MY_LOGGER.debug(f'player_mode: {player_mode_str}')
        player_mode = PlayerMode(player_mode_str)
        return player_mode

    @classmethod
    def set_player_mode(cls, player_mode: PlayerMode, engine_id: str = None) -> None:
        val: IStringValidator
        val = SettingsMap.get_validator(service_id=engine_id,
                                        property_id=SettingsProperties.PLAYER_MODE)

        val.set_tts_value(player_mode.value)
        MY_LOGGER.debug(f'Setting {engine_id} player_mode to '
                        f'{player_mode.value}')
        return

    '''
    @classmethod
    def get_pipe(cls, service_id: str = None) -> bool:
        return False

        pipe_validator: IBoolValidator
        pipe_validator = SettingsMap.get_validator(service_id=service_id,
                                                   property_id=SettingsProperties.PIPE)
        # MY_LOGGER.debug(f'Boolvalidator value: {pipe_validator.get_tts_value()} '
        #                   f'const: {pipe_validator.is_const()}')
        if pipe_validator is None:
            raise NotImplemented()

        pipe: bool = pipe_validator.get_tts_value()
        return pipe

    @classmethod
    def set_pipe(cls, pipe: bool, service_id: str = None) -> None:
        return

        val: IValidator = SettingsMap.get_validator(service_id,
                                                    SettingsProperties.PIPE)
        val.set_tts_value(pipe)
        return
    '''

    @classmethod
    def get_auto_item_extra(cls, default_value: bool = False) -> bool:
        value: bool = cls.get_setting_bool(
                SettingsProperties.AUTO_ITEM_EXTRA,
                engine_id=SettingsProperties.TTS_SERVICE,
                ignore_cache=False,
                default=default_value)
        # MY_LOGGER.debug(f'{SettingsProperties.AUTO_ITEM_EXTRA}: {value}')
        return value

    @classmethod
    def set_auto_item_extra(cls, value: bool) -> None:
        # MY_LOGGER.debug(f'setting {SettingsProperties.AUTO_ITEM_EXTRA}: {value}')
        cls.set_setting_bool(SettingsProperties.AUTO_ITEM_EXTRA, value,
                             SettingsProperties.TTS_SERVICE)
        return

    @classmethod
    def get_auto_item_extra_delay(cls, default_value: int = None) -> int:
        value: int = cls.get_setting_int(
                SettingsProperties.AUTO_ITEM_EXTRA_DELAY,
                 service_id=SettingsProperties.TTS_SERVICE,
                default_value=default_value)
        #  MY_LOGGER.debug(f'{SettingsProperties.AUTO_ITEM_EXTRA_DELAY}: {value}')
        return value

    @classmethod
    def set_auto_item_extra_delay(cls, value: int) -> None:
        # MY_LOGGER.debug(f'setting {SettingsProperties.AUTO_ITEM_EXTRA_DELAY}: {
        # value}')
        cls.set_setting_int(SettingsProperties.AUTO_ITEM_EXTRA_DELAY, value,
                            SettingsProperties.TTS_SERVICE)
        return

    @classmethod
    def get_reader_on(cls, default_value: bool = None) -> bool:
        reader_on_val: IValidator
        reader_on_val = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                  SettingsProperties.READER_ON)
        value: bool = reader_on_val.get_tts_value()
        # MY_LOGGER.debug(f'{SettingsProperties.READER_ON}.'
        #                   f'{SettingsProperties.TTS_SERVICE}: {value}')
        return value

    @classmethod
    def set_reader_on(cls, value: bool) -> None:
        reader_on_val: IValidator
        reader_on_val = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                  SettingsProperties.READER_ON)
        # MY_LOGGER.debug(f'{SettingsProperties.READER_ON}: {value}')
        reader_on_val.set_tts_value(value)
        return

    @classmethod
    def get_speak_list_count(cls, default_value: bool = None) -> bool:
        value: bool = cls.get_setting_bool(
                SettingsProperties.SPEAK_LIST_COUNT,
                engine_id=SettingsProperties.TTS_SERVICE,
                ignore_cache=False,
                default=default_value)

        # MY_LOGGER.debug(f'{SettingsProperties.SPEAK_LIST_COUNT}: {value}')
        return value

    @classmethod
    def set_speak_list_count(cls, value: bool) -> None:
        # MY_LOGGER.debug(f'setting {SettingsProperties.SPEAK_LIST_COUNT}: {value}')
        cls.set_setting_bool(SettingsProperties.SPEAK_LIST_COUNT, value,
                             SettingsProperties.TTS_SERVICE)
        return

    '''
    @classmethod
    def uses_pipe(cls, service_id: str = None) -> bool:
        if service_id is None:
            service_id = super()._current_engine
        pipe_validator: IValidator
        pipe_validator = SettingsMap.get_validator(service_id,
                                                   property_id=SettingsProperties.PIPE)
        pipe_validator: BoolValidator
        use_pipe: bool = pipe_validator.get_tts_value()
        #  MY_LOGGER.debug(f'uses_pipe.{service_id} = {use_pipe}')
        return use_pipe
    '''

    @classmethod
    def get_player_id(cls, engine_id: str = None) -> str:
        if engine_id is None:
            engine_id = SettingsLowLevel.get_engine_id_ll()
            #  service_id = super()._current_engine
        player_validator: IValidator
        player_validator = SettingsMap.get_validator(engine_id,
                                                     property_id=SettingsProperties.PLAYER)
        player_id: str = player_validator.get_tts_value()
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'player.{engine_id} = {player_id}')
        return player_id

    @classmethod
    def set_player(cls, value: str, engine_id: str = None) -> bool:
        """
        TODO: END HIGH LEVEL
        :param value:
        :param engine_id:
        :return:
        """
        # MY_LOGGER.debug(f'setting {SettingsProperties.PLAYER}: {value}')
        return cls.set_setting_str(SettingsProperties.PLAYER, value,
                                   engine_id=engine_id)

    @classmethod
    def set_module(cls, value: str, engine_id: str = None) -> bool:
        """
        TODO: END HIGH LEVEL
        :param value:
        :param engine_id:
        :return:
        """
        # MY_LOGGER.debug(f'setting {SettingsProperties.PLAYER}: {value}')
        return cls.set_setting_str(SettingsProperties.MODULE, value,
                                   engine_id=engine_id)

    @classmethod
    def get_converter(cls, engine_id: str = None) -> str:
        value: str = cls.get_setting_str(SettingsProperties.TRANSCODER,
                                         engine_id=engine_id,
                                         ignore_cache=False,
                                         default=None)
        # MY_LOGGER.debug(f'converter.{service_id} = {value}')
        return value

    @classmethod
    def set_converter(cls, value: str, engine_id: str = None) -> bool:
        """
        TODO: END HIGH LEVEL
        :param value:
        :param engine_id:
        :return:
        """
        MY_LOGGER.debug(f'setting {SettingsProperties.TRANSCODER}: {value}')
        return cls.set_setting_str(SettingsProperties.TRANSCODER, value,
                                   engine_id=engine_id)

    @classmethod
    def get_cache_base(cls) -> str:
        cache_base: str
        cache_base = cls.getSetting(SettingsProperties.CACHE_PATH,
                                    SettingsProperties.TTS_SERVICE,
                                    SettingsProperties.CACHE_PATH_DEFAULT)
        tmp: str = cache_base.strip()
        if tmp != cache_base:
            MY_LOGGER.debug(f'cache_base changed old: {cache_base} new: {tmp}')
            cache_base = tmp
            cls.set_setting_str(SettingsProperties.CACHE_PATH,
                                cache_base,
                                SettingsProperties.TTS_SERVICE)
        return cache_base

    """
        NON-PERSISTED SETTINGS
        
        These settings are determined dynamically at run time. They are placed in
        this class because 1) Familiar location and mechanism
                           2) Reduces possibility of circular dependencies
    """

    _transient_settings: Dict[str, Any] = {}

    @classmethod
    def set_current_input_format(cls, service_id: str, audio_type: AudioType) -> None:
        """
          Holds the currently configured input audio_type of a particular service
          ex: MPV currently consumes only MP3 audio input.

        :param service_id:
        :param audio_type:
        :return:
        """
        key: str = f'{service_id}.{Transient.AUDIO_TYPE_INPUT}'
        cls._transient_settings[key] = audio_type

    @classmethod
    def get_current_input_format(cls, service_id: str) -> AudioType | None:
        """
        Gets the currently configured input audio_type of a particular service

        :param service_id:
        :return:
        """
        key: str = f'{service_id}.{Transient.AUDIO_TYPE_INPUT}'
        return cls._transient_settings[key]

    @classmethod
    def set_current_output_format(cls, service_id: str, audio_type: AudioType) -> None:
        """
        Holds the currently configured input audio_type of a particular service
          ex: MPV currently consumes only MP3 audio output

        :param service_id:
        :param audio_type:
        :return:
        """
        key: str = f'{service_id}.{Transient.AUDIO_TYPE_OUTPUT}'
        cls._transient_settings[key] = audio_type

    @classmethod
    def get_current_output_format(cls, service_id: str) -> AudioType | None:
        """
        Gets the currently configured output audio_type of a particular service

        :param service_id:
        :return:
        """
        key: str = f'{service_id}.{Transient.AUDIO_TYPE_OUTPUT}'
        return cls._transient_settings[key]

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
