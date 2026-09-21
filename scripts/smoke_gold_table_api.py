#!/usr/bin/env python3
"""Smoke operacional de tabelas Gold via API local.

Requer a API já iniciada. Não faz parte da suíte pytest.
Uso: python scripts/smoke_gold_table_api.py
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:8000"

CHECKS: list[dict[str, Any]] = [
    {
        "base_name": "tabela_resumo",
        "params": {"scope": "br", "ano": 2026, "mes": 1, "limit": 10},
    },
    {
        "base_name": "tabela_municipio",
        "params": {"scope": "br", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"},
    },
    {
        "base_name": "tabela_municipio",
        "params": {"scope": "pr", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"},
    },
    {
        "base_name": "tabela_municipio",
        "params": {"scope": "rmc", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"},
    },
    {
        "base_name": "tabela_setor",
        "params": {"scope": "br", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"},
    },
    {
        "base_name": "tabela_setor",
        "params": {"scope": "pr", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"},
    },
    {
        "base_name": "tabela_setor",
        "params": {"scope": "rmc", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"},
    },
]


def fetch_json(url: str, params: dict[str, Any], timeout: float) -> tuple[int, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke de tabelas Gold (API já iniciada).")
    parser.add_argument("--api-base", default=DEFAULT_BASE_URL, help="Base URL da API local")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    base = args.api_base.rstrip("/")

    print("=" * 100)
    print("SMOKE — CONSULTA DE TABELAS GOLD PELA API")
    print("=" * 100)

    errors: list[tuple[str, dict[str, Any], str]] = []

    for check in CHECKS:
        base_name = str(check["base_name"])
        params = dict(check["params"])
        url = f"{base}/api/gold/v1/table/{base_name}"
        print("\n" + "-" * 100)
        print(f"GET {url}")
        print(f"params: {params}")

        try:
            status, data = fetch_json(url, params, args.timeout)
        except urllib.error.URLError as exc:
            errors.append((base_name, params, f"erro de conexão: {exc}"))
            print(f"ERRO: {exc}")
            print("A API precisa estar ativa (ex.: uvicorn app.main:app --host 127.0.0.1 --port 8000).")
            continue
        except json.JSONDecodeError as exc:
            errors.append((base_name, params, f"JSON inválido: {exc}"))
            print(f"ERRO: JSON inválido: {exc}")
            continue

        print(f"status_code: {status}")
        if status != 200:
            errors.append((base_name, params, f"status_code {status}"))
            print(str(data)[:1500])
            continue

        print(f"chaves: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        if not isinstance(data, dict):
            continue

        rows = None
        for key in ("items", "rows", "data", "records"):
            if key in data and isinstance(data[key], list):
                rows = data[key]
                print(f"lista detectada em '{key}': {len(rows)} linhas")
                break

        if rows:
            print("primeira linha:")
            print(rows[0])
        elif rows == []:
            errors.append((base_name, params, "retornou lista vazia"))
            print("ERRO: lista vazia")
        else:
            print("Não encontrei lista padrão de registros; resposta parcial:")
            print(str(data)[:1000])

    print("\n" + "=" * 100)
    print("RESUMO")
    print("=" * 100)
    print(f"Consultas avaliadas: {len(CHECKS)}")
    print(f"Erros encontrados: {len(errors)}")
    if errors:
        print("\nERROS")
        print("-" * 100)
        for base_name, params, msg in errors:
            print(f"[ERRO] {base_name} {params} -> {msg}")
        return 1

    print("\nNenhum erro encontrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
