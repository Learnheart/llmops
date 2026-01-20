"""Tests for MinIOClient."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import io


class TestMinIOClientInit:
    """Tests for MinIOClient initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default settings."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()

            assert client.endpoint == "minio:9000"
            assert client.access_key == "admin"
            assert client.secret_key == "secret"
            assert client.secure is False

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="default:9000",
                minio_access_key="default",
                minio_secret_key="default",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient(
                endpoint="custom:9000",
                access_key="custom_key",
                secret_key="custom_secret",
                secure=True,
            )

            assert client.endpoint == "custom:9000"
            assert client.access_key == "custom_key"
            assert client.secret_key == "custom_secret"
            assert client.secure is True

    def test_client_lazy_loading(self):
        """Test that MinIO client is lazy loaded."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()

            # _client should be None before first access
            assert client._client is None


class TestMinIOClientParsePath:
    """Tests for _parse_path method."""

    @pytest.fixture
    def client(self):
        """Create MinIO client instance."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient
            return MinIOClient()

    def test_parse_minio_url(self, client):
        """Test parsing minio:// URL."""
        bucket, object_name = client._parse_path("minio://my-bucket/path/to/file.pdf")

        assert bucket == "my-bucket"
        assert object_name == "path/to/file.pdf"

    def test_parse_minio_url_simple(self, client):
        """Test parsing simple minio:// URL."""
        bucket, object_name = client._parse_path("minio://docs/file.txt")

        assert bucket == "docs"
        assert object_name == "file.txt"

    def test_parse_regular_path(self, client):
        """Test parsing regular path."""
        bucket, object_name = client._parse_path("bucket/path/to/file.pdf")

        assert bucket == "bucket"
        assert object_name == "path/to/file.pdf"

    def test_parse_path_with_leading_slash(self, client):
        """Test parsing path with leading slash."""
        bucket, object_name = client._parse_path("/bucket/path/to/file.pdf")

        assert bucket == "bucket"
        assert object_name == "path/to/file.pdf"

    def test_parse_bucket_only(self, client):
        """Test parsing bucket-only path."""
        bucket, object_name = client._parse_path("bucket")

        assert bucket == "bucket"
        assert object_name == ""

    def test_parse_bucket_only_with_slash(self, client):
        """Test parsing bucket-only path with leading slash."""
        bucket, object_name = client._parse_path("/bucket")

        assert bucket == "bucket"
        assert object_name == ""

    def test_parse_deep_nested_path(self, client):
        """Test parsing deeply nested path."""
        bucket, object_name = client._parse_path(
            "minio://docs/users/123/uploads/2024/01/document.pdf"
        )

        assert bucket == "docs"
        assert object_name == "users/123/uploads/2024/01/document.pdf"

    def test_parse_path_with_special_characters(self, client):
        """Test parsing path with special characters in filename."""
        bucket, object_name = client._parse_path(
            "minio://docs/file with spaces.pdf"
        )

        assert bucket == "docs"
        assert object_name == "file with spaces.pdf"


