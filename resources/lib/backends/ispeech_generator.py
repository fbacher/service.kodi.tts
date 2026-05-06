# coding=utf-8
from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, ForwardRef

from backends.base import SimpleTTSBackend
from backends.engines.idownloader import IDownloader
from backends.engines.utils.igenerator_deps import IResults, Results
from cache.cache_file_state import CacheFileState
from cache.common_types import CacheEntryInfo
from common.phrases import Phrase, PhraseList
from common.setting_constants import PlayerMode


class ISpeechGenerator:
    """
    Defines the interface for a Speech Generator. Encourages the
    seperation of TTS engine specific (downloader) code from generic
    SpeechGenerator code.
    """

    def __init__(self, engine_instance: SimpleTTSBackend | None = None,
                 downloader: IDownloader | None = None,
                 max_phrase_length: int = 0,
                 **kwargs) -> None:
        """
        :param engine_instance: TTS Engine that this generator is for
        # :param download_results: Allows caller to view generation status
        :param downloader: TTS engine-specific downloader for this generator
        :param max_phrase_length: absolute maximum length the TTS engine can use.
        """
        pass

    def get_voiced_file(self, phrase: Phrase,
                        player_mode: PlayerMode,
                        byte_stream: BinaryIO | None = None) -> CacheFileState:
        """
        TODO: Currently geared to return file path in phrase. Need to also suppport
              pipes/streams as well as engine-speak.

        Produces a voiced file for the given phrase, either from one already in
        the cache, or generating one.

        :param phrase: Contains the text to be voiced as wll as the path that it
                       is or will be located.
        :param player_mode: Informs where to send generated audio
        :param byte_stream: Used with PlayerMode.*PIPE settings. TODO:
        :return: True if the voice file was handed to a player, otherwise False
        """
        pass

    def generate_speech(self, phrase: Phrase,
                        audio_mode: PlayerMode,
                        byte_stream: BinaryIO | None = None,
                        maximum_wait_sec: float = 5.0) -> CacheEntryInfo | BinaryIO:
        """
        NEW !!!
        Generates audio for the given phrase.
        :param phrase: Phrase to generate audio for
        :param audio_mode: Describes how to deliver the audio (file, pipe, etc.)
        :param byte_stream: optional stream to use when a pipe is requested. If None
                            and pipe is requested, then a new pipe is returned.
        :param maximum_wait_sec: Maximum time to wait for generation to complete
        :return: If audio_mode is a pipe and byte_stream is None, then a pipe is
                 returned, otherwise, the method is blocked until the generation
                 is complete and the success can be determined by the returned
                 CacheEntryInfo
        """
        pass

    def voice_chunks(self, chunks: PhraseList, tmp_path: Path) -> BinaryIO | None:
        """
        Generate speech for given phrases.

        :param chunks:   Phrases to voice
        :param tmp_path: Temporary file used during voice generation
        :return:
        """

    def remote_generate_speech(self, phrase: Phrase, timeout: float = 1.0) -> IResults:
        """
        Used when generation service may have significant delay, typically, for a
        remote call or similar. When the timeout expires, the function returns,
        however, the download continues in the background so that the cache gets
        poplulated for next time.

        :param phrase:   Phrase to voice
        :param timeout:  Max seconds to wait
        :return:
        """

        raise NotImplementedError()
