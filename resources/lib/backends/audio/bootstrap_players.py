# coding=utf-8
from __future__ import annotations  # For union operator |

import sys

import xbmc

from backends.settings.service_types import ServiceKey, ServiceType
from backends.settings.settings_map import Status, SettingsMap
from common import *
from common.constants import Constants
from common.logger import *
from common.service_status import Progress, ServiceStatus, StatusType
from common.setting_constants import Players
from common.settings_low_level import SettingsLowLevel
from backends.settings.service_types import ServiceID
from common.system_queries import SystemQueries

MY_LOGGER = BasicLogger.get_logger(__name__)


class BootstrapPlayers:
    player_ids: List[str] = [
        Players.SFX,  # Make FIRST in list. Is failsafe, Kodi internal player
        Players.MPV,
        Players.MPLAYER,
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
        Players.BUILT_IN  # A player which is built into the engine being used
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
            #  SettingsLowLevel.load_settings(service_key)

    @classmethod
    def load_player(cls, player_key: ServiceID) -> None:
        broken: bool = True
        try:
            player_id: str = player_key.service_id
            service_key: ServiceID | None = None

            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'PLATFORM_WINDOWS: {Constants.PLATFORM_WINDOWS}')
            if player_id == Players.MPLAYER and not Constants.PLATFORM_WINDOWS:
                try:
                    service_key = ServiceKey.MPLAYER_KEY
                    from backends.players.mplayer_settings import MPlayerSettings
                    MPlayerSettings.config_settings()
                    if MPlayerSettings.is_usable():
                        from backends.audio.mplayer_audio_player import MPlayerAudioPlayer
                        MPlayerAudioPlayer()
                        broken = False
                except Exception:
                    MY_LOGGER.exception('')
            elif player_id == Players.MPV:
                try:
                    service_key = ServiceKey.MPV_KEY
                    from backends.players.mpv_player_settings import MPVPlayerSettings
                    MPVPlayerSettings.config_settings()
                    if MPVPlayerSettings.is_usable():
                        from backends.audio.mpv_audio_player import MPVAudioPlayer
                        MPVAudioPlayer()
                        broken = False
                except Exception:
                    MY_LOGGER.exception('')
            elif player_id == Players.SFX:
                try:
                    service_key = ServiceKey.SFX_KEY
                    from backends.players.sfx_settings import SFXSettings
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug('Loading SFXSettings')
                    SFXSettings.config_settings()
                    if SFXSettings.is_usable():
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug('Loading PlaySFXAudioPlayer')
                        from backends.audio.sfx_audio_player import PlaySFXAudioPlayer
                        PlaySFXAudioPlayer()
                        broken = False
                except Exception:
                    MY_LOGGER.exception('')
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
                try:
                    service_key = ServiceKey.BUILT_IN_KEY
                    from backends.players.builtin_player_settings import \
                        BuiltinPlayerSettings
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Loading BuiltInPlayerSettings')
                    BuiltinPlayerSettings.config_settings()
                    if BuiltinPlayerSettings.is_usable():
                        from backends.audio.builtin_player import BuiltInPlayer
                        BuiltInPlayer()
                        broken = False
                except Exception:
                    MY_LOGGER.exception('')

            # elif player_id == Players.MP3AudioPlayerHandler:
            #     from backends.audio.player_handler import MP3AudioPlayerHandler
            #     MP3AudioPlayerHandler()
            # elif player_id == Players.BuiltInAudioPlayerHandler:
            #     pass
            if service_key is not None:
                if broken:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'{service_key} is NOT usable')
                    SettingsMap.set_available(service_key, StatusType.BROKEN)
                else:
                    SettingsMap.set_available(service_key, StatusType.OK)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('FAILED')

#  Explicitly called by BootstrapEngines
#  BootstrapPlayers.init()
