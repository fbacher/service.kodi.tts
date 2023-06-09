from backends.engines.base_engine_settings import BaseEngineServiceSettings
from backends.settings.service_types import Services
from common.setting_constants import Backends


class FliteSettings(BaseEngineServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.FLITE_ID
    backend_id = Backends.FLITE_ID
    service_ID: str = Services.FLITE_ID
    displayName = 'flite'
