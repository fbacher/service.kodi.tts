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
from backends.transcoders.trans import TransCode
from common import *

from backends import base
from backends.audio.sound_capabilities import SoundCapabilities
from backends.google_data import GoogleData
from backends.players.iplayer import IPlayer
from backends.settings.service_types import EngineType, Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from cache.voicecache import VoiceCache
from cache.common_types import CacheEntryInfo
from common.base_services import BaseServices
from common.constants import Constants, ReturnCode
from common.debug import Debug
from common.exceptions import ExpiredException
from common.kodi_player_monitor import KodiPlayerMonitor
from common.lang_phrases import SampleLangPhrases
from common.logger import *
from common.message_ids import MessageId
from common.messages import Message, Messages
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList, PhraseUtils
from common.setting_constants import AudioType, Backends, Converters, Genders, PlayerMode
from common.settings import Settings
import langcodes
from gtts import gTTS, gTTSError, lang
from langcodes import LanguageTagError
from utils.util import runInThread
import xbmc

from windowNavigation.choice import Choice

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


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
        self.download_results: Results = Results()
        self.voice_cache: VoiceCache = VoiceCache(GoogleTTSEngine.service_ID)

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
            MY_LOGGER.debug(f'Phrase empty')
            self.set_rc(ReturnCode.OK)
            self.set_finished()
            return self.download_results

        phrase_chunks: PhraseList = PhraseUtils.split_into_chunks(phrase,
                                                                  max_phrase_length)
        unchecked_phrase_chunks: PhraseList = phrase_chunks.clone(check_expired=False)
        runInThread(self._generate_speech, name='dwnldGoo', delay=0.0,
                    phrase_chunks=unchecked_phrase_chunks, original_phrase=phrase,
                    timeout=timeout, gender=phrase.gender)

        max_wait: int = int(timeout / 0.1)
        while max_wait > 0:
            Monitor.exception_on_abort(timeout=0.1)
            max_wait -= 1
            if phrase.cache_path_exists():  # Background process started elsewhere may finish
                break
            if (self.get_rc() <= ReturnCode.MINOR_SAVE_FAIL or
                    KodiPlayerMonitor.instance().isPlaying()):
                MY_LOGGER.debug(f'generate_speech exit rc: {self.get_rc().name}  '
                                f'stop: {KodiPlayerMonitor.instance().isPlaying()}')
                break
        return self.download_results

    def _generate_speech(self, **kwargs) -> None:
        """
            Does the real work of downloading the voiced text.

            DOES NOT check for expired phrases since the download is expensive.
            GenerateSpeech invokes this in its own thread, allowing
            GenerateSpeech to time-out and report an ExpiredException, or
            a timeout failure. Meanwhile this thread should download the
            message and put into the cache.
        :param kwargs:
        :return:
        """
        # Break long texts into 250 char chunks so that they can be downloaded.
        # Concatenate returned binary voice files together and return
        clz = type(self)
        self.set_rc(ReturnCode.OK)
        text_file_path: pathlib.Path | None = None
        phrase_chunks: PhraseList | None = None
        original_phrase: Phrase | None = None
        lang_code: str | None = None
        country_code: str | None = None
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
        MY_LOGGER.debug(f'locale_id: {locale_id} lang_code: {lang_code} language: '
                        f'{langcodes.Language.get(locale_id)}')
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
            MY_LOGGER.debug(f'phrase to download: {original_phrase} '
                            f'path: {original_phrase.get_cache_path(check_expired=False)}')
            Monitor.exception_on_abort()
            if original_phrase.cache_path_exists(check_expired=False):
                self.set_rc(ReturnCode.OK)
                self.set_finished()
                return  # Nothing to do

        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            self.set_finished()
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            self.set_rc(ReturnCode.CALL_FAILED)
            self.set_finished()
            return

        cache_path: pathlib.Path | None = None
        try:
            cache_path = original_phrase.get_cache_path(check_expired=False)
            rc2: int
            rc2, _ = self.voice_cache.create_sound_file(cache_path,
                                                        create_dir_only=True)
            if rc2 != 0:
                if MY_LOGGER.isEnabledFor(ERROR):
                    MY_LOGGER.error(f'Failed to create cache directory '
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
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'phrase: '
                                              f'{phrase_chunk.get_text()}')

                        MY_LOGGER.debug(f'GTTS lang: {lang_code} '
                                        f'terr: {country_code} tld: {tld}')
                        my_gtts: MyGTTS = MyGTTS(phrase_chunk, lang_code=lang_code,
                                                 country_code=country_code,
                                                 tld=tld)
                        # gtts.save(phrase.get_cache_path())
                        #     gTTSError – When there’s an error with the API request.
                        # gtts.stream() # Streams bytes
                        my_gtts.write_to_fp(sound_file)
                        MY_LOGGER.debug(f'Wrote cache_file fragment')
                    except AbortException:
                        sound_file.close()
                        pathlib.Path(sound_file.name).unlink(missing_ok=True)
                        self.set_rc(ReturnCode.ABORT)
                        self.set_finished()
                        reraise(*sys.exc_info())
                    except TypeError as e:
                        MY_LOGGER.exception('')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                    except ExpiredException:
                        MY_LOGGER.exception(f'{phrase_chunks}')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                    except gTTSError as e:
                        MY_LOGGER.exception(f'gTTSError')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                    except IOError as e:
                        MY_LOGGER.exception(f'Error processing phrase: '
                                              f'{phrase_chunk.get_text()}')
                        MY_LOGGER.error(f'Error writing to temp file:'
                                          f' {str(temp_file)}')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                    except Exception as e:
                        MY_LOGGER.exception('')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                MY_LOGGER.debug(f'Finished with loop writing temp file: '
                                  f'{str(temp_file)} size: {temp_file.stat().st_size}')
            if self.get_rc() == ReturnCode.OK:
                try:
                    if temp_file.exists() and temp_file.stat().st_size > 100:
                        temp_file.rename(cache_path)
                        original_phrase.set_exists(True, check_expired=False)
                        MY_LOGGER.debug(f'cache_file is: {str(cache_path)}')
                    else:
                        if temp_file.exists():
                            temp_file.unlink(True)
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.set_finished()
                except ExpiredException:
                    MY_LOGGER.exception(f'{phrase_chunks}')
                    self.set_rc(ReturnCode.DOWNLOAD)
                    self.set_finished()
                except AbortException as e:
                    reraise(*sys.exc_info())
                except Exception as e:
                    MY_LOGGER.exception('')
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
            MY_LOGGER.exception(f'{phrase_chunks}')
            self.set_finished()
            self.set_rc(ReturnCode.DOWNLOAD)

        except Exception as e:
            MY_LOGGER.exception('')
            if MY_LOGGER.isEnabledFor(ERROR):
                MY_LOGGER.error('Failed to download voice: {}'.format(str(e)))
            self.set_finished()
            self.set_rc(ReturnCode.DOWNLOAD)
        MY_LOGGER.debug(f'exit _generate_speech')
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
        if data is not None and len(data) == 2:
            tld = data[0]
        MY_LOGGER.debug(f'lang: {lang_code} country: {country_code} '
                        f'data: {data} tld: {tld}' )
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


