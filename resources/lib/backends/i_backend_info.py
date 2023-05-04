from common.__init__ import *
from backends.i_tts_backend_base import ITTSBackendBase


class IBackendInfo:
    _backendInfoImpl: 'IBackendInfo' = None

    @classmethod
    def getBackend(cls, backend_id: str = None) -> Callable | ITTSBackendBase | None:
        return cls._backendInfoImpl.getBackendByProvider(backend_id)

    @classmethod
    def getBackendFallback(cls) -> ITTSBackendBase | None:
        return cls._backendInfoImpl.getBackendFallback()

    @classmethod
    def isValidBackend(cls, backend_id: str):
        return cls._backendInfoImpl.isValidBackend(backend_id)

    @classmethod
    def getBackendByProvider(cls, backend_id: str = None) -> Callable | ITTSBackendBase | None:
        return cls._backendInfoImpl.getBackend(backend_id)

    @classmethod
    def setBackendInfo(cls, backend: 'IBackendInfo'):
        cls._backendInfoImpl = backend

    @classmethod
    def getBackendIds(cls) -> List[str]:
        pass

    @classmethod
    def isSettingSupported(cls, backend_id: str, setting_id: str) -> bool:
        return cls.getBackend(backend_id).isSettingSupported(setting_id)

    @classmethod
    def getSettingNames(cls) -> List[str] | None:
        """
        Gets a list of all of the setting names/keys that this backend uses

        :return:
        """
        return None

    @classmethod
    def get_setting_default(cls, backend_id: str, setting_id: str) -> Any:
        return cls.getBackend(backend_id).get_setting_default(setting_id)
