# coding=utf-8
# coding=utf-8
from common.phrases import Phrase


class IDownloader():

    def __init__(self):
        """
        :return:
        """
        pass

    def write_to_fp(self, fp):
        raise NotImplementedError


class TTSDownloadError(Exception):

    def __init__(self, msg=None):
        self.msg = msg
