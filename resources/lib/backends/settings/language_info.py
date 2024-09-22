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
from common.logger import BasicLogger, DEBUG_XV, DEBUG_V
from common.message_ids import MessageId, MessageUtils
from common.messages import Message, Messages
from common.setting_constants import Genders, GenderSettingsMap

module_logger = BasicLogger.get_logger(__name__)


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
     The engine_id is used as index for entries_by_engine. Each value 
     is in turn a Dict indexed by a supported langouage family ('en'). The
     value of this second index is every language supported by that engine and
     belonging to that language family (Here, en-us, en-gb, en...) Note that
     there can be more than one language with the same id (one for male and
     another female, for example).
     
         entries_by_engine: key: engine_id
                            value: Dict[lang_family, List[languageInfo]]
                            lang_family (iso-639-1 or -2 code)
                            List[languageInfo} list of all languages supported by 
                            that engine and language ('en' or 'en-us' and other variants).
    """
    entries_by_engine: Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]] = {}
    #  entries_by_language: Dict[str, List[ForwardRef('LanguageInfo')]] = {}

    lang_id_for_lang: Dict[str, int] = {}

    @classmethod
    def class_init(cls):
        if cls._logger is None:
            cls._logger = module_logger

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
                 voice_quality: int,
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
        self.engine_id: str = engine_id
        self.language_id: str = language_id
        self.country_id: str = country_id
        self.region_id: str = region_id
        self.ietf: langcodes.Language = ietf
        self.gender: Genders = gender
        self.translated_voice: str = voice
        self.engine_lang_id: str = engine_lang_id
        self.engine_voice_id: str = engine_voice_id
        self.engine_name_msg_id: int = engine_name_msg_id
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
        self.label: str = None

        # Add LanguageInfo to the appropriate engines and language groups
        # ('en-us' is part of language group 'en')

        # langs_for_engine: indexed by lang: 'en'
        # Contains all languages for a specific engine

        # clz._logger.debug(f'{self}')
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
                     translate messages for any field that it handles. In particular,
                     the language name.
        :param gender: Specifies the gender, if known
        :param voice: engine specific display name of the voice (optional)
        :param engine_quality: 0-5 estimated quality rating (0=least)
        :param voice_quality: 0-5
        :param engine_lang_id: Code that engine may use for the language
        :param engine_voice_id: Code that engine may use for the voice
        :param engine_name_msg_id: msg_id to get translate engine name
        """
        if language_id not in cls.KODI_SUPPORTED_LANGS:
            return None
        if country_id is not None:
            country_id = country_id.lower()
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
                            cls._logger.debug_v(f'Dupe: ignored')
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
    def get_entry(cls, engine_id: str,
                  engine_voice_id: str,
                  lang_id: str = None) -> ForwardRef('LanguageInfo'):
        cls.get_all_lang_info()

        entries:  Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]]
        entries = cls.get_entries(engine_id=engine_id, lang_family=lang_id)
        if cls._logger.isEnabledFor(DEBUG_V):
            cls._logger.debug_v(f'# entries: {len(entries.keys())} keys:'
                                      f' {entries.keys()}')
        if entries is None:
            cls._logger.error(f"Can't find voice entry for engine: {engine_id} "
                              f"# entries: {cls._number_of_entries}")
            return None

        engine_lang_entries:  Dict[str, List[ForwardRef('LanguageInfo')]] | None
        engine_lang_entries = entries.get(engine_id)
        if engine_lang_entries is None:
            cls._logger.error(f"Can't find voice entry for engine: {engine_id} "
                              f"# entries: {cls._number_of_entries}")
            return None

        #  cls._logger.debug(f'# engine_lang_entries: {len(engine_lang_entries.keys())} '
        #                    f'keys: {engine_lang_entries.keys()}')

        lang_info: ForwardRef('LanguageInfo')
        territory_entries: List[ForwardRef('LanguageInfo')]

        if lang_id is None:
            #  cls._logger.debug(f'lang_id is None')
            for territory_entries in engine_lang_entries.values():
                #  cls._logger.debug(f'# territory_entries: {len(territory_entries)} ')
                for lang_info in territory_entries:
                    #  cls._logger.debug(f'engine_voice_id: {engine_voice_id} '
                    #                    f'lang_info voice: {lang_info.engine_voice_id}')
                    if lang_info.engine_voice_id == engine_voice_id:
                        return lang_info
        else:
            #  cls._logger.debug(f'lang_id is not None')
            entries_for_lang = engine_lang_entries.get(lang_id)
            if entries_for_lang is None:
                #  cls._logger.error(f"Can't find voice entry for language: {lang_id}")
                return None
            for lang_info in entries_for_lang:
                if lang_info.engine_voice_id == engine_voice_id:
                    return lang_info

    @classmethod
    def get_entries(cls, translate: bool = True, ordered: bool = True,
                    engine_id: str | None = None,
                    lang_family: str | None = None,
                    deep: bool = True
                    ) -> Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]] | None]:
        """
        Gets language capabilities of all or a single TTS engine.

        :param translate: Translate any fields in BOTH current lang as well
                           as the language of the locale (if they are different)
        :param ordered: Return entries sorted by language
        :param engine_id: If None, then return information for all engines
                       If not None, then return information for the engine
                       identified by 'engine'
        :param lang_family: Limits returned language information to this
                     language family (i.e. 'de')
        :param deep: If True, then return all language info for the given
                    language ('en').
                    If False, then return only one language entry for each
                    supported language ('en') with the closest match to the
                    current Kodi locale.
        :return: Dict indexed by engine_id or language_id. Values are lists
                 of languages supported by that engine. The list will contain
                 all supported variations of a single language if deep=True,
                 otherwise it will contain (TODO: complete)
        """
        number_of_entries: int = 0
        cls.get_all_lang_info()
        langs_for_engines: List[Dict[str, List[ForwardRef('LanguageInfo')]]] = []
        langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
        engine_id_arg: str | None = engine_id
        from backends.settings.settings_helper import SettingsHelper

        kodi_lang, kodi_locale, kodi_friendly_locale, kodi_language = \
            SettingsHelper.get_kodi_locale_info()
        if engine_id is not None:
            langs_for_an_engine = cls.entries_by_engine.get(engine_id)
            if langs_for_an_engine is None:
                return_value:  Dict[str,
                                    Dict[str, List[ForwardRef('LanguageInfo')]] | None]
                return_value = {engine_id: None}
                return return_value
            langs_for_engines.append(langs_for_an_engine)
        else:
            for engine_id, langs_for_an_engine in cls.entries_by_engine.items():
                engine_id: str
                langs_for_engines.append(langs_for_an_engine)

            '''
            if lang_family != '':
                keys_for_lang_family = langs_for_an_engine.keys()
                for key in keys_for_lang_family:
                    if key != lang_family:
                        del keys_for_lang_family[key]
            '''

            for langs_for_an_engine in langs_for_engines:
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
            If engine_id specified, then only return info for that one.
            
            entries_by_engine: key: engine_id
                            value: Dict[lang_family, List[languageInfo]]
                            lang_family (iso-639-1 or -2 code)
                            List[languageInfo} list of all languages supported by 
                            that engine and language ('en' or 'en-us' and other variants).
        """
        if engine_id_arg is not None:
            entry: Dict[str, List[ForwardRef('LanguageInfo')]]
            entry = cls.entries_by_engine.get(engine_id_arg)
            return {engine_id: entry}

        return cls.entries_by_engine

    @property
    def translated_gender_name(self) -> str:
        if self._translated_gender_name is None:
            msg_id: Message = GenderSettingsMap.settings_map.get(
                    self.gender)
            self._translated_gender_name = Messages.get_msg(msg_id)
        return self._translated_gender_name

    @property
    def translated_language_name(self) -> str:
        if self._translated_language_name is None:
            kodi_lang: str
            from backends.settings.settings_helper import SettingsHelper

            kodi_lang, _, _, _ = \
                SettingsHelper.get_kodi_locale_info()
            self._translated_language_name = self.ietf.language_name(
                    language=kodi_lang)
        return self._translated_language_name

    @property
    def translated_lang_country_name(self) -> str:
        if self._translated_lang_country_name is None:
            from backends.settings.settings_helper import SettingsHelper

            kodi_lang, _, _, _ = \
                SettingsHelper.get_kodi_locale_info()
            self._translated_lang_country_name = (
                self.ietf.display_name(
                        language=kodi_lang))
        return self._translated_lang_country_name

    @property
    def translated_engine_name(self) -> str:
        if self._translated_engine_name is None:
            if self.engine_name_msg_id != 0:
                self._translated_engine_name = Messages.get_msg_by_id(
                        self.engine_name_msg_id)
        if self._translated_engine_name is None:
            return ''
        return self._translated_engine_name

    @classmethod
    def get_translated_engine_name(cls, engine_id: str) -> str:
        trans_name: str = MessageUtils.get_msg(engine_id)
        return trans_name


    @property
    def translated_country_name(self) -> str:
        if self._translated_country_name is None:
            from backends.settings.settings_helper import SettingsHelper

            kodi_lang, _, _, _ = \
                SettingsHelper.get_kodi_locale_info()
            self._translated_country_name = (
                self.ietf.territory_name(
                        language=kodi_lang))
            if self._translated_country_name is None:
                self._translated_country_name = ''
        return self._translated_country_name

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
                display_autonym_choice: str = lang_info.ietf.autonym()
                # get how close of a match this language is to
                # Kodi's setting

                match_distance: int
                match_distance = langcodes.tag_distance(desired=kodi_lang,
                                                        supported=lang_info.ietf)
                display_engine_name: str = lang_info.translated_engine_name
                voice_name: str = lang_info.translated_voice
                label: str
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
                #  cls._logger.debug(f'label: {label}')
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

        if cls._logger.isEnabledFor(DEBUG_XV):
            cls._logger.debug_xv(f'get_all_lang_info engine_ids:'
                                            f' {len(engine_ids)}')
        for service_info in services:
            service_info: Tuple[str, str]
            engine_id: str = service_info[0]
            if cls._logger.isEnabledFor(DEBUG_V):
                cls._logger.debug_v(f'getting lang for {engine_id}')
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
        result = (f'{engine_id_str}{language_id_str}{country_id_str}'
                  f'{region_id_str}'  # {gender_str}{voice_str}{engine_lang_id_str}'
                  #  f'{engine_voice_id_str}{engine_name_msg_id_str}'
                  #  f'{engine_quality_str}{voice_quality_str}{translated_gender_name_str}'
                  f'\n{translated_language_name_str}{translated_lang_country_name_str}'
                  f'{translated_engine_name_str}')
        return result


LanguageInfo. class_init()
