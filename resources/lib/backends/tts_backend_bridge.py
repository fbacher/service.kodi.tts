# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.i_backend import IBackend
from backends.i_tts_backend_base import ITTSBackendBase
from common import *


class TTSBackendBridge(ITTSBackendBase):
    _baseBackend: ITTSBackendBase = None

    @classmethod
    def getBackend(cls, backend_id: str) -> IBackend:
        return cls._baseBackend.getBackend(backend_id)

    @classmethod
    def setBaseBackend(cls, backend: ITTSBackendBase) -> None:
        cls._baseBackend = backend

    def setWavStreamMode(self, enable=True):
        raise Exception('Not Implemented')

    def scaleSpeed(self, value, limit):  # Target is between -20 and 20
        raise Exception('Not Implemented')

    def scalePitch(self, value, limit):  # Target is between -20 and 20
        raise Exception('Not Implemented')

    def scaleVolume(self, value, limit):
        raise Exception('Not Implemented')

    def scaleValue(self, value, constraints, limit):
        raise Exception('Not Implemented')

    def scale_db_to_percent(self, value, lower_bound=0, upper_bound=100):
        raise Exception('Not Implemented')

    def volumeUp(self) -> None:
        raise Exception('Not Implemented')

    def volumeDown(self) -> None:
        raise Exception('Not Implemented')

    def flagAsDead(self, reason=''):
        raise Exception('Not Implemented')

    def say(self, text, interrupt=False, preload_cache=False):
        raise Exception('Not Implemented')

    def sayList(self, texts, interrupt=False):
        raise Exception('Not Implemented')

    @classmethod
    def get_pitch_constraints(cls):
        raise Exception('Not Implemented')

    @classmethod
    def get_volume_constraints(cls):
        raise Exception('Not Implemented')

    @classmethod
    def get_speed_constraints(cls):
        raise Exception('Not Implemented')

    @classmethod
    def isSettingSupported(cls, setting: str) -> bool:
        raise Exception('Not Implemented')

    @classmethod
    def getSettingNames(cls) -> List[str]:
        raise Exception('Not Implemented')

    @classmethod
    def get_setting_default(cls, setting: str) -> Any | None:
        raise Exception('Not Implemented')

    @classmethod
    def settingList(cls, setting: str, *args):
        raise Exception('Not Implemented')

    @classmethod
    def setting(cls, setting):
        raise Exception('Not Implemented')

    @classmethod
    def getLanguage(cls) -> str:
        raise Exception('Not Implemented')

    @classmethod
    def getGender(cls) -> str:
        raise Exception('Not Implemented')

    @classmethod
    def getVoice(cls) -> str:
        raise Exception('Not Implemented')

    @classmethod
    def getSpeed(cls):
        raise Exception('Not Implemented')

    @classmethod
    def getPitch(cls) -> float:
        raise Exception('Not Implemented')

    @classmethod
    def getVolume(cls) -> float:
        raise Exception('Not Implemented')

    @classmethod
    def getSetting(cls, key: str, default: str | List[str] | List[bool] | list[
        float] | bool | int | float = None) -> Any | None:
        raise Exception('Not Implemented')

    @classmethod
    def setSetting(cls,
                   setting_id: str,
                   value: str | List[str] | List[bool] | List[float] | List[int] | None
                   ) -> bool:
        raise Exception('Not Implemented')

    @classmethod
    def get_backend_id(cls) -> str:
        raise Exception('Not Implemented')

    def isSpeaking(self) -> bool:
        raise Exception('Not Implemented')

    def getWavStream(self, text):
        raise Exception('Not Implemented')

    def update(self) -> None:
        raise Exception('Not Implemented')

    def stop(self) -> None:
        raise Exception('Not Implemented')

    def close(self):
        raise Exception('Not Implemented')

    def _update(self):
        raise Exception('Not Implemented')

    @classmethod
    def is_available_and_usable(cls) -> bool:
        return cls._baseBackend.is_available_and_usable()

    @classmethod
    def _available(cls):
        raise Exception('Not Implemented')

    @staticmethod
    def available() -> None:
        raise Exception('Not Implemented')
