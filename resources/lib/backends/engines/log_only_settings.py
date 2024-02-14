from __future__ import annotations  # For union operator |

from common import *

from backends.settings.base_service_settings import BaseServiceSettings
from backends.settings.service_types import Services
from common.setting_constants import Backends


class LogOnlySettings(BaseServiceSettings):
    # Only returns .mp3 files
    ID: str = Backends.LOG_ONLY_ID
    backend_id = Backends.LOG_ONLY_ID
    service_ID: str = Services.LOG_ONLY_ID
    displayName = 'LogOnly'

    @classmethod
    def isSupportedOnPlatform(cls):
        """

        @return:
        """
        return True

    @classmethod
    def isInstalled(cls):
        """

        @return:
        """
        return cls.isSupportedOnPlatform()

    @classmethod
    def available(cls):
        """

        @return:
        """
        return True
