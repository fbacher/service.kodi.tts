# coding=utf-8
from __future__ import annotations


try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

#  from backends.settings.langcodes_wrapper import LangCodesWrapper
from backends.settings.service_unavailable_exception import ServiceUnavailable
from common.constants import Constants
from backends.settings.service_types import ServiceID, ServiceKey, SERVICES_BY_TYPE

"""
   Provides a consistent way to represent the important language
   information provided by the various TTS engines. The goal is to
   be able to let the user choose the TTS engine and language from
   among those available on their platform.
   """

import datetime
from typing import Any, Dict, Final, ForwardRef, List, Tuple

import xbmc

import langcodes

from backends.settings.i_validators import AllowedValue, IStringValidator
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import SettingsMap
from common.base_services import BaseServices
from common.logger import *
from common.message_ids import MessageId
from common.setting_constants import Genders, GenderSettingsMap
from common.settings import Settings

MY_LOGGER = BasicLogger.get_logger(__name__)


class LanguageInfo:
    """
    Language Information is defined at startup, in bootstrap_engines,
    BEFORE the engines are fully defined. During configuration, LanguageInfo
    should only 'inhale' the language information during settings definition
    and not query other engines during this stage.

    """

    initialized: bool = False
    all_languages_loaded: bool = False
    _kodi_locale: str = None
    _locale_label: str = None
    _locale: str = None
    _number_of_entries: int = 0

    KODI_SUPPORTED_LANGS: Final[Dict[str, str]] = {
        "af": "af",
        "am": "am",
        "ar": "ar",
        "ast": "ast",
        "az": "az",
        "be": "be",
        "bg": "bg",
        "bs": "bs",
        "ca": "ca",
        "cs": "cs",
        "cy": "cy",
        "da": "da",
        "de": "de",
        "el": "el",
        "en": "en",
        "eo": "eo",
        "es": "es",
        "et": "et",
        "eu": "eu",
        "fa": "fa",
        "fi": "fi",
        "fil": "fil",
        "fo": "fo",
        "fr": "fr",
        "gl": "gl",
        "he": "he",
        "hi": "hi",
        "hr": "hr",
        "hu": "hu",
        "hy": "hy",
        "id": "id",
        "is": "is",
        "it": "it",
        "ja": "ja",
        "kn": "kn",
        "ko": "ko",
        "lt": "lt",
        "lv": "lv",
        "mi": "mi",
        "mk": "mk",
        "ml": "ml",
        "mn": "mn",
        "ms": "ms",
        "mt": "mt",
        "my": "my",
        "nb": "nb",
        "nl": "nl",
        "os": "os",
        "pl": "pl",
        "pt": "pt",
        "ro": "ro",
        "ru": "ru",
        "si": "si",
        "sk": "sk",
        "sl": "sl",
        "sq": "sq",
        "sr": "sr",
        "sv": "sv",
        "szl": "szl",
        "ta": "ta",
        "te": "te",
        "tg": "tg",
        "th": "th",
        "tr": "tr",
        "uk": "uk",
        "uz": "uz",
        "vi": "vi",
        "zh": "zh",
    }
    """
     The setting_id is used as index for entries_by_engine. Each value 
     is in turn a Dict indexed by a supported langouage family ('en'). The
     value of this second index is every language supported by that engine and
     belonging to that language family (Here, en-us, en-gb, en...) Note that
     there can be more than one language with the same id (one for male and
     another female, for example).
     
         entries_by_engine: key: ServiceID
                            value: Dict[lang_family, List[languageInfo]]
                            lang_family (iso-639-1 or -2 code)
                            List[languageInfo} list of all languages supported by 
                            that engine and language ('en' or 'en-us' and other variants).
    """
    entries_by_engine: Dict[ServiceID, Dict[str, List[ForwardRef('LanguageInfo')]]] = {}
    #  entries_by_language: Dict[str, List[ForwardRef('LanguageInfo')]] = {}

    lang_id_for_lang: Dict[str, int] = {}

    def __init__(self, engine_key: ServiceID,
                 language_id: str,
                 country_id: str,
                 region_id: str,
                 ietf: langcodes.Language,
                 gender: Genders,
                 voice: str,
                 engine_lang_id: str,
                 engine_voice_id: str,
                 engine_name_msg_id: MessageId,
                 engine_quality: int,
                 voice_quality: int,
                 ):
        """

        :param engine_key: Same as ServiceID. Specifies which engine
                          this entry applies to
        :param language_id: iso-639-1 or -2 code (if available)
        :param country_id: iso-1366-1 (2 or three letter) country code,
                           if available.
        :param region_id: Some engines have dialects tailored to a region or
                          city, such as espeak-ng: 'en-gb-scotland' or
                          'en-us-nyc'. This field allows the dialect ('nyc' or
                          'scotland') to be specified.
        :param ietf: langcodes.Language IETF standard object. Useful for getting
                     translate messages for any field that it handles. In particular,
                     the language name.
        :param gender: Specifies the gender, if known
        :param voice: engine specific name of the voice (optional)
        :param engine_quality: 0-5 estimated quality rating (0=least)
        :param voice_quality: 0-5
        :param engine_lang_id: Code that engine may use for the language
        :param engine_voice_id: Code that engine may use for the voice
        :param engine_name_msg_id: msg_id to get translate engine name
        """
        clz = LanguageInfo
        clz._number_of_entries += 1
        if country_id is not None:
            country_id = country_id.lower()
        self.engine_key: ServiceID = engine_key
        self.language_id: str = language_id
        self.country_id: str = country_id
        self.region_id: str = region_id
        self.ietf: langcodes.Language = ietf
        self.gender: Genders = gender
        self.translated_voice: str = voice
        self.engine_lang_id: str = engine_lang_id
        self.engine_voice_id: str = engine_voice_id
        self.engine_name_msg_id: MessageId = engine_name_msg_id
        self.engine_quality: int = engine_quality
        self.voice_quality: int = voice_quality

        #  self.translated_country_name: str | None = None
        self._translated_gender_name: str | None = None
        self._translated_language_name: str | None = None
        self._translated_lang_country_name: str | None = None
        self._translated_engine_name: str | None = None
        self._translated_country_name: str | None = None

        """
            label: Translated label in the format of:
                     f'{display_engine_name:10} '
                     f'{lang_info.translated_country_name:20} / '
                     f'{display_autonym_choice:10} '
                     f'voice:  {voice_name:20}')
            prepare_for_display fills it in
        """
        self.label: str | None = None

        # Add LanguageInfo to the appropriate engines and language groups
        # ('en-us' is part of language group 'en')

        # langs_for_engine: indexed by lang: 'en'
        # Contains all languages for a specific engine

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{self}')
        langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
        langs_for_an_engine = clz.entries_by_engine.get(engine_key)
        if langs_for_an_engine is None:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'No languages for engine {engine_key}')
            langs_for_an_engine = {}
            clz.entries_by_engine[engine_key] = langs_for_an_engine

        lang_family_list: List[ForwardRef('LanguageInfo')]
        engine_specific_langs = langs_for_an_engine.setdefault(language_id, [])
        engine_specific_langs.append(self)  # TODO, put best entry first
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Best entry for engine {engine_key} is {self}')

        """
          Create a second table to look up all languges within a family for
          all engines.
        
            lang_entries: List[ForwardRef('LanguageInfo')]
    
            lang_entries = clz.entries_by_language.get(language_id, None)
            if lang_entries is None:
                lang_entries = []
                clz.entries_by_language[language_id] = lang_entries
            lang_entries.append(self)
        """

    @classmethod
    def add_language(cls,
                     engine_key: ServiceID,
                     language_id: str,
                     country_id: str,
                     region_id: str,
                     ietf: langcodes.Language,
                     gender: Genders,
                     voice: str,
                     engine_lang_id: str,
                     engine_voice_id: str,
                     engine_name_msg_id: MessageId,
                     engine_quality: int,
                     voice_quality: int
                     ) -> None:
        """

        :param engine_key: Specifies which engine this entry applies to
        :param language_id: iso-639-1 or -2 code (if available)
        :param country_id: iso-1366-1 (2 or three letter) country code,
                           if available.
        :param region_id: Some engines have dialects tailored to a region or
                          city, such as espeak-ng: 'en-gb-scotland' or
                          'en-us-nyc'. This field allows the dialect ('nyc' or
                          'scotland') to be specified.
        :param ietf: langcodes.Language IETF standard object. Useful for getting
                     translated messages for any field that it handles. In particular,
                     the language name.
        :param gender: Specifies the gender, if known
        :param voice: engine specific display name of the voice (optional)
        :param engine_quality: 0-5 estimated quality rating (0=least)
        :param voice_quality: 0-5
        :param engine_lang_id: Code that engine may use for the language
        :param engine_voice_id: Code that engine may use for the voice
        :param engine_name_msg_id: msg_id to get translated engine name
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'engine: {engine_key} lang: {language_id} '
                            f'country: {country_id} region: {region_id}')
        if language_id not in cls.KODI_SUPPORTED_LANGS:
            return None
        if country_id is not None:
            country_id = country_id.lower()
        langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
        langs_for_an_engine = cls.entries_by_engine.get(engine_key)
        if langs_for_an_engine is not None:
            engine_specific_langs = langs_for_an_engine.get(language_id)
            if engine_specific_langs is not None:
                engine_specific_langs: List[ForwardRef('LanguageInfo')]
                if engine_specific_langs is not None:
                    for lang_info in engine_specific_langs:
                        if (lang_info.country_id == country_id and
                                lang_info.region_id == region_id and
                                lang_info.gender == gender and
                                lang_info.engine_lang_id == engine_lang_id and
                                lang_info.engine_voice_id == engine_voice_id):
                            if MY_LOGGER.isEnabledFor(DEBUG_V):
                                MY_LOGGER.debug_v(f'Dupe: ignored')
                            return
        '''
        MY_LOGGER.debug(f'setting_id: {setting_id}\n'
                        f'country_id: {country_id}\n'
                        f'region_id: {region_id}\n'
                        f'ietf: {ietf}\n'
                        f'gender: {gender}\n'
                        f'voice: {voice}\n'
                        f'engine_lang_id: {engine_lang_id}\n'
                        f'engine_voice_id: {engine_voice_id}\n'
                        f'engine_quality: {engine_quality}\n'
                        f'voice_quality: {voice_quality}')
        '''
        LanguageInfo(engine_key,
                     language_id,
                     country_id,
                     region_id,
                     ietf,
                     gender,
                     voice,
                     engine_lang_id,
                     engine_voice_id,
                     engine_name_msg_id,
                     engine_quality,
                     voice_quality)

    @classmethod
    def get_entry(cls,
                  engine_key: ServiceID | None = None,
                  engine_voice_id: str | None = None,
                  lang_id: str | None = None) -> ForwardRef('LanguageInfo'):
        """
        Finds the LanguageInfo entry that matches the criteria.
        Any missing arguments will be filled in with current setting values.

        :param engine_key:
        :param engine_voice_id:
        :param lang_id: IETF lang 2 or 3 char language ex: 'en'
        :return:
        """
        cls.get_lang_info()
        # Get closet match to current lang setting, not Kodi's locale

        if engine_key is None:
            engine_key: ServiceID = Settings.get_engine_key()
        if engine_voice_id is None:
            engine_voice_id: str = Settings.get_voice(engine_key)
        if lang_id is None:
            ietf_lang: langcodes.Language
            _, _, _, ietf_lang = LanguageInfo.get_kodi_locale_info()
            lang_id = ietf_lang.language
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{engine_key} voice_id: {engine_voice_id} '
                            f'lang: {lang_id}')
        entries:  Dict[ServiceID, Dict[str, List[ForwardRef('LanguageInfo')]]]
        entries = cls.get_entries(engine_key=engine_key, lang_family=lang_id)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'# entries: {len(entries.keys())} keys:'
                              f' {entries.keys()}')
        if entries is None:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.error(f"Can't find voice entry for: {engine_key} "
                                f"# entries: {cls._number_of_entries}")
            return None

        engine_lang_entries:  Dict[str, List[ForwardRef('LanguageInfo')]] | None
        engine_lang_entries = entries.get(engine_key)
        if engine_lang_entries is None:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.error(f"Can't find voice entry for: {engine_key} "
                                f"# entries: {cls._number_of_entries}")
            return None

        #  MY_LOGGER.debug(f'# engine_lang_entries: {len(engine_lang_entries.keys())} '
        #                    f'keys: {engine_lang_entries.keys()}')

        lang_info: ForwardRef('LanguageInfo')
        territory_entries: List[ForwardRef('LanguageInfo')]

        if lang_id is None:
            for territory_entries in engine_lang_entries.values():
                #  MY_LOGGER.debug(f'# territory_entries: {len(territory_entries)} ')
                for lang_info in territory_entries:
                    #  MY_LOGGER.debug(f'engine_voice_id: {engine_voice_id} '
                    #                    f'lang_info voice: {lang_info.engine_voice_id}')
                    if lang_info.engine_voice_id == engine_voice_id:
                        return lang_info
        else:
            #  MY_LOGGER.debug(f'lang_id is not None')
            entries_for_lang = engine_lang_entries.get(lang_id)
            if entries_for_lang is None:
                #  MY_LOGGER.error(f"Can't find voice entry for language: {lang_id}")
                return None
            for lang_info in entries_for_lang:
                if lang_info.engine_voice_id == engine_voice_id:
                    return lang_info

    @classmethod
    def get_entries(cls, translate: bool = True, ordered: bool = True,
                    engine_key: ServiceID | None = None,
                    lang_family: str | None = None,
                    deep: bool = True
                    ) -> Dict[ServiceID, Dict[str, List[ForwardRef('LanguageInfo')]] | None]:
        """
        Gets language capabilities of all or a single TTS engine.

        :param translate: Translate any fields in BOTH current lang as well
                           as the language of the locale (if they are different)
        :param ordered: Return entries sorted by language
        :param engine_key: If None, then return information for all engines
                       If not None, then return information for the engine
                       identified by 'engine'
        :param lang_family: Limits returned language information to this
                     language family (i.e. 'de'). If None, then returns all
                     families
        :param deep: If True, then return all language info for the given
                    language ('en').
                    If False, then return only one language entry for each
                    supported language ('en') with the closest match to the
                    current Kodi locale.
        :return: Dict indexed by service_key. Values are lists
                 of languages supported by that engine. The list will contain
                 all supported variations of a single language if deep=True,
                 otherwise it will contain (TODO: complete)
        """
        number_of_entries: int = 0
        cls.get_lang_info()
        langs_for_engines: List[Dict[engine_key, List[ForwardRef('LanguageInfo')]]] = []
        langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
        engine_key_arg: ServiceID = engine_key
        from backends.settings.settings_helper import SettingsHelper

        kodi_lang, kodi_locale, kodi_friendly_locale, kodi_language = \
            LanguageInfo.get_kodi_locale_info()
        if engine_key is not None:
            langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
            langs_for_an_engine = cls.entries_by_engine.get(engine_key)
            if langs_for_an_engine is None:
                return_value:  Dict[ServiceID,
                                    Dict[str, List[ForwardRef('LanguageInfo')]] | None]
                return_value = {engine_key: None}
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'engine supports no languages return value:'
                                    f' {return_value}')
                return return_value
            langs_for_engines.append(langs_for_an_engine)
        else:
            # Get language info for EVERY engine
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'entries_by_engine.keys: {cls.entries_by_engine.keys()}')
            for engine_key, langs_for_an_engine in cls.entries_by_engine.items():
                engine_key: ServiceID
                langs_for_engines.append(langs_for_an_engine)
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                for engine_key in cls.entries_by_engine.keys():
                    msg: str = f'langs for {engine_key}'
                    for langs_for_an_engine in cls.entries_by_engine[engine_key].values():
                        msg = f'{msg}\n  {langs_for_an_engine}'
                    MY_LOGGER.debug_xv(msg)

            '''
            if lang_family != '':
                keys_for_lang_family = langs_for_an_engine.keys()
                for key in keys_for_lang_family:
                    if key != lang_family:
                        del keys_for_lang_family[key]
            '''

            # Filter out any languages that we are not interested in
            # Add translated messages and additional detail to each entry
            for langs_for_an_engine in langs_for_engines:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'langs_for_an_engine: engine: {langs_for_an_engine}')
                for lang_family_id, engine_langs_in_family in langs_for_an_engine.items():
                    lang_family_id: str
                    if lang_family is not None and lang_family != lang_family_id:
                        continue
                    engine_langs_in_family: List[ForwardRef('LanguageInfo')]
                    number_of_entries += 1
                    cls.prepare_for_display(translate,
                                            engine_langs_in_family,
                                            lang_family_id,
                                            kodi_lang)

        """
            Only return info caller requested:
            If setting_id specified, then only return info for that one.
            
            entries_by_engine: key: service_key (ServiceType, service_id)
                            value: Dict[lang_family, List[languageInfo]]
                            lang_family (iso-639-1 or -2 code)
                            List[languageInfo} list of all languages supported by 
                            that engine and language ('en' or 'en-us' and other variants).
        """
        # Was this called about a specific Engine?
        if engine_key_arg is not None:
            entry: Dict[str, List[ForwardRef('LanguageInfo')]]
            entry = cls.entries_by_engine.get(engine_key_arg)
            return {engine_key_arg: entry}

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'entries_by_engine.keys: {cls.entries_by_engine.keys()}')
        '''
        for key in cls.entries_by_engine.keys():
            msg: str = f'key: {key} '
            for value in cls.entries_by_engine[key]:
                msg = f'{msg}\n  {value}'
            MY_LOGGER.debug(msg)
        '''
        return cls.entries_by_engine

    @property
    def translated_gender_name(self) -> str:
        if self._translated_gender_name is None:
            msg_id: MessageId = GenderSettingsMap.settings_map.get(
                    self.gender)
            self._translated_gender_name = msg_id.get_msg()
        return self._translated_gender_name

    @property
    def translated_language_name(self) -> str:
        clz = type(self)
        if self._translated_language_name is None:
            kodi_lang: str
            from backends.settings.settings_helper import SettingsHelper

            kodi_lang, _, _, kodi_locale = \
                LanguageInfo.get_kodi_locale_info()
            if Constants.USE_LANGCODES_DATA:
                self._translated_language_name = self.ietf.language_name(
                            language=kodi_lang)
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    xx = clz.get_language_name(self.ietf.to_tag(), kodi_lang)
                    MY_LOGGER.debug_v(f'LANGCODES lang: {self.ietf.to_tag()} '
                                      f'kodi_lang: {kodi_lang} '
                                      f'lang_name: {self._translated_language_name}')
                    MY_LOGGER.debug_v(f'LANGCODES2 lang {self.ietf.to_tag()} '
                                      f'kodi_lang: {kodi_lang} '
                                      f'lang_name: {xx}')
            else:
                self._translated_language_name = clz.get_language_name(self.ietf.to_tag(),
                                                                       kodi_lang)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'LANGCODES lang: {self.ietf.to_tag()} '
                                    f'kodi_lang: {kodi_lang} '
                                    f'lang_name: {self._translated_language_name}')
        return self._translated_language_name

    @classmethod
    def get_translated_language_name(cls, langcode: langcodes.Language) -> str:
        result: str = ''
        kodi_lang, _, _, kodi_locale = LanguageInfo.get_kodi_locale_info()
        if Constants.USE_LANGCODES_DATA:
            result = langcode.language_name()
            result2: str = cls.get_language_name(langcode.to_tag(), kodi_lang)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'LANGCODES langcode: {langcode.language} trans: '
                                  f'{result}')
                MY_LOGGER.debug_v(f'LANGCODES2 langcode: {langcode.language} trans: '
                                  f'{result2}')
        else:
            result: str = cls.get_language_name(langcode.to_tag(), kodi_lang)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'LANGCODES langcode: {langcode.language} trans: '
                                  f'{result}')
        return result

    def get_display_name(self, locale_spec: langcodes) -> str:
        """
        Gets the human readable name for the given locale and translated into
        the current language that kodi is using. Includes langauge and
        territory.
        :param locale_spec:
        :return:
        """
        clz = type(self)
        if Constants.USE_LANGCODES_DATA:
            # Gets the display name for self in locale_spec's language
            # In Kodi TTS you only see language variants of your current Kodi
            # language, so self.ietf.autonym should work just as well, unless
            # there are some situations where different territories give different
            # results (spelling, script).
            result: str = self.ietf.display_name(locale_spec)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'LANGCODES lang_id: {self.ietf.to_tag()} kodi_locale: '
                                  f'{locale_spec} result: {result}')
                # When LANGCODES_DATA is not available, just look up in autonym
                # table. Should generally give the same results.
                result2: str = clz.get_autonym(self.ietf.to_tag())
                MY_LOGGER.debug_v(f'LANGCODES2 lang_id: {self.ietf.to_tag().lower()} '
                                  f'locale_spec: '
                                  f'{locale_spec} result: {result2}')
        else:
            result: str = clz.get_autonym(self.ietf.to_tag())
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'LANGCODES lang_id: {self.ietf.to_tag().lower()} '
                                f'locale_spec: '
                                f'{locale_spec} result: {result}')
        return result

    @classmethod
    def get_formatted_lang(cls, lang: str) -> str:
        """
        Convert the given lang to human-friendly text using Kodi's current locale
        :param lang:
        :return:
        """
        _, _, _, kodi_language = \
            cls.get_kodi_locale_info()
        langcode: langcodes.Language = langcodes.Language.get(lang)
        result: str = ''
        if Constants.USE_LANGCODES_DATA:
            result = langcode.display_name(kodi_language)  # Gets the English name
            #  kodi_lang_code = kodi_language.language
            result2 = cls.get_autonym(lang)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'LANGCODES lang: {lang} {result}')
                MY_LOGGER.debug_v(f'LANGCODES2 lang: {lang} {result2}')
        else:
            """
             To do this properly, need to look up the given lang's locale in a
             map of locale -> display. Further, the map depends upon kodi's locale,
             or at least kodie's lang. Therefore would need two tiered map or
             one map with key: <kodi_lang><lang_locale>.
             
             However, at the momemnt I'm only aware of kodi displaying languages
             that are in the same language (not variant) as Kodi is running, so
             this should mean that autonym would work. 
             """
            #  kodi_lang_code = kodi_language.language
            result = cls.get_autonym(lang)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'LANGCODES lang: {lang} {result}')
        return result

    @property
    def translated_lang_country_name(self) -> str:
        """
        Generates the text for the user friendly country name in kodi's current
        language.
        :return:
        """
        clz = type(self)
        if self._translated_lang_country_name is None:
            kodi_lang, _, _, kodi_locale = LanguageInfo.get_kodi_locale_info()
            if Constants.USE_LANGCODES_DATA:
                self._translated_lang_country_name = (
                  self.ietf.display_name(
                            language=kodi_lang))
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug(f'LANGCODES lang: {self.ietf.to_tag()} display: '
                                    f'{self._translated_lang_country_name}')

                territory: str = self.ietf.territory
                if territory is None:
                    territory = ''
                key: str = f'{kodi_lang}-{territory.lower()}'
                txt = clz.get_country_name(key)
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'LANGCODES2 lang: {key} display: '
                                      f'{txt}')
            else:
                key: str = f'{kodi_lang}-{self.ietf.territory}'
                self._translated_lang_country_name = clz.get_country_name(key)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'LANGCODES lang: {key} display: '
                                    f'{self._translated_lang_country_name}')
        return self._translated_lang_country_name

    @property
    def translated_engine_name(self) -> str:
        if self._translated_engine_name is None:
            if self.engine_name_msg_id is not None:
                self._translated_engine_name = self.engine_name_msg_id.get_msg()
        if self._translated_engine_name is None:
            return ''
        return self._translated_engine_name

    @classmethod
    def get_translated_engine_name(cls, engine_key: ServiceID) -> str:
        trans_name: str = Services(engine_key.service_id).translated_name
        return trans_name

    @property
    def translated_country_name(self) -> str:
        """
        Get the name of the country/territory for self translated for the
        current kodi language.
        """
        clz = type(self)
        if self._translated_country_name is None:
            from backends.settings.settings_helper import SettingsHelper

            kodi_lang, _, _, _ = \
                LanguageInfo.get_kodi_locale_info()
            country_name: str = ''
            if Constants.USE_LANGCODES_DATA:
                self._translated_country_name = self.ietf.territory_name(
                        language=kodi_lang)
                country_name: str = clz.get_country_name(self.ietf.to_tag())
            else:
                # Need to look up the country name in a table instead of using
                # the better LANGCODES_DATA.
                # Normally, Kodi tts displays language information for
                # languages that are in the same family as kodi's language ('en')
                # So, assume that kodi's language setting is not important.
                # This will bite us if the above assumption is incorrect.

                country_name: str = clz.get_country_name(self.ietf.to_tag())
                self._translated_country_name = country_name
            if self._translated_country_name is None:
                self._translated_country_name = ''
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'LANGCODES lang: {self.ietf.to_tag().lower()} '
                                  f'{self._translated_country_name}')
                MY_LOGGER.debug_v(f'LANGCODES2 lang: {self.ietf.to_tag().lower()} '
                                  f'{country_name}')
        return self._translated_country_name

    @property
    def autonym(self) -> str:
        clz = type(self)
        if Constants.USE_LANGCODES_DATA:
            display_autonym_choice: str = self.ietf.autonym()
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                x: str = clz.get_autonym(self.ietf.to_tag())
                MY_LOGGER.debug_v(f'LANGCODES autonym: {self.ietf.to_tag().lower()} '
                                  f'{self.ietf.autonym()}')
                MY_LOGGER.debug_v(f'LANGCODES2 autonym: {self.ietf.to_tag().lower()} {x}')
        else:
            display_autonym_choice: str = clz.get_autonym(self.ietf.to_tag())
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'LANGCODES autonym: {self.ietf.to_tag().lower()} '
                                f'{self.ietf.autonym()}')
        return display_autonym_choice

    @classmethod
    def prepare_for_display(cls, translate: bool,
                            engine_langs_in_family: List[ForwardRef('LanguageInfo')],
                            lang_family_id: str,
                            kodi_lang: str) -> None:
        """
        Translates any fields that require it to the current language.

        Note: Changes are made in-place for the argments.

        :param translate: If False, then this serves as a no-op
        :param engine_langs_in_family: List of languages that the engine calling
        this method supports.
        :param lang_family_id:  The IETF language code
        :param kodi_lang:  Kodi's current IETF language code
        :return: None, the changes are made to the given arguments
        """
        for lang_info in engine_langs_in_family:
            lang_info: ForwardRef('LanguageInfo')
            if translate:
                # Get name of the language in its native language
                display_autonym_choice: str = lang_info.autonym
                # get how close of a match this language is to
                # Kodi's setting

                match_distance: int
                match_distance = langcodes.tag_distance(desired=kodi_lang,
                                                        supported=lang_info.ietf)
                display_engine_name: str = lang_info.translated_engine_name
                voice_name: str = lang_info.translated_voice
                label: str = ''
                if display_autonym_choice != lang_info.translated_country_name:
                    label = (f'{display_engine_name:10} '
                             f'{lang_info.translated_country_name:20} / '
                             f'{display_autonym_choice:10} '
                             f'voice:  {voice_name:20}')
                else:
                    label = (f' {display_engine_name:10} '
                             f'{lang_info.translated_country_name:32}   '
                             f'voice:  {voice_name:20}')
                lang_info.label = label
                #  MY_LOGGER.debug(f'label: {label}')
        return

    @classmethod
    def get_lang_info(cls) -> None:
        if cls.all_languages_loaded:
            return

        avail_engines: List[ServiceID]
        avail_engines = SettingsMap.get_available_services(ServiceType.ENGINE)

        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'get_lang_info engine_keys: {len(avail_engines)}')
        failure: bool = False
        for engine_key in reversed(avail_engines):
            engine_key: ServiceID

            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'getting lang for {engine_key}')
            try:
                new_active_engine = BaseServices.get_service(engine_key)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'active_engine: {new_active_engine}')
                if new_active_engine is None:
                    failure = True
                    continue
                new_active_engine.load_languages()
            except ServiceUnavailable:
                MY_LOGGER.exception(f'Error getting languages from {engine_key}.'
                                    f' Skipping')
            except Exception:
                MY_LOGGER.exception(f'Error getting languages from {engine_key}.'
                                    f' Skipping')
        if not failure:
            cls.all_languages_loaded = True
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Returned from load_languages()')

    @property
    def locale(self) -> str:
        clz = type(self)
        if clz._locale is None:
            clz._locale = self.ietf.to_tag()
        return clz._locale

    @property
    def kodi_locale(self) -> str:
        """
        Gets the ietf language tag for Kodi's current language

        :return: ex: en-GB
        """
        clz = type(self)
        if clz._kodi_locale is not None:
            return clz._kodi_locale
        ietf: langcodes.Language
        _, _, _, ietf = LanguageInfo.get_kodi_locale_info()
        clz._kodi_locale = ietf.to_tag()
        return clz._kodi_locale

    @classmethod
    def get_kodi_locale_info(cls) -> Tuple[str, str, str, langcodes.Language]:
        """
        Retrieves the currently configured Kodi locale in several formats

        :return: returns [kodi_lang, kodi_locale, kodi_friendly_locale_name,
                         langcodes.Language]
        """
        tmp: str = xbmc.getLanguage(xbmc.ISO_639_2)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'xbmc.ISO_639_2: {tmp}')
        kodi_language: langcodes.Language
        kodi_language = langcodes.Language.get(tmp)
        kodi_lang: str = kodi_language.language
        kodi_locale: str = kodi_language.to_tag()
        if Constants.USE_LANGCODES_DATA:
            kodi_friendly_locale_name: str = kodi_language.display_name()
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                x: str = cls.get_language_name(kodi_language.to_tag(), kodi_lang)
                MY_LOGGER.debug_xv(f'LANGCODES display_name '
                                   f'{kodi_language.to_tag().lower()}'
                                   f' {kodi_friendly_locale_name}')
                MY_LOGGER.debug_xv(f'LANGCODES2 display_name '
                                   f'{kodi_language.to_tag().lower()} {x}')
        else:
            kodi_friendly_locale_name: str = cls.get_language_name(kodi_language.to_tag(),
                                                                   kodi_lang)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'LANGCODES display_name {kodi_friendly_locale_name}')
        return kodi_lang, kodi_locale, kodi_friendly_locale_name, kodi_language

    @property
    def locale_label(self) -> str:
        """
        Gets the human-friendly name for self in the current kodi_locale

        :return:
        """
        clz = type(self)
        if clz._locale_label is None:
            if Constants.USE_LANGCODES_DATA:
                clz._locale_label = self.ietf.display_name(self.kodi_locale)
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    xx = clz.get_alt_display_name(self.ietf.to_tag())
                    MY_LOGGER.debug_v(f'LANGCODES kodi_locale {self.kodi_locale} '
                                      f'display_name {clz._locale_label}')
                    MY_LOGGER.debug_v(f'LANGCODES2 kodi_locale {self.kodi_locale}'
                                      f' display_name {xx}')
            else:
                # Need to get self fully displayed (lang + territory) in kodi's
                # language.
                # ASSUME that the lang for both self and kodi language are the
                # SAME since tts does not allow you to choose such a combination.
                clz._locale_label = clz.get_alt_display_name(self.ietf.to_tag())
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'LANGCODES kodi_locale {self.kodi_locale} '
                                    f'display_name {clz._locale_label}')
        return clz._locale_label

    @classmethod
    def init(cls) -> None:
        if not cls.initialized:
            service_key: ServiceID = ServiceKey.ENGINE_KEY
            engine_id_val: IStringValidator
            engine_id_val = SettingsMap.get_validator(service_key)

            entries: List[AllowedValue] = engine_id_val.get_allowed_values()
            for engine_key, enabled in entries:
                engine_key: ServiceID
                enabled: bool
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'service_key: {engine_key} enabled: {enabled}')

    def __eq__(self, other):
        """
        Allow for equality checks. DOES NOT handle hash comparisions (maps)
        :param other:
        :return:
        """
        if isinstance(other, LanguageInfo):
            other: LanguageInfo
            return (self.engine_key == other.engine_key and
                    self.language_id == other.language_id and
                    self.engine_voice_id == other.engine_voice_id)
        return NotImplemented

    def __repr__(self) -> str:
        if not MY_LOGGER.isEnabledFor(DEBUG_V):
            return ''

        field_sep: str = ''  # '{field_sep}'
        engine_key_str: str = f'   engine_key: {self.engine_key}{field_sep}'
        language_id_str: str = f'   language_id: {self.language_id}{field_sep}'
        country_id_str: str = f'   country_id: {self.country_id}{field_sep}'
        region_id_str: str = f'   region_id: {self.region_id}{field_sep}'
        gender_str: str = f'   gender: {self.gender}{field_sep}'
        voice_str: str = f'   voice: {self.translated_voice}{field_sep}'
        engine_lang_id_str: str = f'   engine_lang_id: {self.engine_lang_id}{field_sep}'
        engine_voice_id_str: str = f'   engine_voice_id: {self.engine_voice_id}{field_sep}'
        engine_name_msg_id_str: str = f'   engine_name_msg_id: {self.engine_name_msg_id}{field_sep}'
        engine_quality_str: str = f'   engine_quality: {self.engine_quality}{field_sep}'
        voice_quality_str: str = f'   voice_quality: {self.voice_quality}{field_sep} '
        translated_gender_name_str: str = (f'   translated_gender_name: '
                                           f'{self.translated_gender_name}{field_sep}')
        translated_language_name_str: str = (f'   translated_language_name: '
                                             f'{self.translated_language_name}{field_sep}')
        translated_lang_country_name_str: str = (f'   translated_lang_country_name: '
                                                 f'{self.translated_lang_country_name}{field_sep}')
        translated_engine_name_str: str = (f'   translated_engine_name: '
                                           f'{self.translated_engine_name}{field_sep} ')
        result = (f'{engine_key_str}{language_id_str}{country_id_str}'
                  f'{region_id_str}{engine_lang_id_str}{engine_voice_id_str}'
                  # {gender_str}{voice_str}{engine_lang_id_str}'
                  #  f'{engine_voice_id_str}{engine_name_msg_id_str}'
                  #  f'{engine_quality_str}{voice_quality_str}{translated_gender_name_str}'
                  f'\n{translated_language_name_str}{translated_lang_country_name_str}'
                  f'{translated_engine_name_str}')
        return result

    @classmethod
    def get_autonym(cls, locale_id: str) -> str:
        locale_id = locale_id.lower()
        return AUTONYMS.get(locale_id, f'{locale_id} (no label)')

    @classmethod
    def get_alt_display_name(cls, locale_id: str) -> str:
        locale_id = locale_id.lower()
        return LOCALE_SPEC.get(locale_id, f'{locale_id} (no label)')

    @classmethod
    def  get_language_name(cls, locale_id: str, kodi_lang_id: str) -> str:
        locale_id = locale_id.lower()
        kodi_lang_id: str = kodi_lang_id.lower()[0:2]
        key: str = f'{locale_id}-{kodi_lang_id}'
        return LANGUAGE_NAME_FOR_ID.get(key, f'{key} (no label)')

    @classmethod
    def get_country_name(cls, locale_id: str) -> str:
        locale_id = locale_id.lower()
        return COUNTRY_NAME_FOR_LOCALE_ID.get(locale_id, '')


AUTONYMS: Dict[str, str] = {
    'af'             : 'Afrikaans',
    'am'             : 'አማርኛ',
    'ar'             : 'العربية',
    'az'             : 'azərbaycan',
    'be'             : 'беларуская',
    'bg'             : 'български',
    'bs-ba'          : 'bosanski (Bosna i Hercegovina)',
    'bs'             : 'bosanski',
    'ca-ad'          : 'català (Andorra)',
    'ca'             : 'català',
    'ca-es'          : 'català (Espanya)',
    'ca-fr'          : 'català (França)',
    'ca-it'          : 'català (Itàlia)',
    'cs'             : 'čeština',
    'cs-cz'          : 'čeština (Česko)',
    'cy'             : 'Cymraeg',
    'cy-gb'          : 'Cymraeg (Y Deyrnas Unedig)',
    'da'             : 'dansk',
    'da-dk'          : 'dansk (Danmark)',
    'de-at'          : 'Deutsch (Österreich)',
    'de-be'          : 'Deutsch (Belgien)',
    'de-ch'          : 'Deutsch (Schweiz)',
    'de-de'          : 'Deutsch (Deutschland)',
    'de'             : 'Deutsch',
    'de-it'          : 'Deutsch (Italien)',
    'de-li'          : 'Deutsch (Liechtenstein)',
    'de-lu'          : 'Deutsch (Luxemburg)',
    'el-cy'          : 'Ελληνικά (Κύπρος)',
    'el-gr'          : 'Ελληνικά (Ελλάδα)',
    'el'             : 'Ελληνικά',
    'en-029'         : 'English (Caribbean)',
    'en-ag'          : 'English (Antigua & Barbuda)',
    'en-au'          : 'English (Australia)',
    'en-bw'          : 'English (Botswana)',
    'en-ca'          : 'English (Canada)',
    'en-dk'          : 'English (Denmark)',
    'en-gb'          : 'English (United Kingdom)',
    'en-gb-scotland' : 'English (United Kingdom)',
    'en-gb-x-gbclan' : 'English (United Kingdom)',
    'en-gb-x-gbcwmd' : 'English (United Kingdom)',
    'en-gb-x-rp'     : 'English (United Kingdom)',
    'en-hk'          : 'English (Hong Kong SAR China)',
    'en-ie'          : 'English (Ireland)',
    'en-il'          : 'English (Israel)',
    'en-in'          : 'English (India)',
    'en-ng'          : 'English (Nigeria)',
    'en-nz'          : 'English (New Zealand)',
    'en-ph'          : 'English (Philippines)',
    'en-sc'          : 'English (Seychelles)',
    'en-sg'          : 'English (Singapore)',
    'en-us'          : 'English (United States)',
    'en-za'          : 'English (South Africa)',
    'en-zm'          : 'English (Zambia)',
    'en-zw'          : 'English (Zimbabwe)',
    'eo'             : 'Esperanto',
    'eo-us'          : 'Esperanto (Usono)',
    'es-419'         : 'español (Latinoamérica)',
    'es-ar'          : 'español (Argentina)',
    'es-bo'          : 'español (Bolivia)',
    'es-cl'          : 'español (Chile)',
    'es-co'          : 'español (Colombia)',
    'es-cr'          : 'español (Costa Rica)',
    'es-cu'          : 'español (Cuba)',
    'es-do'          : 'español (República Dominicana)',
    'es-ec'          : 'español (Ecuador)',
    'es-es'          : 'español (España)',
    'es'             : 'español',
    'es-gt'          : 'español (Guatemala)',
    'es-hn'          : 'español (Honduras)',
    'es-mx'          : 'español (México)',
    'es-ni'          : 'español (Nicaragua)',
    'es-pa'          : 'español (Panamá)',
    'es-pe'          : 'español (Perú)',
    'es-pr'          : 'español (Puerto Rico)',
    'es-py'          : 'español (Paraguay)',
    'es-sv'          : 'español (El Salvador)',
    'es-us'          : 'español (Estados Unidos)',
    'es-uy'          : 'español (Uruguay)',
    'es-ve'          : 'español (Venezuela)',
    'et-ee'          : 'eesti (Eesti)',
    'et'             : 'eesti',
    'eu-es'          : 'euskara (Espainia)',
    'eu'             : 'euskara',
    'eu-fr'          : 'euskara (Frantzia)',
    'fa-ir'          : 'فارسی (ایران)',
    'fa-latn'        : 'Persian (Latin)',
    'fa'             : 'فارسی',
    'fi-fi'          : 'suomi (Suomi)',
    'fil-pH'         : 'Filipino (Pilipinas)',
    'fi'             : 'suomi',
    'fo-fo'          : 'føroyskt (Føroyar)',
    'fr-be'          : 'français (Belgique)',
    'fr-ca'          : 'français (Canada)',
    'fr-ch'          : 'français (Suisse)',
    'fr-fr'          : 'français (France)',
    'fr-lu'          : 'français (Luxembourg)',
    'gl-es'          : 'galego (España)',
    'he-il'          : 'עברית (ישראל)',
    'he'             : 'עברית',
    'hi-in'          : 'हिन्दी (भारत)',
    'hi'             : 'हिन्दी',
    'hr-hr'          : 'hrvatski (Hrvatska)',
    'hr'             : 'hrvatski',
    'hu-hu'          : 'magyar (Magyarország)',
    'hu'             : 'magyar',
    'hy-am'          : 'հայերեն (Հայաստան)',
    'hy'             : 'հայերեն',
    'id'             : 'bahasa Indonesia',
    'id-id'          : 'bahasa Indonesia (Indonesia)',
    'is-is'          : 'íslenska (Ísland)',
    'is'             : 'íslenska',
    'it-ch'          : 'italiano (Svizzera)',
    'it'             : 'italiano',
    'it-it'          : 'italiano (Italia)',
    'ja-jp'          : '日本語 (日本)',
    'ja'             : '日本語',
    'kn-in'          : 'ಕನ್ನಡ (ಭಾರತ)',
    'kn'             : 'ಕನ್ನಡ',
    'ko'             : '한국어',
    'ko-kr'          : '한국어 (대한민국)',
    'lt'             : 'lietuvių',
    'lt-lt'          : 'lietuvių (Lietuva)',
    'lv'             : 'latviešu',
    'lv-lv'          : 'latviešu (Latvija)',
    'mi'             : 'Māori',
    'mi-nz'          : 'Māori (Aotearoa)',
    'mk-mk'          : 'македонски (Северна Македонија)',
    'mk'             : 'македонски',
    'ml-in'          : 'മലയാളം (ഇന്ത്യ)',
    'ml'             : 'മലയാളം',
    'mn-mn'          : 'монгол (Монгол)',
    'ms'             : 'bahasa Malaysia',
    'ms-my'          : 'bahasa Malaysia (Malaysia)',
    'mt'             : 'Malti',
    'mt-mt'          : 'Malti (Malta)',
    'my-mm'          : 'မြန်မာ (မြန်မာ)',
    'my'             : 'မြန်မာ',
    'nb-no'          : 'norsk bokmål (Norge)',
    'nb'             : 'norsk bokmål',
    'nl-aw'          : 'Nederlands (Aruba)',
    'nl-be'          : 'Nederlands (België)',
    'nl'             : 'Nederlands',
    'nl-nl'          : 'Nederlands (Nederland)',
    'os-ru'          : 'ирон (Уӕрӕсе)',
    'pl-pl'          : 'polski (Polska)',
    'pl'             : 'polski',
    'pt-br'          : 'português (Brasil)',
    'pt'             : 'português',
    'pt-pt'          : 'português (Portugal)',
    'ro'             : 'română',
    'ro-ro'          : 'română (România)',
    'ru-lv'          : 'русский (Латвия)',
    'ru-ru'          : 'русский (Россия)',
    'ru-ua'          : 'русский (Украина)',
    'ru'             : 'русский',
    'si-lk'          : 'සිංහල (ශ්‍රී ලංකාව)',
    'si'             : 'සිංහල',
    'sk-sk'          : 'slovenčina (Slovensko)',
    'sk'             : 'slovenčina',
    'sl-si'          : 'slovenščina (Slovenija)',
    'sl'             : 'slovenščina',
    'sq-al'          : 'shqip (Shqipëri)',
    'sq-mk'          : 'shqip (Maqedonia e Veriut)',
    'sq'             : 'shqip',
    'sr-me'          : 'српски (Црна Гора)',
    'sr-rs'          : 'српски (Србија)',
    'sr'             : 'српски',
    'sv-fi'          : 'svenska (Finland)',
    'sv-se'          : 'svenska (Sverige)',
    'sv'             : 'svenska',
    'ta-in'          : 'தமிழ் (இந்தியா)',
    'ta-lk'          : 'தமிழ் (இலங்கை)',
    'ta'             : 'தமிழ்',
    'te-in'          : 'తెలుగు (భారతదేశం)',
    'te'             : 'తెలుగు',
    'tg-tj'          : 'тоҷикӣ (Тоҷикистон)',
    'th-th'          : 'ไทย (ไทย)',
    'th'             : 'ไทย',
    'tr-cy'          : 'Türkçe (Kıbrıs)',
    'tr-tr'          : 'Türkçe (Türkiye)',
    'tr'             : 'Türkçe',
    'uk-ua'          : 'українська (Україна)',
    'uk'             : 'українська',
    'uz'             : 'o‘zbek',
    'uz-uz'          : 'o‘zbek (Oʻzbekiston)',
    'vi'             : 'Tiếng Việt',
    'vi-vn'          : 'Tiếng Việt (Việt Nam)',
    'vi-vn-x-central': 'Tiếng Việt (Việt Nam)',
    'vi-vn-x-south'  : 'Tiếng Việt (Việt Nam)',
    'zh-cn'          : '中文（中国）',
    'zh-hk'          : 'Chinese（Hong Kong SAR China）',
    'zh-sg'          : '中文（新加坡）',
    'zh-tw'          : 'Chinese（Taiwan）'
}


"""
LOCALE_SPEC provides a means to lookup the display name for a particular locale
in a particular language family. In other words, if I want to display the user
friendly name for 'en-AG' in English I would look up the value of 'en-AG' from
the table below. We don't have to worry about the language family because Kodi TTS
ONLY lists language variations (en-AG) for a single language (en) 
"""
LOCALE_SPEC: Dict[str, str] = {
    # lang_id is language to display
    # using the current language family (en)
    # locale_spec is the resulting user-friendly name for lang_id in the language family
    'en-ag': 'English (Antigua & Barbuda)',
    'en-au': 'English (Australia)',
    'en-bw': 'English (Botswana)',
    'en-ca': 'English (Canada)',
    'en-dk': 'English (Denmark)',
    'en-gb': 'English (United Kingdom)',
    'en-hk': 'English (Hong Kong SAR China)',
    'en-ie': 'English (Ireland)',
    'en-il': 'English (Israel)',
    'en-in': 'English (India)',
    'en-ng': 'English (Nigeria)',
    'en-nz': 'English (New Zealand)',
    'en-ph': 'English (Philippines)',
    'en-sc': 'English (Seychelles)',
    'en-sg': 'English (Singapore)',
    'en-us': 'English (United States)',
    'en-za': 'English (South Africa)',
    'en-zm': 'English (Zambia)',
    'en-zw': 'English (Zimbabwe)'}

LANGUAGE_NAME_FOR_ID: Dict[str, str] = {
    # The key is <locale_of_language_to_get_name_for>-<current_kodi_lang_id>
    'en-en': 'English',
    'en-us-en': 'English (United States)'
}

COUNTRY_NAME_FOR_LOCALE_ID: Dict[str, str] = {
    """
    For a given language and country code, return the user friendly name of the
    country for the given language. Example, if I want the French user-friendly
    name for 'us' the table key would be: 'fr-us' and the returned value
    would be 'United States', but in French not English.
    """
    'af'             : '',
    'am'             : '',
    'ar'             : '',
    'az'             : '',
    'be'             : '',
    'bg'             : '',
    'bs'             : '',
    'bs-ba'          : 'Bosnia & Herzegovina',
    'ca'             : '',
    'ca-ad'          : 'Andorra',
    'ca-es'          : 'Spain',
    'ca-fr'          : 'France',
    'ca-it'          : 'Italy',
    'cs'             : '',
    'cs-cz'          : 'Czechia',
    'cy'             : '',
    'cy-gb'          : 'United Kingdom',
    'da'             : '',
    'da-dk'          : 'Denmark',
    'de'             : '',
    'de-at'          : 'Austria',
    'de-be'          : 'Belgium',
    'de-ch'          : 'Switzerland',
    'de-de'          : 'Germany',
    'de-it'          : 'Italy',
    'de-li'          : 'Liechtenstein',
    'de-lu'          : 'Luxembourg',
    'el'             : '',
    'el-cy'          : 'Cyprus',
    'el-gr'          : 'Greece',
    'en-029'         : 'Caribbean',
    'en-ag'          : 'Antigua & Barbuda',
    'en-au'          : 'Australia',
    'en-bw'          : 'Botswana',
    'en-ca'          : 'Canada',
    'en-dk'          : 'Denmark',
    'en-gb-scotland' : 'United Kingdom',
    'en-gb'          : 'United Kingdom',
    'en-gb-x-gbclan' : 'United Kingdom',
    'en-gb-x-gbcwmd' : 'United Kingdom',
    'en-gb-x-rp'     : 'United Kingdom',
    'en-hk'          : 'Hong Kong SAR China',
    'en-ie'          : 'Ireland',
    'en-il'          : 'Israel',
    'en-in'          : 'India',
    'en-ng'          : 'Nigeria',
    'en-nz'          : 'New Zealand',
    'en-ph'          : 'Philippines',
    'en-sc'          : 'Seychelles',
    'en-sg'          : 'Singapore',
    'en-us'          : 'United States',
    'en-za'          : 'South Africa',
    'en-zm'          : 'Zambia',
    'en-zw'          : 'Zimbabwe',
    'eo'             : '',
    'eo-us'          : 'United States',
    'es'             : '',
    'es-419'         : 'Latin America',
    'es-ar'          : 'Argentina',
    'es-bo'          : 'Bolivia',
    'es-cl'          : 'Chile',
    'es-co'          : 'Colombia',
    'es-cr'          : 'Costa Rica',
    'es-cu'          : 'Cuba',
    'es-do'          : 'Dominican Republic',
    'es-ec'          : 'Ecuador',
    'es-es'          : 'Spain',
    'es-gt'          : 'Guatemala',
    'es-hn'          : 'Honduras',
    'es-mx'          : 'Mexico',
    'es-ni'          : 'Nicaragua',
    'es-pa'          : 'Panama',
    'es-pe'          : 'Peru',
    'es-pr'          : 'Puerto Rico',
    'es-py'          : 'Paraguay',
    'es-sv'          : 'El Salvador',
    'es-us'          : 'United States',
    'es-uy'          : 'Uruguay',
    'es-ve'          : 'Venezuela',
    'et'             : '',
    'et-ee'          : 'Estonia',
    'eu'             : '',
    'eu-es'          : 'Spain',
    'eu-fr'          : 'France',
    'fa'             : '',
    'fa-ir'          : 'Iran',
    'fa-latn'        : '',
    'fi'             : '',
    'fi-fi'          : 'Finland',
    'fil-ph'         : 'Philippines',
    'fo-fo'          : 'Faroe Islands',
    'fr-be'          : 'Belgium',
    'fr-ca'          : 'Canada',
    'fr-ch'          : 'Switzerland',
    'fr-fr'          : 'France',
    'fr-lu'          : 'Luxembourg',
    'gl-es'          : 'Spain',
    'he'             : '',
    'he-il'          : 'Israel',
    'hi'             : '',
    'hi-in'          : 'India',
    'hr'             : '',
    'hr-hr'          : 'Croatia',
    'hu'             : '',
    'hu-hu'          : 'Hungary',
    'hy'             : '',
    'hy-am'          : 'Armenia',
    'id'             : '',
    'id-id'          : 'Indonesia',
    'is'             : '',
    'is-is'          : 'Iceland',
    'it'             : '',
    'it-ch'          : 'Switzerland',
    'it-it'          : 'Italy',
    'ja'             : '',
    'ja-jp'          : 'Japan',
    'kn'             : '',
    'kn-in'          : 'India',
    'ko'             : '',
    'ko-kr'          : 'South Korea',
    'lt'             : '',
    'lt-lt'          : 'Lithuania',
    'lv'             : '',
    'lv-lv'          : 'Latvia',
    'mi'             : '',
    'mi-nz'          : 'New Zealand',
    'mk'             : '',
    'mk-mk'          : 'North Macedonia',
    'ml'             : '',
    'ml-in'          : 'India',
    'mn-mn'          : 'Mongolia',
    'ms'             : '',
    'ms-my'          : 'Malaysia',
    'mt'             : '',
    'mt-mt'          : 'Malta',
    'my'             : '',
    'my-mm'          : 'Myanmar (Burma)',
    'nb'             : '',
    'nb-no'          : 'Norway',
    'nl'             : '',
    'nl-aw'          : 'Aruba',
    'nl-be'          : 'Belgium',
    'nl-nl'          : 'Netherlands',
    'os-ru'          : 'Russia',
    'pl'             : '',
    'pl-pl'          : 'Poland',
    'pt'             : '',
    'pt-br'          : 'Brazil',
    'pt-pt'          : 'Portugal',
    'ro'             : '',
    'ro-ro'          : 'Romania',
    'ru'             : '',
    'ru-lv'          : 'Latvia',
    'ru-ru'          : 'Russia',
    'ru-ua'          : 'Ukraine',
    'si'             : '',
    'si-lk'          : 'Sri Lanka',
    'sk'             : '',
    'sk-sk'          : 'Slovakia',
    'sl'             : '',
    'sl-si'          : 'Slovenia',
    'sq'             : '',
    'sq-al'          : 'Albania',
    'sq-mk'          : 'North Macedonia',
    'sr'             : '',
    'sr-me'          : 'Montenegro',
    'sr-rs'          : 'Serbia',
    'sv'             : '',
    'sv-fi'          : 'Finland',
    'sv-se'          : 'Sweden',
    'ta'             : '',
    'ta-in'          : 'India',
    'ta-lk'          : 'Sri Lanka',
    'te'             : '',
    'te-in'          : 'India',
    'tg-tj'          : 'Tajikistan',
    'th'             : '',
    'th-th'          : 'Thailand',
    'tr'             : '',
    'tr-cy'          : 'Cyprus',
    'tr-tr'          : 'Türkiye',
    'uk'             : '',
    'uk-ua'          : 'Ukraine',
    'uz'             : '',
    'uz-uz'          : 'Uzbekistan',
    'vi'             : '',
    'vi-vn'          : 'Vietnam',
    'vi-vn-x-central': 'Vietnam',
    'vi-vn-x-south'  : 'Vietnam',
    'zh-cn'          : 'China',
    'zh-hk'          : 'Hong Kong SAR China',
    'zh-sg'          : 'Singapore',
    'zh-tw'          : 'Taiwan'
}
