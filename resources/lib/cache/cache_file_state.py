# coding=utf-8
from enum import Enum, IntEnum


class CacheFileState(IntEnum):
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
    UNKNOWN = -1
    DOES_NOT_EXIST = 0
    CREATION_INCOMPLETE = 1
    OK = 2
    BAD = 3
