# coding=utf-8
import re
from collections import UserList
from pathlib import Path

from common.messages import Messages
from common.typing import *


class Phrase:
    """
    A Phrase is a series of words that may be a subset of the complete text to
    be voiced. When voiced text is cached, it can be beneficial to break
    the text up into phrases so that the variant part (say, the run-time hours
    and minutes) can be kept in separate phrases from the rest of the text so
    that there are not possibly hundreds of copies of nearly the same message
    with only the time being different.

    When caching is not used, then phrases be merged with other non-interrupting
    phrases.
    """
    PAUSE_NORMAL: int = 500
    PAUSE_DEFAULT: int = 0
    PAUSE_WORD: int = 0
    PAUSE_SENTENCE: int = 0
    PAUSE_PARAGRAPH: int = 0
    PAUSE_SHORT: int = 0
    PAUSE_LONG: int = 0


    _formatTagRE = re.compile(r'\[/?(?:CR|B|I|UPPERCASE|LOWERCASE)\](?i)')
    _colorTagRE = re.compile(r'\[/?COLOR[^\]\[]*?\](?i)')
    _okTagRE = re.compile(r'(^|\W|\s)OK($|\s|\W)')  # Prevents saying Oklahoma


    def __init__(self, text: str, interrupt: bool = False, pre_pause_ms: int = None,
                 post_pause_ms: int = None,
                 cache_path: Path = None, exists: bool = False,
                 preload_cache: bool = False):
        clz = type(self)
        self.text: str = clz.clean_text(text)
        self.cache_path: Path = cache_path
        self.exists: bool = exists
        self.interrupt: bool = interrupt
        if pre_pause_ms is None:
            self.pre_pause_ms = 0
        if post_pause_ms is None:
            post_pause_ms = clz.PAUSE_DEFAULT
        self.post_pause_ms: int = post_pause_ms
        self.preload_cache = preload_cache

    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text

    def set_cache_path(self, cache_path: Path, exists: bool):
        self.cache_path = cache_path
        self.exists = exists

    def get_cache_path(self) -> Path:
        return self.cache_path

    def is_exists(self) -> bool:
        return self.exists

    def set_exists(self, exists: bool) -> None:
        self.exists = exists

    def get_interrupt(self) -> bool:
        return self.interrupt

    def set_interrupt(self, interrupt: bool) -> None:
        self.interrupt = interrupt

    def get_pre_pause(self) -> int:
        return self.pre_pause_ms

    def set_pre_pause(self, pre_pause_ms: int) -> None:
        self.pre_pause_ms = pre_pause_ms

    def get_post_pause(self) -> int:
        return self.post_pause_ms

    def set_post_pause(self, post_pause_ms: int) -> None:
        self.post_pause_ms = post_pause_ms

    def is_preload_cache(self) -> bool:
        return self.is_preload_cache()

    def set_preload_cache(self, preload_cache:bool):
        self.preload_cache = preload_cache

    @classmethod
    def clean_text(cls, text):
        text = cls._formatTagRE.sub('', text)
        text = cls._colorTagRE.sub('', text)
        # Some speech engines say OK as Oklahoma
        text = cls._okTagRE.sub(r'\1O K\2', text)
        # getLabel() on lists wrapped in [] and some speech engines have
        # problems with text starting with -
        text = text.strip('-[]')
        text = text.replace('XBMC', 'Kodi')
        if text == '..':
            text = Messages.get_msg(Messages.PARENT_DIRECTORY)
        return text


class PhraseList(UserList[Phrase]):

    def __init__(self, initlist: Iterable[Phrase] | None = []) -> None:
        super().__init__(initlist)
        self.phrase_index: int = 0

    @classmethod
    def create(cls, phrases: str | List[str], interrupt: bool) -> 'PhraseList':
        new_phrase_list: PhraseList = PhraseList()
        if isinstance(phrases, str):
            phrases = [phrases]

        for text in phrases:
            text: str
            phrase: Phrase = Phrase(text=text)
            phrases.append(phrase)

        phrase: Phrase = phrases[0]
        phrase.set_interrupt = interrupt
        return phrases

    def compact_phrase(self, start_index: int = None) -> Phrase:
        """
        concatinates the text from one or more adjacent phrases beginning
        with the phrase at start_index and subsequent phrases with
        pause <= PAUSE_NORMAL, or the last phrase in the list.

        If start_index is None or missing, then it is set to index following
        the previous compacted phrase, or index 0 if there was no prior
        call to compact_phrase

        The returned phrase will have:
            a text value of the concatenated phrases that were compacted
            a interrupt field equal to the first phrase compacted
            a delay field equal to the last phrase compacted
            an empty cache path
            a cached value of False

        :param start_index:
        """
        if start_index is not None:
            self.phrase_index = start_index

        current_phrase: Phrase = self.__getitem__(start_index)
        compact_phrase: Phrase
        compact_phrase = Phrase(current_phrase.get_text(),
                                current_phrase.get_interrupt(),
                                current_phrase.get_post_pause(),
                                None,
                                False)
        if compact_phrase.get_post_pause() > Phrase.PAUSE_NORMAL:
            return compact_phrase

        while self.phrase_index < len(self):
            current_phrase = self.__getitem__(self.phrase_index)
            #  Other than the first phrase, none should be marked interrupt, if
            #  so, then throw away previous phrase and start with this one.

            if not current_phrase.get_interrupt():
                text: str = f'{compact_phrase.get_text()} ' \
                            f'{current_phrase.get_text()}'
                compact_phrase.set_text(text)
                compact_phrase.set_interrupt = current_phrase.get_interrupt()

            compact_phrase.set_pause(current_phrase.get_post_pause())
            if compact_phrase.get_post_pause() > Phrase.PAUSE_NORMAL:
                return compact_phrase

    def compact_phrases(self) -> 'PhraseList':
        """
        Produces a new list composed of the compacted phrases from this list
        :return: A PhraseList of one or more phrases
        """

        new_list: PhraseList = PhraseList()
        phrase = self.compact_phrase(0)
        next_phrase: Phrase = self.compact_phrase()
        while next_phrase is not None:
            if not next_phrase.get_interrupt():
                new_list.append(phrase)
            phrase = next_phrase

        return new_list

    def set_all_preload_cache(self, preload: bool) -> None:
        p: Phrase
        for p in self.data:
            p.set_preload_cache(preload)
