
from .__init__ import *


class ISettings:
    BACKEND_DEFAULT: Final[str] = 'auto'

    @classmethod
    def get_backend_id(cls) -> str | None:
        return None


class SettingsBridge(ISettings):

    _settings_ref: Type[ISettings] = None

    @classmethod
    def set_settings_ref(cls, settings_ref: Type[ISettings]):
        cls._settings_ref = settings_ref

    @classmethod
    def get_backend_id(cls) -> str:
        return cls._settings_ref.get_backend_id()