class TestMinIOClientDownload:
    """Tests for download method."""

    @pytest.fixture
    def mock_minio(self):
        """Create mock Minio client."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_download_success(self, mock_minio):
        """Test successful download."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()

            # Mock response
            mock_response = MagicMock()
            mock_response.read.return_value = b"file content"
            mock_minio.get_object.return_value = mock_response
            client._client = mock_minio

            result = await client.download("minio://bucket/file.txt")

            assert result == b"file content"
            mock_minio.get_object.assert_called_once_with("bucket", "file.txt")
            mock_response.close.assert_called_once()
            mock_response.release_conn.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_with_regular_path(self, mock_minio):
        """Test download with regular path format."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()

            mock_response = MagicMock()
            mock_response.read.return_value = b"content"
            mock_minio.get_object.return_value = mock_response
            client._client = mock_minio

            result = await client.download("docs/path/to/file.pdf")

            mock_minio.get_object.assert_called_once_with("docs", "path/to/file.pdf")


class TestMinIOClientUpload:
    """Tests for upload method."""

    @pytest.fixture
    def mock_minio(self):
        """Create mock Minio client."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_upload_success(self, mock_minio):
        """Test successful upload."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()
            mock_minio.bucket_exists.return_value = True
            client._client = mock_minio

            result = await client.upload(
                content=b"test content",
                bucket="my-bucket",
                object_name="path/file.txt",
                content_type="text/plain",
            )

            assert result == "minio://my-bucket/path/file.txt"
            mock_minio.put_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_creates_bucket_if_not_exists(self, mock_minio):
        """Test that upload creates bucket if it doesn't exist."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()
            mock_minio.bucket_exists.return_value = False
            client._client = mock_minio

            await client.upload(
                content=b"test",
                bucket="new-bucket",
                object_name="file.txt",
            )

            mock_minio.make_bucket.assert_called_once_with("new-bucket")

    @pytest.mark.asyncio
    async def test_upload_with_default_content_type(self, mock_minio):
        """Test upload with default content type."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()
            mock_minio.bucket_exists.return_value = True
            client._client = mock_minio

            await client.upload(
                content=b"binary data",
                bucket="bucket",
                object_name="file.bin",
            )

            call_args = mock_minio.put_object.call_args
            assert call_args.kwargs["content_type"] == "application/octet-stream"


class TestMinIOClientDelete:
    """Tests for delete method."""

    @pytest.fixture
    def mock_minio(self):
        """Create mock Minio client."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_delete_success(self, mock_minio):
        """Test successful delete."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()
            client._client = mock_minio

            result = await client.delete("minio://bucket/file.txt")

            assert result is True
            mock_minio.remove_object.assert_called_once_with("bucket", "file.txt")


class TestMinIOClientExists:
    """Tests for exists method."""

    @pytest.fixture
    def mock_minio(self):
        """Create mock Minio client."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_exists_returns_true(self, mock_minio):
        """Test exists returns True when file exists."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()
            mock_minio.stat_object.return_value = MagicMock()
            client._client = mock_minio

            result = await client.exists("minio://bucket/file.txt")

            assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self, mock_minio):
        """Test exists returns False when file doesn't exist."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()
            mock_minio.stat_object.side_effect = Exception("Not found")
            client._client = mock_minio

            result = await client.exists("minio://bucket/nonexistent.txt")

            assert result is False


class TestMinIOClientListObjects:
    """Tests for list_objects method."""

    @pytest.fixture
    def mock_minio(self):
        """Create mock Minio client."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_list_objects_success(self, mock_minio):
        """Test listing objects."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()

            # Create mock objects
            obj1 = MagicMock()
            obj1.object_name = "file1.txt"
            obj1.size = 100
            obj1.last_modified = "2024-01-01"
            obj1.etag = "abc123"

            obj2 = MagicMock()
            obj2.object_name = "file2.txt"
            obj2.size = 200
            obj2.last_modified = "2024-01-02"
            obj2.etag = "def456"

            mock_minio.list_objects.return_value = [obj1, obj2]
            client._client = mock_minio

            result = await client.list_objects("bucket", prefix="", recursive=True)

            assert len(result) == 2
            assert result[0]["name"] == "file1.txt"
            assert result[0]["size"] == 100
            assert result[1]["name"] == "file2.txt"
            assert result[1]["size"] == 200

    @pytest.mark.asyncio
    async def test_list_objects_with_prefix(self, mock_minio):
        """Test listing objects with prefix."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()
            mock_minio.list_objects.return_value = []
            client._client = mock_minio

            await client.list_objects("bucket", prefix="docs/", recursive=False)

            mock_minio.list_objects.assert_called_once_with(
                "bucket",
                prefix="docs/",
                recursive=False,
            )

    @pytest.mark.asyncio
    async def test_list_objects_empty(self, mock_minio):
        """Test listing empty bucket."""
        with patch("app.clients.minio_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="secret",
                minio_secure=False,
            )

            from app.clients.minio_client import MinIOClient

            client = MinIOClient()
            mock_minio.list_objects.return_value = []
            client._client = mock_minio

            result = await client.list_objects("empty-bucket")

            assert result == []
