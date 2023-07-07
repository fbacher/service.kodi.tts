# coding=utf-8

#  TODO: change to regex

import re
from collections import UserList
from pathlib import Path

from common.exceptions import ExpiredException
from common.logger import BasicLogger
from common.messages import Messages
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


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
    PAUSE_NORMAL: int = 125
    PAUSE_DEFAULT: int = 0
    PAUSE_WORD: int = 0
    PAUSE_SENTENCE: int = 0
    PAUSE_PARAGRAPH: int = 0
    PAUSE_SHORT: int = 0
    PAUSE_LONG: int = 0

    _formatTagRE = re.compile(r'\[/?(?:CR|B|I|UPPERCASE|LOWERCASE)](?i)')
    _colorTagRE = re.compile(r'\[/?COLOR[^]\[]*?](?i)')
    _okTagRE = re.compile(r'(^|\W|\s)OK($|\s|\W)')  # Prevents saying Oklahoma
    _logger: BasicLogger = None

    def __init__(self, text: str = '', interrupt: bool = False, pre_pause_ms: int = None,
                 post_pause_ms: int = None,
                 cache_path: Path = None, exists: bool = False,
                 preload_cache: bool = False):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        self.text: str = clz.cleanPhraseext(text)
        self.cache_path: Path = cache_path
        self.exists: bool = exists
        self.interrupt: bool = interrupt
        if pre_pause_ms is None:
            pre_pause_ms = 0
        self.pre_pause_ms = pre_pause_ms
        if post_pause_ms is None:
            post_pause_ms = clz.PAUSE_DEFAULT
        self.post_pause_ms: int = post_pause_ms
        self.preload_cache = preload_cache
        self.serial_number: int = PhraseList.global_serial_number

        # PhraseList can disable expiration checking when you explicitly
        # make an unchecked clone. Useful for seeding a cache for the future

        self.check_expired: bool = True


    @classmethod
    def new_instance(cls, text: str = '', interrupt: bool = False,
                     pre_pause_ms: int = None,
                     post_pause_ms: int = None,
                     cache_path: Path = None, exists: bool = False,
                     preload_cache: bool = False) -> ForwardRef('Phrase'):
        text: str = cls.cleanPhraseext(text)
        if len(text) == 0:
            return None
        return Phrase(text=text, interrupt=interrupt, pre_pause_ms=pre_pause_ms,
                      post_pause_ms=post_pause_ms, cache_path=cache_path)

    def clone(self, check_expired: bool = True) -> 'Phrase':
        phrase: Phrase
        phrase = Phrase(text=self.text, interrupt=self.interrupt,
                      pre_pause_ms=self.pre_pause_ms,
                      post_pause_ms=self.post_pause_ms,
                      cache_path=self.cache_path,
                      exists=self.exists, preload_cache=self.preload_cache)
        phrase.check_expired = check_expired
        return phrase


    def to_dict(self) -> str:
        """
            TODO: do a cleaner job of json encode/decode
        :return:
        """
        tmp: Dict[str, Any] = {
            'text'         : self.text,
            'interrupt'    : self.interrupt,
            'pre_pause_ms' : self.pre_pause_ms,
            'post_pause_ms': self.post_pause_ms,
            'cache_path'   : self.cache_path,
            'exists'       : self.exists,
            'preload_cache': self.preload_cache
        }

    @classmethod
    def create(cls, params: Dict[str, Any]) -> 'Phrase':
        # params: Dict[str, Any] = from_dict.get('phrase')
        phrase: Phrase = Phrase(text=params.get('text'),
                                interrupt=params.get('interrupt'),
                                pre_pause_ms=params.get('pre_pause_ms'),
                                post_pause_ms=params.get('post_pause_ms'),
                                cache_path=params.get('cache_path'),
                                exists=params.get('exists'),
                                preload_cache=params.get('preload_cache'))
        return phrase

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

    def set_preload_cache(self, preload_cache: bool):
        self.preload_cache = preload_cache

    def get_serial_num(self) -> int:
        return self.serial_number

    @classmethod
    def cleanPhraseext(cls, text):
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

    @classmethod
    def from_json(cls, json_object: Any):
        if isinstance(json_object, dict):
            if 'phrase' in json_object:
                return cls.create(json_object.get('phrase'))
        return json_object

    @classmethod
    def set_expired(cls, phrase_or_list):
        if isinstance(phrase_or_list, Phrase):
            phrase: Phrase = phrase_or_list
            if PhraseList.expired_serial_number < phrase.serial_number:
                cls.expired_serial_number = phrase.serial_number
        elif isinstance(phrase_or_list, PhraseList):
            phrases: PhraseList = phrase_or_list
            if PhraseList.expired_serial_number < phrases.serial_number:
                cls.expired_serial_number = phrases.serial_number

        # Just to make sure that global_serial_number is > expired_serial_number

        if PhraseList.expired_serial_number >= PhraseList.global_serial_number:
            PhraseList.global_serial_number = PhraseList.expired_serial_number + 1

    def is_expired(self) -> bool:
        clz = type(self)
        if not self.check_expired:
            return False
        if PhraseList.expired_serial_number >= self.serial_number:
            return True
        return False

    def test_expired(self) -> None:
        if self.is_expired():
            raise ExpiredException()


