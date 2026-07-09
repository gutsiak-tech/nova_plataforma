#!/usr/bin/env python3
"""Smoke test não destrutivo do MVP CAGED Dashboard (API Gold + GeoJSON opcional).

Usa apenas a biblioteca padrão do Python. Não altera arquivos, banco ou estado.
Requer a API ativa em --api-base. Frontend opcional (--skip-front ou WARN se offline).

STRICT_NO_FALLBACK (env, opcional): quando true/1/yes/sim, falha se houver fallback
real PostGIS→filesystem durante este smoke (header X-Fallback-Used=true ou aumento
de /api/ops/fallbacks). Não altera a API — trava só no script.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode


TRUE_VALUES = frozenset({"true", "1", "yes", "sim"})
ALLOWED_GOLD_BACKENDS = frozenset({"filesystem", "postgis"})


def is_strict_no_fallback(raw: str | None = None) -> bool:
    value = (raw if raw is not None else os.getenv("STRICT_NO_FALLBACK", "")).strip().lower()
    return value in TRUE_VALUES


def resolve_admin_bearer_token(cli_value: str | None = None) -> str | None:
    """Token admin para /api/ops/fallbacks: CLI tem prioridade sobre env."""
    if cli_value is not None and str(cli_value).strip():
        return str(cli_value).strip()
    env = os.getenv("ADMIN_BEARER_TOKEN", "").strip()
    return env or None


def _ops_auth_headers(admin_bearer_token: str | None) -> dict[str, str]:
    if not admin_bearer_token:
        return {}
    return {"Authorization": f"Bearer {admin_bearer_token}"}


def _request(
    method: str,
    url: str,
    *,
    timeout: float = 30.0,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int | None, Any | None, str | None, dict[str, str]]:
    """Retorna (status, body_json_ou_None, erro_ou_None, headers_lower)."""
    req = urllib.request.Request(url, method=method)
    if extra_headers:
        for key, value in extra_headers.items():
            req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            headers = {k.lower(): v for k, v in resp.headers.items()}
            raw = resp.read()
            if not raw:
                return int(status), None, None, headers
            try:
                return int(status), json.loads(raw.decode("utf-8")), None, headers
            except (UnicodeDecodeError, json.JSONDecodeError):
                return int(status), None, None, headers
    except urllib.error.HTTPError as exc:
        body: Any | None = None
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        try:
            raw = exc.read()
            if raw:
                body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = None
        return int(exc.code), body, str(exc.reason or exc), headers
    except urllib.error.URLError as exc:
        return None, None, str(exc.reason if hasattr(exc, "reason") else exc), {}
    except TimeoutError:
        return None, None, "timeout", {}
    except OSError as exc:
        return None, None, str(exc), {}


def fetch_ops_fallbacks_total(
    api_base: str,
    *,
    admin_bearer_token: str | None = None,
) -> tuple[int | None, str | None]:
    """Retorna (total_fallbacks, erro). total=None se indisponível."""
    status, body, err, _headers = _request(
        "GET",
        f"{api_base.rstrip('/')}/api/ops/fallbacks",
        extra_headers=_ops_auth_headers(admin_bearer_token) or None,
    )
    if status is None:
        return None, err or "indisponível"
    if status >= 400 or not isinstance(body, dict):
        return None, f"HTTP {status}"
    try:
        return int(body.get("total_fallbacks", 0)), None
    except (TypeError, ValueError):
        return None, "total_fallbacks inválido"


def _format_gold_headers(headers: dict[str, str]) -> str:
    parts: list[str] = []
    for key in ("x-gold-backend", "x-data-source", "x-fallback-used"):
        if key in headers:
            parts.append(f"{key}={headers[key]}")
    return " | ".join(parts) if parts else ""


class SmokeRunner:
    def __init__(
        self,
        *,
        strict_no_fallback: bool = False,
        expect_gold_backend: str | None = None,
        admin_bearer_token: str | None = None,
    ) -> None:
        self.ok = 0
        self.warn = 0
        self.fail = 0
        self.strict_no_fallback = strict_no_fallback
        self.expect_gold_backend = expect_gold_backend
        self.admin_bearer_token = admin_bearer_token
        self.initial_fallbacks: int | None = None
        self.strict_violations: list[str] = []
        self.backend_violations: list[str] = []

    def _record(self, level: str, name: str, detail: str) -> None:
        print(f"[{level}] {name} - {detail}")
        if level == "OK":
            self.ok += 1
        elif level == "WARN":
            self.warn += 1
        else:
            self.fail += 1

    def note_strict_violation(
        self,
        *,
        endpoint: str,
        source: str | None,
        fallback_header: str | None,
        total_inicial: int | None,
        total_final: int | None,
        detail: str,
    ) -> None:
        msg = (
            f"STRICT_NO_FALLBACK violation | endpoint={endpoint} | "
            f"source={source} | fallback={fallback_header} | "
            f"total_inicial={total_inicial} | total_final={total_final} | {detail}"
        )
        self.strict_violations.append(msg)
        self._record("FAIL", "STRICT_NO_FALLBACK", msg)

    def note_backend_violation(self, *, endpoint: str, expected: str, actual: str) -> None:
        msg = (
            f"EXPECTED_BACKEND violation: endpoint={endpoint} | "
            f"expected={expected} | actual={actual}"
        )
        self.backend_violations.append(msg)
        self._record("FAIL", "EXPECTED_BACKEND", msg)

    def check_api_get(
        self,
        name: str,
        url: str,
        *,
        expect_json: bool = True,
        show_gold_headers: bool = False,
        enforce_strict_fallback: bool = False,
    ) -> None:
        status, body, err, headers = _request("GET", url)
        if status is None:
            self._record("FAIL", name, f"API indisponível: {err} ({url})")
            return
        if status >= 400:
            self._record("FAIL", name, f"HTTP {status} ({url})")
            return
        if expect_json and body is None:
            self._record("FAIL", name, f"HTTP {status} sem JSON válido ({url})")
            return
        detail = f"HTTP {status}"
        if show_gold_headers:
            hdr = _format_gold_headers(headers)
            if hdr:
                detail = f"{detail} | {hdr}"
        self._record("OK", name, detail)

        if self.expect_gold_backend and show_gold_headers:
            actual = headers.get("x-gold-backend", "").strip().lower()
            if actual != self.expect_gold_backend:
                self.note_backend_violation(
                    endpoint=name,
                    expected=self.expect_gold_backend,
                    actual=actual or "(ausente)",
                )

        if (
            self.strict_no_fallback
            and enforce_strict_fallback
            and headers.get("x-fallback-used", "").strip().lower() == "true"
        ):
            self.note_strict_violation(
                endpoint=name,
                source=headers.get("x-data-source"),
                fallback_header=headers.get("x-fallback-used"),
                total_inicial=self.initial_fallbacks,
                total_final=None,
                detail="X-Fallback-Used=true na resposta",
            )

    def check_front_head(self, name: str, url: str) -> None:
        status, _body, err, _headers = _request("HEAD", url, timeout=10.0)
        if status is None:
            self._record("WARN", name, f"frontend/geo indisponível: {err}")
            return
        if status >= 400:
            status_get, _, err_get, _ = _request("GET", url, timeout=10.0)
            if status_get is None:
                self._record("WARN", name, f"HEAD HTTP {status}; GET falhou: {err_get}")
                return
            if status_get >= 400:
                self._record("WARN", name, f"HTTP {status_get} em {url}")
                return
            self._record("OK", name, f"HTTP {status_get} (via GET)")
            return
        self._record("OK", name, f"HTTP {status}")

    def check_ops_fallbacks(self, url: str) -> int | None:
        status, body, err, _headers = _request(
            "GET",
            url,
            extra_headers=_ops_auth_headers(self.admin_bearer_token) or None,
        )
        if status is None:
            self._record("FAIL", "ops/fallbacks", f"API indisponível: {err} ({url})")
            return None
        if status in (401, 403, 404) and not self.admin_bearer_token:
            self._record(
                "WARN",
                "ops/fallbacks",
                f"HTTP {status} — endpoint protegido em produção; "
                "forneça --admin-bearer-token ou ADMIN_BEARER_TOKEN "
                "(não é falha PostGIS)",
            )
            return None
        if status >= 400:
            self._record("FAIL", "ops/fallbacks", f"HTTP {status} ({url})")
            return None
        if not isinstance(body, dict):
            self._record("FAIL", "ops/fallbacks", f"HTTP {status} sem JSON de objeto ({url})")
            return None
        total = body.get("total_fallbacks", "?")
        self._record("OK", "ops/fallbacks", f"HTTP {status} | total_fallbacks={total}")
        try:
            return int(total)
        except (TypeError, ValueError):
            return None

    def summary_exit(self) -> int:
        print("")
        print(f"OK={self.ok} WARN={self.warn} FAIL={self.fail}")
        return 0 if self.fail == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Smoke não destrutivo do MVP (API Gold + GeoJSON opcional)."
    )
    p.add_argument("--api-base", default="http://127.0.0.1:8000")
    p.add_argument("--front-base", default="http://localhost:5173")
    p.add_argument("--ano", type=int, default=2026)
    p.add_argument("--mes", type=int, default=4)
    p.add_argument(
        "--skip-front",
        action="store_true",
        help="Não testa assets GeoJSON do frontend.",
    )
    p.add_argument(
        "--expect-gold-backend",
        choices=sorted(ALLOWED_GOLD_BACKENDS),
        default=None,
        help="Falha se X-Gold-Backend diferir do backend esperado nos endpoints Gold/ICT migrados.",
    )
    p.add_argument(
        "--admin-bearer-token",
        default=None,
        help="Bearer para GET /api/ops/fallbacks em produção. Padrão: ADMIN_BEARER_TOKEN.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    api = args.api_base.rstrip("/")
    front = args.front_base.rstrip("/")
    ano = args.ano
    mes = args.mes
    q = urlencode({"ano": ano, "mes": mes})
    strict = is_strict_no_fallback()
    expect_backend = args.expect_gold_backend
    admin_token = resolve_admin_bearer_token(args.admin_bearer_token)

    runner = SmokeRunner(
        strict_no_fallback=strict,
        expect_gold_backend=expect_backend,
        admin_bearer_token=admin_token,
    )
    print(
        f"Smoke platform | api={api} | competencia={ano}-{mes:02d} | "
        f"STRICT_NO_FALLBACK={'true' if strict else 'false'} | "
        f"EXPECT_GOLD_BACKEND={expect_backend or '(nao verificado)'} | "
        f"ADMIN_BEARER={'configurado' if admin_token else 'nao configurado'}"
    )
    print("")

    # Baseline do contador (fallback histórico não conta; só aumento durante o smoke).
    if strict:
        initial, err = fetch_ops_fallbacks_total(api, admin_bearer_token=admin_token)
        if initial is None:
            runner._record(
                "FAIL",
                "STRICT_NO_FALLBACK",
                f"não foi possível ler total_fallbacks inicial: {err}",
            )
        else:
            runner.initial_fallbacks = initial
            print(f"[INFO] fallbacks_inicial={initial}")
            print("")

    runner.check_api_get("health", f"{api}/health")
    runner.check_api_get("ready", f"{api}/ready")
    runner.check_api_get("competencias", f"{api}/api/gold/v1/competencias")

    for scope in ("pr", "rmc", "br"):
        runner.check_api_get(
            f"overview/{scope}",
            f"{api}/api/gold/v1/overview?scope={scope}&{q}",
            show_gold_headers=True,
            enforce_strict_fallback=True,
        )

    runner.check_api_get(
        "table/tabela_municipio?scope=pr",
        f"{api}/api/gold/v1/table/tabela_municipio?scope=pr&{q}&limit=5",
        show_gold_headers=True,
        enforce_strict_fallback=True,
    )
    runner.check_api_get(
        "table/tabela_municipio?scope=rmc",
        f"{api}/api/gold/v1/table/tabela_municipio?scope=rmc&{q}&limit=5",
        show_gold_headers=True,
        enforce_strict_fallback=True,
    )
    runner.check_api_get(
        "table/tabela_uf?scope=br",
        f"{api}/api/gold/v1/table/tabela_uf?scope=br&{q}&limit=5",
        show_gold_headers=True,
        enforce_strict_fallback=True,
    )
    runner.check_api_get(
        "table/tabela_ictt_municipio?scope=pr",
        f"{api}/api/gold/v1/table/tabela_ictt_municipio?scope=pr&{q}&limit=5",
        show_gold_headers=True,
        enforce_strict_fallback=True,
    )
    runner.check_api_get(
        "ict/report-context?scope=pr",
        f"{api}/api/ict/v1/report-context?scope=pr&{q}",
        show_gold_headers=True,
        enforce_strict_fallback=True,
    )

    final_total = runner.check_ops_fallbacks(f"{api}/api/ops/fallbacks")

    if strict and runner.initial_fallbacks is not None and final_total is not None:
        if final_total > runner.initial_fallbacks:
            runner.note_strict_violation(
                endpoint="ops/fallbacks",
                source=None,
                fallback_header=None,
                total_inicial=runner.initial_fallbacks,
                total_final=final_total,
                detail="total_fallbacks aumentou durante o smoke",
            )
        else:
            print(
                f"[INFO] fallbacks_final={final_total} "
                f"(delta={final_total - runner.initial_fallbacks})"
            )

    if not args.skip_front:
        print("")
        print(f"Frontend GeoJSON | front={front}")
        for name, path in (
            ("geo/ufs.geojson", "/geo/ufs.geojson"),
            ("geo/municipios_pr.geojson", "/geo/municipios_pr.geojson"),
            ("geo/municipios_rmc.geojson", "/geo/municipios_rmc.geojson"),
        ):
            runner.check_front_head(name, f"{front}{path}")

    return runner.summary_exit()


if __name__ == "__main__":
    sys.exit(main())
