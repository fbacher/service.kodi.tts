# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

"""
Created on 4/13/21

@author: Frank Feuerbacher
"""
import datetime

from common import *

from cache.prefetch_movie_data.movie_constants import MovieField, MovieType
from common.logger import *

module_logger: BasicLogger = BasicLogger.get_logger(__name__)
CHECK_FOR_NULLS: bool = True


class BaseMovie:

    _logger: BasicLogger = None

    def __init__(self, movie_id: str = None, source: str = None) -> None:
        self._movie_id = None
        if movie_id is not None:
            self.set_id(movie_id)

        self._source: str = source
        self._fully_discovered: bool = False
        self._has_local_trailer = False
        self._has_trailer = False
        self._library_id: int = None
        self._folder_id: str = None
        self._tmdb_id: int = None

    @classmethod
    def class_init(cls):
        if cls._logger is None:
            cls._logger = module_logger

    def __str__(self) -> str:
        return f'{type(self).__name__} id: {self._movie_id} tmdb_id: {self._tmdb_id}'

    def get_id(self) -> str:
        """
        Gets the id appropriate for the class of movie
        :return:
        """
        return str(self._movie_id)

    def set_id(self, movie_id: str) -> None:
        self._movie_id = movie_id

    def get_library_id(self) -> Union[int, None]:
        return self._library_id

    def set_library_id(self, library_id: int = None) -> None:
        self._library_id = library_id


class AbstractMovieId(BaseMovie):

    _logger: BasicLogger = None

    def __init__(self, movie_id: str, source: str) -> None:
        super().__init__(movie_id, source)

    def __str__(self):
        return f'{type(self)}.__name__ id: {self.get_id()}'

    @classmethod
    def class_init(cls):
        if cls._logger is None:
            cls._logger = module_logger

    def get_id(self) -> str:
        return str(self._movie_id)

    def get_tmdb_id(self) -> Union[int, None]:
        """

        :return:
        """
        return self._tmdb_id

    def set_tmdb_id(self, tmdb_id: int = None) -> None:
        self._tmdb_id = tmdb_id

    def get_library_id(self) -> Union[None, int]:
        return self._library_id

    def get_has_trailer(self) -> bool:
        return self._has_trailer

    def set_has_trailer(self, has_trailer: bool = True) -> None:
        self._has_trailer = has_trailer

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            clz = type(self)
            clz._logger.debug(f'instances dose not match self: {type(self)} '
                              f'other: {type(other)}')
            raise NotImplementedError()

        if other.get_id() == self.get_id():
            return True
        return False

    def __ne__(self, other):
        if not isinstance(other, type(self)):
            raise True

        return not self.__eq__(other)

    def __hash__(self):
        return self.get_id().__hash__()


class RawMovie(BaseMovie):

    _logger: BasicLogger = None

    def __init__(self, movie_id: str = None, source: str = None,
                 movie_info: MovieType = None) -> None:
        #
        # Nasty circular dependency here. BaseMovie.__init__() calls
        # self.setId, which some classes override to save into _movie_info.
        # Define _movie_info here, but BaseMovie may alter it, so we
        # have to preserve any changes.

        self._movie_info: MovieType = {}
        super().__init__(movie_id, source)
        if movie_info is None:
            movie_info = {}
        temp_movie_info: MovieType = movie_info.copy()
        for key, value in self._movie_info.items():
            temp_movie_info[key] = value

        self._movie_info = temp_movie_info

    def __str__(self) -> str:
        return f'{type(self).__name__} {self.get_title()}'

    def null_check(self) -> None:
        clz = type(self)
        nulls_found: List[str] = []
        for (key, value) in self._movie_info.items():
            if value is None:
                nulls_found.append(key)

        if clz._logger.isEnabledFor(DEBUG_XV):
            if len(nulls_found) > 0:
                clz._logger.debug_xv(', '.join(nulls_found))

    @classmethod
    def class_init(cls):
        if cls._logger is None:
            cls._logger = module_logger

    def get_property_with_default(self, property_name: str,
                                  default_value: Any = None) -> Any:
        return self._movie_info.get(property_name, default_value)

    def get_property(self, property_name: str, default=None) -> Any:
        return self._movie_info.get(property_name, default)

    def set_property(self, property_name: str, value: Any) -> None:
        self._movie_info[property_name] = value

    def del_property(self, property_name) -> None:
        if property_name in self._movie_info:
            del self._movie_info[property_name]

    def get_as_movie_type(self) -> MovieType:
        return self._movie_info


