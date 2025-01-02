# coding=utf-8
from __future__ import annotations  # For union operator |

from typing import List, Mapping, Optional, Sequence, Union

import langcodes
from common.constants import Constants
from common.logger import BasicLogger
from langcodes import DEFAULT_LANGUAGE

MY_LOGGER = BasicLogger.get_logger(__name__)


class LangCodesWrapper(langcodes.Language):

    def __init__(self, language: Optional[str] = None,
                 extlangs: Optional[Sequence[str]] = None, script: Optional[str] = None,
                 territory: Optional[str] = None,
                 variants: Optional[Sequence[str]] = None,
                 extensions: Optional[Sequence[str]] = None,
                 private: Optional[str] = None):
        super().__init__(language, extlangs, script, territory, variants, extensions,
                         private)

    @property
    def extlangs(self) -> Sequence[str]:
        extlangs: Sequence[str] | None = super().extlangs
        if extlangs is None:
            extlangs = []
        return extlangs

    @property
    def script(self) -> str:
        script: str | None = super().script
        if script is None:
            script = ''
        return script

    @property
    def territory(self) -> str:
        territory: str | None = super().territory
        if territory is None:
            territory = '-'
        return territory

    @property
    def variants(self) -> Sequence[str]:
        variants: Optional[Sequence[str]] = super().variants
        if variants is None:
            variants = ['']
        return variants

    @property
    def extensions(self) -> Sequence[str]:
        extensions: Optional[Sequence[str]] = super().extensions
        if extensions is None:
            extensions = []
        return extensions

    @property
    def private(self) -> str:
        private: Optional[str] = super().private
        if private is None:
            private = ''
        return private

    @classmethod
    def make(cls, language: Optional[str] = None,
             extlangs: Optional[Sequence[str]] = None, script: Optional[str] = None,
             territory: Optional[str] = None, variants: Optional[Sequence[str]] = None,
             extensions: Optional[Sequence[str]] = None,
             private: Optional[str] = None) -> 'Language':
        return super().make(language, extlangs, script, territory, variants, extensions,
                            private)

    @staticmethod
    def get(tag: Union[str, 'Language'], normalize=True) -> 'Language':
        return langcodes.Language.get(tag, normalize)

    def to_tag(self) -> str:
        return super().to_tag()

    def simplify_script(self) -> 'Language':
        return super().simplify_script()

    def assume_script(self) -> 'Language':
        return super().assume_script()

    def prefer_macrolanguage(self) -> 'Language':
        return super().prefer_macrolanguage()

    def to_alpha3(self, variant: str = 'T') -> str:
        return super().to_alpha3(variant)

    def broader_tags(self) -> List[str]:
        return super().broader_tags()

    def broaden(self) -> 'List[Language]':
        return super().broaden()

    def maximize(self) -> 'Language':
        return super().maximize()

    def match_score(self, supported: 'Language') -> int:
        return super().match_score(supported)

    def distance(self, supported: 'Language') -> int:
        return super().distance(supported)

    def is_valid(self) -> bool:
        return super().is_valid()

    def has_name_data(self) -> bool:
        return super().has_name_data()

    def _get_name(self, attribute: str, language: Union[str, 'Language'],
                  max_distance: int) -> str:
        return super()._get_name(attribute, language, max_distance)

    def _best_name(self, names: Mapping[str, str], language: 'Language',
                   max_distance: int):
        return super()._best_name(names, language, max_distance)

    def language_name(self, language: Union[str, 'Language'] = DEFAULT_LANGUAGE,
                      max_distance: int = 25) -> str:
        if True:  # Constants.USE_LANGCODES_DATA:
            return super().language_name(language, max_distance)
        else:
            return 'missing language_name'

    def display_name(self, language: Union[str, 'Language'] = DEFAULT_LANGUAGE,
                     max_distance: int = 25) -> str:
        if True:  #  Constants.USE_LANGCODES_DATA:
            MY_LOGGER.debug(f'USE_LANGCODES_DATA: {Constants.USE_LANGCODES_DATA}')
            return super().display_name(language, max_distance)
        return 'missing display_name'

    def _display_pattern(self) -> str:
        return super()._display_pattern()

    def _display_separator(self) -> str:
        return super()._display_separator()

    def autonym(self, max_distance: int = 9) -> str:
        return super().autonym(max_distance)

    def script_name(self, language: Union[str, 'Language'] = DEFAULT_LANGUAGE,
                    max_distance: int = 25) -> str:
        return super().script_name(language, max_distance)

    def territory_name(self, language: Union[str, 'Language'] = DEFAULT_LANGUAGE,
                       max_distance: int = 25) -> str:
        if True  # Constants.USE_LANGCODES_DATA:
            return super().territory_name(language, max_distance)
        return 'missing territory_name'

    def region_name(self, language: Union[str, 'Language'] = DEFAULT_LANGUAGE,
                    max_distance: int = 25) -> str:
        return super().region_name(language, max_distance)

    def variant_names(self, language: Union[str, 'Language'] = DEFAULT_LANGUAGE,
                      max_distance: int = 25) -> Sequence[str]:
        return super().variant_names(language, max_distance)

    def describe(self, language: Union[str, 'Language'] = DEFAULT_LANGUAGE,
                 max_distance: int = 25) -> dict:
        return super().describe(language, max_distance)

    def speaking_population(self) -> int:
        return super().speaking_population()

    def writing_population(self) -> int:
        return super().writing_population()

    @staticmethod
    def find_name(tagtype: str, name: str,
                  language: Optional[Union[str, 'Language']] = None) -> 'Language':
        return super().find_name(tagtype, name, language)

    @staticmethod
    def find(name: str, language: Optional[Union[str, 'Language']] = None) -> 'Language':
        return super().find(name, language)

    def to_dict(self) -> dict:
        return super().to_dict()

    def update(self, other: 'Language') -> 'Language':
        return super().update(other)

    def update_dict(self, newdata: dict) -> 'Language':
        return super().update_dict(newdata)
