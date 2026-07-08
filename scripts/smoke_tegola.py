#!/usr/bin/env python3
"""Smoke test não destrutivo do Tegola (capabilities + tiles PBF).

Usa apenas a biblioteca padrão do Python. Não altera dados, API Gold ou frontend.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urljoin, urlparse


EXPECTED_MAPS = (
    "municipios_pr",
    "municipios_rmc",
    "ufs_brasil",
    "ictt_municipios_pr",
)

# Centróides aproximados para tiles de teste (WGS84).
TILE_TARGETS: dict[str, tuple[float, float, int]] = {
    "municipios_pr": (-25.43, -49.27, 6),
    "municipios_rmc": (-25.43, -49.27, 6),
    "ictt_municipios_pr": (-25.43, -49.27, 6),
    "ufs_brasil": (-15.78, -47.93, 4),
}


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return x, y


def _request(
    url: str,
    *,
    timeout: float = 30.0,
) -> tuple[int | None, bytes, str | None]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", None) or resp.getcode())
            return status, resp.read(), None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read()
        except Exception:
            body = b""
        return int(exc.code), body, str(exc.reason or exc)
    except urllib.error.URLError as exc:
        return None, b"", str(exc.reason if hasattr(exc, "reason") else exc)
    except TimeoutError:
        return None, b"", "timeout"
    except OSError as exc:
        return None, b"", str(exc)


def _tile_url_candidates(base: str, map_name: str, z: int, x: int, y: int) -> list[str]:
    root = base.rstrip("/") + "/"
    return [
        urljoin(root, f"maps/{map_name}/{z}/{x}/{y}.pbf"),
        urljoin(root, f"maps/{map_name}/{z}/{x}/{y}.vector.pbf"),
        urljoin(root, f"maps/{map_name}/{z}/{x}/{y}.mvt"),
    ]


def _extract_map_tiles(capabilities: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for entry in capabilities.get("maps", []):
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        tiles = entry.get("tiles")
        if isinstance(tiles, list):
            out[name] = [str(t) for t in tiles if isinstance(t, str)]
    return out


def _substitute_tile_template(template: str, z: int, x: int, y: int) -> str:
    return (
        template.replace("{z}", str(z))
        .replace("{x}", str(x))
        .replace("{y}", str(y))
        .replace("{Z}", str(z))
        .replace("{X}", str(x))
        .replace("{Y}", str(y))
    )


class SmokeRunner:
    def __init__(self, *, fail_on_empty: bool) -> None:
        self.fail_on_empty = fail_on_empty
        self.ok = 0
        self.warn = 0
        self.fail = 0

    def record(self, level: str, name: str, detail: str) -> None:
        print(f"[{level}] {name} - {detail}")
        if level == "OK":
            self.ok += 1
        elif level == "WARN":
            self.warn += 1
        else:
            self.fail += 1

    def check_capabilities(self, base: str) -> dict[str, Any] | None:
        url = urljoin(base.rstrip("/") + "/", "capabilities")
        status, body, err = _request(url)
        if status is None:
            self.record("FAIL", "capabilities", err or "indisponível")
            return None
        if status != 200:
            self.record("FAIL", "capabilities", f"HTTP {status}")
            return None
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.record("FAIL", "capabilities", f"JSON inválido: {exc}")
            return None
        if not isinstance(payload, dict):
            self.record("FAIL", "capabilities", "payload não é objeto JSON")
            return None
        maps = payload.get("maps")
        map_names = [m.get("name") for m in maps if isinstance(m, dict)] if isinstance(maps, list) else []
        self.record("OK", "capabilities", f"HTTP 200 | maps={map_names}")
        return payload

    def check_tile(self, base: str, map_name: str, capabilities: dict[str, Any] | None) -> None:
        lat, lon, zoom = TILE_TARGETS.get(map_name, (-15.78, -47.93, 4))
        x, y = lonlat_to_tile(lon, lat, zoom)

        urls: list[str] = []
        if capabilities:
            templates = _extract_map_tiles(capabilities).get(map_name, [])
            for template in templates:
                urls.append(_substitute_tile_template(template, zoom, x, y))
        urls.extend(_tile_url_candidates(base, map_name, zoom, x, y))

        seen: set[str] = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        last_detail = "nenhuma URL testada"
        for url in unique_urls:
            status, body, err = _request(url)
            if status is None:
                last_detail = f"{url} | {err}"
                continue
            if status == 204:
                last_detail = f"{url} | HTTP 204 (vazio)"
                continue
            if status != 200:
                last_detail = f"{url} | HTTP {status}"
                continue
            size = len(body)
            if size == 0:
                last_detail = f"{url} | corpo vazio"
                continue
            self.record(
                "OK",
                f"tile:{map_name}",
                f"HTTP 200 | {size} bytes | z/x/y={zoom}/{x}/{y} | {urlparse(url).path}",
            )
            return

        level = "FAIL" if self.fail_on_empty else "WARN"
        self.record(level, f"tile:{map_name}", last_detail)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke Tegola (capabilities + tiles PBF)")
    parser.add_argument("--tegola-base", default="http://127.0.0.1:8080")
    parser.add_argument(
        "--fail-on-empty",
        action="store_true",
        help="Trata tile vazio/204 como FAIL em vez de WARN",
    )
    args = parser.parse_args()

    runner = SmokeRunner(fail_on_empty=args.fail_on_empty)
    capabilities = runner.check_capabilities(args.tegola_base)
    for map_name in EXPECTED_MAPS:
        runner.check_tile(args.tegola_base, map_name, capabilities)

    print(f"\nResumo: OK={runner.ok} WARN={runner.warn} FAIL={runner.fail}")
    return 1 if runner.fail else 0


if __name__ == "__main__":
    sys.exit(main())