class AbstractMovie(RawMovie):

    _logger: BasicLogger = None

    def __init__(self, movie_id: str = None, source: str = None,
                 movie_info: MovieType = None) -> None:
        #
        # TODO: Remove if we keep RawMovie
        #
        # Nasty circular dependency here. BaseMovie.__init__() calls
        # self.setId, which some classes override to save into _movie_info.
        # Define _movie_info here, but BaseMovie may alter it, so we
        # have to preserve any changes.

        self._movie_info: MovieType = {}
        super().__init__(movie_id, source)
        if movie_info is None:
            movie_info = {}
        temp_movie_info: MovieType = movie_info.copy()
        for key, value in self._movie_info.items():
            temp_movie_info[key] = value

        self._movie_info = temp_movie_info

    def __str__(self) -> str:
        return f'{type(self).__name__} {self.get_title()} ({self.get_year()}) id:'

    def null_check(self) -> None:
        clz = type(self)
        nulls_found: List[str] = []
        for (key, value) in self._movie_info.items():
            if value is None:
                nulls_found.append(key)

        if clz._logger.isEnabledFor(DEBUG_XV):
            if len(nulls_found) > 0:
                clz._logger.debug_xv(', '.join(nulls_found))

    @classmethod
    def class_init(cls):
        if cls._logger is None:
            cls._logger = module_logger

    def get_property_with_default(self, property_name: str,
                                  default_value: Any = None) -> Any:
        return self._movie_info.get(property_name, default_value)

    def get_property(self, property_name: str, default=None) -> Any:
        return self._movie_info.get(property_name, default)

    def set_property(self, property_name: str, value: Any) -> None:
        self._movie_info[property_name] = value

    def del_property(self, property_name) -> None:
        if property_name in self._movie_info:
            del self._movie_info[property_name]

    def get_as_movie_type(self) -> MovieType:
        return self._movie_info

    def get_discovery_state(self) -> str:  # DiscoveryState:
        return self._movie_info.setdefault(MovieField.DISCOVERY_STATE,
                                           MovieField.NOT_INITIALIZED)

    def set_discovery_state(self, state: str) -> None:  # DiscoveryState):
        self._movie_info[MovieField.DISCOVERY_STATE] = state

    def get_title(self) -> str:
        return self._movie_info.get(MovieField.TITLE)

    def set_title(self, title: str) -> None:
        self._movie_info[MovieField.TITLE] = title

    def set_alt_titles(self, alt_titles: List[Tuple[str, str]]) -> None:
        # Each entry is: (Alt-title, country_code)
        self._movie_info[MovieField.ALT_TITLES] = alt_titles

    def get_year(self) -> int:
        return self._movie_info.get(MovieField.YEAR, 0)

    def set_year(self, year: int) -> None:
        try:
            int_year: int = int(year)
        except:
            clz = type(self)
            clz._logger.error(f'Invalid year: {year} for movie: {self.get_title()} ')
            return
        if year is not None:
            self._movie_info[MovieField.YEAR] = year

    def get_certification_id(self) -> str:
        certification_id: str = self._movie_info.get(MovieField.CERTIFICATION_ID, '')
        return certification_id

    def set_certification_id(self, certification: str) -> None:
        self._movie_info[MovieField.CERTIFICATION_ID] = certification

    def has_directors(self) -> bool:
        return len(self.get_directors()) > 0

    def get_directors(self) -> List[str]:
        return self._movie_info.setdefault(MovieField.DIRECTOR, [])

    def set_directors(self, directors: List[str]) -> None:
        # Eliminate duplicates (should be very rare)
        self._movie_info[MovieField.DIRECTOR] = list(set(directors))

    def get_detail_directors(self) -> str:
        return ', '.join(self.get_directors())

    def has_fanart(self) -> bool:
        return self.get_fanart('') != ''

    def get_fanart(self, default=None) -> Union[str, None]:
        return self._movie_info.get(MovieField.FANART, default)

    def set_fanart(self, path: str) -> None:
        self._movie_info[MovieField.FANART] = path

    def get_genre_names(self) -> List[str]:
        """
        Returns names of genres in the source database schema
        #  TODO: probably should change to internal Genre id format
        :return:
        """
        return self._movie_info.setdefault(MovieField.GENRE_NAMES, [])

    def set_genre_names(self, genres: List[str]) -> None:
        self._movie_info[MovieField.GENRE_NAMES] = genres

    def is_language_information_found(self) -> bool:
        return self._movie_info.setdefault(MovieField.LANGUAGE_INFORMATION_FOUND, False)

    def set_is_language_information_found(self, found: bool) -> None:
        self._movie_info[MovieField.LANGUAGE_INFORMATION_FOUND] = found

    def get_library_id(self) -> Union[int, None]:
        return self._movie_info.get(MovieField.MOVIEID, None)

    def set_library_id(self, library_id: int = None) -> None:
        self._movie_info[MovieField.MOVIEID] = library_id

    def has_library_id(self) -> bool:
        is_has_library_id = False
        if self.get_library_id() is not None:
            is_has_library_id = True

        return is_has_library_id

    def is_original_language_found(self) -> bool:
        return self._movie_info.setdefault(MovieField.LANGUAGE_MATCHES, False)

    def set_is_original_language_found(self, is_original_language_found: bool) -> None:
        self._movie_info[MovieField.LANGUAGE_MATCHES] = is_original_language_found

    def get_original_title(self) -> str:
        return self._movie_info.setdefault(MovieField.ORIGINAL_TITLE, '')

    def set_original_title(self, original_title: str) -> None:
        self._movie_info[MovieField.ORIGINAL_TITLE] = original_title

    def get_plot(self) -> str:
        return self._movie_info.setdefault(MovieField.PLOT, '')

    def set_plot(self, plot: str) -> None:
        self._movie_info[MovieField.PLOT] = plot

    def get_rating(self) -> float:  # 0 .. 10
        return self._movie_info.setdefault(MovieField.RATING, 0.0)

    def set_rating(self, rating: float) -> None:
        self._movie_info[MovieField.RATING] = float(rating)

    def get_detail_rating(self) -> str:
        votes: str = str(self.get_votes())
        return f'{self.get_rating()} ({votes} / votes)'

    def get_runtime(self) -> int:
        if self._movie_info.get(MovieField.RUNTIME) is None:
            x = 1
        return self._movie_info.setdefault(MovieField.RUNTIME, 0)

    def set_runtime(self, seconds: int) -> None:
        if seconds is None:
            seconds = 0

        self._movie_info[MovieField.RUNTIME] = seconds

    def has_studios(self) -> bool:
        return len(self.get_studios()) > 0

    def get_studios(self) -> List[str]:
        return self._movie_info.setdefault(MovieField.STUDIO, [])

    def set_studios(self, studios_arg: List[str]) -> None:

        if len(studios_arg) > MovieField.MAX_STUDIOS:
            studios = studios_arg[:MovieField.MAX_STUDIOS - 1]
        else:
            studios = studios_arg

        self._movie_info[MovieField.STUDIO] = studios

    def get_detail_studios(self) -> str:
        return ', '.join(self.get_studios())

    def set_unique_ids(self, ids: Dict[str, str]):
        self._movie_info[MovieField.UNIQUE_ID] = ids

    def get_tag_names(self) -> List[str]:  # TODO: eliminate!
        return self._movie_info.setdefault(MovieField.TMDB_TAG_NAMES, [])

    def set_tag_names(self, keywords: List[str]) -> None:
        self._movie_info[MovieField.TMDB_TAG_NAMES] = keywords

    def get_tag_ids(self) -> List[str]:  # TODO: eliminate!
        return self._movie_info.setdefault(MovieField.TMDB_TAG_IDS, [])

    def set_tag_ids(self, keywords: List[str]) -> None:
        self._movie_info[MovieField.TMDB_TAG_IDS] = keywords

    def get_votes(self) -> int:
        return self._movie_info.setdefault(MovieField.VOTES, 0)

    def set_votes(self, votes: int) -> None:
        self._movie_info[MovieField.VOTES] = votes

    def has_actors(self) -> bool:
        return len(self.get_actors()) > 0

    def get_actors(self) -> List[str]:
        """
        Gets ordered list of actors for this movies, in order of billing.
        Maximum of MovieField.MAX_DISPLAYED_ACTORS returned.
        :return:
        """
        return self._movie_info.get(MovieField.ACTORS, [])

    def set_actors(self, actors: List[str]) -> None:
        if len(actors) > MovieField.MAX_ACTORS:
            actors = actors[:MovieField.MAX_ACTORS - 1]

        self._movie_info[MovieField.ACTORS] = actors

    def has_writers(self) -> bool:
        return len(self.get_writers()) > 0

    def get_detail_actors(self) -> str:
        return ', '.join(self.get_actors())

    def get_writers(self) -> List[str]:
        return self._movie_info.setdefault(MovieField.WRITER, [])

    def set_writers(self, writers_arg: List[str]) -> None:
        # There can be duplicates (script, book, screenplay...)
        duplicate_writers: Set[str] = set()
        writers: List[str] = []
        writer: str
        for writer in writers_arg:
            if writer not in duplicate_writers:
                duplicate_writers.add(writer)
                writers.append(writer)

        if len(writers) > MovieField.MAX_WRITERS:
            writers = writers[:MovieField.MAX_WRITERS - 1]

        self._movie_info[MovieField.WRITER] = writers

    def get_detail_writers(self) -> str:
        movie_writers = ', '.join(self.get_writers())
        return movie_writers

    def get_voiced_detail_writers(self) -> List[str]:
        writers = self.get_writers()
        if len(writers) > MovieField.MAX_VOICED_WRITERS:
            writers = writers[:(MovieField.MAX_VOICED_WRITERS - 1)]

        return writers

    def get_voiced_actors(self) -> List[str]:
        #  TODO: change set to loop
        actors: List[str] = list(set(self.get_actors()))  # In case not unique

        if len(actors) > MovieField.MAX_VOICED_ACTORS:
            actors = actors[:MovieField.MAX_VOICED_ACTORS - 1]
        return actors

    def get_voiced_directors(self) -> List[str]:
        #  TODO: change set to loop
        directors: List[str] = list(set(self.get_directors()))  # In case not unique

        if len(directors) > MovieField.MAX_VOICED_DIRECTORS:
            directors = directors[:MovieField.MAX_VOICED_DIRECTORS - 1]
        return directors

    def get_detail_genres(self) -> str:
        return ' / '.join(self.get_genre_names())

    def get_detail_runtime(self) -> str:
        runtime: int = self.get_runtime()
        delta_time: datetime.timedelta = datetime.timedelta(seconds=runtime)
        hours: int = int(delta_time.total_seconds() // 3600)
        minutes: int = int((delta_time.total_seconds() % 3600) // 60)
        seconds: int = int(delta_time.total_seconds() % 60)
        return f'{hours:}:{minutes:02}:{seconds:02}'

    def set_voiced_detail_directors(self, directors: List[str]) -> None:
        if len(directors) > MovieField.MAX_VOICED_DIRECTORS:
            self._movie_info[MovieField.VOICED_DIRECTORS] = \
                directors[:MovieField.MAX_VOICED_DIRECTORS - 1]
        else:
            self._movie_info[MovieField.VOICED_DIRECTORS] = directors

    def get_voiced_studios(self) -> List[str]:
        studios: List[str] = self.get_studios()
        if len(studios) > MovieField.MAX_VOICED_STUDIOS:
            studios = studios[:MovieField.MAX_VOICED_STUDIOS - 1]
        return studios

    def get_itunes_id(self) -> str:
        return self._movie_info.get(MovieField.ITUNES_ID)

    def set_itunes_id(self, itunes_id: str) -> None:
        self._movie_info[MovieField.ITUNES_ID] = itunes_id

    def get_tfh_id(self) -> str:
        return self._movie_info.get(MovieField.TFH_ID)

    def set_tfh_id(self, tfh_id: str) -> None:
        self._movie_info[MovieField.TFH_ID] = tfh_id

    def get_id(self) -> str:
        raise NotImplemented


class LibraryMovie(AbstractMovie):
    _logger: BasicLogger = None

    def __init__(self, movie_id: str = None, source: str = None,
                 movie_info: MovieType = None) -> None:
        if movie_info is not None:
            movie_id = movie_info.get(MovieField.MOVIEID, None)
        super().__init__(movie_id, MovieField.LIBRARY_SOURCE, movie_info)

    @classmethod
    def class_init(cls):
        if cls._logger is None:
            cls._logger = module_logger

    def get_id(self) -> str:
        return str(self.get_property(MovieField.MOVIEID))

    def set_id(self, library_id: str):
        self.set_library_id(int(library_id))
        self._movie_id = library_id


BaseMovie.class_init()
AbstractMovieId.class_init()
RawMovie.class_init()
AbstractMovie.class_init()
LibraryMovie.class_init()
