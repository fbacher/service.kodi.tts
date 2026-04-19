# coding=utf-8
from common.logger import *
import xbmc

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)

MY_LOGGER.error("In cache_file_state")
xbmc.log("In cache_file_state",  xbmc.LOGDEBUG)


class StrEnumWithPriority(StrEnum):
    """
        A StrEnum that also includes an ordinal value (for preference
        comparision)
    """
    def __new__(cls, value: str, ord_value: int):
        member = str.__new__(cls, value)
        member._value_ = value
        member.ordinal = ord_value
        # MY_LOGGER.error(f'ord_value: {ord_value}')
        return member

    # def __init__(self, ordinal: int) -> None:
    #     MY_LOGGER.(f'ordinal: {ordinal}')
    #     self.ordinal = ordinal

    def __eq__(self, other):
        # raise NotImplementedError
        if self.__class__ is other.__class__:
            return self.ordinal == other.ordinal
        raise NotImplementedError

    def __ne__(self, other):
        # raise NotImplementedError
        if self.__class__ is other.__class__:
            return self.ordinal != other.ordinal
        raise NotImplementedError

    def __ge__(self, other):
        # raise NotImplementedError
        if self.__class__ is other.__class__:
            return self.ordinal >= other.ordinal
        raise NotImplementedError

    def __gt__(self, other):
        # MY_LOGGER.error('In __gt__')
        # raise NotImplementedError
        if self.__class__ is other.__class__:
            return self.ordinal > other.ordinal
        raise NotImplementedError

    def __le__(self, other):
        # raise NotImplementedError
        if self.__class__ is other.__class__:
            return self.ordinal <= other.ordinal
        raise NotImplementedError

    def __lt__(self, other) -> bool:
        if self.__class__ is other.__class__:
            # raise NotImplementedError
            # MY_LOGGER.error(f'val: {self._value_} ordinal: {self.ordinal}')
            # MY_LOGGER.error(f'OTHER val: {other._value_} ordinal: {other.ordinal}')
            # MY_LOGGER.error(f'val < other: {self.ordinal < other.ordinal}')
            return self.ordinal < other.ordinal
        raise NotImplementedError


class CacheFileState(StrEnumWithPriority):
    """
    Reports the state of a cached audio file. Can be one of:
      DOES_NOT_EXIST This indicates that there is no cached audio file nor is
         one in process of being created/downloaded
      CREATION_INCOMPLETE This indicates that creation/download has been initiated
         and in progress
      OK Indicates that a cache file by this name exists and appears valid
      BAD Indicates that a cache file by this name exists, but appears bad.
         This state does not last long since a bad file is discarded soon
         after discovery.
    """
    UNKNOWN = 'unknown', -1
    DOES_NOT_EXIST = 'Does not exist', 0
    CREATION_INCOMPLETE = 'Creation incomplete', 1
    OK = 'ok', 2
    BAD = 'bad', 3
