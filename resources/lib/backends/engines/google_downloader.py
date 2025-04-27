from __future__ import annotations

import threading
from typing import Tuple

from backends.google_data import GoogleData
from common.constants import ReturnCode
from common.exceptions import DownloaderBusyException
from common.logger import *
from gtts import gTTS, gTTSError

from backends.engines.idownloader import IDownloader, TTSDownloadError
from common.phrases import Phrase

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


class MyGTTS(IDownloader):

    # Prevent two simultaneous downloads from occurring: both to reduce cpu and
    # to prevent the same phrases being downloaded at the same time (which causes
    # trouble.

    def __init__(self) -> None:
        """

        """
        super().__init__()
        self.phrase: Phrase | None = None
        self.gtts: gTTS | None = None
        self.lang_code: str | None = None
        self.country_code: str | None = None
        self.country_code: str | None = None
        self.lang_check: bool | None = False
        self.tld: str | None = None

    def config(self, phrase: Phrase, lang_code: str = 'en',
               country_code: str = 'us', tld: str = 'com',
               lang_check: bool = False) -> None:

        """
        Configure and initiate the next download.
        Note that write_to_fp is used to write the downloaded data to a file

        :param phrase:
        :param lang_code:  2-char language code
        :param country_code:  country code
        :param tld: Top Level Domain Google has different voice varients depending upon
               the country. For example, you get a US accent if you use the '.com'
               Internet domain when you get your english translation. If you want
               British English, then you use Britian's TLD 'gb'. Not every domain has
               its own accent, but the major ones tend to.
        :param lang_check: True more error detection, but a bit slower to check
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
        clz = type(self)

        self.phrase = phrase
        self.lang_code = lang_code
        self.country_code: str = country_code
        self.tld = tld
        self.lang_check = lang_check
        data: Tuple[str, str]  # [tld, _]
        data = GoogleData.country_code_country_tld[country_code]
        if data is not None and len(data) == 2:
            tld = data[0]
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'lang: {lang_code} country: {country_code} '
                            f'data: {data} tld: {tld}')
        self.gtts: gTTS = gTTS(phrase.get_text(),
                               lang=lang_code,
                               slow=False,
                               lang_check=lang_check,
                               tld=tld
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

    def write_to_fp(self, fp):
        """
        Causes gtts to write downloaded data to the given file
        :param fp:
        :return:
        """
        try:
            self.gtts.write_to_fp(fp)
        except gTTSError as e:
            raise TTSDownloadError() from e
        self.gtts = None
