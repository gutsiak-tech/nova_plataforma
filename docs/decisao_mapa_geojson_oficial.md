# Decisão: GeoJSON como caminho oficial dos mapas

## 1. Decisão

- **GeoJSON** é o caminho oficial dos mapas no MVP.
- **Tegola não será usado no frontend** neste momento.
- **PostGIS** continua como backend analítico (com fallback Gold filesystem).

## 2. Motivo

- A integração Tegola + `leaflet.vectorgrid` para Brasil/UF apresentou **artefatos visuais graves** (blocos/retângulos de tiles, sobreposição) e **lentidão forte** no navegador.
- GeoJSON atende ao escopo atual: UFs, municípios PR, RMC e ICT PR.
- O projeto poderá migrar futuramente para **GCP / Google Maps**; manter vector tiles customizados no frontend não é prioridade do MVP.

## 3. Arquitetura oficial agora

```
Frontend Leaflet
  → GeoJSON estático (dashboard/public/geo/)
  → join com métricas da API Gold / PostGIS

API FastAPI
  → PostGIS quando GOLD_BACKEND=postgis
  → fallback Gold filesystem
```

## 4. O que fica mantido

| Componente | Status |
|------------|--------|
| PostGIS | Mantido |
| `GOLD_BACKEND=filesystem\|postgis` | Mantido |
| Fallback PostGIS → filesystem | Mantido |
| `/api/ops/fallbacks` | Mantido |
| `STRICT_NO_FALLBACK` (smoke) | Mantido |
| GeoJSON em `dashboard/public/geo/` | Mantido |
| `scripts/smoke_platform.py` | Mantido |
| `scripts/validate_postgis_vs_gold.py` | Mantido |
| Loaders PostGIS | Mantidos |

## 5. O que fica desativado no frontend

| Item | Status |
|------|--------|
| Tegola no frontend | Removido |
| `leaflet.vectorgrid` | Removido |
| `VITE_MAP_GEOMETRY_SOURCE` | Removido |
| `VITE_TEGOLA_BASE_URL` | Removido |
| `TegolaUfVectorLayer` | Removido |

## 6. Infra experimental (mantida, não integrada)

| Item | Uso |
|------|-----|
| `services/tileserver/config.toml` | Preparado; validação isolada |
| `scripts/smoke_tegola.py` | Smoke experimental do tileserver |
| `docs/tegola_config_postgis.md` | Documentação do tileserver |

## 7. Limitações conhecidas do GeoJSON

- Pode pesar se expandir para municípios de todo o Brasil.
- Pode ser insuficiente para muitas camadas ou geometria muito detalhada.
- Exige cuidado com simplificação na geração dos assets.
- Renderiza toda a malha no browser.

## 8. Justificativa

Para o MVP atual, GeoJSON é **mais simples, previsível e estável** do que vector tiles via Tegola no Leaflet.

## 9. Próximo passo sugerido

- Manter mapas em GeoJSON para o MVP.
- Avaliar **Google Maps** ou outra solução gerenciada quando houver migração GCP.
- PostGIS permanece como fonte analítica; não é necessário remover o scaffolding Tegola da infra.
