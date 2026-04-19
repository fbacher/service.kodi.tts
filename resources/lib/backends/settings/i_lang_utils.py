# coding=utf-8
from __future__ import annotations


try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from backends.settings.service_types import ServiceID, ServiceKey, SERVICES_BY_TYPE

from typing import Any, Dict, Final, ForwardRef, List, Tuple

from langcodes import Language
from common.logger import *

MY_LOGGER = BasicLogger.get_logger(__name__)


class ILangUtils:
    """
    Interface for LangUtils
    """

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
        pass

    @property
    def engine_key(self) -> ServiceID:
        raise NotImplementedError

    @property
    def translated_language_name(self) -> str:
        raise NotImplementedError

    @classmethod
    def get_translated_language_name(cls, langcode: Language) -> str:
        raise NotImplementedError

    def get_display_name(self, locale_spec: Language) -> str:
        raise NotImplementedError

    @classmethod
    def get_formatted_lang(cls, lang: str) -> str:
        raise NotImplementedError

    @property
    def translated_locale(self) -> str:
        """
        Generates the text for the user-friendly country name in kodi's current
        language.
        :return:
        """
        raise NotImplementedError

    @property
    def translated_country_name(self) -> str:
        """
        Get the name of the country/territory for self translated for the
        current kodi language.
        """
        raise NotImplementedError

    @property
    def autonym(self) -> str:
        raise NotImplementedError

    @classmethod
    def prepare_for_display(cls, translate: bool,
                            engine_langs_in_family: List[ForwardRef('LanguageInfo')],
                            ietf_locale: str,
                            kodi_ietf: str) -> None:
        """
        Translates any fields that require into the current language.

        Note: Changes are made in-place for the argments.

        :param translate: If False, then this serves as a no-op
        :param engine_langs_in_family: List of languages that the engine calling
        this method supports.
        :param ietf_locale:  The IETF language code to translate into
        :param kodi_ietf:  Kodi's current IETF language code
        :return: None, the changes are made to the given arguments
        """
        raise NotImplementedError

    @property
    def locale_id(self) -> str:
        raise NotImplementedError

    @classmethod
    def get_kodi_locale_info(cls) -> Tuple[str, str, str, Language]:
        """
        Retrieves the currently configured Kodi locale_id in several formats

        :return: returns [kodi_lang (en), kodi_locale (en-US), kodi_locale_label,
                         kodi_language (langcodes.Language instance for 'en-US)]
        """
        raise NotImplementedError

    def __eq__(self, other):
        """
        Allow for equality checks. DOES NOT handle hash comparisions (maps)
        :param other:
        :return:
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    @classmethod
    def get_autonym(cls, locale_id: str) -> str:
        raise NotImplementedError

    @classmethod
    def get_alt_display_name(cls, locale_id: str) -> str:
        raise NotImplementedError

    @classmethod
    def  get_language_name(cls, locale_id: str, kodi_lang_id: str) -> str:
        raise NotImplementedError

    @classmethod
    def get_country_name(cls, locale_id: str) -> str:
        raise NotImplementedError


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
    LOCALE_SPEC provides a means to lookup the display name for a particular locale_id
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
