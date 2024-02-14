from __future__ import annotations  # For union operator |

from common import *

from backends.audio.base_audio import AudioPlayer
from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import ServiceType
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.setting_constants import Players

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class BuiltInAudioPlayer(AudioPlayer):
    ID = Players.INTERNAL
    service_ID = ID
    sound_file_base = '{speech_file_name}{sound_file_type}'
    sound_dir: str = None

    _supported_input_formats: List[str] = [SoundCapabilities.MP3, SoundCapabilities.WAVE]
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)
    _logger: BasicLogger = None

    def __init__(self, *args, **kwargs):
        super().__init__()
        clz = type(self)
        clz._logger = module_logger.getChild(
                self.__class__.__name__)

        self.volume_configurable = True
        self.pipe_configurable = True
        self.speed_configurable = True
        self.pitch_configurable = True

    def set_speed_configurable(self, configurable):
        self.speed_configurable = configurable

    def canSetSpeed(self):
        return self.speed_configurable

    def set_pitch_configurable(self, configurable):
        self.pitch_configurable = configurable

    def canSetPitch(self):
        return self.pitch_configurable

    def set_volume_configurable(self, configurable):
        self.volume_configurable = configurable

    def canSetVolume(self):
        return self.volume_configurable

    def set_pipe_configurable(self, configurable):
        self.pipe_configurable = configurable

    def canSetPipe(self) -> bool:
        return self.pipe_configurable

    @staticmethod
    def available(ext=None):
        return True

    @classmethod
    def is_builtin(cls):
        #
        # Is this Audio Player built-into the voice engine (i.e. espeak).
        #
        return True

    @classmethod
    def register(cls):
        PlayerIndex.register(BuiltInAudioPlayer.ID, BuiltInAudioPlayer)
        BaseServices.register(cls)
