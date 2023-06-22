from backends.settings.service_types import Services
from common.setting_constants import Backends


class LogOnlySettings:
    # Only returns .mp3 files
    ID: str = Backends.LOG_ONLY_ID
    backend_id = Backends.LOG_ONLY_ID
    service_ID: str = Services.LOG_ONLY_ID
    displayName = 'LogOnly'
