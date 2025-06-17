# coding=utf-8
from __future__ import annotations  # For union operator |

import sys

from common import *

from cache.prefetch_movie_data.movie import LibraryMovie
from cache.prefetch_movie_data.movie_constants import MovieField, MovieType
from common.logger import *

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class ParseLibrary:
    DEFAULT_LAST_PLAYED_DATE: str = '1900-01-01 01:01:01'

    def __init__(self, library_entry: Dict[str, Any]) -> None:
        self._library_entry: Dict[str, Any] = library_entry
        library_id: int = self._library_entry[MovieField.MOVIEID]
        self._movie: LibraryMovie = LibraryMovie(None)
        self._movie.set_library_id(library_id)

    def get_movie(self) -> LibraryMovie:
        return self._movie

    def parse_title(self) -> str:
        title: str = self._library_entry[MovieField.TITLE]
        self._movie.set_title(title)
        return title

    def parse_plot(self) -> None:
        plot: str = self._library_entry.get(MovieField.PLOT, '')
        self._movie.set_plot(plot)

    def parse_writers(self) -> None:
        writers: List[str] = self._library_entry.get(MovieField.WRITER, [])
        self._movie.set_writers(writers)

    def parse_fanart(self) -> None:
        fanart_path: str = self._library_entry.get(MovieField.FANART, '')
        self._movie.set_fanart(fanart_path)

    def parse_directors(self) -> None:
        directors: List[str] = self._library_entry.get(MovieField.DIRECTOR, [])
        self._movie.set_directors(directors)

    def parse_actors(self) -> None:
        """
        "cast": [{"thumbnail": "image://%2fmovies%2f...Norma_Shearer.jpg/",
          "role": "Dolly",
          "name": "Norma Shearer",
          "order": 0},
         {"thumbnail": ... "order": 10}],
        :return:
        """

        duplicate_check: Set[str] = set()

        cast: List[Dict[str, Union[str, int]]] = self._library_entry.get('cast', [])
        actors: List[str] = []
        # Create list of actors, sorted by "order".
        # Sort map entries by "order"

        entries: List[Dict[str, Union[str, int]]] = sorted(cast,
                                                           key=lambda i: i['order'])

        entry: Dict[str, str]
        for entry in entries:
            actor: str = entry['name']
            if actor not in duplicate_check:
                duplicate_check.add(actor)
                actors.append(actor)

        self._movie.set_actors(actors)

    def parse_studios(self) -> None:
        studios: List[str] = self._library_entry.get(MovieField.STUDIO, [])
        self._movie.set_studios(studios)

    def parse_year(self) -> int:
        year: int = self._library_entry.get(MovieField.YEAR, 0)
        self._movie.set_year(year)
        return year

    def parse_genres(self) -> None:
        # Genre labels are unconstrained by kodi. They are simply imported from
        # whatever movie scraper is in effect. TMDb and IMDb are frequent sources.
        # May not be English. GenreUtils gets Genre Labels from TMDb and can
        # convert to language neutral ids.

        genres: List[str] = self._library_entry.get(MovieField.GENRE_NAMES, [])
        self._movie.set_genre_names(genres)

    def parse_runtime(self) -> None:
        movie_seconds: int = self._library_entry.get(MovieField.RUNTIME, 0)
        self._movie.set_runtime(movie_seconds)

    def parse_original_title(self) -> None:
        original_title: str = self._library_entry.get(MovieField.ORIGINAL_TITLE, '')
        self._movie.set_original_title(original_title)

    def parse_vote_average(self) -> None:
        vote_average: int = 0
        try:
            vote_average = int(self._library_entry.get(MovieField.RATING, 0))
        except ValueError:
            pass

        self._movie.set_rating(vote_average)

    def parse_unique_ids(self) -> None:
        unique_ids: Dict[str, str] = self._library_entry.get(MovieField.UNIQUE_ID, {})
        self._movie.set_unique_ids(unique_ids)

    def parse_votes(self) -> None:
        votes: int = self._library_entry.get(MovieField.VOTES, 0)
        self._movie.set_votes(votes)

    @classmethod
    def parse_movie(cls,
                    is_sparse: bool = True,
                    raw_movie: MovieType = None) -> LibraryMovie:
        movie: LibraryMovie | None = None
        try:
            movie_parser: ParseLibrary = ParseLibrary(raw_movie)
            movie_parser.parse_title()
            movie_parser.parse_unique_ids()
            movie_parser.parse_year()
            movie_parser.parse_vote_average()

            if not is_sparse:
                movie_parser.parse_plot()
                movie_parser.parse_writers()
                movie_parser.parse_fanart()
                movie_parser.parse_directors()
                movie_parser.parse_actors()
                movie_parser.parse_studios()
                movie_parser.parse_genres()
                movie_parser.parse_runtime()
                movie_parser.parse_original_title()
                movie_parser.parse_votes()

            movie: LibraryMovie = movie_parser.get_movie()
        except AbortException:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
            movie = None

        return movie
