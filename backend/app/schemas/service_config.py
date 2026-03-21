"""Pydantic schemas for service config endpoints."""

from pydantic import BaseModel, Field

from app.models import ServiceType


class ServiceConfigRequest(BaseModel):
    """Request body for creating/updating a service config.

    Both fields are optional to support partial updates.
    If no config exists yet, both are required — enforced at service layer.
    """

    url: str | None = Field(default=None, min_length=1, max_length=500)
    api_key: str | None = Field(default=None, min_length=1, max_length=500)


class ServiceTestRequest(BaseModel):
    """Request body for testing a connection before saving."""

    url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, max_length=500)


class ServiceConfigResponse(BaseModel):
    """Single service config response (key masked)."""

    service_type: ServiceType
    url: str
    masked_api_key: str
    is_configured: bool


class ServiceConfigListResponse(BaseModel):
    """List of all service configs."""

    services: list[ServiceConfigResponse]


class ServiceTestResponse(BaseModel):
    """Result of a connection test."""

    service_type: ServiceType
    success: bool
    message: str
