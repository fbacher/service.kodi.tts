# coding=utf-8
from __future__ import annotations  # For union operator |

import sys

import xbmc

from backends.settings.service_types import ServiceKey, ServiceType
from backends.settings.settings_map import Status, SettingsMap
from common import *
from common.constants import Constants
from common.logger import *
from common.service_status import Progress, ServiceStatus
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
        Players.BUILT_IN
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
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'load_player: {player_id}')
            cls.load_player(service_key)
            # Add all settings
            SettingsLowLevel.load_settings(service_key)

    @classmethod
    def load_player(cls, player_key: ServiceID) -> None:
        try:
            player_id: str = player_key.service_id
            service_status: ServiceStatus = ServiceStatus(status=Status.FAILED)

            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'PLATFORM_WINDOWS: {Constants.PLATFORM_WINDOWS}')
            if player_id == Players.MPLAYER and not Constants.PLATFORM_WINDOWS:
                from backends.players.mplayer_settings import MPlayerSettings
                service_status = MPlayerSettings.config_settings()
                if service_status.is_usable():
                    from backends.audio.mplayer_audio_player import MPlayerAudioPlayer
                    MPlayerAudioPlayer()
                else:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'MPlayerSettings is NOT usable but: '
                                        f'{service_status}')
            elif player_id == Players.MPV:
                try:
                    from backends.players.mpv_player_settings import MPVPlayerSettings
                    service_status = MPVPlayerSettings.config_settings()
                except Exception:
                    MY_LOGGER.exception('')
                    SettingsMap.set_available(ServiceKey.MPV_KEY,
                                              ServiceStatus(status=Status.UNKNOWN))
                if service_status.is_usable():
                    from backends.audio.mpv_audio_player import MPVAudioPlayer
                    MPVAudioPlayer()
            elif player_id == Players.SFX:
                from backends.players.sfx_settings import SFXSettings
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug('Loading SFXSettings')
                service_status = SFXSettings.config_settings()
                if service_status.is_usable():
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug('Loading PlaySFXAudioPlayer')
                    from backends.audio.sfx_audio_player import PlaySFXAudioPlayer
                    PlaySFXAudioPlayer()
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
            elif player_id == Players.BUILT_IN:
                from backends.players.builtin_player_settings import BuiltinPlayerSettings
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Loading BuiltInPlayerSettings')
                service_status = BuiltinPlayerSettings.config_settings()
                if service_status.is_usable():
                    from backends.audio.builtin_player import BuiltInPlayer
                    BuiltInPlayer()

            # elif player_id == Players.MP3AudioPlayerHandler:
            #     from backends.audio.player_handler import MP3AudioPlayerHandler
            #     MP3AudioPlayerHandler()
            # elif player_id == Players.BuiltInAudioPlayerHandler:
            #     pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('FAILED')
            SettingsMap.set_available(player_key, ServiceStatus(status=Status.UNKNOWN))

#  Explicitly called by BootstrapEngines
#  BootstrapPlayers.init()
