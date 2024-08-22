# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os
import pathlib
import sys
import tempfile

import gtts
from backends.ispeech_generator import ISpeechGenerator
from backends.settings.language_info import LanguageInfo
from backends.settings.settings_helper import SettingsHelper
from common import *

from backends import base
from backends.audio.sound_capabilties import SoundCapabilities
from backends.google_data import GoogleData
from backends.players.iplayer import IPlayer
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from cache.voicecache import VoiceCache
from common.base_services import BaseServices
from common.constants import Constants, ReturnCode
from common.exceptions import ExpiredException
from common.kodi_player_monitor import KodiPlayerMonitor
from common.lang_phrases import SampleLangPhrases
from common.logger import *
from common.messages import Message, Messages
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList, PhraseUtils
from common.setting_constants import Backends, Genders, Languages, Mode, PlayerMode
from common.settings import Settings
import langcodes
from gtts import gTTS, gTTSError, lang
from langcodes import LanguageTagError
from utils.util import runInThread
import xbmc

from windowNavigation.choice import Choice

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class Results:
    """
        Contains results of background thread/process
        Provides ability for caller to get status/results
        Also allows caller to abandon results, but allow task to continue
        quietly. This is useful for downloading/generating speech which may
        get canceled before finished, but results can be cached for later use
    """

    def __init__(self):
        self.rc: ReturnCode = ReturnCode.NOT_SET
        # self.download: io.BytesIO = io.BytesIO(initial_bytes=b'')
        self.finished: bool = False
        self.phrase: Phrase = None

    def get_rc(self) -> ReturnCode:
        return self.rc

    # def get_download_bytes(self) -> memoryview:
    #     return self.download.getbuffer()

    # def get_download_stream(self) -> io.BytesIO:
    #     return self.download

    def is_finished(self) -> bool:
        return self.finished

    def get_phrase(self) -> Phrase:
        return self.phrase

    def set_finished(self, finished: bool) -> None:
        self.finished = finished

    # def set_download(self, data: bytes | io.BytesIO | None) -> None:
    #     self.download = data

    def set_rc(self, rc: ReturnCode) -> None:
        self.rc = rc

    def set_phrase(self, phrase: Phrase) -> None:
        self.phrase = phrase


