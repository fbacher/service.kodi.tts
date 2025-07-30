# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys

import gtts
import langcodes
from backends import base
from backends.engines.google_downloader import MyGTTS
from backends.engines.speech_generator import SpeechGenerator
from backends.google_data import GoogleData
from backends.ispeech_generator import ISpeechGenerator
from backends.players.iplayer import IPlayer
from backends.settings.language_info import LanguageInfo
from backends.settings.service_types import ServiceID, ServiceKey, Services, ServiceType
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_helper import SettingsHelper
from cache.common_types import CacheEntryInfo
from cache.cache_file_state import CacheFileState
from cache.voicecache import VoiceCache
from common import *
from common.base_services import BaseServices
from common.constants import Constants
from common.debug import Debug
from common.exceptions import ExpiredException
from common.logger import *
from common.message_ids import MessageId
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import Backends, Genders, PlayerMode
from common.settings import Settings
from gtts import gTTS, lang
from langcodes import LanguageTagError
from windowNavigation.choice import Choice

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class LangInfo:
    """
    Manages the language choices for gTTS.
    """

    lang_info_map: Dict[str, ForwardRef('LangInfo')] = {}
    initialized: bool = False
    global_lang_initalized: bool = False

    @classmethod
    def load_languages(cls):
        """
        Get all supported languages from GTTS. Using 'langcodes', convert
        them into standard IETF format, get translated names, etc.... Finally,
        hand off the entries to Kodi TTS.

        :return:
        """
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

                LanguageInfo.add_language(engine_key=GoogleTTSEngine.service_key,
                                          language_id=lang_code,
                                          country_id=territory,
                                          ietf=ietf_lang,
                                          region_id='',  # Not used by Google
                                          gender=Genders.ANY,
                                          voice=voice_name,
                                          engine_lang_id=locale_id,
                                          engine_voice_id=voice_id,
                                          engine_name_msg_id=engine_name_msg_id,
                                          engine_quality=4,
                                          voice_quality=-1)


