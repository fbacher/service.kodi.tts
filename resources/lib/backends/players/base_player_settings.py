from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, IntValidator, StringValidator,
                                          Validator)
from common.base_services import BaseServices
from common.setting_constants import Players
from common.typing import *


class BasePlayerSettings(BaseServiceSettings):

    broken = False

    # Define TTS native scales for volume, speed, etc
    #
    # Min, Default, Max, Integer_Only (no float)
    ttsPitchConstraints: Constraints = Constraints(0, 50, 99, True, False, 1.0,
                                                   SettingsProperties.PITCH, 50, 1.0)
    ttsVolumeConstraints: Constraints = Constraints(minimum=-12, default=0, maximum=12,
                                                    integer=True, decibels=True,
                                                    scale=1.0,
                                                    property_name=SettingsProperties.VOLUME,
                                                    midpoint=0, increment=1.0)
    ttsSpeedConstraints: Constraints = Constraints(25, 100, 400, False, False, 0.01,
                                                   SettingsProperties.SPEED, 100, 0.25)

    # TODO: move to default settings map
    TTSConstraints: Dict[str, Constraints] = {
        SettingsProperties.SPEED : ttsSpeedConstraints,
        SettingsProperties.PITCH : ttsPitchConstraints,
        SettingsProperties.VOLUME: ttsVolumeConstraints
    }
    # TODO: eliminate these
    pitchConstraints: Constraints = ttsPitchConstraints
    volumeConstraints: Constraints = ttsVolumeConstraints
    speedConstraints: Constraints = ttsSpeedConstraints
    # Volume scale as presented to the user

    # volumeExternalEndpoints = (-12, 12)
    # volumeStep = 1
    # volumeSuffix = 'dB'
    # speedInt = True
    # _loadedSettings = {}
    #  currentSettings = []
    settings: Dict[str, Validator] = {}
    constraints: Dict[str, Constraints] = {}

    initialized_settings: bool = False

    # _supported_input_formats: List[str] = []
    # _supported_output_formats: List[str] = []
    # _provides_services: List[ServiceType] = [ServiceType.ENGINE]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz.initialized_settings:
            return

        if not clz.initialized_settings:
            clz.initialized_settings = True

        allowed_engine_ids: List[str] = [

        ]

    @classmethod
    def init_settings(cls):

        valid_players: List[str] = [Players.SFX, Players.WINDOWS, Players.APLAY,
                                    Players.PAPLAY, Players.AFPLAY, Players.SOX,
                                    Players.MPLAYER, Players.MPG321, Players.MPG123,
                                    Players.INTERNAL, Players.MPG321_OE_PI]
        player_validator: StringValidator
        player_validator = StringValidator(SettingsProperties.PLAYER, cls.service_ID,
                                           allowed_values=valid_players,
                                           default_value=Players.MPLAYER)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER,
                                   player_validator)

    @classmethod
    def register(cls, what: Type[ITTSBackendBase]) -> None:
        BaseServices.register(what)
