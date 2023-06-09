from backends.audio.sound_capabilties import SoundCapabilities
from backends.players.base_player_settings import BasePlayerSettings
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          Validator)
from common.setting_constants import Players
from common.settings_low_level import SettingsProperties
from common.typing import *


class Mplayer(BasePlayerSettings):
    ID = Players.MPLAYER
    service_ID: str = Services.MPLAYER_ID
    displayName = 'MPlayer'

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

    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE]
    sound_capabilities = SoundCapabilities(service_ID, _provides_services,
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
        # Must have cls.sound_capabilities defined
        clz.register(clz)

    @classmethod
    def init(cls):
        # Not supporting Pitch changes with mplayer at this time

        # TTS Speed constraints defined as linear from 0.25 to 4 with 1 being 100%
        # speed. 0.25 is 1/4 speed, 4 is 4x speed. This fits nicely with Mplayer
        # speed settings.
        # Since saving the value in settings.xml as a float makes it more difficult
        # for a human to work with, we save it as an int by scaling it by 100 when it
        # it is saved.
        #
        # ttsSpeedConstraints: Constraints = Constraints(25, 100, 400, False, False, 0.01,
        #                                           SettingsProperties.SPEED, 100, 0.25)

        speed_constraints_validator = ConstraintsValidator(SettingsProperties.SPEED,
                                                           cls.backend_id,
                                                           cls.ttsSpeedConstraints)

        # MPlayer uses a decibel volume scale with range -200db .. +40db.
        # TTS uses a decibel scale with range -12db .. +12db. Just convert the
        # values with no change. Do this by simply using the TTS volume constraints

        volume_constraints_validator: ConstraintsValidator
        volume_constraints_validator = ConstraintsValidator(SettingsProperties.VOLUME,
                                                            cls.backend_id,
                                                            cls.ttsVolumeConstraints)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.VOLUME,
                                   volume_constraints_validator)

        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, cls.backend_id,
                                        default=True)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.CACHE_SPEECH,
                                   cache_validator)

        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingsProperties.PIPE, cls.backend_id,
                                       default=False)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PIPE,
                                   pipe_validator)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.SPEED,
                                   speed_constraints_validator)
