"""MinIO connection."""

import os
from minio import Minio
from io import BytesIO


class MinioClient:
    """Client để tương tác với MinIO."""

    def __init__(self):
        self._client: Minio | None = None
        self.bucket = os.getenv("MINIO_BUCKET", "documents")

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
                access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                secure=os.getenv("MINIO_SECURE", "false").lower() == "true"
            )
        return self._client

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def list_objects(self, prefix: str = "", recursive: bool = True) -> list:
        self.ensure_bucket()
        return list(self.client.list_objects(self.bucket, prefix=prefix, recursive=recursive))

    def upload(self, content: bytes, object_name: str, content_type: str | None = None) -> None:
        self.ensure_bucket()
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=BytesIO(content),
            length=len(content),
            content_type=content_type or "application/octet-stream"
        )


minio_client = MinioClient()
