# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.audio.base_audio import AudioPlayer
from backends.audio.sound_capabilities import SoundCapabilities
from backends.players.builtin_player_settings import BuiltinPlayerSettings
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import PlayerType, ServiceID, ServiceType
from backends.settings.service_unavailable_exception import ServiceUnavailable
from backends.settings.settings_map import Status
from common import *
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import AudioType, Players

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class BuiltInPlayer(AudioPlayer, BaseServices):
    ID = Players.BUILT_IN
    service_id: str = PlayerType.BUILT_IN_PLAYER.value
    service_type: ServiceType = ServiceType.PLAYER
    service_key: ServiceID = ServiceID(service_type, service_id)
    _initialized: bool = False

    def __init__(self):
        clz = BuiltInPlayer
        # Set get here size super also sets clz.get. And clz is the same for
        # both. This messes up register
        if not clz._initialized:
            clz.register(self)
            clz._initialized = True
        super().__init__()

        self.engine_id: str | None = None
        self.configVolume: bool = True
        self.configSpeed: bool = True
        self.engine_key: ServiceID | None = None
        self.engine = None

    def init(self, engine_key: ServiceID):
        self.engine_key = engine_key
        try:
            self.engine = BaseServices.get_service(self.engine_key)
        except ServiceUnavailable:
            MY_LOGGER.warning(f'Could not load engine: {self.engine_key}')
            self.engine = None

    @staticmethod
    def available(ext=None):
        return True

    @classmethod
    def is_builtin(cls):
        #
        # Is this Audio Player built-into the voice engine (i.e. espeak).
        #
        return True

    def stop_player(self, purge: bool = True,
                    keep_silent: bool = False,
                    kill: bool = False):
        pass

    @classmethod
    def register(cls, what):
        PlayerIndex.register(BuiltInPlayer.ID, what)
        BaseServices.register(what)
