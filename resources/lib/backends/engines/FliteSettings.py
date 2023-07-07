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


class FliteSettings:
    # Only returns .mp3 files
    ID: str = Backends.FLITE_ID
    backend_id = Backends.FLITE_ID
    service_ID: str = Services.FLITE_ID
    displayName = 'flite'

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
        if FliteSettings.initialized:
            return
        FliteSettings.initialized = True
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        FliteSettings.init_settings()
        SettingsMap.set_is_available(clz.service_ID, Reason.AVAILABLE)

    @classmethod
    def init_settings(cls):
        pass

    @classmethod
    def isSupportedOnPlatform(cls) -> bool:
        return (SystemQueries.isLinux())

    @classmethod
    def isInstalled(cls) -> bool:
        installed: bool = False
        if cls.isSupportedOnPlatform():
            installed = True
        return installed

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        return SettingsMap.is_valid_property(cls.service_ID, setting)

    @classmethod
    def available(cls):
        try:
            subprocess.call(['flite', '--help'], stdout=(open(os.path.devnull, 'w')),
                            universal_newlines=True, stderr=subprocess.STDOUT)
        except (OSError, IOError):
            return SystemQueries.isATV2() and SystemQueries.commandIsAvailable('flite')
        return True
