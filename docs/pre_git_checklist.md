# Checklist pré-Git

Validação operacional da arquitetura estabilizada antes de inicializar o repositório Git.

**Escopo congelado:** GeoJSON oficial nos mapas; Tegola desativado no frontend; PostGIS como backend analítico com fallback Gold filesystem; `GOLD_BACKEND` controlado por `.env` e `scripts/start_stack.ps1`.

Não altere backend, frontend, mapas, GeoJSON, Tegola, schema/loaders PostGIS, fallback ou contratos JSON nesta etapa — apenas valide.

---

## 1. Build do dashboard

```powershell
cd dashboard
npm run build
```

- [ ] `tsc -b` e `vite build` concluem sem erro
- [ ] Artefatos gerados em `dashboard/dist/`

---

## 2. Testes pytest relevantes

Na raiz do projeto (com `.venv` ativo e `pip install -r requirements.txt`):

```powershell
python -m pytest tests/test_smoke_strict_no_fallback.py tests/test_smoke_expect_gold_backend.py tests/test_gold_backend_flag.py tests/test_data_source_observability.py tests/test_fallback_registry.py tests/test_ict_report_context_api.py -q
```

- [ ] Todos os testes passam (esperado: 39 passed, 1 skipped)
- [ ] `scikit-learn` instalado (`requirements.txt` lista `scikit-learn`)

---

## 3. Paridade Gold × PostGIS (jan–abr/2026)

Exige Postgres/PostGIS com dados carregados:

```powershell
python scripts/validate_postgis_vs_gold.py --ano 2026 --mes 1 --scope all
python scripts/validate_postgis_vs_gold.py --ano 2026 --mes 2 --scope all
python scripts/validate_postgis_vs_gold.py --ano 2026 --mes 3 --scope all
python scripts/validate_postgis_vs_gold.py --ano 2026 --mes 4 --scope all
```

- [ ] Cada competência: `OK=17 WARN=0 FAIL=0`

---

## 4. Smoke filesystem

```powershell
.\scripts\stop_api.ps1
.\scripts\start_stack.ps1 -GoldBackend filesystem
python scripts\smoke_platform.py --expect-gold-backend filesystem --skip-front
```

Headers esperados nos endpoints de dados:

- [ ] `X-Gold-Backend: filesystem`
- [ ] `X-Data-Source: filesystem`
- [ ] `X-Fallback-Used: false`
- [ ] `total_fallbacks=0`
- [ ] `OK=12 WARN=0 FAIL=0`

---

## 5. Smoke PostGIS

```powershell
.\scripts\stop_api.ps1
.\scripts\start_stack.ps1 -GoldBackend postgis
python scripts\smoke_platform.py --expect-gold-backend postgis --skip-front
```

Headers esperados:

- [ ] `X-Gold-Backend: postgis`
- [ ] `X-Data-Source: postgis`
- [ ] `X-Fallback-Used: false`
- [ ] `total_fallbacks=0`
- [ ] `OK=12 WARN=0 FAIL=0`

> **Dica:** use `stop_api.ps1` antes de trocar o backend para evitar listeners fantasmas na porta 8000.

---

## 6. Smoke PostGIS estrito

Com a API PostGIS ativa:

```powershell
$env:STRICT_NO_FALLBACK="true"
python scripts\smoke_platform.py --expect-gold-backend postgis --skip-front
```

- [ ] `fallbacks_inicial=0` e `fallbacks_final=0 (delta=0)`
- [ ] `total_fallbacks=0`
- [ ] `OK=12 WARN=0 FAIL=0`
- [ ] Nenhum endpoint com `X-Fallback-Used: true`

---

## 7. GeoJSON oficial nos mapas

- [ ] Decisão documentada em [`decisao_mapa_geojson_oficial.md`](decisao_mapa_geojson_oficial.md)
- [ ] Assets em `dashboard/public/geo/` (`ufs.geojson`, `municipios_pr.geojson`, `municipios_rmc.geojson`)
- [ ] Componentes de mapa usam `react-leaflet` + `GeoJSON` (sem vector tiles no frontend)

---

## 8. Tegola frontend desativado

- [ ] Sem referências a `tegola`, `vectorgrid` ou `VITE_TEGOLA_*` em `dashboard/src/`
- [ ] Tegola permanece apenas como infra experimental (`docs/tegola_config_postgis.md`, `scripts/smoke_tegola.py`)

---

## 9. PostGIS funcionando

- [ ] Paridade Gold × PostGIS (item 3) aprovada
- [ ] Smoke PostGIS (itens 5 e 6) aprovado
- [ ] `GOLD_BACKEND=postgis` efetivo no processo uvicorn (via `start_stack.ps1 -GoldBackend postgis`)

---

## 10. Fallback funcionando

- [ ] `tests/test_fallback_registry.py` passa
- [ ] `GET /api/ops/fallbacks` responde durante o smoke
- [ ] Documentação em [`gold_backend_postgis_fallback.md`](gold_backend_postgis_fallback.md)
- [ ] Em operação PostGIS saudável: `X-Fallback-Used: false` e `total_fallbacks=0`
- [ ] `STRICT_NO_FALLBACK` é trava operacional apenas do smoke (não altera a API)

---

## Encerramento

```powershell
.\scripts\stop_api.ps1
```

---

## Referências

- [`README.md`](../README.md) — seção **Operação local**
- [`scripts/start_stack.ps1`](../scripts/start_stack.ps1)
- [`scripts/stop_api.ps1`](../scripts/stop_api.ps1)
- [`scripts/smoke_platform.py`](../scripts/smoke_platform.py)
