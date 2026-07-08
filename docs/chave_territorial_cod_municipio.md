# Chave territorial `cod_municipio` — diagnóstico

Documento de preparação para a migração PostGIS/Tegola.  
**Não altera** o MVP filesystem-first: apenas registra o estado da chave territorial.

Competência inspecionada: **2026-04**.  
Script: `python scripts/diagnose_territorial_keys.py --ano 2026 --mes 4`

---

## 1. Como o join territorial funciona hoje

Fluxo ativo do dashboard:

1. A API entrega métricas Gold (`tabela_municipio_*`, `tabela_uf`, ICTT) **sem** `cod_municipio` (exceto ICTT, que já traz `municipio_norm`).
2. O frontend carrega geometrias estáticas de `dashboard/public/geo/*.geojson`.
3. `dashboard/src/lib/geoJoin.ts` faz join client-side por **nome normalizado**:
   - escopo `br` → property `uf_norm`
   - escopos `pr` / `rmc` → property `municipio_norm`
4. A normalização no front remove acentos, faz trim, colapsa espaços e usa **UPPERCASE** (`normalizeGeoKey`).

O ICTT (`pipelines/gold/compute_ictt.py`) já usa o universo de `municipios_pr.geojson` e mergeia por `municipio_norm`, mas **não grava** `cod_municipio` na tabela Gold ICTT.

---

## 2. Por que join por nome é suficiente para o MVP, mas frágil para PostGIS/Tegola

**Suficiente no MVP:** cobre o mapa Leaflet atual; RMC e ICTT fecham 100% por nome; PR fecha quase todo o conjunto com movimento.

**Frágil para banco/tiles:**

- nomes duplicáveis / homônimos em escopo nacional;
- ortografias e artefatos de microdados (ex.: valor `IGNORADO`);
- Tegola/PostGIS precisam de **chave estável e indexável** (`cod_municipio` IBGE, 7 dígitos);
- loaders PostGIS já esperam `cod_municipio` para UPSERT em `geo.municipios`.

---

## 3. Onde existe código IBGE hoje

### GeoJSON (ativo no frontend)

Arquivos em `dashboard/public/geo/` (e espelho em `data-lake/geo/processed/`):

| Arquivo | Feições | Propriedade de código | Preenchimento |
|---------|---------|------------------------|---------------|
| `municipios_pr.geojson` | 399 | **`cod_municipio`** | 399/399 |
| `municipios_rmc.geojson` | 29 | **`cod_municipio`** | 29/29 |

Outras properties: `municipio`, `municipio_norm`, `uf`, `uf_norm`, `uf_sigla`.

Geração: `pipelines/geo/prepare_geo_assets.py` (detecta `CD_MUN` / candidatos IBGE no shapefile e sobe como `cod_municipio`).

### Shapefiles

`data-lake/geodata/municipios/uf=PR/ano=2024/PR_Municipios_2024.shp` — malha IBGE 2024 (fonte do GeoJSON).

### Gold municipal

| Tabela | `cod_municipio`? | Colunas territoriais |
|--------|------------------|----------------------|
| `tabela_municipio` | **Não** | `uf`, `municipio` |
| `tabela_municipio_pr` | **Não** | `uf`, `municipio` |
| `tabela_municipio_rmc` | **Não** | `uf`, `municipio` |
| `tabela_ictt_municipio_pr` | **Não** | `uf`, `municipio`, `municipio_norm` (+ métricas ICTT) |

---

## 4. Resultado do `diagnose_territorial_keys.py` (2026-04)

| Join | Gold | GeoJSON | Casados | Não casados (Gold) | Cobertura Gold→Geo |
|------|------|---------|---------|--------------------|--------------------|
| `tabela_municipio_pr` × `municipios_pr` | 106 | 399 | 105 | **1 (`IGNORADO`)** | **99,06%** |
| `tabela_municipio_rmc` × `municipios_rmc` | 18 | 29 | 18 | 0 | **100%** |
| `tabela_ictt_municipio_pr` × `municipios_pr` | 399 | 399 | 399 | 0 | **100%** |

Observações:

- GeoJSON PR tem 399 municípios (universo completo); a Gold de movimentação PR só lista municípios com movimento na competência — daí “GeoJSON sem Gold” não é falha de join do mapa.
- RMC GeoJSON tem 29 municípios da lista institucional; Gold RMC tem 18 com movimento — todos casam.
- O único não casado em PR é o artefato **`IGNORADO`** (não é município IBGE). Deve ser tratado na etapa de enriquecimento (excluir, mapear à parte ou manter sem `cod_municipio`).

Exit code do script: **1** (por causa desse 1 município artefato em PR).

Chave futura recomendada: **`cod_municipio` (IBGE 7 dígitos)**.

---

## 5. Enriquecimento seguro da Gold

Script: `scripts/enrich_gold_cod_municipio.py`

