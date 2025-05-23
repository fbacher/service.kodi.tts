# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess

from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import BaseEngineSettings
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Status, SettingsMap
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import AudioType, Backends
from common.system_queries import SystemQueries

module_logger = BasicLogger.get_logger(__name__)


class FestivalSettings(BaseServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.FESTIVAL_ID
    engine_id = Backends.FESTIVAL_ID
    service_id: str = Services.FESTIVAL_ID
    service_type: ServiceType = ServiceType.ENGINE_SETTINGS
    displayName = 'festival'

    _supported_input_formats: List[AudioType] = []
    _supported_output_formats: List[AudioType] = [AudioType.WAV]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    SoundCapabilities.add_service(service_id, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _logger: BasicLogger = None

    # Every setting from settings.xml must be listed here
    # SettingName, default value
    initialized: bool = False

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(clz.service_id, *args, **kwargs)
        BaseEngineSettings(clz.service_id)
        if clz.initialized:
            return
        clz.initialized = True
        if clz._logger is None:
            clz._logger = module_logger
        self.init_settings()
        installed: bool = clz.isInstalled()
        SettingsMap.set_available(clz.service_id, Status.AVAILABLE)

    @classmethod
    def init_settings(cls):
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        service_properties = {Constants.NAME: cls.displayName}
        SettingsMap.define_service_properties(ServiceType.ENGINE, cls.service_id,
                                              service_properties)

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        return SettingsMap.is_valid_setting(cls.service_id, setting)

    @classmethod
    def isSupportedOnPlatform(cls):
        return SystemQueries.isLinux()

    @classmethod
    def isInstalled(cls):
        installed = False
        if cls.isSupportedOnPlatform():
            installed = True
        return installed

    @classmethod
    def available(cls):
        try:
            subprocess.call(['festival', '--help'], stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT,
                            universal_newlines=True, encoding='utf-8')
        except (OSError, IOError):
            return False
        return True
