class IPlayer:
    def __init__(self) -> None:
        pass

    def init(self, service_id: str) -> None:
        pass

    @classmethod
    def set_sound_dir(cls):
        raise NotImplemented

    @classmethod
    def get_tmp_path(cls, speech_file_name: str, sound_file_type: str) -> str:
        raise NotImplemented

    def do(self, **kwargs):
        raise NotImplemented

    def canSetSpeed(self) -> bool:
        raise NotImplemented

    def setSpeed(self, speed: float) -> None:
        """

        @param speed:
        """
        raise NotImplemented

    def canSetPitch(self) -> bool:
        """

        @return:
        """
        raise NotImplemented

    def setPitch(self, pitch: float) -> None:
        raise NotImplemented

    def canSetVolume(self) -> bool:
        raise NotImplemented

    def setVolume(self, volume: float) -> None:
        raise NotImplemented

    def canSetPipe(self) -> bool:
        raise NotImplemented

    def pipe(self, source) -> None:
        raise NotImplemented

    def play(self, path: str) -> None:
        raise NotImplemented

    def isPlaying(self) -> bool:
        raise NotImplemented

    def stop(self) -> None:
        raise NotImplemented

    def close(self) -> None:
        raise NotImplemented

    @staticmethod
    def available(ext=None) -> bool:
        raise NotImplemented

    @classmethod
    def is_builtin(cls) -> bool:
        #
        # Is this Audio Player built-into the voice engine (i.e. espeak).
        #
        raise NotImplemented

    @staticmethod
    def register() -> None:
        raise NotImplemented
