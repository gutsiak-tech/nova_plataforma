import { GOLD_COLUMNS } from '../api/goldColumns'
import type { GoldRow, IcttMunicipio } from '../api/types'
import { normalizeGeoKey, type GeoFeatureProperties } from './geoJoin'

export type IcttMetricRow = {
  municipio: string
  municipio_norm: string
  ICTT: number | null
  tooltip_resumo: string
  classe_ictt: string
  status_calculo: string
}

export type IcttKpis = {
  calculatedCount: number
  meanIctt: number | null
  topMunicipio: string | null
  topIctt: number | null
  insufficientCount: number
}

export function toFiniteNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

export function isIcttCalculated(row: GoldRow): boolean {
  return toFiniteNumber(row[GOLD_COLUMNS.ICTT]) !== null
}

export function computeIcttKpis(rows: GoldRow[]): IcttKpis {
  const calculated = rows.filter(isIcttCalculated)
  const insufficient = rows.length - calculated.length

  let meanIctt: number | null = null
  if (calculated.length > 0) {
    const sum = calculated.reduce(
      (acc, row) => acc + (toFiniteNumber(row[GOLD_COLUMNS.ICTT]) ?? 0),
      0,
    )
    meanIctt = sum / calculated.length
  }

  let topMunicipio: string | null = null
  let topIctt: number | null = null
  for (const row of calculated) {
    const value = toFiniteNumber(row[GOLD_COLUMNS.ICTT])
    if (value === null) continue
    if (topIctt === null || value > topIctt) {
      topIctt = value
      topMunicipio = String(row[GOLD_COLUMNS.MUNICIPIO] ?? '—')
    }
  }

  return {
    calculatedCount: calculated.length,
    meanIctt,
    topMunicipio,
    topIctt,
    insufficientCount: insufficient,
  }
}

export function buildTopIcttRanking(rows: GoldRow[], limit = 20): GoldRow[] {
  return rows
    .filter(isIcttCalculated)
    .slice()
    .sort(
      (a, b) =>
        Number(a[GOLD_COLUMNS.RANKING_ICTT] ?? Number.MAX_SAFE_INTEGER) -
        Number(b[GOLD_COLUMNS.RANKING_ICTT] ?? Number.MAX_SAFE_INTEGER),
    )
    .slice(0, limit)
}

export function buildIcttMetricIndex(rows: GoldRow[]): Map<string, IcttMetricRow> {
  const index = new Map<string, IcttMetricRow>()
  for (const row of rows) {
    const normRaw = row[GOLD_COLUMNS.MUNICIPIO_NORM] ?? row[GOLD_COLUMNS.MUNICIPIO]
    const norm = normalizeGeoKey(String(normRaw ?? ''))
    if (!norm) continue

    const ictt = toFiniteNumber(row[GOLD_COLUMNS.ICTT])

    index.set(norm, {
      municipio: String(row[GOLD_COLUMNS.MUNICIPIO] ?? ''),
      municipio_norm: norm,
      ICTT: ictt,
      tooltip_resumo: String(row[GOLD_COLUMNS.TOOLTIP_RESUMO] ?? ''),
      classe_ictt: String(row[GOLD_COLUMNS.CLASSE_ICTT] ?? ''),
      status_calculo: String(row[GOLD_COLUMNS.STATUS_CALCULO] ?? ''),
    })
  }
  return index
}

export function lookupIcttMetric(
  properties: GeoFeatureProperties,
  index: Map<string, IcttMetricRow>,
): IcttMetricRow | undefined {
  const fromProperty = properties.municipio_norm
  const key =
    fromProperty != null && String(fromProperty).trim()
      ? normalizeGeoKey(String(fromProperty))
      : normalizeGeoKey(String(properties.municipio ?? properties.NM_MUN ?? ''))
  if (!key) return undefined
  return index.get(key)
}

export function asIcttMunicipioRows(rows: GoldRow[]): IcttMunicipio[] {
  return rows as IcttMunicipio[]
}
