# -*- coding: utf-8 -*-

"""
Created on Feb 10, 2019

@author: fbacher
"""

import datetime
import random
from enum import auto, Enum

import xbmc

import simplejson as json
from common.logger import *
from common.monitor import Monitor
from common.typing import *
from .movie_constants import MovieType

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class JsonReturnCode(Enum):
    OK = auto()
    RETRY = auto()
    FAILURE_NO_RETRY = auto()
    UNKNOWN_ERROR = auto()


class Result:

    def __init__(self, rc: JsonReturnCode, status: int = None, msg: str = None,
                 data: MovieType = None) -> None:
        self._rc: JsonReturnCode = rc
        self._status: int = status
        self._msg: str = msg
        self._data: MovieType = data

    def get_api_success(self) -> str:
        api_success: str = None
        if self._data is not None and isinstance(self._data, dict):
            api_success = self._data.get('success')

        return api_success

    def get_api_status_code(self) -> str:
        api_status_code = None
        if self._data is not None and isinstance(self._data, dict):
            api_status_code = self._data.get('status_code')

        return api_status_code

    def get_api_status_msg(self) -> str:
        api_status_msg: str = None
        if self._data is not None and isinstance(self._data, dict):
            api_status_msg = self._data.get('status_message')

        return api_status_msg

    def get_rc(self) -> JsonReturnCode:
        return self._rc

    def set_rc(self, rc: JsonReturnCode) -> None:
        self._rc = rc

    def get_status(self) -> int:
        return self._status

    def set_status(self, status: int) -> None:
        self._status = status

    def get_msg(self) -> str:
        return self._msg

    def set_msg(self, msg: str) -> None:
        self._msg = msg

    def get_data(self) -> MovieType:
        return self._data

    def set_data(self, data: MovieType) -> None:
        self._data = data


class JsonUtilsBasic:
    RandomGenerator = random.Random()
    RandomGenerator.seed()

    _exit_requested = False
    """
        Tunes and TMDB each have rate limiting:
            TMDB is limited over a period of 10 seconds
            iTunes is limited to 20 requests/minute and 200
            results per search.
            
            For iTunes see:
         https://affiliate.itunes.apple.com/resources/documentation/itunes-store-web
         -service-search-api/#overview
             All iTunes results are JSON UTF-8

        In order to track the rate of requests over a minute, we have to
        track the timestamp of each request made in the last minute.
    
        Keep in mind for both TMDB and iTunes, that other plugins may be
        making requests
    """

    # In 2019 TMDb turned off rate limiting. Bumped limits up a bit

    TMDB_NAME = 'tmdb'
    TMDB_REQUEST_INDEX = 0
    TMDB_WINDOW_TIME_PERIOD = datetime.timedelta(seconds=100)
    TMDB_WINDOW_MAX_REQUESTS = 120

    ITUNES_NAME = 'iTunes'
    ITUNES_REQUEST_INDEX = 1
    ITUNES_WINDOW_TIME_PERIOD = datetime.timedelta(minutes=1)
    ITUNES_WINDOW_MAX_REQUESTS = 20

    ROTTEN_TOMATOES_NAME = 'Rotten Tomatoes'
    ROTTEN_TOMATOES_REQUEST_INDEX = 2

    # Values not specified in available docs. Not using Rotten Tomatoes
    # at this time

    ROTTEN_TOMATOES_WINDOW_TIME_PERIOD = datetime.timedelta(minutes=1)
    ROTTEN_TOMATOES_WINDOW_MAX_REQUESTS = 20

    UNLIMITED = 'unlimited'

    _logger: BasicLogger = None
    _instance = None

    @classmethod
    def class_init(cls) -> None:
        """

        """
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)

    @classmethod
    def get_kodi_json(cls,
                      query: str,
                      dump_results: bool = False) -> Dict[str, Any]:
        """
            Queries Kodi database and returns JSON result

        :param query:
        :param dump_results:
        :return:
        """
        json_text = xbmc.executeJSONRPC(query)
        Monitor.exception_on_abort()
        movie_results = json.loads(json_text, encoding='utf-8',
                                   object_hook=JsonUtilsBasic.abort_checker)
        if dump_results and cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            Monitor.exception_on_abort()
            cls._logger.debug_extra_verbose(f'JASON DUMP: '
                                            f'{json.dumps(json_text, indent=3, sort_keys=True)}')
        return movie_results

    @staticmethod
    def abort_checker(dct: Dict[str, Any]) -> Dict[str, Any]:
        """

        :param dct:
        :return:
        """
        Monitor.exception_on_abort()
        return dct


# Force initialization of config_logger
JsonUtilsBasic.class_init()
