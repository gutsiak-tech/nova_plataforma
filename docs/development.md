# Local development

Ambiente de laboratório em Windows (PowerShell) e Node.js. Não use caminhos absolutos de máquina.

## Prerequisites

- Python 3 com `venv`
- Node.js e npm
- Cópia de [`.env.example`](../.env.example) para `.env`
- Camada `data-lake/` local (microdados e Gold **não** vêm no Git)

## Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Stack recomendada

```powershell
.\scripts\start_stack.ps1 -GoldBackend filesystem
```

PostGIS (opcional, Docker + Postgres configurados):

```powershell
.\scripts\start_stack.ps1 -GoldBackend postgis
```

Encerrar API local:

```powershell
.\scripts\stop_api.ps1
```

`GOLD_BACKEND` precisa estar no **mesmo processo** da API. Definir a variável só no terminal do smoke não altera um uvicorn já iniciado.

## Backend manual

```powershell
.\.venv\Scripts\Activate.ps1
$env:GOLD_BACKEND="filesystem"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Porta: **8000**. Docs interativas: `/docs` (indisponíveis se `APP_ENV=production`).

## Frontend

```bash
cd dashboard
npm install
npm run dev
```

Vite: `http://localhost:5173`. Proxy `/api` → `http://127.0.0.1:8000`.

Build:

```bash
cd dashboard
npm run build
```

## Tests

Comando padrão (não exige API nem dataset de holdout):

```bash
pytest -q
```

Frontend:

```bash
cd dashboard
npm test
npm run build
```

Holdout ICTT 2025 (opcional, marcado `slow`/`integration`): defina `ICTT_V2_HOLDOUT_CSV` ou coloque o CSV em `data-lake/raw/migrantes/ano=2025/`. Sem o arquivo, o teste é ignorado (`skip`). O dataset não entra no Git.

Smoke operacional de tabelas Gold (API já iniciada; fora da suíte pytest):

```bash
python scripts/smoke_gold_table_api.py
```

## Pipeline

Ver [`pipeline.md`](pipeline.md). Exemplo:

```powershell
python -m pipelines.jobs.run_monthly_pipeline --ano 2026 --mes 4
python -m pipelines.gold.compute_ictt_v2 --ano 2026 --mes 4
```

## Configuration

Portas, CORS, `VITE_API_BASE_URL` e hardening: [`CONFIG.md`](CONFIG.md).
