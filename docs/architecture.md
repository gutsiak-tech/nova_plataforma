# Architecture

Estado atual do sistema. Snapshots históricos (filesystem-first pré-PostGIS) estão em [`arquitetura_atual.md`](arquitetura_atual.md).

## Layers

```
Raw data (Novo CAGED)
   ↓
Bronze          ingestão e metadata
   ↓
Silver          limpeza e padronização
   ↓
Gold            indicadores analíticos (Parquet + CSV)
   ↓
FastAPI         serving versionado
   ↓
Dashboard       React / Vite
```

Cálculo e serving são separados. A API não recalcula Gold. O dashboard não lê o data lake.

## Data plane

| Camada | Função | Local típico |
|---|---|---|
| Bronze | Microdados + `metadata.json` | `data-lake/bronze/` |
| Silver | Parquet tratado | `data-lake/silver/` |
| Gold | Tabelas por competência `ano=YYYY/mes=MM/` | `data-lake/gold/` |
| Catálogo | Schema formal da Gold | `data-lake/catalog/` |

Implementação: Python + pandas em `pipelines/`. Não usa Spark, Databricks nem Delta Lake.

## Serving

`GOLD_BACKEND` seleciona a fonte analítica:

- `filesystem` (padrão) — Parquet/CSV em `data-lake/gold/`
- `postgis` — tabelas carregadas a partir da Gold; fallback documentado em [`gold_backend_postgis_fallback.md`](gold_backend_postgis_fallback.md)

Mapas do dashboard usam **GeoJSON estático** (`dashboard/public/geo/`). Tegola existe como experimento de infra e não integra o frontend.

## ICTT v2

```
Silver
   ↓
ICTT v2 computation (`pipelines/gold/compute_ictt_v2.py`)
   ↓
Gold Parquet (`.../ictt_v2/tabela_ictt_v2_municipio_pr.parquet`)
   ↓
/api/ict/v2
   ↓
/ict
```

- Spec congelada: `pipelines/gold/ictt_v2/methodology_v2.json`
- API somente leitura: `app/api/routes_ictt_v2.py`
- Frontend: `dashboard/src/pages/IcttV2Page.tsx`

A Gold V1 (`tabela_ictt_municipio`) e `/api/ict/v1` permanecem para o fallback `/ict-v1`.

## Applications

| Componente | Stack | Entrada |
|---|---|---|
| Pipeline | Python, pandas | `python -m pipelines.jobs.run_monthly_pipeline` |
| API | FastAPI, uvicorn | `app.main:app` |
| Dashboard | React, TypeScript, Vite | `dashboard/` |

## Boundaries

- Pipeline grava Gold; não serve HTTP.
- API lê Gold versionada; não acessa microdados no caminho ICTT v2.
- ICTT v2 não usa PostGIS.
- Dashboard consome JSON da API e geometria GeoJSON; join territorial no cliente.
