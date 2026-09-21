# Arquitetura atual — baseline congelado (MVP)

> **Snapshot histórico** do baseline filesystem-first, anterior à migração territorial PostGIS/Tegola.
> Estado operacional atual: [`architecture.md`](architecture.md). ICTT v2.0: [`ictt-methodology.md`](ictt-methodology.md).

Documento de congelamento do estado operacional **antes** da migração territorial PostGIS/Tegola.  
Não descreve o estado futuro desejado; registra apenas o que está ativo hoje.

---

## 1. Estado atual do projeto

- **MVP filesystem-first.**
- **FastAPI** lê a camada Gold local em `data-lake/gold/caged/ano=*/mes=*/` (Parquet com fallback CSV).
- **Frontend React/Vite** consome a API Gold via proxy `/api` e renderiza mapas com **GeoJSON estático** em `dashboard/public/geo/`.
- **PostGIS / Tegola** existem no repositório (`sql/`, `infra/docker-compose.yml`, `services/tileserver/`, loaders), mas **não estão integrados ao produto** (o dashboard não consome Tegola nem `/api/map` no fluxo principal).

Não há, neste momento:

- `GOLD_BACKEND`
- `app/repositories/`
- `VITE_MAP_GEOMETRY_SOURCE` / `VITE_TEGOLA_BASE_URL`
- `STRICT_NO_FALLBACK`

---

## 2. Fluxo atual dos dados

```
microdados → Bronze → Silver → Gold (CSV/Parquet em data-lake/)
                                    ↓
                              FastAPI (app/)
                                    ↓
                         React/Vite (dashboard/)
                                    ↓
                    pages / KPIs / gráficos / tabelas

GeoJSON estático (dashboard/public/geo/)
                                    ↓
                         Leaflet (TerritoryMap / IctMap)
                                    ↓
              join client-side (geoJoin.ts) com métricas da API Gold
```

| Consumo | Fonte ativa |
|---------|-------------|
| Overview / tabelas / competências / ICT | Filesystem Gold via `/api/gold/v1/*` e `/api/ict/v1/*` |
| Geometria do mapa | `/geo/*.geojson` (estático) |
| Métricas do mapa | `tabela_municipio` / `tabela_uf` / ICTT via API + join por nome normalizado |

---

## 3. O que NÃO está ativo ainda

- PostGIS como backend principal de indicadores.
- Gold filesystem como fallback de um backend PostGIS.
- Tegola / vector tiles no frontend.
- GeoJSON como fallback de Tegola.
- Observabilidade `X-Data-Source` nas respostas HTTP.
- Contador `/api/ops/fallbacks`.
- Feature flags de fonte de dados / geometria.

A rota `GET /api/map/municipios` e os loaders PostGIS existem no código, mas **não fazem parte do caminho de produto do dashboard**.

---

## 4. Arquivos críticos do baseline

| Área | Arquivo / pasta |
|------|-----------------|
| Leitura Gold | `app/services/gold_service.py` |
| Rotas Gold | `app/api/routes_gold.py` |
| Rotas ICT | `app/api/routes_ict.py` |
| Mapa território | `dashboard/src/components/map/TerritoryMap.tsx` |
| Mapa ICT | `dashboard/src/components/map/IctMap.tsx` |
| Join geo ↔ métricas | `dashboard/src/lib/geoJoin.ts` |
| Assets GeoJSON | `dashboard/public/geo/` |
| Dados Gold | `data-lake/gold/caged/` |
| Agregação Gold | `pipelines/gold/aggregate_indicators.py` |
| ICTT | `pipelines/gold/compute_ictt.py` |
| Schema PostGIS (preparado) | `sql/schema.sql` |
| Compose PostGIS+Tegola (preparado) | `infra/docker-compose.yml` |
| Config Tegola (preparada / legada) | `services/tileserver/config.toml` |

Smoke do baseline: `scripts/smoke_platform.py`.

---

## 5. Riscos atuais

- Join territorial por **nome normalizado** (`municipio_norm` / `uf_norm`), não por código IBGE.
- Ausência de `cod_municipio` estável nas tabelas Gold territoriais usadas pelo mapa.
- Config Tegola legada (referencia artefato/MV desalinhado do schema stateless atual).
- PostGIS preparado, mas **fora** do fluxo principal e sem feature flag.
- Até este congelamento, ausência de smoke geral multi-endpoint; o script `scripts/smoke_platform.py` passa a cobrir o baseline.
- Ausência de feature flags (`GOLD_BACKEND`, `VITE_MAP_GEOMETRY_SOURCE`, etc.).

---

## 6. Próxima etapa recomendada

1. Validar o MVP com `python scripts/smoke_platform.py` (e `--skip-front` se o Vite não estiver no ar).
2. Enriquecer a chave territorial (**IBGE / `cod_municipio`**) na Silver/Gold.
3. Só então iniciar a migração territorial PostGIS com filesystem como fallback e Tegola para geometria (GeoJSON como fallback).

---

*Baseline documentado para homologação/migração futura. Alterações de comportamento do produto devem ser tratadas como evolução além deste congelamento.*
