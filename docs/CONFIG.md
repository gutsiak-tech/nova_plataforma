# Configuração — nova_plataforma

Referência operacional curta para desenvolvimento local e deploy. Detalhes de dados Gold/API/front-end: [`DATA_CONTRACT.md`](DATA_CONTRACT.md).

---

## Portas principais

| Serviço | Porta | Onde |
|---------|-------|------|
| API FastAPI | **8000** | `uvicorn app.main:app --host 127.0.0.1 --port 8000`; `scripts/start_stack.ps1` |
| Dashboard Vite (dev) | **5173** | `dashboard/vite.config.ts` (`server.port`) |
| Vite preview | **4173** | `npm run preview` (padrão Vite); incluída no CORS da API |
| Vite alternativa | **5174** | Usada quando 5173 está ocupada; incluída no CORS da API |

---

## Dev proxy

Em desenvolvimento, `dashboard/vite.config.ts` define:

```text
/api  →  http://127.0.0.1:8000
```

O cliente axios (`dashboard/src/api/http.ts`) usa `baseURL=''`, então chamadas a `/api/gold/v1/...` passam pelo proxy do Vite. **A API deve estar ativa antes do dashboard.**

---

## API base URL (`VITE_API_BASE_URL`)

| Ambiente | Comportamento |
|----------|---------------|
| **Dev** | `baseURL=''` + proxy Vite (acima) |
| **Produção** | Se o host estático **não** servir `/api` na mesma origem, defina **`VITE_API_BASE_URL`** (ex.: `http://127.0.0.1:8000`) **antes** de `npm run build` |

Implementação: `dashboard/src/api/http.ts` → `import.meta.env.VITE_API_BASE_URL ?? ''`.

Não há `VITE_*` em [`.env.example`](../.env.example) na raiz do projeto; variáveis Vite costumam ser definidas no ambiente de build ou em `dashboard/.env` local (não versionado).

---

## CORS

Origens permitidas são configuradas por **`CORS_ALLOWED_ORIGINS`** (vírgula-separada) em `.env`.

| Ambiente | Comportamento |
|----------|---------------|
| **Dev** (variável vazia) | Defaults em `app/core/config.py`: localhost/127.0.0.1 nas portas 5173, 5174, 4173 |
| **Produção** | Defina origens explícitas, ex.: `CORS_ALLOWED_ORIGINS=https://dashboard.exemplo.org` |

Implementação: `app/main.py` → `CORSMiddleware(allow_origins=CORS_ALLOWED_ORIGINS)`.

Não use `*` em produção se houver credenciais ou endpoints administrativos.

---

## Segurança (hardening mínimo)

| Variável | Default | Uso |
|----------|---------|-----|
| `ADMIN_BEARER_TOKEN` | vazio | Bearer token para `POST /api/admin/*` |
| `ENABLE_DEBUG_ROUTES` | `false` | Monta `/api/debug/*` (também exige Bearer) |
| `APP_ENV` | `local` | Em `production`, admin sem token configurado retorna 503 |

Endpoints **read-only** do dashboard (`/api/gold/v1/*`, `GET /api/map/municipios`, `/health`) permanecem públicos.

Detalhes internos de erro Gold são filtrados em `APP_ENV=production` (sem paths locais na resposta).

---

## Defaults (back-end e front-end)

| Variável | Back-end (`.env` / `app/core/config.py`) | Front-end |
|----------|------------------------------------------|-----------|
| `DEFAULT_ANO` | `2026` (fallback no código) | `dashboard/src/api/constants.ts` → `DEFAULT_API_ANO = 2026` (hardcoded; comentário indica alinhamento com `.env`) |
| `DEFAULT_MES` | `4` (fallback; [`.env.example`](../.env.example)) | `DEFAULT_API_MES = 4` em `constants.ts`; fallbacks em `gold.ts` se `/competencias` falhar |
| `DEFAULT_UF` | `PR` | não identificado uso direto no dashboard |
| **Scope** | `br` default em `GET /table` e `GET /overview` | `ScopeContext.tsx` → `useState<Scope>('br')` |

Competência no UI: URL `?ano=&mes=` + `localStorage` — ver `dashboard/src/lib/competenciaPersistence.ts` e `MonthContext.tsx`.

---

## Limites de tabela (`/api/gold/v1/table/{base_name}`)

| Local | Valor |
|-------|-------|
| `app/api/routes_gold.py` | `limit` query: default **50**, máximo **2000** (`ge=1, le=2000`) |
| `dashboard/src/lib/apiLimits.ts` | `API_TABLE_MAX_LIMIT = 2000` |
| `dashboard/src/api/gold.ts` | `fetchTable` default `limit: 2000` |

O front-end envia até 2000 linhas por padrão; a API aceita no máximo 2000. O alinhamento entre esses valores é verificado estaticamente por `tests/test_config_alignment.py`.

---

## Tailwind CSS

| Arquivo | Papel |
|---------|-------|
| **`dashboard/tailwind.config.cjs`** | **Única fonte de verdade** — PostCSS (`postcss.config.cjs`) carrega este arquivo no build |

Alterações de theme/plugins Tailwind devem ir apenas no `.cjs`. Tokens de cor para charts: `dashboard/src/index.css` (CSS variables) → `tokens.ts` → `chartTheme.ts`; classes de layout: `theme.ts`.

---

## Documentos relacionados

- [`README.md`](../README.md) — visão geral e execução
- [`DATA_CONTRACT.md`](DATA_CONTRACT.md) — contrato Pipeline Gold / API / front-end
- [`gold_catalog.md`](gold_catalog.md) — catálogo formal da camada Gold
- [`runbook_operacional.md`](runbook_operacional.md) — rotina mensal e diagnóstico

---

## Testes estáticos de configuração e contrato

| Arquivo | O que protege |
|---------|---------------|
| [`tests/test_gold_frontend_contract.py`](../tests/test_gold_frontend_contract.py) | Contrato de dados Gold/API/front-end vs [`DATA_CONTRACT.md`](DATA_CONTRACT.md) |
| [`tests/test_config_alignment.py`](../tests/test_config_alignment.py) | Alinhamento documentado deste arquivo e do README: Tailwind único (`tailwind.config.cjs`), limite **2000**, defaults `DEFAULT_ANO`/`DEFAULT_MES`, `VITE_API_BASE_URL`, proxy Vite, CORS em `app/main.py`, referências cruzadas |

Ambos são **estáticos** (leitura de arquivos com `pathlib`/regex), **não dependem** de data-lake populado e **não validam**:

- CORS em runtime (requisições reais do browser)
- deploy ou build de produção (`npm run build`)
- API em execução (smoke HTTP)
- aparência visual / CSS gerado

A contagem total de testes é **dinâmica** (varia conforme novos arquivos em `tests/`). Obtenha a contagem atual com:

```powershell
python -m pytest tests/ --collect-only -q
```
