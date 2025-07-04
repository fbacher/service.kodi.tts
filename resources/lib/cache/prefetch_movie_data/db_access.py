# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

"""
Created on 6/12/21

@author: Frank Feuerbacher

Provides methods to create and execute queries to Kodi database

"""
import sys

import json

from common import *

from cache.prefetch_movie_data.json_utils_basic import JsonUtilsBasic
from common.logger import *
from common.monitor import Monitor

MY_LOGGER: Final[BasicLogger] = BasicLogger.get_logger(__name__)


class DBAccess:
    # The properties below are largely the same as what is found in
    # movie_constants MOVIE_FIELD. However, the ones here are the
    # the Kodi db property names and several in MOVIE_FIELD have
    # been changed to be more clear. Example: "mpaa" is used to
    # store certification, but "mpaa" is the name of the US
    # certification authority. In this case, this addon uses
    # "certification" instead of "mpaa" to hold the same info.

    MINIMAL_PROPERTIES: Final[List[str]] = [
        "title",
        "lastplayed",
        "rating",
        "mpaa",
        "year",
        "trailer",
        "uniqueid"
    ]

    DETAIL_PROPTIES: Final[List[str]] = [
        "title",
        "lastplayed",
        "rating",
        "mpaa",
        "year",
        "trailer",
        "uniqueid",
        "studio",
        "cast",
        "plot",
        "writer",
        "director",
        "fanart",
        "ratings",
        "runtime",
        "thumbnail",
        "file",
        "genre",
        "tag",
        "userrating",
        "votes"
    ]

    @classmethod
    def create_details_query(cls) -> str:
        """
        :return:
        """

        # Getting ALL of the properties that we use and not just the ones needed for
        # Details. This is done because there are not that many that we can skip and
        # it means that we don't have to merge results.

        prefix = f'{{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", ' \
                 f'"params": {{' \
                 f'"properties": ' \
                 f'['

        query_properties: str = ', '.join(f'"{prop}"' for prop in cls.DETAIL_PROPTIES)
        query_suffix = f']}}, "id": 1}}'

        query = f'{prefix}{query_properties}{query_suffix}'

        if MY_LOGGER.isEnabledFor(DISABLED):
            MY_LOGGER.debug_v(f'query: {query}')

        return query

    @classmethod
    def get_movie_details(cls, query: str) -> List[Dict[str, Any]]:
        movies: List[Dict[str, Any]] = []
        try:
            if MY_LOGGER.isEnabledFor(DISABLED):
                import json as json
                # json_encoded: Dict = json.loads(query)
                dump: str = json.dumps(query, indent=3, sort_keys=True)
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'JASON DUMP: {dump}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            pass

        # Depending upon the query, either a single movie is returned, or a list.
        # Always return a list

        query_result: Dict[str, Any] = {}
        try:
            query_result: Dict[str, Any] = JsonUtilsBasic.get_kodi_json(query,
                                                                        dump_results=False)
            if query_result.get('error') is not None:
                raise ValueError

            Monitor.exception_on_abort()
            result: Dict[str, Any] = query_result.get('result', {})
            movie: Dict[str, Any] = result.get('movies', None)
            if movie is None:
                movies = result.get('movies', [])
                if MY_LOGGER.isEnabledFor(DISABLED):
                    MY_LOGGER.error(f'Got back movies {len(movies)} '
                                    'instead of moviedetails.')
            else:
                movies.append(movie)

        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            movies = []
            message: str = ''
            if query_result is not None:
                error = query_result.get('error')
                if error is not None:
                    message: str = error.get('message')
            MY_LOGGER.exception(message)
            try:
                import json as json
                # json_encoded: Dict = json.loads(query)
                dump: str = json.dumps(query, indent=3, sort_keys=True)
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'JASON DUMP: {dump}')
            except Exception:
                movies = []

        return movies

    @classmethod
    def create_title_date_query(cls, title: str, year: str) -> str:
        """


        :return:
        """
        '''
  {"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "properties": [ 
  "title", "lastplayed", "studio", "cast", "plot", "writer", "director", "fanart", 
  "runtime", "mpaa", "thumbnail", "file","year", "genre", "tag", "trailer" ], "filter": 
  { "or": [ { "field": "genre", "operator": "contains", "value": [ "Film-Noir" ] }, 
  { "field": "tag", "operator": "contains", "value": [ "classic noir", "film noir", 
  "french noir", "brit noir" ] } ] } }, "id": 1 }
  
"{\"jsonrpc\": \"2.0\", \"method\": \"VideoLibrary.GetMovies\", \"params\": { 
\"properties\": [ \"title\", \"lastplayed\", \"rating\", \"mpaa\", \"year\", 
\"trailer\", \"uniqueid\" ], \"filter\": { \"and\": [ { \"field\": \"title\", 
\"operator\", \"is\", \"value\": \"Cash on Demand\" }, { \"field\": \"year\", 
\"operator\": \"is\", \"value\": \"1961\" } ] } }, \"id\": 1}"

'{
"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "properties": [ 
"title", "lastplayed", "rating", "mpaa", "year", "trailer", "uniqueid" ], "filter": { 
"and": [ { "field": "title", "operator", "is", "value": "Cash on Demand" }, { "field": 
"year", "operator": "is", "value": "1961" } ] } }, "id": 1}'


'''

        props: List[str]
        props = cls.MINIMAL_PROPERTIES

        query_properties: str = ', '.join(f'"{prop}"' for prop in props)
        query = f'{{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", ' \
                f'"params": {{ "properties": [ {query_properties} ], ' \
                f'"filter": {{ "and": [ ' \
                f'{{ "field": "title", "operator": ' \
                f'"is", "value": "{title}" }}, ' \
                f'{{ "field": "year", "operator": "is", "value": "{year}" }} ' \
                f'] }} }}, "id": 1}}'

        if MY_LOGGER.isEnabledFor(DISABLED):
            MY_LOGGER.debug_v(f'title: {title} year: {year}')
            MY_LOGGER.debug_v(f'query: {query}')
            try:
                x = json.loads(query)
                query_str = json.dumps(x, indent=4, sort_keys=True)
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    MY_LOGGER.debug_xv(f'query: {query_str}')
            except Exception:
                pass

        return query