class LangInfo:
    """
    Manages the language choices for gTTS.
    """

    lang_info_map: Dict[str, ForwardRef('LangInfo')] = {}
    initialized: bool = False
    global_lang_initalized: bool = False

    '''
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
    '''
    '''
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
    '''

    @classmethod
    def load_languages(cls):
        """
        Get all supported languages from GTTS. Using 'langcodes', convert
        them into standard IETF format, get translated names, etc.. Finally,
        hand off the entries to Kodi TTS.

        :return:
        """
        MY_LOGGER.debug(f'initalized: {cls.initialized}')
        if not cls.initialized:
            cls.initialized = True
            lang_map: Dict[str, str] = gtts.lang.tts_langs()

            """
              Only the keys are of interest. The key is usually a simple
              language code, but can be lang-territory.
              The value is simple an English translation of the key. 
              langcodes gives us the translation for many languages.

            The dictionary returned combines languages from two origins:
              - Languages fetched from Google Translate (pre-generated in gtts.langs)
              - Languages that are undocumented variations that were observed to work 
                and present different dialects or accents.
            """
            # Convert to langcodes
            ietf_langs: List[langcodes.Language] = []
            for gtts_lang in lang_map.keys():
                #  MY_LOGGER.debug(f'gtts_lang: {gtts_lang}')
                gtts_lang: str
                ietf_lang: langcodes.Language
                try:
                    ietf_lang = langcodes.Language.get(gtts_lang)
                    ietf_langs.append(ietf_lang)
                    #  MY_LOGGER.debug(f'ietf_langs added {ietf_lang}')
                except AbortException as e:
                    reraise(*sys.exc_info())
                except LanguageTagError:
                    MY_LOGGER.exception('')

            """
            Get an informal list of language variants for each
            language. For example, 'en' (english) is spoken in (at least)
            the following territories:
              ['ag', 'au', 'bw', 'ca', 'dk', 'gb', 'hk', 'ie', 'il', 'in', 
               'ng', 'nz', 'ph', 'sc', 'sg', 'us', 'za', 'zm', 'zw']
            """
            extra_locales: Dict[str, str] = GoogleData.get_locales()
            # Again, we only care about the key, which is a lang-territory code.
            # The value is an English description

            ietf_lang_territories: List[langcodes.Language] = []
            for gtts_lang_territory in extra_locales.keys():
                #  MY_LOGGER.debug(f'gtts_lang_territory: {gtts_lang_territory}')
                gtts_lang_territory: str
                ietf_lang_terr: langcodes.Language
                try:
                    ietf_lang_terr = langcodes.Language.get(gtts_lang_territory)
                    ietf_lang_territories.append(ietf_lang_terr)
                    # pt-BR
                    # MY_LOGGER.debug(f'adding {ietf_lang_terr} to ietf_lang_territories')
                except AbortException as e:
                    reraise(*sys.exc_info())
                except LanguageTagError:
                    MY_LOGGER.exception('')

            """
            Now for getting this all together. 
              - Use the ietf_langs as the authoritative list of languages
                supported by GTTS.
              - Create langcode instances for each ietf_lang, extra_locale.
              - Create combined langcode list from the two above where 
              - the language is in common but the territory is not.
              - Finally, create LanguageInfo instances for KodiTTS that 
                have the results.
            """

            # Use a map[<lang_code>, Dict[<langcode>, None]] for the combined
            # set of language variants for each lang_code. Second Dict
            # has None value because it is being used as a set.
            lang_variants: Dict[str, Dict[str, None]] = {}
            # Make sure the primary language has an entry ('en')
            ietf_lang: langcodes.Language
            for ietf_lang in ietf_lang_territories:
                #  MY_LOGGER.debug(f'ietf_lang: {ietf_lang}')
                lang_code: str = ietf_lang.language
                variants: Dict[str, None] = lang_variants.get(lang_code)
                if variants is None:
                    variants = {}
                    lang_variants[lang_code] = None

            # Now, that primary lang added, add the variants (en-us, en-gb...)

            #  ietf_langs: List[langcodes.Language]
            ietf_lang_territories: List[langcodes.Language]
            lang_variants: Dict[str, Dict[str, None]]
            ietf_lang: langcodes.Language
            for ietf_lang in ietf_lang_territories:
                lang_code: str = ietf_lang.language
                # variants enforces langcodes.Language being unique
                variants: Dict[str, None] = lang_variants.get(lang_code)
                locale_id: str = ietf_lang.to_tag()  # Mixed case
                territory: str = ietf_lang.territory.lower()
                # MY_LOGGER.debug(f'lang-territory: {ietf_lang.to_tag()}')
                voice_name: str = locale_id
                try:
                    voice_name = langcodes.Language.get(locale_id).display_name()
                except AbortException as e:
                    reraise(*sys.exc_info())
                except:
                    pass

                voice_id: str = locale_id.lower()
                engine_name_msg_id: MessageId = MessageId.ENGINE_GOOGLE

                LanguageInfo.add_language(engine_id=GoogleTTSEngine.engine_id,
                                          language_id=lang_code,
                                          country_id=territory,
                                          ietf=ietf_lang,
                                          region_id='',  # Not used by Google
                                          gender=Genders.UNKNOWN,
                                          voice=voice_name,
                                          engine_lang_id=locale_id,
                                          engine_voice_id=voice_id,
                                          engine_name_msg_id=engine_name_msg_id,
                                          engine_quality=4,
                                          voice_quality=-1)


