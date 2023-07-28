# coding=utf-8
import os
import pathlib
import sys

import regex

from backends.audio.sound_capabilties import SoundCapabilities
from cache.prefetch_movie_data.parse_library import ParseLibrary
from cache.voicecache import VoiceCache
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.settings import Settings
from common.typing import *
from cache.prefetch_movie_data.db_access import DBAccess

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SeedCache:
    _logger: BasicLogger = None

    @classmethod
    def init(cls):
        if cls._logger is None:
            cls._logger: BasicLogger = module_logger.getChild(cls.__name__)

    @classmethod
    def discover_movie_info(cls, engine_id: str) -> None:
        try:
            query:str = DBAccess.create_details_query()
            results: List[List[Any]] = DBAccess.get_movie_details(query)
            movies: List[Dict[str, Any]] = results[0]
            engine_output_formats = SoundCapabilities.get_output_formats(engine_id)
            number_of_movies = len(movies)
            cls._logger.debug(f'Number of movies to discover: {number_of_movies:d}')
            movie_counter: int = 0
            for raw_movie in movies:
                try:
                    movie_counter += 1
                    if (movie_counter % 100) == 0:
                        cls._logger.debug(f'Movies processed: {movie_counter:d}')
                    Monitor.wait_for_abort(60.0)  # yield back 60 seconds between entries
                    movie = ParseLibrary.parse_movie(is_sparse=False,
                                                     raw_movie=raw_movie)
                    '''
                        
                        movie_parser.parse_studios()
                        movie_parser.parse_runtime()
                        movie_parser.parse_votes()
                        Country
                        Premiered
                        Rated
                        Tags
                        Date Added
                        Last Played
                        Type movie
                    '''
                    plot_found = cls.write_cache_txt(movie.get_plot(), engine_id, engine_output_formats)
                    if plot_found:
                        continue
                    title: str = movie.get_title()
                    cls.write_cache_txt(title, engine_id, engine_output_formats)
                    cls.write_cache_txt(str(movie.get_year()), engine_id, engine_output_formats)
                    genres: str = movie.get_detail_genres()
                    writers: str = movie.get_detail_writers()
                    directors: str = movie.get_detail_directors()
                    cls.write_cache_txt(writers, engine_id, engine_output_formats)
                    cls.write_cache_txt(directors, engine_id, engine_output_formats)
                    cls.write_cache_txt(genres, engine_id, engine_output_formats)
                    studios: str = movie.get_detail_studios()
                    rating: str = movie.get_detail_rating()
                    cls.write_cache_txt(rating, engine_id, engine_output_formats)
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    cls._logger.exception('')
                cls._logger.debug(f'Done counting movies # {movie_counter:d}')

        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')

    @classmethod
    def write_cache_txt(cls, text_to_voice: str, engine_id: str,
                        input_formats: List[str]) -> bool:
        phrase: Phrase = Phrase(text_to_voice, check_expired=False)

        voice_file_path, exists, _ = VoiceCache.get_best_path(phrase, ['.mp3'])
        if exists:
            return False
        return True


SeedCache.init()
