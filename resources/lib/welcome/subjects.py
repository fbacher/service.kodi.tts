# coding=utf-8
from __future__ import annotations

"""
Contains subject matter for the user to learn about how to use Kodi TTS as well
as a bit about Kodi itself. This is NOT an exhaustive user's guide but is meant
to get a user started and answer common questions.

Make compatible with the Kodi's message system. An individual subject will have
an id and contain two message ids: one for the subject title and another for
the subject details.

A subject category will have a category id, a message id for the category
title and a number of subject or category ids.
"""
from enum import auto, Enum

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from typing import Dict, ForwardRef, List, Tuple, Union

import xbmcaddon

from common.constants import Constants
from common.critical_settings import CriticalSettings
from common.logger import BasicLogger

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_logger(__name__)

else:
    module_logger = BasicLogger.get_logger(__name__)


class MessageRef(Enum):
    """
    Provides means for message numbers to have names
    """
    RETURN_TO_PREVIOUS_MENU = 32858
    INTRODUCTION = 32824
    INTRODUCTION_TEXT = 32825
    WINDOWS_TTS = 32826
    WINDOWS_TTS_TEXT = 32827
    WELCOME_TTS = 32828
    WELCOME_TTS_TEXT = 32829

    KEYBOARD_MAPPINGS_CAT = 32830
    KEYBOARD_MAPPINGS = 32830
    KEYBOARD_MAPPINGS_TEXT = 32831
    PREDEFINED_MAPPINGS = 32832
    PREDEFINED_MAPPINGS_TEXT = 32855
    PREDEFINED_OPEN_SETTINGS = 32833
    PREDEFINED_OPEN_SETTINGS_TEXT = 32834
    PREDEFINED_VOICE_HINTS = 32835
    PREDEFINED_VOICE_HINTS_TEXT = 32836
    PREDEFINED_REPEAT = 32837
    PREDEFINED_REPEAT_TEXT = 32838
    PREDEFINED_VERBOSITY = 32839
    PREDEFINED_VERBOSITY_TEXT = 32840
    PREDEFINED_HELP = 32841
    PREDEFINED_HELP_TEXT = 32842
    PREDEFINED_TOGGLE_VOICING = 32843
    PREDEFINED_TOGGLE_VOICING_TEXT = 32844
    PREDEFINED_TOGGLE_TTS = 32845
    PREDEFINED_TOGGLE_TTS_TEXT = 32846
    PREDEFINED_INCREASE_VOLUME = 32847
    PREDEFINED_INCREASE_VOLUME_TEXT = 32848
    PREDEFINED_DECREASE_VOLUME = 32849
    PREDEFINED_DECREASE_VOLUME_TEXT = 32850
    PREDEFINED_INCREASE_SPEED = 32851
    PREDEFINED_INCREASE_SPEED_TEXT = 32852
    PREDEFINED_DECREASE_SPEED = 32853
    PREDEFINED_DECREASE_SPEED_TEXT = 32854

    def get_msg(self) -> str:
        # module_logger.debug(f'MessageRef: {self} value: {self.value}')
        return Utils.get_msg(self.value)


class SubjectRef(StrEnum):
    """
    Provides means for Subjects to have unique names for ids

    """
    INTRODUCTION = auto()
    WINDOWS_TTS = auto()
    WELCOME_TTS = auto()
    KEYBOARD_MAPPINGS = auto()
    # KEYBOARD_MAPPINGS_TEXT = auto()
    PREDEFINED_MAPPINGS = auto()
    PREDEFINED_OPEN_SETTINGS = auto()
    # PREDEFINED_OPEN_SETTINGS_TEXT = auto()
    PREDEFINED_VOICE_HINTS = auto()
    # PREDEFINED_VOICE_HINTS_TEXT = auto()
    PREDEFINED_REPEAT = auto()
    # PREDEFINED_REPEAT_TEXT = auto()
    PREDEFINED_VERBOSITY = auto()
    # PREDEFINED_VERBOSITY_TEXT = auto()
    PREDEFINED_HELP = auto()
    # PREDEFINED_HELP_TEXT = auto()
    PREDEFINED_TOGGLE_VOICING = auto()
    # PREDEFINED_TOGGLE_VOICING_TEXT = auto()
    PREDEFINED_TOGGLE_TTS = auto()
    # PREDEFINED_TOGGLE_TTS_TEXT = auto()
    PREDEFINED_INCREASE_VOLUME = auto()
    # PREDEFINED_INCREASE_VOLUME_TEXT = auto()
    PREDEFINED_DECREASE_VOLUME = auto()
    # PREDEFINED_DECREASE_VOLUME_TEXT = auto()
    PREDEFINED_INCREASE_SPEED = auto()
    # PREDEFINED_INCREASE_SPEED_TEXT = auto()
    PREDEFINED_DECREASE_SPEED = auto()
    # PREDEFINED_DECREASE_SPEED_TEXT = auto()


class CategoryRef(StrEnum):
    WELCOME_TTS = auto()
    KEYBOARD_MAPPINGS_CAT = auto()


