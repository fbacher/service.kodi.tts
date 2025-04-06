# coding=utf-8
from __future__ import annotations  # For union operator |

from pathlib import Path

from backends.settings.service_types import ServiceID, ServiceType
from common import *

from common.phrases import Phrase


class IPlayer:
    ID: str = None
    service_id: str | None = None
    service_type: ServiceType | None= None
    service_key: ServiceID | None = None

    def __init__(self) -> None:
        pass

    def init(self, service_key: ServiceID) -> None:
        pass

    @classmethod
    def set_sound_dir(cls):
        raise NotImplementedError

    @classmethod
    def get_sound_dir(cls) -> Path:
        raise NotImplementedError

    @classmethod
    def get_tmp_path(cls, speech_file_name: str, sound_file_type: str) -> Path:
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

    def stop_player(self, purge: bool = True,
                    keep_silent: bool = False,
                    kill: bool = False):
        """
        Stop player_key (most likely because current text is expired)
        Engines may wish to override this method, particularly when
        the player_key is built-in.

        :param purge: if True, then purge any queued vocings
                      if False, then only stop playing current phrase
        :param keep_silent: if True, ignore any new phrases until restarted
                            by resume_player.
                            If False, then play any new content
        :param kill: If True, kill any player_key processes. Implies purge and
                     keep_silent.
                     If False, then the player_key will remain ready to play new
                     content, depending upon keep_silent
        :return:
        """
        raise NotImplementedError()

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

    def is_slave_player(self) -> bool:
        return False

    @staticmethod
    def register() -> None:
        raise NotImplementedError

    def destroy(self):
        raise NotImplementedError()
