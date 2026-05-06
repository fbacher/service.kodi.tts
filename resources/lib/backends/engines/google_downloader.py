# coding=utf-8
from __future__ import annotations

import threading
from pathlib import Path
from typing import BinaryIO, Tuple

import langcodes
from backends.engines.utils.igenerator_deps import ITTSData
from backends.google_data import GoogleData
from backends.settings.engine_voice import EngineVoice
from backends.settings.engine_voice_manager import EngineVoiceManager
from common.constants import ReturnCode
from common.logger import *
from gtts import gTTS, gTTSError

from backends.engines.idownloader import IDownloader, OutputType, TTSDownloadError
from common.phrases import Phrase

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)

'''
class Results:
    """
        Contains results of background thread/process
        Provides ability for caller to get status/results
        Also allows caller to abandon results, but allow task to continue
        quietly. This is useful for downloading/generating speech which may
        get canceled before finished, but results can be cached for later use
    """

    def __init__(self):
        self.rc: ReturnCode = ReturnCode.OK
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
'''

class MyGTTS(IDownloader):

    # Prevent two simultaneous downloads from occurring: both to reduce cpu and
    # to prevent timing related side effects of downloading a phrase twice.
    #  TODO: Verify HOW this is accomplished

    def __init__(self,
                 output_type: OutputType = OutputType.USE_FILE_PTR, **kwargs):
        """
        :param output_type:  How the downloader should handle output
        :param kwargs: Any engine specific arguments
        :return:
        """
        super().__init__(output_type, **kwargs)
        MY_LOGGER.debug(f'In google_downloader.init')
        self.phrase: Phrase | None = None
        self._output_type: OutputType = output_type
        self._tts_data: ITTSData | None = kwargs.pop('tts_data', None)
        self.gtts: gTTS | None = None
        self.lang_check: bool = kwargs.get('lang_check', False)
        self.tld: str = kwargs.pop('tld', '')
        MY_LOGGER.debug(f'tts_data: {self._tts_data}')
        MY_LOGGER.debug(f'tld: {self.tld}')

    def download(self, phrase: Phrase, **kwargs) -> None:
        """
        Configure and initiate the next download.
        Note that write_to_fp is used to write the downloaded data to a file

        :param phrase:
        :param kwargs: Any engine specific arguments
        :return:

        Raises:
        AssertionError – When text is None or empty; when there’s nothing left to speak
        after pre-precessing, tokenizing and cleaning.
        ValueError – When lang_check is True and lang is not supported.
        RuntimeError – When lang_check is True but there’s an error loading the
        languages dictionary.

        country_code_country_tld: Dict[str, Tuple[str, str]] = {
                                ISO3166-1, <google tld>, <country name>
        """
        MY_LOGGER.debug(f'In download phrase: {phrase}')
        self.phrase = phrase
        fp = kwargs.get('pipe', None)
        file_path: Path = kwargs.get('tmp_path', None)

        e_voice: EngineVoice = phrase.e_voice
        if e_voice is None:
            e_voice = EngineVoiceManager.get_e_voice()
        e_voice_lang: langcodes.Language = langcodes.Language.get(e_voice.lang)
        lang_code: str = e_voice_lang.language
        country_code: str = e_voice_lang.territory.lower()
        data: Tuple[str, str]  # [tld, _]
        data = GoogleData.country_code_country_tld[country_code]

        if data is not None and len(data) == 2:
            self.tld = data[0]

            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'lang: {lang_code} country: {country_code} '
                                f'data: {data} tld: {self.tld}')
        self.gtts: gTTS = gTTS(phrase.get_text(),
                               lang=lang_code,
                               slow=False,
                               lang_check=self.lang_check,
                               tld=self.tld
                               #  pre_processor_funcs=[
                               #     pre_processors.tone_marks,
                               #     pre_processors.end_of_line,
                               #     pre_processors.abbreviations,
                               #     pre_processors.word_sub,
                               # ],
                               # tokenizer_func=Tokenizer(
                               #         [
                               #             tokenizer_cases.tone_marks,
                               #             tokenizer_cases.period_comma,
                               #             tokenizer_cases.colon,
                               #             tokenizer_cases.other_punctuation,
                               #         ]
                               # ).run,
                               )
        MY_LOGGER.debug(f'writing phrase: {phrase.text}')
        if fp is not None:
            MY_LOGGER.debug(f'write_to_fp phrase: {phrase.text}')
            self.write_to_fp(fp)
        elif file_path is not None:
            self.save(file_path)
        return

    def save(self, save_file: Path) -> None:
        try:
            MY_LOGGER.debug(f'text: {self.phrase.text} save_file {save_file}')
            self.gtts.save(str(save_file))
        except Exception as e:
            MY_LOGGER.exception(str(e))
        MY_LOGGER.debug(f'cache_path exists: {save_file.exists()}')

    def write_to_fp(self, fp: BinaryIO):
        """
        Causes gtts to write downloaded data to the given stream
        :param fp:
        :return:
        """
        try:
            if not self._output_type == OutputType.USE_FILE_PTR:
                raise TTSDownloadError('USE_FILE_PTR not enabled')

            MY_LOGGER.debug(f'text: {self.phrase.get_text()}')
            self.gtts.write_to_fp(fp)
        except gTTSError as e:
            MY_LOGGER.debug(f'Error: {e}')
            raise TTSDownloadError() from e
        #  self.gtts = None
