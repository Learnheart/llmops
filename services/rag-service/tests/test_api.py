"""Tests for API endpoints."""

import pytest


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "rag-service"

    def test_liveness(self, client):
        """Test liveness probe."""
        response = client.get("/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestComponentEndpoints:
    """Tests for component listing endpoints."""

    def test_list_all_components(self, client):
        """Test listing all components."""
        response = client.get("/api/v1/components")
        assert response.status_code == 200
        data = response.json()

        assert "parsers" in data
        assert "chunkers" in data
        assert "embedders" in data
        assert "indexers" in data
        assert "searchers" in data
        assert "optimizers" in data

    def test_list_parsers(self, client):
        """Test listing parsers."""
        response = client.get("/api/v1/components/parsers")
        assert response.status_code == 200
        data = response.json()

        assert data["category"] == "parsers"
        assert data["count"] > 0
        assert len(data["components"]) > 0

    def test_list_invalid_category(self, client):
        """Test listing invalid category."""
        response = client.get("/api/v1/components/invalid")
        assert response.status_code == 404

    def test_get_component_info(self, client):
        """Test getting component info."""
        response = client.get("/api/v1/components/chunkers/recursive")
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "recursive"
        assert data["category"] == "chunkers"
        assert "description" in data
        assert "config_schema" in data


class TestPipelineEndpoints:
    """Tests for pipeline endpoints."""

    def test_validate_ingestion_config(self, client):
        """Test validating ingestion config."""
        response = client.post(
            "/api/v1/pipelines/validate",
            json={
                "pipeline_type": "ingestion",
                "config": {
                    "parser": {"type": "auto"},
                    "chunker": {"type": "recursive"},
                    "embedder": {"type": "openai"},
                    "indexer": {"type": "milvus"},
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_validate_invalid_component(self, client):
        """Test validating config with invalid component."""
        response = client.post(
            "/api/v1/pipelines/validate",
            json={
                "pipeline_type": "ingestion",
                "config": {
                    "parser": {"type": "nonexistent"},
                    "chunker": {"type": "recursive"},
                    "embedder": {"type": "openai"},
                    "indexer": {"type": "milvus"},
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_get_ingestion_template(self, client):
        """Test getting ingestion template."""
        response = client.get("/api/v1/pipelines/templates/ingestion")
        assert response.status_code == 200
        data = response.json()

        assert "parser" in data
        assert "chunker" in data
        assert "embedder" in data
        assert "indexer" in data

    def test_get_retrieval_template(self, client):
        """Test getting retrieval template."""
        response = client.get("/api/v1/pipelines/templates/retrieval")
        assert response.status_code == 200
        data = response.json()

        assert "searcher" in data
        assert "optimizers" in data


class TestIngestionEndpoints:
    """Tests for ingestion API endpoints."""

    def test_ingest_documents_validation_error(self, client):
        """Test ingestion with invalid request."""
        response = client.post(
            "/api/v1/ingest",
            json={
                # Missing required fields
                "documents": [],
            },
        )
        assert response.status_code == 422  # Validation error

    def test_ingest_documents_empty_user_id(self, client):
        """Test ingestion with empty user_id."""
        response = client.post(
            "/api/v1/ingest",
            json={
                "user_id": "",
                "knowledge_base_id": "kb123",
                "documents": [
                    {
                        "storage_path": "minio://docs/test.pdf",
                        "filename": "test.pdf",
                    }
                ],
            },
        )
        assert response.status_code == 422

    def test_ingest_documents_missing_knowledge_base(self, client):
        """Test ingestion with missing knowledge_base_id."""
        response = client.post(
            "/api/v1/ingest",
            json={
                "user_id": "user123",
                "documents": [
                    {
                        "storage_path": "minio://docs/test.pdf",
                        "filename": "test.pdf",
                    }
                ],
            },
        )
        assert response.status_code == 422

    def test_ingest_batch_validation(self, client):
        """Test batch ingestion validation."""
        response = client.post(
            "/api/v1/ingest/batch",
            json={
                "user_id": "",
                "knowledge_base_id": "kb123",
                "documents": [],
            },
        )
        assert response.status_code == 422

    def test_ingest_status_not_found(self, client):
        """Test getting status for non-existent run."""
        response = client.get("/api/v1/ingest/status/non-existent-run-id")
        assert response.status_code == 404


class TestRetrievalEndpoints:
    """Tests for retrieval API endpoints."""

    def test_retrieve_validation_error(self, client):
        """Test retrieval with invalid request."""
        response = client.post(
            "/api/v1/retrieve",
            json={
                # Missing required fields
            },
        )
        assert response.status_code == 422

    def test_retrieve_empty_query(self, client):
        """Test retrieval with empty query."""
        response = client.post(
            "/api/v1/retrieve",
            json={
                "user_id": "user123",
                "knowledge_base_id": "kb123",
                "query": "",
            },
        )
        assert response.status_code == 422

    def test_retrieve_empty_user_id(self, client):
        """Test retrieval with empty user_id."""
        response = client.post(
            "/api/v1/retrieve",
            json={
                "user_id": "",
                "knowledge_base_id": "kb123",
                "query": "test query",
            },
        )
        assert response.status_code == 422

    def test_retrieve_batch_validation(self, client):
        """Test batch retrieval validation."""
        response = client.post(
            "/api/v1/retrieve/batch",
            json={
                "user_id": "",
                "knowledge_base_id": "kb123",
                "queries": [],
            },
        )
        assert response.status_code == 422

    def test_retrieve_batch_empty_queries(self, client):
        """Test batch retrieval with empty queries list."""
        response = client.post(
            "/api/v1/retrieve/batch",
            json={
                "user_id": "user123",
                "knowledge_base_id": "kb123",
                "queries": [],
            },
        )
        assert response.status_code == 422

    def test_retrieve_top_k_validation(self, client):
        """Test retrieval with invalid top_k."""
        response = client.post(
            "/api/v1/retrieve",
            json={
                "user_id": "user123",
                "knowledge_base_id": "kb123",
                "query": "test",
                "top_k": 0,  # Invalid: must be >= 1
            },
        )
        assert response.status_code == 422

    def test_retrieve_top_k_max_validation(self, client):
        """Test retrieval with top_k exceeding max."""
        response = client.post(
            "/api/v1/retrieve",
            json={
                "user_id": "user123",
                "knowledge_base_id": "kb123",
                "query": "test",
                "top_k": 200,  # Invalid: max is 100
            },
        )
        assert response.status_code == 422

    def test_simple_search_validation(self, client):
        """Test simple search endpoint validation."""
        # Missing required query parameters
        response = client.post("/api/v1/retrieve/search")
        assert response.status_code == 422


class TestIngestionEndpointsWithMocks:
    """Tests for ingestion endpoints with mocked services."""

    def test_ingest_request_schema(self, client, ingestion_config):
        """Test ingestion request schema validation."""
        # Valid request structure (will fail at service level, but validates schema)
        request_data = {
            "user_id": "user123",
            "knowledge_base_id": "kb123",
            "documents": [
                {
                    "storage_path": "minio://docs/test.pdf",
                    "filename": "test.pdf",
                    "metadata": {"source": "test"},
                }
            ],
            "config": ingestion_config,
        }

        # This will fail because no actual services are available,
        # but we're testing the schema validation passes
        response = client.post("/api/v1/ingest", json=request_data)

        # Should not be a validation error (422)
        # It may be 500 (service error) or 201 (success with mocks)
        assert response.status_code != 422


class TestRetrievalEndpointsWithMocks:
    """Tests for retrieval endpoints with mocked services."""

    def test_retrieve_request_schema(self, client, retrieval_config):
        """Test retrieval request schema validation."""
        request_data = {
            "user_id": "user123",
            "knowledge_base_id": "kb123",
            "query": "What is machine learning?",
            "config": retrieval_config,
            "top_k": 5,
        }

        response = client.post("/api/v1/retrieve", json=request_data)

        # Should not be a validation error
        assert response.status_code != 422

    def test_batch_retrieve_request_schema(self, client, retrieval_config):
        """Test batch retrieval request schema validation."""
        request_data = {
            "user_id": "user123",
            "knowledge_base_id": "kb123",
            "queries": ["Query 1", "Query 2", "Query 3"],
            "config": retrieval_config,
            "top_k": 5,
        }

        response = client.post("/api/v1/retrieve/batch", json=request_data)

        # Should not be a validation error
        assert response.status_code != 422


class TestPipelineRunEndpoints:
    """Tests for pipeline run listing endpoints."""

    def test_list_pipeline_runs(self, client):
        """Test listing pipeline runs."""
        response = client.get("/api/v1/pipelines/runs")

        # Should return 200 with empty list or actual runs
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert isinstance(data["runs"], list)

    def test_list_pipeline_runs_with_filters(self, client):
        """Test listing pipeline runs with filters."""
        response = client.get(
            "/api/v1/pipelines/runs",
            params={
                "user_id": "user123",
                "pipeline_type": "ingestion",
                "page": 1,
                "page_size": 10,
            },
        )

        assert response.status_code == 200

    def test_list_pipeline_runs_pagination(self, client):
        """Test pipeline runs pagination."""
        response = client.get(
            "/api/v1/pipelines/runs",
            params={
                "page": 1,
                "page_size": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
