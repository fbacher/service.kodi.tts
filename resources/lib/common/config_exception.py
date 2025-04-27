# coding=utf-8
from backends.settings.service_types import ServiceID
from common.service_status import ServiceStatus


class UnusableServiceException(Exception):
    """
    Indicates that a service is not usable.
    """
    def __init__(self, service_key: ServiceID,
                 reason: ServiceStatus,
                 msg: str = ''):
        super().__init__(msg)
        self.reason: ServiceStatus = reason
        self.service_key: ServiceID = service_key

    def get_reason(self) -> ServiceStatus:
        return self.reason

    def get_service_key(self) -> ServiceID:
        return self.service_key
