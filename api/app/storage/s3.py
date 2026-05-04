from __future__ import annotations

import io
from urllib.parse import urlparse

import boto3
from botocore.client import Config

from app.core.config import settings


class S3Storage:
    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            use_ssl=settings.s3_use_ssl,
            config=Config(signature_version="s3v4"),
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=settings.s3_bucket)
        except Exception:
            self.client.create_bucket(Bucket=settings.s3_bucket)

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        self.client.upload_fileobj(
            io.BytesIO(data),
            settings.s3_bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        endpoint = self._public_endpoint().rstrip("/")
        return f"{endpoint}/{settings.s3_bucket}/{key}"

    def _public_endpoint(self) -> str:
        configured = settings.s3_public_endpoint_url.strip()
        if configured:
            return configured

        endpoint = settings.s3_endpoint_url.strip()
        parsed = urlparse(endpoint)
        # Dev convenience: docker-internal host `minio` is not reachable by the browser.
        if parsed.hostname == "minio":
            scheme = parsed.scheme or "http"
            port = f":{parsed.port}" if parsed.port else ""
            return f"{scheme}://localhost{port}"
        return endpoint


storage = S3Storage()
