/** Cores compartilhadas entre choropleth e legenda do mapa territorial (ORGMIGRA). */
export const MAP_CHOROPLETH = {
  noData: '#475569',
  neutral: '#94a3b8',
  positiveMid: '#65B244',
  negativeMid: '#e11d48',
  /** Saldo positivo: baixo → elevado (amarelo → verde → azul). */
  positive: ['#EAF5E6', '#F9BD2C', '#65B244', '#194E93'] as const,
  /** Saldo negativo: escala rose discreta (semântica preservada). */
  negative: ['#fecdd3', '#fb7185', '#e11d48', '#be123c'] as const,
  stroke: 'rgba(24, 72, 144, 0.38)',
  accent: {
    hover: '#8C5DAC',
    hoverStroke: '#8858A8',
  },
} as const

export function saldoFillColor(saldo: number | undefined, maxAbs: number): string {
  if (saldo == null || !Number.isFinite(saldo)) return MAP_CHOROPLETH.noData
  if (saldo === 0 || maxAbs <= 0) return MAP_CHOROPLETH.neutral
  const ratio = Math.min(1, Math.abs(saldo) / maxAbs)
  const band = ratio > 0.75 ? 3 : ratio > 0.5 ? 2 : ratio > 0.25 ? 1 : 0
  return saldo > 0 ? MAP_CHOROPLETH.positive[band] : MAP_CHOROPLETH.negative[band]
}
