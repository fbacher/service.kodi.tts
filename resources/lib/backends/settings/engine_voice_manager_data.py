# coding=utf-8

from typing import Any, Dict, Final, ForwardRef, List, Tuple
from backends.settings.service_types import ServiceID


class EngineVoiceManagerData:

    """
         The ServiceID is used as index for variants_by_engine. Each value
         is in turn a Dict indexed by a supported locale_id id ('en-us').

             variants_by_engine: Dict[key, value]
                                key: ServiceID
                                value: Dict[lang-country, languageInfo]
                                lang-country: ietf.to_tag() ex: en-us
                                List[languageInfo] list of language variants supported by
                                that engine (for Kodi's current language setting ('en')).
        """
    lang_variants_by_engine: Dict[ServiceID, Dict[str, ForwardRef('LanguageInfo')]] = {}

    voice_groups: Dict[str, List[ForwardRef('VoiceGroup')]] | None = None
