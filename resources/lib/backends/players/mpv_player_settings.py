from __future__ import annotations  # For union operator |

from backends.settings.i_validators import INumericValidator
from common import *

from backends.audio.sound_capabilties import SoundCapabilities
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, StringValidator, Validator)
from common.setting_constants import PlayerModes, Players
from common.settings_low_level import SettingsProperties


class MPVPlayerSettings:
    ID = Players.MPV
    service_ID: str = Services.MPV_ID
    displayName = 'MPV'

    """
    In an attempt to bring some consistency between the various players, engines and 
    converters, standard "TTS" constraints are defined which every engine, player,
    converter, etc. is to convert to/from. Hopefully this will help these settings
    to remain sane regardless of the combination of services used. 
    
    So, if an engine does not produce volume that matches the db-scale based
    ttsVolumeConstraints, then the engine needs to create a customer converter. 
    Here, volumeConversionConstraints performs that function. ResponsiveVoice
    uses a percent scale with a default value of 1.0 and a max of 2.0. In 
    ResponsiveVoice.getEngineVolume you can see the conversion using:
    
        volume = cls.volumeConstraints.translate_value(
                                        cls.volumeConversionConstraints, volumeDb)
    
    """

    settings: Dict[str, Validator] = {}

    _supported_input_formats: List[str] = [SoundCapabilities.WAVE, SoundCapabilities.MP3]
    _supported_output_formats: List[str] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

    # Every setting from settings.xml must be listed here
    # SettingName, default value

    initialized: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        if clz.initialized:
            clz.initialized = True
            return
        clz.init()

    @classmethod
    def init(cls):
        # Not supporting Pitch changes with MPV_Player at this time

        # TTS Speed constraints defined as linear from 0.25 to 4 with 1 being 100%
        # speed. 0.25 is 1/4 speed, 4 is 4x speed. This fits nicely with MPV_Player
        # speed settings.
        # Since saving the value in settings.xml as a float makes it more difficult
        # for a human to work with, we save it as an int by scaling it by 100 when it
        # is saved.
        #
        # ttsSpeedConstraints: Constraints = Constraints(25, 100, 400, False, False, 0.01,
        #                                           SettingsProperties.SPEED, 100, 0.25)

        """
         MPlayer uses both percentage and decibel volume scales.
         The decibel scale is used for the (-af) audio filter with range -200db .. +40db.
         The percent scale is used for the --volume flag (there are multiple ways to
         specify volume, including json).

         TTS uses a decibel scale with range -12db .. +12db. Just convert the
         values with no change. Do this by simply using the TTS volume constraints
        """

        tts_volume_validator: INumericValidator
        tts_volume_validator = SettingsMap.get_validator(SettingsProperties.TTS_SERVICE,
                                                         SettingsProperties.VOLUME)
        volume_validator: NumericValidator
        volume_validator = NumericValidator(SettingsProperties.VOLUME,
                                            cls.service_ID,
                                            minimum=5, maximum=400,
                                            default=100, is_decibels=False,
                                            is_integer=False)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.VOLUME,
                                   volume_validator)

        speed_validator: NumericValidator
        speed_validator = NumericValidator(SettingsProperties.SPEED,
                                           cls.service_ID,
                                           minimum=0.25, maximum=3,
                                           is_decibels=False,
                                           is_integer=False)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.SPEED,
                                   speed_validator)

        '''
        volume_constraints_validator: ConstraintsValidator
        volume_constraints_validator = ConstraintsValidator(SettingsProperties.VOLUME,
                                                            cls.service_ID,
                                                            BaseServiceSettings.ttsVolumeConstraints)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOLUME,
                                   volume_constraints_validator)
        '''

        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, cls.service_ID,
                                        default=True)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.CACHE_SPEECH,
                                   cache_validator)

        allowed_player_modes: List[str] = [
            PlayerModes.SLAVE_FILE.value,
            PlayerModes.FILE.value
        ]
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(SettingsProperties.PLAYER_MODE,
                                                cls.service_ID,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerModes.SLAVE_FILE.value)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER_MODE,
                                   player_mode_validator)
        '''
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingsProperties.PIPE, cls.service_ID,
                                       default=False)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PIPE,
                                   pipe_validator)
        '''
