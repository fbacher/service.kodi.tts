from backends.engines.base_engine_settings import BaseEngineServiceSettings
from backends.settings.service_types import Services
from common.setting_constants import Backends


class SpeechDispatcherSettings(BaseEngineServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.SPEECH_DISPATCHER_ID
    backend_id = Backends.SPEECH_DISPATCHER_ID
    service_ID: str = Services.SPEECH_DISPATCHER_ID
    displayName = 'Speech Dispatcher'
