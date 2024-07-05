# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import io
import os
import pathlib
import re
import sys
from datetime import timedelta
from time import time

import requests
import xbmc

from common import *

from backends.audio.sound_capabilties import ServiceType, SoundCapabilities
from backends.base import SimpleTTSBackend
from backends.players.iplayer import IPlayer
from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import ConstraintsValidator
from cache.voicecache import VoiceCache
from common.base_services import BaseServices
from common.constants import Constants, ReturnCode
from common.exceptions import ExpiredException
from common.logger import *
from common.messages import Messages
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import Backends, Genders, Languages, Mode
from common.settings import Settings
from utils.util import runInThread
from windows.ui_constants import UIConstants

module_logger = BasicLogger.get_module_logger(module_path=__file__)


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
        self.download: bytes = None
        self.finished: bool = False
        self.phrase: Phrase = None

    def get_rc(self) -> ReturnCode:
        return self.rc

    def get_download(self) -> bytes | None:
        return self.download

    def is_finished(self) -> bool:
        return self.finished

    def get_phrase(self) -> Phrase:
        return self.phrase

    def set_finished(self, finished: bool) -> None:
        self.finished = finished

    def set_download(self, data: bytes | None) -> None:
        self.download = data

    def set_rc(self, rc: ReturnCode) -> None:
        self.rc = rc

    def set_phrase(self, phrase: Phrase) -> None:
        self.phrase = phrase


