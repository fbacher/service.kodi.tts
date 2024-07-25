# coding=utf-8
from typing import Dict, ForwardRef, List, Tuple

import xbmc
import langcodes

from backends.backend_info import BackendInfo
from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.i_validators import AllowedValue, IStringValidator
from backends.settings.language_info import LanguageInfo
from backends.settings.service_types import ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import StringValidator
from common.base_services import BaseServices
from common.exceptions import LogicError
from common.logger import BasicLogger
from common.messages import Message, Messages
from common.setting_constants import GenderSettingsMap, PlayerMode
from common.settings import Settings
from windowNavigation.choice import Choice

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SettingsHelper:
    _logger: BasicLogger = None
    initialized: bool = False
    engine_id: str = None
    current_language_choices: List[LanguageInfo] = []
    engine_instance: ITTSBackendBase | None = None
    allowed_player_modes: Dict[str, List[AllowedValue]] = {}

    @classmethod
    def init_class(cls) -> None:
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls.__name__)
            #  cls.get_engines_supporting_lang()
            cls.initialized = True

    @classmethod
    def get_current_language_choices(cls) -> List[LanguageInfo]:
        if not cls.initialized:
            cls.init_class()
        return cls.current_language_choices

    @classmethod
    def build_allowed_player_modes(cls) -> None:
        """
           Creates a Dictionary of the allowed PlayerMode for a given service.

           The created structure is allowed_player_modes

           The engine and player must both support the same PlayerMode. The UI
           needs to reflect what the current choices are. Side-effects that
           lead to incorrect configurations must be prevented.

           The structure is simple. It is indexed by service_id (engine or
           player). Each value is a list of AllowedValues for PlayerMode for
           that service. The structure is used to see if a combination of
           engine, player and mode are valid. AllowedValue has an enabled
           flag that is False when that PlayerMode can not be used due to
           that other service (engine or player) involved.

           Use Cases:
              The UI allows the user to select the Engine, Player and PlayerMode
              independently. However, they all depend upon each other. When a
              change is made that creats an invalid configuration it is much
              better to automatically adjust the configuration so that it
              remains valid rather than going through a cumbersome multi-step
              process to manually make the changes.

              Related to the first case. The user desires to hear the effects
              of the change while making them.

        """

        if len(cls.allowed_player_modes.keys()) > 0:
            return

        services: List[Tuple[str, str]]
        services = SettingsMap.get_services_for_service_type(ServiceType.ENGINE)
        services.extend(SettingsMap.get_services_for_service_type(ServiceType.PLAYER))
        for service_id, label in services:
            service_id: str
            label: str
            cls._logger.debug(f'service: {service_id} {label}')
            player_mode_val: StringValidator | IStringValidator
            player_mode_val = SettingsMap.get_validator(service_id,
                                                        SettingsProperties.PLAYER_MODE)
            if player_mode_val is None:
                cls._logger.info(f'No PLAYER_MODE validator for: {label}')
                continue
            allowed_player_modes: List[AllowedValue]
            allowed_player_modes = player_mode_val.get_allowed_values()
            cls.allowed_player_modes[service_id] = allowed_player_modes

    @classmethod
    def update_player_mode(cls, engine_id: str, player_id: str,
                           player_mode: PlayerMode
                           ) -> Tuple[PlayerMode, List[AllowedValue]]:
        """
        Consults with and updates allowed_player_modes to determine what if any
        changes need to be made to have a valid configuration.

        :param engine_id:  The engine to be used
        :param player_id:  The player to be used
        :param player_mode: The proposed player mode
        :return: Tuple[player_mode, List[AllowedValue]
                 player_mode is the mode to use and the AllowedValues are to
                 be used for UI. List is based upon the engine's modes, but
                 with any unsupported values from the player marked disabled.
        """
        engine_allowed_values: List[AllowedValue] = cls.allowed_player_modes[engine_id]
        player_allowed_values: List[AllowedValue] = cls.allowed_player_modes[player_id]
        engine_player_mode: AllowedValue | None = None
        player_player_mode: AllowedValue | None = None
        engine_player_mode = AllowedValue.find_value(player_mode,
                                                     engine_allowed_values)
        player_player_mode = AllowedValue.find_value(player_mode, player_allowed_values)

        """
         player mode is unsupported, then pick another, similar one. 
         Also, change player. Can also use adapters, but code not really there.
                        Substitutions
        SLAVE_FILE      FILE
        SLAVE_PIPE 
        FILE = 'file'   SLAVE_FILE (not likely, but also unlikely to happen)
        PIPE = 'pipe'
        ENGINE_SPEAK = 'engine_speak'
        """
        new_player_mode: PlayerMode = PlayerMode.FILE  # Just to seed it
        if engine_player_mode is None and player_player_mode is None:
            # Very odd. Just use old standby.
            new_player_mode: PlayerMode = PlayerMode.FILE
            engine_player_mode = AllowedValue.find_value(new_player_mode,
                                                         engine_allowed_values)
            player_player_mode = AllowedValue.find_value(new_player_mode,
                                                         player_allowed_values)

            cls._logger.debug(f'Can not find player_mode: {player_mode} for'
                              f' {engine_id} nor {player_id}.'
                              f' Substitute {PlayerMode.FILE}')
        # if engine or player doesn't support the mode, then pick another mode
        elif engine_player_mode is None:
            # Unlikely to occur because it is easy to have pipe wrapper
            new_player_mode: PlayerMode = PlayerMode.FILE
            engine_player_mode = AllowedValue.find_value(new_player_mode,
                                                         engine_allowed_values)
            player_player_mode = AllowedValue.find_value(new_player_mode,
                                                         player_allowed_values)

            cls._logger.debug(f'Can not find player_mode: {player_mode} for'
                              f' {engine_id}'
                              f' Substitute {PlayerMode.FILE}')
        elif player_player_mode is None:
            # Most likely mismatch is engine is SLAVE_FILE, but player does not
            # do slave. Downgrade to FILE, like the rest
            new_player_mode: PlayerMode = PlayerMode.FILE
            engine_player_mode = AllowedValue.find_value(new_player_mode,
                                                         engine_allowed_values)
            player_player_mode = AllowedValue.find_value(new_player_mode,
                                                         player_allowed_values)

            cls._logger.debug(f'Can not find player_mode: {player_mode} for'
                              f' {player_id}'
                              f' Substitute {PlayerMode.FILE}')

        return new_player_mode, engine_allowed_values


    @classmethod
    def get_engine_id(cls):
        if cls.engine_id is None:
            cls.engine_id = Settings.getSetting(SettingsProperties.ENGINE, None,
                                                 SettingsProperties.ENGINE_DEFAULT)
        cls._logger.debug(f'engine_id: {cls.engine_id}')
        valid_engine: bool = False

        if cls.engine_id != SettingsProperties.ENGINE_DEFAULT:
            valid_engine = SettingsMap.is_available(cls.engine_id)
        # if not valid_engine:
        #     cls.engine_id = BackendInfo.getAvailableBackends()[0].backend_id
        cls._logger.debug(f'final engine_id: {cls.engine_id}')
        return cls.engine_id

    @classmethod
    def update_enabled_state(cls, engine_id: str, player_id: str) -> None:
        engine_allowed_values: List[AllowedValue] = cls.allowed_player_modes[engine_id]
        player_allowed_values: List[AllowedValue] = cls.allowed_player_modes[player_id]
        AllowedValue.update_enabled_state(engine_values=engine_allowed_values,
                                          player_values=player_allowed_values)
    @classmethod
    def get_engines_supporting_lang(cls) -> Tuple[List[Choice], int]:
        """

        :return:
        """
        cls._logger.debug(f'In get_engines_supporting_lang')
        choices: List[Choice] = []
        current_choice_index: int = -1
        cls.current_language_choices.clear()
        try:
            # Get all language entries (engine=None does that)
            entries = LanguageInfo.get_entries(translated=True,
                                               ordered=True,
                                               engine=None)
            count: int = 0
            for key, value in entries.items():
                for lang, lang_values in value.items():
                    count += len(lang_values)

            cls._logger.debug(f'FLOYD # items: {count}')

        except Exception as e:
            cls._logger.exception('')
            entries = {}

        # cls._logger.debug(f'entries:{entries}')
        try:
            """
                We display two views. In both cases they are arranged in 
                the display order of the language family, then language, then
                engine display order. So, if we display only language entries
                in the 'en' language family for every engine we have something like:

                    en English, United States eSpeak
                    en English, United States GoogleTTS 

            """
            tmp: str = xbmc.getLanguage(xbmc.ISO_639_2)
            kodi_language: langcodes.Language
            kodi_language = langcodes.Language.get(tmp)
            kodi_lang: str = kodi_language.language
            kodi_locale: str = kodi_language.to_tag()
            cls._logger.debug(f'FLOYD kodi_language: {kodi_language} '
                              f'Kodi lang: {kodi_lang} '
                              f'kodi_locale: {kodi_locale}')

            #  Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]]
            # sorted_keys: List[Tuple[str, str]] = []
            #
            # Top level dict is indexed by engine-id
            # The value is a Dict, indexed by language_id ('en') with value
            # being a List of every LanguageInfo who's language is within the
            # same family as it's key.
            # So to sort, we need to sort both the second level dict's keys
            # as well as the List of LangInfos

            current_value: str = cls.getSetting(SettingsProperties.LANGUAGE,
                                                 kodi_locale)
            if current_value == 'unknown':
                current_value = kodi_locale
            current_language: langcodes.Language.get(current_value)

            default_setting_index: int = -1
            # cls._logger.debug(f'FLOYD About to sort choices')
            # entries: Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]] = None

            idx: int = 0
            sort_choices: List[Choice] = []
            for engine_id, langs_for_an_engine in entries.items():
                engine_id: str
                # cls._logger.debug(f'FLOYD engine_id: {engine_id}')
                langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
                for lang_family_id, engine_langs_in_family in langs_for_an_engine.items():
                    lang_family_id: str
                    engine_langs_in_family: List[ForwardRef('LanguageInfo')]
                    # cls._logger.debug(f'FLOYD lang_family_id: {lang_family_id}')
                    if lang_family_id != kodi_lang:
                        continue

                    engine_supported_voices: int = 0
                    engine_label: str = ''
                    for lang_info in engine_langs_in_family:
                        lang_info: LanguageInfo
                        # def tag_distance(desired: Union[str, Language],
                        #    supported: Union[str, Language]) -> int:
                        #  closest_supported_match(desired_language,
                        #     supported_languages)
                        #  closest_match(desired_language, supported_language)
                        cls._logger.debug(f'FLOYD lang_info {lang_info.ietf.language}'
                                           f' {lang_info.ietf.territory}')
                        if lang_info.engine_name_msg_id != 0:
                            # TODO: Performance
                            lang_info.translated_engine_name = Messages.get_msg_by_id(
                                    lang_info.engine_name_msg_id)
                        engine_label = lang_info.translated_engine_name

                        engine_supported_voices += 1
                    choice: Choice
                    choice = Choice(label=engine_label, value=engine_id,
                                    choice_index=0)
                    cls._logger.debug(f'choice: {choice}')
                    sort_choices.append(choice)

            # Sort the choices and fix indices

            # cls._logger.debug(f'FLOYD # sort_choices: {len(sort_choices)}')
            sorted_choices: List[Choice]
            sorted_choices = sorted(sort_choices, key=lambda entry: entry.label)
            # cls._logger.debug(f'FLOYD # sort_choices: {len(sorted_choices)}')
            # cls._logger.debug(f'MOOSE choice[0]: {sorted_choices[0].value}')

            idx: int = 0
            for choice in sorted_choices:
                choice: Choice
                if current_choice_index == -1:
                    current_choice_index = idx
                if default_setting_index == -1:
                    default_setting_index = idx
                choices.append(choice)
                # cls._logger.debug(f'choice: {choice.label} {choice.value}')
                idx += 1
                # if idx > 5:
                #     break

            # cls._logger.debug(f'FLOYD current_choice_index: {current_choice_index} '
            #                   f'default_setting_index: {default_setting_index}'
            #                   f' # choices: {len(choices)}')
            # for choice in choices:
            #     cls._logger.debug(f'choices: {choice.label} {choice.value}')

        except Exception as e:
            cls._logger.exception('')
        for choice in choices:
            cls._logger.debug(f'choices: {choice.label} {choice.value}')
        return choices, current_choice_index

    @classmethod
    def get_kodi_locale_info(cls) -> Tuple[str, str, str]:
        """
        Retrieves the currently configured Kodi locale in several formats

        :return: returns [kodi_lang, kodi_locale, kodi_friendly_locale_name]
        """
        tmp: str = xbmc.getLanguage(xbmc.ISO_639_2)
        kodi_language: langcodes.Language
        kodi_language = langcodes.Language.get(tmp)
        kodi_lang: str = kodi_language.language
        kodi_locale: str = kodi_language.to_tag()
        kodi_friendly_locale_name: str = kodi_language.display_name()
        cls._logger.debug(f'kodi_lang: {kodi_lang} \n kodi_locale: {kodi_locale}\n '
                          f'{kodi_friendly_locale_name}')
        kodi_friendly_locale_name = kodi_friendly_locale_name.lower()
        return kodi_lang, kodi_locale, kodi_friendly_locale_name

    @classmethod
    def get_language_choices(cls) -> Tuple[List[Choice], int]:
        """

        :return:
        """
        cls._logger.debug(f'In get_language_choices')
        choices: List[Choice] = []
        current_choice_index: int = -1
        cls.current_language_choices.clear()
        entries: Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]] = None
        try:
            # Get all language entries (engine=None does that)
            entries = LanguageInfo.get_entries(translated=True,
                                               ordered=True,
                                               engine=None)
            count: int = 0
            for key, value in entries.items():
                for lang, lang_values in value.items():
                    count += len(lang_values)
                    cls._logger.debug(f'key: {key} lang:{lang} '
                                      f'# values {len(lang_values)}')

            cls._logger.debug(f'FLOYD # items: {count}')

        except Exception as e:
            cls._logger.exception('')
            entries = {}
        try:
            """
                We display two views. In both cases they are arranged in 
                the display order of the language family, then language, then
                engine display order. So, if we display only language entries
                in the 'en' language family for every engine we have something like:

                    en English, United States eSpeak
                    en English, United States GoogleTTS 

            """
            tmp: str = xbmc.getLanguage(xbmc.ISO_639_2)
            kodi_language: langcodes.Language
            kodi_language = langcodes.Language.get(tmp)
            kodi_lang: str = kodi_language.language
            kodi_locale: str = kodi_language.to_tag()
            cls._logger.debug(f'FLOYD kodi_language: {kodi_language} '
                              f'Kodi lang: {kodi_lang} '
                              f'kodi_locale: {kodi_locale}')

            #  Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]]
            # sorted_keys: List[Tuple[str, str]] = []
            #
            # Top level dict is indexed by engine-id
            # The value is a Dict, indexed by language_id ('en') with value
            # being a List of every LanguageInfo who's language is within the
            # same family as it's key.
            # So to sort, we need to sort both the second level dict's keys
            # as well as the List of LangInfos
            """
            for key, _ in entries.items():
                key: str
                values: List[LanguageInfo]
                display_value: str = (langcodes.Language.get(key).
                                      display_name(language=current_kodi_lang))
                sorted_keys.append((display_value, key))

            sort_keys: List[Tuple[str, str]] = sorted(sorted_keys, key=lambda x: x[0])
            """

            current_value: str = cls.getSetting(SettingsProperties.LANGUAGE,
                                                 kodi_locale)
            if current_value == 'unknown':
                current_value = kodi_locale
            current_language: langcodes.Language.get(current_value)

            default_setting_index: int = -1
            cls._logger.debug(f'FLOYD About to sort choices')
            # entries: Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]] = None

            idx: int = 0
            sort_choices: List[Choice] = []
            for engine_id, langs_for_an_engine in entries.items():
                engine_id: str
                #  cls._logger.debug(f'FLOYD engine_id: {engine_id}')
                langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
                for lang_family_id, engine_langs_in_family in langs_for_an_engine.items():
                    lang_family_id: str
                    engine_langs_in_family: List[ForwardRef('LanguageInfo')]
                    cls._logger.debug(f'FLOYD lang_family_id: {lang_family_id} '
                                      f'kodi_lang: {kodi_lang}')
                    if lang_family_id != kodi_lang:
                        continue

                    for lang_info in engine_langs_in_family:
                        lang_info: LanguageInfo
                        # def tag_distance(desired: Union[str, Language],
                        #    supported: Union[str, Language]) -> int:
                        #  closest_supported_match(desired_language,
                        #     supported_languages)
                        #  closest_match(desired_language, supported_language)
                        # cls._logger.debug(f'FLOYD lang_info {lang_info.ietf.language}'
                        #                   f' {lang_info.ietf.territory}')
                        if lang_info.engine_name_msg_id != 0:
                            # TODO: Performance
                            lang_info.translated_engine_name = Messages.get_msg_by_id(
                                    lang_info.engine_name_msg_id)

                        lang_info.translated_language_name = lang_info.ietf.language_name(
                                language=kodi_language)
                        lang_info.translated_lang_country_name = (
                            lang_info.ietf.territory_name(
                                    language=kodi_language))
                        # Convert 'en-us' to 'English (United States)'
                        # lang_info.translated_locale_name = (
                        #     lang_info.ietf.display_name(
                        #            language=kodi_language))

                        msg_id: Message = GenderSettingsMap.settings_map.get(
                                lang_info.gender)
                        lang_info.translated_gender_name = Messages.get_msg(msg_id)

                        # Get the name of the language in the current language
                        display_current_lang: str = lang_info.ietf.display_name(
                                language=kodi_language)
                        display_current_territory: str = lang_info.ietf.territory_name()
                        # Get name of the language in its native language
                        display_lang_choice: str = lang_info.ietf.autonym()
                        # get how close of a match this language is to
                        # Kodi's setting

                        match_distance: int
                        match_distance = langcodes.tag_distance(desired=kodi_language,
                                                                supported=lang_info.ietf)
                        display_engine_name: str = lang_info.translated_engine_name
                        voice_name: str = lang_info.engine_voice_id
                        label: str
                        if display_lang_choice != display_current_lang:
                            label = (f'{display_engine_name:10} '
                                     f'{display_current_territory:20} / '
                                     f'{display_lang_choice:10} '
                                     f'voice:  {voice_name:20}')
                        else:
                            label = (f' {display_engine_name:10} '
                                     f'{display_current_territory:32}   '
                                     f'voice:  {voice_name:20}')
                        cls._logger.debug(f'FLOYD'
                                           f' {lang_info.translated_lang_country_name} '
                                           f'distance: {match_distance}')
                        key: str = f'{match_distance:3d}{label}'
                        choice: Choice
                        choice = Choice(label=label, value='', choice_index=-1,
                                        sort_key=key, lang_info=lang_info,
                                        match_distance=match_distance)
                        sort_choices.append(choice)


            # Sort the choices and fix indices

            # cls._logger.debug(f'FLOYD # sort_choices: {len(sort_choices)}')
            sorted_choices: List[Choice]
            sorted_choices = sorted(sort_choices, key=lambda chc: chc.sort_key)
            cls._logger.debug(f'FLOYD # sort_choices: {len(sort_choices)}')

            closest_match_index: int = -1
            closest_match: int = 10000
            choice: Choice
            for choice in sorted_choices:
                lang_info: LanguageInfo = choice.lang_info
                locale: str = lang_info.ietf.to_tag()
                lang_id: str = lang_info.language_id
                choice.engine_id = lang_info.engine_id
                choice.idx = idx
                cls.current_language_choices.append(lang_info)
                # cls._logger.debug(f'FLOYD lang_id: {lang_id} current_lang: {kodi_lang}')
                if choice.match_distance < closest_match:
                    closest_match = choice.match_distance
                    closest_match_index = idx
                if current_choice_index == -1 and locale == kodi_locale:
                    current_choice_index = idx
                if default_setting_index == -1 and locale == kodi_locale:
                    default_setting_index = idx
                choices.append(choice)
                cls._logger.debug(f'{choice}')
                idx += 1
                # if idx > 5:
                #     break

            cls._logger.debug(f'FLOYD current_choice_index: {current_choice_index} '
                              f'default_setting_index: {default_setting_index} '
                              f'closest_match_idx: {closest_match_index} '
                              f'closest_match: {closest_match}')
            if current_choice_index == -1:
                current_choice_index = closest_match_index
                # current_choice_index = default_setting_index

        except Exception as e:
            cls._logger.exception('')
        return choices, current_choice_index

    @classmethod
    def getSetting(cls, setting_id, default=None):
        """

        :param setting_id:
        :param default:
        :return:
        """
        engine: ITTSBackendBase = cls.getEngineClass(cls.engine_id)
        value = None
        try:
            if default is None:
                default = engine.get_setting_default(setting_id)
            value = engine.getSetting(setting_id, default)
        except AttributeError:
            value = None
        return value

    @classmethod
    def getEngineClass(cls, engine_id=None) -> ITTSBackendBase:
        """

        :param engine_id:
        :return:
        """
        if engine_id is None:
            engine_id = cls.engine_id
        if cls.engine_instance is None or cls.engine_instance.backend_id != engine_id:
            backend_id: str = None
            if cls.engine_instance is not None:
                backend_id = cls.engine_instance.backend_id
            cls._logger.debug(f'engine_id changed: {engine_id} was {backend_id}')

            cls.engine_instance = BaseServices.getService(engine_id)
        return cls.engine_instance


SettingsHelper.init_class()
