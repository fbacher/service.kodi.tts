# coding=utf-8
from __future__ import annotations

import threading
from typing import Dict

from common.logger import BasicLogger
from common.phrases import Phrase

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class CacheEntryMgr:
    """
    Provides methods to manage the state of generating voice files from text.
    Prevents duplicate conversion of phrases to voice files

    Use:

    """
    # Whenever a voicing is being created for text that is destined for the
    # cache, there will be an entry in this table. The key is the md5 hash
    # of the text. The table is protected by an RLock.
    active_audio_creation: Dict[str, bool] = {}
    active_audio_lock: threading.RLock = threading.RLock()

    @classmethod
    def start_work(cls, phrase: Phrase) -> bool:
        """
        Used to track when the text of a phrase is being converted to voice.
        Prevents multiple conversions for same phrase

        :param phrase: Contains the text to convert to voice
        :return: True if the given phrase was added to lock map by this call,
                 otherwise False
        """
        with cls.active_audio_lock:
            if cls.active_audio_creation.get(phrase.text) is None:
                cls.active_audio_creation[phrase.text] = True
                return True
            return False

    @classmethod
    def is_working_on(cls, phrase: Phrase) -> bool:
        with cls.active_audio_lock:
            result: bool | None = cls.active_audio_creation.get(phrase.text)
            if result is None:
                result = True
            return result

    @classmethod
    def work_complete(cls, phrase: Phrase) -> None:
        with cls.active_audio_lock:
            if cls.active_audio_creation.get(phrase.text) is None:
                MY_LOGGER.debug(f'NOT LOCKED!!')
            else:
                del cls.active_audio_creation[phrase.text]
