# coding=utf-8
from __future__ import annotations  # For union operator |

import sys

import xbmcaddon

from backends.settings.service_types import ServiceKey, Services, ServiceType, TTS_Type
from common import *

from backends.base import BaseEngineService
from backends.settings.settings_map import Status, SettingsMap
from common.constants import Constants
from backends.settings.service_unavailable_exception import ServiceUnavailable
from common.logger import *
from common.service_status import ServiceStatus, StatusType
from common.setting_constants import Backends
from common.settings_low_level import SettingsLowLevel
from backends.settings.service_types import ServiceID
from windowNavigation.configure import Configure

MY_LOGGER = BasicLogger.get_logger(__name__)


class BootstrapEngines:
    # Instances of ITTSBackendBase
    engine_ids_by_priority: List[str] = [
        # SAPITTSBackend(),
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

    @classmethod
    def init(cls) -> None:
        # Initialize the players since engine availability depends upon player_key
        # availability. Further, Players don't have such dependencies on engines.

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug('About to load TTS_Key settings')
        # Populate the settings cache
        SettingsLowLevel.get_engine_id_ll(ignore_cache=True)

        from backends.audio.bootstrap_players import BootstrapPlayers
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Starting BootstrapPlayers')
        BootstrapPlayers.init()
        if not cls._initialized:
            cls._initialized = True
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'About to determine_available_engines')
            cls.configure_engine_settings()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'About to call Settings.load_settings')
            SettingsLowLevel.load_settings(ServiceKey.TTS_KEY)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'About to load_other_engines')
            cls.load_other_engines()
            cls.verify_configurations()

    @classmethod
    def configure_engine_settings(cls):
        service_status: ServiceStatus = ServiceStatus(status=Status.FAILED)
        if Backends.ESPEAK_ID in cls.engine_ids_by_priority:
            try:
                from backends.espeak_settings import ESpeakSettings
                ESpeakSettings.config_settings()
            except AbortException:
                reraise(*sys.exc_info())
            except Exception as e:
                MY_LOGGER.exception('')
                SettingsMap.set_available(ServiceKey.ESPEAK_KEY,
                                          status=StatusType.BROKEN)
        '''
        try:
            from backends.engines.festival_settings import FestivalSettings
            festival: FestivalSettings = FestivalSettings()
            is_available: bool = festival.isInstalled()
            if is_available:
                SettingsMap.set_available(Backends.FESTIVAL_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_available(Backends.FESTIVAL_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_available(Backends.FESTIVAL_ID, Reason.BROKEN)

        try:
            from backends.engines.FliteSettings import FliteSettings
            flite: FliteSettings = FliteSettings()
            is_available: bool = flite.isInstalled()
            if is_available:
                SettingsMap.set_available(Backends.FLITE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_available(Backends.FLITE_ID, Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_available(Backends.FLITE_ID, Reason.BROKEN)
        '''
        try:
            from backends.engines.google_settings import GoogleSettings
            GoogleSettings.config_settings()
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_available(ServiceKey.GOOGLE_KEY,
                                      StatusType.BROKEN)

        try:
            from backends.no_engine_settings import NoEngineSettings
            NoEngineSettings.config_settings()
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_available(ServiceKey.NO_ENGINE_KEY,
                                      StatusType.BROKEN)
        '''
        try:
            from backends.settings.Pico2WaveSettings import Pico2WaveSettings
            pico2Wave: Pico2WaveSettings = Pico2WaveSettings()
            is_available: bool = pico2Wave.isInstalled()
            if is_available:
                SettingsMap.set_available(Backends.PICO_TO_WAVE_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_available(Backends.PICO_TO_WAVE_ID,
                                             Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_available(Backends.PICO_TO_WAVE_ID, Reason.BROKEN)
        try:
            from backends.settings.piper_settings import PiperSettings
            piper: PiperSettings = PiperSettings()
            is_available: bool = piper.isInstalled()
            if is_available:
                SettingsMap.set_available(Backends.PIPER_ID, Reason.AVAILABLE)
            else:
                SettingsMap.set_available(Backends.PIPER_ID,
                                             Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_available(Backends.PIPER_ID, Reason.BROKEN)

        try:
            from backends.engines.responsive_voice_settings import ResponsiveVoiceSettings
            responsive_settings: ResponsiveVoiceSettings = ResponsiveVoiceSettings()
            is_available: bool = responsive_settings.isInstalled()
            if is_available:
                SettingsMap.set_available(Backends.RESPONSIVE_VOICE_ID,
                                             Reason.AVAILABLE)
            else:
                SettingsMap.set_available(Backends.RESPONSIVE_VOICE_ID,
                                             Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_available(Backends.RESPONSIVE_VOICE_ID, Reason.BROKEN)

        try:
            from backends.engines.experimental_engine_settings import ExperimentalSettings
            experimental: ExperimentalSettings = ExperimentalSettings()
            is_available: bool = experimental.isInstalled()
            if is_available:
                SettingsMap.set_available(Backends.EXPERIMENTAL_ENGINE_ID,
                                             Reason.AVAILABLE)
            else:
                SettingsMap.set_available(Backends.EXPERIMENTAL_ENGINE_ID,
                                             Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_available(Backends.EXPERIMENTAL_ENGINE_ID, Reason.BROKEN)

        try:
            from backends.engines.speech_dispatcher_settings import \
                SpeechDispatcherSettings
            spd: SpeechDispatcherSettings = SpeechDispatcherSettings()
            is_available: bool = spd.isInstalled()
            if is_available:
                SettingsMap.set_available(Backends.SPEECH_DISPATCHER_ID,
                                             Reason.AVAILABLE)
            else:
                SettingsMap.set_available(Backends.SPEECH_DISPATCHER_ID,
                                             Reason.NOT_AVAILABLE)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
            SettingsMap.set_available(Backends.SPEECH_DISPATCHER_ID, Reason.BROKEN)
        '''
        if Constants.PLATFORM_WINDOWS:
            try:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Loading PowerShell')
                from backends.engines.windows.powershell_settings import \
                                                                   PowerShellTTSSettings
                PowerShellTTSSettings.config_settings()
            except AbortException:
                reraise(*sys.exc_info())
            except Exception as e:
                MY_LOGGER.exception('')
                SettingsMap.set_available(ServiceKey.POWERSHELL_KEY,
                                          StatusType.BROKEN)

    @classmethod
    def load_engine(cls, engine_id: str) -> None:
        try:
            engine_service: ServiceID
            engine_service = ServiceID(ServiceType.ENGINE, service_id=engine_id)
            if not SettingsMap.is_available(engine_service):
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'{engine_service} NOT SettingsMap.is_available')
                return

            engine: BaseEngineService | None = None
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Loading service_id: {engine_id}')
            if engine_id in (Backends.ESPEAK_ID):
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
            # elif engine_id == Backends.PIPER_ID:
            #     from backends.engines.piper import PiperTTSBackend
            #     engine = PiperTTSBackend()
            # elif setting_id == Backends.RECITE_ID:
            # elif engine_id == Backends.RESPONSIVE_VOICE_ID:
            #     from backends.responsive_voice import ResponsiveVoiceTTSBackend
            #     engine = ResponsiveVoiceTTSBackend()
            # elif engine_id == Backends.EXPERIMENTAL_ENGINE_ID:
            #     from backends.engines.experimental_engine import ExperimentalTTSBackend
            #     engine = ExperimentalTTSBackend()
            # elif engine_id == Backends.SPEECH_DISPATCHER_ID:
            #     from backends.speechdispatcher import SpeechDispatcherTTSBackend
            #     engine = SpeechDispatcherTTSBackend()
            elif engine_id == Backends.GOOGLE_ID:
                from backends.google import GoogleTTSEngine
                engine = GoogleTTSEngine()
            elif Constants.PLATFORM_WINDOWS and engine_id == Backends.POWERSHELL_ID:
                from backends.engines.windows.powershell import PowerShellTTS
                engine = PowerShellTTS()
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
            service_key: ServiceID | None = None
            try:
                service_key = ServiceID(ServiceType.ENGINE, engine_id,
                                        f'{TTS_Type.SERVICE_ID}')
                # SettingsMap.set_available(service_key, Reason.AVAILABLE)
            except Exception:
                MY_LOGGER.exception('')
                if service_key is not None:
                    SettingsMap.set_available(service_key,
                                              StatusType.BROKEN)
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
            service_key: ServiceID = ServiceID(ServiceType.ENGINE, engine_id,
                                               f'{TTS_Type.SERVICE_ID}')
            try:
                instance: BaseServices | None = None
                try:
                    instance = BaseServices.get_service(service_key)
                except ServiceUnavailable as e:
                    if e.reason != Status.UNKNOWN:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Failed to load {engine_id} reason:'
                                            f' {e.reason}')
                if instance is None:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Loading engine: {engine_id}')
                    cls.load_engine(engine_id)
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Loaded engine: {engine_id}')
            except ServiceUnavailable as e:
                pass  # Fix in verify_configurations (settings incomplete)
            except Exception:
                MY_LOGGER.exception('')
        # Include settings for other engines
        # Settings.load_settings()

    @classmethod
    def verify_configurations(cls) -> None:
        from common.base_services import BaseServices
        for engine_id in cls.engine_ids_by_priority:
            engine_id: str
            service_key: ServiceID = ServiceID(ServiceType.ENGINE, engine_id,
                                               f'{TTS_Type.SERVICE_ID}')
            if not SettingsMap.is_available(service_key):
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Engine NOT available: {service_key}')
                continue
            try:
                configure: Configure = Configure.instance(refresh=True)
                configure.validate_repair(service_key)
            except ServiceUnavailable as e:
                if e.active:  # Must Choose another engine. Let InitTTS deal with it
                    pass
            except Exception:
                MY_LOGGER.exception('')


# BootstrapEngines.init()