class GoogleSpeechGenerator(ISpeechGenerator):

    MAXIMUM_PHRASE_LENGTH: Final[int] = 200

    _logger: BasicLogger = None

    def __init__(self) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.download_results: Results = Results()
        self.voice_cache: VoiceCache = VoiceCache()

    def set_rc(self, rc: ReturnCode) -> None:
        self.download_results.set_rc(rc)

    def get_rc(self) -> ReturnCode:
        return self.download_results.get_rc()

    def set_phrase(self, phrase: Phrase) -> None:
        self.download_results.set_phrase(phrase)

    # def get_download_bytes(self) -> memoryview:
    #     return self.download_results.get_download_bytes()

    def set_finished(self) -> None:
        self.download_results.set_finished(True)

    def is_finished(self) -> bool:
        return self.download_results.is_finished()

    def generate_speech(self, phrase: Phrase, timeout=1.0) -> Results:
        """
        :param phrase:   Phrase to voice
        :param timeout:  Max time to wait
        :return:
        """
        # Disable expiration checks. We are doing this in background. Results
        # are cached for next time

        clz = type(self)
        Monitor.exception_on_abort(timeout=0.0)
        GoogleTTSEngine.update_voice_path(phrase)
        max_phrase_length: int | None
        max_phrase_length = SettingsMap.get_service_property(GoogleTTSEngine.service_ID,
                                                             Constants.MAX_PHRASE_LENGTH)
        if max_phrase_length is None:
            max_phrase_length = 10000  # Essentially no limit
        self.set_phrase(phrase)
        if phrase.is_empty():
            clz._logger.debug(f'Phrase empty')
            self.set_rc(ReturnCode.OK)
            self.set_finished()
            return self.download_results

        phrase_chunks: PhraseList = PhraseUtils.split_into_chunks(phrase,
                                                                  max_phrase_length)
        unchecked_phrase_chunks: PhraseList = phrase_chunks.clone(check_expired=False)
        runInThread(self._generate_speech, name='download_speech', delay=0.0,
                    phrase_chunks=unchecked_phrase_chunks, original_phrase=phrase,
                    timeout=timeout, gender=phrase.gender)

        max_wait: int = int(timeout / 0.1)
        while max_wait > 0:
            Monitor.exception_on_abort(timeout=0.1)
            max_wait -= 1
            if phrase.exists():  # Background process started elsewhere may finish
                break
            if (self.get_rc() <= ReturnCode.MINOR_SAVE_FAIL or
                    KodiPlayerMonitor.instance().isPlaying()):
                clz._logger.debug(f'generate_speech exit rc: {self.get_rc().name}  '
                                  f'stop: {KodiPlayerMonitor.instance().isPlaying()}')
                break
        return self.download_results

    def _generate_speech(self, **kwargs) -> None:
        # Break long texts into 250 char chunks so that they can be downloaded.
        # Concatenate returned binary voice files together and return
        clz = type(self)
        self.set_rc(ReturnCode.OK)
        text_file_path: pathlib.Path = None
        phrase_chunks: PhraseList | None = None
        original_phrase: Phrase = None
        lang_code: str = None
        country_code: str = None
        gender: str = ''
        tld: str = ''
        tld_arg: str = kwargs.get('tld', None)
        if tld_arg is not None:
            tld = tld_arg
        '''
        lang_code_arg: str = kwargs.get('lang_code', None)
        if lang_code_arg is not None:
            lang_code = lang_code_arg

        country_code_arg: str = kwargs.get('country_code', 'us')
        if country_code_arg is not None:
            country_code = country_code_arg
        
        if lang_code is None or country_code is None:
            locale_id: str = GoogleTTSEngine.get_voice()
            if lang_code is None:
                lang_code = langcodes.Language.get(locale_id).language
            if country_code is None:
                country_code = langcodes.Language.get(locale_id).territory
        '''
        locale_id: str = GoogleTTSEngine.get_voice()
        lang_code = langcodes.Language.get(locale_id).language
        country_code = langcodes.Language.get(locale_id).territory.lower()
        # self._logger.debug(f'voice: {locale_id} lang_code: {lang_code} '
        #                    f'territory: {country_code}')

        # Google don't care about gender
        # arg = kwargs.get('gender', None)
        # if arg is None:
        #     gender: str = GoogleTTSEngine.getGender()
        # else:
        #     gender = arg

        try:
            # The passed in phrase_chunks, are actually chunks of a phrase. Therefor
            # we concatenate the voiced text from each chunk to produce one
            # sound file. This phrase list has expiration disabled.

            phrase_chunks = kwargs.get('phrase_chunks', None)
            if phrase_chunks is None or len(phrase_chunks) == 0:
                self.set_rc(ReturnCode.NO_PHRASES)
                self.set_finished()
                return

            original_phrase = kwargs.get('original_phrase', None)
            clz._logger.debug(f'phrase to download: {original_phrase} '
                              f'path: {original_phrase.get_cache_path()}')
            Monitor.exception_on_abort()
            if original_phrase.exists():
                self.set_rc(ReturnCode.OK)
                self.set_finished()
                return  # Nothing to do

        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            self.set_finished()
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
            self.set_rc(ReturnCode.CALL_FAILED)
            self.set_finished()
            return

        cache_path: pathlib.Path | None = None
        try:
            cache_path = original_phrase.get_cache_path()
            rc2: int
            rc2, _ = self.voice_cache.create_sound_file(cache_path,
                                                        create_dir_only=True)
            if rc2 != 0:
                if clz._logger.isEnabledFor(ERROR):
                    clz._logger.error(f'Failed to create cache directory '
                                      f'{cache_path.parent}')
                self.set_rc(ReturnCode.CALL_FAILED)
                self.set_finished()
                return

            with tempfile.NamedTemporaryFile(mode='w+b', buffering=-1,
                                             suffix=cache_path.suffix,
                                             prefix=cache_path.stem,
                                             dir=cache_path.parent,
                                             delete=False) as sound_file:
                # each 'phrase' is a chunk from one, longer phrase. The chunks
                # are small enough for gTTS to handle. We concatenate the results
                # from the phrase_chunks to the same file.
                temp_file = pathlib.Path(sound_file.name)
                for phrase_chunk in phrase_chunks:
                    phrase_chunk: Phrase
                    try:
                        Monitor.exception_on_abort()
                        if clz._logger.isEnabledFor(DEBUG):
                            clz._logger.debug(f'phrase: '
                                              f'{phrase_chunk.get_text()}')

                        clz._logger.debug(f'GTTS lang: {lang_code} '
                                          f'terr: {country_code} tld: {tld}')
                        my_gtts: MyGTTS = MyGTTS(phrase_chunk, lang_code=lang_code,
                                                 country_code=country_code,
                                                 tld=tld)
                        # gtts.save(phrase.get_cache_path())
                        #     gTTSError – When there’s an error with the API request.
                        # gtts.stream() # Streams bytes
                        my_gtts.write_to_fp(sound_file)
                        clz._logger.debug(f'Wrote cache_file fragment')
                    except AbortException:
                        sound_file.close()
                        pathlib.Path(sound_file.name).unlink(missing_ok=True)
                        self.set_rc(ReturnCode.ABORT)
                        self.set_finished()
                        reraise(*sys.exc_info())
                    except TypeError as e:
                        clz._logger.exception('')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                    except ExpiredException:
                        clz._logger.exception('')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                    except gTTSError as e:
                        clz._logger.exception(f'gTTSError')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                    except IOError as e:
                        clz._logger.exception(f'Error processing phrase: '
                                              f'{phrase_chunk.get_text()}')
                        clz._logger.error(f'Error writing to temp file:'
                                          f' {str(temp_file)}')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                    except Exception as e:
                        clz._logger.exception('')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                clz._logger.debug(f'Finished with loop writing temp file: '
                                  f'{str(temp_file)} size: {temp_file.stat().st_size}')
            if self.get_rc() == ReturnCode.OK:
                try:
                    if temp_file.exists() and temp_file.stat().st_size > 100:
                        temp_file.rename(cache_path)
                        original_phrase.set_exists(True)
                        clz._logger.debug(f'cache_file is: {str(cache_path)}')
                    else:
                        if temp_file.exists():
                            temp_file.unlink(True)
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                except Exception as e:
                    clz._logger.exception('')
            else:
                if temp_file.exists():
                    temp_file.unlink(True)
                self.set_rc(ReturnCode.DOWNLOAD)
                self.set_finished()
        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            self.set_finished()
            reraise(*sys.exc_info())
        except ExpiredException:
            clz._logger.exception('')
            self.set_finished()
            self.set_rc(ReturnCode.DOWNLOAD)
        except Exception as e:
            clz._logger.exception('')
            if clz._logger.isEnabledFor(ERROR):
                clz._logger.error('Failed to download voice: {}'.format(str(e)))
            self.set_finished()
            self.set_rc(ReturnCode.DOWNLOAD)
        clz._logger.debug(f'exit download_speech')
        self.set_finished()
        return None