class GoogleTTSEngine(base.SimpleTTSBackend):
    ID: str = Backends.GOOGLE_ID
    engine_id: str = Backends.GOOGLE_ID
    service_id: str = Services.GOOGLE_ID
    service_type: ServiceType = ServiceType.ENGINE
    service_key: ServiceID = ServiceKey.GOOGLE_KEY
    MAX_PHRASE_KEY: ServiceID = service_key.with_prop(SettingProp.MAX_PHRASE_LENGTH)
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

        self.f = False
        self.voice_cache: VoiceCache = VoiceCache(service_key=GoogleTTSEngine.service_key)

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
        player: IPlayer = self.get_player(self.service_key)
        player_mode: PlayerMode = Settings.get_player_mode(clz.service_key)
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
            voice_id: str = Settings.get_voice(cls.service_key)
            #  lang_info.engine_voice_id
            kodi_locale: str = Constants.LOCALE
            if voice_id is None or voice_id == '':
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug('Fix Settings.get_voice to use kodi_locale by'
                                    ' default')
            #     voice_id = kodi_locale
            # else:
            #    ietf_lang: langcodes.Language = langcodes.get(voice_id)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'orig Phrase locale: {locale}')
            if locale is None:
                locale = kodi_locale
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'locale: {locale}')
            ietf_lang: langcodes.Language = langcodes.Language.get(locale)

            phrase.set_lang_dir(ietf_lang.language)
            phrase.set_voice(voice_id)
            phrase.set_voice_dir(voice_id)
            #  HACK for broken xbmc.getLanguage
            if ietf_lang.territory is None:
                ietf_lang = langcodes.get(voice_id)
            phrase.set_territory_dir(ietf_lang.territory.lower())
        return

    def create_speech_generator(self) -> ISpeechGenerator | None:
        my_gtts: MyGTTS = MyGTTS()
        #  max_phrase_length_key: ServiceID = GoogleTTSEngine.MAX_PHRASE_KEY
        # max_phrase_length: int | None
        # max_phrase_length = Settings.get_max_phrase_length(max_phrase_length_key)
        max_chunk_size: int = gTTS.GOOGLE_TTS_MAX_CHARS

        generator: SpeechGenerator
        generator = SpeechGenerator(engine_instance=self,
                                    downloader=my_gtts,
                                    max_phrase_length=0,
                                    max_chunk_size=max_chunk_size)
        return generator

    def runCommand(self, phrase: Phrase) -> bool:
        clz = type(self)
        # Caching is ALWAYS used here, otherwise the delay would be maddening.
        # Therefore, this is primarily called when the voice file is NOT in the
        # cache. In this case it is also ONLY called by the background thread
        # in SeedCache.
        # It can also be called by the TTS engine during configuration. In this case
        # it is okay if it is a little slow.
        #
        cache_file_state: CacheFileState
        cache_file_state = self.get_cached_voice_file(phrase)
        MY_LOGGER.debug(f'cache_file_state: {cache_file_state} phrase: {phrase}')
        return cache_file_state == CacheFileState.OK

        '''
        try:
            clz.update_voice_path(phrase)
            file_state: CacheFileState = phrase.cache_file_state()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'{phrase.current_state} file_state: {file_state.value} '
                                f'download pending: {phrase.is_download_pending()} ')
            if file_state < CacheFileState.OK:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'phrase file:'
                                    f' {phrase.get_cache_path(check_expired=False)} '
                                    f'exists: '
                                    f'{phrase.get_cache_path(check_expired=False).exists()}')

            if (phrase.is_download_pending()
                    and file_state < CacheFileState.CREATION_INCOMPLETE):
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
                generator: ISpeechGenerator
                generator = self.create_speech_generator()
                # if MY_LOGGER.isEnabledFor(DEBUG):
                #     MY_LOGGER.debug(f'calling generate_speech')
                generator.remote_generate_speech(tmp_phrase, timeout=5.0)
        except AbortException as e:
            reraise(*sys.exc_info())
        except ExpiredException:
            reraise(*sys.exc_info())

        if MY_LOGGER.isEnabledFor(DEBUG) and phrase.cache_file_state != CacheFileState.OK:
            MY_LOGGER.debug(f'cache_file_state: {phrase.cache_file_state()}')
        return phrase.cache_file_state() == CacheFileState.OK
        '''

    def get_cached_voice_file(self, phrase: Phrase,
                              generate_voice: bool = True) -> CacheFileState:
        """
        Return cached file if present. Optionally creates the cache file.

        Very similar to runCommand, except that the cached files are expected
        to be sent to a slave player, or some other player than can play a sound
        file.
        :param phrase: Contains the text to be voiced as wll as the path that it
                       is or will be located.
        :param generate_voice: NOT USED
        :return: True if the voice file was handed to a player, otherwise False
        """
        clz = type(self)
        try:
            clz.update_voice_path(phrase)
            result: CacheEntryInfo
            result = self.get_voice_cache().get_path_to_voice_file(phrase,
                                                       use_cache=Settings.is_use_cache())
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'result: {result}')
            if not result.audio_exists:
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
                generator: ISpeechGenerator
                generator = self.create_speech_generator()

                # Blocks a max of timeout seconds. Generator continues past
                # timeout so the file will be in the cache for the next time

                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'calling remote_generate_speech')
                generator.remote_generate_speech(tmp_phrase, timeout=1.0)
                try:
                    attempts: int = 10
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'cache_file_state: {phrase.cache_file_state()}')
                    while not phrase.cache_file_state() < CacheFileState.OK:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'cache_file_state: {phrase.cache_file_state()}')
                        attempts -= 1
                        if attempts <= 0:
                            if MY_LOGGER.isEnabledFor(DEBUG):
                                MY_LOGGER.debug(f'Timed out')
                            break
                        Monitor.exception_on_abort(timeout=0.1)
                except AbortException as e:
                    reraise(*sys.exc_info())
                except ExpiredException:
                    reraise(*sys.exc_info())
                except Exception:
                    MY_LOGGER.exception('')
        except ExpiredException:
            reraise(*sys.exc_info())
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'cache_file_state: {phrase.cache_file_state()}')
        return phrase.cache_file_state()

    def runCommandAndPipe(self, phrase: Phrase) -> BinaryIO | None:
        """
        TODO: Change to pass a byte-stream back (or into) get_cached_voice_file/generate.
              Do in such a way that the pipe is opened asap to avoid rereading
              cache.
        :param phrase:
        :return:
        """
        clz = type(self)
        cache_file_state: CacheFileState
        cache_file_state = self.get_cached_voice_file(phrase)
        MY_LOGGER.debug(f'cache_file_state: {cache_file_state} phrase: {phrase}')
        if cache_file_state != CacheFileState.OK:
            return None
        byte_stream: BinaryIO | None = None
        byte_stream = phrase.get_cache_path().open(mode='br')
        return byte_stream

        '''
            # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        audio_pipe = None
        byte_stream: BinaryIO | None = None
        try:

            if attempts >= 0:
                byte_stream = phrase.get_cache_path().open(mode='br')
            except AbortException as e:
            reraise(*sys.exc_info())
        except FileNotFoundError:
            if MY_LOGGER.isEnabledFor(DEBUG):
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

        
        try:
            clz.update_voice_path(phrase)
            voice_cache: VoiceCache = self.get_voice_cache()
            result: CacheEntryInfo
            result = voice_cache.get_path_to_voice_file(phrase,
                                                        use_cache=Settings.is_use_cache())
            if not result.audio_exists:
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
                # Can use eSpeak as a backup in case generator is not fast enough,
                # however internet speeds (at least around here) are fast enough.
                # If this presents a problem, this code can be re-enabled.
                #
                # espeak_engine: ESpeakTTSBackend =\
                #     BaseServices.get_service(SettingProp.ESPEAK_ID)
                # if not espeak_engine.initialized:
                #     espeak_engine.init()

                # espeak_engine.say_phrase(phrase)
                # generate voice in cache for the future.
                # Ignore result, don't wait
                generator: ISpeechGenerator
                generator = self.create_speech_generator()
                generator.remote_generate_speech(phrase=tmp_phrase)
            try:
                attempts: int = 10
                while phrase.cache_file_state() < CacheFileState.OK:
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
                if MY_LOGGER.isEnabledFor(DEBUG):
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
        '''

    def seed_text_cache(self, phrases: PhraseList) -> None:
        """
        Provides means to generate voice files before actually needed. Currently
        called by worker_thread to get a bit of a head-start on the normal path.
        (Probably does not help much). Also, called by disabled code which
        :param phrases:
        :return:
        """
        self.get_voice_cache().seed_text_cache(phrases)

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
        if setting == SettingProp.LANGUAGE:
            # Returns list of languages and value of closest match to current
            # locale

            cls.load_languages()
            MY_LOGGER.debug(f'Who uses this?')
            Debug.dump_current_thread()

            value: Tuple[List[Choice], int]
            value = SettingsHelper.get_language_choices(cls.service_key,
                                                        get_best_match=True)
            choices: List[Choice] = value[0]
            best: int = value[1]
            default_setting: str = choices[best].lang_info.locale.lower()
            return choices, default_setting

        elif setting == SettingProp.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            default_player: str = cls.get_setting_default(SettingProp.PLAYER)
            player_ids: List[Choice] = []
            return player_ids, default_player

    @classmethod
    def get_default_language(cls) -> str:
        value: Tuple[List[Choice], int]
        value = SettingsHelper.get_language_choices(cls.service_key,
                                                    get_best_match=True)
        choices: List[Choice] = value[0]
        best: int = value[1]
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'choices: {choices} best: {best}'
                            f' best_choice: {choices[best]}')
        default_lang: str = choices[best].lang_info.locale.lower()
        return default_lang

    @classmethod
    def get_voice(cls) -> str:
        voice: str = Settings.get_voice(cls.service_key)
        return voice

    @classmethod
    def getLanguage(cls) -> str:
        """
        Gets the current locale ex: en-us

        :return:
        """
        language: str = Settings.get_language(cls.service_key)
        languages: List[Tuple[str, str]]  # lang_id, locale_id
        languages, default_lang = cls.settingList(SettingProp.LANGUAGE)
        language = default_lang
        # language_validator: StringValidator
        # language_validator = cls.get_validator(cls.setting_id,
        #                                        setting_id=SettingProp.LANGUAGE)
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
        return cls.getSetting(SettingProp.API_KEY)
