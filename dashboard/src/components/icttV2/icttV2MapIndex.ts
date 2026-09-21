import type { IcttV2MunicipalityPublic } from '../../api/icttV2Types'
import { normalizeGeoKey, type GeoFeatureProperties } from '../../lib/geoJoin'

export function buildIcttV2RowIndex(
  rows: IcttV2MunicipalityPublic[],
): { byCode: Map<string, IcttV2MunicipalityPublic>; byName: Map<string, IcttV2MunicipalityPublic> } {
  const byCode = new Map<string, IcttV2MunicipalityPublic>()
  const byName = new Map<string, IcttV2MunicipalityPublic>()
  for (const row of rows) {
    byCode.set(row.codigo_municipio, row)
    byName.set(normalizeGeoKey(row.municipio), row)
  }
  return { byCode, byName }
}

export function lookupIcttV2Row(
  properties: GeoFeatureProperties,
  index: ReturnType<typeof buildIcttV2RowIndex>,
): IcttV2MunicipalityPublic | undefined {
  const code = String(properties.cod_municipio ?? properties.CD_MUN ?? '').trim()
  if (code && index.byCode.has(code)) return index.byCode.get(code)
  const name = normalizeGeoKey(
    String(properties.municipio_norm ?? properties.municipio ?? properties.NM_MUN ?? ''),
  )
  return name ? index.byName.get(name) : undefined
}
