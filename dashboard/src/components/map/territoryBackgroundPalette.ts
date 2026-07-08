import type { Scope } from '../../api/types'
import type { GeoFeatureProperties } from '../../lib/geoJoin'

/** Ativar apenas para diagnóstico local — manter `false` no resultado final. */
export const DEBUG_TERRITORY_COLORS = false

// Decorative only: colors are deterministic and not data-driven.
// Paleta ORGMIGRA — contornos priorizados, opacidade suave.

export type DecorativeTerritoryStyle = {
  fill: string
  stroke: string
  fillOpacity: number
  strokeOpacity: number
}

type PaletteSwatch = DecorativeTerritoryStyle

const DEBUG_PALETTE: PaletteSwatch[] = [
  { fill: '#65B244', stroke: '#60B040', fillOpacity: 0.48, strokeOpacity: 0.68 },
  { fill: '#F9BD2C', stroke: '#F8B828', fillOpacity: 0.38, strokeOpacity: 0.6 },
  { fill: '#64748b', stroke: '#475569', fillOpacity: 0.36, strokeOpacity: 0.56 },
  { fill: '#194E93', stroke: '#184890', fillOpacity: 0.42, strokeOpacity: 0.62 },
]

const TERRITORY_BACKGROUND_PALETTES: Record<Scope, PaletteSwatch[]> = {
  br: [
    { fill: '#94a3b8', stroke: '#475569', fillOpacity: 0.21, strokeOpacity: 0.5 },
    { fill: '#194E93', stroke: '#184890', fillOpacity: 0.19, strokeOpacity: 0.48 },
    { fill: '#cbd5e1', stroke: '#64748b', fillOpacity: 0.2, strokeOpacity: 0.46 },
    { fill: '#3d73ad', stroke: '#184890', fillOpacity: 0.17, strokeOpacity: 0.44 },
    { fill: '#F9BD2C', stroke: '#F8B828', fillOpacity: 0.15, strokeOpacity: 0.4 },
  ],
  pr: [
    { fill: '#94a3b8', stroke: '#475569', fillOpacity: 0.2, strokeOpacity: 0.48 },
    { fill: '#8C5DAC', stroke: '#8858A8', fillOpacity: 0.18, strokeOpacity: 0.46 },
    { fill: '#cbd5e1', stroke: '#64748b', fillOpacity: 0.17, strokeOpacity: 0.44 },
    { fill: '#65B244', stroke: '#60B040', fillOpacity: 0.16, strokeOpacity: 0.42 },
  ],
  rmc: [
    { fill: '#94a3b8', stroke: '#475569', fillOpacity: 0.21, strokeOpacity: 0.5 },
    { fill: '#194E93', stroke: '#184890', fillOpacity: 0.19, strokeOpacity: 0.48 },
    { fill: '#cbd5e1', stroke: '#64748b', fillOpacity: 0.17, strokeOpacity: 0.44 },
    { fill: '#F9BD2C', stroke: '#F8B828', fillOpacity: 0.15, strokeOpacity: 0.4 },
  ],
}

export function stableTerritoryHash(value: string): number {
  let hash = 0
  for (let i = 0; i < value.length; i++) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0
  }
  return hash
}

export function getDecorativeTerritoryKey(
  properties: GeoFeatureProperties,
  index: number,
  scope: Scope,
): string {
  if (scope === 'br') {
    return String(
      properties.uf_norm ?? properties.uf ?? properties.uf_sigla ?? properties.name ?? index,
    )
  }
  return String(
    properties.municipio_norm ?? properties.municipio ?? properties.name ?? index,
  )
}

export function getDecorativeTerritoryStyle(
  properties: GeoFeatureProperties,
  index: number,
  scope: Scope,
): DecorativeTerritoryStyle {
  const key = getDecorativeTerritoryKey(properties, index, scope)
  const palette = DEBUG_TERRITORY_COLORS ? DEBUG_PALETTE : TERRITORY_BACKGROUND_PALETTES[scope]
  const colorIndex = stableTerritoryHash(key) % palette.length
  return palette[colorIndex]
}

export function getDecorativeTerritoryStyleByKey(
  territoryKey: string,
  scope: Scope,
): DecorativeTerritoryStyle {
  const palette = DEBUG_TERRITORY_COLORS ? DEBUG_PALETTE : TERRITORY_BACKGROUND_PALETTES[scope]
  const colorIndex = stableTerritoryHash(territoryKey) % palette.length
  return palette[colorIndex]
}
