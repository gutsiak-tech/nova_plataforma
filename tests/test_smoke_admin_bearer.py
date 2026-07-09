"""Testes do Bearer admin em /api/ops/fallbacks no smoke."""

from __future__ import annotations

import scripts.smoke_platform as smoke


def test_resolve_admin_bearer_token_prefers_cli(monkeypatch):
    monkeypatch.setenv("ADMIN_BEARER_TOKEN", "from-env")
    assert smoke.resolve_admin_bearer_token("from-cli") == "from-cli"


def test_resolve_admin_bearer_token_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("ADMIN_BEARER_TOKEN", "from-env")
    assert smoke.resolve_admin_bearer_token(None) == "from-env"
    monkeypatch.delenv("ADMIN_BEARER_TOKEN", raising=False)
    assert smoke.resolve_admin_bearer_token("") is None


def test_check_ops_fallbacks_ok_with_token(monkeypatch):
    runner = smoke.SmokeRunner(admin_bearer_token="secret")

    def _fake_request(method, url, *, timeout=30.0, extra_headers=None):
        assert extra_headers == {"Authorization": "Bearer secret"}
        return (200, {"total_fallbacks": 0}, None, {})

    monkeypatch.setattr(smoke, "_request", _fake_request)
    total = runner.check_ops_fallbacks("http://example/api/ops/fallbacks")
    assert total == 0
    assert runner.ok == 1
    assert runner.fail == 0


def test_check_ops_fallbacks_warns_when_protected_without_token(monkeypatch):
    runner = smoke.SmokeRunner(admin_bearer_token=None)

    def _fake_request(method, url, *, timeout=30.0, extra_headers=None):
        assert extra_headers is None
        return (401, {"detail": "Unauthorized"}, "Unauthorized", {})

    monkeypatch.setattr(smoke, "_request", _fake_request)
    total = runner.check_ops_fallbacks("http://example/api/ops/fallbacks")
    assert total is None
    assert runner.warn == 1
    assert runner.fail == 0


def test_check_ops_fallbacks_fails_with_wrong_token(monkeypatch):
    runner = smoke.SmokeRunner(admin_bearer_token="wrong")

    def _fake_request(method, url, *, timeout=30.0, extra_headers=None):
        return (403, {"detail": "Forbidden"}, "Forbidden", {})

    monkeypatch.setattr(smoke, "_request", _fake_request)
    total = runner.check_ops_fallbacks("http://example/api/ops/fallbacks")
    assert total is None
    assert runner.fail == 1
