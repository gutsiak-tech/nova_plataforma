# Observatório de Migrantes

Plataforma de inteligência territorial do mercado de trabalho formal, com foco em movimentações de pessoas migrantes registradas no Novo CAGED.

O sistema processa microdados em uma arquitetura Medallion (Bronze → Silver → Gold), serve indicadores por API FastAPI e apresenta o resultado em um dashboard React.

## Overview

- Fonte: base filtrada do Novo CAGED (vínculos formais).
- Recortes territoriais: Brasil, Paraná e Região Metropolitana de Curitiba.
- Competência mensal (`ano`/`mês`) em todo o produto.
- Indicadores de admissões, desligamentos, saldo, setores, ocupações, perfil, país e salários.
- **ICTT v2.0** (Índice de Competitividade Territorial do Trabalho) como experiência principal em `/ict`.

Os microdados não fazem parte do repositório. Cada ambiente precisa da própria camada `data-lake/`.

## Architecture

```
Raw data
   ↓
Bronze
   ↓
Silver
   ↓
Gold (Parquet/CSV)
   ↓
FastAPI
   ↓
Dashboard
```

Serving da Gold: filesystem por padrão; PostGIS opcional (`GOLD_BACKEND=postgis`). Mapas usam GeoJSON estático.

Detalhes: [`docs/architecture.md`](docs/architecture.md).

## Data pipeline

Jobs em `pipelines/` (pandas, filesystem local):

1. Validação Bronze
2. Limpeza Silver
3. Agregação Gold + catálogo
4. ICTT v2 (partição própria, sem substituir a Gold V1)

Rotina mensal: [`docs/pipeline.md`](docs/pipeline.md) e [`docs/runbook_operacional.md`](docs/runbook_operacional.md).

## ICTT

O ICTT v2.0 combina quatro dimensões com pesos iguais (Absorção, Remuneração, Qualidade contratual, Diversificação). A normalização `NORM_B` está congelada.

| Rota | Conteúdo |
|---|---|
| `/ict` | ICTT v2.0 (experiência pública) |
| `/ict-v1` | ICT V1 (fallback técnico temporário) |
| `/ict-v2` | Redirect para `/ict` |

Metodologia: [`docs/ictt-methodology.md`](docs/ictt-methodology.md).

## Backend API

- Saúde: `GET /health`, `GET /ready`
- Gold: `/api/gold/v1/*`
- ICTT v2: `/api/ict/v2/*`
- ICT V1: `/api/ict/v1/report-context`

Contratos ICT: [`docs/api.md`](docs/api.md). Contrato Gold/front-end: [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md).

## Dashboard

React + TypeScript + Vite em `dashboard/`. Em desenvolvimento, `/api` é proxied para `http://127.0.0.1:8000`.

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

```powershell
.\scripts\start_stack.ps1 -GoldBackend filesystem
```

Ou, manualmente:

```powershell
$env:GOLD_BACKEND="filesystem"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd dashboard
npm install
npm run dev
```

Guia completo: [`docs/development.md`](docs/development.md). Configuração: [`docs/CONFIG.md`](docs/CONFIG.md).

## Tests

```bash
pytest -q
```

A contagem de testes é dinâmica:

```text
python -m pytest tests/ --collect-only -q
```

Contrato Gold/API/front-end: `tests/test_gold_frontend_contract.py`. Alinhamento de configuração (Tailwind, limites, CORS, defaults): `tests/test_config_alignment.py`.

Frontend:

```bash
cd dashboard
npm test
npm run build
```

Tailwind: config único em `dashboard/tailwind.config.cjs`.

Em produção, se o host estático não fizer proxy de `/api`, defina `VITE_API_BASE_URL` antes do build.

## Data and persistence

`data-lake/` é artefato local (Bronze, Silver, Gold, catálogo). Não versionar microdados, Parquet analítico nem `.env`.

GeoJSON de referência: `data-lake/geo/` (ver [`data-lake/geo/README.md`](data-lake/geo/README.md)).

## Repository structure

```
app/            FastAPI application
dashboard/      React frontend
pipelines/      Bronze, Silver, Gold and ICTT jobs
tests/          backend and pipeline tests
docs/           technical documentation
scripts/        operational scripts
infra/          optional PostGIS compose
sql/            schema and views
deploy/         reverse-proxy examples
src/            legacy pipeline modules (prefer pipelines/)
data-lake/      local data artifacts, not source code
```

## Documentation

| Documento | Conteúdo |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Arquitetura atual |
| [`docs/ictt-methodology.md`](docs/ictt-methodology.md) | Metodologia ICTT v2.0 |
| [`docs/api.md`](docs/api.md) | API ICTT |
| [`docs/development.md`](docs/development.md) | Setup local |
| [`docs/pipeline.md`](docs/pipeline.md) | Execução do pipeline |
| [`docs/gold_catalog.md`](docs/gold_catalog.md) | Catálogo Gold |
| [`docs/gold_backend_postgis_fallback.md`](docs/gold_backend_postgis_fallback.md) | Filesystem vs PostGIS |
| [`CHANGELOG.md`](CHANGELOG.md) | Histórico de versões |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Convenções de contribuição |

Documentos institucionais e operacionais adicionais permanecem em `docs/` (`handoff_institucional.md`, `runbook_operacional.md`, `entrega_institucional.md`).

## License and data

Microdados do CAGED são dados públicos. Consulte a fonte oficial para termos de uso. Este repositório não redistribui a base bruta.