class MyGTTS(gTTS):

    def __init__(self, phrase: Phrase, lang_code: str = 'en',
                 country_code: str = 'us', tld: str = 'com',
                 lang_check: bool = False) -> None:
        """
        :param self:
        :param phrase:
        :param lang_code:  2-char language code
        :param country_code:  country code
        :param lang_check: True more error detection, but a bit slower to check
        :return:

        Raises:
        AssertionError – When text is None or empty; when there’s nothing left to speak
        after pre-precessing, tokenizing and cleaning.
        ValueError – When lang_check is True and lang is not supported.
        RuntimeError – When lang_check is True but there’s an error loading the
        languages dictionary.

        country_code_country_tld: Dict[str, Tuple[str, str]] = {
                                ISO3166-1, <google tld>, <country name>
        """
        data: Tuple[str, str]
        data = GoogleData.country_code_country_tld[country_code]
        module_logger.debug(f'lang: {lang_code} country: {country_code} '
                            f'data: {data} tld: {tld}' )
        if data is not None and len(data) == 2:
            tld = data[0]
        super().__init__(phrase.get_text(),
                         lang=lang_code,
                         slow=False,
                         lang_check=lang_check,
                         tld=tld
                         #  pre_processor_funcs=[
                         #     pre_processors.tone_marks,
                         #     pre_processors.end_of_line,
                         #     pre_processors.abbreviations,
                         #     pre_processors.word_sub,
                         # ],
                         # tokenizer_func=Tokenizer(
                         #         [
                         #             tokenizer_cases.tone_marks,
                         #             tokenizer_cases.period_comma,
                         #             tokenizer_cases.colon,
                         #             tokenizer_cases.other_punctuation,
                         #         ]
                         # ).run,
                         )


