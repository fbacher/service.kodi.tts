# coding=utf-8

from __future__ import annotations  # For union operator |

import hashlib
import inspect
#  TODO: change to regex
import pathlib
import re
import sys
from collections import UserList
from pathlib import Path

try:
    import regex
except ImportError:
    import re as regex
from common import *

from common.constants import Constants
from common.critical_settings import CriticalSettings
from common.exceptions import EmptyPhraseException, ExpiredException
from common.logger import *
from common.messages import Message, Messages
from common.monitor import Monitor
from simplejson import JSONEncoder

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
    PAUSE_NORMAL: int = 50
    PAUSE_DEFAULT: int = 0
    PAUSE_WORD: int = 0
    PAUSE_SENTENCE: int = 0
    PAUSE_PARAGRAPH: int = 0
    PAUSE_SHORT: int = 45
    PAUSE_LONG: int = 145

    available_pauses: List[int] = [
        45,
        50,
        100,
        145,
        150,
        200,
        250,
        300,
        350,
        400,
        450,
        500
    ]
    min_pause: int = available_pauses[0]
    max_pause: int = available_pauses[len(available_pauses) - 1]

    _remove_multiple_whitespace_re: Final[regex.Pattern] = regex.compile(r'(\s{2,})')
    _formatTagRE: Final[regex.Pattern] = regex.compile(
        r'\[/?(?:CR|B|I|UPPERCASE|LOWERCASE)]', re.IGNORECASE)
    _colorTagRE: Final[regex.Pattern] = regex.compile(r'\[/?COLOR[^]\[]*?]',
                                                      re.IGNORECASE)
    _okTagRE: Final[regex.Pattern] = regex.compile(
        r'(^|\W|\s)OK($|\s|\W)')  # Prevents saying Oklahoma
    _hyphen_prefix: Final[regex.Pattern] = regex.compile(r'(:?(-\[)([^[]*)(]))')
    _pauseRE: Final[regex.Pattern] = regex.compile(Constants.PAUSE_INSERT)

    _logger: BasicLogger = None

    def __init__(self, text: str = '', interrupt: bool = False, pre_pause_ms: int = None,
                 post_pause_ms: int = None,
                 cache_path: Path = None, exists: bool = False, temp: bool = False,
                 preload_cache: bool = False,
                 serial_number: int | None = None,
                 check_expired: bool = True,
                 speak_while_playing: bool = True,
                 text_id: str | None = None,
                 language: str | None = None,
                 gender: str | None = None,
                 voice: str | None = None,
                 debug_info: str | None = None,
                 debug_context: int = 1):
        """

        :param text: Text to be voiced
        :param interrupt: Interrupts any previously queued speech if True
        :param pre_pause_ms: Amount of time to wait prior to voicing this phrase
        :param post_pause_ms: Amount of time to wait after voicing this phrase
        :param cache_path: Path to the cache entry for this phrase (set even
                           when not yet in the cache)
        :param exists: True if a cache entry for this phrase exists
        :param temp:
        :param preload_cache:
        :param serial_number: Monotonically increasing number to aid in purging
                              expired or interrupted messages
        :param check_expired: Controls whether a check for interrupted or otherwise
                              expired messages are made. Typically used when voice is
                              to be generated and cached even if not spoken.
        :param speak_while_playing: If True, then voice text even if video is playing
        :param text_id:
        :param language: When None, then use current language, otherwise voice
                         phrase in specified language. One use is during language
                         configuration. Lang spec is engine specific, so only
                         applies to current engine
        :param gender: When None, then use current gender, otherwise voice phrase in
                       specified gender. One use is during language configuration.
        :param voice:  When None, then use current voice. Otherwse, voice phrase
                       using specified voice. One us is during language configuration.
                       Voice values are engine specific, so only applies to current
                       engine
        :param debug_info:
        :param debug_context: A debug string can be associated with a phrase to
                             aid in tracking down where originally generated0
        """
        clz = type(self)
        Monitor.exception_on_abort()
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        debug_context += 1
        self.text: str = clz.clean_phrase_text(text)
        # if self.text == '':
        #     clz._logger.debug(f'empty text')
        self.cache_path: Path = cache_path
        self._exists: bool = exists
        self._temp: bool = temp
        self.interrupt: bool = interrupt
        if pre_pause_ms is None:
            pre_pause_ms = 0
        self.pre_pause_ms = pre_pause_ms
        if post_pause_ms is None:
            post_pause_ms = clz.PAUSE_DEFAULT
        self.post_pause_ms: int = post_pause_ms
        self.preload_cache: bool = preload_cache
        self.serial_number: int
        if serial_number:
            self.serial_number = serial_number
        else:
            self.serial_number = PhraseList.global_serial_number
        self._speak_while_playing: bool = speak_while_playing
        self.download_pending: bool = False

        # PhraseList can disable expiration checking when you explicitly
        # make an unchecked clone. Useful for seeding a cache for the future

        self.check_expired: bool = check_expired
        self.language: str | None = language
        self.gender: str | None = gender
        self.voice: str | None = voice
        if debug_info is None:
            debug_info = ''
        self.debug_info: str | None = debug_info
        self.set_debug_info(debug_info, context=debug_context)
        if text_id is None:
            text_id = text
        self.text_id: str | None = None
        self.set_text_id(text_id)  # Keeps md5

    def __repr__(self) -> str:
        pre_pause_str = ''
        if self.pre_pause_ms != 0:
            pre_pause_str = f' pre_pause: {self.pre_pause_ms}'
        post_pause_str: str = ''
        if self.post_pause_ms != 0:
            post_pause_str = f' post_pause: {self.post_pause_ms}'
        return f'Phrase: {self.text} {pre_pause_str}{post_pause_str}'

    @classmethod
    def new_instance(cls, text: str = '', interrupt: bool = False,
                     pre_pause_ms: int = None,
                     post_pause_ms: int = None,
                     cache_path: Path = None, exists: bool = False,
                     temp: bool = False,
                     preload_cache: bool = False,
                     serial_number: int = None,
                     speak_while_playing: bool = False,
                     check_expired: bool = True,
                     text_id: str | None = None,
                     debug_info: str | None = None) -> ForwardRef('Phrase'):
        text: str = cls.clean_phrase_text(text)
        # if len(text) == 0:
        #     raise EmptyPhraseException()
        if serial_number is None:
            serial_number = PhraseList.global_serial_number
        return Phrase(text=text, interrupt=interrupt, pre_pause_ms=pre_pause_ms,
                      post_pause_ms=post_pause_ms, cache_path=cache_path,
                      exists=exists, temp=temp,
                      preload_cache=preload_cache,
                      serial_number=serial_number,
                      speak_while_playing=speak_while_playing,
                      check_expired=check_expired,
                      text_id=text_id,
                      debug_info=debug_info,
                      debug_context=2)

    def clone(self, check_expired: bool = True) -> 'Phrase':
        phrase: Phrase
        phrase = Phrase(text=self.text, interrupt=self.interrupt,
                        pre_pause_ms=self.pre_pause_ms,
                        post_pause_ms=self.post_pause_ms,
                        cache_path=self.cache_path,
                        exists=self._exists, temp=self._temp,
                        preload_cache=self.preload_cache,
                        speak_while_playing=self._speak_while_playing,
                        check_expired=check_expired,
                        debug_info=self.debug_info)
        phrase.text_id = self.text_id
        return phrase

    def to_json(self) -> str:
        data: Dict[str, Dict[str, Any]] = self.to_dict()
        json_str: str = JSONEncoder.default(data)
        return json_str

    def to_dict(self) -> Dict[str, Any]:
        """
            TODO: do a cleaner job of json encode/decode
        :return:
        """
        tmp: Dict[str, Dict[str, Any]] = {'phrase': {
            'text'               : self.text,
            'interrupt'          : self.interrupt,
            'pre_pause_ms'       : self.pre_pause_ms,
            'post_pause_ms'      : self.post_pause_ms,
            'cache_path'         : self.cache_path,
            'exists'             : self._exists,
            'temp'               : self._temp,
            'preload_cache'      : self.preload_cache,
            'speak_while_playing': self._speak_while_playing,
            'check_expired'      : self.check_expired,
            'text_id'            : self.text_id,
            'debug_info'         : self.debug_info
        }}
        return tmp

    @classmethod
    def create(cls, params: Dict[str, Any]) -> 'Phrase':
        phrase: Phrase = Phrase(text=params.get('text'),
                                interrupt=params.get('interrupt'),
                                pre_pause_ms=params.get('pre_pause_ms'),
                                post_pause_ms=params.get('post_pause_ms'),
                                cache_path=params.get('cache_path'),
                                exists=params.get('exists'),
                                temp=params.get('temp'),
                                preload_cache=params.get('preload_cache'),
                                speak_while_playing=params.get('speak_while_playing',
                                                               False),
                                check_expired=params.get('check_expired', True),
                                text_id=params.get('text_id'),
                                debug_info=params.get('debug_info'))
        return phrase

    def get_text(self) -> str:
        clz = type(self)
        # clz._logger.debug(f'{self.get_debug_info()}')
        self.test_expired()
        return self.text

    def get_text_id(self) -> str:
        return self.text_id

    def set_text_id(self, text_id: str | None) -> None:
        if text_id is None:
            self.text_id = None
        else:
            self.text_id = hashlib.md5(text_id.encode('utf-8')).digest()

    def compare_text_id(self, other_text_id: str | None) -> bool:
        if other_text_id is None:
            return False
        return other_text_id == self.text_id

    def get_debug_info(self) -> str:
        return self.debug_info

    def set_debug_info(self, debug_info: str | None = None, context: int = 1) -> None:
        clz = type(self)
        # self.debug_info = debug_info
        try:
            stack_trace: List[Tuple[inspect.FrameInfo]] = inspect.stack()
            caller_frame: inspect.FrameInfo = stack_trace[context]
            filename = Path(caller_frame.filename).name
            lineno = caller_frame.lineno
            function = caller_frame.function
            self.debug_info = f'file {filename} func: {function} line: {lineno}'
        except Exception as e:
            clz._logger.exception('')

    def debug_data(self) -> str:
        return f'{self.serial_number:d}_{self.text:20} expired: {self.is_expired()}' \
               f' expires: {self.check_expired}'

    def set_text(self, text: str, context: int = 1,
                 preserve_debug_info: bool = True) -> None:
        clz = type(self)
        if not preserve_debug_info:
            self.set_debug_info(context=context)
        self.test_expired()
        if clz._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            clz._logger.debug_extra_verbose(f'Phrase: {self}')

        self.text = text

    def set_cache_path(self, cache_path: Path, exists: bool, temp: bool = False):
        self.test_expired()
        self.cache_path = cache_path
        self._exists = exists
        self._temp = temp

    def get_cache_path(self) -> Path:
        self.test_expired()
        return self.cache_path

    def exists(self) -> bool:
        self.test_expired()
        return self._exists

    def set_exists(self, exists: bool) -> None:
        self.test_expired()
        self._exists = exists

    def get_interrupt(self) -> bool:
        self.test_expired()
        return self.interrupt

    def set_interrupt(self, interrupt: bool) -> None:
        self.test_expired()
        self.interrupt = interrupt

    def get_pre_pause(self) -> int:
        self.test_expired()
        return self.pre_pause_ms

    def set_pre_pause(self, pre_pause_ms: int) -> None:
        self.test_expired()
        self.pre_pause_ms = pre_pause_ms

    def get_pre_pause_path(self, audio_type: str = 'mp3') -> Path | None:
        clz = type(self)
        return self.get_pause_path(self.get_post_pause())

    def get_post_pause(self) -> int:
        self.test_expired()
        return self.post_pause_ms

    def get_post_pause_path(self, audio_type: str = 'mp3') -> Path | None:
        clz = type(self)
        return self.get_pause_path(self.get_post_pause())

    def get_pause_path(self, pause_ms: int) -> Path | None:
        clz = type(self)
        if pause_ms == 0:
            return None

        if (pause_ms < Phrase.min_pause) or (pause_ms > Phrase.max_pause):
            clz._logger.debug_verbose(f'pause out of range: {pause_ms}')

        found_pause_ms: int | None = None
        for available_pause in Phrase.available_pauses:
            if pause_ms <= available_pause:
                found_pause_ms = available_pause
                break

        if found_pause_ms is None:
            found_pause_ms = Phrase.max_pause
        pause_file_path: Path = CriticalSettings.RESOURCES_PATH.joinpath(
                'wavs', f'silence{found_pause_ms:03d}.wav')
        return pause_file_path

    def set_post_pause(self, post_pause_ms: int) -> None:
        self.test_expired()
        self.post_pause_ms = post_pause_ms

    def is_preload_cache(self) -> bool:
        self.test_expired()
        return self.preload_cache

    def set_preload_cache(self, preload_cache: bool) -> None:
        self.test_expired()
        self.preload_cache = preload_cache

    def is_download_pending(self) -> bool:
        return self.download_pending

    def set_download_pending(self, is_pending: bool = True) -> None:
        self.download_pending = is_pending

    def get_serial_num(self) -> int:
        self.test_expired()
        return self.serial_number

    def is_empty(self) -> bool:
        return self.text == ''

    @classmethod
    def clean_phrase_text(cls, text: str) -> str:
        text = text.strip()
        text = cls._remove_multiple_whitespace_re.sub('', text)
        text = cls._formatTagRE.sub('', text)
        text = cls._colorTagRE.sub('', text)
        # Some speech engines say OK as Oklahoma
        text = cls._okTagRE.sub(r'\1O K\2', text)

        # getLabel() on lists wrapped in [] and some speech engines have
        # problems with text starting with -
        text = regex.sub(cls._hyphen_prefix, '\g<2>', text)
        text = text.replace('XBMC', 'Kodi')
        if text == '..':
            text = Messages.get_msg(Messages.PARENT_DIRECTORY)
        if text.endswith(')'):  # Skip this most of the time
            # For boolean settings
            result: PhraseList
            result = Messages.format_boolean(text, enabled_msgid=Messages.ENABLED.get_msg_id(),
                                             disabled_msgid= Messages.DISABLED.get_msg_id())
            # The result will have embedded PAUSE_INSERTs in it that will be
            # handled later in
            text = result.get_aggregate_text()  # Should be just one Phrase

        return text

    @classmethod
    def from_json(cls, json_object: Any):
        if isinstance(json_object, dict):
            if 'phrase' in json_object:
                return cls.create(json_object.get('phrase'))
        return json_object

    @classmethod
    def set_expired(cls, phrase_or_list: Union['Phrase', 'PhraseList'], all: bool):
        """
        Mark the global PhraseList expired_serial_number with the
        serial_number of the given Phrase or PhraseList (unless already marked)
        :param phrase_or_list:
        :param all:
        :return:
        """
        if isinstance(phrase_or_list, Phrase):
            phrase: Phrase = phrase_or_list
            if PhraseList.expired_serial_number < phrase.serial_number:
                cls.expired_serial_number = phrase.serial_number
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug_verbose(f'Set Phrase EXPIRED: {phrase.debug_data()} '
                                  f'global serial: {PhraseList.expired_serial_number}')

        elif isinstance(phrase_or_list, PhraseList):
            phrases: PhraseList = phrase_or_list
            if PhraseList.expired_serial_number < phrases.serial_number:
                cls.expired_serial_number = phrases.serial_number

        # Just to make sure that global_serial_number is > expired_serial_number

        if PhraseList.expired_serial_number >= PhraseList.global_serial_number:
            PhraseList.global_serial_number = PhraseList.expired_serial_number + 1
        if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            cls._logger.debug(f'Set Phrase EXPIRED: {phrase_or_list.debug_data()} '
                              f'global serial: {PhraseList.expired_serial_number}')

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

    @property
    def speak_while_playing(self) -> bool:
        return self._speak_while_playing

    def set_speak_while_playing(self, speak_while_playing: bool) -> None:
        self._speak_while_playing = speak_while_playing

    def text_equals(self, other: Phrase | str) -> bool:
        if other is None:
            return False

        if isinstance(other, str):
            return other == self.text
        return other.text == self.text


