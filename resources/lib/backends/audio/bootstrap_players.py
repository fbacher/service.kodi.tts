from common.setting_constants import Players
from common.typing import *


class BootstrapPlayers:
    player_ids: List[str] = [
        Players.MPLAYER,
        Players.SFX,
        Players.WINDOWS,
        Players.APLAY,
        Players.PAPLAY,
        Players.AFPLAY,
        Players.SOX,
        Players.MPG321,
        Players.MPG123,
        Players.MPG321_OE_PI,
        Players.INTERNAL,
        Players.NONE,
        Players.WavAudioPlayerHandler,
        Players.MP3AudioPlayerHandler,
        Players.BuiltInAudioPlayerHandler
    ]
    _initialized: bool = False

    @classmethod
    def init(cls) -> None:
        if not cls._initialized:
            cls.initialized = True

    @classmethod
    def load_player(cls, player_id: str) -> None:
        if player_id == Players.MPLAYER:
            from backends.audio.mplayer_audio_player import MPlayerAudioPlayer
            MPlayerAudioPlayer()
        elif player_id == Players.SFX:
            from backends.audio.sfx_audio_player import PlaySFXAudioPlayer
            PlaySFXAudioPlayer()
        elif player_id == Players.WINDOWS:
            from backends.audio.windows_audio_player import WindowsAudioPlayer
            WindowsAudioPlayer()
        elif player_id == Players.APLAY:
            from backends.audio.aplay_audio_player import AplayAudioPlayer
            AplayAudioPlayer()
        # elif player_id == Players.RECITE_ID:
        elif player_id == Players.PAPLAY:
            from backends.audio.paplay_audio_player import PaplayAudioPlayer
            PaplayAudioPlayer()
        elif player_id == Players.AFPLAY:
            from backends.audio.afplay_audio_player import AfplayPlayer
            AfplayPlayer()
        elif player_id == Players.SOX:
            from backends.audio.sfx_audio_player import PlaySFXAudioPlayer
            PlaySFXAudioPlayer()
        elif player_id == Players.MPG321:
            from backends.audio.mpg321_audio_player import Mpg321AudioPlayer
            Mpg321AudioPlayer()
        elif player_id == Players.MPG123:
            from backends.audio.mpg123_audio_player import Mpg123AudioPlayer
            Mpg123AudioPlayer()
        elif player_id == Players.MPG321_OE_PI:
            from backends.audio.mpg321oep_audio_player import Mpg321OEPiAudioPlayer
            Mpg321OEPiAudioPlayer()
        elif player_id == Players.INTERNAL:
            pass
        elif player_id == Players.NONE:
            pass
        # elif player_id == Players.WavAudioPlayerHandler:
        #    from backends.audio.player_handler import WavAudioPlayerHandler
        #     WavAudioPlayerHandler()
        # elif player_id == Players.MP3AudioPlayerHandler:
        #     from backends.audio.player_handler import MP3AudioPlayerHandler
        #     MP3AudioPlayerHandler()
        # elif player_id == Players.BuiltInAudioPlayerHandler:
        #     pass


BootstrapPlayers.init()
