"""HTTP 层集成测试 — TestClient 验证端点可达（此前 66 个测试全是 API 层）"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_root_returns_200():
    """根路径返回演示页（此前是 404）"""
    r = client.get("/")
    assert r.status_code == 200
    assert "客服引擎" in r.text


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