# Python 3.8 does not support (Windows)
# class PhraseList(UserList[Phrase]):
class PhraseList(UserList):

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
        Monitor.exception_on_abort()
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)

        clz.global_serial_number += 1
        self.serial_number: int = clz.global_serial_number
        self.check_expired = check_expired

    @classmethod
    def create(cls, texts: str | List[str], interrupt: bool = False,
               preload_cache: bool = False, check_expired: bool = True,
               text_id: str | None = None) -> 'PhraseList':
        """

        :param texts: One or more strings to create Phrases from
        :param interrupt: If True, then when this PhraseList is voiced, all
                          prior voicings are aborted and discarded.
                          Defalt False
        :param preload_cache:
        :param check_expired: When True, then most methods to acceses a Phrase
                              will throw an ExpiredException when a newer
                              Phrase interrupts.
                              Default True
        :param text_id: Sets the text_id of the FIRST Phrase created. Defaults
                        to the first value in texts
        :return:
        """
        if not isinstance(texts, list):
            texts = [texts]
        phrases: PhraseList = PhraseList(check_expired=check_expired)
        cls.convert_str_to_phrases(texts, phrases=phrases, preload_cache=preload_cache)
        if len(phrases) == 0:
            phrases.append(Phrase(text='', preload_cache=False,
                                  pre_pause_ms=0))
        else:
            if text_id is None:
                text_id = texts[0]
            phrases[0].set_text_id(text_id)

        phrase: Phrase = phrases[0]
        phrase.set_interrupt(interrupt)
        return phrases

    @classmethod
    def convert_str_to_phrases(cls, texts: List[str],
                               phrases: PhraseList,
                               preload_cache: bool = False):
        pre_pause: int = 0
        for text in texts:
            text: str | int
            if isinstance(text, int):
                pre_pause = text
                continue
            elif not isinstance(text, str):
                raise TypeError(f'Expected list of strings and ints not {type(text)}')
            # Split of "...a b c......de..." will produce:
            #   ['', 'a', 'b', 'c', '', 'de', '']
            # Therefore, PAUSE_INSERT occurs between every element, it also
            # occurs on every empty element in the list.
            #
            # Note that pre-pauses get assigned to the next fragment. Therefore,
            # duplicates pauses or those at end of string or dropped.

            fragments: List[str] = text.split(Constants.PAUSE_INSERT)
            fragment: str
            for fragment in fragments:
                if fragment == '':
                    # A pause on fragment following an empty fragment
                    pre_pause = Phrase.PAUSE_NORMAL
                else:
                    fragment: str = Phrase.clean_phrase_text(fragment)
                    if cls._logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
                        cls._logger.debug_extra_verbose(
                                f'# fragment: {fragment} pre_pause: {pre_pause}')
                    phrase: Phrase = Phrase(text=fragment, preload_cache=preload_cache,
                                            pre_pause_ms=pre_pause)

                    # Every fragment indicates a pause for next fragment
                    pre_pause = Phrase.PAUSE_NORMAL
                    phrase.serial_number = phrases.serial_number
                    phrases.append(phrase)

    def add_text(self, texts: str | List[str],  pre_pause_ms: int = None,
                 post_pause_ms: int = None, text_id: str | None = None) -> PhraseList:
        """
        Appends one or more text strings at the end of this PhraseList.
        Note that unlike create, this method can replace embedded delay
        strings ('...') with a default delay value for the phrase/phrases
        involved.

        Note that an explicit pre_pause_ms or post_pause_ms argument will override
        any embedded delay string ('...'), but only for the beginning and ending
        of the phrase list.

        :param texts: One or more strings to append onto Phrases
        :param pre_pause_ms: If specified, will be assigned to the First phrase added
        :param post_pause_ms: If specified, will be assigned to the Last phrase added
        :param text_id: Sets the text_id of the FIRST Phrase created. Defaults
                        to the first value in texts
        :return:
        """
        clz = type(self)
        if not isinstance(texts, list):
            texts = [texts]

        if len(texts) == 0:
            return self

        start_of_addition: int = len(self)
        clz.convert_str_to_phrases(texts, self)
        if pre_pause_ms is not None and pre_pause_ms > 0:
            self[start_of_addition].set_pre_pause(pre_pause_ms)
        if post_pause_ms is not None and post_pause_ms > 0:
            phrase: Phrase = self.data[-1]
            phrase.set_post_pause(post_pause_ms)

        return self

    def get_aggregate_text(self) -> str:
        text: str = ''
        text = ' '.join(f'{x.text}' for x in self.data)
        return text

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
                compact_phrase.set_text(text, preserve_debug_info=True)
                compact_phrase.set_interrupt(current_phrase.get_interrupt())

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

    def debug_data(self) -> str:
        clz = type(self)
        return f'{self.serial_number:d} expired: {self.is_expired()} ' \
               f'expires: {self.check_expired} global: {clz.global_serial_number:d}'

    @classmethod
    def set_current_expired(cls) -> None:
        cls.expired_serial_number = cls.global_serial_number

    def expire_all_prior(self) -> None:
        clz = type(self)
        if not self.is_expired() and not self.check_expired:
            if clz.expired_serial_number < (self.serial_number - 1):
                clz.expired_serial_number = self.serial_number - 1

    def set_expired(self) -> None:
        clz = type(self)
        if not self.is_expired() and not self.check_expired:
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

    def equal_text(self, other: PhraseList) -> bool:
        if other is None:
            return False

        if not isinstance(other, PhraseList):
            return False
        if len(self) != len(other):
            return False
        for p in range(0, len(self)):
            if not self[p].get_text() == other[p].get_text():
                return False
        return True

    def contains(self, other: str | Phrase | PhraseList) -> bool:
        """
        Determines whether this PhraseList contains a Phrase with text == to
        other text

        :param other: String or Phrase to compare text value
        :return:
        """
        clz = type(self)
        txt: str
        if other is None:
            return False

        if isinstance(other, PhraseList):
            if other.is_empty():
                return False
            length: int = len(other)
            start: int = length - len(self)
            if start < 0:
                return False
            idx: int
            for idx in 0, (length - 1):
                if self[idx + start] != other[idx]:
                    # clz._logger.debug(f'me[{idx + start}]: {self[idx + start]} '
                    #                   f'them[{idx}]: {other[idx]}')
                    return False
            return True

        elif isinstance(other, Phrase):
            txt = other.text
        else:
            txt = other
        for phrase in self.data:
            phrase: Phrase
            if phrase.text_equals(txt):
                return True
        return False

    def ends_with(self, other: str | Phrase | PhraseList) -> bool:
        """
        Determines whether this PhraseList contains a Phrase with text == to
        other text

        :param other: String or Phrase to compare text value
        :return:
        """
        clz = type(self)
        txt: str
        if other is None:
            return False

        if isinstance(other, PhraseList):
            # clz._logger.debug(f'self: {self} \n'
            #                   f'other: {other}\n'
            #                   f'len(self): {len(self)} len(other): {len(other)}')
            if other.is_empty():
                return False
            length: int = len(other)
            start: int = len(self) - length
            if start < 0:
                return False
            idx: int
            for idx in 0, (length - 1):
                # clz._logger.debug(f'me[{idx + start}]: {self[idx + start]} '
                #                   f'them[{idx}]: {other[idx]}\n'
                #                   f'equals: {self[idx + start] != other[idx]}')
                if self[idx + start] != other[idx]:
                    return False
            return True

        elif isinstance(other, Phrase):
            txt = other.text
        else:
            txt = other
        if self[-1] == txt:
            return True
        return False

    def __repr__(self) -> str:
        text: str = ''
        text = ' '.join(f'{str(x)}' for x in self.data)
        return text

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, PhraseList):
            raise TypeError('Must be PhraseList')
        other: PhraseList
        if self.check_expired and (self.is_expired() or other.is_expired()):
            raise ExpiredException()
        return super().__lt__(other)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, PhraseList):
            raise TypeError('Must be PhraseList')
        other: PhraseList
        if self.check_expired and (self.is_expired() or other.is_expired()):
            raise ExpiredException()
        return super().__le__(other)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, PhraseList):
            raise TypeError('Must be PhraseList')
        other: PhraseList
        if self.check_expired and (self.is_expired() or other.is_expired()):
            raise ExpiredException()
        return super().__gt__(other)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, PhraseList):
            raise TypeError('Must be PhraseList')
        other: PhraseList
        if self.check_expired and (self.is_expired() or other.is_expired()):
            raise ExpiredException()
        return super().__ge__(other)

    def __contains__(self, item: object) -> bool:
        if not isinstance(item, PhraseList):
            raise TypeError('Must be PhraseList')
        item: PhraseList
        if self.check_expired and (self.is_expired() or item.is_expired()):
            raise ExpiredException()
        return super().__contains__(item)

    def __len__(self) -> int:
        if self.check_expired and self.is_expired():
            raise ExpiredException()
        return super().__len__()

    def __getitem__(self: 'PhraseList', i: slice | int) -> Phrase:
        if self.check_expired and self.is_expired():
            raise ExpiredException()
        return super().__getitem__(i)

    def __setitem__(self, i: slice | int, o: Phrase | Iterable[Phrase]) -> None:
        if self.check_expired and self.is_expired():
            raise ExpiredException()
        return super().__setitem__(i, o)

    def __delitem__(self, i: int | slice) -> None:
        if self.check_expired and self.is_expired():
            raise ExpiredException()
        return super().__delitem__(i)

    def __add__(self, other: Iterable[Phrase]) -> PhraseList | UserList:
        if self.check_expired and self.is_expired():
            raise ExpiredException()
        return super().__add__(other)

    def __iadd__(self, other: Iterable[Phrase]) -> PhraseList | UserList:
        if self.check_expired and self.is_expired():
            raise ExpiredException()
        return super().__iadd__(other)

    def __mul__(self, n: int):
        if self.check_expired and self.is_expired():
            raise ExpiredException()
        return super().__mul__(n)

    def __imul__(self, n: int):
        if self.check_expired and self.is_expired():
            raise ExpiredException()
        return super().__imul__(n)

    def append(self, item: Phrase) -> None:
        if not isinstance(item, Phrase):
            raise TypeError(f'Expected a Phrase not {type(item)}')
        if self.check_expired and self.is_expired():
            raise ExpiredException()
        if item.is_expired():
            raise ExpiredException()
        return self.data.append(item)

    def insert(self, i: int, item: Phrase) -> None:
        if not isinstance(item, Phrase):
            raise TypeError('Expected a Phrase')
        if self.is_expired() and self.check_expired:
            raise ExpiredException()
        return super().insert(i, item)

    def pop(self, i: int = ...) -> Phrase:
        if self.is_expired() and self.check_expired:
            raise ExpiredException()
        return super().pop(i)

    def remove(self, item: Phrase) -> None:
        if self.is_expired() and self.check_expired:
            raise ExpiredException()
        return super().remove(item)

    def clear(self) -> None:
        if self.is_expired() and self.check_expired:
            raise ExpiredException()
        return super().clear()

    def copy(self) -> 'PhraseList' | UserList:
        if self.is_expired() and self.check_expired:
            raise ExpiredException()
        return super().copy()

    def count(self, item: Phrase) -> int:
        if self.is_expired() and self.check_expired:
            raise ExpiredException()
        return super().count(item)

    def index(self, item: Phrase, *args: Any) -> int:
        if self.is_expired() and self.check_expired:
            raise ExpiredException()
        return super().index(item, *args)

    def reverse(self) -> None:
        if self.is_expired() and self.check_expired:
            raise ExpiredException()
        return super().reverse()

    def sort(self, *args: Any, **kwds: Any) -> None:
        if self.is_expired() and self.check_expired:
            raise ExpiredException()
        return super().sort(*args, **kwds)

    def extend(self, other: Iterable[Phrase], no_check: bool = False) -> None:
        if not no_check and self.is_expired() and self.check_expired:
            raise ExpiredException()
        return self.data.extend(other)

    def is_empty(self) -> bool:
        return len(self.data) == 0


