# coding=utf-8
from __future__ import annotations  # For union operator |

import sys

from backends.settings.service_types import ServiceID
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from cache.prefetch_movie_data.db_access import DBAccess
from cache.prefetch_movie_data.parse_library import ParseLibrary
from cache.voicecache import VoiceCache
from common.constants import Constants
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList

MY_LOGGER = BasicLogger.get_logger(__name__)


class SeedCache:

    voice_cache_instance: VoiceCache
    @classmethod
    def discover_movie_info(cls, engine_key: ServiceID) -> None:
        """
        Seeds the cache with movie information. There is no guarantee that the
        text generated here actually matches real messages to be voiced. It is just
        an educated guess.

        TODO: This never turns off discovery. It is run every time tts starts and
            service_worker has the call to this hard-coded to turn on.
            Change to use a setting
            Change to turn off after some goal is achieved.
            Measure how many of these texts actually get used.
            Allow reseeding to occur manually, or when a bunch of movies/tv shows
            added.

        :param engine_key:
        :return:
        """
        try:

            cls.voice_cache_instance = VoiceCache(engine_key)

            query: str = DBAccess.create_details_query()
            results: List[List[Any]] = DBAccess.get_movie_details(query)
            movies: List[Dict[str, Any]] = results[0]
            engine_output_formats = SoundCapabilities.get_output_formats(engine_key)
            number_of_movies = len(movies)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Number of movies to discover: {number_of_movies:d}')
            movie_counter: int = 0
            for raw_movie in movies:
                try:
                    movie_counter += 1
                    if (movie_counter % 100) == 0 and MY_LOGGER.isEnabledFor(DEBUG):
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Movies processed: {movie_counter:d}')
                    # Don't hog cpu. Wait a few seconds between queries
                    timeout: float
                    timeout = Constants.SEED_CACHE_MOVIE_INFO_DELAY_BETWEEN_QUERY_SECONDS
                    Monitor.exception_on_abort(timeout=timeout)
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
                    plot_found = cls.write_cache_txt(movie.get_plot(), engine_key,
                                                     engine_output_formats)
                    if plot_found:
                        continue
                    title: str = movie.get_title()
                    cls.write_cache_txt(title, engine_key, engine_output_formats)
                    cls.write_cache_txt(str(movie.get_year()), engine_key,
                                        engine_output_formats)
                    genres: str = movie.get_detail_genres()
                    writers: str = movie.get_detail_writers()
                    directors: str = movie.get_detail_directors()
                    cls.write_cache_txt(writers, engine_key, engine_output_formats)
                    cls.write_cache_txt(directors, engine_key, engine_output_formats)
                    cls.write_cache_txt(genres, engine_key, engine_output_formats)
                    studios: str = movie.get_detail_studios()
                    rating: str = movie.get_detail_rating()
                    cls.write_cache_txt(rating, engine_key, engine_output_formats)
                except AbortException:
                    reraise(*sys.exc_info())
                except Exception as e:
                    MY_LOGGER.exception('')
                MY_LOGGER.debug(f'Done counting movies # {movie_counter:d}')

        except AbortException:
            return  # Let thread die
        except Exception as e:
            MY_LOGGER.exception('')

    @classmethod
    def write_cache_txt(cls, text_to_voice: str, engine_key: ServiceID,
                        input_formats: List[str]) -> bool:
        phrase: Phrase = Phrase(text_to_voice, check_expired=False)
        phrases: PhraseList = PhraseList.create(texts=text_to_voice, check_expired=False)
        cls.voice_cache_instance.seed_text_cache(phrases)
        return True
