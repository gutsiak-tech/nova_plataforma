import type { GeoFeatureProperties } from '../../lib/geoJoin'
import type { IcttV2MunicipalityPublic } from '../../api/icttV2Types'
import {
  formatIcttScore,
  formatOptionalNumber,
  reliabilityLabel,
} from '../../lib/icttV2View'

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function featureTitle(
  properties: GeoFeatureProperties,
  row?: IcttV2MunicipalityPublic,
): string {
  return String(properties.municipio ?? properties.NM_MUN ?? row?.municipio ?? 'Município')
}

function rowLine(label: string, value: string): string {
  return `<div class="territory-map-tooltip__row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`
}

export function buildIcttV2TooltipHtml(
  properties: GeoFeatureProperties,
  row: IcttV2MunicipalityPublic | undefined,
): string {
  const title = escapeHtml(featureTitle(properties, row))
  if (!row || !row.calculavel || row.ictt_v2 == null) {
    return `
      <div class="territory-map-tooltip__body territory-map-tooltip__body--ictt">
        <div class="territory-map-tooltip__title">${title}</div>
        <div class="territory-map-tooltip__empty">ICTT não calculável</div>
        <div class="territory-map-tooltip__meta">Menos de 10 admissões na competência</div>
      </div>
    `
  }

  const ictt = formatIcttScore(row.ictt_v2, 1) ?? 'ICTT não calculável'
  const reliability = reliabilityLabel(row.reliability_class) ?? '—'
  return `
    <div class="territory-map-tooltip__body territory-map-tooltip__body--ictt">
      <div class="territory-map-tooltip__title">${title}</div>
      ${rowLine('ICTT', ictt)}
      ${rowLine('Absorção', formatOptionalNumber(row.absorcao, 1) ?? '—')}
      ${rowLine('Remuneração', formatOptionalNumber(row.remuneracao, 1) ?? '—')}
      ${rowLine('Qualidade contratual', formatOptionalNumber(row.qualidade_contratual, 1) ?? '—')}
      ${rowLine('Diversificação', formatOptionalNumber(row.diversificacao, 1) ?? '—')}
      ${rowLine('Confiabilidade', reliability)}
    </div>
  `
}
