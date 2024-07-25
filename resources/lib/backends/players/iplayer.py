from __future__ import annotations  # For union operator |

from common import *

from common.phrases import Phrase


class IPlayer:
    ID: str = None

    def __init__(self) -> None:
        pass

    def init(self, service_id: str) -> None:
        pass

    @classmethod
    def set_sound_dir(cls):
        raise NotImplementedError

    @classmethod
    def get_sound_dir(cls) -> str:
        raise NotImplementedError

    @classmethod
    def get_tmp_path(cls, speech_file_name: str, sound_file_type: str) -> str:
        raise NotImplementedError

    def do(self, **kwargs):
        raise NotImplementedError

    def canSetSpeed(self) -> bool:
        raise NotImplementedError

    def setSpeed(self, speed: float) -> None:
        """

        @param speed:
        """
        raise NotImplementedError

    def canSetPitch(self) -> bool:
        """

        @return:
        """
        raise NotImplementedError

    def setPitch(self, pitch: float) -> None:
        raise NotImplementedError

    def canSetVolume(self) -> bool:
        raise NotImplementedError

    def setVolume(self, volume: float) -> None:
        raise NotImplementedError

    def canSetPipe(self) -> bool:
        raise NotImplementedError

    def pipe(self, source: BinaryIO, phrase: Phrase) -> None:
        raise NotImplementedError

    def play(self, phrase: Phrase) -> None:
        raise NotImplementedError

    def slave_play(self, phrase: Phrase) -> None:
        raise NotImplementedError

    def isPlaying(self) -> bool:
        raise NotImplementedError

    def abort_voicing(self, purge: bool = True, future: bool = False) -> None:
        """
        Stop voicing pending speech and/or future speech.

        Vocing can be resumed using resume_voicing

        :param purge: if True, then abandon playing all pending speech
        :param future: if True, then ignore future voicings.
        :return: None
        """
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    @staticmethod
    def available(ext=None) -> bool:
        raise NotImplementedError

    @classmethod
    def is_builtin(cls) -> bool:
        #
        # Is this Audio Player built-into the voice engine (i.e. espeak).
        #
        raise NotImplementedError

    @staticmethod
    def register() -> None:
        raise NotImplementedError
