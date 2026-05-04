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
        return self.file_url_for_key(key)

    def download_bytes(self, key: str) -> tuple[bytes, str]:
        response = self.client.get_object(Bucket=settings.s3_bucket, Key=key)
        content_type = response.get("ContentType", "application/octet-stream")
        data = response["Body"].read()
        return data, content_type

    def delete_object(self, key: str) -> None:
        self.client.delete_object(Bucket=settings.s3_bucket, Key=key)

    def object_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=settings.s3_bucket, Key=key)
            return True
        except Exception:
            return False

    def list_objects(self, prefix: str) -> list[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                key = item.get("Key")
                if key:
                    keys.append(key)
        return keys

    def key_from_url(self, file_url: str) -> str:
        parsed = urlparse(file_url)
        path = parsed.path.lstrip("/")
        bucket_prefix = f"{settings.s3_bucket}/"
        if path.startswith(bucket_prefix):
            return path[len(bucket_prefix):]
        if path == settings.s3_bucket:
            return ""
        return path

    def file_url_for_key(self, key: str) -> str:
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
