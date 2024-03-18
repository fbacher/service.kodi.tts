# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os
import pathlib
import re
import sys
import tempfile

import gtts
from backends.ispeech_generator import ISpeechGenerator
from common import *

from backends import base
from backends.audio.sound_capabilties import SoundCapabilities
from backends.google_data import GoogleData
from backends.players.iplayer import IPlayer
from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (ConstraintsValidator, NumericValidator,
                                          StringValidator)
from cache.voicecache import VoiceCache
from common.base_services import BaseServices
from common.constants import Constants, ReturnCode
from common.exceptions import ExpiredException
from common.kodi_player_monitor import KodiPlayerMonitor
from common.logger import *
from common.logger import BasicLogger
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList, PhraseUtils
from common.setting_constants import Backends, Mode
from common.settings import Settings
from gtts import gTTS, gTTSError, lang
from utils.util import runInThread

module_logger = BasicLogger.get_module_logger(module_path=__file__)
PUNCTUATION_PATTERN = re.compile(r'([.,:])', re.DOTALL)


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


class LanguageInfo:

    lang_info_map: Dict[str, 'LanguageInfo'] = {}
    initialized: bool = False

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
    def get(cls, locale_id: str) -> 'LanguageInfo':
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


class GoogleSpeechGenerator(ISpeechGenerator):
    RESPONSIVE_VOICE_URL: Final[
        str] = "http://responsivevoice.org/responsivevoice/getvoice.php"
    MAXIMUM_PHRASE_LENGTH: Final[int] = 200

    _logger: BasicLogger = None

    def __init__(self) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        self.download_results: Results = Results()

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
        # Disable expiration checks. We are doing this in background. Results
        # are cached for next time

        clz = type(self)
        Monitor.exception_on_abort(timeout=0.0)
        max_phrase_length: int | None
        max_phrase_length = SettingsMap.get_service_property(GoogleTTSEngine.service_ID,
                                                             Constants.MAX_PHRASE_LENGTH)
        if max_phrase_length is None:
            max_phrase_length = 10000  # Essentially no limit
        self.set_phrase(phrase)
        phrase_chunks: PhraseList = PhraseUtils.split_into_chunks(phrase,
                                                                  max_phrase_length)
        unchecked_phrase_chunks: PhraseList = phrase_chunks.clone(check_expired=False)
        runInThread(self._generate_speech, name='download_speech', delay=0.0,
                    phrase_chunks=unchecked_phrase_chunks, original_phrase=phrase,
                    timeout=timeout)
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
        try:
            # The passed in phrase_chunks, are actually chunks of a phrase. Therefore
            # we concatenate the voiced text from each chunk to produce one
            # sound file. This phrase list has expiration disabled.

            phrase_chunks = kwargs.get('phrase_chunks', None)
            if phrase_chunks is None or len(phrase_chunks) == 0:
                self.set_rc(ReturnCode.NO_PHRASES)
                self.set_finished()
                return

            original_phrase = kwargs.get('original_phrase', None)
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
            rc2, _ = VoiceCache.create_sound_file(cache_path,
                                                  create_dir_only=True)
            if rc2 != 0:
                if clz._logger.isEnabledFor(ERROR):
                    clz._logger.error(f'Failed to create cache directory '
                                      f'{cache_path.parent}')
                self.set_rc(ReturnCode.CALL_FAILED)
                self.set_finished()
                return

            language: str = GoogleTTSEngine.getLanguage()
            gender: str = GoogleTTSEngine.getGender()
            pitch: str = GoogleTTSEngine.getPitch_str()  # hard coded. Let
            # player decide
            speed: str = GoogleTTSEngine.getApiSpeed()  # Also hard coded
            # value for 1x speed
            volume: str = GoogleTTSEngine.getEngineVolume_str()
            service: str = GoogleTTSEngine.getVoice()
            api_volume: str = volume  # volume
            api_speed = speed
            api_pitch: str = pitch
            temp_file: pathlib.Path | None = None
            with tempfile.NamedTemporaryFile(mode='w+b', buffering=-1,
                                             suffix=cache_path.suffix,
                                             prefix=cache_path.stem,
                                             dir=cache_path.parent,
                                             delete=False) as sound_file:
                # each 'phrase' is a chunk from one, longer phrase. The chunks
                # are small enough for gTTS to handle. We concatenate the results
                # from the phrase_chunks to the same file.
                temp_file = pathlib.Path(sound_file.name)
                phrase_chunk: Phrase = None
                for phrase_chunk in phrase_chunks:
                    try:
                        Monitor.exception_on_abort()
                        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_verbose(f'phrase: '
                                                      f'{phrase_chunk.get_text()}')

                        my_gtts: MyGTTS = MyGTTS(phrase_chunk, lang=language)
                        # gtts.save(phrase.get_cache_path())
                        #     gTTSError – When there’s an error with the API request.
                        # gtts.stream() # Streams bytes
                        my_gtts.write_to_fp(sound_file)
                        clz._logger.debug(f'Wrote cache_file fragment')
                    except AbortException:
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
                                  f'{str(temp_file)}')
            if self.get_rc() == ReturnCode.OK:
                try:
                    if temp_file.exists() and temp_file.stat().st_size > 0:
                        temp_file.rename(cache_path)
                        original_phrase.set_exists(True)
                        clz._logger.debug(f'cache_file is: {str(cache_path)}')
                    else:
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

    def __init__(self, phrase: Phrase, lang: str = 'en-gb') -> None:
        """
        :param self:
        :param phrase:
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
        lang_country = lang.split('-')
        country_code: str = ''
        lang_code = 'en'
        if len(lang_country) == 2:
            lang_code = lang_country[0]
            country_code = lang_country[1]

        tld: Tuple[str, str]
        tld = GoogleData.country_code_country_tld[country_code]
        if tld is not None and len(tld) == 2:
            tld = tld[0]
        else:
            tld = ''
        super().__init__(phrase.get_text(),
                         lang=lang_code,
                         slow=False,
                         lang_check=True,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)

        # self.simple_cmd: SimpleRunCommand = None
        self.f = False
        if not clz._initialized:
            BaseServices().register(self)
            clz._initialized = True

    def init(self) -> None:
        clz = type(self)
        super().init()
        self.update()

    def getMode(self) -> Mode:
        clz = type(self)
        player: IPlayer = self.get_player(self.service_ID)
        if clz.getSetting(SettingsProperties.PIPE):
            return Mode.PIPE
        else:
            return Mode.FILEOUT

    def runCommand(self, phrase: Phrase) -> bool:
        clz = type(self)
        # Caching is ALWAYS used here, otherwise the delay would be maddening.
        # Therefore, this is only called when the voice file is NOT in the
        # cache. It is also ONLY called by the background thread in SeedCache.
        try:
            attempts: int = 25
            while (not phrase.exists() and phrase.is_download_pending() and
                   attempts > 0):
                if phrase.exists():
                    break
                Monitor.exception_on_abort(timeout=0.1)
                attempts -= 1

            if not phrase.exists():
                clz._logger.debug(f'Phrase: {phrase.get_text()} not yet downloaded')

            if not phrase.is_download_pending and not phrase.exists():
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
                # generate voice in cache for the future.
                # Ignore result, don't wait
                generator: GoogleSpeechGenerator = GoogleSpeechGenerator()
                generator.generate_speech(tmp_phrase, timeout=1.0)
        except ExpiredException:
            return False

        return phrase.exists()

    def runCommandAndPipe(self, phrase: Phrase) -> BinaryIO:
        clz = type(self)

        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        audio_pipe = None
        byte_stream: BinaryIO | None = None
        try:
            VoiceCache.get_path_to_voice_file(phrase, use_cache=Settings.is_use_cache())
            if not phrase.exists():
                tmp_phrase: Phrase = phrase.clone(check_expired=False)
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
                while not phrase.get_cache_path().exists():
                    attempts -= 1
                    if attempts <= 0:
                        break
                    Monitor.exception_on_abort(timeout=0.5)
                    # byte_stream = io.open(phrase.get_cache_path(), 'br')
                if attempts >= 0:
                    byte_stream = phrase.get_cache_path().open(mode='br')
            except AbortException as e:
                reraise(*sys.exc_info())
            except Exception:
                clz._logger.exception('')
                byte_stream = None

        except ExpiredException:
            pass
        # the following a geared towards Mplayer. Assumption is that only adjust
        # volume in player, other settings in engine.

        # volume_db: float = clz.get_volume_db()  # -12 .. 12
        return byte_stream

    def seed_text_cache(self, phrases: PhraseList) -> None:
        # For engines that are expensive, it can be beneficial to cache the voice
        # files. In addition, by saving text to the cache that is not yet
        # voiced, then a background process can generate speech so the cache
        # gets built more quickly

        clz = type(self)
        try:
            # We don't care whether it is too late to say this text.
            clz._logger.debug(f'Here')
            phrases = phrases.clone(check_expired=False)
            for phrase in phrases:
                if Settings.is_use_cache():
                    VoiceCache.get_path_to_voice_file(phrase, use_cache=True)
                    if not phrase.exists():
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

    @classmethod
    def settingList(cls, setting: str, *args) -> List[str] | List[Tuple[str, str]] | Tuple[
        List[str], str] | Tuple[List[Tuple[str, str]], str]:
        """
        Gets the possible specified setting values in same representation
        as stored in settings.xml (not translated). Sorting/translating done
        in UI.

        :param setting: name of the setting
        :param args: Not used
        :return:
        """
        if setting == SettingsProperties.LANGUAGE:
            # Returns list of languages and value of closest match to current
            # locale

            if not LanguageInfo.initialized:
                lang_map = gtts.lang.tts_langs()
                '''
                gtts.lang.tts_langs()[source]

                Languages Google Text-to-Speech supports.
        
                Returns:
        
                A dictionary of the type { ‘<lang>’: ‘<name>’}
        
                Where <lang> is an IETF language tag such as en or zh-TW, and <name>
                 is the full English name of the language, such as English or Chinese (
                 Mandarin/Taiwan).
                
                Return type:
                
                dict
                
                The dictionary returned combines languages from two origins:
                - Languages fetched from Google Translate (pre-generated in gtts.langs)
                - Languages that are undocumented variations that were observed to work 
                  and present different dialects or accents.
                  
                Also, experimental country-code 
                '''
                #                <locale>   <lang_id> <country_id>, <google_domain>
                locale_map: Dict[str, Tuple[str, str, str]]
                tmp_lang_ids = lang_map.keys()  # en, zh-TW, etc
                lang_ids: List[str] = list(tmp_lang_ids)
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
                    lang_info: LanguageInfo
                    lang_info = LanguageInfo(locale_id, lang_code, country_code,
                                             locale_id, country_name, tld, )

            # LanguageInfo.initialized = True
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
            languages: List[Tuple[str, str]] = []
            locale_ids: List[str] = LanguageInfo.get_locales()
            # Sort by locale so that we have shortest locales listed first
            # i.e. 'en" before 'en-us'
            for locale_id in sorted(locale_ids):
                lower_lang = locale_id.lower()
                if longest_match == -1:
                    if lower_lang.startswith(default_lang):
                        longest_match = idx
                # elif lower_lang.startswith(default_lang_country):
                #     longest_match = idx
                if lower_lang.startswith(default_locale):
                    longest_match = idx

                lang_info: LanguageInfo = LanguageInfo.get(locale_id)
                if lang_info is None:
                    entry = (locale_id, locale_id)
                else:
                    entry = (lang_info.get_language_name(),
                             locale_id)  # Display value, setting_value
                languages.append(entry)
                idx += 1

            # Now, convert index to index of default_setting

            default_setting = ''
            if longest_match > 0:
                default_setting = languages[longest_match][1]

            return languages, default_setting

            '''
            elif setting == SettingsProperties.GENDER:
                current_locale = cls.getLanguage()
                voices = cls.voices_by_locale_map.get(current_locale)
    
                genders = set()
                if voices is not None:
                    for voice_name, voice_id, gender_id in voices:
                        genders.add(gender_id)
    
                return list(genders)
    
            elif setting == SettingsProperties.VOICE:
                current_locale = cls.getLanguage()
                voices = cls.voices_by_locale_map.get(current_locale)
    
                voice_ids: List[Tuple[str, str]] = list()
                if voices is not None:
                    for voice_name, voice_id, gender_id in voices:
                        voice_name: str
                        voice_id: str
    
                        # TODO: translate voice_id
                        voice_ids.append((voice_name, voice_id))
    
                return list(voice_ids)
            '''

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            default_player: str = cls.get_setting_default(SettingsProperties.PLAYER)
            player_ids: List[str] = []
            return player_ids, default_player

    @classmethod
    def get_default_language(cls) -> str:
        languages: List[str]
        default_lang: str
        languages: List[Tuple[str, str]]  # lang_id, locale_id
        languages, default_lang = cls.settingList(SettingsProperties.LANGUAGE)
        return default_lang

    # Intercept simply for testing purposes: to disable bypass
    # of voicecache during config to avoid hammering remote
    # vender service.
    #
    # TODO: Remove on ship

    @classmethod
    def setSetting(cls, key, value):
        changed = super().setSetting(key, value)
        VoiceCache.for_debug_setting_changed()
        return changed

 

    @classmethod
    def getEngineVolume_str(cls) -> str:
        volume_validator: NumericValidator
        volume_validator = cls.get_validator(cls.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume: int = volume_validator.get_value()
        return str(volume)

    @classmethod
    def getVoice(cls) -> str:
        voice = cls.getSetting(SettingsProperties.VOICE)
        return ''

        if voice is None:
            lang = cls.voices_by_locale_map.get(cls.getLanguage())
            if lang is not None:
                voice = lang[0][1]
        voice = ''
        return voice

    @classmethod
    def getLanguage(cls) -> str:
        """
        Gets the current locale ex: en-us

        :return:
        """
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
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        pitch_validator: ConstraintsValidator
        pitch_validator = cls.get_validator(cls.service_ID,
                                            property_id=SettingsProperties.PITCH)
        if Settings.is_use_cache():
            pitch = pitch_validator.default_value
        else:
            pitch: float = pitch_validator.get_tts_value()
        return pitch

    @classmethod
    def getPitch_str(cls) -> str:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        # TODO: Solve this differently!!!!

        # pitch: float = cls.getPitch()
        # return '{:.2f}'.format(pitch)
        return '50'

    @classmethod
    def getSpeed(cls) -> float:
        # Native ResponsiveVoice speed is 1 .. 100, with default of 50,
        # Since Responsive voice always requires a player, and caching is
        # a practical necessity, a fixed setting of 50 is used with Responsive Voice
        # and leave it to the player to adjust speed.
        #
        # Kodi TTS uses a speed of +0.25 .. 1 .. +4.0
        # 0.25 is 1/4 speed and 4.0 is 4x speed
        #
        # This speed is represented as a setting as in integer by multiplying
        # by 100.
        #
        speed_validator: NumericValidator
        speed_validator = cls.get_validator(cls.service_ID,
                                            property_id=SettingsProperties.SPEED)
        speed: float
        speed = speed_validator.get_value()
        return speed

    @classmethod
    def getApiSpeed(cls) -> str:
        speed: float = cls.getSpeed()
        # Leave it to the player to adjust speed
        return "50"

    @classmethod
    def getGender(cls) -> str:
        gender = 'female'
        return gender

    @classmethod
    def getAPIKey(cls) -> str:
        return cls.getSetting(SettingsProperties.API_KEY)

    # All voices are empty strings
    # def setVoice(self, voice):
    #    self.voice = voice

    @staticmethod
    def available() -> bool:
        engine_output_formats: List[str]
        engine_output_formats = SoundCapabilities.get_output_formats(
                GoogleTTSEngine.service_ID)
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER, consumer_formats=[SoundCapabilities.MP3],
                producer_formats=[])
        if len(candidates) > 0:
            return True
