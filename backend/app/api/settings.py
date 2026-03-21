"""Settings API router for service configuration management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ServiceConfig, ServiceType
from app.schemas.service_config import (
    ServiceConfigListResponse,
    ServiceConfigRequest,
    ServiceConfigResponse,
    ServiceTestRequest,
    ServiceTestResponse,
)
from app.services import service_config_repository as config_repo
from app.services.service_test import test_service_connection
from app.utils.encryption import decrypt_api_key, mask_api_key

router = APIRouter(
    prefix="/api/v1/settings/services",
    tags=["Settings"],
)


def _to_response(config: ServiceConfig) -> ServiceConfigResponse:
    plain_key = decrypt_api_key(config.encrypted_api_key)
    return ServiceConfigResponse(
        service_type=config.service_type,
        url=config.url,
        masked_api_key=mask_api_key(plain_key),
        is_configured=True,
    )


@router.get("", response_model=ServiceConfigListResponse)
async def list_services(
    session: AsyncSession = Depends(get_session),
) -> ServiceConfigListResponse:
    """Get all service configs. Unconfigured services return is_configured=False."""
    configs = await config_repo.get_all_configs(session)
    configured = {c.service_type: c for c in configs}

    services = []
    for st in ServiceType:
        if st in configured:
            services.append(_to_response(configured[st]))
        else:
            services.append(
                ServiceConfigResponse(
                    service_type=st,
                    url="",
                    masked_api_key="",
                    is_configured=False,
                )
            )
    return ServiceConfigListResponse(services=services)


@router.put("/{service}", response_model=ServiceConfigResponse)
async def upsert_service(
    service: ServiceType,
    body: ServiceConfigRequest,
    session: AsyncSession = Depends(get_session),
) -> ServiceConfigResponse:
    """Create or update a service config.

    Partial update is supported: omit a field to keep the existing value.
    If no config exists yet, both url and api_key are required.
    """
    existing = await config_repo.get_config_by_service(session, service)

    if existing is None:
        if body.url is None or body.api_key is None:
            raise HTTPException(
                status_code=422,
                detail="Both url and api_key are required when creating a new service config",
            )
        url, api_key = body.url, body.api_key
    else:
        url = body.url if body.url is not None else existing.url
        api_key = (
            body.api_key
            if body.api_key is not None
            else decrypt_api_key(existing.encrypted_api_key)
        )

    config = await config_repo.upsert_config(session, service, url, api_key)
    await session.commit()
    await session.refresh(config)
    return _to_response(config)


@router.delete("/{service}", status_code=204)
async def delete_service(
    service: ServiceType,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a service config."""
    deleted = await config_repo.delete_config(session, service)
    if not deleted:
        raise HTTPException(status_code=404, detail="Service config not found")
    await session.commit()


@router.post("/{service}/test", response_model=ServiceTestResponse)
async def test_service(
    service: ServiceType,
    body: ServiceTestRequest,
) -> ServiceTestResponse:
    """Test connection using provided url + api_key (before saving)."""
    success, message = await test_service_connection(service, body.url, body.api_key)
    return ServiceTestResponse(service_type=service, success=success, message=message)
