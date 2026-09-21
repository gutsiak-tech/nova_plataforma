import { useCallback, useEffect, useMemo, type ReactNode } from 'react'
import { GeoJSON, MapContainer, useMap } from 'react-leaflet'
import type { Layer, PathOptions } from 'leaflet'
import L from 'leaflet'
import type { Feature, GeoJsonObject } from 'geojson'
import type { IcttV2MunicipalityPublic } from '../../api/icttV2Types'
import { type GeoFeatureProperties, type GeoJsonFeatureCollection } from '../../lib/geoJoin'
import { Card } from '../ui/Card'
import { MapPlaceholder } from '../map/MapPlaceholder'
import { FIT_BOUNDS_PADDING, MAP_FALLBACK } from '../map/mapTerritoryCopy'
import { theme } from '../../lib/theme'
import { ICTT_V2_MAP_STROKE, icttV2FillColor } from './icttV2Choropleth'
import { IcttV2MapLegend } from './IcttV2MapLegend'
import { buildIcttV2RowIndex, lookupIcttV2Row } from './icttV2MapIndex'
import { buildIcttV2TooltipHtml } from './icttV2Tooltip'

const MAP_CANVAS_CLASS = 'territory-map-canvas h-[360px] w-full md:h-[500px]'

type IcttV2MapSnapshot = {
  rows: IcttV2MunicipalityPublic[]
  competenciaLabel: string
  geoJson: GeoJsonFeatureCollection
}

function FitPrBounds({ data }: { data: GeoJsonFeatureCollection }) {
  const map = useMap()
  useEffect(() => {
    const bounds = L.geoJSON(data as GeoJsonObject).getBounds()
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: FIT_BOUNDS_PADDING.pr, animate: false })
    }
  }, [data, map])
  return null
}

function FocusSelected({
  geoJson,
  selectedCodigo,
}: {
  geoJson: GeoJsonFeatureCollection
  selectedCodigo: string | null
}) {
  const map = useMap()
  useEffect(() => {
    if (!selectedCodigo) return
    const feature = geoJson.features.find((item) => {
      const code = String(item.properties.cod_municipio ?? item.properties.CD_MUN ?? '').trim()
      return code === selectedCodigo
    })
    if (!feature) return
    const bounds = L.geoJSON(feature as GeoJsonObject).getBounds()
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [56, 56], maxZoom: 10, animate: true })
    }
  }, [geoJson, map, selectedCodigo])
  return null
}

function MapPanelShell({
  competenciaLabel,
  refreshing,
  children,
  overlay,
}: {
  competenciaLabel: string
  refreshing?: boolean
  children: ReactNode
  overlay?: ReactNode
}) {
  return (
    <Card enter={false} hover={false} className="overflow-hidden p-0">
      <div className={`space-y-1.5 ${theme.mapPanel.headerBorderClass} px-4 py-3 sm:px-5`}>
        <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
          <h3 className={theme.mapPanel.titleClass}>Mapa ICTT v2.0 · Paraná</h3>
          <p className={theme.mapPanel.metaClass}>Competência {competenciaLabel}</p>
        </div>
      </div>
      <div className="relative">
        <div className={MAP_CANVAS_CLASS}>{children}</div>
        {overlay}
        {refreshing ? (
          <div
            className="pointer-events-none absolute inset-0 z-10 bg-white/10 transition-opacity duration-200"
            aria-hidden
          />
        ) : null}
        <div className="px-3 pb-3 pt-4 sm:px-5">
          <div className={theme.mapPanel.legendOverlayClass}>
            <IcttV2MapLegend />
          </div>
        </div>
      </div>
    </Card>
  )
}

