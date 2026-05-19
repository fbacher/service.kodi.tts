# coding=utf-8
from __future__ import annotations

import langcodes
from backends.settings.i_lang_utils import ILangUtils

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from common.constants import Constants
from backends.settings.service_types import ServiceID, ServiceKey, SERVICES_BY_TYPE

"""
   Provides a consistent way to represent the important language
   information provided by the various TTS engines. The goal is to
   be able to let the user choose the TTS engine and language from
   among those available on their platform.
   """

from typing import Any, Dict, Final, ForwardRef, List, Tuple

from langcodes import Language
from common.logger import *

MY_LOGGER = BasicLogger.get_logger(__name__)


class LangUtils(ILangUtils):
    """
    Language Information is defined at startup, in bootstrap_engines,
    BEFORE the engines are fully defined. During configuration, LanguageInfo
    should only 'inhale' the language information during settings definition
    and not query other engines during this stage.

    """
    _initialized: bool = False
    kodi_language: Language = None
    kodi_locale_label: str = None
    _number_of_entries: int = 0
    lang_id_for_lang: Dict[str, int] = {}

    def __init__(self, engine_key: ServiceID,
                 ietf: Language,
                 engine_lang_id: str
                 ):
        """

        :param engine_key: Same as ServiceID. Specifies which engine
                          this entry applies to
        :param ietf: langcodes.Language IETF standard object. Useful for getting
                     translate messages for any field that it handles. In particular,
                     the language name.
        :param engine_lang_id: Code that engine may use for the language
        """
        super().__init__(engine_key=engine_key,
                         ietf=ietf,
                         engine_lang_id=engine_lang_id)
        self._engine_key: ServiceID = engine_key
        self.ietf: Language = ietf
        self.engine_lang_id: str = engine_lang_id
        self._language_label: str | None = None
        self._country_label: str | None = None
        self._lang_country_label: str | None = None

    @property
    def engine_key(self) -> ServiceID:
        return self._engine_key

    @property
    def translated_language_name(self) -> str:
        clz = type(self)
        kodi_lang: str = clz.kodi_language.language
        if Constants.USE_LANGCODES_DATA:
            self._language_label = self.ietf.language_name(
                    language=kodi_lang)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                xx = clz.get_language_name(self.ietf.to_tag(), kodi_lang)
                MY_LOGGER.debug_v(f'LANGCODES lang: {self.ietf.to_tag().lower()} '
                                  f'kodi_lang: {kodi_lang} '
                                  f'lang_name: {self._language_label}')
                MY_LOGGER.debug_v(f'LANGCODES2 lang {self.ietf.to_tag().lower()} '
                                  f'kodi_lang: {kodi_lang} '
                                  f'lang_name: {xx}')
        else:
            self._language_label = clz.get_language_name(self.ietf.to_tag(),
                                                         kodi_lang)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'LANGCODES lang: {self.ietf.to_tag().lower()} '
                                f'kodi_lang: {kodi_lang} '
                                f'lang_name: {self._language_label}')
        return self._language_label

    @classmethod
    def get_translated_language_name(cls, langcode: Language) -> str:
        result: str = ''
        kodi_lang: str = cls.kodi_language.language
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

    def get_display_name(self, locale_spec: Language) -> str:
        """
        Gets the human-readable name for the given locale_id and translated into
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
                MY_LOGGER.debug_v(f'LANGCODES lang_id: {self.ietf.to_tag().lower()} kodi_locale: '
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
        Convert the given lang to human-friendly text using Kodi's current locale_id
        :param lang: ietf formated language (en-US)
        :return:
        """
        langcode: Language = Language.get(lang)
        result: str = ''
        if Constants.USE_LANGCODES_DATA:
            result = langcode.display_name(cls.kodi_language)  # Gets the English name
            #  kodi_lang_code = kodi_language.language
            result2 = cls.get_autonym(lang)
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'LANGCODES lang: {lang} {result}')
                MY_LOGGER.debug_v(f'LANGCODES2 lang: {lang} {result2}')
        else:
            """
             To do this properly, need to look up the given lang's locale_id in a
             map of locale_id -> display. Further, the map depends upon kodi's locale_id,
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
    def translated_locale(self) -> str:
        """
        Generates the text for the user-friendly country name in kodi's current
        language.
        :return:
        """
        clz = type(self)
        if self._lang_country_label is None:
            if Constants.USE_LANGCODES_DATA:
                self._lang_country_label = (
                  self.ietf.display_name(
                            language=clz.kodi_lang))
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug(f'LANGCODES lang: {self.ietf.to_tag().lower()} display: '
                                    f'{self._lang_country_label}')

                territory: str = self.ietf.territory
                if territory is None:
                    territory = ''
                key: str = f'{clz.kodi_lang}-{territory.lower()}'
                txt = clz.get_country_name(key)
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'LANGCODES2 lang: {key} display: '
                                      f'{txt}')
            else:
                key: str = f'{clz.kodi_lang}-{self.ietf.territory.lower()}'
                self._lang_country_label = clz.get_country_name(key)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'LANGCODES lang: {key} display: '
                                    f'{self._lang_country_label}')
        return self._lang_country_label

    @property
    def translated_country_name(self) -> str:
        """
        Get the name of the country/territory for self translated for the
        current kodi language.
        """
        clz = type(self)
        if self._country_label is None:
            country_name: str = ''
            if Constants.USE_LANGCODES_DATA:
                self._country_label = self.ietf.territory_name(
                        language=clz.kodi_lang)
                country_name: str = clz.get_country_name(self.ietf.to_tag())
            else:
                # Need to look up the country name in a table instead of using
                # the better LANGCODES_DATA.
                # Normally, Kodi tts displays language information for
                # languages that are in the same family as kodi's language ('en')
                # So, assume that kodi's language setting is not important.
                # This will bite us if the above assumption is incorrect.

                country_name: str = clz.get_country_name(self.ietf.to_tag())
                self._country_label = country_name
            if self._country_label is None:
                self._country_label = ''
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'LANGCODES lang: {self.ietf.to_tag().lower()} '
                                  f'{self._country_label}')
                MY_LOGGER.debug_v(f'LANGCODES2 lang: {self.ietf.to_tag().lower()} '
                                  f'{country_name}')
        return self._country_label

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

    @property
    def locale_id(self) -> str:
        clz = type(self)
        if clz._locale is None:
            clz._locale = self.ietf.to_tag().lower()
        return clz._locale

    @classmethod
    def get_kodi_locale_info(cls) -> Tuple[str, str, str, Language]:
        """
        Retrieves the currently configured Kodi locale_id in several formats

        :return: returns [kodi_lang (en), kodi_locale (en-US), kodi_locale_label,
                         kodi_language (langcodes.Language instance for 'en-US)]
        """
        # xbmc.getLanguage is a mess, but hopefully fixed in upcoming release
        # On Linux, you can get the language code ('en' or 'eng') but you can't
        # get 'en-us'. On windows getLanguage(iso_639_1, True)  returns 'en-us'
        # ENGLISH_NAME produces a non-standard string "English-USA (12h)" on windows
        # Even the embedded python windows locale_id.getlocale() returns an odd string:
        # English_United States. While Linux getLanguage(iso_639_1, True) returns 'en-'
        # However on Linux Python locale_id.getlocale() produces the expected value:
        # 'en-us'
        #
        return (cls.kodi_lang, cls.kodi_locale, cls.kodi_locale_label,
                cls.kodi_language)

    @classmethod
    def init(cls) -> None:
        """
        Kodi's language cannot
        """
        if not cls._initialized:
            cls._initialized = True
            lang_territory: str = Constants.LOCALE
            # kodi_language = langcodes.Language instance for 'en-US'
            cls.kodi_language = Language.get(lang_territory)
            # kodi_locale = 'en-US'
            cls.kodi_locale = cls.kodi_language.to_tag()
            # kodi_lang = 'en'
            cls.kodi_lang: str = cls.kodi_language.language
            if Constants.USE_LANGCODES_DATA:
                cls.kodi_locale_label = cls.kodi_language.display_name(cls.kodi_locale)
            else:
                # Need to get self fully displayed (lang + territory) in kodi's
                # language.
                # ASSUME that the lang for both self and kodi language are the
                # SAME since tts does not allow you to choose such a combination.
                cls.kodi_locale_label = cls.get_alt_display_name(cls.kodi_locale)
            if Constants.USE_LANGCODES_DATA:
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    x: str = cls.get_language_name(cls.kodi_language.to_tag().lower(),
                                                   cls.kodi_lang)
                    MY_LOGGER.debug_xv(f'LANGCODES display_name '
                                       f'{cls.kodi_language.to_tag().lower()}'
                                       f' {cls.kodi_locale_label}')
                    MY_LOGGER.debug_xv(f'LANGCODES2 display_name '
                                       f'{cls.kodi_language.to_tag().lower()} {x}')
            else:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(
                        f'LANGCODES display_name {cls.kodi_locale_label}')

    def __eq__(self, other):
        """
        Allow for equality checks. DOES NOT handle hash comparisions (maps)
        :param other:
        :return:
        """
        if isinstance(other, LangUtils):
            other: LangUtils
            return (self._engine_key == other._engine_key and
                    self.locale_id == other.locale_id)
        return NotImplemented

    def __repr__(self) -> str:
        if not MY_LOGGER.isEnabledFor(DEBUG):
            return ''

        field_sep: str = ''  # '{field_sep}'
        engine_key_str: str = f'   engine_key: {self._engine_key}{field_sep}'
        #  TODO:
        # engine_name_msg_id_str: str = f'   engine_name_msg_id: {self.engine_name_msg_id}{field_sep}'

        language_id_str: str = f'   language_id: {self.ietf.to_tag().lower()}{field_sep}'
        engine_lang_id_str: str = f'   engine_lang_id: {self.engine_lang_id}{field_sep}'
        # translated_engine_name_str: str = (f'   translated_engine_name: '
        #                                    f'{self.translated_engine_name}{field_sep} ')
        translated_language_name_str: str
        translated_language_name_str = (f'   translated_language_name: '
                                        f'{self.translated_language_name}{field_sep}')
        translated_lang_country_name_str: str = (f'   translated_locale: '
                                                 f'{self.translated_locale}{field_sep}')
        result = (f'{engine_key_str}{language_id_str}{engine_lang_id_str}'
                  f'\n{translated_language_name_str}{translated_lang_country_name_str}')
        return result

    @classmethod
    def get_autonym(cls, locale_id: str) -> str:
        locale_id = locale_id.lower()
        return ILangUtils.AUTONYMS.get(locale_id, f'{locale_id} (no label)')

    @classmethod
    def get_alt_display_name(cls, locale_id: str) -> str:
        locale_id = locale_id.lower()
        return ILangUtils.LOCALE_SPEC.get(locale_id, f'{locale_id} (no label)')

    @classmethod
    def  get_language_name(cls, locale_id: str, kodi_lang_id: str) -> str:
        locale_id = locale_id.lower()
        kodi_lang_id: str = kodi_lang_id.lower()[0:2]
        key: str = f'{locale_id}-{kodi_lang_id}'
        return ILangUtils.LANGUAGE_NAME_FOR_ID.get(key, f'{key} (no label)')

    @classmethod
    def get_country_name(cls, locale_id: str) -> str:
        locale_id = locale_id.lower()
        return ILangUtils.COUNTRY_NAME_FOR_LOCALE_ID.get(locale_id, '')


LangUtils.init()
