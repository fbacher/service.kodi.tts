# -*- coding: utf-8 -*-
import hashlib
import logging
import pathlib

import regex

from gtts import gTTS, gTTSError

# from common.constants import ReturnCode
# from common.exceptions import ExpiredException
# from common.logger import *
# from common.monitor import Monitor
from common.typing import *

from test.google_data import GoogleData

PUNCTUATION_PATTERN = regex.compile(r'([.,:])', regex.DOTALL)


class LanguageInfo:

    _logger: logging.Logger = None
    lang_info_map: Dict[str, 'LanguageInfo'] = {}
    entries_by_language_code: Dict[str, Dict['LanguageInfo', 'LanguageInfo']] = {}
    initialized: bool = False

    def __init__(self, locale_id: str, language_code: str, country_code: str,
                 language_name: str, country_name: str, google_tld: str) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = logging.getLogger('LanguageInfo')

        clz._logger.debug(f'locale_id: {locale_id} language_code: {language_code}')
        clz._logger.debug(f'country_code: {country_code} language_name: {language_name}')
        clz._logger.debug(f'country_name: {country_name} google_tld: {google_tld}')
        self.locale_id: str = locale_id
        self.language_code: str = language_code
        self.country_code: str = country_code
        self.language_name: str = language_name
        self.country_name: str = country_name
        self.google_tld: str = google_tld
        clz.lang_info_map[locale_id] = self
        country_variants: Dict['LanguageInfo', 'LanguageInfo']
        country_variants = clz.entries_by_language_code.setdefault(language_code, {})
        country_variants[self] = self

    @classmethod
    def get(cls, locale_id: str) -> 'LanguageInfo':
        return cls.lang_info_map.get(locale_id)

    @classmethod
    def get_country_variants(cls, lang_code: str) -> Dict['LanguageInfo', 'LanguageInfo']:
        return cls.entries_by_language_code[lang_code]

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


class SpeechGenerator:
    RESPONSIVE_VOICE_URL: Final[
        str] = "http://responsivevoice.org/responsivevoice/getvoice.php"
    MAXIMUM_PHRASE_LENGTH: Final[int] = 200

    _logger: logging.Logger = logging.getLogger('SpeechGenerator')

    @classmethod
    def get_hash(cls, text_to_voice: str) -> str:
        hash_value: str = hashlib.md5(
                text_to_voice.encode('UTF-8')).hexdigest()
        return hash_value

    @classmethod
    def generate_speech(cls, phrase: str, country: LanguageInfo) -> None:
        try:
            file_hash: str = cls.get_hash(phrase)
            lang: str = country.get_language_code()
            locale_id: str = country.get_locale_id()
            tld: str = country.get_google_tld()
            text_file_path: pathlib.Path = None
            path_prefix: pathlib.Path = pathlib.Path(f'/tmp/google_test/{lang}')
            text_file_path = path_prefix / f'{file_hash}.txt'
            mp3_path: pathlib.Path = path_prefix / f'{locale_id}_{tld}/{file_hash}.mp3'
            mp3_path.parent.mkdir(mode=0o777, parents=True, exist_ok=True)
            with text_file_path.open('wt') as f:
                f.write(phrase)

            with mp3_path.open('wb') as sound_file:
                try:
                    # Monitor.exception_on_abort()
                    # if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                    #     cls._logger.debug_verbose(f'phrase: '
                    #                               f'{phrase}')

                    gtts: MyGTTS = MyGTTS(phrase, locale=locale_id)
                    gtts.write_to_fp(sound_file)
                    cls._logger.debug(f'Wrote cache_file fragment')
                except TypeError as e:
                    cls._logger.exception('')
                # except ExpiredException:
                #    # cls._logger.exception('')
                #    pass
                except gTTSError as e:
                    print(f'gTTSError {e}')
                    pass
                except IOError  as e:
                    cls._logger.exception(f'Error processing phrase: '
                                      f'{phrase}')
                    cls._logger.error(f'Error writing to cache file:'
                                      f' {str(mp3_path)}')
                    print(f'IOError: {e}')
                    try:
                        mp3_path.unlink(True)
                    except Exception as e2:
                        pass
                        #     cls._logger.exception('Can not delete '
                        #                           f' {str(mp3_path)}')
                except Exception as e:
                    print(f'Exception {e}')
                    pass

            cls._logger.debug(f'Finished with loop writing cache_file: '
                              f'{mp3_path}')
        # except AbortException:
        #     reraise(*sys.exc_info())
        # except ExpiredException:
        #     cls._logger.exception('')
        except Exception as e:
            cls._logger.error('Failed to download voice: {}'.format(str(e)))
            print(f'Exception {e}')
        cls._logger.debug(f'exit download_speech')
        return None


class MyGTTS(gTTS):


    _logger: logging.Logger | None = None

    def __init__(self, phrase: str, locale: str = 'en-gb') -> None:
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
        clz = type(self)
        if clz._logger is None:
            clz._logger = logging.getLogger(clz.__name__)
        lang_country = locale.split('-')
        country_code: str = ''
        lang_code = 'en'
        if len(lang_country) == 2:
            lang_code = lang_country[0]
            country_code = lang_country[1]

        country_tld_codes: Tuple[str, str]
        country_tld_codes = GoogleData.country_code_country_tld[country_code]
        tld: str = ''
        if country_tld_codes is not None and len(country_tld_codes) == 2:
            tld = country_tld_codes[0]

        super().__init__(phrase,
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
