# -*- coding: utf-8 -*-


from typing import *

from backends.settings.i_validators import IValidator, ValueType
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from common.constants import Constants
from common.logger import *
from common.settings_bridge import ISettings, SettingsBridge
from common.settings_low_level import SettingsLowLevel

from kutils.kodiaddon import Addon

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
    def get_addon() -> Addon:
        """

        :return:
        """
        if SettingsProperties._addon_singleton is None:
            try:
                SettingsProperties._addon_singleton = Addon(Constants.ADDON_ID)
            except Exception:
                pass

        return SettingsProperties._addon_singleton

    @staticmethod
    def on_settings_changed() -> None:
        """

        :return:
        """
        # Settings.load_settings()

    @classmethod
    def get_addons_md5(cls) -> str:
        addon_md5_val: IValidator = SettingsMap.get_validator(SettingsProperties.ADDONS_MD5,
                                                              '')
        addon_md5: str = addon_md5_val.getValue()
        cls._logger.debug(f'addons MD5: {SettingsProperties.ADDONS_MD5}')
        return addon_md5

    @classmethod
    def set_addons_md5(cls, addon_md5: str) -> None:
        addon_md5_val: IValidator = SettingsMap.get_validator(SettingsProperties.ADDONS_MD5,
                                                              '')
        addon_md5_val.setValue(addon_md5)
        cls._logger.debug(f'setting addons md5: {addon_md5}')
        return

    @classmethod
    def get_api_key(cls, engine_id: str = None) -> str:
        if engine_id is None:
            engine_id = cls._current_engine
        cls._logger.debug(f'getting api_key for engine_id: {engine_id}')
        engine_api_key_validator: IValidator
        engine_api_key_validator = SettingsMap.get_validator(engine_id,
                                                             property_id=SettingsProperties.API_KEY)
        api_key: str = engine_api_key_validator.getValue()
        return api_key

    @classmethod
    def set_api_key(cls, api_key: str, engine_id: str = None) -> None:
        cls._logger.debug(f'setting api_key: {api_key}')
        if engine_id is None:
            engine_id = cls._current_engine
        engine_api_key_validator: IValidator
        engine_api_key_validator = SettingsMap.get_validator(engine_id,
                                                             property_id=SettingsProperties.API_KEY)
        engine_api_key_validator.setValue(api_key)
        return

    @classmethod
    def get_engine_id(cls, bootstrap: bool = False) -> str:
        if bootstrap:
            return
        engine_id_validator = SettingsMap.get_validator(SettingsProperties.ENGINE, None)
        engine_id: str = None
        if engine_id_validator is None:
            engine_id = SettingsLowLevel.getSetting(SettingsProperties.ENGINE, None)
        else:
            engine_id: str = engine_id_validator.getValue()
        return engine_id

    @classmethod
    def set_engine_id(cls, engine_id: str) -> None:
        engine_id_validator = SettingsMap.get_validator(SettingsProperties.ENGINE, '')
        engine_id_validator.setValue(engine_id)
        return

    @classmethod
    def get_gender(cls, engine_id: str = None) -> str:
        if engine_id is None:
            engine_id = cls._current_engine
        cls._logger.debug(f'getting gender for engine_id: {engine_id}')
        engine_gender_validator: IValidator
        engine_gender_validator = SettingsMap.get_validator(engine_id,
                                                            property_id=SettingsProperties.GENDER)
        api_key: str = engine_gender_validator.getValue()
        return api_key

    @classmethod
    def set_gender(cls, gender: str,  engine_id: str = None) -> None:
        cls._logger.debug(f'setting gender: {gender}')
        if engine_id is None:
            engine_id = cls._current_engine
        engine_gender_validator: IValidator
        engine_gender_validator = SettingsMap.get_validator(engine_id,
                                                             property_id=SettingsProperties.GENDER)
        engine_gender_validator.setValue(gender)
        return

    @classmethod
    def get_language(cls, engine_id: str = None) -> str:
        if engine_id is None:
            engine_id = cls._current_engine
        cls._logger.debug(f'getting language for engine_id: {engine_id}')
        engine_language_validator: IValidator
        engine_language_validator = SettingsMap.get_validator(engine_id,
                                                            property_id=SettingsProperties.LANGUAGE)
        language: str = engine_language_validator.getValue()
        return language

    @classmethod
    def set_language(cls, language: str,  engine_id: str = None) -> None:
        cls._logger.debug(f'setting language: {language}')
        if engine_id is None:
            engine_id = cls._current_engine
        engine_language_validator: IValidator
        engine_language_validator = SettingsMap.get_validator(engine_id,
                                                            property_id=SettingsProperties.LANGUAGE)
        engine_language_validator.setValue(language)
        return

    @classmethod
    def get_auto_item_extra(cls, default_value: bool = None) -> bool:
        value: bool = cls.get_setting_bool(
                SettingsProperties.AUTO_ITEM_EXTRA, backend_id=None,
                default_value=default_value)
        cls._logger.debug(f'{SettingsProperties.AUTO_ITEM_EXTRA}: {value}')
        return value

    @classmethod
    def set_auto_item_extra(cls, value: bool) -> None:
        cls._logger.debug(f'setting {SettingsProperties.AUTO_ITEM_EXTRA}: {value}')
        cls.set_setting_bool(SettingsProperties.AUTO_ITEM_EXTRA, value)
        return

    @classmethod
    def get_auto_item_extra_delay(cls, default_value: int = None) -> int:
        value: int = cls.get_setting_int(
                SettingsProperties.AUTO_ITEM_EXTRA_DELAY, default_value)
        cls._logger.debug(f'{SettingsProperties.AUTO_ITEM_EXTRA_DELAY}: {value}')
        return value

    @classmethod
    def set_auto_item_extra_delay(cls, value: int) -> None:
        cls._logger.debug(f'setting {SettingsProperties.AUTO_ITEM_EXTRA_DELAY}: {value}')
        cls.set_setting_int(SettingsProperties.AUTO_ITEM_EXTRA_DELAY, value)
        return

    @classmethod
    def get_reader_on(cls, default_value: bool = None) -> bool:
        reader_on_val: IValidator
        reader_on_val = SettingsMap.get_validator(SettingsProperties.READER_ON,
                                                  '')
        value: bool = reader_on_val.getValue()
        cls._logger.debug(f'{SettingsProperties.READER_ON}: {value}')
        return value

    @classmethod
    def set_reader_on(cls, value: bool) -> None:
        reader_on_val: IValidator
        reader_on_val = SettingsMap.get_validator(SettingsProperties.READER_ON,
                                                  '')
        cls._logger.debug(f'{SettingsProperties.READER_ON}: {value}')
        reader_on_val.setValue(value)
        return

    @classmethod
    def get_speak_list_count(cls, default_value: bool = None) -> bool:
        value: bool = cls.get_setting_bool(
                SettingsProperties.SPEAK_LIST_COUNT, backend_id=None,
                default_value=default_value)

        cls._logger.debug(f'{SettingsProperties.SPEAK_LIST_COUNT}: {value}')
        return value

    @classmethod
    def set_speak_list_count(cls, value: bool) -> None:
        cls._logger.debug(f'setting {SettingsProperties.SPEAK_LIST_COUNT}: {value}')
        cls.set_setting_bool(SettingsProperties.SPEAK_LIST_COUNT, value)
        return

    def getSpeed(cls, service_id: str, value_type: ValueType=ValueType.VALUE) -> float:
        engine_speed_validator: IValidator
        engine_speed_validator = SettingsMap.get_validator(service_id,
                                                           property_id=SettingsProperties.SPEED)
        speed = engine_speed_validator.getValue(value_type)
        return speed

    def setSpeed(cls, value: int, service_id: str = None) -> float:
        if service_id is None:
            engine_id = cls._current_engine
        speed_validator: IValidator
        speed_validator = SettingsMap.get_validator(service_id,
                                                    property_id=SettingsProperties.SPEED)
        speed = speed_validator.getValue()
        return speed

    @classmethod
    def get_player(cls, default_value: str | None, backend_id: str = None) -> str:
        value: str = cls.get_setting_str(SettingsProperties.PLAYER, engine_id=backend_id,
                                              ignore_cache=False,
                                              default_value=default_value)
        cls._logger.debug(f'player.{backend_id} = {value}')
        return value

    @classmethod
    def set_player(cls, value: str, backend_id: str = None) -> bool:
        """
        TODO: END HIGH LEVEL
        :param value:
        :param backend_id:
        :return:
        """
        cls._logger.debug(f'setting {SettingsProperties.PLAYER}: {value}')
        return cls.set_setting_str(SettingsProperties.PLAYER, value, backend_id=backend_id)

    @classmethod
    def is_use_cache(cls, engine_id: str) -> bool:
        return cls.get_setting_bool(SettingsProperties.CACHE_SPEECH, engine_id)

    @classmethod
    def configuring_settings(cls):
        cls._logger.debug('configuring_settings hardcoded to false')
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
