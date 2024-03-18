# coding=utf-8
from __future__ import annotations  # For union operator |

from common import *

from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.constraints import Constraints
from backends.settings.service_types import Services
from backends.settings.validators import (NumericValidator, Validator)
from common.base_services import BaseServices
from common.settings_low_level import SettingsProperties


class BasePlayerServiceSettings(BaseServiceSettings):
    service_ID: str = Services.NONE_ID
    displayName: str = 'NoPlayer'
    canStreamWav = False
    inWavStreamMode = False
    interval = 100
    broken = False

    # Define TTS native scales for volume, speed, etc
    #
    # Min, Default, Max, Integer_Only (no float)
    ttsPitchConstraints: Constraints = Constraints(0, 50, 99, True, False, 1.0,
                                                   SettingsProperties.PITCH, 50, 1.0)
    tts_volume_validator: NumericValidator
    tts_volume_validator = NumericValidator(SettingsProperties.VOLUME,
                                            Services.TTS_SERVICE,
                                            minimum=5, maximum=400,
                                            default=100, is_decibels=False,
                                            is_integer=False)

    tts_speed_validator: NumericValidator
    tts_speed_validator = NumericValidator(SettingsProperties.SPEED,
                                           Services.TTS_SERVICE,
                                           minimum=25, maximum=400,
                                           default=100, is_decibels=False,
                                           is_integer=False)

    ttsSpeedConstraints: Constraints = Constraints(25, 100, 400, False, False, 0.01,
                                                   SettingsProperties.SPEED, 100, 0.25)

    # TODO: move to default settings map
    TTSConstraints: Dict[str, Constraints] = {
        SettingsProperties.SPEED: ttsSpeedConstraints,
        SettingsProperties.PITCH: ttsPitchConstraints,
        SettingsProperties.VOLUME: tts_volume_validator
    }
    # TODO: eliminate these
    pitchConstraints: Constraints = ttsPitchConstraints
    volume_validator: NumericValidator = tts_volume_validator
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
        clz.init_settings()

        '''
        CONVERTER?,
        GENDER_VISIBLE,
        GUI,
        SPEECH_DISPATCHER,
        OUTPUT_VIA,
        OUTPUT_VISIBLE,
        SETTINGS_BEING_CONFIGURED,
        SETTINGS_DIGEST,
        SPEAK_VIA_KODI,
        TTSD_HOST,
        TTSD_PORT,
        VOICE_VISIBLE,
        VOLUME_VISIBLE
        '''

    @classmethod
    def init_settings(cls):
        #
        # Need to define Conversion Constraints between the TTS 'standard'
        # constraints/settings to the engine's constraints/settings
        '''
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingsProperties.PIPE, cls.backend_id,
                                       default=False)
        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, cls.backend_id,
                                        default=True)

        #  TODO:  Need to eliminate un-available players
        #         Should do elimination in separate code

        valid_players: List[str] = [Players.SFX, Players.WINDOWS, Players.APLAY,
                                    Players.PAPLAY, Players.AFPLAY, Players.SOX,
                                    Players.MPLAYER, Players.MPG321, Players.MPG123,
                                    Players.INTERNAL, Players.MPG321_OE_PI]
        player_validator: StringValidator
        player_validator = StringValidator(SettingsProperties.PLAYER, cls.backend_id,
                                           allowed_values=valid_players,
                                           default=Players.MPLAYER)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PIPE,
                                   pipe_validator)

        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER,
                                   player_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.CACHE_SPEECH,
                                   cache_validator)
        '''

    @classmethod
    def register(cls, what: Type[ITTSBackendBase]) -> None:
        BaseServices.register(what)  # _settings(what)
