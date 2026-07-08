"""Testes unitários de --expect-gold-backend no smoke (sem PostGIS real)."""

from __future__ import annotations

import scripts.smoke_platform as smoke


def test_expect_postgis_passes_when_header_matches(monkeypatch):
    runner = smoke.SmokeRunner(expect_gold_backend="postgis")

    def _fake_request(method, url, *, timeout=30.0):
        return (
            200,
            {"ok": True},
            None,
            {
                "x-gold-backend": "postgis",
                "x-data-source": "postgis",
                "x-fallback-used": "false",
            },
        )

    monkeypatch.setattr(smoke, "_request", _fake_request)
    runner.check_api_get(
        "overview/br",
        "http://example/overview",
        show_gold_headers=True,
        enforce_strict_fallback=True,
    )
    assert runner.ok == 1
    assert runner.fail == 0
    assert runner.backend_violations == []


def test_expect_postgis_fails_when_header_is_filesystem(monkeypatch):
    runner = smoke.SmokeRunner(expect_gold_backend="postgis")

    def _fake_request(method, url, *, timeout=30.0):
        return (
            200,
            {"ok": True},
            None,
            {
                "x-gold-backend": "filesystem",
                "x-data-source": "filesystem",
                "x-fallback-used": "false",
            },
        )

    monkeypatch.setattr(smoke, "_request", _fake_request)
    runner.check_api_get(
        "overview/br",
        "http://example/overview",
        show_gold_headers=True,
        enforce_strict_fallback=True,
    )
    assert runner.ok == 1
    assert runner.fail == 1
    assert len(runner.backend_violations) == 1
    assert "EXPECTED_BACKEND violation" in runner.backend_violations[0]
    assert "expected=postgis" in runner.backend_violations[0]
    assert "actual=filesystem" in runner.backend_violations[0]


def test_expect_filesystem_passes_when_header_matches(monkeypatch):
    runner = smoke.SmokeRunner(expect_gold_backend="filesystem")

    def _fake_request(method, url, *, timeout=30.0):
        return (
            200,
            {"ok": True},
            None,
            {
                "x-gold-backend": "filesystem",
                "x-data-source": "filesystem",
                "x-fallback-used": "false",
            },
        )

    monkeypatch.setattr(smoke, "_request", _fake_request)
    runner.check_api_get(
        "table/tabela_uf?scope=br",
        "http://example/table",
        show_gold_headers=True,
    )
    assert runner.ok == 1
    assert runner.fail == 0


def test_without_expect_backend_ignores_header_mismatch(monkeypatch):
    runner = smoke.SmokeRunner(expect_gold_backend=None)

    def _fake_request(method, url, *, timeout=30.0):
        return (
            200,
            {"ok": True},
            None,
            {
                "x-gold-backend": "filesystem",
                "x-data-source": "filesystem",
                "x-fallback-used": "false",
            },
        )

    monkeypatch.setattr(smoke, "_request", _fake_request)
    runner.check_api_get(
        "overview/br",
        "http://example/overview",
        show_gold_headers=True,
    )
    assert runner.ok == 1
    assert runner.fail == 0
    assert runner.backend_violations == []
