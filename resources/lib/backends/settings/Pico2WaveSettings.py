from backends.settings.service_types import Services
from common.setting_constants import Backends


class Pico2WaveSettings:
    # Only returns .mp3 files
    ID: str = Backends.PICO_TO_WAVE_ID
    backend_id = Backends.PICO_TO_WAVE_ID
    service_ID: str = Services.PICO_TO_WAVE_ID
    displayName = 'Pico2Wave'
