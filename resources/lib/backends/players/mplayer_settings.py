from __future__ import annotations  # For union operator |

from backends.settings.i_validators import INumericValidator
from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          NumericValidator, StringValidator, Validator)
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import AudioType, PlayerMode, Players
from common.settings_low_level import SettingsProperties

module_logger = BasicLogger.get_logger(__name__)


class MPlayerSettings:
    ID = Players.MPLAYER
    service_ID: str = Services.MPLAYER_ID
    service_type: str = ServiceType.PLAYER
    displayName = 'MPlayer'

    _logger: BasicLogger = None

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
    _supported_input_formats: List[AudioType] = [AudioType.WAV, AudioType.MP3]
    _supported_output_formats: List[AudioType] = []
    _provides_services: List[ServiceType] = [ServiceType.PLAYER,
                                             ServiceType.TRANSCODER]
    SoundCapabilities.add_service(service_ID, _provides_services,
                                  _supported_input_formats,
                                  _supported_output_formats)

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
        # Not supporting Pitch changes with mplayer at this time

        # TTS Speed constraints defined as linear from 0.25 to 4 with 1 being 100%
        # speed. 0.25 is 1/4 speed, 4 is 4x speed. This fits nicely with Mplayer
        # speed settings.
        # Since saving the value in settings.xml as a float makes it more difficult
        # for a human to work with, we save it as an int by scaling it by 100 when it
        # it is saved.
        #
        if MPlayerSettings._logger is None:
            MPlayerSettings._logger = module_logger

        service_properties = {Constants.NAME: cls.displayName}
        SettingsMap.define_service(ServiceType.PLAYER, cls.service_ID,
                                   service_properties)

        speed_validator: NumericValidator
        speed_validator = NumericValidator(SettingsProperties.SPEED,
                                           SettingsProperties.TTS_SERVICE,
                                           minimum=.25, maximum=3,
                                           default=1,
                                           is_decibels=False,
                                           is_integer=False)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.SPEED,
                                   speed_validator)
        """
         MPlayer uses both percentage and decibel volume scales.
         The decibel scale is used for the (-af) audio filter with range -200db .. +40db.
         The percent scale is used for the --volume flag (there are multiple ways to
         specify volume, including json).
        
         TTS uses a decibel scale with range -12db .. +12db. Just convert the
         values with no change. Do this by simply using the TTS volume constraints
        """

        volume_validator: NumericValidator
        volume_validator = NumericValidator(SettingsProperties.VOLUME,
                                            cls.service_ID,
                                            minimum=5, maximum=400,
                                            default=100, is_decibels=False,
                                            is_integer=False)
        SettingsMap.define_setting(cls.service_ID,
                                   SettingsProperties.VOLUME,
                                   volume_validator)

        cache_validator: BoolValidator
        cache_validator = BoolValidator(SettingsProperties.CACHE_SPEECH, cls.service_ID,
                                        default=True)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.CACHE_SPEECH,
                                   cache_validator)

        '''
        pipe_validator: BoolValidator
        pipe_validator = BoolValidator(SettingsProperties.PIPE, cls.service_ID,
                                       default=False)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PIPE,
                                   pipe_validator)
       '''
        allowed_player_modes: List[str] = [
            PlayerMode.FILE.value
        ]
        cls._logger.debug(f'About to import mplayer PLAYER_MODE')
        player_mode_validator: StringValidator
        player_mode_validator = StringValidator(SettingsProperties.PLAYER_MODE,
                                                cls.service_ID,
                                                allowed_values=allowed_player_modes,
                                                default=PlayerMode.FILE.value)
        SettingsMap.define_setting(cls.service_ID, SettingsProperties.PLAYER_MODE,
                                   player_mode_validator)

        x = SettingsMap.get_services_for_service_type(ServiceType.PLAYER)
        cls._logger.debug(f'PLAYERS len: {len(x)}')
        for service_id, label in x:
            cls._logger.debug(f'{service_id} {label}')
