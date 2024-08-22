from backends.settings.language_info import LanguageInfo


class Choice:
    """
    Encapsulates information for making a settings choice.

    Typicaly contains display_value, id and choice_index. May contain more
    items, as needed. By containing the choice variants here, the users of this
    class don't have to change whenever a new variant is is_required.
    """

    def __init__(self, label: str, value: str, choice_index: int,
                 sort_key: str = None, enabled: bool = True,
                 engine_id: str = '', lang_info: LanguageInfo = None,
                 match_distance: int = 1000) -> None:
        """

        :param label: User friendly, translate label
        :param value: value used in settings, etc.
        :param choice_index: When from a list of choices, this is its place in list.
        :param sort_key:  Key to use when sorting list
        :param enabled:   Some settings may not be useable depending on other settings
                          We want to include disabled choices to show a consistent list,
                          but marked in UI as disabled
        :param engine_id: Identifies which engine this setting is associated with
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
        self.value: str = value
        self.choice_index: int = choice_index
        self.engine_id: str = engine_id
        self.lang_info: LanguageInfo = lang_info
        self.sort_key: str = sort_key
        self.enabled: bool = enabled
        self.match_distance: int = match_distance

    def __repr__(self) -> str:
        result: str = (f'label: {self.label} value: {self.value} idx: {self.choice_index}\n'
                       f'engine_id: {self.engine_id} lang_info: {self.lang_info}')
        return result
