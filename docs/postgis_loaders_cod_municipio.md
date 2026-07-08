# Loaders PostGIS com `cod_municipio`

Documento da **fase de loaders** — carga PostGIS a partir da Gold enriquecida.

> **Nota histórica:** quando este documento foi escrito, a API Gold ainda não lia PostGIS como backend. **Hoje**, com `GOLD_BACKEND=postgis` (via `.env` ou `scripts/start_stack.ps1 -GoldBackend postgis`), a API já lê os endpoints migrados diretamente do PostGIS, com fallback Gold filesystem. Ver [`gold_backend_postgis_fallback.md`](gold_backend_postgis_fallback.md).  
> Os loaders abaixo continuam válidos para popular o banco; mapas no frontend seguem **GeoJSON** (Tegola não integrado ao dashboard).

---

## 1. Objetivo

Carregar geometrias e fatos da Gold para PostGIS de forma **idempotente**, usando **`cod_municipio` (IBGE)** como chave territorial principal nos fatos municipais e ICTT.

## 2. Por que `cod_municipio`

Join por nome é frágil para banco/tiles. A Gold PR/RMC/ICTT já foi enriquecida via GeoJSON (`pipelines/gold/enrich_cod_municipio.py`). Os loaders **exigem** essa coluna nos datasets municipais e falham de forma explícita se ela estiver ausente — **sem** fallback silencioso por nome.

## 3. Tratamento de `IGNORADO`

Categoria **não territorial**. Linhas com município `IGNORADO` são **ignoradas** na carga municipal PostGIS (não entram em `serving.fact_*`). Não falham o loader.

## 4. Datasets suportados

### Geometria (`pipelines/gold/load_geo_tables.py`)

| Dataset | Destino | Fonte padrão |
|---------|---------|--------------|
| `municipios-pr` | `geo.municipios` | `dashboard/public/geo/municipios_pr.geojson` |
| `municipios-rmc` | `geo.municipios_rmc` (+ upsert em `geo.municipios`) | `municipios_rmc.geojson` |
| `ufs` | `geo.ufs` | `ufs.geojson` |

API admin legada `load_municipios_geometria(shapefile, ...)` permanece para shapefile.

### Fatos (`pipelines/gold/load_fact_tables.py`)

| Dataset | Fonte Gold | Destino |
|---------|------------|---------|
| `municipio-pr` | `tabela_municipio_pr` | `serving.fact_emprego_municipio_mes` |
| `municipio-rmc` | `tabela_municipio_rmc` | `serving.fact_emprego_municipio_mes` |
| `uf` | `tabela_uf` | `serving.fact_emprego_uf_mes` |
| `ictt-pr` | `tabela_ictt_municipio_pr` | `serving.fact_ictt_municipio_pr_mes` |

## 5. Schema / migration

- Baseline: `sql/schema.sql`, `sql/views.sql`, `sql/indexes.sql`
- Migration idempotente para bases existentes: `sql/migrations/002_postgis_fact_cod_municipio.sql`

Views stateless (filtrar por `ano`/`mes` na query):

- `serving.vw_emprego_municipio_mes`
- `serving.vw_emprego_uf_mes`
- `serving.vw_mapa_ictt_municipios_pr_mes`

## 6. Como carregar geometrias

```powershell
# Garantir PostGIS no ar (Tegola pode subir junto; falha legada do Tegola não invalida esta etapa)
docker compose -f infra/docker-compose.yml up -d postgres

# Aplicar migration 002 se o volume já existia
# (ex.: docker exec -i projeto_caged_postgres psql -U postgres -d plataforma < sql/migrations/002_postgis_fact_cod_municipio.sql)

python -m pipelines.gold.load_geo_tables --dataset municipios-pr
python -m pipelines.gold.load_geo_tables --dataset municipios-rmc
python -m pipelines.gold.load_geo_tables --dataset ufs
```

## 7. Como carregar fatos

```powershell
python -m pipelines.gold.load_fact_tables --dataset municipio-pr --ano 2026 --mes 4
python -m pipelines.gold.load_fact_tables --dataset municipio-rmc --ano 2026 --mes 4
python -m pipelines.gold.load_fact_tables --dataset uf --ano 2026 --mes 4
python -m pipelines.gold.load_fact_tables --dataset ictt-pr --ano 2026 --mes 4
```

Reexecutar as mesmas cargas é seguro (upsert).

## 8. Como validar Gold × PostGIS

```powershell
python scripts/validate_postgis_vs_gold.py --ano 2026 --mes 4 --scope all
```

A validação municipal compara **apenas os `cod_municipio` presentes na Gold** da competência (evita falsos FAILs por resíduos de malha completa / cargas legadas ainda no volume Docker).

UF: uma linha Gold sem sigla válida (ex.: categoria não mapeável) é ignorada no loader (`skipped`); as 27 UFs IBGE devem casar.

## 9. O que esta etapa NÃO faz

- Não cria `GOLD_BACKEND`
- Não faz a API Gold ler PostGIS como fonte principal
- Não altera frontend / mapas / GeoJSON
- Não altera `services/tileserver/config.toml` / Tegola
- Não muda contratos JSON do dashboard
- Não faz `TRUNCATE`/`DROP` de fatos legados já presentes no volume
