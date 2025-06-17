# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import subprocess

from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.engines.base_engine_settings import BaseEngineSettings
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Status, SettingsMap
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import AudioType, Backends
from common.system_queries import SystemQueries

module_logger = BasicLogger.get_logger(__name__)


class Pico2WaveSettings:
    # Only returns .mp3 files
    ID: str = Backends.PICO_TO_WAVE_ID
    engine_id = Backends.PICO_TO_WAVE_ID
    service_id: str = Services.PICO_TO_WAVE_ID
    displayName = 'Pico2Wave'

    #  supported_settings: Dict[str, str | int | bool] = settings
    initialized: bool = False
    _supported_input_formats: List[AudioType] = []
    _supported_output_formats: List[AudioType] = [AudioType.WAV]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    SoundCapabilities.add_service(service_id, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _logger: BasicLogger = None

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(*args, **kwargs)
        BaseEngineSettings(clz.service_id)
        if Pico2WaveSettings.initialized:
            return
        Pico2WaveSettings.initialized = True
        if clz._logger is None:
            clz._logger = module_logger
        Pico2WaveSettings.init_settings()
        SettingsMap.set_available(clz.service_id, Status.AVAILABLE)

    @classmethod
    def init_settings(cls):
        service_properties = {Constants.NAME: cls.displayName}
        SettingsMap.define_service_properties(ServiceType.ENGINE, cls.service_id,
                                              service_properties)

    @classmethod
    def isSupportedOnPlatform(cls):
        return SystemQueries.isLinux() or SystemQueries.isAndroid()

    @classmethod
    def isInstalled(cls):
        installed = False
        if cls.isSupportedOnPlatform():
            installed = cls.available()
        return installed

    @classmethod
    def available(cls):
        try:
            subprocess.call(['pico2wave', '--help'], universal_newlines=True,
                            stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        except (OSError, IOError):
            return False
        return True
