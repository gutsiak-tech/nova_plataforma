import type { IcttMetricRow } from '../../lib/ictMetrics'
import type { GeoFeatureProperties } from '../../lib/geoJoin'

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function featureTitle(properties: GeoFeatureProperties, metric?: IcttMetricRow): string {
  return String(
    properties.municipio ?? properties.NM_MUN ?? metric?.municipio ?? 'Município',
  )
}

export function buildIcttTooltipHtml(
  properties: GeoFeatureProperties,
  metric: IcttMetricRow | undefined,
): string {
  const tooltip = metric?.tooltip_resumo?.trim()
  if (tooltip) {
    const safe = escapeHtml(tooltip)
    return `<div class="territory-map-tooltip__body territory-map-tooltip__body--ictt">${safe}</div>`
  }

  const title = escapeHtml(featureTitle(properties, metric))
  return `
    <div class="territory-map-tooltip__body territory-map-tooltip__body--ictt">
      <div class="territory-map-tooltip__title">${title}</div>
      <div class="territory-map-tooltip__empty">Sem dados ICT para este município.</div>
    </div>
  `
}