class Subject:
    """
    Encapsulates one subject.

    """
    subject_map: Dict[str, ForwardRef('Subject')] = {}

    def __init__(self, subject_id: SubjectRef, name_id: MessageRef,
                 text_id: MessageRef):
        """
        Currently statically built

        :param subject_id: Identifies this subject.
        :param name_id: message id for the subject title
        :param text_id:  message id for the subject text
        """
        clz = Subject
        self.subject_id: SubjectRef = subject_id
        self.name_id: MessageRef = name_id
        self.text_id: MessageRef = text_id
        clz.subject_map[subject_id] = self

    def get_name(self) -> str:
        name: str = self.name_id.get_msg()
        return name

    def get_text(self) -> str:
        return self.text_id.get_msg()

    @classmethod
    def get_subject(cls,
                    subject_ref: SubjectRef) -> Union[ForwardRef('Subject'), None]:
        # for k, v in cls.subject_map.items():
        #     module_logger.debug(f'key: {k} {type(k)} value: {v}')

        value = cls.subject_map.get(subject_ref)
        # module_logger.debug(f'subject_ref: {subject_ref} value: {value}')
        return value

    def __repr__(self) -> str:
        subject_id_str = ''
        if self.subject_id is not None:
            subject_id_str = f'\n  category_id: {self.subject_id}'
        name_id_str = ''
        if self.name_id is not None:
            name_id_str = f'\n  name_id: {self.name_id}'
        text_id_str = ''
        if self.text_id is not None:
            text_id_str = f'\n  text_id: {self.text_id}'
        result: str = (f'Category: '
                       f'{subject_id_str}'
                       f'{name_id_str}'
                       f'{text_id_str}')
        return result


class Category:
    """
    Encapsulates a group of subjects and categories. Currently, statically built.
    """

    category_map: Dict[CategoryRef, ForwardRef('Category')] = {}

    def __init__(self, category_id: CategoryRef,
                 name_id: MessageRef,
                 text_id: MessageRef,
                 subject_ids: List[SubjectRef | CategoryRef]):
        self.category_id: CategoryRef = category_id
        self.name_id: MessageRef = name_id
        self.text_id: MessageRef = text_id
        self.subject_ids: List[SubjectRef | CategoryRef] = subject_ids
        Category.category_map[category_id] = self
        module_logger.debug(f'cat_id: {category_id} '
                            f'cat: {self}')
        # for p in self.subject_ids:
        #     module_logger.debug(f'{p} type: {type(p)} subRef: '
        #                         f'{isinstance(p, SubjectRef)} catref: '
        #                         f'{isinstance(p, CategoryRef)} '
        #                         f'MessageRef: {isinstance(p, MessageRef)}')

    def get_name(self) -> str:
        """
            Message ids come from MessageRef
            There are always a pair of MessgeRefs:
                MESSAGE_REF for the label
                MESSAGE_REF_TEXT for the text

        """
        name: str = self.name_id.get_msg()
        return name

    def get_text(self) -> str:
        name: str = self.text_id.get_msg()
        return name

    def get_choices(self) -> Tuple[str, str, List[SubjectRef | CategoryRef]]:
        # module_logger.debug(f'name {self.get_name()} '
        #                     f'subject_ids: {self.subject_ids}')
        '''
        for p in self.subject_ids:
            module_logger.debug(f'{p} type: {type(p)} subRef: '
                                f'{isinstance(p, SubjectRef)} catref: '
                                f'{isinstance(p, CategoryRef)} '
                                f'MessageRef: {isinstance(p, MessageRef)}')
        '''
        return self.get_name(), self.get_text(), self.subject_ids

    @classmethod
    def get_category(cls, category_ref: CategoryRef) -> ForwardRef('Category'):
        module_logger.debug(f'category_ref: {category_ref} map: '
                            f'{cls.category_map.get(category_ref)}')
        return cls.category_map.get(category_ref)

    def __repr__(self) -> str:
        category_id_str = ''
        if self.category_id is not None:
            category_id_str = f'\n  category_id: {self.category_id}'
        name_id_str = ''
        if self.name_id is not None:
            name_id_str = f'\n  name_id: {self.name_id} name: {self.get_name()}'
        text_id_str = ''
        if self.text_id is not None:
            text_id_str = f'\n  text_id: {self.text_id} text: {self.get_text()}'
        result: str = (f'Category: '
                       f'{category_id_str}'
                       f'{name_id_str}'
                       f'{text_id_str}')
        for p in self.subject_ids:
            result = f'{result}\n{p}'
        return result


class Utils:

    @classmethod
    def get_msg(cls, msg_id: int) -> str:
        text: str = CriticalSettings.ADDON.getLocalizedString(msg_id)
        return text