### O que foi feito (competência 2026-04)

| Tabela | Antes (`cod_municipio` preenchido) | Depois | Observação |
|--------|-------------------------------------|--------|------------|
| `tabela_municipio_pr` | 0 / 106 | **105 / 106** | 1 linha `IGNORADO` permanece sem código |
| `tabela_municipio_rmc` | 0 / 18 | **18 / 18** | — |
| `tabela_ictt_municipio_pr` | 0 / 399 | **399 / 399** | — |
| `tabela_municipio` (BR) | n/a | **não enriquecida** | diagnóstico apenas nesta etapa |

- Lookup: GeoJSON `municipios_pr.geojson` / `municipios_rmc.geojson` (property `cod_municipio`).
- Colunas `municipio` e `municipio_norm` (quando existiam) foram **preservadas**.
- Nenhuma coluna existente foi removida ou renomeada; nenhuma linha removida.
- `IGNORADO` **não** é tratado como município real: linha mantida, `cod_municipio` nulo.
- Parquet e CSV sincronizados; backups `.bak_YYYYMMDD_HHMMSS` criados com `--backup`.
- Script **idempotente**: reexecução só preenche nulos/vazios.

### Contrato do frontend

O frontend continua usando o contrato antigo (join por nome via `geoJoin.ts`).  
A coluna `cod_municipio` é **aditiva** nas respostas JSON da API e poderá ser usada depois por PostGIS/Tegola, sem exigir mudança imediata do dashboard.

### Comandos

```powershell
# Dry-run (uma competência)
python scripts/enrich_gold_cod_municipio.py --ano 2026 --mes 4 --dry-run --strict

# Aplicar com backup (uma competência)
python scripts/enrich_gold_cod_municipio.py --ano 2026 --mes 4 --backup --strict
```

---

## 6. Backfill e uso mensal

### Módulo reutilizável

A lógica vive em `pipelines/gold/enrich_cod_municipio.py`.

Wrappers / entrypoints:

| Entrypoint | Uso |
|------------|-----|
| `scripts/enrich_gold_cod_municipio.py` | CLI pontual (1 competência) |
| `scripts/backfill_gold_cod_municipio.py` | Várias competências (`--meses 1 2 3 4`) |
| `pipelines/jobs/enrich_gold_cod_municipio.py` | Job Python dedicado |
| `pipelines/jobs/run_monthly_pipeline.py --enrich-cod-municipio` | Flag **opcional** após `aggregate_indicators` (com backup + strict); o fluxo sem a flag permanece igual |

### Como rodar

```powershell
# Uma competência
python scripts/enrich_gold_cod_municipio.py --ano 2026 --mes 4 --backup --strict

# Backfill multi-competência (dry-run e apply)
python scripts/backfill_gold_cod_municipio.py --ano 2026 --meses 1 2 3 4 --dry-run --strict
python scripts/backfill_gold_cod_municipio.py --ano 2026 --meses 1 2 3 4 --backup --strict

# Pipeline mensal (opcional)
python -m pipelines.jobs.run_monthly_pipeline --ano 2026 --mes 4 --enrich-cod-municipio
```

### Backfill aplicado (2026-01 .. 2026-04)

| Competência | `tabela_municipio_pr` | `tabela_municipio_rmc` | `tabela_ictt_municipio_pr` |
|-------------|------------------------|------------------------|----------------------------|
| 2026-01 | 103/104 (+ `IGNORADO` nulo) | 18/18 | 399/399 |
| 2026-02 | 105/106 (+ `IGNORADO` nulo) | 18/18 | 399/399 |
| 2026-03 | 105/106 (+ `IGNORADO` nulo) | 18/18 | 399/399 |
| 2026-04 | 105/106 (+ `IGNORADO` nulo) | 18/18 | 399/399 |

- `IGNORADO` é categoria **não territorial**: linha preservada, `cod_municipio` nulo; não falha `--strict` nem o diagnóstico de municípios reais.
- Contrato antigo do frontend preservado (`cod_municipio` é coluna aditiva).
- Esta etapa prepara loaders PostGIS futuros; **PostGIS ainda não está ligado**.

O diagnóstico `scripts/diagnose_territorial_keys.py` reporta `IGNORADO` à parte e só falha se houver município **real** sem match.

---

## 7. Recomendação para a próxima etapa

1. Usar `--enrich-cod-municipio` no rotina mensal (ou o job dedicado) após regenerar Gold.
2. Decidir política para `tabela_municipio` BR (malha nacional).
3. Adaptar loaders PostGIS para consumir `cod_municipio` já preenchido.
4. Só então ligar PostGIS/Tegola com feature flags (`GOLD_BACKEND`, geometria Tegola + GeoJSON fallback).

---

*Enriquecimento reproduzível na Gold PR/RMC/ICTT. Frontend e fluxo MVP inalterados.*
