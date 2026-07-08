# Gold backend PostGIS com fallback filesystem

## 1. O que é `GOLD_BACKEND`

Variável de ambiente que escolhe a fonte preferencial dos endpoints Gold territoriais:

```env
# filesystem | postgis
GOLD_BACKEND=filesystem
```

Default: **`filesystem`**. Valor inválido ou ausente → `filesystem` (com warning no log).

## 2. Valores

| Valor | Comportamento |
|-------|----------------|
| `filesystem` | Lê Gold no filesystem (Parquet/CSV). Não exige PostGIS. |
| `postgis` | Tenta PostGIS nos endpoints migrados; se falhar ou sem dados, usa filesystem. |

## 3. Headers de observabilidade

| Header | Significado |
|--------|-------------|
| `X-Gold-Backend` | Modo configurado (`filesystem` ou `postgis`). |
| `X-Data-Source: filesystem` | Resposta veio do filesystem (modo filesystem **ou** endpoint ainda não migrado com backend postgis). |
| `X-Data-Source: postgis` | Resposta veio do PostGIS. |
| `X-Data-Source: fallback_filesystem` | Backend era postgis, mas houve fallback real. |
| `X-Fallback-Used` | `true` somente no fallback real; `false` caso contrário. |

## 4. Endpoints migrados (podem ler PostGIS)

- `GET /api/gold/v1/table/tabela_municipio?scope=pr`
- `GET /api/gold/v1/table/tabela_municipio?scope=rmc`
- `GET /api/gold/v1/table/tabela_uf?scope=br`
- `GET /api/gold/v1/table/tabela_ictt_municipio?scope=pr`
- `GET /api/gold/v1/overview?scope=pr|rmc|br` (KPIs/rankings territoriais via PostGIS; setores/perfis/salários ainda filesystem)
- `GET /api/ict/v1/report-context?scope=pr`

### ICTT municipal PR

`tabela_ictt_municipio?scope=pr` lê `serving.fact_ictt_municipio_pr_mes` quando `GOLD_BACKEND=postgis`.

- Coluna do índice: `ICTT` (mesmo nome da Gold filesystem).
- Contrato JSON preservado (`municipio`, `municipio_norm`, `cod_municipio`, dimensões, etc.).
- Fallback filesystem permanece se PostGIS falhar ou não tiver dados da competência.
- Frontend, mapas, Tegola e GeoJSON **não** foram alterados; GeoJSON segue como geometria principal/fallback visual.

ICTT com `scope` diferente de `pr` não é suportado no PostGIS: com `GOLD_BACKEND=postgis` usa filesystem (`X-Data-Source: filesystem`, `X-Fallback-Used: false`).

### ICT report-context

`/api/ict/v1/report-context?scope=pr` agora também pode ler PostGIS (`GOLD_BACKEND=postgis`).

- Monta o **mesmo contrato JSON** via `build_report_context` a partir de `serving.fact_ictt_municipio_pr_mes`.
- Evolução mensal usa competências ICTT presentes no PostGIS até a competência pedida.
- Fallback filesystem permanece (cache JSON Gold / geração a partir do Parquet).
- Fallbacks reais entram em `GET /api/ops/fallbacks`.
- Frontend, mapas, GeoJSON e Tegola não foram alterados.

## 5. Endpoints ainda filesystem (mesmo com `GOLD_BACKEND=postgis`)

- demais tabelas Gold (setor, ocupação, perfis, etc.)
- catálogo / competências / meta
- mapas / Tegola / GeoJSON

Para esses, com backend postgis: `X-Data-Source: filesystem` e `X-Fallback-Used: false` (não é fallback; ainda não migrado).

## 6. Fallback

Quando `GOLD_BACKEND=postgis` e o repository PostGIS falha ou não tem dados:

1. Log `[DATA_SOURCE] fallback usado` (endpoint, table, scope, ano, mes, motivo)
2. Lê filesystem
3. Headers: `X-Data-Source: fallback_filesystem`, `X-Fallback-Used: true`

`IGNORADO` não existe no PostGIS (não é município real). A comparação territorial PostGIS usa os `cod_municipio` da Gold da competência (exclui resíduos de malha completa no volume).

## 7. Comandos oficiais (stack + smoke)

`GOLD_BACKEND` precisa estar no **processo que inicia a API**. Não adianta setar `$env:GOLD_BACKEND` apenas no terminal do smoke.

Configure em `.env` (default seguro):

```env
# Gold backend: filesystem | postgis
GOLD_BACKEND=filesystem
```

