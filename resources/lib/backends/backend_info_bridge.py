from backends.i_backend_info import IBackendInfo
from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.constraints import Constraints
from common.__init__ import *
from common.exceptions import NotReadyException
from common.base_services import BaseServices


class BackendInfoBridge(IBackendInfo):
    _backendInfoImpl: IBackendInfo = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__

    @classmethod
    def getBackend(cls, backend_id: str = None) -> BaseServices:
        return BaseServices.getService(backend_id)

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
    def isValidBackend(cls, backend_id: str):
        return cls._backendInfoImpl.isValidBackend(backend_id)

    @classmethod
    def isBackendSettingSupported(cls, backend_id: str, setting_id: str) -> bool:
        return cls.getBackend(backend_id).isSettingSupported(setting_id)

    '''
    @classmethod
    def getBackendSettingNames(cls, backend_id: str) -> List[str]:
        """
        Gets a list of all of the setting names/keys that this backend uses

        :return:
        """
        return cls.getBackend(backend_id).getSettingNames()
    '''

    @classmethod
    def getBackendConstraints(cls, backend_id: str, setting_id: str) -> Constraints:
        return cls.getBackend(backend_id).getConstraints(setting_id)

    @classmethod
    def negotiate_engine_config(cls, backend_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:

        engine: BackendInfoBridge = cls.getBackend(backend_id)
        return engine.negotiate_engine_config(backend_id, player_volume_adjustable,
                                              player_speed_adjustable,
                                              player_pitch_adjustable)

    @classmethod
    def get_backend_setting_default(cls, backend_id: str, setting_id: str) -> Any:
        return cls.getBackend(backend_id).get_setting_default(setting_id)
