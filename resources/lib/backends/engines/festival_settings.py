from backends.engines.base_engine_settings import BaseEngineServiceSettings
from backends.settings.service_types import Services
from common.setting_constants import Backends


class FestivalSettings(BaseEngineServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.FESTIVAL_ID
    backend_id = Backends.FESTIVAL_ID
    service_ID: str = Services.FESTIVAL_ID
    displayName = 'festival'
