# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys

from common import *

from backends.settings.i_validators import (IBoolValidator, IGenderValidator,
                                            IIntValidator,
                                            INumericValidator, IStringValidator,
                                            IValidator)
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from common.exceptions import *
from common.logger import *
from common.setting_constants import Genders, PlayerModes
from common.settings_bridge import SettingsBridge
from common.settings_low_level import SettingsLowLevel

module_logger = BasicLogger.get_module_logger(module_path=__file__)


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
    _logger: BasicLogger = None
    _initialized: bool = False

    @classmethod
    def init(cls):
        if not cls._initialized:
            cls._initialized = True
            SettingsBridge.set_settings_ref(cls)
            cls._logger = module_logger.getChild(cls.__name__)

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
        # cls._logger.debug(f'addons MD5: {SettingsProperties.ADDONS_MD5}')
        return addon_md5

    @classmethod
    def set_addons_md5(cls, addon_md5: str) -> None:
        addon_md5_val: IValidator = SettingsMap.get_validator(
                SettingsProperties.TTS_SERVICE, SettingsProperties.ADDONS_MD5)
        addon_md5_val.set_tts_value(addon_md5)
        # cls._logger.debug(f'setting addons md5: {addon_md5}')
        return

    @classmethod
    def get_api_key(cls, engine_id: str = None) -> str:
        if engine_id is None:
            engine_id = super()._current_engine
        # cls._logger.debug(f'getting api_key for engine_id: {engine_id}')
        engine_api_key_validator: IValidator
        engine_api_key_validator = SettingsMap.get_validator(engine_id,
                                                             property_id=SettingsProperties.API_KEY)
        api_key: str = engine_api_key_validator.get_tts_value()
        return api_key

    @classmethod
    def set_api_key(cls, api_key: str, engine_id: str = None) -> None:
        # cls._logger.debug(f'setting api_key: {api_key}')
        if engine_id is None:
            engine_id = super()._current_engine
        engine_api_key_validator: IValidator
        engine_api_key_validator = SettingsMap.get_validator(engine_id,
                                                             property_id=SettingsProperties.API_KEY)
        engine_api_key_validator.set_tts_value(api_key)
        return

    @classmethod
    def get_engine_id(cls, bootstrap: bool = False) -> str | None:
        #  cls._logger.debug(f'boostrap: {bootstrap}')
        if bootstrap:
            return SettingsLowLevel.get_engine_id_ll(default=None, bootstrap=bootstrap)

        engine_id: str = SettingsLowLevel.getSetting(SettingsProperties.ENGINE, None)
        #  cls._logger.debug(f'engine_id: {engine_id}')
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
    def set_engine_id(cls, engine_id: str) -> None:
        engine_id_validator = SettingsMap.get_validator(SettingsProperties.ENGINE, '')
        engine_id_validator.set_tts_value(engine_id)
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
    def get_gender(cls, engine_id: str = None) -> Genders:
        if engine_id is None:
            engine_id = super()._current_engine
        # cls._logger.debug(f'getting gender for engine_id: {engine_id}')
        gender_validator: IGenderValidator
        gender_validator = SettingsMap.get_validator(Services.TTS_SERVICE,
                                                     property_id=SettingsProperties.GENDER)
        gender: Genders = gender_validator.get_tts_value()
        return gender

    @classmethod
    def set_gender(cls, gender: int, engine_id: str = None) -> None:
        # cls._logger.debug(f'setting gender: {gender}')
        if engine_id is None:
            engine_id = super()._current_engine
        engine_gender_validator: IValidator
        engine_gender_validator = SettingsMap.get_validator(engine_id,
                                                            property_id=SettingsProperties.GENDER)
        engine_gender_validator.set_tts_value(gender)
        return

    @classmethod
    def get_language(cls, engine_id: str = None) -> str:
        if engine_id is None:
            engine_id = super()._current_engine
        language: str = None
        try:
            # cls._logger.debug(f'getting language for engine_id: {engine_id}')
            engine_language_validator: IValidator
            engine_language_validator = SettingsMap.get_validator(engine_id,
                                                                  property_id=SettingsProperties.LANGUAGE)
            if engine_language_validator is not None:
                language = engine_language_validator.get_tts_value()
            else:
                language = cls.get_setting_str(SettingsProperties.LANGUAGE, engine_id,
                                               default=None)
        except Exception as e:
            cls._logger.exception('')
        return language

    @classmethod
    def set_language(cls, language: str, engine_id: str = None) -> None:
        # cls._logger.debug(f'setting language: {language}')
        if engine_id is None:
            engine_id = super()._current_engine
        engine_language_validator: IValidator
        engine_language_validator = SettingsMap.get_validator(engine_id,
                                                              property_id=SettingsProperties.LANGUAGE)
        engine_language_validator.set_tts_value(language)
        return

    @classmethod
    def get_voice_path(cls, service_id: str = None) -> str:
        if service_id is None:
            service_id = super()._current_engine
        validator: IStringValidator
        property_id: str = SettingsProperties.VOICE_PATH
        validator = SettingsMap.get_validator(service_id,  property_id=property_id)
        value: str = validator.getInternalValue()
        return value

    @classmethod
    def set_voice_path(cls, voice_path: str = None, service_id: str = None) -> None:
        if service_id is None:
            service_id = super()._current_engine
        engine_language_validator: IStringValidator
        property_id: str = SettingsProperties.VOICE_PATH
        validator: IStringValidator = SettingsMap.get_validator(service_id,
                                                                property_id=property_id)
        validator.setInternalValue(voice_path)
        return

    @classmethod
    def get_volume(cls, engine_id: str = None) -> int:
        if engine_id is None:
            engine_id = super()._current_engine
        volume_val: INumericValidator = SettingsMap.get_validator(
            engine_id, SettingsProperties.VOLUME)
        return volume_val.get_value()

    @classmethod
    def set_volume(cls, volume: int, engine_id: str = None) -> None:
        if engine_id is None:
            engine_id = super()._current_engine
        #  cls._logger.debug(f'{super()._current_engine} {SettingsLowLevel._current_engine}')
        volume_val: INumericValidator = SettingsMap.get_validator(
                engine_id, SettingsProperties.VOLUME)
        volume_val.set_value(volume)
        return

    @classmethod
    def get_speed(cls) -> float:
        speed_val: INumericValidator = SettingsMap.get_validator(
                SettingsProperties.TTS_SERVICE, SettingsProperties.SPEED)
        return speed_val.get_value()

    @classmethod
    def set_speed(cls, speed: int) -> None:
        speed_val: INumericValidator = SettingsMap.get_validator(
                SettingsProperties.TTS_SERVICE, SettingsProperties.SPEED)
        speed_val.set_value(speed)
        return

    @classmethod
    def get_voice(cls, engine_id: str | None) -> int:
        if engine_id is None:
            engine_id = super()._current_engine
        voice_val: IValidator = SettingsMap.get_validator(
                engine_id, SettingsProperties.VOICE)
        voice: int = voice_val.get_tts_value()
        return voice

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
            cls._logger.exception('')
        return result

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
    def get_player_mode(cls, engine_id: str = None) -> PlayerModes:

        val: IStringValidator
        if engine_id is None:
            engine_id = super()._current_engine
        val = SettingsMap.get_validator(service_id=engine_id,
                                        property_id=SettingsProperties.PLAYER_MODE)
        if val is None:
            raise NotImplemented()

        player_mode_str: str = val.get_tts_value()
        cls._logger.debug(f'player_mode: {player_mode_str}')
        player_mode = PlayerModes(player_mode_str)
        return player_mode

    @classmethod
    def set_player_mode(cls, player_mode: PlayerModes, engine_id: str = None) -> None:
        val: IStringValidator
        val = SettingsMap.get_validator(service_id=engine_id,
                                        property_id=SettingsProperties.PLAYER_MODE)
        val.set_tts_value(player_mode.name)
        return

    '''
    @classmethod
    def get_pipe(cls, engine_id: str = None) -> bool:
        return False

        pipe_validator: IBoolValidator
        pipe_validator = SettingsMap.get_validator(service_id=engine_id,
                                                   property_id=SettingsProperties.PIPE)
        # cls._logger.debug(f'Boolvalidator value: {pipe_validator.get_tts_value()} '
        #                   f'const: {pipe_validator.is_const()}')
        if pipe_validator is None:
            raise NotImplemented()

        pipe: bool = pipe_validator.get_tts_value()
        return pipe

    @classmethod
    def set_pipe(cls, pipe: bool, engine_id: str = None) -> None:
        return

        val: IValidator = SettingsMap.get_validator(engine_id,
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
        # cls._logger.debug(f'{SettingsProperties.AUTO_ITEM_EXTRA}: {value}')
        return value

    @classmethod
    def set_auto_item_extra(cls, value: bool) -> None:
        # cls._logger.debug(f'setting {SettingsProperties.AUTO_ITEM_EXTRA}: {value}')
        cls.set_setting_bool(SettingsProperties.AUTO_ITEM_EXTRA, value,
                             SettingsProperties.TTS_SERVICE)
        return

    @classmethod
    def get_auto_item_extra_delay(cls, default_value: int = None) -> int:
        value: int = cls.get_setting_int(
                SettingsProperties.AUTO_ITEM_EXTRA_DELAY,
                backend_id=SettingsProperties.TTS_SERVICE,
                default_value=default_value)
        #  cSls._logger.debug(f'{SettingsProperties.AUTO_ITEM_EXTRA_DELAY}: {value}')
        return value

    @classmethod
    def set_auto_item_extra_delay(cls, value: int) -> None:
        # cls._logger.debug(f'setting {SettingsProperties.AUTO_ITEM_EXTRA_DELAY}: {
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
        # cls._logger.debug(f'{SettingsProperties.READER_ON}.'
        #                   f'{SettingsProperties.TTS_SERVICE}: {value}')
        return value

    @classmethod
    def set_reader_on(cls, value: bool) -> None:
        reader_on_val: IValidator
        reader_on_val = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                  SettingsProperties.READER_ON)
        # cls._logger.debug(f'{SettingsProperties.READER_ON}: {value}')
        reader_on_val.set_tts_value(value)
        return

    @classmethod
    def get_speak_list_count(cls, default_value: bool = None) -> bool:
        value: bool = cls.get_setting_bool(
                SettingsProperties.SPEAK_LIST_COUNT,
                engine_id=SettingsProperties.TTS_SERVICE,
                ignore_cache=False,
                default=default_value)

        # cls._logger.debug(f'{SettingsProperties.SPEAK_LIST_COUNT}: {value}')
        return value

    @classmethod
    def set_speak_list_count(cls, value: bool) -> None:
        # cls._logger.debug(f'setting {SettingsProperties.SPEAK_LIST_COUNT}: {value}')
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
        #  cls._logger.debug(f'uses_pipe.{service_id} = {use_pipe}')
        return use_pipe
    '''

    @classmethod
    def get_player_id(cls, engine_id: str = None) -> str:
        if engine_id is None:
            engine_id = super()._current_engine
        player_validator: IValidator
        player_validator = SettingsMap.get_validator(engine_id,
                                                     property_id=SettingsProperties.PLAYER)
        player_id: str = player_validator.get_tts_value()
        if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            cls._logger.debug_extra_verbose(f'player.{engine_id} = {player_id}')
        return player_id

    @classmethod
    def set_player(cls, value: str, engine_id: str = None) -> bool:
        """
        TODO: END HIGH LEVEL
        :param value:
        :param engine_id:
        :return:
        """
        # cls._logger.debug(f'setting {SettingsProperties.PLAYER}: {value}')
        return cls.set_setting_str(SettingsProperties.PLAYER, value,
                                   engine_id=engine_id)

    @classmethod
    def get_converter_id(cls, engine_id: str = None) -> str:
        value: str = cls.get_setting_str(SettingsProperties.CONVERTER,
                                         engine_id=engine_id,
                                         ignore_cache=False,
                                         default=None)
        # cls._logger.debug(f'converter.{engine_id} = {value}')
        return value

    @classmethod
    def set_converter(cls, value: str, backend_id: str = None) -> bool:
        """
        TODO: END HIGH LEVEL
        :param value:
        :param backend_id:
        :return:
        """
        # cls._logger.debug(f'setting {SettingsProperties.CONVERTER}: {value}')
        return cls.set_setting_str(SettingsProperties.CONVERTER, value,
                                   engine_id=backend_id)

    @classmethod
    def get_cache_base(cls) -> str:
        cache_base: str
        cache_base = cls.getSetting(SettingsProperties.CACHE_PATH,
                                    SettingsProperties.TTS_SERVICE,
                                    SettingsProperties.CACHE_PATH_DEFAULT)
        tmp: str = cache_base.strip()
        if tmp != cache_base:
            cls._logger.debug(f'cache_base changed old: {cache_base} new: {tmp}')
            cache_base = tmp
            cls.set_setting_str(SettingsProperties.CACHE_PATH,
                                cache_base,
                                SettingsProperties.TTS_SERVICE)
        return cache_base

    @classmethod
    def configuring_settings(cls):
        # cls._logger.debug('configuring_settings hardcoded to false')
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
