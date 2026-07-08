/** Cores do choropleth ICTT (escala 0–100 + sem dados). */
export const ICT_CHOROPLETH = {
  noData: '#cbd5e1',
  neutralStroke: 'rgba(24, 72, 144, 0.38)',
  hoverStroke: '#8858A8',
  /** Baixo → alto ICTT. */
  scale: ['#E8F4FC', '#9BC9E8', '#4A90C4', '#194E93', '#0B2D52'] as const,
} as const

export function icttFillColor(ictt: number | null | undefined): string {
  if (ictt == null || !Number.isFinite(ictt)) return ICT_CHOROPLETH.noData
  const ratio = Math.min(1, Math.max(0, ictt / 100))
  const band =
    ratio >= 0.8 ? 4 : ratio >= 0.6 ? 3 : ratio >= 0.4 ? 2 : ratio >= 0.2 ? 1 : 0
  return ICT_CHOROPLETH.scale[band]
}
