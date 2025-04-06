# coding=utf-8
from __future__ import annotations  # For union operator |

import sys

import xbmc

from backends.settings.service_types import ServiceType
from backends.settings.settings_map import Reason, SettingsMap
from common import *
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Players
from common.settings_low_level import SettingsLowLevel
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class BootstrapPlayers:
    player_ids: List[str] = [
        Players.MPV,
        Players.MPLAYER,
        Players.SFX,
        # Players.WINDOWS,
        # Players.APLAY,
        # Players.PAPLAY,
        # Players.AFPLAY,
        # Players.SOX,
        # Players.MPG321,
        # Players.MPG123,
        # Players.MPG321_OE_PI,
        # Players.NONE,
        # Players.WavAudioPlayerHandler,
        # Players.MP3AudioPlayerHandler,
        Players.INTERNAL
    ]
    _initialized: bool = False

    @classmethod
    def init(cls) -> None:
        if not cls._initialized:
            cls.initialized = True
            cls.load_players()

    @classmethod
    def load_players(cls):
        for player_id in cls.player_ids:
            service_key: ServiceID = ServiceID(ServiceType.PLAYER, player_id)
            MY_LOGGER.debug(f'load_player: {player_id}')
            cls.load_player(service_key)
            # Add all settings
            SettingsLowLevel.load_settings(service_key)

    @classmethod
    def load_player(cls, player_key: ServiceID) -> None:
        try:
            player_id: str = player_key.service_id
            available: Reason | None
            if not SettingsMap.is_available(player_key):
                MY_LOGGER.debug(f'{player_id} NOT available')
                return

            if player_id == Players.MPLAYER and not Constants.PLATFORM_WINDOWS:
                from backends.players.mplayer_settings import MPlayerSettings
                available = MPlayerSettings.check_availability()
                if available == Reason.AVAILABLE:
                    from backends.audio.mplayer_audio_player import MPlayerAudioPlayer
                    MPlayerSettings.config_settings()
                    available = MPlayerAudioPlayer().check_availability()
            elif player_id == Players.MPV:
                from backends.players.mpv_player_settings import MPVPlayerSettings
                available = MPVPlayerSettings.check_availability()
                if available == Reason.AVAILABLE:
                    from backends.audio.mpv_audio_player import MPVAudioPlayer
                    MPVPlayerSettings.config_settings()
                    available = MPVAudioPlayer().check_availability()
            elif player_id == Players.SFX:
                from backends.players.sfx_settings import SFXSettings
                MY_LOGGER.debug('Loading SFXSettings')
                available = SFXSettings.check_availability()
                if available == Reason.AVAILABLE:
                    MY_LOGGER.debug('Loading PlaySFXAudioPlayer')
                    from backends.audio.sfx_audio_player import PlaySFXAudioPlayer
                    SFXSettings.config_settings()
                    MY_LOGGER.debug(f'Checking if SFX available {available}')
                    available = PlaySFXAudioPlayer().check_availability()
                    MY_LOGGER.debug('SFX available {available}')
                '''
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
                elif player_id == Players.MPG321:
                    from backends.audio.mpg321_audio_player import Mpg321AudioPlayer
                    available = Mpg321AudioPlayer().available()
                elif player_id == Players.MPG123:
                    from backends.audio.mpg123_audio_player import Mpg123AudioPlayer
                    available = Mpg123AudioPlayer().available()
                elif player_id == Players.MPG321_OE_PI:
                    from backends.audio.mpg321oep_audio_player import Mpg321OEPiAudioPlayer
                    available = Mpg321OEPiAudioPlayer().available()
                '''
            elif player_id == Players.INTERNAL:
                from backends.players.builtin_player_settings import BuiltinPlayerSettings
                MY_LOGGER.debug(f'Loading BuiltInPlayerSettings')
                available = BuiltinPlayerSettings.check_availability()
                if available == Reason.AVAILABLE:
                    MY_LOGGER.debug(f'Loading BuiltinPlayerSettings')
                    BuiltinPlayerSettings.config_settings()
                    from backends.audio.builtin_player import BuiltInPlayer
                    available = BuiltInPlayer().check_availability()
                    MY_LOGGER.debug(f'BuiltInPlayer available: {available}')
            # elif player_id == Players.MP3AudioPlayerHandler:
            #     from backends.audio.player_handler import MP3AudioPlayerHandler
            #     MP3AudioPlayerHandler()
            # elif player_id == Players.BuiltInAudioPlayerHandler:
            #     pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('BROKEN')
            SettingsMap.set_is_available(player_key, Reason.BROKEN)

    '''
    @classmethod
    def load_other_players(cls) -> None:
        for player_id in cls.player_ids:
            player_id: str
            if BasePlayerServices.get_player(player_id) is None:
                cls.load_player(player_id)
    '''


BootstrapPlayers.init()
