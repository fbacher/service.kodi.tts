# coding=utf-8
from __future__ import annotations

import sys
import threading
from pathlib import Path

import xbmc

from backends.engines.google_downloader import MyGTTS
from backends.engines.idownloader import IDownloader, TTSDownloadError
from backends.ispeech_generator import ISpeechGenerator
from cache.common_types import CacheEntryInfo
from common.exceptions import AbortException, ExpiredException
from common.settings import Settings
from six import reraise

import langcodes
from backends.base import SimpleTTSBackend
from backends.settings.service_types import ServiceID
from cache.cache_file_state import CacheFileState
from cache.voicecache import VoiceCache
from common.constants import ReturnCode
from common.kodi_player_monitor import KodiPlayerMonitor
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList, PhraseUtils
from utils.util import runInThread

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class Results:
    """
        Contains results of background thread/process
        Provides ability for caller to get status/results
        Also allows caller to abandon results, but allow task to continue
        quietly. This is useful for downloading/generating speech which may
        get canceled before finished, but results can be cached for later use
    """

    def __init__(self):
        self.rc: ReturnCode = ReturnCode.NOT_SET
        # self.download: io.BytesIO = io.BytesIO(initial_bytes=b'')
        self.finished: bool = False
        self.phrase: Phrase | None = None

    def get_rc(self) -> ReturnCode:
        return self.rc

    # def get_download_bytes(self) -> memoryview:
    #     return self.download.getbuffer()

    # def get_download_stream(self) -> io.BytesIO:
    #     return self.download

    def is_finished(self) -> bool:
        return self.finished

    def get_phrase(self) -> Phrase:
        return self.phrase

    def set_finished(self, finished: bool) -> None:
        self.finished = finished

    # def set_download(self, data: bytes | io.BytesIO | None) -> None:
    #     self.download = data

    def set_rc(self, rc: ReturnCode) -> None:
        self.rc = rc

    def set_phrase(self, phrase: Phrase) -> None:
        self.phrase = phrase

    def __str__(self) -> str:
        return f'{self.phrase} finished: {self.finished} rc: {self.rc}'


