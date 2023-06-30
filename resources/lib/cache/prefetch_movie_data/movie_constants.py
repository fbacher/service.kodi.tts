# -*- coding: utf-8 -*-
"""
Created on 5/17/21

@author: Frank Feuerbacher
"""

from common.logger import *
from common.typing import *


module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)
CHECK_FOR_NULLS: bool = True

MovieType = Dict[str, Any]


class MovieField:
    """
        Defines constant values for Kodi trailer dict fields. Including some
        defined for this plugin.

    """

    """
        Properties requested for initial query of library movies:
                              ["title", "lastplayed", "studio", "cast", "plot", "writer", \
                        "director", "fanart", "runtime", "mpaa", "thumbnail", "file", \
                        "year", "genre", "trailer"]\

        Values returned:
        Kodi library movie: {
         "plot": "Dolly, alias \"Angel Face,\"...
         "writer": ["Leroy Scott", "Edmund Goulding"],
         "movieid": 18338,
         "title": "A Lady of Chance",
         "fanart": "image://%2fmovies%2f...-fanart.jpg/",
         "mpaa": "",
         "lastplayed": "2019-01-29 07:16:43",
         "label": "A Lady of Chance",
         "director": ["Robert Z. Leonard"]
         "cast": [{"thumbnail": "image://%2fmovies%2f...Norma_Shearer.jpg/",
                    "role": "Dolly",
                    "name": "Norma Shearer",
                    "order": 0},
                  {"thumbnail": ... "order": 10}],
         "studio": ["Metro-Goldwyn-Mayer (MGM)"],
         "file": "/movies/XBMC/Movies/20s/A Lady of Chance (1928).avi",
         "year": 1928,
         "genre": ["Comedy", "Drama", "Romance"],
         "runtime": 4800,
         "thumbnail": "image://%2fmovi...%20(1928)-poster.jpg/",
         "trailer": "/movies/XBMC/Movies/20s/A Lady of C...ler.mkv"}

        Possible Properties from VideoLibrary.getMovies:

        Parms:
              "genreid" a Library.Id
            "genre" string
            "year" int
            "actor": string
            "director" string
            "studio": string
            "country" string
            "setid" Library.Id
            "set" string
            tag string
        results


Item.Details.Base
    string label
Media.Details.Base
    [ string fanart ]
    [ string thumbnail ]


Video Details Base
 [Media.Artwork art ]
      Global.String.NotEmpty banner ]
    [ Global.String.NotEmpty fanart ]
    [ Global.String.NotEmpty poster ]
    [ Global.String.NotEmpty thumb ]
[ integer playcount = "0" ]

Video.Details.Media
    [string title]
    [ Video.Cast cast ]
    [ Array.String country ]
    [ Array.String genre ]
    [ string imdbnumber ]
    Library.Id movieid
    [ string mpaa ]
    [ string originaltitle ]
    [ string plotoutline ]
    [ string premiered ]
    [ number rating = "0" ]
    [ mixed ratings ]
    [ string set ]
    [ Library.Id setid = "-1" ]
    [ Array.String showlink ]
    [ string sorttitle ]
    [ Array.String studio ]
    [ Array.String tag ]
    [ string tagline ]
    [ integer top250 = "0" ]
    [ string trailer ]
    [ Media.UniqueID uniqueid ]
    [ integer userrating = "0" ]
    [ string votes ]
    [ Array.String writer ]
    [ integer year = "0" ]


Video.Details.Item
    [ string dateadded ]
    [ string file ]
    [ string lastplayed ]
    [ string plot ]


Video.Details.File
    [ Array.String director ]
    [ Video.Resume resume ]
    [ integer runtime = "0" ] Runtime in seconds
    [ Video.Streams streamdetails ]

Video.Details.Movie
    [ Video.Cast cast ]
    [ Array.String country ]
    [ Array.String genre ]
    [ string imdbnumber ]
    Library.Id movieid
    [ string mpaa ]
    [ string originaltitle ]
    [ string plotoutline ]
    [ string premiered ]
    [ number rating = "0" ]
    [ mixed ratings ]
    [ string set ]
    [ Library.Id setid = "-1" ]
    [ Array.String showlink ]
    [ string sorttitle ]
    [ Array.String studio ]
    [ Array.String tag ]
    [ string tagline ]
    [ integer top250 = "0" ]
    [ string trailer ]
    [ Media.UniqueID uniqueid ]
    [ integer userrating = "0" ]
    [ string votes ]
    [ Array.String writer ]
    [ integer year = "0" ]

List.Limits

    [ List.Amount end = "-1" ] Index of the last item to return
    [ integer start = "0" ] Index of the first item to return

List.Sort

    [ boolean ignorearticle = false ]
    [ string method = "none" ]
    [ string order = "ascending" ]
    """
    TITLE: Final[str] = 'title'
    ORIGINAL_TITLE: Final[str] = 'originaltitle'
    TRAILER: Final[str] = 'trailer'
    LAST_PLAYED: Final[str] = 'lastplayed'
    CERTIFICATION_ID: Final[str] = 'certification'
    FANART: Final[str] = 'fanart'
    THUMBNAIL: Final[str] = 'thumbnail'
    FILE: Final[str] = 'file'
    YEAR: Final[str] = 'year'
    WRITER: Final[str] = 'writer'
    DIRECTOR: Final[str] = 'director'
    PLOT: Final[str] = 'plot'
    GENRE_NAMES: Final[str] = 'genre'
    STUDIO: Final[str] = 'studio'
    MOVIEID: Final[str] = 'movieid'
    LABEL: Final[str] = 'label'
    RUNTIME: Final[str] = 'runtime'
    TAG: Final[str] = 'tag'
    UNIQUE_ID: Final[str] = 'uniqueid'

    # Some values for UNIQUE_ID field:
    UNIQUE_ID_TMDB: Final[str] = 'tmdb'
    UNIQUE_ID_UNKNOWN: Final[str] = 'unknown'
    UNIQUE_ID_IMDB: Final[str] = 'imdb'

    RELEASE_DATE: Final[str] = 'releasedate'
    POSTER: Final[str] = 'poster'
    POSTER_2X: Final[str] = 'poster_2x'
    LOCATION: Final[str] = 'location'
    RATING: Final[str] = 'rating'
    VOTES: Final[str] = 'votes'

    # Properties invented by this plugin:

    # From iTunes
    # From TMDb

    # Probably don't need this field in kodi movie dict
    ADULT: Final[str] = 'adult'

    ALT_TITLES: Final[str] = 'alt_titles'
    TRAILER_TYPE: Final[str] = 'trailerType'
    # TODO rename to trailerSource
    SOURCE: Final[str] = 'source'
    CACHED_TRAILER: Final[str] = 'cached_trailer'
    NORMALIZED_TRAILER: Final[str] = 'normalized_trailer'
    ORIGINAL_LANGUAGE: Final[str] = 'original_language'
    LANGUAGE_INFORMATION_FOUND: Final[str] = 'language_information_found'
    LANGUAGE_MATCHES: Final[str] = 'language_matches'

    ITUNES_ID: Final[str] = 'rts.appleId'
    YOUTUBE_ID: Final[str] = 'rts.youtubeId'
    TFH_ID: Final[str] = 'rts.tfhId'
    TFH_TITLE: Final[str] = 'rts.tfh_title'
    YOUTUBE_PLAYLIST_INDEX: Final[str] = 'rts.youtube_index'
    YOUTUBE_TRAILERS_IN_PLAYLIST: Final[str] = 'rts.youtube.trailers_in_index'

    # Processed values for InfoDialog
    ACTORS: Final[str] = 'rts.actors'
    MAX_ACTORS: Final[int] = 6
    MAX_WRITERS: Final[int] = 4
    MAX_STUDIOS: Final[int] = 2

    # For use with speech synthesis
    MAX_VOICED_ACTORS: Final[int] = 3
    VOICED_ACTORS: Final[str] = 'rts.voiced.actors'
    MAX_VOICED_DIRECTORS: Final[int] = 2
    VOICED_DIRECTORS: Final[str] = 'rts.voiced.directors'
    MAX_VOICED_WRITERS: Final[int] = 2
    VOICED_DETAIL_WRITERS: Final[str] = 'rts.voiced.writers'
    MAX_VOICED_STUDIOS: Final[int] = 2
    VOICED_DETAIL_STUDIOS: Final[str] = 'rts.voiced.studios'

    # Reference to corresponding movie dict entry
    DETAIL_ENTRY: Final[str] = 'rts.movie.entry'

    # Source Values. Used to identify source database of movies. Also used to
    # identify discovery modules.

    FOLDER_SOURCE: Final[str] = 'folder'
    LIBRARY_SOURCE: Final[str] = 'library'
    ITUNES_SOURCE: Final[str] = 'iTunes'
    TMDB_SOURCE: Final[str] = 'TMDb'
    TFH_SOURCE: Final[str] = 'TFH'

    TRAILER_TYPE_TRAILER: Final[str] = 'Trailer'
    TRAILER_TYPE_FINAL_TRAILER: Final[str] = 'Final Trailer'
    TRAILER_TYPE_OFFICIAL_TRAILER: Final[str] = 'Official Trailer'
    TRAILER_TYPE_FEATURETTE: Final[str] = 'Featurette'
    TRAILER_TYPE_CLIP: Final[str] = 'Clip'
    TRAILER_TYPE_TEASER: Final[str] = 'Teaser'
    TRAILER_TYPE_BEHIND_THE_SCENES: Final[str] = 'Behind the Scenes'
    TRAILER_TYPE_COMMENTARY: Final[str] = 'Trailer Commentary'

    # Not all sources (TMDb, iTunes provide all of these 'trailer-types'

    TRAILER_TYPES: Tuple[str] = (TRAILER_TYPE_OFFICIAL_TRAILER, TRAILER_TYPE_FINAL_TRAILER,
                                 TRAILER_TYPE_TRAILER, TRAILER_TYPE_FEATURETTE,
                                 TRAILER_TYPE_CLIP, TRAILER_TYPE_TEASER,
                                 TRAILER_TYPE_BEHIND_THE_SCENES, TRAILER_TYPE_COMMENTARY)

    # Map the above TRAILER_TYPES into the base trailer types that this app
    # provides settings for

    TRAILER_TYPE_MAP: Dict[str, str] = {
        TRAILER_TYPE_OFFICIAL_TRAILER:  TRAILER_TYPE_TRAILER,
        TRAILER_TYPE_FINAL_TRAILER: TRAILER_TYPE_TRAILER,
        TRAILER_TYPE_TRAILER: TRAILER_TYPE_TRAILER,
        TRAILER_TYPE_FEATURETTE: TRAILER_TYPE_FEATURETTE,
        TRAILER_TYPE_CLIP: TRAILER_TYPE_CLIP,
        TRAILER_TYPE_TEASER: TRAILER_TYPE_TEASER,
        TRAILER_TYPE_BEHIND_THE_SCENES: TRAILER_TYPE_CLIP,
        TRAILER_TYPE_COMMENTARY: TRAILER_TYPE_CLIP
    }

    SUPPORTED_TRAILER_TYPES: Tuple[str] = (
        TRAILER_TYPE_TRAILER,
        TRAILER_TYPE_FEATURETTE,
        TRAILER_TYPE_CLIP,
        TRAILER_TYPE_TEASER
    )

    LIB_TMDB_ITUNES_TFH_SOURCES: Tuple[str] = (
        LIBRARY_SOURCE, TMDB_SOURCE, ITUNES_SOURCE, TFH_SOURCE)

    # In addition to above source values, these are used to identify
    # discovery modules

    LIBRARY_NO_TRAILER: Final[str] = 'library_no_trailer'
    LIBRARY_URL_TRAILER: Final[str] = 'library_url_trailer'

    # Trailer Type values:
    TMDB_TYPE: Final[str] = 'TMDB_type'
    TMDB_BUFFER_NUMBER: Final[str] = 'TMDB_BUFFER_NUMBER'  # For statistics, remember download page
    TMDB_TOTAL_PAGES: Final[str] = 'TMDB_TOTAL_PAGES'  # For statistics

    TMDB_TAG_NAMES: Final[str] = 'rts.tags'
    TMDB_TAG_IDS: Final[str] = 'rts.tag_ids'
    TMDB_GENRE_IDS: Final[str] = 'rts.genre_ids'
    TMDB_VOTE_AVERAGE: Final[str] = 'rts.tmdb_vote_average'
    TMDB_IS_VIDEO: Final[str] = 'rts.tmdb_video'
    TMDB_POPULARITY: Final[str] = 'rts.tmdb_popularity'

    # DISCOVERY_STATE element contains an ordered list of
    # states.The numeric prefix makes the values comparable like an
    # (poor man's) enum.

    DISCOVERY_STATE: Final[str] = 'DiscoveryState'
    NOT_INITIALIZED: Final[str] = '00_not_initialized'
    NOT_FULLY_DISCOVERED: Final[str] = '01_notFullyDiscovered'
    TRAILER_DISCOVERY_IN_PROGRESS: Final[str] = '02_discoveryInProgress'

    # Most discovery done. Remote trailers and any volume normalization
    # has not yet been done, nor have final details from other sources
    # been acquired. (Example, TFH movie needs details from TMDb).

    DISCOVERY_NEARLY_COMPLETE: Final[str] = '03_discoveryNearlyComplete'

    # READY_TO_DISPLAY means that everything that is needed to play and
    # display info about the trailer has been discovered (i.e. has
    # gone through MovieDetail).

    DISCOVERY_READY_TO_DISPLAY: Final[str] = '04_discoveryReadyToDisplay'

    # FULLY_DISCOVERED indicates that this movie has been fully discovered in
    # the past, and therefore likely to do so again. Helps to prioritize
    # discovery of movies that are most likely to result in ready-to-play
    # trailers

    FULLY_DISCOVERED: Final[str] = 'fully_discovered'

    # IN_FETCH_QUEUE is a boolean
    IN_FETCH_QUEUE: Final[str] = 'in_fetch_queue'

    # TRAILER_PLAYED is a boolean field
    TRAILER_PLAYED: Final[str] = 'trailerPlayed'

    # TMDB_ID_FINDABLE is False, IFF we have tried to
    # find the tmdb id but failed due to TMDb not able to
    # find the movie (not due to communication or other similar failure).

    TMDB_ID_FINDABLE: Final[str] = 'rts.findable'

    # Indicates whether this entry is from the TMDb cache

    CACHED: Final[str] = 'cached'

    # Used to tag class type for serialization

    CLASS: Final[str] = 'class'

    # Used to for serialization of fields not in Map, but as fields (perhaps a
    # mistake)

    LIBRARY_ID: Final[str] = 'rts.library_id'
    TMDB_ID: Final[str] = 'rts.tmdb_id'
    HAS_LOCAL_TRAILER: Final[str] = 'rts.has_local_trailer'
    HAS_TRAILER: Final[str] = 'rts.has_trailer'

    # Reasons a TMDB movie was rejected

    REJECTED: Final[str] = 'rts.rejected'  # Value is a List of the following reasons:
    REJECTED_NO_TRAILER: Final[int] = 1
    REJECTED_FILTER_GENRE: Final[int] = 2
    REJECTED_FAIL: Final[int] = 3  # Request to TMDB failed
    REJECTED_FILTER_DATE: Final[int] = 4
    REJECTED_LANGUAGE: Final[int] = 5
    REJECTED_CERTIFICATION: Final[int] = 6
    REJECTED_ADULT: Final[int] = 7
    REJECTED_VOTE: Final[int] = 8
    REJECTED_TOO_MANY_TMDB_REQUESTS: Final[int] = 9
    REJECTED_NO_TMDB_ID: Final[int] = 10
    REJECTED_WATCHED: Final[int] = 11
    REJECTED_NOT_IN_CACHE: Final[int] = 12

    REJECTED_REASON_MAP = {
        REJECTED_NO_TRAILER: 'No Trailer Found',
        REJECTED_FILTER_GENRE: 'Genre filter',
        REJECTED_FAIL: '',
        REJECTED_FILTER_DATE: 'Date filter',
        REJECTED_LANGUAGE: 'Language filter',
        REJECTED_CERTIFICATION: 'Certification filter',
        REJECTED_ADULT: 'Adult filter',
        REJECTED_VOTE: 'Vote filter',
        REJECTED_TOO_MANY_TMDB_REQUESTS: 'Too many requests try later',
        REJECTED_NO_TMDB_ID: 'No TMDB-id',
        REJECTED_WATCHED: 'Already watched filter',
        REJECTED_NOT_IN_CACHE: 'Not found in cache'
    }
    DEFAULT_MOVIE: MovieType = {
        ACTORS: [],
        CERTIFICATION_ID: '',
        DIRECTOR: [],
        DISCOVERY_STATE: NOT_INITIALIZED,
        FANART: '',
        FILE: '',
        GENRE_NAMES: [],
        PLOT: '',
        RATING: 0.0,
        RUNTIME: 0,
        SOURCE: '',
        STUDIO: [],
        THUMBNAIL: '',
        TITLE: 'default_' + TITLE,
        TMDB_TAG_NAMES: [],
        TRAILER: '',
        TRAILER_TYPE: '',
        VOTES: 0,
        WRITER: [],
        YEAR: 0
    }

    # Used to by get_detail_info to copy fields from TMDb query to non-TMDb movie (TFH, etc.)
    # to supply missing data. The values in this dict are here in case no value was found
    # in the movie to be copied from.

    CLONE_FIELDS: MovieType = {
        ACTORS: [],
        CERTIFICATION_ID: '',
        DIRECTOR: [],
        DISCOVERY_STATE: NOT_INITIALIZED,
        FANART: '',
        # FILE: '',
        GENRE_NAMES: [],
        # PLOT: '',
        # RATING: 0.0,
        RUNTIME: 0,
        # SOURCE: '',
        STUDIO: [],
        # THUMBNAIL: '',
        TITLE: 'default_' + TITLE,
        TMDB_TAG_NAMES: [],
        # TRAILER: '',
        TRAILER_TYPE: '',
        # VOTES: 0,
        WRITER: [],
        YEAR: 0
    }

    # Meant to clone fields that are generated at run-time.

    DETAIL_CLONE_FIELDS: MovieType = {
        NORMALIZED_TRAILER: '',
        CACHED_TRAILER: '',
        TRAILER: ''
    }

    # Used to by get_detail_info to copy fields from TMDb query to TFH movies
    # to supply missing data. The values in this dict are here in case no value was found
    # in the movie to be copied from.

    TFH_CLONE_FIELDS: MovieType = {
        ACTORS: [],
        CERTIFICATION_ID: '',
        DIRECTOR: [],
        DISCOVERY_STATE: NOT_INITIALIZED,
        FANART: '',
        FILE: '',
        GENRE_NAMES: [],
        # PLOT: '',
        # RATING: 0.0,
        RUNTIME: 0,
        # SOURCE: '',
        STUDIO: [],
        # THUMBNAIL: '',
        TITLE: 'default_' + TITLE,
        TMDB_TAG_NAMES: [],
        # TRAILER: '',
        # TRAILER_TYPE: '',
        VOTES: 0,
        WRITER: [],
        YEAR: 0
    }

    # Initially, the only data in a TFH movie is that which comes from Youtube playlist
    TFH_SKELETAL_MOVIE: MovieType = {
        TITLE: 'default_' + TITLE,
        TFH_ID: '',
        # ORIGINAL_LANGUAGE    # For TMDb, assume that only ORIGINAL_LANGUAGE is spoken
        TRAILER: '',
        PLOT: '',
        SOURCE: '',
        TRAILER_TYPE: TRAILER_TYPE_TRAILER
    }

    TMDB_PAGE_DATA_FIELDS: Final[List[str]] = [
        CLASS,
        TITLE,
        YEAR,
        TMDB_POPULARITY,
        VOTES,
        RATING,
        TMDB_GENRE_IDS,
        ORIGINAL_LANGUAGE,
        ORIGINAL_TITLE,
        CERTIFICATION_ID,
        TMDB_BUFFER_NUMBER,
        TMDB_TOTAL_PAGES
        ]

    TMDB_ENTRY_FIELDS: Final[List[str]] = [
        #  "alternative_titles",
        "backdrop_path",
        #  "belongs_to_collection",
        #  "budget",
        "credits",
        "genres",
        #  "homepage",
        "id",
        "imdb_id",
        "keywords",
        "original_language",
        "original_title",
        "overview",
        "popularity",
        "poster_path",
        "production_companies",
        #  "production_countries",
        "release_date",
        "releases",
        #  "revenue",
        "runtime",
        "spoken_languages",
        #  "status",
        "tagline",
        TITLE,
        "video",
        "videos",
        "vote_average",
        "vote_count",
        CACHED
    ]


class DiscoveryState:
    NOT_INITIALIZED: Final[str] = '00_not_initialized'
    NOT_FULLY_DISCOVERED: Final[str] = '01_notFullyDiscovered'
    TRAILER_DISCOVERY_IN_PROGRESS: Final[str] = '02_discoveryInProgress'
    DISCOVERY_COMPLETE: Final[str] = '03_discoveryComplete'
    DISCOVERY_READY_TO_DISPLAY: Final[str] = '04_discoveryReadyToDisplay'