class PhraseList(UserList[Phrase]):
    # To aid in throwing away text which is no longer relevant due to the
    # changing UI, every PhraseList has a serial number. Each Phrase in that
    # PhraseList is assigned the PhraseList's serial number. This makes it
    # easy to say "reject every phrase before this serial number"

    global_serial_number: int = 1
    expired_serial_number: int = 0
    _logger: BasicLogger = None
    def __init__(self, check_expired: bool = True) -> None:
        super().__init__()
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)

        clz.global_serial_number += 1
        self.serial_number: int = clz.global_serial_number
        self.check_expired = check_expired

    @classmethod
    def create(cls, texts: str | List[str], interrupt: bool = False,
               preload_cache: bool = False) -> 'PhraseList':
        if not isinstance(texts, str):
            raise TypeError('Expected list of strings')

        if not isinstance(texts, list):
            texts = [texts]

        phrases: PhraseList = PhraseList()
        pre_pause: int = 0
        for text in texts:
            text: str | int
            if isinstance(text, int):
                pre_pause = text
                continue
            text: str = Phrase.cleanPhraseext(text)

            # Drop any empty text

            if len(text) != 0:
                phrase: Phrase = Phrase(text=text, preload_cache=preload_cache,
                                        pre_pause_ms = pre_pause)
                pre_pause = 0
                phrase.serial_number = phrases.serial_number
                phrases.append(phrase)

        phrase: Phrase = phrases[0]
        phrase.set_interrupt = interrupt
        return phrases

    def clone(self, check_expired: bool = True) -> 'PhraseList':
        phrases: PhraseList = PhraseList(check_expired=check_expired)
        phrase: Phrase
        for phrase in self.data:
            new_phrase: Phrase = phrase.clone(check_expired=check_expired)
            phrases.append(new_phrase)

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
        if start_index is None:
            start_index = 0
        phrase_index = start_index

        current_phrase: Phrase = self.data[start_index]
        compact_phrase: Phrase
        compact_phrase = Phrase(current_phrase.get_text(),
                                current_phrase.get_interrupt(),
                                current_phrase.get_pre_pause(),
                                current_phrase.get_post_pause(),
                                cache_path=None,
                                exists=False,
                                preload_cache=current_phrase.is_preload_cache())
        if compact_phrase.get_post_pause() > Phrase.PAUSE_NORMAL:
            return compact_phrase

        while phrase_index < len(self):
            current_phrase = self.data[phrase_index]
            #  Other than the first phrase, none should be marked interrupt, if
            #  so, then throw away previous phrase and start with this one.

            if not current_phrase.get_interrupt():
                text: str = f'{compact_phrase.get_text()} ' \
                            f'{current_phrase.get_text()}'
                compact_phrase.set_text(text)
                compact_phrase.set_interrupt = current_phrase.get_interrupt()

            compact_phrase.set_post_pause(current_phrase.get_post_pause())
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

    @classmethod
    def set_current_expired(cls) -> None:
        cls.expired_serial_number = cls.global_serial_number

    def set_expired(self) -> None:
        clz = type(self)
        if clz.expired_serial_number < self.serial_number:
            clz.expired_serial_number = self.serial_number

        # Just to make sure that global_serial_number is > expired_serial_number

        if clz.expired_serial_number >= clz.global_serial_number:
            clz.global_serial_number = clz.expired_serial_number + 1

    def is_expired(self) -> bool:
        clz = type(self)
        if not self.check_expired:
            return False
        return clz.expired_serial_number >= self.serial_number

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, PhraseList):
            raise TypeError('Must be PhraseList')
        other: PhraseList
        if self.is_expired() or other.is_expired():
            raise ExpiredException()
        return super().__lt__(other)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, PhraseList):
            raise TypeError('Must be PhraseList')
        other: PhraseList
        if self.is_expired() or other.is_expired():
            raise ExpiredException()
        return super().__le__(other)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, PhraseList):
            raise TypeError('Must be PhraseList')
        other: PhraseList
        if self.is_expired() or other.is_expired():
            raise ExpiredException()
        return super().__gt__(other)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, PhraseList):
            raise TypeError('Must be PhraseList')
        other: PhraseList
        if self.is_expired() or other.is_expired():
            raise ExpiredException()
        return super().__ge__(other)

    def __contains__(self, item: object) -> bool:
        if not isinstance(item, PhraseList):
            raise TypeError('Must be PhraseList')
        item: PhraseList
        if self.is_expired() or item.is_expired():
            raise ExpiredException()
        return super().__contains__(item)

    def __len__(self) -> int:
        if self.is_expired():
            raise ExpiredException()
        return super().__len__()

    def __getitem__(self: 'PhraseList', i: slice | int) -> Phrase:
        if self.is_expired():
            raise ExpiredException()
        return super().__getitem__(i)

    def __setitem__(self, i: slice | int, o: Phrase | Iterable[Phrase]) -> None:
        if self.is_expired():
            raise ExpiredException()
        return super().__setitem__(i, o)

    def __delitem__(self, i: int | slice) -> None:
        if self.is_expired():
            raise ExpiredException()
        return super().__delitem__(i)

    def __add__(self, other: Iterable[Phrase]) -> None:
        if self.is_expired():
            raise ExpiredException()
        return super().__add__(other)

    def __iadd__(self, other: Iterable[Phrase]) -> None:
        if self.is_expired():
            raise ExpiredException()
        return super().__iadd__(other)

    def __mul__(self, n: int):
        if self.is_expired():
            raise ExpiredException()
        return super().__mul__(n)

    def __imul__(self, n: int):
        if self.is_expired():
            raise ExpiredException()
        return super().__imul__(n)

    def append(self, item: Phrase) -> None:
        if not isinstance(item, Phrase):
            raise TypeError('Expected a Phrase')
        if self.is_expired():
            raise ExpiredException()
        item: Phrase
        if item.is_expired():
            raise ExpiredException()
        return self.data.append(item)

    def insert(self, i: int, item: Phrase) -> None:
        if not isinstance(item, Phrase):
            raise TypeError('Expected a Phrase')
        if self.is_expired():
            raise ExpiredException()
        return super().insert(i, item)

    def pop(self, i: int = ...) -> Phrase:
        if self.is_expired():
            raise ExpiredException()
        return super().pop(i)

    def remove(self, item: Phrase) -> None:
        if self.is_expired():
            raise ExpiredException()
        return super().remove(item)

    def clear(self) -> None:
        if self.is_expired():
            raise ExpiredException()
        return super().clear()

    def copy(self) -> 'PhraseList':
        if self.is_expired():
            raise ExpiredException()
        return super().copy()

    def count(self, item: Phrase) -> int:
        if self.is_expired():
            raise ExpiredException()
        return super().count(item)

    def index(self, item: Phrase, *args: Any) -> int:
        if self.is_expired():
            raise ExpiredException()
        return super().index(item, *args)

    def reverse(self) -> None:
        if self.is_expired():
            raise ExpiredException()
        return super().reverse()

    def sort(self, *args: Any, **kwds: Any) -> None:
        if self.is_expired():
            raise ExpiredException()
        return super().sort(*args, **kwds)

    def extend(self, other: Iterable[Phrase], no_check: bool = False) -> None:
        if not no_check and self.is_expired():
            raise ExpiredException()
        return self.data.extend(other)
