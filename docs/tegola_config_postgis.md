# Tegola — configuração PostGIS (preparação / experimental)

> **Nota:** Tegola está preparado e validado isoladamente (`scripts/smoke_tegola.py`), mas **não integrado ao frontend**. GeoJSON é o caminho oficial dos mapas — ver [`decisao_mapa_geojson_oficial.md`](decisao_mapa_geojson_oficial.md).

## 1. Objetivo

Alinhar o servidor de vector tiles **Tegola** ao schema PostGIS atual (`geo.*`), servindo **geometria + identificadores estáveis** para uso futuro no dashboard. Nesta etapa o Tegola é validado isoladamente; o frontend continua usando **GeoJSON**.

## 2. Maps e layers

| Map | Layer (provider) | Fonte PostGIS | Campos principais |
|-----|------------------|---------------|-------------------|
| `municipios_pr` | `plataforma_postgis.municipios_pr` | `geo.municipios` (`uf = 'PR'`) | `cod_municipio`, `municipio`, `municipio_norm`, `uf`, `geom` |
| `municipios_rmc` | `plataforma_postgis.municipios_rmc` | `geo.municipios_rmc` ⋈ `geo.municipios` | idem |
| `ufs_brasil` | `plataforma_postgis.ufs_brasil` | `geo.ufs` | `uf`, `nome_uf`, `uf_norm`, `cod_uf`, `geom` |
| `ictt_municipios_pr` | `plataforma_postgis.ictt_municipios_pr` | `geo.municipios` (`uf = 'PR'`) | idem municípios PR |

Métricas temporais (CAGED, ICTT, saldo etc.) **não** entram nos tiles — continuam na API Gold.

## 3. Sem ano/mês hardcoded

A configuração em `services/tileserver/config.toml` é **stateless**: não filtra `ano`, `mes` nem competência. Não usa a materialized view legada `serving.mv_mapa_saldo_municipio` (removida). Geometrias vêm de `geo.municipios` / `geo.ufs`; SQL usa `ST_AsBinary(geom) AS geom` e `geom && !BBOX!`.

## 4. Subir localmente

Pré-requisito: PostGIS com geometrias carregadas (`pipelines.gold.load_geo_tables`).

```powershell
docker compose -f infra/docker-compose.yml up -d postgres
python scripts/validate_postgis_vs_gold.py --ano 2026 --mes 4 --scope all
docker compose -f infra/docker-compose.yml up -d tegola
```

Logs:

```powershell
docker compose -f infra/docker-compose.yml logs tegola --tail=100
```

## 5. Testar `/capabilities`

```powershell
curl -i "http://127.0.0.1:8080/capabilities"
```

Deve listar os quatro maps acima.

## 6. Smoke automatizado

```powershell
python scripts/smoke_tegola.py
python scripts/smoke_tegola.py --tegola-base http://127.0.0.1:8080 --fail-on-empty
```

Verifica `GET /capabilities` (HTTP 200) e um tile `.pbf` por map (corpo > 0 bytes). Exit code `0` se não houver `FAIL`.

Exemplo de tile (padrão Tegola):

`http://127.0.0.1:8080/maps/municipios_pr/{z}/{x}/{y}.pbf`

## 7. O que esta etapa **não** faz

- Não altera `dashboard/src/` nem componentes React/Leaflet.
- Não troca GeoJSON por vector tiles no frontend.
- Não altera API Gold, `GOLD_BACKEND`, fallback PostGIS→filesystem nem `/api/ops/fallbacks`.
- Não remove GeoJSON.
- Não integra Tegola ao mapa da aplicação (próxima fase).

## 8. Correção em relação à config legada

A config anterior expunha um único map `municipios` / layer `saldo_municipio` sobre `serving.mv_mapa_saldo_municipio` com `ano = 2026`, `mes = 1` e `uf = 'PARANÁ'`. Foi substituída pelas quatro layers territoriais acima, alinhadas a `geo.*`.
