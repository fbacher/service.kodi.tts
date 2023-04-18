from common.__init__ import *
from backends.i_tts_backend_base import ITTSBackendBase
from backends.i_backend import IBackend


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

    def volumeUp(self):
        raise Exception('Not Implemented')

    def volumeDown(self):
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
    def isSettingSupported(cls, setting):
        raise Exception('Not Implemented')

    @classmethod
    def getSettingNames(cls):
        raise Exception('Not Implemented')

    @classmethod
    def get_setting_default(cls, setting):
        raise Exception('Not Implemented')

    @classmethod
    def settingList(cls, setting, *args):
        raise Exception('Not Implemented')

    @classmethod
    def setting(cls, setting):
        raise Exception('Not Implemented')

    @classmethod
    def getLanguage(cls):
        raise Exception('Not Implemented')

    @classmethod
    def getGender(cls):
        raise Exception('Not Implemented')

    @classmethod
    def getVoice(cls):
        raise Exception('Not Implemented')

    @classmethod
    def getSpeed(cls):
        raise Exception('Not Implemented')

    @classmethod
    def getPitch(cls):
        raise Exception('Not Implemented')

    @classmethod
    def getVolume(cls):
        raise Exception('Not Implemented')

    @classmethod
    def getSetting(cls, key, default=None):
        raise Exception('Not Implemented')

    @classmethod
    def setSetting(cls,
                   setting_id: str,
                   value: Union[None, str, List, bool, int, float]
                   ) -> bool:
        raise Exception('Not Implemented')

    @classmethod
    def get_backend_id(cls):
        raise Exception('Not Implemented')

    def isSpeaking(self):
        raise Exception('Not Implemented')

    def getWavStream(self, text):
        raise Exception('Not Implemented')

    def update(self):
        raise Exception('Not Implemented')

    def stop(self):
        raise Exception('Not Implemented')

    def close(self):
        raise Exception('Not Implemented')

    def _update(self):
        raise Exception('Not Implemented')

    @classmethod
    def is_available_and_usable(cls):
        return cls._baseBackend.is_available_and_usable()

    @classmethod
    def _available(cls):
        raise Exception('Not Implemented')

    @staticmethod
    def available():
        raise Exception('Not Implemented')
