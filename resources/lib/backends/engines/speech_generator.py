# coding=utf-8
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any, BinaryIO, Dict

import langcodes
from backends.engines.idownloader import IDownloader, TTSDownloadError
from backends.ispeech_generator import ISpeechGenerator, Results
from backends.settings.engine_voice import EngineVoice
from backends.settings.engine_voice_manager import EngineVoiceManager
from backends.settings.lang_utils import LangUtils
from backends.settings.service_types import ServiceID
from cache.common_types import CacheEntryInfo
from common.exceptions import AbortException, ExpiredException
from six import reraise

from backends.base import SimpleTTSBackend
from cache.cache_file_state import CacheFileState
from cache.voicecache import VoiceCache
from common.constants import Constants, ReturnCode
from common.kodi_player_monitor import KodiPlayerMonitor
from common.logger import *
from common.minimal_monitor import MinimalMonitor
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList, PhraseUtils
from common.setting_constants import PlayerMode
from common.settings import Settings
from utils.util import runInThread

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class SpeechGenerator(ISpeechGenerator):

    # TODO: Consider detecting when phrase is already being voiced

    def __init__(self, engine_instance: SimpleTTSBackend | None = None,
                 downloader: IDownloader | None = None,
                 max_phrase_length: int = 0,
                 max_wait_sec: int = 5,
                 **kwargs) -> None:
        """
        :param engine_instance: TTS Engine that this generator is for
        # :param download_results: Allows caller to view generation status
        :param downloader: TTS engine-specific downloader for this generator
        :param max_phrase_length: absolute maximum length the TTS engine can use.
        """
        super().__init__(engine_instance, downloader, max_phrase_length)
        self.engine_instance: SimpleTTSBackend = engine_instance
        self.download_results: Results = Results()
        self._downloader: IDownloader = downloader
        self.v_cache: VoiceCache = VoiceCache(engine_instance.service_key)
        self.max_phrase_length: int = max_phrase_length
        self.kwargs = kwargs
        self.original_phrase: Phrase | None = None
        self._max_wait_sec: int = max_wait_sec
        # Depending upon the engine, may have a preference or requirement for not
        # using a file pointer for copying TTS from engine to a file. For example,
        # Piper supports writing to a file or returning a file handle that it
        # creates. See download.

        self.use_fp_for_tmp: bool = kwargs.get('use_fp_for_tmp', True)

    @property
    def downloader(self) -> IDownloader:
        return self._downloader

    def set_rc(self, rc: ReturnCode) -> None:
        self.download_results.set_rc(rc)

    def get_rc(self) -> ReturnCode:
        return self.download_results.get_rc()

    def set_phrase(self) -> None:
        self.download_results.set_phrase(self.original_phrase)

    def set_finished(self) -> None:
        self.download_results.set_finished(True)

    def is_finished(self) -> bool:
        return self.download_results.is_finished()

    @property
    def use_cache(self) -> bool:
        return Settings.is_use_cache()

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
        try:
            self.update_voice_path(self.engine_instance, phrase)
            result: CacheEntryInfo
            result = self.v_cache.get_path_to_voice_file(phrase,
                                                         self.use_cache)
            if not result.audio_exists:
                # Blocks a max of timeout seconds. Generator continues past
                # timeout so the file will be in the cache for the next time

                time_limit: float = self._max_wait_sec * 2
                self.generate_speech(phrase, audio_mode=player_mode,
                                     maximum_wait_sec=self._max_wait_sec)
                try:
                    attempts: int = int(time_limit / 0.1) + 1
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'{phrase.short_text()}:'
                                        f' {phrase.cache_file_state()}')
                    while phrase.cache_file_state() < CacheFileState.OK:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'{phrase.short_text()}: '
                                            f'{phrase.cache_file_state()}')
                        attempts -= 1
                        if attempts <= 0:
                            if MY_LOGGER.isEnabledFor(DEBUG):
                                MY_LOGGER.debug(f'Timed out')
                            break
                        Monitor.exception_on_abort(timeout=0.1)
                except (AbortException, ExpiredException) as e:
                    reraise(*sys.exc_info())
                except Exception:
                    MY_LOGGER.exception('')
        except ExpiredException:
            reraise(*sys.exc_info())
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{phrase.short_text()}: {phrase.cache_file_state()}')
        return phrase.cache_file_state()

    def generate_speech(self, phrase: Phrase,
                        audio_mode: PlayerMode,
                        byte_stream: BinaryIO | None = None,
                        maximum_wait_sec: float = 5.0) -> None | BinaryIO:
        """
        Generates audio for the given phrase.
        :param phrase: Phrase to generate audio for
        :param audio_mode: Describes how to deliver the audio (file, pipe, etc.)
        :param byte_stream: optional stream to use when a pipe is requested. If None
                            and pipe is requested, then a new pipe is returned.
        :param maximum_wait_sec: Maximum time to wait for generation to complete
        :return: If audio_mode is a pipe and byte_stream is None, then a pipe is
                 returned, otherwise, the method is blocked until the generation
                 is complete and the success can be determined by the returned
                 Results
        """
        # TODO: Add check for empty phrase
        if audio_mode == PlayerMode.ENGINE_SPEAK:
            raise NotImplementedError
        phrase_info: CacheEntryInfo = self.get_audio_path(self.v_cache, phrase)
        if phrase_info.audio_exists:
            if audio_mode == PlayerMode.SLAVE_PIPE:
                raise NotImplementedError
            if audio_mode == PlayerMode.PIPE:
                if byte_stream is None:
                    byte_stream: BinaryIO = phrase.cache_path.open(mode='rb')
                    return byte_stream
                else:
                    raise NotImplementedError
            return None
        self.original_phrase = phrase

        if self.downloader.supports_chunks and self.downloader.creates_tmp:
            raise NotImplementedError('SpeechGenerator currently doesn\'t support '
                                      'chunking with downloader creating tmp file')
        self.update_voice_path(self.engine_instance, self.original_phrase)
        self.original_phrase.set_download_pending(True)
        self.set_phrase()
        if self.original_phrase.is_empty():
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Phrase empty')
            self.set_rc(ReturnCode.OK)
            self.set_finished()
            return None

        cache_path: Path | None = None
        tmp_path: Path | None = None
        success: bool = True
        try:
            cache_path = self.original_phrase.get_cache_path(check_expired=False)
            rc2: int
            rc2, tmp_path, _ = self.v_cache.create_tmp_sound_file(cache_path,
                                                                  create_dir_only=True)
            if rc2 != 0:
                success = False
        except Exception as e:
            MY_LOGGER.exception('')
            success = False
        if not success:
            if MY_LOGGER.isEnabledFor(ERROR):
                MY_LOGGER.error(f'Failed to create cache directory '
                                f'{cache_path.parent}')
            self.original_phrase.set_cache_file_state(CacheFileState.BAD)
            self.original_phrase.add_event(f'Failed to create cache dir')
            self.set_rc(ReturnCode.CALL_FAILED)
            self.set_finished()
            return None

        self.original_phrase.set_cache_file_state(CacheFileState.CREATION_INCOMPLETE)
        result = self.generate_audio(phrase, tmp_path, phrase_info, audio_mode,
                                     byte_stream, maximum_wait_sec)
        if self.get_rc() != ReturnCode.OK:
            MY_LOGGER.debug(f'Return Code not OK: {self.get_rc()}')
            if tmp_path is not None and tmp_path.exists():
                try:
                    MY_LOGGER.debug(f'unlink {tmp_path}\n and {cache_path}')
                    tmp_path.unlink()
                except Exception as e:
                    MY_LOGGER.error(f'Failed to unlink {tmp_path}')
            if cache_path is not None and cache_path.exists():
                try:
                    MY_LOGGER.debug(f'unlink {cache_path}')
                    cache_path.unlink()
                except Exception as e:
                    MY_LOGGER.error(f'Failed to unlink {cache_path}')
            self.set_finished()
            return None
        try:
            MY_LOGGER.debug(f'Renaming {phrase.text} {tmp_path} to {cache_path}')
            size: int = tmp_path.stat().st_size
            MY_LOGGER.debug(f'Size of tmp_path to rename: {size}')
            tmp_path.rename(cache_path)
            self.set_finished()
            self.original_phrase.set_exists(True, check_expired=False)
            self.original_phrase.set_cache_file_state(CacheFileState.OK)
            self.original_phrase.add_event('generation finished')
            self.original_phrase.set_download_pending(False)
        except Exception as e:
            MY_LOGGER.exception(f'Failed to rename {cache_path}')
            self.original_phrase.add_event(f'Failed to rename'
                                           f' {tmp_path}')
            self.set_rc(ReturnCode.FILE)
            self.original_phrase.set_cache_file_state(CacheFileState.DOES_NOT_EXIST)
            self.set_finished()
        return None

    def generate_audio(self, phrase: Phrase,
                       tmp_path: Path,
                       phrase_info: CacheEntryInfo,
                       audio_mode: PlayerMode,
                       byte_stream: BinaryIO | None = None,
                       maximum_wait_sec: float = 5.0) -> None | BinaryIO:
        """
        Generates audio for the given phrase.
        :param phrase: Phrase to generate audio for
        :param tmp_path: the generated voice for a phrase/phrase_chunks are
                         first written to tmp_path. Once everthing is done properly,
                         then it is renamed to phrase.cache_path
        :param phrase_info: information about the cache status of the phrase
        :param audio_mode: Describes how to deliver the audio (file, pipe, etc.)
        :param byte_stream: optional stream to use when a pipe is requested. If None
                            and pipe is requested, then a new pipe is returned.
        :param maximum_wait_sec: Maximum time to wait for generation to complete
        :return: If audio_mode is a pipe and byte_stream is None, then a pipe is
                 returned, otherwise, the method is blocked until the generation
                 is complete and the success can be determined by the returned
                 CacheEntryInfo
        """
        chunks: PhraseList  # Chunks will be not be checked for expiration
        chunks = PhraseUtils.split_into_chunks(phrase,
                                               chunk_size=self.max_phrase_length)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'calling voice_chunks')
        try:
            thread: threading.Thread
            thread = runInThread(self.voice_chunks, name='dwnldGen', delay=0.0,
                                 chunks=chunks, tmp_path=tmp_path)
            attempts: int = int(maximum_wait_sec * 2 / 0.1) + 1
            while thread.is_alive():
                Monitor.exception_on_abort(timeout=0.1)
                attempts -= 1
                #  KodiPlayerMonitor.instance().isPlaying()):
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(
                        f'exit rc: {self.get_rc().name}  kodi playing:'
                        f' {KodiPlayerMonitor.instance().isPlaying()}')
                if self.get_rc() == ReturnCode.CALL_FAILED:
                    break
        except AbortException as e:
            self.set_rc(ReturnCode.ABORT)
            reraise(*sys.exc_info())
        except ExpiredException:
            self.set_rc(ReturnCode.EXPIRED)
            reraise(*sys.exc_info())
        except Exception:
            MY_LOGGER.exception('')
            self.set_rc(ReturnCode.CALL_FAILED)

        return None

    def voice_chunks(self, chunks: PhraseList, tmp_path: Path) -> BinaryIO | None:
        """
        Generate speech for given phrases.

        :param chunks:   Phrases to voice
        :param tmp_path: Temporary file used during voice generation
        :return:
        """
        success: bool = True
        try:
            if tmp_path is not None:
                MY_LOGGER.debug(f'open tmp_path for writing {tmp_path}')
        except Exception as e:
            MY_LOGGER.exception('')
            self.set_rc(ReturnCode.CALL_FAILED)
            self.original_phrase.add_event(f'Exception occurred. See log.')

        # When the generator/downloader can't write to a file pointer, then
        # it is easiest to open a fake file pointer and let the downloader write
        # or append to the temp file.

        if self.use_fp_for_tmp:
            with tmp_path.open(mode='wb') as tmp_fp:
                tmp_fp: BinaryIO
                for chunk in chunks:
                    chunk: Phrase
                    MY_LOGGER.debug(f'chunk: {chunk.text} tmp_path: {tmp_path}')
                    self._generate_speech_for_chunk(chunk, tmp_path, tmp_fp)
                    if tmp_fp.tell() == 0:
                        MY_LOGGER.debug(f'{chunk.short_text()} '
                                        f'Got 0 bytes From write_to_fp.')
                        self.set_rc(ReturnCode.DOWNLOAD)
                        self.original_phrase.add_event('0 length download')
                    else:
                        MY_LOGGER.debug(f'tmp_fp.tell: {tmp_fp.tell()}')
                    if self.get_rc() != ReturnCode.OK:
                        self.set_rc(ReturnCode.CALL_FAILED)
                        self.original_phrase.set_cache_file_state(CacheFileState.BAD)
                        self.original_phrase.add_event('chunk failure')
                        break
        else:
            for chunk in chunks:
                chunk: Phrase
                self._generate_speech_for_chunk(chunk, tmp_path, None)
                if self.get_rc() != ReturnCode.OK:
                    self.set_rc(ReturnCode.CALL_FAILED)
                    self.original_phrase.set_cache_file_state(CacheFileState.BAD)
                    self.original_phrase.add_event('chunk failure')
                    break
        if self.get_rc() == ReturnCode.OK:
            self.set_rc(ReturnCode.OK)
            self.original_phrase.set_cache_file_state(CacheFileState.OK)
            self.original_phrase.add_event('chunks complete')
        return None

    def _generate_speech_for_chunk(self, phrase_chunk: Phrase, tmp_path: Path,
                                   tmp_fp: BinaryIO | None) -> None:
        """
        Generates the speech for the given phrase. The downloader creates its own
        temp file for TTS output.

        :param phrase_chunk: phrase to voice
        :param tmp_path: path to use for downloading. Once all has been downloaded,
                         then rename to Phrase.cache_file.
        :param tmp_fp: File pointer for tmp_path
        :return: Nothing, status can be found in self.download_results
        """
        downloader_name: str = self.downloader.__class__.__name__
        try:
            Monitor.exception_on_abort()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Calling downloader with phrase: '
                                f'{phrase_chunk.short_text()}')
            # TODO: Allow engine to inject their own handles here.
            kwargs: Dict[str, Any] = {'tmp_path': tmp_path, 'pipe': tmp_fp,
                                      'use_fp_for_tmp': self.use_fp_for_tmp}
            self.downloader.download(phrase=phrase_chunk, **kwargs)
            MinimalMonitor.exception_on_abort(timeout=0.05)
        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            reraise(*sys.exc_info())
        except (TypeError, ExpiredException) as e:
            MY_LOGGER.exception('')
            self.original_phrase.add_event('expired')
            self.set_rc(ReturnCode.DOWNLOAD)
        except TTSDownloadError as e:
            MY_LOGGER.info(f'{TTSDownloadError:} {e.msg}')
            MY_LOGGER.exception(f'TTSDownloadError')
            self.set_rc(ReturnCode.DOWNLOAD)
            self.original_phrase.add_event('download error')
        except Exception as e:
            MY_LOGGER.exception('')
            self.set_rc(ReturnCode.DOWNLOAD)
            self.original_phrase.add_event('download failed')

    def get_audio_path(self, v_cache: VoiceCache, phrase: Phrase) -> CacheEntryInfo:
        """
        Determines the path where the audio for the given phrase should be located.
        The path will depend upon whether caching is enabled.

        :param v_cache: VoiceCache for current engine (depends on settings)
        :param phrase: Contains the text to be voiced,
        :result:
        :raises: ExpiredException
        """
        result: CacheEntryInfo | None = None
        try:
            self.update_voice_path(self.engine_instance, phrase)
            use_cache = self.use_cache
            result = v_cache.get_path_to_voice_file(phrase, use_cache=use_cache)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'result: {result}')
        except ExpiredException:
            reraise(*sys.exc_info())
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{phrase.short_text()}: {phrase.cache_file_state()}')
        return result

    @classmethod
    def update_voice_path(cls, engine_instance: SimpleTTSBackend,
                          phrase: Phrase) -> None:
        """
        Modify any cache path to reflect the voice, language and territory.
        :param engine_instance: engine that owns the phrase
        :param phrase:
        :return:
        """
        MY_LOGGER.debug(f'phrase: {phrase}')
        locale_id: str = phrase.language  # IETF format
        if phrase.language is None:
            locale_id = LangUtils.kodi_locale
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'orig Phrase locale_id: {locale_id}')
        ietf_lang: langcodes.Language = langcodes.get(locale_id)
        service_key: ServiceID = engine_instance.service_key
        e_voice: EngineVoice = EngineVoiceManager.get_e_voice(service_key)

        if Settings.is_use_cache and not phrase.is_lang_territory_set():
            phrase.set_lang_dir(ietf_lang.language)
            phrase.set_territory_dir(ietf_lang.territory.lower())
            MY_LOGGER.debug(
                f'Setting voice_dir: voice_group_id: {e_voice.engine_vg_id} \n'
                f'quality_id: {e_voice.voice_quality} \n')
            MY_LOGGER.debug(f'voice_id.voice_id: {e_voice.e_voice_id} '
                            f'cache_path_segment: {e_voice.cache_path_segment}')
            phrase.e_voice = e_voice
            phrase.set_voice_dir(e_voice.cache_path_segment)
        else:
            phrase.e_voice = e_voice
            phrase.set_voice_dir(e_voice.cache_path_segment)
        return
