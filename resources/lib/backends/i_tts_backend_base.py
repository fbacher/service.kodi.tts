from __future__ import annotations  # For union operator |

from common import *

from backends.i_backend import IBackend
from backends.settings.constraints import Constraints
from common.phrases import PhraseList
from windowNavigation.choice import Choice


class ITTSBackendBase(IBackend):
    """The interface class for all speech engine backends"""

    _baseBackend: IBackend = None

    canStreamWav: bool = False
    _backend_id: str = 'ITTSBackendBase'
    displayName: str = 'ITTSBackendBase'
    inWavStreamMode = False
    interval = 100
    broken = False
    # Min, Default, Max, Integer_Only (no float)
    # speedConstraints: Constraints = Constraints(0, 0, 0, True)
    # pitchConstraints: Constraints = (0, 0, 0, True)

    # Volume constraints imposed by the api being called

    # volumeConstraints = (-12, 0, 12, True)

    # Volume scale as presented to the user

    volumeExternalEndpoints = (-12, 12)
    volumeStep = 1
    volumeSuffix = 'dB'
    speedInt = True
    # _loadedSettings = {}
    dead = False  # Backend should flag this true if it's no longer usable
    deadReason = ''  # Backend should set this reason when marking itself dead
    _closed = False
    currentBackend = None
    #  currentSettings = []
    settings = {}
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super(ITTSBackendBase, self).__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__

    def re_init(self):
        raise Exception('Not Implemented')

    def init(self):
        raise Exception('Not Implemented')

    @property
    def backend_id(self) -> str:
        clz = type(self)
        return clz._backend_id

    @classmethod
    def setBaseBackend(cls, backend: IBackend) -> None:
        cls._baseBackend = backend

    def setWavStreamMode(self, enable=True):
        raise Exception('Not Implemented')

    @classmethod
    def scaleSpeed(cls, value, limit):  # Target is between -20 and 20
        raise Exception('Not Implemented')

    @classmethod
    def scalePitch(cls, value, limit):  # Target is between -20 and 20
        raise Exception('Not Implemented')

    @classmethod
    def scaleVolume(cls, value, limit):
        raise Exception('Not Implemented')

    @classmethod
    def scaleValue(cls, value, constraints, limit):
        raise Exception('Not Implemented')

    def scale_db_to_percent(self, value, lower_bound=0, upper_bound=100):
        raise Exception('Not Implemented')

    def volumeUp(self) -> None:
        raise Exception('Not Implemented')

    def volumeDown(self) -> None:
        raise Exception('Not Implemented')

    def flagAsDead(self, reason=''):
        raise Exception('Not Implemented')

    def say(self, phrases: PhraseList):
        raise Exception('Not Implemented')

    def isSpeaking(self) -> bool:
        raise NotImplementedError()

    @classmethod
    def get_constraints(cls, setting: str) -> Constraints | None:
        raise Exception('Not Implemented')

    @classmethod
    def get_pitch_constraints(cls) -> Constraints:
        raise Exception('Not Implemented')

    @classmethod
    def get_volume_constraints(cls) -> Constraints:
        raise Exception('Not Implemented')

    @classmethod
    def get_speed_constraints(cls) -> Constraints:
        raise Exception('Not Implemented')

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        raise Exception('Not Implemented')

    @classmethod
    def is_available_and_usable(cls) -> bool:
        raise Exception('Not Implemented')

    @staticmethod
    def isSupportedOnPlatform() -> bool:
        """
        This O/S supports this engine/backend

        :return:
        """
        raise Exception('Not Implemented')

    @classmethod
    def getSettingNames(cls):
        raise Exception('Not Implemented')

    @classmethod
    def get_setting_default(cls, setting):
        raise Exception('Not Implemented')

    @classmethod
    def getBackendConstraints(cls, setting_id: str):
        raise Exception('Not Implemented')

    @classmethod
    def settingList(cls, setting, *args) -> List[Choice]:
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
    def get_backend_id(cls) -> str:
        raise Exception('Not Implemented')

    def is_speaking(self) -> bool:
        raise Exception('Not Implemented')

    def getWavStream(self, text):
        raise Exception('Not Implemented')

    def notify(self, msg) -> None:
        raise Exception('Not Implemented')

    def update(self):
        raise Exception('Not Implemented')

    def stop(self) -> None:
        raise Exception('Not Implemented')

    def _close(self):
        raise Exception('Not Implemented')

    def close(self) -> None:
        raise Exception('Not Implemented')

    def _update(self):
        raise Exception('Not Implemented')

    @classmethod
    def _available(cls):
        raise Exception('Not Implemented')

    @staticmethod
    def available() -> bool:
        raise Exception('Not Implemented')
