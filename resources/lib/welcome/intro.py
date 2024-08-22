# coding=utf-8
from typing import Final


class Introduction:

    INTRO_TEXT: Final[str] = ('Welcome to Kodi Text to Speech which provides basic'
                              'TTS functionality to Kodi. This is based on the '
                              'previous version of XBMC TTS which is no longer '
                              'supported. This version of Kodi TTS is maintained '
                              'by a different team and is a major release. '
                              'This is an early release This is a major release and attempts to'
                              'improve on ')

    def __init__(self) -> None:
        # Disable screen scraping
        # read Intro
