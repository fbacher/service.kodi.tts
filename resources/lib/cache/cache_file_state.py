# coding=utf-8
try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum


class StrEnumWithPriority(StrEnum):
    """
        A StrEnum that also includes an ordinal value (for preference
        comparision)
    """
    def __new__(cls, value: str, ord_value: int):
        member = str.__new__(cls, value)
        member._value_ = value
        member.ordinal = ord_value
        #  MY_LOGGER.debug(f'ord_value: {ord_value}')
        return member

    # def __init__(self, ordinal: int) -> None:
    #     MY_LOGGER.debug(f'ordinal: {ordinal}')
    #     self.ordinal = ordinal

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal >= other.ordinal
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal > other.ordinal
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal <= other.ordinal
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.ordinal < other.ordinal
        return NotImplemented


class CacheFileState(StrEnumWithPriority):
    """
    Reports the state of a cached audio file. Can be one of:
      DOES_NOT_EXIST This indicates that there is no cached audio file nor is
         one in process of being created/downloaded
      CREATION_INCOMPLETE This indicates that creation/download has been initiated
         and in progress
      OK Indicates that a cache file by this name exists and appears valid
      BAD Indicates that a cache file by this name exists, but appears bad.
         This state does not last long since it a bad file is discarded soon
         after discovery.
    """
    UNKNOWN = 'unknown', -1
    DOES_NOT_EXIST = 'Does not exist', 0
    CREATION_INCOMPLETE = 'Creation incomplete', 1
    OK = 'ok', 2
    BAD = 'bad', 3