class PhraseUtils:

    PUNCTUATION_PATTERN = regex.compile(r'([.,:])', regex.DOTALL)
    _logger: BasicLogger = None
    _initialized: bool = False

    def __init__(self):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        clz._initialized = True

    @classmethod
    def split_into_chunks(cls, phrase: Phrase, chunk_size: int = 100) -> PhraseList[
        Phrase]:
        phrases: PhraseList[Phrase] = PhraseList(check_expired=False)
        out_chunks: List[str] = []
        try:
            chunks: List[str] = regex.split(cls.PUNCTUATION_PATTERN, phrase.get_text())
            if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                cls._logger.debug_verbose(f'len chunks: {len(chunks)}')
            text_file_path: pathlib.Path
            text_file_path = phrase.get_cache_path().with_suffix('.txt')
            with text_file_path.open('at', encoding='utf-8') as text_file:
                while len(chunks) > 0:
                    Monitor.exception_on_abort()
                    chunk: str = chunks.pop(0)
                    # When a chunk exceeds the maximum chunk length,
                    # go ahead and return the over-length chunk.

                    if len(chunk) >= chunk_size:
                        if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                            cls._logger.debug_verbose(f'Long chunk: {chunk}'
                                                      f' length: {len(chunk)}')
                            try:
                                text_file.write(f'\nPhrase: {chunk}')
                            except Exception as e:
                                cls._logger.exception(f'Failed to save text cache file')
                                try:
                                    text_file_path.unlink(True)
                                except Exception as e2:
                                    pass
                        out_chunks.append(chunk)
                        chunk = ''
                    else:
                        # Append chunks onto chunks as long as there is room
                        while len(chunks) > 0:
                            Monitor.exception_on_abort()
                            next_chunk = chunks[0]  # Don't pop yet
                            if ((len(next_chunk) + len(
                                    next_chunk)) <= chunk_size):
                                if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                                    cls._logger.debug_verbose(f'Appending to chunk:'
                                                              f' {next_chunk}'
                                                              f' len: {len(next_chunk)}')
                                chunk += chunks.pop(0)
                            else:
                                out_chunks.append(chunk)
                                if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                                    cls._logger.debug_verbose(f'Normal chunk: {chunk}'
                                                              f' length: {len(chunk)}')
                                chunk = ''
                                break
                    if len(chunk) > 0:
                        out_chunks.append(chunk)
                        if cls._logger.isEnabledFor(DEBUG_VERBOSE):
                            cls._logger.debug_verbose(f'Last chunk: {chunk}'
                                                      f' length: {len(chunk)}')
                phrases: PhraseList[Phrase] = PhraseList()
                # Force these phrases have the same serial # as the original
                phrases.serial_number = phrase.serial_number
                first: bool = True
                for chunk in out_chunks:
                    if first:
                        chunk_phrase: Phrase = Phrase(chunk, phrase.get_interrupt(),
                                                      phrase.get_pre_pause(),
                                                      phrase.get_post_pause(),
                                                      phrase.get_cache_path(), False,
                                                      phrase.is_preload_cache(),
                                                      check_expired=False)
                        first = False
                    else:
                        chunk_phrase: Phrase = Phrase(chunk, check_expired=False)
                    phrases.append(chunk_phrase)
                    chunk_phrase.serial_number = phrase.serial_number
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            phrases = PhraseList()
            phrases.serial_number = phrase.serial_number
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
        return phrases


if not PhraseUtils._initialized:
    PhraseUtils()
