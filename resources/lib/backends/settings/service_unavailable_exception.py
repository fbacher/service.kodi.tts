# coding=utf-8
from __future__ import annotations  # For union operator |

from common.logger import BasicLogger
from backends.settings.service_types import ServiceID


class ServiceUnavailable(Exception):
    def __init__(self, service_key: ServiceID, reason: str, active: bool | None,
                 msg: str = ''):
        """
        Indicates that a service is not functional for some reason

        :param service_key:
        :param reason:
        :param active: If True, then the service is the currently active service
                       in Settings (ex 'engine_id'). None indicates that active
                       status could not be determined at the time.
        :param msg:
        """
        super().__init__(msg)
        self.service_key: ServiceID = service_key
        self.reason: str = reason
        self.active: bool | None = active
