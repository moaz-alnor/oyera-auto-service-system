"""Constants and permission identifiers for the service catalogue."""

from enum import StrEnum


class ServicePermissionName(StrEnum):
    """Identify service-catalogue permissions."""

    VIEW_SERVICE = "service_catalogue.view_service"
    ADD_SERVICE = "service_catalogue.add_service"
    CHANGE_SERVICE = "service_catalogue.change_service"
    CHANGE_SERVICE_PRICE = "service_catalogue.change_service_price"
    DEACTIVATE_SERVICE = "service_catalogue.deactivate_service"
    REACTIVATE_SERVICE = "service_catalogue.reactivate_service"
