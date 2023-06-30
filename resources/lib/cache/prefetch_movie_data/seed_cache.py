# coding=utf-8
import os
import sys

from backends.audio.sound_capabilties import SoundCapabilities
from cache.prefetch_movie_data.movie_constants import MovieType
from cache.prefetch_movie_data.parse_library import ParseLibrary
from cache.voicecache import VoiceCache
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase
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
            for raw_movie in movies:
                try:
                    Monitor.wait_for_abort(30.0)  # yield back 30 seconds between entries
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
                    title: str = movie.get_title()
                    cls.write_cache_txt(title, engine_id, engine_output_formats)
                    cls.write_cache_txt(str(movie.get_year), engine_id, engine_output_formats)
                    cls.write_cache_txt(movie.get_plot(), engine_id, engine_output_formats)
                    genres: str = movie.get_detail_genres()
                    writers: str = movie.get_detail_writers()
                    directors: str = movie.get_detail_directors()
                    cls.write_cache_txt(writers, engine_id, engine_output_formats)
                    cls.write_cache_txt(directors, engine_id, engine_output_formats)
                    cls.write_cache_txt(genres, engine_id, engine_output_formats)
                    cls.write_cache_txt(movie.get_plot(), engine_id, engine_output_formats)
                    studios: str = movie.get_detail_studios()
                    rating: str = movie.get_detail_rating()
                    cls.write_cache_txt(rating, engine_id, engine_output_formats)
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    cls._logger.exception('')

        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')


    @classmethod
    def write_cache_txt(cls, text_to_voice: str, engine_id: str,
                        input_formats: List[str]):
        phrase: Phrase = Phrase(text_to_voice)
        voice_file_path, exists, _ = VoiceCache.get_best_path(phrase, ['.mp3'])
        if exists:
            return

        # TODO: Need to split strings longer than engine can handle. See
        #       ResponsiveVoice

        VoiceCache.create_sound_file(phrase.get_cache_path(), create_dir_only=True)
        path: str
        file_type: str
        text_file_path, file_type = os.path.splitext(voice_file_path)
        text_file_path = f'{text_file_path}.txt'
        try:
            if os.path.isfile(text_file_path):
                os.unlink(text_file_path)

            with open(text_file_path, 'wt') as f:
                f.write(text_to_voice)
        except Exception as e:
            if cls._logger.isEnabledFor(ERROR):
                cls._logger.error(
                        f'Failed to save voiced text file: '
                        f'{text_file_path} Exception: {str(e)}')

SeedCache.init()