Ou passe explicitamente ao subir o stack:

### Modo seguro filesystem

```powershell
.\scripts\start_stack.ps1 -GoldBackend filesystem -SkipDashboard
python scripts/smoke_platform.py --expect-gold-backend filesystem --skip-front
```

### Modo PostGIS

```powershell
.\scripts\start_stack.ps1 -GoldBackend postgis -SkipDashboard
python scripts/smoke_platform.py --expect-gold-backend postgis --skip-front
```

Confirme no log de startup da API: `gold_backend=postgis` (ou `filesystem`).

### Modo PostGIS estrito

```powershell
$env:STRICT_NO_FALLBACK="true"
python scripts/smoke_platform.py --expect-gold-backend postgis --skip-front
```

- `--expect-gold-backend` verifica se a API subiu no backend esperado (`X-Gold-Backend`).
- `STRICT_NO_FALLBACK` verifica se houve fallback real PostGIS→filesystem durante o smoke.

## 8. Smoke legado (sem verificação de backend)

```powershell
python scripts/smoke_platform.py
```

O smoke exibe `x-gold-backend` / `x-data-source` / `x-fallback-used` nos endpoints Gold testados.

## 9. Voltar ao modo antigo

Defina no `.env`:

```env
GOLD_BACKEND=filesystem
```

Reinicie a API via `start_stack.ps1` ou `uvicorn`.

## 10. Contador operacional de fallbacks

Endpoint somente leitura:

```powershell
GET /api/ops/fallbacks
```

Snapshot em memória do processo FastAPI:

```json
{
  "total_fallbacks": 0,
  "by_endpoint": {},
  "by_table": {},
  "by_scope": {},
  "by_reason": {},
  "last_fallback_at": null,
  "recent_events": []
}
```

### O que conta

Apenas fallback **real** PostGIS → filesystem, quando o orquestrador responde com:

- `X-Data-Source: fallback_filesystem`
- `X-Fallback-Used: true`

(Ou seja: `GOLD_BACKEND=postgis`, consulta suportada, PostGIS falhou/sem dados, filesystem usado.)

### O que NÃO conta

- `GOLD_BACKEND=filesystem`
- endpoint/tabela ainda não migrado que usa filesystem esperado (`X-Data-Source: filesystem`)
- fallback visual GeoJSON do frontend
- reinício da API (zera o contador; não há persistência nesta etapa)

### Como interpretar

- `total_fallbacks=0` com `GOLD_BACKEND=postgis` → PostGIS servindo (ou não houve consulta com falha)
- `total_fallbacks>0` → houve degradação operacional; inspecione `by_reason` / `recent_events`
- Combine com headers `X-Gold-Backend`, `X-Data-Source`, `X-Fallback-Used` por request

## 11. STRICT_NO_FALLBACK no smoke

Trava **apenas operacional** do script `scripts/smoke_platform.py`. **Não altera a API.**

### Ativar

```powershell
.\scripts\start_stack.ps1 -GoldBackend postgis -SkipDashboard
$env:STRICT_NO_FALLBACK="true"
python scripts/smoke_platform.py --expect-gold-backend postgis --skip-front
```

Valores truthy: `true`, `1`, `yes`, `sim`.

### O que falha

1. Qualquer endpoint migrado testado pelo smoke com `X-Fallback-Used: true`.
2. Aumento de `total_fallbacks` em `/api/ops/fallbacks` **durante** o smoke  
   (`total_final > total_inicial`).

Mensagem: `STRICT_NO_FALLBACK violation` (endpoint, source, fallback header, totais).

### O que NÃO falha

- `STRICT_NO_FALLBACK` ausente/desligado (comportamento antigo do smoke)
- `GOLD_BACKEND=filesystem`
- fallback histórico já presente no registry **antes** do smoke (só o delta importa)
- endpoint ainda não migrado / filesystem esperado
- GeoJSON / frontend

### Desligar

```powershell
Remove-Item Env:STRICT_NO_FALLBACK -ErrorAction SilentlyContinue
```

## 12. Tegola (nota)

A configuração Tegola em `services/tileserver/config.toml` permanece como **experimento de infra** (validação isolada via `scripts/smoke_tegola.py`). O frontend **não consome** vector tiles; mapas usam **GeoJSON** — ver [`decisao_mapa_geojson_oficial.md`](decisao_mapa_geojson_oficial.md).

## 13. O que esta etapa NÃO altera

- frontend
- mapas / GeoJSON
- comportamento da API / contratos JSON
- novos endpoints PostGIS
- loaders PostGIS
