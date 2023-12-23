"""
Provides a means to access a Player class by name. The map is built using dynamic
code to invoke a Player's register function which adds itself to the map. This
avoids nasty dependency issues during startup.
"""
from backends.players.iplayer import IPlayer
from common.setting_constants import Players
from common.typing import *


class PlayerIndex:
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
        Players.NONE]
    #     Players.WavAudioPlayerHandler,
    #     Players.MP3AudioPlayerHandler,
    #     Players.BuiltInAudioPlayerHandler
    # ]
    _player_lookup: Dict[str, IPlayer] = {}

    @staticmethod
    def register(player_id: str, player: IPlayer) -> None:
        PlayerIndex._player_lookup[player_id] = player
        return

    @staticmethod
    def get_player(player_id: str) -> IPlayer:
        player: IPlayer | None = PlayerIndex._player_lookup.get(player_id)
        if player is None:
            # BootstrapPlayers.load_player(player_id)
            player = PlayerIndex._player_lookup.get(player_id)
        return player
