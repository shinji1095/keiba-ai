from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from app.core.config import settings
from app.core.errors import AppError


@dataclass
class ScraperIngestClient:
    base_url: str
    timeout_sec: float
    ssl_context: Optional[ssl.SSLContext] = None

    @classmethod
    def from_settings(cls) -> Optional["ScraperIngestClient"]:
        if not settings.scraper_forward_enabled:
            return None
        if not settings.scraper_control_base_url:
            raise AppError.internal(
                "scraper forward is enabled but SCRAPER_CONTROL_BASE_URL is not set"
            )

        base_url = settings.scraper_control_base_url.rstrip("/")
        ssl_context = _build_ssl_context(
            base_url=base_url,
            mtls_cert=settings.scraper_mtls_cert,
            mtls_key=settings.scraper_mtls_key,
            mtls_ca_cert=settings.scraper_mtls_ca_cert,
        )
        return cls(
            base_url=base_url,
            timeout_sec=settings.scraper_forward_timeout_sec,
            ssl_context=ssl_context,
        )

    def post(self, path: str, payload: dict) -> None:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                req, timeout=self.timeout_sec, context=self.ssl_context
            ) as resp:
                if resp.status >= 400:
                    raise AppError.bad_gateway(
                        "scraper ingest failed",
                        details={"url": url, "status": resp.status},
                    )
        except urllib.error.HTTPError as exc:
            raise AppError.bad_gateway(
                "scraper ingest failed",
                details={"url": url, "status": exc.code},
            ) from exc
        except (urllib.error.URLError, ssl.SSLError) as exc:
            raise AppError.bad_gateway(
                "scraper ingest connection error",
                details={"url": url, "reason": str(getattr(exc, "reason", exc))},
            ) from exc


def _build_ssl_context(
    *,
    base_url: str,
    mtls_cert: Optional[str],
    mtls_key: Optional[str],
    mtls_ca_cert: Optional[str],
) -> Optional[ssl.SSLContext]:
    scheme = urlparse(base_url).scheme
    if scheme != "https" and not (mtls_cert or mtls_key or mtls_ca_cert):
        return None

    context = ssl.create_default_context(cafile=mtls_ca_cert or None)
    if mtls_cert and mtls_key:
        context.load_cert_chain(certfile=mtls_cert, keyfile=mtls_key)
    return context
