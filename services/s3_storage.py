"""
S3 Storage Service – handles file upload/download to AWS S3.
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from config.settings import settings

logger = logging.getLogger(__name__)


class S3StorageService:
    """Wrapper around boto3 S3 client."""

    def __init__(self) -> None:
        self.bucket = settings.s3_bucket_name
        self._client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            region_name=settings.aws_region,
        )

    # ── Upload ───────────────────────────────────────────
    def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file-like object to S3. Returns the S3 key."""
        try:
            self._client.upload_fileobj(
                file_obj,
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            logger.info("Uploaded %s to s3://%s/%s", key, self.bucket, key)
            return key
        except ClientError as exc:
            logger.error("S3 upload failed for %s: %s", key, exc)
            raise

    def upload_bytes(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        """Upload raw bytes to S3."""
        return self.upload_file(BytesIO(data), key, content_type)

    # ── Download ─────────────────────────────────────────
    def download_file(self, key: str) -> bytes:
        """Download a file from S3 and return its bytes."""
        try:
            buf = BytesIO()
            self._client.download_fileobj(self.bucket, key, buf)
            buf.seek(0)
            return buf.read()
        except ClientError as exc:
            logger.error("S3 download failed for %s: %s", key, exc)
            raise

    # ── Delete ───────────────────────────────────────────
    def delete_file(self, key: str) -> None:
        """Delete a file from S3."""
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("Deleted s3://%s/%s", self.bucket, key)
        except ClientError as exc:
            logger.error("S3 delete failed for %s: %s", key, exc)
            raise

    # ── Pre-signed URL ───────────────────────────────────
    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a temporary download URL."""
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as exc:
            logger.error("Presigned URL generation failed for %s: %s", key, exc)
            raise

    # ── List ─────────────────────────────────────────────
    def list_files(self, prefix: str = "") -> list[str]:
        """List all object keys under a prefix."""
        try:
            resp = self._client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj["Key"] for obj in resp.get("Contents", [])]
        except ClientError as exc:
            logger.error("S3 list failed for prefix %s: %s", prefix, exc)
            raise