class GoogleTTSEngine(base.SimpleTTSBackend):
    ID: str = Backends.GOOGLE_ID
    backend_id = Backends.GOOGLE_ID
    engine_id = Backends.GOOGLE_ID
    service_ID: str = Services.GOOGLE_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    displayName = 'GoogleTTS'

    _logger: BasicLogger = None
    # lang_map: Dict[str, str] = None # IETF_lang_name: display_name
    _initialized: bool = False

    class LangInfo:
        _logger: BasicLogger = None

        lang_info_map: Dict[str, ForwardRef('LangInfo')] = {}
        initialized: bool = False
        global_lang_initalized: bool = False

        def __init__(self, locale_id: str, language_code: str, country_code: str,
                     language_name: str, country_name: str, google_tld: str) -> None:
            clz = type(self)
            self.locale_id: str = locale_id
            self.language_code: str = language_code
            self.country_code: str = country_code
            self.language_name: str = language_name
            self.country_name: str = country_name
            self.google_tld: str = google_tld
            clz.lang_info_map[locale_id] = self

        @classmethod
        def get(cls, locale_id: str) -> ForwardRef('LangInfo'):
            return cls.lang_info_map.get(locale_id)

        def get_locale_id(self) -> str:
            return self.locale_id

        def get_language_code(self) -> str:
            return self.language_code

        def get_country_code(self) -> str:
            return self.country_code

        def get_language_name(self) -> str:
            return self.language_name

        def get_country_name(self) -> str:
            return self.country_name

        def get_google_tld(self) -> str:
            return self.google_tld

        @classmethod
        def get_locales(cls) -> List[str]:
            return list(cls.lang_info_map.keys())

        @classmethod
        def load_lang_info(cls):
            if not cls.initialized:
                if cls._logger is None:
                    cls._logger = module_logger.getChild(cls.__name__)
                cls.initialized = True
                lang_map = gtts.lang.tts_langs()

                '''
                Languages Google Text-to-Speech supports.
                Returns:
                    A dictionary of the type { ‘<lang>’: ‘<name>’}
                     Where <lang> is an IETF language tag such as en or zh-TW, and <name>
                     is the full English name of the language, such as English or Chinese (
                     Mandarin/Taiwan).
        
                    The dictionary returned combines languages from two origins:
                    - Languages fetched from Google Translate (pre-generated in gtts.langs)
                    - Languages that are undocumented variations that were observed to work 
                      and present different dialects or accents.
                #             <locale>   (<lang_id> <country_id>, <google_domain>)
                locale_map: Dict[str, Tuple[str, str, str]]
                tmp_lang_ids = lang_map.keys()  # en, zh-TW, etc
                
                lang_ids: List[str] = list(tmp_lang_ids)
                '''

                extra_locales = sorted(GoogleData.get_locales())
                for locale_id in extra_locales:
                    lang_country = locale_id.split('-')
                    if len(lang_country) == 2:
                        lang_code = lang_country[0]
                        country_code = lang_country[1]
                    else:
                        lang_code = lang_country
                        country_code = lang_country
                    lang_name: str = lang_map.get(lang_code, locale_id)
                    result = GoogleData.country_code_country_tld.get(country_code)
                    if result is None:
                        cls._logger.debug(f'No TLD for {country_code}.')
                        result = 'com', country_code
                    if len(result) != 2:
                        cls._logger.debug(
                                f'Missing TLD/country code info: result: {result}')
                        result = 'com', country_code
                    tld, country_name = result
                    lang_info: GoogleTTSEngine.LangInfo
                    lang_info = GoogleTTSEngine.LangInfo(locale_id,
                                                         lang_code,
                                                         country_code,
                                                         locale_id,
                                                         f'{country_name}',
                                                         tld)

        @classmethod
        def load_global_lang_info(cls):
            if cls.global_lang_initalized:
                return
            cls.global_lang_initialized = True
            entry: Dict[str, ForwardRef('LangInfo')]
            for locale_id, entry in cls.lang_info_map.items():
                locale_id: str
                entry: GoogleTTSEngine.LangInfo

                lang: langcodes.Language = None
                try:
                    lang = langcodes.Language.get(locale_id)
                except LanguageTagError:
                    cls._logger.exception('')
                voice: str = ''
                try:
                    voice = langcodes.Language.get(locale_id).display_name()
                except:
                    voice = locale_id

                voice_id: str = entry.locale_id.lower()
                engine_name_msg_id: str = Messages.BACKEND_GOOGLE.get_msg_id()
                LanguageInfo.add_language(engine_id=GoogleTTSEngine.engine_id,
                                          language_id=entry.language_code,
                                          country_id=entry.country_code,
                                          ietf=lang,
                                          region_id='',  # Not used by Google
                                          gender=Genders.UNKNOWN,
                                          voice=voice,
                                          engine_lang_id=locale_id,
                                          engine_voice_id=voice_id,
                                          engine_name_msg_id=engine_name_msg_id,
                                          engine_quality=4,
                                          voice_quality=-1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)

        # self.simple_cmd: SimpleRunCommand = None
        self.f = False
        self.voice_cache: VoiceCache = VoiceCache()

        if not clz._initialized:
            BaseServices().register(self)
            clz._initialized = True

    def init(self) -> None:
        clz = type(self)
        super().init()
        self.update()

    def get_voice_cache(self) -> VoiceCache:
        return self.voice_cache

    def get_player_mode(self) -> PlayerMode:
        clz = type(self)
        player: IPlayer = self.get_player(self.service_ID)
        player_mode: PlayerMode = Settings.get_player_mode(clz.service_ID)
        return player_mode

    @classmethod
    def update_voice_path(cls, phrase: Phrase) -> None:
        if not phrase.is_lang_territory_set():
            locale: str = phrase.language  # IETF format
            _, kodi_locale, _, ietf_lang = SettingsHelper.get_kodi_locale_info()
            voice: str = Settings.get_voice(cls.service_ID)
            if voice is None or voice == '':
                voice = kodi_locale
            else:
                ietf_lang: langcodes.Language = langcodes.get(voice)
            # cls._logger.debug(f'orig Phrase locale: {locale}')
            if locale is None:
                locale = kodi_locale
            # cls._logger.debug(f'locale: {locale}')
            ietf_lang: langcodes.Language
            phrase.set_lang_dir(ietf_lang.language)
            phrase.set_territory_dir(ietf_lang.territory.lower())
        return

    def runCommand(self, phrase: Phrase) -> bool:
        clz = type(self)
        # Caching is ALWAYS used here, otherwise the delay would be maddening.
        # Therefore, this is primarily called when the voice file is NOT in the
        # cache. In this case it is also ONLY called by the background thread
        # in SeedCache.
        # It can also be called by the TTS engine during configuration. In this case
        # it is okay if it is a little slow. -
        #
        try:
            clz.update_voice_path(phrase)
            attempts: int = 25  # Waits up to about 2.5 seconds
            while (not phrase.cache_path_exists() and phrase.is_download_pending() and
                   attempts > 0):
                if phrase.cache_path_exists():
                    break
                Monitor.exception_on_abort(timeout=0.1)
                attempts -= 1

            if not phrase.cache_path_exists():
                clz._logger.debug(f'Phrase: {phrase.get_text()} not yet downloaded')

            if not phrase.is_download_pending and not phrase.cache_path_exists():
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
                # generate voice in cache for the future.
                # Ignore result, don't wait
                generator: GoogleSpeechGenerator = GoogleSpeechGenerator()
                generator.generate_speech(tmp_phrase, timeout=1.0)
        except ExpiredException:
            return False

        return phrase.cache_path_exists()

    def get_cached_voice_file(self, phrase: Phrase,
                              generate_voice: bool = True) -> bool:
        """
        Assumes that cache is used. Normally missing voiced files is placed in
        the cache by an earlier step, but can be initiated here as well.

        Very similar to runCommand, except that the cached files are expected
        to be sent to a slave player, or some other player than can play a sound
        file.
        :param phrase: Contains the text to be voiced as wll as the path that it
                       is or will be located.
        :param generate_voice: If true, then wait a bit to generate the speech
                               file.
        :return: True if the voice file was handed to a player, otherwise False
        """
        clz = type(self)

        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        try:
            self.get_voice_cache().get_path_to_voice_file(phrase,
                                                          use_cache=Settings.is_use_cache())
            if not phrase.cache_path_exists():
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
                generator: GoogleSpeechGenerator = GoogleSpeechGenerator()

                # Blocks a max of timeout seconds. Generator continues past
                # timeout so the file will be in the cache for the next time

                generator.generate_speech(tmp_phrase, timeout=1.0)
            try:
                attempts: int = 10
                while not phrase.cache_path_exists():
                    attempts -= 1
                    if attempts <= 0:
                        break
                    Monitor.exception_on_abort(timeout=0.5)
            except AbortException as e:
                reraise(*sys.exc_info())
            except Exception:
                clz._logger.exception('')

        except ExpiredException:
            pass
        return phrase.cache_path_exists()

    def runCommandAndPipe(self, phrase: Phrase) -> BinaryIO:
        clz = type(self)

        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        audio_pipe = None
        byte_stream: BinaryIO | None = None
        try:
            clz.update_voice_path(phrase)
            self.get_voice_cache().get_path_to_voice_file(phrase,
                                                          use_cache=Settings.is_use_cache())
            if not phrase.cache_path_exists():
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
                # Can use eSpeak as a backup in case generator is not fast enough,
                # however internet speeds (at least around here) are fast enough.
                # If this presents a problem, this code can be re-enabled.
                #
                # espeak_engine: ESpeakTTSBackend =\
                #     BaseServices.getService(SettingsProperties.ESPEAK_ID)
                # if not espeak_engine.initialized:
                #     espeak_engine.init()

                # espeak_engine.say_phrase(phrase)
                # generate voice in cache for the future.
                # Ignore result, don't wait
                generator: GoogleSpeechGenerator = GoogleSpeechGenerator()
                generator.generate_speech(tmp_phrase, timeout=1.0)
            try:
                attempts: int = 10
                while not phrase.cache_path_exists():
                    attempts -= 1
                    if attempts <= 0:
                        break
                    Monitor.exception_on_abort(timeout=0.5)
                    # byte_stream = io.open(phrase.get_cache_path(), 'br')
                if attempts >= 0:
                    byte_stream = phrase.get_cache_path().open(mode='br')
            except AbortException as e:
                reraise(*sys.exc_info())
            except FileNotFoundError:
                clz._logger.debug(f'File not found: {phrase.get_cache_path()}')
                byte_stream = None
            except Exception:
                clz._logger.exception('')
                byte_stream = None

        except ExpiredException:
            pass
        return byte_stream

    def seed_text_cache(self, phrases: PhraseList) -> None:
        """
        Provides means to generate voice files before actually needed. Currently
        called by worker_thread to get a bit of a head-start on the normal path.
        (Probably does not help much). Also, called by disabled code which
        :param phrases:
        :return:
        """

        clz = type(self)
        try:
            # We don't care whether it is too late to say this text.
            clz._logger.debug(f'Here')
            phrases = phrases.clone(check_expired=False)
            for phrase in phrases:
                if Settings.is_use_cache():
                    GoogleTTSEngine.update_voice_path(phrase)
                    self.voice_cache.get_path_to_voice_file(phrase, use_cache=True)
                    if not phrase.cache_path_exists():
                        text_to_voice: str = phrase.get_text()
                        voice_file_path: pathlib.Path = phrase.get_cache_path()
                        clz._logger.debug_extra_verbose(f'PHRASE Text {text_to_voice}')
                        rc: int = 0
                        try:
                            # Should only get here if voiced file (.wav, .mp3,
                            # etc.) was NOT
                            # found. We might see a pre-existing .txt file which means
                            # that
                            # the download failed. To prevent multiple downloads,
                            # wait a day
                            # before retrying the download.

                            voice_text_file: pathlib.Path | None = None
                            voice_text_file = voice_file_path.with_suffix('.txt')
                            try:
                                if os.path.isfile(voice_text_file):
                                    os.unlink(voice_text_file)

                                with open(voice_text_file, 'wt', encoding='utf-8') as f:
                                    f.write(text_to_voice)
                            except Exception as e:
                                if clz._logger.isEnabledFor(ERROR):
                                    clz._logger.error(
                                            f'Failed to save voiced text file: '
                                            f'{voice_text_file} Exception: {str(e)}')
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                        'Failed to download voice: {}'.format(str(e)))
        except Exception as e:
            clz._logger.exception('')
        clz._logger.debug(f'Leaving')

    def update(self):
        pass

    def close(self):
        # self._close()
        pass

    def _close(self):
        # self.stop()
        # super()._close()
        pass

    def _stop(self):
        """
        Stop producing current audio. Originates from KodiPlayerMonitor
        :return:
        """
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose('stop')

    @classmethod
    def get_speech_generator(cls) -> GoogleSpeechGenerator:
        return GoogleSpeechGenerator()

    @classmethod
    def has_speech_generator(cls) -> bool:
        return True

    sample_phrases: Dict[str, int] = {
        'de_de.would_you_like_to_switch_to_this_language': 24132,
        'de_de.lang': 123,
    }

    @classmethod
    def voice_native_name_of_lang(cls, iso_639_1: str,
                                  gender: str | None = None) -> PhraseList:
        phrases: PhraseList = PhraseList()
        lang_info: List[str] = SampleLangPhrases.langs.get(iso_639_1)
        if lang_info is not None:
            phrase: Phrase = Phrase(text=lang_info[1], language=iso_639_1,
                                    gender=gender, voice=None)
            phrases.append(phrase)

        return phrases

    @classmethod
    def settingList(cls, setting: str,
                    *args) -> Tuple[List[Choice], str]:
        """
        Gets the possible specified setting values in same representation
        as stored in settings.xml (not translate). Sorting/translating done
        in UI.

        :param setting: name of the setting
        :param args: Not used
        :return:
        """
        if setting == SettingsProperties.LANGUAGE:
            # Returns list of languages and value of closest match to current
            # locale
            cls.LangInfo.load_lang_info()
            # Make language info for this engine known to settings.
            cls.LangInfo.load_global_lang_info()

            kodi_lang: str = xbmc.getLanguage(xbmc.ISO_639_2)
            kodi_lang_2: str = xbmc.getLanguage(xbmc.ISO_639_1)
            cls._logger.debug(f'lang: {kodi_lang} lang_2: {kodi_lang_2}')
            # LangInfo.initialized = True
            # Get current process' language_code i.e. en-us
            default_locale = Constants.LOCALE.lower().replace('_', '-')

            # GoogleData.country_code_country_tld # Dict[str, Tuple[str, str]]
            #                          ISO3166-1, <google tld>, <country name>
            """
            The lang_variants table returns the different country codes that support
            a given language. The country codes are 3166-1 two letter codes and the
            language codes are ISO 639-1
            """

            # GoogleData.lang_variants # Dict[str, List[str]]

            longest_match = -1
            default_lang = default_locale[0:2]
            idx = 0
            languages: List[Choice] = []
            locale_ids: List[str] = cls.LangInfo.get_locales()
            # Sort by locale so that we have the shortest locales listed first
            # i.e. 'en" before 'en-us'
            for locale_id in sorted(locale_ids):
                lower_lang = locale_id.lower()
                if longest_match == -1:
                    if lower_lang.startswith(default_lang):
                        longest_match = idx
                if lower_lang.startswith(default_locale):
                    longest_match = idx
                choice: Choice
                # lang_info: LangInfo = LangInfo.get(locale_id)
                locale_msg: Message = Languages.locale_msg_map.get(locale_id)
                if locale_msg is None:
                    choice = Choice(locale_id, locale_id, choice_index=idx)
                else:
                    choice = Choice(Messages.get_msg(locale_msg),
                                    locale_id, choice_index=idx)
                languages.append(choice)
                idx += 1

            # Now, convert index to index of default_setting

            default_setting = ''
            if longest_match > 0:
                default_setting = languages[longest_match].value

            return languages, default_setting

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            default_player: str = cls.get_setting_default(SettingsProperties.PLAYER)
            player_ids: List[Choice] = []
            return player_ids, default_player

    @classmethod
    def get_default_language(cls) -> str:
        languages: List[str]
        default_lang: str
        languages: List[Tuple[str, str]]  # lang_id, locale_id
        languages, default_lang = cls.settingList(SettingsProperties.LANGUAGE)
        return default_lang

    @classmethod
    def get_voice(cls) -> str:
        voice: str = Settings.get_voice(cls.engine_id)
        return voice

    @classmethod
    def getLanguage(cls) -> str:
        """
        Gets the current locale ex: en-us

        :return:
        """
        language: str = Settings.get_language(cls.engine_id)
        languages: List[Tuple[str, str]]  # lang_id, locale_id
        languages, default_lang = cls.settingList(SettingsProperties.LANGUAGE)
        language = default_lang
        # language_validator: StringValidator
        # language_validator = cls.get_validator(cls.service_ID,
        #                                        property_id=SettingsProperties.LANGUAGE)
        # language = language_validator.get_tts_value()
        return language

    @classmethod
    def getPitch(cls) -> float:
        """
        Pitch is not settable on Google TTS

        :return:
        """


    @classmethod
    def getGender(cls) -> str:
        gender = 'female'
        return gender

    @classmethod
    def getAPIKey(cls) -> str:
        return cls.getSetting(SettingsProperties.API_KEY)

    @staticmethod
    def available() -> bool:
        available: bool = True
        try:
            default_lang: str = GoogleTTSEngine.get_default_language()
            GoogleTTSEngine._logger.debug(f'default_lang: {default_lang}')
        except Exception:
            available = False

        engine_output_formats: List[str]
        engine_output_formats = SoundCapabilities.get_output_formats(
                GoogleTTSEngine.service_ID)
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER, consumer_formats=[SoundCapabilities.MP3],
                producer_formats=[])
        if len(candidates) == 0:
            available = False
        return available
