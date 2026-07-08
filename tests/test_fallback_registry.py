"""Testes do registry e do endpoint /api/ops/fallbacks."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from app.core import fallback_registry as registry
from app.services.gold_service import GoldMonthRef


@pytest.fixture(autouse=True)
def _clean_registry():
    registry.reset()
    yield
    registry.reset()


def test_registry_starts_empty():
    snap = registry.snapshot()
    assert snap["total_fallbacks"] == 0
    assert snap["by_endpoint"] == {}
    assert snap["by_table"] == {}
    assert snap["by_scope"] == {}
    assert snap["by_reason"] == {}
    assert snap["last_fallback_at"] is None
    assert snap["recent_events"] == []


def test_registry_record_increments_buckets():
    registry.record_fallback(
        endpoint="/api/gold/v1/table",
        table_name="tabela_municipio",
        scope="pr",
        ano=2026,
        mes=4,
        reason="conexao: simulated",
    )
    snap = registry.snapshot()
    assert snap["total_fallbacks"] == 1
    assert snap["by_endpoint"]["/api/gold/v1/table"] == 1
    assert snap["by_table"]["tabela_municipio"] == 1
    assert snap["by_scope"]["pr"] == 1
    assert snap["by_reason"]["conexao: simulated"] == 1
    assert snap["last_fallback_at"] is not None
    assert len(snap["recent_events"]) == 1
    assert snap["recent_events"][0]["ano"] == 2026
    assert snap["recent_events"][0]["mes"] == 4


def test_registry_recent_events_limit():
    for i in range(registry.RECENT_EVENTS_LIMIT + 10):
        registry.record_fallback(
            endpoint="/api/gold/v1/table",
            table_name="tabela_uf",
            scope="br",
            ano=2026,
            mes=1,
            reason=f"reason-{i}",
        )
    snap = registry.snapshot()
    assert snap["total_fallbacks"] == registry.RECENT_EVENTS_LIMIT + 10
    assert len(snap["recent_events"]) == registry.RECENT_EVENTS_LIMIT
    assert snap["recent_events"][0]["reason"] == "reason-10"
    assert snap["recent_events"][-1]["reason"] == f"reason-{registry.RECENT_EVENTS_LIMIT + 9}"


def _reload_client(monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.core.config as config_module
    import app.main as main_module

    importlib.reload(config_module)
    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_ops_fallbacks_endpoint_structure(monkeypatch: pytest.MonkeyPatch):
    client = _reload_client(monkeypatch, GOLD_BACKEND="filesystem")
    response = client.get("/api/ops/fallbacks")
    assert response.status_code == 200
    body = response.json()
    for key in (
        "total_fallbacks",
        "by_endpoint",
        "by_table",
        "by_scope",
        "by_reason",
        "last_fallback_at",
        "recent_events",
    ):
        assert key in body
    assert body["total_fallbacks"] == 0
    assert body["recent_events"] == []


def test_orchestrator_registers_real_fallback(monkeypatch: pytest.MonkeyPatch):
    from app.repositories.gold_postgis_repository import PostgisUnavailableError
    import app.repositories.gold_repository as gold_repo

    monkeypatch.setenv("GOLD_BACKEND", "postgis")
    import app.core.config as config_module

    importlib.reload(config_module)

    def _boom(*_a, **_k):
        raise PostgisUnavailableError("conexao: simulated")

    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.is_table_supported",
        lambda base_name, scope: True,
    )
    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.build_table_payload",
        _boom,
    )

    month = GoldMonthRef(ano=2026, mes=4)
    result = gold_repo.get_table(
        month,
        base_name="tabela_municipio",
        scope="pr",
        limit=5,
        offset=0,
        sort_by=None,
        sort_dir="desc",
    )
    assert result.data_source == "fallback_filesystem"
    assert result.fallback_used is True
    snap = registry.snapshot()
    assert snap["total_fallbacks"] == 1
    assert snap["by_endpoint"]["/api/gold/v1/table"] == 1
    assert snap["by_table"]["tabela_municipio"] == 1
    assert snap["by_scope"]["pr"] == 1


def test_orchestrator_does_not_register_filesystem_mode(monkeypatch: pytest.MonkeyPatch):
    import app.repositories.gold_repository as gold_repo

    monkeypatch.setenv("GOLD_BACKEND", "filesystem")
    import app.core.config as config_module

    importlib.reload(config_module)

    month = GoldMonthRef(ano=2026, mes=4)
    result = gold_repo.get_table(
        month,
        base_name="tabela_municipio",
        scope="pr",
        limit=5,
        offset=0,
        sort_by=None,
        sort_dir="desc",
    )
    assert result.data_source == "filesystem"
    assert result.fallback_used is False
    assert registry.snapshot()["total_fallbacks"] == 0


def test_orchestrator_does_not_register_unsupported_expected_filesystem(
    monkeypatch: pytest.MonkeyPatch,
):
    import app.repositories.gold_repository as gold_repo

    monkeypatch.setenv("GOLD_BACKEND", "postgis")
    import app.core.config as config_module

    importlib.reload(config_module)

    month = GoldMonthRef(ano=2026, mes=4)
    # tabela_setor não está em POSTGIS_TABLE_SUPPORT → filesystem esperado
    result = gold_repo.get_table(
        month,
        base_name="tabela_setor",
        scope="pr",
        limit=5,
        offset=0,
        sort_by=None,
        sort_dir="desc",
    )
    assert result.gold_backend == "postgis"
    assert result.data_source == "filesystem"
    assert result.fallback_used is False
    assert registry.snapshot()["total_fallbacks"] == 0