function IcttV2MapCanvas({
  snapshot,
  selectedCodigo,
  onSelect,
}: {
  snapshot: IcttV2MapSnapshot
  selectedCodigo: string | null
  onSelect: (codigoMunicipio: string) => void
}) {
  const { rows, geoJson } = snapshot
  const index = useMemo(() => buildIcttV2RowIndex(rows), [rows])

  const styleFeature = useCallback(
    (feature?: Feature): PathOptions => {
      const properties = (feature?.properties ?? {}) as GeoFeatureProperties
      const row = lookupIcttV2Row(properties, index)
      const selected = row?.codigo_municipio === selectedCodigo
      return {
        fillColor: icttV2FillColor(row?.calculavel ? row.ictt_v2 : null),
        fillOpacity: row?.calculavel ? 0.88 : 0.55,
        color: selected ? ICTT_V2_MAP_STROKE.selected : ICTT_V2_MAP_STROKE.neutral,
        weight: selected ? 2.4 : 1.15,
      }
    },
    [index, selectedCodigo],
  )

  const onEachFeature = useCallback(
    (feature: Feature, layer: Layer) => {
      const properties = (feature.properties ?? {}) as GeoFeatureProperties
      const row = lookupIcttV2Row(properties, index)
      const baseStyle = styleFeature(feature)
      layer.bindTooltip(buildIcttV2TooltipHtml(properties, row), {
        sticky: true,
        opacity: 0.98,
        className: 'territory-map-tooltip territory-map-tooltip--ict',
      })
      layer.on('mouseover', () => {
        ;(layer as L.Path).setStyle({
          ...baseStyle,
          color: ICTT_V2_MAP_STROKE.hover,
          weight: (baseStyle.weight ?? 1) + 0.6,
        })
      })
      layer.on('mouseout', () => {
        ;(layer as L.Path).setStyle(styleFeature(feature))
      })
      layer.on('click', () => {
        if (row) onSelect(row.codigo_municipio)
      })
    },
    [index, onSelect, styleFeature],
  )

  return (
    <MapContainer
      center={[-24.5, -51.5]}
      zoom={7}
      className="h-full w-full rounded-none"
      scrollWheelZoom={false}
      attributionControl={false}
      zoomControl={false}
      zoomSnap={0.25}
      zoomDelta={0.25}
    >
      <FitPrBounds data={geoJson} />
      <FocusSelected geoJson={geoJson} selectedCodigo={selectedCodigo} />
      <GeoJSON
        key={`${snapshot.competenciaLabel}:${selectedCodigo ?? 'none'}`}
        data={geoJson as GeoJsonObject}
        style={styleFeature}
        onEachFeature={onEachFeature}
      />
    </MapContainer>
  )
}

type IcttV2MapProps = {
  rows: IcttV2MunicipalityPublic[]
  competenciaLabel: string
  geoJson: GeoJsonFeatureCollection | null
  geoLoading: boolean
  geoError: string | null
  refreshing?: boolean
  selectedCodigo: string | null
  onSelect: (codigoMunicipio: string) => void
}

export function IcttV2Map({
  rows,
  competenciaLabel,
  geoJson,
  geoLoading,
  geoError,
  refreshing = false,
  selectedCodigo,
  onSelect,
}: IcttV2MapProps) {
  const snapshot =
    geoJson != null && !geoError && rows.length > 0
      ? { rows, competenciaLabel, geoJson }
      : null

  if (!snapshot) {
    if (geoError || (!geoLoading && !geoJson)) {
      return <MapPlaceholder message={MAP_FALLBACK.geoError} />
    }
    return (
      <MapPanelShell competenciaLabel="—">
        <div className="flex h-full flex-col items-center justify-center gap-2 px-6">
          <div className={theme.mapPanel.loadingSpinnerClass} />
          <p className={theme.mapPanel.loadingMessageClass}>{MAP_FALLBACK.geoLoading}</p>
        </div>
      </MapPanelShell>
    )
  }

  return (
    <MapPanelShell
      competenciaLabel={competenciaLabel}
      refreshing={refreshing}
      overlay={
        geoLoading ? (
          <div className="pointer-events-none absolute inset-0 z-[5] flex items-center justify-center bg-white/20">
            <div className={theme.mapPanel.loadingSpinnerClass} />
          </div>
        ) : null
      }
    >
      <IcttV2MapCanvas snapshot={snapshot} selectedCodigo={selectedCodigo} onSelect={onSelect} />
    </MapPanelShell>
  )
}
