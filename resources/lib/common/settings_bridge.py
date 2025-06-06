# coding=utf-8
from __future__ import annotations  # For union operator |

from common import *


class ISettings:
    BACKEND_DEFAULT: Final[str] = 'auto'

    @classmethod
    def get_engine_id(cls) -> str | None:
        return None

    @classmethod
    def getSetting(cls, setting_id: str, engine_id: str | None,
                   default_value: Any | None = None) -> Any:
        return None

    @classmethod
    def setSetting(cls, setting_id: str,
                   value: str | int | float | bool | List[str] | List[bool] | List[float],
                   engine_id: str) -> None:
        return None


class SettingsBridge(ISettings):

    _settings_ref: Type[ISettings] = None

    @classmethod
    def set_settings_ref(cls, settings_ref: Type[ISettings]):
        cls._settings_ref = settings_ref

    @classmethod
    def get_engine_id(cls) -> str:
        return cls._settings_ref.get_engine_id()

    @classmethod
    def getSetting(cls, setting_id: str, engine_id: str | None,
                   default_value: Any | None = None) -> Any:
        return cls._settings_ref.getSetting(setting_id, engine_id, default_value)

    @classmethod
    def setSetting(cls, setting_id: str, value: str | int | float | bool | List[str] |
                                                List[bool] | List[float],
                   engine_id: str | None = None) -> None:
        cls._settings_ref.setSetting(setting_id, value, engine_id)
