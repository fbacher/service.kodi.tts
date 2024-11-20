from __future__ import annotations  # For union operator |

# from backends.i_tts_backend_base import ITTSBackendBase
# from backends.settings.service_types import Services
import sys

import xbmcaddon

from backends.settings.i_validators import AllowedValue
from backends.settings.service_types import Services, ServiceType
from common import *

from backends.base import BaseEngineService
from backends.settings.setting_properties import SettingsProperties
# from backends.settings.settings_map import SettingsMap
# from backends.settings.validators import StringValidator
from backends.settings.settings_map import Reason, SettingsMap
from common.constants import Constants
from common.logger import BasicLogger
from common.setting_constants import Backends, PlayerMode
from common.settings import Settings
# from voiceover import VoiceOverBackend #Can't test
from common.settings_low_level import SettingsLowLevel
from utils import util
from windowNavigation.choice import Choice

# from speechutil import SpeechUtilComTTSBackend

MY_LOGGER = BasicLogger.get_logger(__name__)


class BootstrapEngines:
    # Instances of ITTSBackendBase
    engine_ids_by_priority: List[str] = [  # SAPITTSBackend(),
        Backends.NO_ENGINE_ID,
        # OSXSayTTSBackend(),
        Backends.ESPEAK_ID,
        # JAWSTTSBackend(),
        # NVDATTSBackend(),
        # Backends.FLITE_ID,
        # Backends.PICO_TO_WAVE_ID,
        # Backends.PIPER_ID,
        # Backends.FESTIVAL_ID,
        # CepstralTTSBackend(),
        #            CepstralTTSOEBackend(),
        # Backends.SPEECH_DISPATCHER_ID,
        #            VoiceOverBackend(),
        # SpeechServerBackend(),
        # ReciteTTSBackend(),
        # GoogleTTSBackend(),
        Backends.GOOGLE_ID,
        # Backends.RESPONSIVE_VOICE_ID,
        # Backends.EXPERIMENTAL_ENGINE_ID,
        #   SpeechUtilComTTSBackend(),
        # ESpeakCtypesTTSBackend(),
        # Backends.SAPI_ID,
        # Backends.LOG_ONLY_ID
    ]
    if Constants.PLATFORM_WINDOWS:
        engine_ids_by_priority.append(Backends.POWERSHELL_ID)
    _initialized: bool = False
    '''
    @classmethod
    def init(cls) -> None:
        MY_LOGGER.debug(f'initializing')
        cls._initialized = True
        MY_LOGGER = MY_LOGGER
        addon = xbmcaddon.Addon(Constants.ADDON_ID)
        all_settings: xbmcaddon.Settings = addon.getSettings()
        # bval: bool = all_settings.getBool('gui.tts')
        engine: str = all_settings.getString('engine')
        debug_level: int = all_settings.getInt('debug_log_level.tts')
        speed_tts: int = all_settings.getInt('speed.tts')
        gender_eSpeak: str = all_settings.getString('gender.eSpeak')

        MY_LOGGER.debug(f'engine: {engine} debug_level: {debug_level} '
                          f'speed_tts: {speed_tts} gender: {gender_eSpeak}')

        all_settings.setString('engine', 'Trouble')
        addon.openSettings()
        exit(0)
        return
    '''

    @classmethod
    def init(cls) -> None:
        # Initialize the players since engine availability depends upon player
        # availability). Further, Players don't have such dependencies on engines.

        # Settings and SettingsLowLevel depend upon the settings being defined
        # before they are loaded.

        from backends.settings.base_service_settings import BaseServiceSettings

        MY_LOGGER.debug(f'Loading BaseServiceSettings.init_settings()')
        BaseServiceSettings.init_settings()
        MY_LOGGER.debug('Loading BaseServiceSettings.init_global_settings()')
        BaseServiceSettings.init_global_settings()
        SettingsLowLevel.load_settings(ServiceType.TTS)
        MY_LOGGER.debug('About to init BootstrapPlayers')

        from backends.audio.bootstrap_players import BootstrapPlayers
        MY_LOGGER.debug(f'Starting BootstrapPlayers')
        BootstrapPlayers.init()
        MY_LOGGER.debug(f'Initialized: {cls._initialized}')
        if not cls._initialized:
            MY_LOGGER.debug(f'initializing')
            cls._initialized = True
            MY_LOGGER.debug(f'About to load_base')
            cls.load_base()
            MY_LOGGER.debug(f'About to determine_available_engines')
            cls.determine_available_engines()
            MY_LOGGER.debug(f'Loading No_Engine')
            cls.load_no_engine()
            MY_LOGGER.debug(f'About to load_current_backend')
            cls.load_current_backend()
            cls.load_default_engine()
            # Load all settings for current backend
            # Can be called multiple times
            # MY_LOGGER.debug(f'About to call Settings.load_settings')
            # Settings.load_settings()
            MY_LOGGER.debug(f'About to load_other_engines')
            cls.load_other_engines()
            #  util.runInThread(cls.load_other_engines, name='bootLd')
            MY_LOGGER.debug(f'About to call Settings.load_settings')
            SettingsLowLevel.load_settings(ServiceType.ENGINE)

    @classmethod
    def load_base(cls):
        MY_LOGGER.debug(f'importing BaseServiceSettings')
        from backends.settings.base_service_settings import BaseServiceSettings
        MY_LOGGER.debug(f'imported BaseServiceSettings')
        BaseServiceSettings()

    @classmethod
    def determine_available_engines(cls):
        try:
            from backends.espeak_settings import ESpeakSettings
            espeak_settings: ESpeakSettings = ESpeakSettings()
            is_available: bool = espeak_settings.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.ESPEAK_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.ESPEAK_ID, Reason.NOT_AVAILABLE)

        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_is_available(Backends.ESPEAK_ID, Reason.BROKEN)
        '''
        try:
            from backends.engines.festival_settings import FestivalSettings
            festival: FestivalSettings = FestivalSettings()
            is_available: bool = festival.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.FESTIVAL_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.FESTIVAL_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_is_available(Backends.FESTIVAL_ID, Reason.BROKEN)

        try:
            from backends.engines.FliteSettings import FliteSettings
            flite: FliteSettings = FliteSettings()
            is_available: bool = flite.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.FLITE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.FLITE_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_is_available(Backends.FLITE_ID, Reason.BROKEN)
        '''
        try:
            from backends.engines.google_settings import GoogleSettings
            google_settings: GoogleSettings = GoogleSettings()
            is_available: bool = google_settings.available()
            MY_LOGGER.debug(f'google available: {is_available}')
            if is_available:
                SettingsMap.set_is_available(Backends.GOOGLE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.GOOGLE_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_is_available(Backends.GOOGLE_ID, Reason.BROKEN)

        try:
            from backends.no_engine_settings import NoEngineSettings
            no_engine_settings: NoEngineSettings = NoEngineSettings()
            is_available: bool = no_engine_settings.available()
            MY_LOGGER.debug(f'no_engine available: {is_available}')
            if is_available:
                SettingsMap.set_is_available(Backends.NO_ENGINE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.NO_ENGINE_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_is_available(Backends.NO_ENGINE_ID, Reason.BROKEN)
        '''
        try:
            from backends.settings.Pico2WaveSettings import Pico2WaveSettings
            pico2Wave: Pico2WaveSettings = Pico2WaveSettings()
            is_available: bool = pico2Wave.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.PICO_TO_WAVE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.PICO_TO_WAVE_ID,
                                             Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_is_available(Backends.PICO_TO_WAVE_ID, Reason.BROKEN)
        try:
            from backends.settings.piper_settings import PiperSettings
            piper: PiperSettings = PiperSettings()
            is_available: bool = piper.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.PIPER_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.PIPER_ID,
                                             Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_is_available(Backends.PIPER_ID, Reason.BROKEN)

        try:
            from backends.engines.responsive_voice_settings import ResponsiveVoiceSettings
            responsive_settings: ResponsiveVoiceSettings = ResponsiveVoiceSettings()
            is_available: bool = responsive_settings.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.RESPONSIVE_VOICE_ID,
                                             Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.RESPONSIVE_VOICE_ID,
                                             Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_is_available(Backends.RESPONSIVE_VOICE_ID, Reason.BROKEN)

        try:
            from backends.engines.experimental_engine_settings import ExperimentalSettings
            experimental: ExperimentalSettings = ExperimentalSettings()
            is_available: bool = experimental.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.EXPERIMENTAL_ENGINE_ID,
                                             Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.EXPERIMENTAL_ENGINE_ID,
                                             Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_is_available(Backends.EXPERIMENTAL_ENGINE_ID, Reason.BROKEN)

        try:
            from backends.engines.speech_dispatcher_settings import \
                SpeechDispatcherSettings
            spd: SpeechDispatcherSettings = SpeechDispatcherSettings()
            is_available: bool = spd.isInstalled()
            if is_available:
                SettingsMap.set_is_available(Backends.SPEECH_DISPATCHER_ID,
                                             Reason.AVAILABLE)
            else:
                SettingsMap.set_is_available(Backends.SPEECH_DISPATCHER_ID,
                                             Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_is_available(Backends.SPEECH_DISPATCHER_ID, Reason.BROKEN)
        '''
        if Constants.PLATFORM_WINDOWS:
            try:
                MY_LOGGER.debug(f'Loading PowerShell')
                from backends.engines.windows.powershell_settings import \
                                                                   PowerShellTTSSettings
                pwsh: PowerShellTTSSettings = PowerShellTTSSettings()
                is_available: bool = pwsh.isInstalled()
                if is_available:
                    SettingsMap.set_is_available(Services.POWERSHELL_ID,
                                                 Reason.AVAILABLE)
                else:
                    SettingsMap.set_is_available(Services.POWERSHELL_ID,
                                                 Reason.NOT_AVAILABLE)
            except AbortException:
                reraise(*sys.exc_info())
            except Exception as e:
                MY_LOGGER.exception('')
                SettingsMap.set_is_available(Services.POWERSHELL_ID, Reason.BROKEN)

    @classmethod
    def load_no_engine(cls) ->None:
        engine_id: str = SettingsProperties.NO_ENGINE_ID
        MY_LOGGER.debug(f'Trying to load engine: {engine_id}')
        Settings.set_engine_id(engine_id)
        BootstrapEngines.load_engine(engine_id)
        MY_LOGGER.debug(f'Loaded:{engine_id}')

    @classmethod
    def load_current_backend(cls) -> None:
        """
        engine_id_validator = StringValidator(SettingsProperties.ENGINE, '',
                                              allowed_values=Backends.ALL_ENGINE_IDS,
                                              min_length=1,  # Size way too big
                                              max_length=32,
                                              default=Backends.ESPEAK_ID)
        SettingsMap.define_setting(SettingsProperties.ENGINE, Services.TTS_SERVICE,
                                   engine_id_validator)
        """
        engine_id: str = SettingsLowLevel.get_engine_id_ll(bootstrap=True,
                                                           default=None)
        MY_LOGGER.debug(f'engine_id: {engine_id}')
        if engine_id is None:
            engine_id = SettingsProperties.ENGINE_DEFAULT
        MY_LOGGER.debug(f'Trying to load engine: {engine_id}')
        Settings.set_engine_id(engine_id)
        BootstrapEngines.load_engine(engine_id)
        MY_LOGGER.debug(f'Loaded:{engine_id}')

    @classmethod
    def load_default_engine(cls) -> None:
        engine_id = Backends.DEFAULT_ENGINE_ID
        MY_LOGGER.debug(f'Trying to load engine: {engine_id}')
        BootstrapEngines.load_engine(engine_id)
        MY_LOGGER.debug(f'Loaded:{engine_id}')

    @classmethod
    def load_engine(cls, engine_id: str) -> None:
        try:
            available: bool = True
            if not SettingsMap.is_available(engine_id):
                MY_LOGGER.debug(f'{engine_id} NOT SettingsMap.is_available')
                return

            engine: BaseEngineService | None = None
            #  MY_LOGGER.debug(f'Loading service_id: {service_id}')
            if engine_id in (Backends.AUTO_ID, Backends.ESPEAK_ID):
                from backends.espeak import ESpeakTTSBackend
                engine = ESpeakTTSBackend()
            elif engine_id == Backends.FESTIVAL_ID:
                from backends.festival import FestivalTTSBackend
                engine = FestivalTTSBackend()
            elif engine_id == Backends.FLITE_ID:
                from backends.flite import FliteTTSBackend
                engine = FliteTTSBackend()
            elif engine_id == Backends.NO_ENGINE_ID:
                from backends.no_engine import NoEngine
                engine = NoEngine()
            elif engine_id == Backends.PICO_TO_WAVE_ID:
                from backends.pico2wave import Pico2WaveTTSBackend
                engine = Pico2WaveTTSBackend()
            elif engine_id == Backends.PIPER_ID:
                from backends.engines.piper import PiperTTSBackend
                engine = PiperTTSBackend()
            # elif service_id == Backends.RECITE_ID:
            elif engine_id == Backends.RESPONSIVE_VOICE_ID:
                from backends.responsive_voice import ResponsiveVoiceTTSBackend
                engine = ResponsiveVoiceTTSBackend()
            elif engine_id == Backends.EXPERIMENTAL_ENGINE_ID:
                from backends.engines.experimental_engine import ExperimentalTTSBackend
                engine = ExperimentalTTSBackend()
            elif engine_id == Backends.SPEECH_DISPATCHER_ID:
                from backends.speechdispatcher import SpeechDispatcherTTSBackend
                engine = SpeechDispatcherTTSBackend()
            elif engine_id == Backends.GOOGLE_ID:
                from backends.google import GoogleTTSEngine
                engine = GoogleTTSEngine()
            elif Constants.PLATFORM_WINDOWS and engine_id == Backends.POWERSHELL_ID:
                from backends.engines.windows.powershell import PowerShellTTS
                engine = PowerShellTTS()
            elif engine_id == Backends.SAPI_ID:
                try:
                    from backends.sapi import SAPIBackend
                    MY_LOGGER.debug(f'Loading {engine_id}')
                    engine = SAPIBackend()
                    MY_LOGGER.debug(f'Finished loading {engine_id}')
                except Exception as e:
                    MY_LOGGER.exception('Loading SAPI')
                    available = False
            else:  # Catch all default
                pass
                '''
                try:
                    from backends.responsive_voice import ResponsiveVoiceTTSBackend
                    engine = ResponsiveVoiceTTSBackend()
                except Exception as e:
                    MY_LOGGER.exception('Loading DEFAULT engine')
                    available = False
                '''
            try:
                if available:
                    available: bool = engine.available()
                    MY_LOGGER.debug(f'{engine_id} returns available {available}')
                if available:
                    SettingsMap.set_is_available(engine_id, Reason.AVAILABLE)
                else:
                    SettingsMap.set_is_available(engine_id, Reason.NOT_AVAILABLE)
            except Exception:
                MY_LOGGER.exception('')
                SettingsMap.set_is_available(engine_id, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return

    @classmethod
    def load_other_engines(cls) -> None:
        from common.base_services import BaseServices
        for engine_id in cls.engine_ids_by_priority:
            engine_id: str
            if BaseServices.getService(engine_id) is None:
                MY_LOGGER.debug(f'Loading engine: {engine_id}')
                cls.load_engine(engine_id)
                MY_LOGGER.debug(f'Loaded engine: {engine_id}')

        # Include settings for other engines
        # Settings.load_settings()


# BootstrapEngines.init()
