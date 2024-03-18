# coding=utf-8

from common.phrases import Phrase

class IResults:

    def __init__(self) -> None:
        raise NotImplementedError()

class ISpeechGenerator:

    def __init__(self) -> None:
        raise NotImplementedError()

    def generate_speech(self, phrase: Phrase, timeout: float = 1.0) -> IResults:
        raise NotImplementedError()
