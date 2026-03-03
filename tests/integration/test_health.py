"""Integration tests for the /health endpoint."""

import pytest


class TestHealthEndpoint:
    async def test_health_returns_200(self, api_client):
        response = await api_client.get("/health")
        assert response.status_code == 200

    async def test_health_returns_ok_status(self, api_client):
        data = (await api_client.get("/health")).json()
        assert data["status"] == "ok"

    async def test_health_includes_version(self, api_client):
        data = (await api_client.get("/health")).json()
        assert "version" in data
        assert data["version"]  # non-empty

    async def test_openapi_docs_reachable(self, api_client):
        response = await api_client.get("/docs")
        assert response.status_code == 200

    async def test_openapi_json_contains_routes(self, api_client):
        data = (await api_client.get("/openapi.json")).json()
        paths = list(data["paths"].keys())
        assert "/api/v1/orders/" in paths
        assert "/api/v1/orders/{order_id}" in paths
        assert "/health" in paths