class SpeechGenerator:
    RESPONSIVE_VOICE_URL: Final[
        str] = "http://responsivevoice.org/responsivevoice/getvoice.php"

    _logger: BasicLogger = None
    _initialized: bool = False

    def __init__(self) -> None:
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)
        if not clz._initialized:
            BaseServices().register(self)
            clz._initialized = True
        self.download_results: Results = Results()

    def set_rc(self, rc: ReturnCode) -> None:
        self.download_results.set_rc(rc)

    def get_rc(self) -> ReturnCode:
        return self.download_results.get_rc()

    def set_phrase(self, phrase: Phrase) -> None:
        self.download_results.set_phrase(phrase)

    def set_download(self, download: bytes) -> None:
        self.download_results.set_download(download)

    def set_finished(self) -> None:
        self.download_results.set_finished(True)

    def is_finished(self) -> bool:
        return self.download_results.is_finished()

    def get_results(self) -> Results:
        if self.get_rc() == ReturnCode.OK:
            phrase: Phrase = self.download_results.get_phrase()
            phrase.set_exists(True)
        return self.download_results

    def generate_speech(self, caller: Callable, phrase: Phrase,
                        timeout: float = 30.0) -> Results:
        # Disable expiration checks. We are doing this in background. Results
        # are cached for next time

        unchecked_phrase: Phrase = phrase.clone(check_expired=False)
        self.set_phrase(unchecked_phrase)
        runInThread(self._generate_speech, name='download_speech', delay=0.0,
                    phrase=unchecked_phrase)
        max_wait: int = int(timeout / 0.1)
        while Monitor.exception_on_abort(timeout=0.1):
            max_wait -= 1
            if (self.get_rc() == ReturnCode.OK or caller.stop_processing or
                    max_wait <= 0):
                break
        return self.download_results

    def _generate_speech(self, phrase: Phrase) -> ReturnCode:
        # Break long texts into 250 char chunks so that they can be downloaded.
        # Concatenate returned binary voice files together and return
        clz = type(self)
        self.set_rc(ReturnCode.OK)
        text_file_path: pathlib.Path = None
        try:
            clz._logger.debug_extra_verbose(f'Text len: {len(phrase.get_text())} '
                                            f'{phrase.get_text()}')
            Monitor.exception_on_abort()
            save_copy_of_text: bool = True
            save_to_file: bool = phrase.get_cache_path() is not None

            cache_file: IO[io.BufferedWriter] = None
            if save_to_file:
                rc2: int
                rc2, cache_file = VoiceCache.create_sound_file(phrase.get_cache_path(),
                                                               create_dir_only=False)
                if rc2 != 0 or cache_file is None:
                    if clz._logger.isEnabledFor(ERROR):
                        clz._logger.error(f'Failed to create cache file {cache_file}')
                    self.set_rc(ReturnCode.CALL_FAILED)
                    return self.get_rc()
            try:
                # Should only get here if voiced file (.wav, .mp3, etc.) was NOT
                # found. We might see a pre-existing .txt file which means that
                # the download failed. To prevent multiple downloads, wait a day
                # before retrying the download.

                failing_voice_text_file: pathlib.Path | None = None
                if save_to_file:
                    failing_voice_text_file = phrase.get_cache_path().with_suffix(
                            '.txt')
                    if failing_voice_text_file.is_file():
                        expiration_time: float = time() - timedelta(
                                hours=24).total_seconds()
                        if (
                                os.stat(failing_voice_text_file).st_mtime <
                                expiration_time):
                            clz._logger.debug(f'voice_file_path.unlink(')
                        else:
                            clz._logger.debug_extra_verbose(
                                    'Previous attempt to get speech failed. '
                                    'Skipping.')
                            self.set_rc(ReturnCode.MINOR)
                            return self.get_rc()

                    if save_copy_of_text:
                        path: str
                        file_type: str
                        text_file_path = failing_voice_text_file
                        text_file_path = text_file_path.with_suffix('.txt')
                        try:
                            text_file_path.unlink(missing_ok=True)

                            with text_file_path.open('wt', encoding='utf-8') as f:
                                f.write(phrase.get_text())
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(f'Failed to save voiced text file: '
                                                  f'{text_file_path} Exception: '
                                                  f'{str(e)}')

                # Break long phrases into chunk of 250

                phrase_chunks: PhraseList[Phrase] = self.split_into_chunks(phrase)
                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose(f'phrase_chunks len: '
                                              f'{len(phrase_chunks)}')

                # Pass means for results to be communicated back. Caller can
                # choose to ignore/abandon results, but download will still
                # occur and cached for later use.
                self.download_results: Results = Results()

                runInThread(self.download_speech, name='download_speech', delay=0.0,
                            phrases=phrase_chunks)
                thirty_seconds: int = int(30 / 0.1)
                while Monitor.exception_on_abort(timeout=0.1):
                    thirty_seconds -= 1
                    if (
                            self.download_results.get_rc() == ReturnCode.OK or
                            thirty_seconds <= 0):
                        break

                if self.get_rc() != ReturnCode.OK:
                    text_file_path.unlink(missing_ok=True)

            except AbortException:
                text_file_path.unlink(missing_ok=True)
                self.set_rc(ReturnCode.ABORT)
                reraise(*sys.exc_info())
            except Exception:
                clz._logger.exception('')
                self.set_rc(ReturnCode.CALL_FAILED)
        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            reraise(*sys.exc_info())
        except Exception:
            clz._logger.exception('')
            self.set_rc(ReturnCode.CALL_FAILED)
            return self.get_rc()
        return self.get_rc()

    def download_speech(self, phrases: PhraseList) -> Results:
        # Concatenate returned binary voice files together and return
        clz = type(self)
        aggregate_voiced_bytes: bytes = b''
        try:
            key: str = ResponsiveVoiceTTSBackend.getAPIKey()
            lang: str = ResponsiveVoiceTTSBackend.getLanguage()
            gender: str = ResponsiveVoiceTTSBackend.getGender()
            pitch: str = ResponsiveVoiceTTSBackend.getPitch_str()  # hard coded. Let
            # player decide
            speed: str = ResponsiveVoiceTTSBackend.getApiSpeed()  # Also hard coded
            # value for 1x speed
            volume: str = ResponsiveVoiceTTSBackend.getEngineVolume_str()
            service: str = ResponsiveVoiceTTSBackend.getVoice()
            api_volume: str = volume  # volume
            api_speed = speed
            api_pitch: str = pitch
            params: Dict[str, str] = {"key"   : key,  # "t": text_to_voice,
                                      "tl"    : lang, "pitch": api_pitch,
                                      "rate"  : api_speed,
                                      "vol"   : api_volume, "sv": service, "vn": '',
                                      "gender": gender}
            magic: Final[bytes] = b'<!DOCTYPE'
            failed: bool = False
            with phrases[0].get_cache_path().open('wb') as cache_file:
                phrase: Phrase
                for phrase in phrases:
                    try:
                        Monitor.exception_on_abort()
                        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_verbose(f'phrase: '
                                                      f'{phrase.get_text()}')
                        params["t"] = phrase.get_text()
                        r = requests.get(clz.RESPONSIVE_VOICE_URL, params=params,
                                         timeout=20.0)
                        if r is None or r.status_code != 200:
                            failed = True
                            break
                        else:
                            try:
                                if len(r.content) < 2048:
                                    failed = True
                                    break
                                if r.content[0:len(magic)] == magic:
                                    failed = True
                                    break
                                cache_file.write(r.content)
                                aggregate_voiced_bytes += r.content
                            except IOError:
                                clz._logger.error(f'Error writing to cache file:'
                                                  f' {str(phrase.get_cache_path())}')
                                aggregate_voiced_bytes = b''
                                try:
                                    phrase.get_cache_path().unlink(True)
                                except Exception as e2:
                                    clz._logger.exception('Can not delete '
                                                          f' {str(phrase.get_cache_path())}')

                                '''
                                text_path: pathlib.Path = None
                                try:
                                    text_path = phrase.get_cache_path().with_suffix(
                                        '.txt')
                                    text_path.unlink(True)
                                except Exception as e:
                                    clz._logger.exception(f'Unable to delete '
                                                          f'{str(text_path)}')
                                '''
                        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_extra_verbose(
                                    f'Request status: {r.status_code}'
                                    f' elapsed: {r.elapsed}'
                                    f' content len: {len(r.content)}')
                    except AbortException:
                        self.set_rc(ReturnCode.ABORT)
                        reraise(*sys.exc_info())
                    except Exception as e:
                        clz._logger.exception(f'Error processing phrase: '
                                              f'{phrase.get_text()}')
                        aggregate_voiced_bytes = b''
                        self.set_rc(ReturnCode.DOWNLOAD)
                        break
            if failed:
                reason: str = r.reason

                if reason == 'OK':
                    reason = 'Bad audio file'
                if clz._logger.isEnabledFor(ERROR):
                    clz._logger.error(f'Failed to download voice for {phrase.get_text()} '
                                      f'status: {r.status_code:d} reason {reason}')
        except AbortException:
            self.set_rc(ReturnCode.ABORT)
            reraise(*sys.exc_info())
        except Exception as e:
            if clz._logger.isEnabledFor(ERROR):
                clz._logger.error('Failed to download voice: {}'.format(str(e)))
            aggregate_voiced_bytes = b''
            self.set_rc(ReturnCode.DOWNLOAD)
        finally:
            if self.get_rc() != ReturnCode.OK:
                aggregate_voiced_bytes = b''
                try:
                    phrases[0].get_cache_path().unlink(True)
                except Exception:
                    clz._logger.exception('')

        self.set_download(aggregate_voiced_bytes)
        return None

    def split_into_chunks(self, phrase: Phrase) -> PhraseList[Phrase]:
        clz = type(self)
        phrases: PhraseList[Phrase] = PhraseList(check_expired=False)
        phrases.check_expired = False
        out_chunks: List[str] = []
        try:
            chunks: List[str] = re.split(UIConstants.PUNCTUATION_PATTERN, phrase.get_text())
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'len chunks: {len(chunks)}')
            text_file_path: pathlib.Path
            text_file_path = phrase.get_cache_path().with_suffix('.txt')
            with text_file_path.open('at', encoding='utf-8') as text_file:
                while len(chunks) > 0:
                    Monitor.exception_on_abort()
                    chunk: str = chunks.pop(0)
                    # When a chunk exceeds the maximum chunk length,
                    # go ahead and return the over-length chunk.

                    if (len(chunk) >= clz.MAXIMUM_PHRASE_LENGTH):
                        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_verbose(f'Long chunk: {chunk}'
                                                      f' length: {len(chunk)}')
                            try:
                                text_file.write(f'\nPhrase: {chunk}')
                            except Exception as e:
                                clz._logger.exception(f'Failed to save text cache file')
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
                                    next_chunk)) <= clz.MAXIMUM_PHRASE_LENGTH):
                                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                                    clz._logger.debug_verbose(f'Appending to chunk:'
                                                              f' {next_chunk}'
                                                              f' len: {len(next_chunk)}')
                                xbmc.log(f'Appending to next_chunk:'
                                         f' {next_chunk}'
                                         f' len: {len(next_chunk)}', xbmc.LOGDEBUG)
                                chunk += chunks.pop(0)
                            else:
                                out_chunks.append(chunk)
                                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                                    clz._logger.debug_verbose(f'Normal chunk: {chunk}'
                                                              f' length: {len(chunk)}')
                                xbmc.log(f'Normal chunk: {chunk}'
                                         f' length: {len(chunk)}', xbmc.LOGDEBUG)
                                chunk = ''
                                break
                    if len(chunk) > 0:
                        out_chunks.append(chunk)
                        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_verbose(f'Last chunk: {chunk}'
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
            self.set_rc(ReturnCode.ABORT)
            reraise(*sys.exc_info())
        except ExpiredException:
            phrases = PhraseList()
            phrases.serial_number = phrase.serial_number
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
        return phrases


class ResponsiveVoiceTTSBackend(SimpleTTSBackend):
    ID: str = Backends.RESPONSIVE_VOICE_ID
    backend_id: str = Backends.RESPONSIVE_VOICE_ID
    service_ID: str = Services.RESPONSIVE_VOICE_ID
    service_TYPE: str = ServiceType.ENGINE

    # The Responsive Voice service was designed to provide text to speech in
    # a browser environment. Responsive Voice can perform the speech generation
    # directly from a remote server, or it can use an O/S supplied speech
    # engine found on Windows, MacOs, iOS, etc. In our case we only use the
    # non-natively produced speech generation.
    #
    # The open-source API that is used defines a large list of voices in
    # voice.py. It specifies parameters that don't appear to do anything,
    # at least for the free voices from Responsive Voice. Further, the
    # class names and parameters specify genders, which are largely incorrect.
    # The most important things that determine the voice are the lang (locale)
    # and the service (blank, g1, g2, g3, although others likely exist). There
    # is little pattern to the service and what it means. The parameters
    # rate, volume, speed, pitch have the expected effect, but gender appears
    # to have no effect for the calls tried. Still, instead of abandoning the
    # classes defined in voice.py and defining my own, the code continues to
    # reference them in part with the idea that they may prove more useful
    # later.
    #
    # In most cases the only difference between several voices appears to
    # be the pitch or speed.

    VOICE_1: str = Messages.get_msg(Messages.VOICE_1)
    VOICE_2: str = Messages.get_msg(Messages.VOICE_2)
    VOICE_3: str = Messages.get_msg(Messages.VOICE_3)

    voices_by_locale_map: Dict[str, Tuple[str, str, str]] = {Languages.LOCALE_AF: (
        (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_AF_ZA                                                  : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_AR_SA                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_BS                                                     : (
            (VOICE_1, "", Genders.MALE), (VOICE_2, "g1", Genders.MALE),
            (VOICE_3, "g2", Genders.MALE)), Languages.LOCALE_CA                 : (
            VOICE_1, "", Genders.MALE), Languages.LOCALE_CA_ES                  : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_CS                                                     : (
            (VOICE_1, "", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_CY                                                     : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_DA_DK                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_DE_DE                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EL_GR                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_AU                                                  : (
            (VOICE_1, "", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_GB                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_IE                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_IN                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_US                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EN_ZA                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_EO                                                     : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_ES_ES                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ES                                                     : (
            (VOICE_1, "", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ES_MX                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ES_US                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_FI_FI                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_FR_BE                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_FR_FR                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_FR_CA                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_FR                                                     : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_HI                                                     : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_HI_IN                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_HR_HR                                                  : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_HU_HU                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_HY_AM                                                  : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_ID_ID                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_IS_IS                                                  : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_IT_IT                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_JA_JP                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_KO_KR                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_LA                                                     : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_LV_LV                                                  : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_NB_NO                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_NL_BE                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_NL_NL                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_NO_NO                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_PL_PL                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_PT_BR                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_PT_PT                                                  : (
            (VOICE_1, "g1", Genders.UNKNOWN), (VOICE_2, "g2", Genders.UNKNOWN)),
        Languages.LOCALE_RO_RO                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_RU_RU                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_SK_SK                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_SQ_AL                                                  : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCAL_SR_ME                                                   : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_SR_RS                                                  : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_SW_KE                                                  : (
            (VOICE_1, "g1", Genders.MALE), (VOICE_2, "g2", Genders.MALE)),
        Languages.LOCALE_TA                                                     : (
            (VOICE_1, "g1", Genders.UNKNOWN), (VOICE_2, "g2", Genders.UNKNOWN)),
        Languages.LOCALE_TH_TH                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_TR_TR                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_VI_VN                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ZH_CN                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ZH_HK                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE)),
        Languages.LOCALE_ZH_TW                                                  : (
            (VOICE_1, "g1", Genders.FEMALE), (VOICE_2, "g2", Genders.FEMALE))}

    _logger: BasicLogger = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__name__)

        self.process = None
        self.stop_processing = False
        self.download_results: Results | None = None
        BaseServices().register(self)

    def init(self) -> None:
        clz = type(self)
        if self.initialized:
            return
        super().init()
        self.update()

    def getMode(self) -> Mode:
        clz = type(self)
        player: IPlayer = self.get_player(clz.service_ID)
        if clz.getSetting(SettingsProperties.PIPE):
            return Mode.PIPE
        else:
            return Mode.FILEOUT

    def runCommand(self, phrase: Phrase) -> bool:
        clz = type(self)
        # If caching disabled, then exists is always false. file_path
        # always contains path to cached file, or path where to download to

        self.stop_processing = False
        file_path: Any
        exists: bool
        voiced_text: bytes
        try:
            if phrase.get_cache_path() is None:
                VoiceCache.get_path_to_voice_file(phrase,
                                                  use_cache=Settings.is_use_cache())
            if not phrase.exists():
                generator: SpeechGenerator = SpeechGenerator()
                results: Results = generator.generate_speech(self, phrase)
                if results.get_rc() == ReturnCode.OK:
                    phrase.set_exists(True)
        except ExpiredException:
            return False

        return phrase.exists()

    def runCommandAndPipe(self, phrase: Phrase):
        clz = type(self)

        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        self.stop_processing = False
        audio_pipe = None
        voice_file: pathlib.Path | None
        exists: bool
        byte_stream: io.BinaryIO = None
        try:
            VoiceCache.get_path_to_voice_file(phrase, use_cache=Settings.is_use_cache())
            if not phrase.exists():
                generator: SpeechGenerator = SpeechGenerator()
                results: Results = generator.generate_speech(self, phrase)
                if results.get_rc() == ReturnCode.OK:
                    phrase.set_exists(True)
                    byte_stream = io.BytesIO(self.download_results.download)
            else:
                try:
                    byte_stream = io.open(phrase.get_cache_path(), 'br')
                except Exception:
                    clz._logger.exception('')
                    byte_stream = None

        except ExpiredException:
            pass
        # the following a geared towards Mplayer. Assumption is that only adjust
        # volume in player, other settings in engine.

        # volume_db: float = clz.get_volume_db()  # -12 .. 12
        return byte_stream

    def seed_text_cache(self, phrases: PhraseList) -> None:
        # For engine that are expensive, it can be beneficial to cache the voice
        # files. In addition, by saving text to the cache that is not yet
        # voiced, then a background process can generate speech so the cache
        # gets built more quickly

        clz = type(self)
        try:
            # We don't care whether it is too late to say this text.

            phrases = phrases.clone(check_expired=False)
            for phrase in phrases:
                if Settings.is_use_cache():
                    VoiceCache.get_path_to_voice_file(phrase, use_cache=True)
                    if not phrase.exists():
                        text_to_voice: str = phrase.get_text()
                        voice_file_path: pathlib.Path = phrase.get_cache_path()
                        clz._logger.debug_extra_verbose(f'PHRASE Text {text_to_voice}')
                        rc: int = 0
                        try:
                            # Should only get here if voiced file (.wav, .mp3,
                            # etc.) was NOT
                            # found. We might see a pre-existing .txt file which means
                            # that
                            # the download failed. To prevent multiple downloads,
                            # wait a day
                            # before retrying the download.

                            voice_text_file: pathlib.Path | None = None
                            voice_text_file = voice_file_path.with_suffix('.txt')
                            try:
                                if os.path.isfile(voice_text_file):
                                    os.unlink(voice_text_file)

                                with open(voice_text_file, 'wt', encoding='utf-8') as f:
                                    f.write(text_to_voice)
                            except Exception as e:
                                if clz._logger.isEnabledFor(ERROR):
                                    clz._logger.error(
                                            f'Failed to save voiced text file: '
                                            f'{voice_text_file} Exception: {str(e)}')
                        except Exception as e:
                            if clz._logger.isEnabledFor(ERROR):
                                clz._logger.error(
                                        'Failed to download voice: {}'.format(str(e)))
        except Exception as e:
            clz._logger.exception('')

    def update(self):
        self.process = None
        self.stop_processing = False

    def close(self):
        # self._close()
        pass

    def _close(self):
        # self.stop()
        # super()._close()
        pass

    def stop(self):
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose('stop')
        self.stop_processing = True
        if not self.process:
            return
        try:
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose('terminate')
            self.process.terminate()  # Could use self.process.kill()
        except AbortException:
            reraise(*sys.exc_info())
        except:
            pass

    @classmethod
    def settingList(cls, setting, *args) -> List[str] | List[Tuple[str, str]] | Tuple[
        List[str], str] | Tuple[List[Tuple[str, str]], str]:
        """
        Gets the possible specified setting values in same representation
        as stored in settings.xml (not translated). Sorting/translating done
        in UI.

        :param setting:
        :param args:
        :return:
        """
        if setting == SettingsProperties.LANGUAGE:
            # Returns list of languages and value of closest match to current
            # locale

            locales = cls.voices_by_locale_map.keys()

            # Get current process' language_code i.e. en-us
            default_locale = Constants.LOCALE.lower().replace('_', '-')

            longest_match = -1
            default_lang = default_locale[0:2]
            default_lang_country = ''
            if len(default_locale) >= 5:
                default_lang_country = default_locale[0:5]

            idx = 0
            languages = []
            # Sort by locale so that we have shortest locales listed first
            # i.e. 'en" before 'en-us'
            for locale in sorted(locales):
                lower_lang = locale.lower()
                if longest_match == -1:
                    if lower_lang.startswith(default_lang):
                        longest_match = idx
                elif lower_lang.startswith(default_lang_country):
                    longest_match = idx
                elif lower_lang.startswith(default_locale):
                    longest_match = idx

                lang = Languages.get_label(locale)
                entry = (lang, locale)  # Display value, setting_value
                languages.append(entry)
                idx += 1

            # Now, convert index to index of default_setting

            default_setting = ''
            if longest_match > 0:
                default_setting = languages[longest_match][1]

            return languages, default_setting

        elif setting == SettingsProperties.GENDER:
            current_locale = cls.getLanguage()
            voices = cls.voices_by_locale_map.get(current_locale)

            genders = set()
            if voices is not None:
                for voice_name, voice_id, gender_id in voices:
                    genders.add(gender_id)

            return list(genders)

        elif setting == SettingsProperties.VOICE:
            current_locale = cls.getLanguage()
            voices = cls.voices_by_locale_map.get(current_locale)

            voice_ids: List[Tuple[str, str]] = list()
            if voices is not None:
                for voice_name, voice_id, gender_id in voices:
                    voice_name: str
                    voice_id: str

                    # TODO: translate voice_id
                    voice_ids.append((voice_name, voice_id))

            return list(voice_ids)

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            default_player: str = cls.get_setting_default(SettingsProperties.PLAYER)
            player_ids: List[str] = []
            return player_ids, default_player

    @classmethod
    def get_default_language(cls) -> str:
        languages: List[str]
        default_lang: str
        languages, default_lang = cls.settingList(SettingsProperties.LANGUAGE)
        return default_lang

    # Intercept simply for testing purposes: to disable bypass
    # of voicecache during config to avoid hammering remote
    # vender service.
    #
    # TODO: Remove on ship

    @classmethod
    def setSetting(cls, key, value):
        changed = super().setSetting(key, value)
        VoiceCache.for_debug_setting_changed()
        return changed

    @classmethod
    def negotiate_engine_config(cls, backend_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        """
        Player is informing engine what it is capable of controlling
        Engine replies what it is allowing engine to control
        """
        if Settings.is_use_cache():
            return True, True, True

        return False, False, False

    @classmethod
    def getVolumeDb(cls) -> float | None:
        volume_validator: ConstraintsValidator | IValidator
        volume_validator = SettingsMap.get_validator(cls.service_ID,
                                                     property_id=SettingsProperties.VOLUME)
        volume, _, _, _ = volume_validator.get_tts_values()

        return None  # Find out if used

    @classmethod
    def getEngineVolume(cls) -> float:
        """
        Get the configured volume in our standard  -12db .. +12db scale converted
        to the native scale of the API (0.1 .. 1.0). The maximum volume (1.0) is
        equivalent
        to 0db. Since we have to use a different player AND since it almost guaranteed
        that the voiced text is cached, just set volume to fixed 1.0 and let player
        handle volume).
        """
        return cls.getVolumeDb()

    @classmethod
    def getEngineVolume_str(cls) -> str:
        volume_validator: ConstraintsValidator
        volume_validator = cls.get_validator(cls.service_ID,
                                             property_id=SettingsProperties.VOLUME)
        volume: str = volume_validator.getUIValue()
        return volume

    @classmethod
    def getVoice(cls) -> str:
        voice = cls.getSetting(SettingsProperties.VOICE)
        if voice is None:
            lang = cls.voices_by_locale_map.get(cls.getLanguage())
            if lang is not None:
                voice = lang[0][1]
        voice = 'g2'
        return voice

    @classmethod
    def getLanguage(cls) -> str:
        language_validator: ConstraintsValidator
        language_validator = cls.get_validator(cls.service_ID,
                                               property_id=SettingsProperties.LANGUAGE)
        language, _, _, _ = language_validator.get_tts_values()
        language = 'en-US'
        return language

    @classmethod
    def getPitch(cls) -> float:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        pitch_validator: ConstraintsValidator
        pitch_validator = cls.get_validator(cls.service_ID,
                                            property_id=SettingsProperties.PITCH)
        if Settings.is_use_cache():
            pitch = pitch_validator.default_value
        else:
            pitch, _, _, _ = pitch_validator.get_tts_values()
        return pitch

    @classmethod
    def getPitch_str(cls) -> str:
        # Range 0 .. 99, 50 default
        # API 0.1 .. 1.0. 0.5 default
        # TODO: Solve this differently!!!!

        pitch: float = cls.getPitch()
        return '{:.2f}'.format(pitch)

    @classmethod
    def getSpeed(cls) -> float:
        # Native ResponsiveVoice speed is 1 .. 100, with default of 50,
        # Since Responsive voice always requires a player, and caching is
        # a practical necessity, a fixed setting of 50 is used with Responsive Voice
        # and leave it to the player to adjust speed.
        #
        # Kodi TTS uses a speed of +0.25 .. 1 .. +4.0
        # 0.25 is 1/4 speed and 4.0 is 4x speed
        #
        # This speed is represented as a setting as in integer by multiplying
        # by 100.
        #
        speed_validator: ConstraintsValidator
        speed_validator = cls.get_validator(cls.service_ID,
                                            property_id=SettingsProperties.SPEED)
        speed, _, _, _ = speed_validator.get_tts_value()
        # speed = float(speed_i) / 100.0
        return speed

    @classmethod
    def getApiSpeed(cls) -> str:
        speed: float = cls.getSpeed()
        # Leave it to the player to adjust speed
        return "50"

    @classmethod
    def getGender(cls) -> str:
        gender = 'female'
        return gender

    @classmethod
    def getAPIKey(cls) -> str:
        return cls.getSetting(SettingsProperties.API_KEY)

    # All voices are empty strings
    # def setVoice(self, voice):
    #    self.voice = voice

    @staticmethod
    def available() -> bool:
        engine_output_formats: List[str]
        engine_output_formats = SoundCapabilities.get_output_formats(
                ResponsiveVoiceTTSBackend.service_ID)
        candidates: List[str]
        candidates = SoundCapabilities.get_capable_services(
                service_type=ServiceType.PLAYER, consumer_formats=[SoundCapabilities.MP3],
                producer_formats=[])
        if len(candidates) > 0:
            return True
