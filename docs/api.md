# API

Serving HTTP do Observatório de Migrantes. A API lê Gold versionada; não recalcula indicadores no request.

Base local: `http://127.0.0.1:8000`.

## Saúde

| Método | Caminho | Função |
|---|---|---|
| GET | `/health` | Processo vivo |
| GET | `/ready` | Gold + catálogo disponíveis |

## Gold

Prefixo `/api/gold/v1`. Escopo `br` \| `pr` \| `rmc`. Competência via `ano` e `mes`.

Principais rotas: `/competencias`, `/overview`, `/table/{base_name}`, `/catalog`, `/meta`.

Contrato de tabelas e colunas: [`DATA_CONTRACT.md`](DATA_CONTRACT.md).

## ICTT v2

Prefixo `/api/ict/v2`. Fonte: Parquet `ictt_v2/tabela_ictt_v2_municipio_pr.parquet`. Sem PostGIS, sem CSV, sem recálculo.

O frontend `/ict` consome exclusivamente este prefixo.

| Método | Caminho | Função |
|---|---|---|
| GET | `/api/ict/v2/competencias` | Competências com artefato v2 |
| GET | `/api/ict/v2/methodology` | Versão, NORM_B, pesos, elegibilidade |
| GET | `/api/ict/v2/municipalities` | Malha municipal da competência |
| GET | `/api/ict/v2/municipalities/{codigo_municipio}` | Detalhe municipal |
| GET | `/api/ict/v2/ranking` | Ranking no universo `n10` ou `n20` |

Query comum: `competencia=YYYY-MM` (ex.: `2026-04`).

- `municipalities`: `reliability=reduced\|higher` (opcional)
- `ranking`: `universe=n10\|n20` (**obrigatório**; a API não elege ranking oficial)

Códigos de erro frequentes: `INVALID_COMPETENCIA`, `ICTT_V2_NOT_FOUND`, `ICTT_V2_MUNICIPALITY_NOT_FOUND`, `INVALID_UNIVERSE`, `INVALID_RELIABILITY`.

Municípios com N < 10 retornam `ictt_v2: null` e `calculavel: false`. Não há sentinela zero.

## ICT V1

| Método | Caminho | Função |
|---|---|---|
| GET | `/api/ict/v1/report-context` | Contexto analítico da Gold V1 (PCA) |

Query: `scope=pr`, `ano`, `mes`. Backend Gold conforme `GOLD_BACKEND`.

A rota de UI `/ict-v1` usa este endpoint. É **fallback técnico temporário**, não um produto público permanente.

## Frontend

| Rota | Backend |
|---|---|
| `/ict` | `/api/ict/v2/*` |
| `/ict-v1` | `/api/ict/v1/report-context` + Gold municipal V1 |
| `/ict-v2` | redirect HTTP client-side para `/ict` |
