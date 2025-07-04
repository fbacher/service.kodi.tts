# coding=utf-8
from typing import ForwardRef, List

from backends.settings.language_info import LanguageInfo
from backends.settings.service_types import ServiceID
from common.logger import *

MY_LOGGER = BasicLogger.get_logger(__name__)


class Choice:
    """
    Encapsulates information for making a settings choice.

    Typicaly contains display_value, id and choice_index. May contain more
    items, as needed. By containing the choice variants here, the users of this
    class don't have to change whenever a new variant is is_required.
    """

    def __init__(self, label: str, value: str, choice_index: int,
                 sort_key: str = None, enabled: bool = True,
                 engine_key: ServiceID = None, lang_info: LanguageInfo = None,
                 match_distance: int = 1000, hint: str = None) -> None:
        """

        :param label: User friendly, translated label
        :param hint: User friendly, translated hint
        :param value: value used in settings, etc.
        :param choice_index: When from a list of choices, this is its place in list.
        :param sort_key:  Key to use when sorting list
        :param enabled:   Some settings may not be useable depending on other settings
                          We want to include disabled choices to show a consistent list,
                          but marked in UI as disabled
        :param engine_key: Identifies which engine this setting is associated with
        :param lang_info: language information for language-related settings.
        :param match_distance: for language related settings. Represents how close
                               this choice is to the desired language. For example,
                               a voice for en-GB is not as close to en-US as a
                               en-US one, but close enough to use. Comes from
                               langcodes.
        """
        if sort_key is None:
            sort_key = label

        self.label: str = label
        self.hint: str = hint
        self.value: str = value
        self.choice_index: int = choice_index
        self.engine_key: ServiceID = engine_key
        self.lang_info: LanguageInfo = lang_info
        self.sort_key: str = sort_key
        self.enabled: bool = enabled
        self.match_distance: int = match_distance

    @classmethod
    def dbg_print(cls, choices: List[ForwardRef('Choice')]) -> None:
        for choice in choices:
            choice: Choice
            MY_LOGGER.debug(f'Choice {choice}')
            MY_LOGGER.debug('')

    def __str__(self) -> str:
        result: str = (f'idx: {self.choice_index} label: {self.label} value:'
                       f' {self.value}\n'
                       f'service_id: {self.engine_key} lang_info: {self.lang_info}')
        return result

    def __rpr__(self) -> str:
        return self.__str__()
