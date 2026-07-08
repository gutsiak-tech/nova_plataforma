# Backfill PostGIS — competências MVP (2026-01 .. 2026-04)

Documento da etapa de carga multi-competência no PostGIS **sem** conectar a API.

---

## 1. Objetivo

Deixar o PostGIS completo e validado para as competências do MVP (`2026-01` a `2026-04`), usando os loaders idempotentes com `cod_municipio`.

A API Gold continua lendo **filesystem**. Frontend/mapas/Tegola não mudam.

## 2. Competências carregadas

- `2026-01`
- `2026-02`
- `2026-03`
- `2026-04`

## 3. Datasets carregados (por competência)

- `municipio-pr` → `serving.fact_emprego_municipio_mes`
- `municipio-rmc` → `serving.fact_emprego_municipio_mes`
- `uf` → `serving.fact_emprego_uf_mes`
- `ictt-pr` → `serving.fact_ictt_municipio_pr_mes`

Geometrias (uma vez, antes dos fatos):

- `municipios-pr` → `geo.municipios`
- `municipios-rmc` → `geo.municipios_rmc` (+ geometria em `geo.municipios`)
- `ufs` → `geo.ufs`

## 4. Dry-run

```powershell
python scripts/backfill_postgis_facts.py --ano 2026 --meses 1 2 3 4 --dry-run --validate
```

Não escreve no banco; lista cargas e validações planejadas.

## 5. Carga real

```powershell
# Geometrias (idempotente)
python -m pipelines.gold.load_geo_tables --dataset municipios-pr
python -m pipelines.gold.load_geo_tables --dataset municipios-rmc
python -m pipelines.gold.load_geo_tables --dataset ufs

# Fatos + validação por competência
python scripts/backfill_postgis_facts.py --ano 2026 --meses 1 2 3 4 --validate
```

## 6. Validação explícita

```powershell
python scripts/validate_postgis_vs_gold.py --ano 2026 --mes 1 --scope all
python scripts/validate_postgis_vs_gold.py --ano 2026 --mes 2 --scope all
python scripts/validate_postgis_vs_gold.py --ano 2026 --mes 3 --scope all
python scripts/validate_postgis_vs_gold.py --ano 2026 --mes 4 --scope all
```

## 7. Idempotência

Reexecutar o backfill com `--validate` e as validações por competência deve manter totais iguais (upsert; sem duplicar).

## 8. Tratamento de `IGNORADO`

Categoria não territorial: não entra em `serving.fact_emprego_municipio_mes`. Loaders municipais reportam `ignored_non_territorial`.

## 8.1. Resíduos legados no PostGIS (UF)

A validação UF filtra pelas siglas presentes na Gold (mesmo padrão dos municípios). Resíduos antigos (ex.: `NI`) podem existir no volume Docker, mas **não** são gravados pelo loader atual e **não** provocam `FAIL` se os totais Gold × PostGIS (pelas UFs da competência) baterem. Não usamos `TRUNCATE`/`DROP` nesta etapa.

## 9. O que esta etapa NÃO faz

- Não cria `GOLD_BACKEND`
- Não cria `app/repositories/`
- Não conecta a API Gold ao PostGIS
- Não altera frontend / mapas / GeoJSON
- Não altera Tegola / `services/tileserver/config.toml`
- Não remove filesystem Gold
