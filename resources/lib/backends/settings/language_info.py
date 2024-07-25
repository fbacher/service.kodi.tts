# coding=utf-8
import datetime
from typing import Any, Dict, Final, ForwardRef, List, Tuple

import xbmc

import langcodes

from backends.settings.i_validators import AllowedValue, IStringValidator
from backends.settings.service_types import ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.messages import Message, Messages
from common.setting_constants import Genders, GenderSettingsMap, Languages

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class LanguageInfo:
    """
    Provides a consistent way to represent the important language
    information provided by the various TTS engines. The goal is to
    be able to let the user choose the TTS engine and language from
    among those available on their platform.
    """

    _logger: BasicLogger = None;
    initialized: bool = False
    all_languages_loaded: bool = False
    _kodi_locale: str = None
    _locale_label: str = None
    _locale: str = None


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
     The engine_id is used as index for entries_by_engine. Each value 
     is in turn a Dict indexed by a supported langouage family ('en'). The
     value of this second index is every language supported by that engine and
     belonging to that language family (Here, en-us, en-gb, en...) Note that
     there can be more than one language with the same id (one for male and
     another female, for example).
     
    """
    entries_by_engine: Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]] = {}
    #  entries_by_language: Dict[str, List[ForwardRef('LanguageInfo')]] = {}

    lang_id_for_lang: Dict[str, int] = {}

    def __init__(self, engine_id: str,
                 language_id: str,
                 country_id: str,
                 region_id: str,
                 ietf: langcodes.Language,
                 gender: Genders,
                 voice: str,
                 engine_lang_id: str,
                 engine_voice_id: str,
                 engine_name_msg_id: int,
                 engine_quality: int,
                 voice_quality: int
                 ):
        """

        :param engine_id: Same as service_ID/engine_ID. Specifies which engine
                          this entry applies to
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
        :param voice: engine specific name of the voice (optional)
        :param engine_quality: 0-5 estimated quality rating (0=least)
        :param voice_quality: 0-5
        :param engine_lang_id: Code that engine may use for the language
        :param engine_voice_id: Code that engine may use for the voice
        :param engine_name_msg_id: msg_id to get translated engine name
        """
        clz = LanguageInfo
        clz._logger = module_logger.getChild(LanguageInfo.__name__)

        self.engine_id: str = engine_id
        self.language_id: str = language_id
        self.country_id: str = country_id
        self.region_id: str = region_id
        self.ietf: langcodes.Language = ietf
        self.gender: Genders = gender
        self.voice: str = voice
        self.engine_lang_id: str = engine_lang_id
        self.engine_voice_id: str = engine_voice_id
        self.engine_name_msg_id: int = engine_name_msg_id
        self.engine_quality: int = engine_quality
        self.voice_quality: int = voice_quality

        #  self.translated_country_name: str | None = None
        self.translated_gender_name: str | None = None
        self.translated_language_name: str | None = None
        self.translated_lang_country_name: str | None = None
        self.translated_engine_name: str | None = None

        clz._logger.debug(f'{engine_id} ')

        # Add LanguageInfo to the appropriate engines and language groups
        # ('en-us' is part of language group 'en')

        # langs_for_engine: indexed by lang: 'en'
        # Contains all languages for a specific engine

        clz._logger.debug(f'{self}')
        langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
        langs_for_an_engine = clz.entries_by_engine.get(engine_id)
        if langs_for_an_engine is None:
            langs_for_an_engine = {}
            clz.entries_by_engine[engine_id] = langs_for_an_engine

        lang_family_list: List[ForwardRef('LanguageInfo')]
        engine_specific_langs = langs_for_an_engine.get(language_id)
        if engine_specific_langs is None:
            engine_specific_langs = []
            langs_for_an_engine[language_id] = engine_specific_langs
        engine_specific_langs.append(self)  # TODO, put best entry first

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
    def add_language(cls, engine_id: str,
                     language_id: str,
                     country_id: str,
                     region_id: str,
                     ietf: langcodes.Language,
                     gender: Genders,
                     voice: str,
                     engine_lang_id: str,
                     engine_voice_id: str,
                     engine_name_msg_id: int,
                     engine_quality: int,
                     voice_quality: int
                     ) -> None:
        """

        :param engine_id: Same as service_ID/engine_ID. Specifies which engine
                          this entry applies to
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
        :param voice: engine specific name of the voice (optional)
        :param engine_quality: 0-5 estimated quality rating (0=least)
        :param voice_quality: 0-5
        :param engine_lang_id: Code that engine may use for the language
        :param engine_voice_id: Code that engine may use for the voice
        :param engine_name_msg_id: msg_id to get translated engine name
        """
        if language_id not in cls.KODI_SUPPORTED_LANGS:
            return None
        langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
        langs_for_an_engine = cls.entries_by_engine.get(engine_id)
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
                            cls._logger.debug(f'Dupe: ignored')
                            return

        LanguageInfo(engine_id,
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
    def get_entries(cls, translated: bool=True, ordered: bool = True,
                    engine: str | None = None,
                    lang_family: str | None = None,
                    deep: bool = False
                    ) -> Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]]:
        """

        :param translated: Translate any fields in BOTH current lang as well
                           as the language of the locale (if they are different)
        :param ordered: Return entries sorted by language
        :param engine: If None, then return information for all engines
                       If not None, then return information for the engine
                       identified by 'engine'
        :param lang_family: Limits returned language information to this
                     language family (i.e. 'de')
        :param deep: If True, then return all language info for the given
                    engine or language ('en').
                    If False, then return only one language entry for each
                    supported language ('en'). Meant for engines
        :return: Dict indexed by engine_id or language_id. Values are lists
                 of languages supported by that engine. The list will contain
                 all supported variations of a single language if deep=True,
                 otherwise it will contain (TODO: complete)
        """
        number_of_entries: int = 0
        cls.get_all_lang_info()
        current_kodi_lang: str = xbmc.getLanguage(xbmc.ISO_639_2)
        source: Dict[str, List[ForwardRef('LanguageInfo')]]
        # if engine is None:
        #     source = cls.entries_by_language
        # else:
        #    source = cls.entries_by_engine
        """
            Return languages that apply to a specific engine.
            If deep is False, then return a language entry for each 
            language supported by that engine. 
            If deep is True, then return every language supported by that
            engine that is in the specified language family ('en').
            
            Also, sort by language, then engine
        """

        #  entries_by_engine: Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]] = {}

        for engine_id, langs_for_an_engine in cls.entries_by_engine.items():
            engine_id: str
            langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]

            '''
            if lang_family != '':
                keys_for_lang_family = langs_for_an_engine.keys()
                for key in keys_for_lang_family:
                    if key != lang_family:
                        del keys_for_lang_family[key]
            '''

            for lang_family_id, engine_langs_in_family in langs_for_an_engine.items():
                lang_family_id: str
                engine_langs_in_family: List[ForwardRef('LanguageInfo')]
                number_of_entries += 1
                cls.prepare_for_display(translated,
                                        engine_langs_in_family,
                                        lang_family_id,
                                        current_kodi_lang)
            # else:
            #     engine_langs_in_family = langs_for_an_engine.get(lang_family)
            #     if engine_langs_in_family is not None:
            #         cls.prepare_for_display(translated,
            #                                 engine_langs_in_family,
            #                                 lang_family,
            #                                 current_kodi_lang)

        return cls.entries_by_engine

    @classmethod
    def prepare_for_display(cls, translated: bool,
                            engine_langs_in_family: List[ForwardRef('LanguageInfo')],
                            lang_family_id: str,
                            current_kodi_lang: str) -> None:
        for lang_info in engine_langs_in_family:
            lang_info: ForwardRef('LanguageInfo')
            if translated:
                if lang_info.engine_name_msg_id != 0:
                    lang_info.translated_engine_name = Messages.get_msg_by_id(
                            lang_info.engine_name_msg_id)

                lang_info.translated_language_name = lang_info.ietf.language_name(
                        language=current_kodi_lang)
                lang_info.translated_lang_country_name = (
                    lang_info.ietf.territory_name(
                            language=current_kodi_lang))
                # Convert 'en-us' to 'English (United States)'
                lang_info.translated_lang_country_name = (
                    lang_info.ietf.display_name(
                            language=current_kodi_lang))

                msg_id: Message = GenderSettingsMap.settings_map.get(
                        lang_info.gender)
                lang_info.translated_gender_name = Messages.get_msg(msg_id)
        return

    @classmethod
    def get_all_lang_info(cls) -> None:
        if cls.all_languages_loaded:
            return

        cls.all_languages_loaded = True
        engine_ids: List[Tuple[str, Dict[str, Any]]]
        engine_ids = SettingsMap.get_available_service_ids(
                service_type=ServiceType.ENGINE)
        services: List[Tuple[str, str]]
        services = SettingsMap.get_services_for_service_type(ServiceType.ENGINE)
        # Each tuple contains [Service_Id, service_display_name]

        cls._logger.debug(f'get_all_lang_info engine_ids: {len(engine_ids)}')
        for service_info in services:
            service_info: Tuple[str, str]
            engine_id: str = service_info[0]
            cls._logger.debug(f'getting lang for {engine_id}')
            new_active_engine = BaseServices.getService(engine_id)
            new_active_engine.settingList(SettingsProperties.LANGUAGE)

    @property
    def locale(self) -> str:
        clz = type(self)
        if clz._locale is None:
            clz._locale = self.ietf.to_tag()
        return clz._locale

    @property
    def kodi_locale(self) -> str:
        clz = type(self)
        if clz._kodi_locale is not None:
            return clz._kodi_locale

        tmp: str = xbmc.getLanguage(xbmc.ISO_639_2)
        kodi_language: langcodes.Language
        kodi_language = langcodes.Language.get(tmp)
        kodi_lang: str = kodi_language.language
        clz._kodi_locale = kodi_language.to_tag()
        return clz._kodi_locale

    @property
    def locale_label(self) -> str:
        clz = type(self)
        if clz._locale_label is None:
            clz._locale_label = self.ietf.display_name(self.kodi_locale)
        return clz._locale_label

    '''
    @classmethod
    def get_translated_country_name(cls, country_id: str) -> str:
        msg_id: int = Languages.country_msg_map.get(country_id)
        if msg_id is None:
            return country_id
        return Messages.get_msg_by_id(msg_id)

    @classmethod
    def get_translated_language_name(cls, lang_id: str) -> str:
        LanguageInfo._logger.debug(f'lang_id: {lang_id}')
        msg_id: int = Languages.lang_msg_map.get(lang_id)
        LanguageInfo._logger.debug(f'msg_id: {msg_id}')
        if msg_id is None:
            return lang_id
        return Messages.get_msg_by_id(msg_id)


    @classmethod
    def get_translated_msg_for_locale(cls, lang_code: str,
                                      country_code: str) -> str:
        """
        Gets a translated human-readable name for lang-country_code

        :param lang_code: lower-case iso-639-1 or -2 code (639-1 preferred)
                            and country_code is upper-case (if available)
        :param country_code: upper-case iso-1366-1 (2 or three letter) country code
                           with iso-1366-1 preferred
        :return: Translated string for the locale. Example:
                 en-US becomse "English (United States)".
                 If no translation found then lang_code-COUNTRY_CODE is
                 returned.
        """
        if Languages._logger is None:
            Languages._logger = module_logger.getChild(Languages.__class__.__name__)

        LanguageInfo._logger.debug(f'lang_code: {lang_code} country_code: {country_code}')
        locale_name: str = ''
        if country_code != '':
            locale_name = f'{lang_code}-{country_code}'
        else:
            locale_name = lang_code
        msg = self.ietf.displayName
        msg_id: Message = Languages.locale_msg_map.get(locale_name)
        if msg_id is None:
            LanguageInfo._logger.debug(f'No translation for locale: {locale_name}')
            # Construct locale
            lang_name: str = cls.get_translated_language_name(lang_code)
            country_name: str = cls.get_translated_country_name(country_code)
            msg = Messages.get_formatted_msg_by_id(Languages.LOCALE_GENERIC, lang_name,
                                                   country_name)
            if msg is None:
                msg = locale_name
        else:
            msg: str = Messages.get_msg(msg_id)
        return msg
    '''

    @classmethod
    def init(cls) -> None:
        if not cls.initialized:
            engine_id_val: IStringValidator
            engine_id_val = SettingsMap.get_validator(SettingsProperties.ENGINE,
                                                      '')

            entries: List[AllowedValue] = engine_id_val.get_allowed_values()
            for engine_id, enabled in entries:
                engine_id: str
                enabled: bool

    def __repr__(self) -> str:
        field_sep: str = ''  # '{field_sep}'
        engine_id_str: str = f'   engine_id: {self.engine_id}{field_sep}'
        language_id_str: str = f'   language_id: {self.language_id}{field_sep}'
        country_id_str: str = f'   country_id: {self.country_id}{field_sep}'
        region_id_str: str = f'   region_id: {self.region_id}{field_sep}'
        gender_str: str = f'   gender: {self.gender}{field_sep}'
        voice_str: str = f'   voice: {self.voice}{field_sep}'
        engine_lang_id_str: str = f'   engine_lang_id: {self.engine_lang_id}{field_sep}'
        engine_voice_id_str: str = f'   engine_voice_id: {self.engine_voice_id}{field_sep}'
        engine_name_msg_id_str: str = f'   engine_name_msg_id: {self.engine_name_msg_id}{field_sep}'
        engine_quality_str: str = f'   engine_quality: {self.engine_quality}{field_sep}'
        voice_quality_str: str = f'   voice_quality: {self.voice_quality}{field_sep}'
        translated_gender_name_str: str = (f'   translated_gender_name: '
                                           f'{self.translated_gender_name}{field_sep}')
        translated_language_name_str: str = (f'   translated_language_name: '
                                             f'{self.translated_language_name}{field_sep}')
        translated_lang_country_name_str: str = (f'   translated_lang_country_name: '
                                                 f'{self.translated_lang_country_name}{field_sep}')
        translated_engine_name_str: str = (f'translated_engine_name: '
                                           f'{self.translated_engine_name}{field_sep}')
        result = (f'{engine_id_str}{language_id_str}{country_id_str}'
                  f'{region_id_str}'  # {gender_str}{voice_str}{engine_lang_id_str}'
                  #  f'{engine_voice_id_str}{engine_name_msg_id_str}'
                  #  f'{engine_quality_str}{voice_quality_str}{translated_gender_name_str}'
                  f'\n{translated_language_name_str}{translated_lang_country_name_str}'
                  f'{translated_engine_name_str}')
        return result
