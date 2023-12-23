import os
import subprocess

from backends.audio.sound_capabilties import SoundCapabilities
from backends.engines.base_engine_settings import BaseEngineSettings
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Reason, SettingsMap
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Backends
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class FestivalSettings(BaseServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.FESTIVAL_ID
    backend_id = Backends.FESTIVAL_ID
    service_ID: str = Services.FESTIVAL_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    displayName = 'festival'

    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _logger: BasicLogger = None

    # Every setting from settings.xml must be listed here
    # SettingName, default value
    initialized: bool = False

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(clz.service_ID, *args, **kwargs)
        BaseEngineSettings(clz.service_ID)
        if clz.initialized:
            return
        clz.initialized = True
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.init_settings()
        installed: bool = clz.isInstalled()
        SettingsMap.set_is_available(clz.service_ID, Reason.AVAILABLE)

    @classmethod
    def init_settings(cls):
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings

        service_properties = {Constants.NAME: cls.displayName}
        SettingsMap.define_service(ServiceType.ENGINE, cls.service_ID,
                                   service_properties)

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        return SettingsMap.is_valid_property(cls.service_ID, setting)

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
                            stderr=subprocess.STDOUT, universal_newlines=True)
        except (OSError, IOError):
            return False
        return True
