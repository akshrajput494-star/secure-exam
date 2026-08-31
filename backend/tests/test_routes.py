import pytest
from httpx import AsyncClient, ASGITransport
import os

# Assuming app is importable from main
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_download_exam_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/exams/123/download")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_list_exams_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/exams")
    assert response.status_code == 401

# Add more comprehensive tests assuming mock dependencies here...
