# coding=utf-8
from __future__ import annotations  # For union operator |
import common

from backends.i_backend_info import IBackendInfo
from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.constraints import Constraints
from backends.settings.service_types import ServiceID
from common import *
from common.base_services import BaseServices
from common.logger import BasicLogger

module_logger = BasicLogger.get_logger(__name__)


class BackendInfoBridge(IBackendInfo):
    _backendInfoImpl: IBackendInfo = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__

    @classmethod
    def getBackend(cls, engine_id: ServiceID = None) -> ITTSBackendBase:
        return BaseServices.get_service(engine_id)

    @classmethod
    def getBackendIds(cls) -> List[str]:
        return cls._backendInfoImpl.getBackendIds()

    @classmethod
    def getBackendFallback(cls) -> ITTSBackendBase | None:
        return cls._backendInfoImpl.getBackendFallback()

    @classmethod
    def setBackendInfo(cls, backend: IBackendInfo) -> None:
        cls._backendInfoImpl = backend

    @classmethod
    def isValidBackend(cls, engine_id: str):
        return cls._backendInfoImpl.isValidBackend(engine_id)

    @classmethod
    def isBackendSettingSupported(cls, engine_id: str, setting_id: str) -> bool:
        return cls.getBackend(engine_id).isSettingSupported(setting_id)

    @classmethod
    def getBackendConstraints(cls, engine_id: str, setting_id: str) -> Constraints:
        return cls.getBackend(engine_id).getConstraints(setting_id)

    @classmethod
    def negotiate_engine_config(cls, engine_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:

        try:
            engine: BackendInfoBridge = cls.getBackend(engine_id)
            return engine.negotiate_engine_config(engine_id, player_volume_adjustable,
                                                  player_speed_adjustable,
                                                  player_pitch_adjustable)
        except Exception:
            module_logger.exception('')

    '''
    @classmethod
    def get_backend_setting_default(cls, setting_id: str, setting_id: str) -> Any:
        return cls.getBackend(setting_id).get_setting_default(setting_id)
    '''
