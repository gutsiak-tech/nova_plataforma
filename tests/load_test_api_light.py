import time
import random
import statistics
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://127.0.0.1:8000"

endpoints = [
    ("/health", {}),
    ("/ready", {}),
    ("/api/gold/v1/competencias", {}),
    ("/api/gold/v1/overview", {}),
    ("/api/gold/v1/table/tabela_resumo", {"scope": "br", "ano": 2026, "mes": 4, "limit": 10}),
    ("/api/gold/v1/table/tabela_municipio", {"scope": "br", "ano": 2026, "mes": 4, "limit": 2000, "sort_by": "saldo"}),
    ("/api/gold/v1/table/tabela_municipio", {"scope": "pr", "ano": 2026, "mes": 4, "limit": 2000, "sort_by": "saldo"}),
    ("/api/gold/v1/table/tabela_municipio", {"scope": "rmc", "ano": 2026, "mes": 4, "limit": 2000, "sort_by": "saldo"}),
    ("/api/gold/v1/table/tabela_setor", {"scope": "br", "ano": 2026, "mes": 4, "limit": 2000, "sort_by": "saldo"}),
]

TOTAL_REQUESTS = 200
MAX_WORKERS = 20

print("=" * 100)
print("TESTE 17 — CARGA LEVE DA API GOLD FILESYSTEM")
print("=" * 100)
print(f"Total de requisições: {TOTAL_REQUESTS}")
print(f"Concorrência: {MAX_WORKERS} workers")

def make_request(i):
    endpoint, params = random.choice(endpoints)
    url = BASE_URL + endpoint

    start = time.perf_counter()

    try:
        response = requests.get(url, params=params, timeout=20)
        elapsed = time.perf_counter() - start

        ok = response.status_code == 200

        return {
            "ok": ok,
            "status_code": response.status_code,
            "endpoint": endpoint,
            "elapsed": elapsed,
            "error": None if ok else response.text[:300],
        }

    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "ok": False,
            "status_code": None,
            "endpoint": endpoint,
            "elapsed": elapsed,
            "error": str(e),
        }

started = time.perf_counter()

results = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(make_request, i) for i in range(TOTAL_REQUESTS)]

    for future in as_completed(futures):
        results.append(future.result())

finished = time.perf_counter()

success = [r for r in results if r["ok"]]
failures = [r for r in results if not r["ok"]]
times = [r["elapsed"] for r in results]

print("\n" + "-" * 100)
print("RESUMO")
print("-" * 100)
print(f"Tempo total do teste: {finished - started:.3f}s")
print(f"Requisições bem-sucedidas: {len(success)}")
print(f"Falhas: {len(failures)}")
print(f"Taxa de sucesso: {len(success) / len(results) * 100:.2f}%")

print("\nTEMPOS DE RESPOSTA")
print("-" * 100)
print(f"média: {statistics.mean(times):.4f}s")
print(f"mediana: {statistics.median(times):.4f}s")
print(f"mínimo: {min(times):.4f}s")
print(f"máximo: {max(times):.4f}s")

if len(times) >= 20:
    sorted_times = sorted(times)
    p95 = sorted_times[int(len(sorted_times) * 0.95) - 1]
    p99 = sorted_times[int(len(sorted_times) * 0.99) - 1]
    print(f"p95: {p95:.4f}s")
    print(f"p99: {p99:.4f}s")

if failures:
    print("\nFALHAS")
    print("-" * 100)
    for failure in failures[:20]:
        print(failure)

print("\nPOR ENDPOINT")
print("-" * 100)

by_endpoint = {}

for r in results:
    by_endpoint.setdefault(r["endpoint"], []).append(r)

for endpoint, rows in sorted(by_endpoint.items()):
    endpoint_times = [r["elapsed"] for r in rows]
    endpoint_failures = [r for r in rows if not r["ok"]]

    print(
        f"{endpoint:45} "
        f"requests={len(rows):3d} "
        f"falhas={len(endpoint_failures):3d} "
        f"media={statistics.mean(endpoint_times):.4f}s "
        f"max={max(endpoint_times):.4f}s"
    )

print("\n" + "=" * 100)
print("FIM DO TESTE 17")
print("=" * 100)
