from __future__ import annotations

import io

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
        endpoint = settings.s3_endpoint_url.rstrip("/")
        return f"{endpoint}/{settings.s3_bucket}/{key}"


storage = S3Storage()
