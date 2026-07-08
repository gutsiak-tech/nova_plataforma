# Mapa territorial — vector tiles no frontend (histórico / experimental)

> **ATENÇÃO:** a integração Tegola no frontend foi **desabilitada e removida**. **GeoJSON é o caminho oficial** dos mapas. Ver [`decisao_mapa_geojson_oficial.md`](decisao_mapa_geojson_oficial.md).

Este documento permanece como **registro histórico** da tentativa de integração Brasil/UF via Tegola + `leaflet.vectorgrid` (removida em 2026).

---

## Contexto histórico

Foi implementada (e depois removida) uma integração experimental com:

- `VITE_MAP_GEOMETRY_SOURCE=geojson|tegola`
- `VITE_TEGOLA_BASE_URL`
- `TegolaUfVectorLayer` + `leaflet.vectorgrid`
- Camada `ufs_brasil` apenas para `scope=br`

### Motivo da remoção

- Artefatos visuais graves (blocos/retângulos de tiles, sobreposição).
- Lentidão forte no navegador.
- GeoJSON atende ao MVP; migração futura provável para GCP/Google Maps.

### O que permanece ativo

| Item | Status |
|------|--------|
| GeoJSON (`dashboard/public/geo/`) | **Oficial** |
| PostGIS backend | Mantido |
| `services/tileserver/config.toml` | Experimental / isolado |
| `scripts/smoke_tegola.py` | Smoke experimental |

### Arquivos removidos do frontend

- `dashboard/src/config/mapSource.ts`
- `dashboard/src/components/map/TegolaUfVectorLayer.tsx`
- `dashboard/src/types/leaflet.vectorgrid.d.ts`
- `leaflet.vectorgrid` (dependência)
- `mapTegolaUfProperties` em `geoJoin.ts`
- `dashboard/.env.example` (variáveis Tegola)

---

## Registro técnico (antes da remoção)

<details>
<summary>Conteúdo original da integração (colapsado)</summary>

### Variáveis que existiam

```env
VITE_MAP_GEOMETRY_SOURCE=geojson
VITE_TEGOLA_BASE_URL=http://127.0.0.1:8080
```

### Escopo da integração removida

| Camada | Fonte com flag `tegola` |
|--------|-------------------------|
| Brasil/UF (`scope=br`) | Tegola `ufs_brasil` |
| Paraná, RMC, ICT | Sempre GeoJSON |

### Join de métricas

Tiles expunham `uf`, `nome_uf`, `uf_norm`, `cod_uf`. Join via `uf_norm`, igual ao GeoJSON.

### Fallback planejado (removido com a integração)

1. Flag ausente/inválida → GeoJSON.
2. `GET /capabilities` falha → GeoJSON.
3. `tileerror` → GeoJSON.

</details>