class SpeechGenerator(ISpeechGenerator):

    exclusive_lock: threading.RLock = threading.RLock()

    def __init__(self, engine_instance: SimpleTTSBackend,
                 downloader: IDownloader,
                 max_phrase_length: int = 0,
                 max_chunk_size:  int = 0) -> None:
        self.download_results: Results = Results()
        self.engine_instance: SimpleTTSBackend = engine_instance
        self._downloader: IDownloader = downloader
        self.voice_cache: VoiceCache = VoiceCache(engine_instance.service_key)
        self.max_phrase_length: int = max_phrase_length
        self.max_chunk_size: int = max_chunk_size

    def set_rc(self, rc: ReturnCode) -> None:
        self.download_results.set_rc(rc)

    def get_rc(self) -> ReturnCode:
        return self.download_results.get_rc()

    def set_phrase(self, phrase: Phrase) -> None:
        self.download_results.set_phrase(phrase)

    # def get_download_bytes(self) -> memoryview:
    #     return self.download_results.get_download_bytes()

    def set_finished(self) -> None:
        self.download_results.set_finished(True)

    def is_finished(self) -> bool:
        return self.download_results.is_finished()

    def generate_speech(self, phrase: Phrase, timeout=1.0) -> Results:
        """
        Generate speech for given phrase. Generation can either be done locally,
        or through a remote service (by forwarding to remote_generate_speech).

        :param phrase:   Phrase to voice
        :param timeout:  Max time to wait
        :return:
        """
        # Disable expiration checks. We are doing this in background. Results
        # are cached for next time
        super().generate_speech(phrase, timeout)
        return self.remote_generate_speech(phrase, timeout)

    def remote_generate_speech(self, phrase: Phrase, timeout=1.0) -> Results:
        """
        :param phrase:   Phrase to voice
        :param timeout:  Max time to wait
        :return:
        """
        # Disable expiration checks. We are doing this in background. Results
        # are cached for next time

        clz = type(self)
        phrase_chunks: PhraseList = PhraseUtils.split_into_chunks(phrase,
                                                                  self.max_chunk_size)
        unchecked_phrase_chunks: PhraseList = phrase_chunks.clone(check_expired=False)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Phrase Chunks: {unchecked_phrase_chunks}')

        phrase.cache_file_state(check_expired=False)
        Monitor.exception_on_abort(timeout=0.0)
        self.engine_instance.update_voice_path(phrase)
        phrase.set_download_pending(True)
        self.set_phrase(phrase)
        if phrase.is_empty():
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Phrase empty')
            self.set_rc(ReturnCode.OK)
            self.set_finished()
            return self.download_results

        phrase.set_cache_file_state(CacheFileState.CREATION_INCOMPLETE)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'runInThread _generate_speech')
        runInThread(self._remote_generate_speech, name='dwnldGen', delay=0.0,
                    phrase_chunks=unchecked_phrase_chunks, original_phrase=phrase,
                    timeout=timeout, gender=phrase.gender)

        max_wait: int = int(timeout / 0.1)
        while max_wait > 0:
            Monitor.exception_on_abort(timeout=0.1)
            max_wait -= 1
            # Background process started elsewhere may finish
            if phrase.cache_file_state() >= CacheFileState.OK:
                break
            if (self.get_rc() >= ReturnCode.MINOR_SAVE_FAIL or
                    KodiPlayerMonitor.instance().isPlaying()):
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'generate_speech exit rc: {self.get_rc().name}  '
                                    f'stop: {KodiPlayerMonitor.instance().isPlaying()}')
                break
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'max_wait: {max_wait} results: {self.download_results}')
        return self.download_results

    def _remote_generate_speech(self, **kwargs) -> None:
        """
            Does the real work of downloading the voiced text.

            DOES NOT check for expired phrases since the download is expensive.
            GenerateSpeech invokes this in its own thread, allowing
            GenerateSpeech to time-out and report an ExpiredException, or
            a timeout failure. Meanwhile this thread should download the
            message and put into the cache.
        :param kwargs:
        :return:
        """
        # Break long texts into 250 char chunks so that they can be downloaded.
        # Concatenate returned binary voice files together and return
        clz = type(self)
        self.set_rc(ReturnCode.OK)
        text_file_path: Path | None = None
        phrase_chunks: PhraseList | None = None
        original_phrase: Phrase | None = None
        lang_code: str | None = None
        country_code: str | None = None
        gender: str = ''
        tld: str = ''
        tld_arg: str = kwargs.get('tld', None)
        if tld_arg is not None:
            tld = tld_arg
        locale_id: str = self.engine_instance.get_voice()
        lang_code = langcodes.Language.get(locale_id).language
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'locale_id: {locale_id} lang_code: {lang_code} language: '
                            f'{langcodes.Language.get(locale_id)}')
        country_code = langcodes.Language.get(locale_id).territory.lower()
        # self._logger.debug(f'voice: {locale_id} lang_code: {lang_code} '
        #                    f'territory: {country_code}')

        # Google don't care about gender
        # arg = kwargs.get('gender', None)
        # if arg is None:
        #     gender: str = GoogleTTSEngine.getGender()
        # else:
        #     gender = arg

        try:
            # The passed in phrase_chunks, are actually chunks of a phrase. Therefor
            # we concatenate the voiced text from each chunk to produce one
            # sound file. This phrase list has expiration disabled.

            phrase_chunks = kwargs.get('phrase_chunks', None)
            if phrase_chunks is None or len(phrase_chunks) == 0:
                self.set_rc(ReturnCode.NO_PHRASES)
                self.set_finished()
                return

            original_phrase = kwargs.get('original_phrase', None)
            # X
            # original_phrase.cache_file_state(check_expired=False)
            # MY_LOGGER.debug(f'phrase to download: {original_phrase} '
            #                 f'path: {original_phrase.get_cache_path(check_expired=False)}')
            Monitor.exception_on_abort()
            if (original_phrase.cache_file_state(check_expired=False) ==
                    CacheFileState.OK):
                self.set_rc(ReturnCode.OK)
                self.set_finished()
                original_phrase.add_event(f'already generated')
                return  # Nothing to do
        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            self.set_finished()
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            self.set_rc(ReturnCode.CALL_FAILED)
            self.set_finished()
            return

        cache_path: Path | None = None
        tmp_path: Path | None = None
        try:
            cache_path = original_phrase.get_cache_path(check_expired=False)
            rc2: int
            rc2, tmp_path, _ = self.voice_cache.create_tmp_sound_file(cache_path,
                                                                      create_dir_only=True)
            if rc2 != 0:
                if MY_LOGGER.isEnabledFor(ERROR):
                    MY_LOGGER.error(f'Failed to create cache directory '
                                    f'{cache_path.parent}')
                original_phrase.set_cache_file_state(CacheFileState.BAD)
                original_phrase.add_event(f'Failed to create cache dir')
                self.set_rc(ReturnCode.CALL_FAILED)
                self.set_finished()
                return

            with clz.exclusive_lock:
                if cache_path.exists():
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'PATH EXISTS: {cache_path}')
                    return
                with open(tmp_path, mode='w+b', buffering=-1) as sound_file:
                    # each 'phrase' is a chunk from one, longer phrase. The chunks
                    # are small enough for gTTS to handle. We append the results
                    # from the phrase_chunks to the same file.
                    for phrase_chunk in phrase_chunks:
                        phrase_chunk: Phrase
                        try:
                            Monitor.exception_on_abort()
                            if MY_LOGGER.isEnabledFor(DEBUG):
                                MY_LOGGER.debug(f'phrase: '
                                                f'{phrase_chunk.get_text()}')

                            my_gtts: MyGTTS = MyGTTS()
                            my_gtts.config(phrase_chunk, lang_code=lang_code,
                                           country_code=country_code, tld=tld)
                            if MY_LOGGER.isEnabledFor(DEBUG):
                                MY_LOGGER.debug(f'GTTS lang: {lang_code}')
                            phrase_chunk.add_event('my_gtts')
                            # gtts.save(phrase.get_cache_path())
                            #     gTTSError – When there’s an error with the API request.
                            # gtts.stream() # Streams bytes
                            my_gtts.write_to_fp(sound_file)
                            if MY_LOGGER.isEnabledFor(DEBUG):
                                MY_LOGGER.debug(f'Wrote cache_file fragment to: '
                                                f'{tmp_path}')
                        except AbortException:
                            self.set_rc(ReturnCode.ABORT)
                            self.set_finished()
                            reraise(*sys.exc_info())
                        except (TypeError, ExpiredException) as e:
                            MY_LOGGER.exception('')
                            self.set_rc(ReturnCode.DOWNLOAD)
                            original_phrase.add_event('expired')
                            self.set_finished()
                        except TTSDownloadError as e:
                            MY_LOGGER.info(f'{TTSDownloadError:} {e.msg}')
                            MY_LOGGER.exception(f'TTSDownloadError')
                            self.set_rc(ReturnCode.DOWNLOAD)
                            original_phrase.add_event('download error')
                            self.set_finished()
                        except IOError as e:
                            MY_LOGGER.exception(f'Error processing phrase: '
                                                f'{phrase_chunk.get_text()}')
                            MY_LOGGER.error(f'Error writing to temp file:'
                                            f' {tmp_path}')
                            original_phrase.add_event('error writing temp')
                            original_phrase.set_cache_file_state(CacheFileState.BAD)
                            self.set_rc(ReturnCode.DOWNLOAD)
                            self.set_finished()
                        except Exception as e:
                            MY_LOGGER.exception('')
                            original_phrase.add_event('download failed')
                            self.set_rc(ReturnCode.DOWNLOAD)
                            self.set_finished()
                if (self.get_rc() == ReturnCode.OK
                        and tmp_path.stat().st_size > 100):
                    try:
                        tmp_path.rename(cache_path)
                        original_phrase.set_exists(True, check_expired=False)
                        original_phrase.set_cache_file_state(CacheFileState.OK)
                        original_phrase.add_event('generation finished')
                        original_phrase.set_download_pending(False)
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'cache_file is: {str(cache_path)}')
                        self.set_finished()
                    except AbortException as e:
                        reraise(*sys.exc_info())
                    except Exception as e:
                        MY_LOGGER.exception('')
                else:
                    self.set_rc(ReturnCode.DOWNLOAD)
                    self.set_finished()
        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            self.set_finished()
            reraise(*sys.exc_info())
        except ExpiredException:
            MY_LOGGER.exception(f'{phrase_chunks}')
            self.set_finished()
            self.set_rc(ReturnCode.DOWNLOAD)
        except Exception as e:
            MY_LOGGER.exception('')
            if MY_LOGGER.isEnabledFor(ERROR):
                MY_LOGGER.error(f'Failed to download voice: {e}')
            self.set_finished()
            self.set_rc(ReturnCode.DOWNLOAD)
        finally:
            tmp_path.unlink(missing_ok=True)
            self.set_finished()
        return None
