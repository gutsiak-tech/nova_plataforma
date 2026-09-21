import { ICT_CHOROPLETH } from '../map/ictChoropleth'

function hexToRgb(hex: string): [number, number, number] {
  const raw = hex.replace('#', '')
  return [
    Number.parseInt(raw.slice(0, 2), 16),
    Number.parseInt(raw.slice(2, 4), 16),
    Number.parseInt(raw.slice(4, 6), 16),
  ]
}

function lerp(start: number, end: number, t: number): number {
  return start + (end - start) * t
}

/** Escala visual contínua 0–100. Não é classe metodológica nem quintil persistido. */
export function icttV2FillColor(ictt: number | null | undefined): string {
  if (ictt == null || !Number.isFinite(ictt)) return ICT_CHOROPLETH.noData
  const t = Math.min(1, Math.max(0, ictt / 100))
  const scale = ICT_CHOROPLETH.scale
  const pos = t * (scale.length - 1)
  const index = Math.min(scale.length - 2, Math.floor(pos))
  const frac = pos - index
  const from = hexToRgb(scale[index])
  const to = hexToRgb(scale[index + 1])
  const r = Math.round(lerp(from[0], to[0], frac))
  const g = Math.round(lerp(from[1], to[1], frac))
  const b = Math.round(lerp(from[2], to[2], frac))
  return `rgb(${r}, ${g}, ${b})`
}

export const ICTT_V2_MAP_STROKE = {
  neutral: ICT_CHOROPLETH.neutralStroke,
  hover: ICT_CHOROPLETH.hoverStroke,
  selected: '#184890',
  noData: ICT_CHOROPLETH.noData,
} as const
