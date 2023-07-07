import os
import subprocess

from backends.audio.sound_capabilties import SoundCapabilities
from backends.engines.base_engine_settings import BaseEngineSettings
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Reason, SettingsMap
from common.logger import BasicLogger
from common.setting_constants import Backends
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class Pico2WaveSettings:
    # Only returns .mp3 files
    ID: str = Backends.PICO_TO_WAVE_ID
    backend_id = Backends.PICO_TO_WAVE_ID
    service_ID: str = Services.PICO_TO_WAVE_ID
    displayName = 'Pico2Wave'

    #  supported_settings: Dict[str, str | int | bool] = settings
    initialized: bool = False
    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _logger: BasicLogger = None

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(*args, **kwargs)
        BaseEngineSettings(clz.service_ID)
        if Pico2WaveSettings.initialized:
            return
        Pico2WaveSettings.initialized = True
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        Pico2WaveSettings.init_settings()
        SettingsMap.set_is_available(clz.service_ID, Reason.AVAILABLE)

    @classmethod
    def init_settings(cls):
        pass

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
            subprocess.call(['pico2wave', '--help'],  universal_newlines=True,
                            stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        except (OSError, IOError):
            return False
        return True
