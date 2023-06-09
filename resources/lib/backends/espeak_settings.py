from backends.engines.base_engine_settings import BaseEngineServiceSettings
from backends.settings.service_types import Services
from common.setting_constants import Backends


class ESpeakSettings(BaseEngineServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.ESPEAK_ID
    backend_id = Backends.ESPEAK_ID
    service_ID: str = Services.ESPEAK_ID
    displayName = 'eSpeak'
