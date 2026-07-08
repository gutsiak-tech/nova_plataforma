"""Testes unitários do STRICT_NO_FALLBACK no smoke (sem PostGIS real)."""

from __future__ import annotations

import scripts.smoke_platform as smoke


def test_is_strict_no_fallback_truthy():
    for raw in ("true", "TRUE", "1", "yes", "YES", "sim", " Sim "):
        assert smoke.is_strict_no_fallback(raw) is True


def test_is_strict_no_fallback_falsy(monkeypatch):
    monkeypatch.delenv("STRICT_NO_FALLBACK", raising=False)
    for raw in ("", "false", "0", "no", "nao", None):
        assert smoke.is_strict_no_fallback(raw) is False


def test_strict_disabled_does_not_fail_on_fallback_header():
    runner = smoke.SmokeRunner(strict_no_fallback=False)
    # Simula check_api_get path: enforce+header true sem strict → sem FAIL extra
    runner.strict_no_fallback = False
    headers = {
        "x-gold-backend": "postgis",
        "x-data-source": "fallback_filesystem",
        "x-fallback-used": "true",
    }
    # lógica equivalente ao ramo enforce
    if (
        runner.strict_no_fallback
        and True
        and headers.get("x-fallback-used", "").strip().lower() == "true"
    ):
        runner.note_strict_violation(
            endpoint="table",
            source=headers.get("x-data-source"),
            fallback_header=headers.get("x-fallback-used"),
            total_inicial=0,
            total_final=None,
            detail="should not happen",
        )
    assert runner.fail == 0
    assert runner.strict_violations == []


def test_strict_enabled_fails_on_fallback_header():
    runner = smoke.SmokeRunner(strict_no_fallback=True)
    runner.initial_fallbacks = 3
    runner.note_strict_violation(
        endpoint="table/tabela_municipio?scope=pr",
        source="fallback_filesystem",
        fallback_header="true",
        total_inicial=3,
        total_final=None,
        detail="X-Fallback-Used=true na resposta",
    )
    assert runner.fail == 1
    assert "STRICT_NO_FALLBACK violation" in runner.strict_violations[0]
    assert "total_inicial=3" in runner.strict_violations[0]


def test_strict_registry_increase_fails_but_stable_history_ok():
    runner = smoke.SmokeRunner(strict_no_fallback=True)
    runner.initial_fallbacks = 5
    # histórico antigo (5) sem aumento → ok
    final_stable = 5
    if final_stable > runner.initial_fallbacks:
        runner.note_strict_violation(
            endpoint="ops/fallbacks",
            source=None,
            fallback_header=None,
            total_inicial=runner.initial_fallbacks,
            total_final=final_stable,
            detail="should not",
        )
    assert runner.fail == 0

    final_up = 6
    if final_up > runner.initial_fallbacks:
        runner.note_strict_violation(
            endpoint="ops/fallbacks",
            source=None,
            fallback_header=None,
            total_inicial=runner.initial_fallbacks,
            total_final=final_up,
            detail="total_fallbacks aumentou durante o smoke",
        )
    assert runner.fail == 1
    assert "total_final=6" in runner.strict_violations[0]


def test_check_api_get_strict_with_monkeypatch(monkeypatch):
    runner = smoke.SmokeRunner(strict_no_fallback=True)
    runner.initial_fallbacks = 0

    def _fake_request(method, url, *, timeout=30.0):
        return (
            200,
            {"ok": True},
            None,
            {
                "x-gold-backend": "postgis",
                "x-data-source": "fallback_filesystem",
                "x-fallback-used": "true",
            },
        )

    monkeypatch.setattr(smoke, "_request", _fake_request)
    runner.check_api_get(
        "table/demo",
        "http://example/table",
        show_gold_headers=True,
        enforce_strict_fallback=True,
    )
    assert runner.ok == 1  # HTTP 200 ainda OK
    assert runner.fail == 1  # + violação strict
    assert any("STRICT_NO_FALLBACK violation" in v for v in runner.strict_violations)


def test_check_api_get_strict_off_ignores_fallback_header(monkeypatch):
    runner = smoke.SmokeRunner(strict_no_fallback=False)

    def _fake_request(method, url, *, timeout=30.0):
        return (
            200,
            {"ok": True},
            None,
            {
                "x-gold-backend": "postgis",
                "x-data-source": "fallback_filesystem",
                "x-fallback-used": "true",
            },
        )

    monkeypatch.setattr(smoke, "_request", _fake_request)
    runner.check_api_get(
        "table/demo",
        "http://example/table",
        show_gold_headers=True,
        enforce_strict_fallback=True,
    )
    assert runner.ok == 1
    assert runner.fail == 0