class Load:

    @staticmethod
    def load_help():

        module_logger.debug(f'In Load')

        intro: Subject
        intro = Subject(SubjectRef.INTRODUCTION, MessageRef.INTRODUCTION,
                        MessageRef.INTRODUCTION_TEXT)
        windows_tts: Subject
        windows_tts = Subject(SubjectRef.WINDOWS_TTS, MessageRef.WINDOWS_TTS,
                              MessageRef.WINDOWS_TTS_TEXT)
        Subject(SubjectRef.WELCOME_TTS, MessageRef.WELCOME_TTS,
                MessageRef.WELCOME_TTS_TEXT)
        Subject(SubjectRef.KEYBOARD_MAPPINGS, MessageRef.KEYBOARD_MAPPINGS,
                MessageRef.KEYBOARD_MAPPINGS_TEXT)
        Subject(SubjectRef.PREDEFINED_MAPPINGS, MessageRef.PREDEFINED_MAPPINGS,
                MessageRef.PREDEFINED_MAPPINGS_TEXT)
        Subject(SubjectRef.PREDEFINED_OPEN_SETTINGS,
                MessageRef.PREDEFINED_OPEN_SETTINGS,
                MessageRef.PREDEFINED_OPEN_SETTINGS_TEXT)
        Subject(SubjectRef.PREDEFINED_VOICE_HINTS, MessageRef.PREDEFINED_VOICE_HINTS,
                MessageRef.PREDEFINED_VOICE_HINTS_TEXT)
        Subject(SubjectRef.PREDEFINED_REPEAT, MessageRef.PREDEFINED_REPEAT,
                MessageRef.PREDEFINED_REPEAT_TEXT)
        Subject(SubjectRef.PREDEFINED_VERBOSITY, MessageRef.PREDEFINED_VERBOSITY,
                MessageRef.PREDEFINED_VERBOSITY_TEXT)
        Subject(SubjectRef.PREDEFINED_HELP, MessageRef.PREDEFINED_HELP,
                MessageRef.PREDEFINED_HELP_TEXT)
        Subject(SubjectRef.PREDEFINED_TOGGLE_VOICING,
                MessageRef.PREDEFINED_TOGGLE_VOICING,
                MessageRef.PREDEFINED_TOGGLE_VOICING_TEXT)
        Subject(SubjectRef.PREDEFINED_TOGGLE_TTS, MessageRef.PREDEFINED_TOGGLE_TTS,
                MessageRef.PREDEFINED_TOGGLE_TTS_TEXT)
        Subject(SubjectRef.PREDEFINED_INCREASE_VOLUME,
                MessageRef.PREDEFINED_INCREASE_VOLUME,
                MessageRef.PREDEFINED_INCREASE_VOLUME_TEXT)
        Subject(SubjectRef.PREDEFINED_DECREASE_VOLUME,
                MessageRef.PREDEFINED_DECREASE_VOLUME,
                MessageRef.PREDEFINED_DECREASE_VOLUME_TEXT)
        Subject(SubjectRef.PREDEFINED_INCREASE_SPEED,
                MessageRef.PREDEFINED_INCREASE_SPEED,
                MessageRef.PREDEFINED_INCREASE_SPEED_TEXT)
        Subject(SubjectRef.PREDEFINED_DECREASE_SPEED,
                MessageRef.PREDEFINED_DECREASE_SPEED,
                MessageRef.PREDEFINED_DECREASE_SPEED_TEXT)

        subjects: List[SubjectRef] = [SubjectRef.INTRODUCTION,
                                      SubjectRef.WELCOME_TTS,
                                      CategoryRef.KEYBOARD_MAPPINGS_CAT]
        top_cat: Category
        top_cat = Category(CategoryRef.WELCOME_TTS, MessageRef.WELCOME_TTS,
                           MessageRef.WELCOME_TTS_TEXT, subjects)

        keyboard_subjects: List[SubjectRef] = [SubjectRef.KEYBOARD_MAPPINGS,
                                               SubjectRef.PREDEFINED_MAPPINGS,
                                               SubjectRef.PREDEFINED_OPEN_SETTINGS,
                                               SubjectRef.PREDEFINED_VOICE_HINTS,
                                               SubjectRef.PREDEFINED_REPEAT,
                                               SubjectRef.PREDEFINED_VERBOSITY,
                                               SubjectRef.PREDEFINED_HELP,
                                               SubjectRef.PREDEFINED_TOGGLE_VOICING,
                                               SubjectRef.PREDEFINED_TOGGLE_TTS,
                                               SubjectRef.PREDEFINED_INCREASE_VOLUME,
                                               SubjectRef.PREDEFINED_DECREASE_VOLUME,
                                               SubjectRef.PREDEFINED_INCREASE_SPEED,
                                               SubjectRef.PREDEFINED_DECREASE_SPEED
                                               ]
        keyboard_cat: Category
        keyboard_cat = Category(CategoryRef.KEYBOARD_MAPPINGS_CAT,
                                MessageRef.KEYBOARD_MAPPINGS_CAT,
                                MessageRef.KEYBOARD_MAPPINGS_TEXT,
                                keyboard_subjects)

        module_logger.debug('Done loaded')

        for subj_ref in SubjectRef:
            subj_ref: SubjectRef
            subject: Subject = Subject.get_subject(subj_ref)
            # module_logger.debug(f'sub_ref: {subj_ref}\n'
            #                     f'{subject}')

        for cat_ref in CategoryRef:
            cat_ref: CategoryRef
            category: Category = Category.get_category(cat_ref)
            # module_logger.debug(f'cat_ref: {cat_ref}\n'
            #                     f'category: {category}')
