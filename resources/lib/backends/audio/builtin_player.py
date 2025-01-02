from __future__ import annotations  # For union operator |

from backends.audio.base_audio import AudioPlayer
from backends.audio.sound_capabilities import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import ServiceType
from common import *
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import AudioType, Players

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class BuiltInPlayer(AudioPlayer, BaseServices):
    ID = Players.INTERNAL
    service_ID = ID
    service_TYPE: str = ServiceType.PLAYER
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

    def init(self, engine_id: str):
        self.engine_id = engine_id
        engine: BaseServices = BaseServices.getService(engine_id)

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
