# coding=utf-8
import logging

import gtts

from common import *
# from common.get import *
from gtts import gTTS, lang
from test.google_data import GoogleData

from test.google import LanguageInfo, SpeechGenerator


class GttsTestDriver:

    _logger: logging.Logger = None

    @classmethod
    def run_test(cls, lang_code: str, phrase: str) -> None:
        logging.basicConfig(filename='/home/fbacher/.kodi/temp/google.log',
                            level=logging.DEBUG)
        print(f'cls._logger: {cls._logger}')
        if cls._logger is None:
            cls._logger = logging.getLogger(cls.__name__)
            cls._logger.setLevel(logging.DEBUG)
            cls._logger.debug('debug log level')
            print(f'cls._logger: {cls._logger}')
        try:
            cls.initialize()
            countries: Dict[LanguageInfo, LanguageInfo] = LanguageInfo.get_country_variants(lang_code)
            country: LanguageInfo
            for country in countries:
                SpeechGenerator.generate_speech(phrase, country)
        except Exception:
            cls._logger.exception('')

    @classmethod
    def initialize(cls):
        try:
            cls._logger.debug(f'LanguageInfo.initialized: {LanguageInfo.initialized}')
            if not LanguageInfo.initialized:
                cls._logger.debug(f'Initializing LangInfo')
                lang_map = gtts.lang.tts_langs()

                #                <locale>   <lang_id> <country_id>, <google_domain>
                locale_map: Dict[str, Tuple[str, str, str]]
                tmp_lang_ids = lang_map.keys() # en, zh-TW, etc
                extra_locales = sorted(GoogleData.get_locales())
                for locale_id in extra_locales:
                    lang_country = locale_id.split('-')
                    cls._logger.debug(f'extra_locales lang_country: {lang_country}')
                    if len(lang_country) == 2:
                        lang_code = lang_country[0]
                        country_code = lang_country[1]
                    else:
                        lang_code = lang_country
                        country_code = lang_country
                    lang_name: str = lang_map.get(lang_code, locale_id)
                    cls._logger.debug(f'lang_name: {lang_name} lang_code: {lang_code} '
                                      f'locale_id: {locale_id}')
                    result = GoogleData.country_code_country_tld.get(country_code)
                    if result is None:
                        print(f'No TLD for {country_code}.')
                        result = 'com', country_code
                    if len(result) != 2:
                        print(f'Missing TLD/country code info: result: {result}')
                        result = 'com', country_code
                    tld, country_name = result
                    lang_info: LanguageInfo
                    lang_info = LanguageInfo(locale_id, lang_code, country_code,
                                             locale_id, country_name, tld, )

                # Get current process' language_code i.e. en-us
            default_locale = 'en-us'

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
            languages = []
            locale_ids: List[str] = LanguageInfo.get_locales()
            # Sort by locale so that we have shortest locales listed first
            # i.e. 'en" before 'en-us'
            for locale_id in sorted(locale_ids):
                lower_lang = locale_id.lower()
                if longest_match == -1:
                    if lower_lang.startswith(default_lang):
                        longest_match = idx
                if lower_lang.startswith(default_locale):
                    longest_match = idx

                lang_info: LanguageInfo = LanguageInfo.get(locale_id)
                if lang_info is None:
                    entry = (locale_id, locale_id)
                else:
                    entry = (lang_info.get_language_name(), locale_id)
                languages.append(entry)
                idx += 1

            # Now, convert index to index of default_setting

            default_setting = ''
            if longest_match > 0:
                default_setting = languages[longest_match][1]

            return languages, default_setting
        except Exception:
            cls._logger.exception('')
        LanguageInfo.initialized = True
