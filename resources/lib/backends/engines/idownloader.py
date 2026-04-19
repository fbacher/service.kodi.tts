# coding=utf-8
from pathlib import Path

from backends.engines.utils.igenerator_deps import ITTSData
from common.phrases import Phrase
from common.strenum import StrEnum


class OutputType(StrEnum):
    USE_FILE = 'use_file'
    USE_FILE_PTR = 'use_file_ptr'


class IDownloader():

    def __init__(self,
                 output_type: OutputType = OutputType.USE_FILE,
                 **kwargs):
        """
        :param output_type:  How the downloader should handle output
        :param kwargs: Any engine specific arguments
        :return:
        """
        self._phrase: Phrase | None = None
        self._output_type: OutputType = output_type
        self._kwargs: dict = kwargs

    @property
    def output_type(self) -> OutputType:
        return self._output_type

    def save(self, save_file: Path) -> None:
        pass

    def write_to_fp(self, fp):
        raise NotImplementedError

    def download(self, phrase: Phrase, **kwargs) -> int:
        """
        Configure and initiate the next download.
        Depending upon self._output_type, write_to_fp will be used
        to write/concatenate downloaded audio to a file.

        :param phrase:
        :param kwargs: Any engine specific arguments

        :return:

        Raises:
        AssertionError – When text is None or empty; when there’s nothing left to speak
        after pre-precessing, tokenizing and cleaning.
        ValueError – When lang_check is True and lang is not supported.
        RuntimeError – When lang_check is True but there is an error loading the
        languages dictionary.
        """

        raise NotImplementedError

    @property
    def supports_chunks(self) -> bool:
        return True

    @property
    def creates_tmp(self) -> bool:
        return False


class TTSDownloadError(Exception):

    def __init__(self, msg=None):
        self.msg = msg