class GoogleTTSEngine(base.SimpleTTSBackend):
    ID: str = Backends.GOOGLE_ID
    engine_id: str = Backends.GOOGLE_ID
    service_ID: str = Services.GOOGLE_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    displayName = 'GoogleTTS'

    _logger: BasicLogger = None
    # lang_map: Dict[str, str] = None # IETF_lang_name: display_name
    _initialized: bool = False

    @classmethod
    def load_languages(cls) -> None:
        """
        Determines the languages supported by GoogleTTS and converts them
        into a format that Kodi TTS likes

        :return:
        """
        LangInfo.load_languages()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)

        # self.simple_cmd: SimpleRunCommand = None
        self.f = False
        self.voice_cache: VoiceCache = VoiceCache(service_id=GoogleTTSEngine.service_ID)

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
        """
        If a language is specified for this phrase, then modify any
        cache path to reflect the chosen language and territory.
        :param phrase:
        :return:
        """
        if Settings.is_use_cache() and not phrase.is_lang_territory_set():
            locale: str = phrase.language  # IETF format
            _, kodi_locale, _, ietf_lang = LanguageInfo.get_kodi_locale_info()
            voice: str = Settings.get_voice(cls.service_ID)
            if voice is None or voice == '':
                voice = kodi_locale
            else:
                ietf_lang: langcodes.Language = langcodes.get(voice)
            # MY_LOGGER.debug(f'orig Phrase locale: {locale}')
            if locale is None:
                locale = kodi_locale
            # MY_LOGGER.debug(f'locale: {locale}')
            ietf_lang: langcodes.Language
            phrase.set_lang_dir(ietf_lang.language)
            if ietf_lang.territory is not None:
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
                MY_LOGGER.debug(f'Phrase: {phrase.get_text()} not yet downloaded')

            if not phrase.is_download_pending and not phrase.cache_path_exists():
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
                # generate voice in cache for the future.
                # Ignore result, don't wait
                generator: GoogleSpeechGenerator = GoogleSpeechGenerator()
                generator.generate_speech(tmp_phrase, timeout=1.0)
        except AbortException as e:
            reraise(*sys.exc_info())
        except ExpiredException:
            reraise(*sys.exc_info())

        return phrase.cache_path_exists()

    def get_cached_voice_file(self, phrase: Phrase,
                              generate_voice: bool = True) -> bool:
        """
        Assumes that cache is used. Normally missing voiced files are placed in
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
            result: CacheEntryInfo
            result = self.get_voice_cache().get_path_to_voice_file(phrase,
                                                          use_cache=Settings.is_use_cache())
            if not result.audio_exists:
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
            except ExpiredException:
                reraise(*sys.exc_info())
            except Exception:
                MY_LOGGER.exception('')
        except ExpiredException:
            reraise(*sys.exc_info())
        return phrase.cache_path_exists()
        '''
        cache_entry_exists: bool = phrase.cache_path_exists()

        # Support for running with NO ENGINE nor PLAYER using limited pre-generated
        # cache. The intent is to provide enough TTS so the user can configure
        # to use an engine and player.
        force_wave: bool = False
        if not force_wave or not cache_entry_exists:
            return cache_entry_exists
        # Convert .mp3 files into .wav and save in NO_ENGINE engine's cache
        no_engine_voice_cache: VoiceCache = VoiceCache(EngineType.NO_ENGINE.value)
        wave_phrase: Phrase = phrase.clone(check_expired=False)
        no_engine_cache_path: pathlib.Path
        cache_info: CacheEntryInfo
        wave_phrase.set_territory_dir('')
        cache_info = no_engine_voice_cache.get_path_to_voice_file(wave_phrase,
                                                                  use_cache=True)
        if not cache_info.audio_exists:
            mp3_file: pathlib.Path = phrase.get_cache_path()
            wave_file = cache_info.current_audio_path
            # trans_id: str = Settings.get_converter(self.engine_id)
            trans_id: str = Converters.LAME
            MY_LOGGER.debug(f'service_id: {self.engine_id} trans_id: {trans_id}')
            success = TransCode.transcode(trans_id=trans_id,
                                          input_path=mp3_file,
                                          output_path=wave_file,
                                          remove_input=False)
            if success:
                phrase.text_exists(check_expired=False)
            MY_LOGGER.debug(f'success: {success} wave_file: {wave_file} mp3: {mp3_file}')
            return success
        '''

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
            result: CacheEntryInfo
            result = self.get_voice_cache().get_path_to_voice_file(phrase,
                                                          use_cache=Settings.is_use_cache())
            if not result.audio_exists:
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
                MY_LOGGER.debug(f'File not found: {phrase.get_cache_path()}')
                byte_stream = None
            except ExpiredException:
                reraise(*sys.exc_info())
            except Exception:
                MY_LOGGER.exception('')
                byte_stream = None

        except ExpiredException:
            reraise(*sys.exc_info())
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
            MY_LOGGER.debug(f'Here')
            phrases = phrases.clone(check_expired=False)
            for phrase in phrases:
                phrase: Phrase
                if Settings.is_use_cache():
                    GoogleTTSEngine.update_voice_path(phrase)
                    result = CacheEntryInfo
                    result = self.voice_cache.get_path_to_voice_file(phrase, use_cache=True)
                    if not result.audio_exists:
                        text_to_voice: str = phrase.get_text()
                        voice_file_path: result.current_audio_path
                        MY_LOGGER.debug_xv(f'PHRASE Text {text_to_voice}')
                        rc: int = 0
                        try:
                            # Should only get here if voiced file (.wav, .mp3,
                            # etc.) was NOT found.
                            voice_text_file: pathlib.Path | None = None
                            voice_text_file = voice_file_path.with_suffix('.txt')
                            try:
                                if os.path.isfile(voice_text_file):
                                    os.unlink(voice_text_file)
                                with open(voice_text_file, 'wt',
                                          encoding='utf-8') as f:
                                    f.write(text_to_voice)
                            except Exception as e:
                                if MY_LOGGER.isEnabledFor(ERROR):
                                    MY_LOGGER.error(
                                            f'Failed to save text file: '
                                            f'{voice_text_file} Exception: {str(e)}')
                        except Exception as e:
                            if MY_LOGGER.isEnabledFor(ERROR):
                                MY_LOGGER.error(f'Failed to download voice: {e}')
        except AbortException as e:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        MY_LOGGER.debug(f'Leaving')

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
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v('stop')

    @classmethod
    def get_speech_generator(cls) -> GoogleSpeechGenerator:
        return GoogleSpeechGenerator()

    @classmethod
    def has_speech_generator(cls) -> bool:
        return True

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

            cls.load_languages()
            MY_LOGGER.debug(f'Who uses this?')
            Debug.dump_current_thread()

            value: Tuple[List[Choice], int]
            value = SettingsHelper.get_language_choices(cls.service_ID,
                                                        get_best_match=True)
            choices: List[Choice] = value[0]
            best: int = value[1]
            default_setting: str = choices[best].lang_info.locale.lower()
            return choices, default_setting

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            default_player: str = cls.get_setting_default(SettingsProperties.PLAYER)
            player_ids: List[Choice] = []
            return player_ids, default_player

    @classmethod
    def get_default_language(cls) -> str:
        value: Tuple[List[Choice], int]
        value = SettingsHelper.get_language_choices(cls.service_ID,
                                                    get_best_match=True)
        choices: List[Choice] = value[0]
        best: int = value[1]
        MY_LOGGER.debug(f'choices: {choices} best: {best}'
                        f' best_choice: {choices[best]}')
        default_lang: str = choices[best].lang_info.locale.lower()
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
        '''
        Building language information references other engines which are not
        yet configured. Do this later, or reorganize so that other engines
        are not queried during bootstrap.
        
        try:
            default_lang: str = GoogleTTSEngine.get_default_language()
            MY_LOGGER.debug(f'default_lang: {default_lang}')
        except AbortException as e:
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
            available = False
        '''

        engine_output_formats: List[str]
        engine_output_formats = SoundCapabilities.get_output_formats(
                GoogleTTSEngine.service_ID)
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER, consumer_formats=[AudioType.MP3],
                producer_formats=[])
        if len(candidates) == 0:
            MY_LOGGER.debug(f'No Sound Candidates')
            available = False
        return available
