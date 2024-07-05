# coding=utf-8
from typing import List

import xbmcgui

from common.messages import Messages
from common.phrases import PhraseList
from windows.ui_constants import UIConstants


class LabelUtils:



    @classmethod
    def _clean_text(cls, text):
        text = UIConstants.FORMAT_TAG_RE.sub('', text)
        text = UIConstants.COLOR_TAG_RE.sub('', text)
        # Some speech engines say OK as Oklahoma
        text = UIConstants.OK_TAG_RE.sub(r'\1O K\2', text)
        # getLabel() on lists wrapped in [] and some speech engines have
        # problems with text starting with -
        text = text.strip('-[]')
        text = text.replace('XBMC', 'Kodi')
        if text == '..':
            text = Messages.get_msg(Messages.PARENT_DIRECTORY)
        return text

    @classmethod
    def clean_text(cls, text: str | List[str]) -> str | List[str]:
        if isinstance(text, str):
            return cls._clean_text(text)
        else:
            return [cls._clean_text(t) for t in text]
