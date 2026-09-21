# Contributing

Convenções curtas para quem altera este repositório.

## Environment

Siga [`docs/development.md`](docs/development.md). Não commite `.env`, `data-lake/` analítico nem microdados.

## Before a commit

```bash
pytest -q
```

```bash
cd dashboard
npm test
npm run build
```

Rode lint só nos arquivos que você tocou, se o escopo for frontend.

## Conventions

- Pipeline novo em `pipelines/`, não em `src/` (legado).
- API ICTT v2 é serving: não recalcular o índice no request.
- Metodologia v2 vive em `pipelines/gold/ictt_v2/methodology_v2.json`. Não retunar P05/P95 em produção.
- Migrações de schema PostGIS em `sql/migrations/`, versionadas.
- Commits focados (pipeline, API, frontend, docs) em vez de lotes mistos.

## Data

Não versionar Parquet/CSV Gold, dumps SQL nem exports de holdout. Metadata geográfica versionada segue a política de `data-lake/geo/`.

## ICTT

Não alterar scores, rankings ou contratos `/api/ict/v2` sem atualizar spec, testes de fingerprint e [`docs/ictt-methodology.md`](docs/ictt-methodology.md). A V1 em `/ict-v1` só deve mudar se o objetivo for a própria V1.
