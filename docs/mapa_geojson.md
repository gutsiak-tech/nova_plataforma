# Mapa territorial — assets GeoJSON

Documentação da estratégia de mapa adotada na etapa **M3** e preparação de assets na **M3.1**.

## Estratégia

O dashboard usa **GeoJSON estático** servido por `dashboard/public/geo/` antes de integrar PostGIS/Tegola. Métricas (saldo, admissões, desligamentos) continuam vindo da **camada Gold** via API; o mapa apenas fornece geometrias.

| Escopo | GeoJSON | Dados Gold |
|--------|---------|------------|
| Brasil (`br`) | `ufs.geojson` | `tabela_uf` |
| Paraná (`pr`) | `municipios_pr.geojson` | `tabela_municipio_pr` |
| RMC (`rmc`) | `municipios_rmc.geojson` | `tabela_municipio_rmc` |

## Shapefiles necessários

1. UFs/estados do Brasil
2. Municípios do Paraná

Não é necessário shapefile da RMC — ela é filtrada a partir dos municípios paranaenses.

## Preparar assets

Ver instruções completas em [`data-lake/geo/README.md`](../data-lake/geo/README.md).

```bash
python -m pipelines.geo.prepare_geo_assets --help
```

## Chaves de join

Propriedades geradas nos GeoJSONs:

- `uf`, `uf_sigla`, `uf_norm`, `cod_uf`
- `municipio`, `municipio_norm`, `cod_municipio`

Join inicial com a Gold por **nome normalizado** (`*_norm`). Código IBGE (`cod_municipio`) é preservado quando presente no shapefile para migração futura.

## PostGIS e Tegola

A infraestrutura em `infra/docker-compose.yml` permanece para etapa futura (**M6**), após integração de código IBGE na Gold.

### Arquitetura stateless (multiusuário)

- **`GET /api/map/municipios?ano=&mes=&uf=`** — consulta parametrizada; **não** altera estado no banco.
- View **`serving.vw_emprego_municipio_mes`** — filtre por competência na query (`WHERE ano/mes/uf`).
- **Não usar** `REFRESH MATERIALIZED VIEW` por troca de filtro de usuário.
- Materialized view legada `mv_saldo_municipio` foi **descontinuada** (ver `sql/materialized_views.sql`).
- Loaders PostGIS: carga **idempotente** (`ON CONFLICT DO UPDATE`) — ver `pipelines/gold/load_fact_tables.py` e `load_geo_tables.py`.
- Migração de bases antigas: `sql/migrations/001_drop_legacy_map_global_state.sql`.

## Próxima etapa

**M4** — implementar `TerritoryMap` com Leaflet/react-leaflet, substituindo `MapPlaceholder`.
