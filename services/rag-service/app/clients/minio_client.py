"""MinIO client for document storage."""

import io
from typing import Optional
from urllib.parse import urlparse

from app.config import get_settings

settings = get_settings()


class MinIOClient:
    """Client for MinIO object storage operations."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
    ):
        """Initialize MinIO client.

        Args:
            endpoint: MinIO endpoint
            access_key: Access key
            secret_key: Secret key
            secure: Use HTTPS
        """
        self.endpoint = endpoint or settings.minio_endpoint
        self.access_key = access_key or settings.minio_access_key
        self.secret_key = secret_key or settings.minio_secret_key
        self.secure = secure if secure is not None else settings.minio_secure
        self._client = None

    @property
    def client(self):
        """Lazy-load MinIO client."""
        if self._client is None:
            try:
                from minio import Minio
            except ImportError:
                raise ImportError("minio is required. Install with: pip install minio")

            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )

        return self._client

    def _parse_path(self, path: str) -> tuple[str, str]:
        """Parse storage path into bucket and object name.

        Supports formats:
        - minio://bucket/path/to/file
        - bucket/path/to/file
        - /bucket/path/to/file

        Args:
            path: Storage path

        Returns:
            Tuple of (bucket, object_name)
        """
        # Handle minio:// URLs
        if path.startswith("minio://"):
            parsed = urlparse(path)
            bucket = parsed.netloc
            object_name = parsed.path.lstrip("/")
            return bucket, object_name

        # Handle regular paths
        path = path.lstrip("/")
        parts = path.split("/", 1)

        if len(parts) == 1:
            # Only bucket name, no object
            return parts[0], ""

        return parts[0], parts[1]

    async def download(self, path: str) -> bytes:
        """Download file content from MinIO.

        Args:
            path: Storage path (minio://bucket/path or bucket/path)

        Returns:
            File content as bytes
        """
        bucket, object_name = self._parse_path(path)

        response = self.client.get_object(bucket, object_name)
        try:
            content = response.read()
        finally:
            response.close()
            response.release_conn()

        return content

    async def upload(
        self,
        content: bytes,
        bucket: str,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload content to MinIO.

        Args:
            content: File content
            bucket: Bucket name
            object_name: Object name/path
            content_type: MIME type

        Returns:
            Storage path
        """
        # Ensure bucket exists
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

        # Upload
        data = io.BytesIO(content)
        self.client.put_object(
            bucket,
            object_name,
            data,
            length=len(content),
            content_type=content_type,
        )

        return f"minio://{bucket}/{object_name}"

    async def delete(self, path: str) -> bool:
        """Delete file from MinIO.

        Args:
            path: Storage path

        Returns:
            True if deleted
        """
        bucket, object_name = self._parse_path(path)
        self.client.remove_object(bucket, object_name)
        return True

    async def exists(self, path: str) -> bool:
        """Check if file exists.

        Args:
            path: Storage path

        Returns:
            True if exists
        """
        bucket, object_name = self._parse_path(path)

        try:
            self.client.stat_object(bucket, object_name)
            return True
        except Exception:
            return False

    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        recursive: bool = True,
    ) -> list[dict]:
        """List objects in bucket.

        Args:
            bucket: Bucket name
            prefix: Object prefix
            recursive: List recursively

        Returns:
            List of object metadata
        """
        objects = self.client.list_objects(
            bucket,
            prefix=prefix,
            recursive=recursive,
        )

        return [
            {
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified,
                "etag": obj.etag,
            }
            for obj in objects
        ]
