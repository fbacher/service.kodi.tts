from __future__ import annotations  # For union operator |

import sys

from backends.settings.settings_map import Reason, SettingsMap
from common import *
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Players
from common.settings_low_level import SettingsLowLevel
from common.system_queries import SystemQueries

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class BootstrapPlayers:
    player_ids: List[str] = [
        Players.MPV,
        Players.MPLAYER,
        # Players.SFX,
        # Players.WINDOWS,
        # Players.APLAY,
        # Players.PAPLAY,
        # Players.AFPLAY,
        # Players.SOX,
        # Players.MPG321,
        # Players.MPG123,
        # Players.MPG321_OE_PI,
        # Players.INTERNAL,
        # Players.NONE,
        # Players.WavAudioPlayerHandler,
        # Players.MP3AudioPlayerHandler,
        # Players.BuiltInAudioPlayerHandler
    ]
    _initialized: bool = False
    _logger: BasicLogger = None

    @classmethod
    def init(cls) -> None:
        if not cls._initialized:
            if cls._logger is None:
                cls._logger = module_logger.getChild(cls.__name__)
            cls.initialized = True
            if Constants.PLATFORM_WINDOWS:
                cls.player_ids.append(Players.MPLAYER)
            cls.load_players()

    @classmethod
    def load_players(cls):
        for player_id in cls.player_ids:
            cls.load_player(player_id)
        # Add all settings
        SettingsLowLevel.load_settings()
        # SettingsLowLevel.commit_settings()

    @classmethod
    def load_player(cls, player_id: str) -> None:
        try:
            available: bool = True
            if not SettingsMap.is_available(player_id):
                cls._logger.debug(f'{player_id} NOT SettingsMap.is_available')
                return

            if player_id == Players.MPLAYER:
                from backends.players.mplayer_settings import MPlayerSettings
                MPlayerSettings()
                from backends.audio.mplayer_audio_player import MPlayerAudioPlayer
                available = MPlayerAudioPlayer().available()
            if player_id == Players.MPV:
                from backends.players.mpv_player_settings import MPVPlayerSettings
                MPVPlayerSettings()
                from backends.audio.mpv_audio_player import MPVAudioPlayer
                available = MPVAudioPlayer().available()
            elif player_id == Players.SFX:
                from backends.audio.sfx_audio_player import PlaySFXAudioPlayer
                available = PlaySFXAudioPlayer().available()
            elif player_id == Players.WINDOWS:
                if SystemQueries.isWindows():
                    from backends.audio.windows_audio_player import WindowsAudioPlayer
                    available = WindowsAudioPlayer().available()
                else:
                    available = False
            elif player_id == Players.APLAY:
                from backends.audio.aplay_audio_player import AplayAudioPlayer
                available = AplayAudioPlayer().available()
            # elif player_id == Players.RECITE_ID:
            elif player_id == Players.PAPLAY:
                from backends.audio.paplay_audio_player import PaplayAudioPlayer
                available = PaplayAudioPlayer().available()
            elif player_id == Players.AFPLAY:
                from backends.audio.afplay_audio_player import AfplayPlayer
                available = AfplayPlayer().available()
            elif player_id == Players.SOX:
                from backends.audio.sfx_audio_player import PlaySFXAudioPlayer
                available = PlaySFXAudioPlayer().available()
            elif player_id == Players.MPG321:
                from backends.audio.mpg321_audio_player import Mpg321AudioPlayer
                available = Mpg321AudioPlayer().available()
            elif player_id == Players.MPG123:
                from backends.audio.mpg123_audio_player import Mpg123AudioPlayer
                available = Mpg123AudioPlayer().available()
            elif player_id == Players.MPG321_OE_PI:
                from backends.audio.mpg321oep_audio_player import Mpg321OEPiAudioPlayer
                available = Mpg321OEPiAudioPlayer().available()
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
            try:
                if available:
                    SettingsMap.set_is_available(player_id, Reason.AVAILABLE)
                else:
                    cls._logger.debug(f'{player_id} returns NOT available')
                    SettingsMap.set_is_available(player_id, Reason.NOT_AVAILABLE)
            except Exception:
                cls._logger.exception('')
                SettingsMap.set_is_available(player_id, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            cls._logger.exception('')
            SettingsMap.set_is_available(player_id, Reason.BROKEN)

    '''
    @classmethod
    def load_other_players(cls) -> None:
        for player_id in cls.player_ids:
            player_id: str
            if BasePlayerServices.get_player(player_id) is None:
                cls.load_player(player_id)
    '''


BootstrapPlayers.init()
