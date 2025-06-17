# coding=utf-8
from typing import ForwardRef
import xbmc

from backends.settings.service_types import MyType

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


class StatusType(MyType):
    """
    Uses a StrEnum but with an extra attribute for comparision
    """
    UNCHECKED = 'unchecked', 1  # Check not yet started
    CHECKING = 'checking', 2    # Check in progress
    OK = 'ok', 3                # Functional
    NOT_ON_PLATFORM = 'not_on_platform', 4  # Not an option on this platform
    NOT_FOUND = 'not_found', 5  # Command/service not found
    BROKEN = 'broken', 6        # Broken


class ServiceStatus:

    UNKNOWN_STATUS: ForwardRef('ServiceStatus') = None
    GOOD_STATUS: ForwardRef('ServiceStatus') = None
    NOT_AVAILABLE_STATUS: ForwardRef('ServiceStatus') = None

    @classmethod
    def init_class(cls) -> None:
        cls.UNKNOWN_STATUS = ServiceStatus()
        cls.UNKNOWN_STATUS.status = Status.UNKNOWN
        cls.UNKNOWN_STATUS.progress = Progress.START
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
        self._status_summary: StatusType = StatusType.UNCHECKED

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
    def status(self, status: Status) -> None:
        self._status = status

    @property
    def status_summary(self) -> StatusType:
        return self._status_summary

    @status_summary.setter
    def status_summary(self, value: StatusType) -> None:
        self._status_summary = value

    def is_usable(self) -> bool:
        usable: bool = self._progress == Progress.USABLE and self._status == Status.OK
        return usable

    def __str__(self) -> str:
        return f'{self._progress.value} {self._status.value}'


ServiceStatus.init_class()
