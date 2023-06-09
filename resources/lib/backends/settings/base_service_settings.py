# coding=utf-8
from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.service_types import Services
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, IntValidator, StringValidator)
from common.base_services import BaseServices
from common.setting_constants import Backends
from common.settings_low_level import SettingsProperties
from common.typing import *


class BaseServiceSettings:
    backend_id = 'auto'
    service_ID: str = Services.AUTO_ENGINE_ID
    displayName: str = 'Auto'
    pauseInsert = '...'
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False

    initialized_settings: bool = False

    # _supported_input_formats: List[str] = []
    # _supported_output_formats: List[str] = []
    # _provides_services: List[ServiceType] = [ServiceType.ENGINE]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if BaseServiceSettings.initialized_settings:
            return

        if not BaseServiceSettings.initialized_settings:
            BaseServiceSettings.initialized_settings = True

        engine_id_validator = StringValidator(SettingsProperties.ENGINE,
                                              '',
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way too big
                                              max_length=32,
                                              default_value=Backends.ESPEAK_ID)
        SettingsMap.define_setting(SettingsProperties.ENGINE, '',
                                   engine_id_validator)

        addon_md5_validator = StringValidator(SettingsProperties.ADDONS_MD5, '',
                                              allowed_values=[], min_length=32,
                                              max_length=32, default_value='')
        SettingsMap.define_setting(SettingsProperties.ADDONS_MD5, None,
                                   addon_md5_validator)

        auto_item_extra_validator: BoolValidator
        auto_item_extra_validator = BoolValidator(SettingsProperties.AUTO_ITEM_EXTRA, '',
                                                  default=False)
        SettingsMap.define_setting(SettingsProperties.AUTO_ITEM_EXTRA, '',
                                   auto_item_extra_validator)
        auto_item_extra_delay_validator: IntValidator
        auto_item_extra_delay_validator = IntValidator(
                SettingsProperties.AUTO_ITEM_EXTRA_DELAY, '',
                min_value=0, max_value=3, default_value=0,
                step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(SettingsProperties.AUTO_ITEM_EXTRA_DELAY, '',
                                   auto_item_extra_delay_validator)
        background_progress_validator: IntValidator
        background_progress_validator = IntValidator(
                SettingsProperties.BACKGROUND_PROGRESS_INTERVAL, '',
                min_value=0, max_value=60, default_value=5,
                step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(SettingsProperties.BACKGROUND_PROGRESS_INTERVAL,
                                   '',
                                   background_progress_validator)
        disable_broken_services: BoolValidator
        disable_broken_services = BoolValidator(
                SettingsProperties.DISABLE_BROKEN_SERVICES, '',
                default=True)
        SettingsMap.define_setting(SettingsProperties.DISABLE_BROKEN_SERVICES, '',
                                   disable_broken_services)
        speak_background_progress: BoolValidator
        speak_background_progress = BoolValidator(
                SettingsProperties.SPEAK_BACKGROUND_PROGRESS, '',
                default=False)
        SettingsMap.define_setting(SettingsProperties.SPEAK_BACKGROUND_PROGRESS, '',
                                   speak_background_progress)
        speak_during_media: BoolValidator
        speak_during_media = BoolValidator(
                SettingsProperties.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA, '',
                default=False)
        SettingsMap.define_setting(SettingsProperties.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA,
                                   '', speak_during_media)
        cache_path_val: StringValidator
        cache_path_val = StringValidator(SettingsProperties.CACHE_PATH, '',
                                         allowed_values=[],
                                         min_length=1,
                                         max_length=1024,
                                         default_value=SettingsProperties.CACHE_PATH_DEFAULT)
        SettingsMap.define_setting(SettingsProperties.CACHE_PATH,'',
                                   cache_path_val)

        cache_expiration_val: IntValidator
        cache_expiration_val = IntValidator(SettingsProperties.CACHE_EXPIRATION_DAYS, '',
                                            min_value=0, max_value=3654,
                                            default_value=365,
                                            step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(SettingsProperties.CACHE_EXPIRATION_DAYS, '',
                                   cache_expiration_val)
        override_poll_interval_val: BoolValidator
        override_poll_interval_val = BoolValidator(
                SettingsProperties.OVERRIDE_POLL_INTERVAL, '',
                default=False)
        SettingsMap.define_setting(SettingsProperties.OVERRIDE_POLL_INTERVAL, '',
                                   override_poll_interval_val)
        # Poll interval in milliseconds
        poll_interval_val: IntValidator
        poll_interval_val = IntValidator(SettingsProperties.POLL_INTERVAL, '',
                                         min_value=0, max_value=1000, default_value=100,
                                         step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(SettingsProperties.POLL_INTERVAL, '',
                                   poll_interval_val)

        debug_log_level_val: IntValidator
        debug_log_level_val = IntValidator(SettingsProperties.DEBUG_LOG_LEVEL, '',
                                           min_value=0, max_value=5, default_value=4,
                                           # INFO
                                           step=1, scale_internal_to_external=1)
        SettingsMap.define_setting(SettingsProperties.DEBUG_LOG_LEVEL, '',
                                   debug_log_level_val)

        reader_on_val: BoolValidator
        reader_on_val = BoolValidator(SettingsProperties.READER_ON, '',
                                      default=True)
        SettingsMap.define_setting(SettingsProperties.READER_ON, '',
                                   reader_on_val)
        speak_list_count_val: BoolValidator
        speak_list_count_val = BoolValidator(SettingsProperties.SPEAK_LIST_COUNT, '',
                                             default=True)
        SettingsMap.define_setting(SettingsProperties.SPEAK_LIST_COUNT, '',
                                   speak_list_count_val)

        version_val: StringValidator
        version_val = StringValidator(SettingsProperties.VERSION, '',
                                      allowed_values=[],
                                      min_length=5,
                                      max_length=20,
                                      default_value=None)
        SettingsMap.define_setting(SettingsProperties.VERSION, '',
                                   version_val)

        use_tempfs_val: BoolValidator
        use_tempfs_val = BoolValidator(SettingsProperties.USE_TEMPFS, '',
                                       default=True)
        SettingsMap.define_setting(SettingsProperties.USE_TEMPFS, '',
                                   use_tempfs_val)


        '''
        CONVERTER?,
        GENDER_VISIBLE,
        GUI,
        SPEECH_DISPATCHER,
        OUTPUT_VIA,
        OUTPUT_VISIBLE,
        SETTINGS_BEING_CONFIGURED,
        SETTINGS_DIGEST,
        SPEAK_VIA_KODI,
        TTSD_HOST,
        TTSD_PORT,
        VOICE_VISIBLE,
        VOLUME_VISIBLE
        '''

    @classmethod
    def register(cls, what: Type[ITTSBackendBase]) -> None:
        BaseServices.register(what)
