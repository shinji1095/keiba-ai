from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_db, require_admin
from app.schemas.admin import (
    OAuthClientCreateRequest,
    OAuthClientCreateResponse,
    OAuthClientListResponse,
    OAuthClientRotateSecretResponse,
    OAuthClientUpdateRequest,
    OAuthClientView,
)
from app.services.oauth_client_service import OAuthClientService

router = APIRouter()


@router.post("/oauth-clients", response_model=OAuthClientCreateResponse)
def create_oauth_client(
    payload: OAuthClientCreateRequest,
    db=Depends(get_db),
    _=Depends(require_admin),
) -> OAuthClientCreateResponse:
    svc = OAuthClientService(db)
    return svc.create_client(payload)


@router.get("/oauth-clients", response_model=OAuthClientListResponse)
def list_oauth_clients(
    page: int = 1,
    page_size: int = 50,
    db=Depends(get_db),
    _=Depends(require_admin),
) -> OAuthClientListResponse:
    svc = OAuthClientService(db)
    return svc.list_clients(page=page, page_size=page_size)


@router.patch("/oauth-clients/{client_id}", response_model=OAuthClientView)
def update_oauth_client(
    client_id: str,
    payload: OAuthClientUpdateRequest,
    db=Depends(get_db),
    _=Depends(require_admin),
) -> OAuthClientView:
    svc = OAuthClientService(db)
    return svc.update_client(client_id, payload)


@router.delete(
    "/oauth-clients/{client_id}",
    status_code=204,
    response_class=Response,
    response_model=None,
)
def revoke_oauth_client(
    client_id: str, db=Depends(get_db), _=Depends(require_admin)
) -> Response:
    svc = OAuthClientService(db)
    svc.revoke_client(client_id)
    return Response(status_code=204)


@router.post(
    "/oauth-clients/{client_id}/rotate-secret",
    response_model=OAuthClientRotateSecretResponse,
)
def rotate_secret(
    client_id: str, db=Depends(get_db), _=Depends(require_admin)
) -> OAuthClientRotateSecretResponse:
    svc = OAuthClientService(db)
    return svc.rotate_secret(client_id)
