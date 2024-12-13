from __future__ import annotations  # For union operator |

from backends.i_tts_backend_base import ITTSBackendBase
from common import *


class IBackendInfo:
    _backendInfoImpl: 'IBackendInfo' = None

    @classmethod
    def getBackend(cls, engine_id: str = None) -> Callable | ITTSBackendBase | None:
        return cls._backendInfoImpl.getBackendByProvider(engine_id)

    @classmethod
    def getBackendFallback(cls) -> ITTSBackendBase | None:
        return cls._backendInfoImpl.getBackendFallback()

    @classmethod
    def isValidBackend(cls, engine_id: str):
        return cls._backendInfoImpl.isValidBackend(engine_id)

    @classmethod
    def getBackendByProvider(cls,
                             engine_id: str = None) -> Callable | ITTSBackendBase | None:
        return cls._backendInfoImpl.getBackend(engine_id)

    @classmethod
    def setBackendInfo(cls, backend: 'IBackendInfo'):
        cls._backendInfoImpl = backend

    @classmethod
    def getBackendIds(cls) -> List[str]:
        pass

    @classmethod
    def isSettingSupported(cls, engine_id: str, setting_id: str) -> bool:
        return cls.getBackend(engine_id).isSettingSupported(setting_id)

    @classmethod
    def getSettingNames(cls) -> List[str] | None:
        """
        Gets a list of all of the setting names/keys that this backend uses

        :return:
        """
        return None

    @classmethod
    def get_setting_default(cls, engine_id: str, setting_id: str) -> Any:
        return cls.getBackend(engine_id).get_setting_default(setting_id)

    @classmethod
    def negotiate_engine_config(cls, engine_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        pass
