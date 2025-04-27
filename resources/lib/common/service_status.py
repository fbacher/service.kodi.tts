# coding=utf-8
from typing import ForwardRef

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum


class Status(StrEnum):
    """

    """
    UNKNOWN = 'unknown'
    AVAILABLE = 'available'  # Appears fully functional
    #  BROKEN = 'broken'  # Command found, but not runnable
    OK = 'ok'
    FAILED = 'fail'
    FORCE = 'force'  # Used to force good status


class Progress(StrEnum):
    # The status is checked in the following order.
    # ServiceStatus uses this to remember the last check made

    # Initial state
    START = 'start'
    #  First thing checked is that this platform supports the service
    SUPPORTED = 'supported'
    # Next, check if service is installed (frequently no real check is made,
    # just advances to next step.
    INSTALLED = 'installed'
    # A service is AVAILABLE when a smoke test proves that it is runnable
    AVAILABLE = 'available'
    # A service is USABLE when it is available and is able to be used with at
    # least one valid configuration. (Ex: an engine has any required players,
    # transcoders, etc. needed to create a useful TTS configuration.
    USABLE = 'usable'
    # Force registration for settings (validators)
    FORCE = 'force'


class ServiceStatus:

    GOOD_STATUS: ForwardRef('ServiceStatus') = None
    NOT_AVAILABLE_STATUS: ForwardRef('ServiceStatus') = None

    @classmethod
    def init_class(cls) -> None:
        cls.GOOD_STATUS = ServiceStatus()
        cls.GOOD_STATUS.status = Status.OK
        cls.GOOD_STATUS.progress = Progress.USABLE
        cls.NOT_AVAILABLE_STATUS = ServiceStatus()
        cls.NOT_AVAILABLE_STATUS.progress = Progress.AVAILABLE
        cls.NOT_AVAILABLE_STATUS.status = Status.FAILED

    def __init__(self, status: Status = Status.OK) -> None:
        if status == Status.FORCE:
            self._progress = Progress.FORCE
        else:
            self._progress: Progress = Progress.START
        self._status: Status = status

    @property
    def progress(self) -> Progress:
        return self._progress

    @progress.setter
    def progress(self, progress: Progress) -> None:
        self._progress = progress

    @property
    def status(self) -> Status:
        return self._status

    @status.setter
    def status(self, status:Status) -> None:
        self._status = status

    def is_usable(self) -> bool:
        return self._progress == Progress.USABLE and self._status == Status.OK

    def __str__(self) -> str:
        return f'{self._progress.value} {self._status.value}'


ServiceStatus.init_class()
