import { useCallback, useEffect, useMemo, useRef, type ReactNode } from 'react'
import { GeoJSON, MapContainer, useMap } from 'react-leaflet'
import type { Layer, PathOptions } from 'leaflet'
import L from 'leaflet'
import type { Feature, GeoJsonObject } from 'geojson'
import { GOLD_COLUMNS } from '../../api/goldColumns'
import type { GoldRow, Scope } from '../../api/types'
import {
  buildMetricIndex,
  joinGeoJsonWithMetrics,
  type GeoFeatureProperties,
  type GeoJsonFeatureCollection,
} from '../../lib/geoJoin'
import { Card } from '../ui/Card'
import { MapLegend } from './MapLegend'
import { MapPlaceholder } from './MapPlaceholder'
import { saldoFillColor, MAP_CHOROPLETH } from './mapChoropleth'
import { theme } from '../../lib/theme'
import {
  BRASIL_FRAMING_BOUNDS,
  FIT_BOUNDS_PADDING,
  MAP_FALLBACK,
} from './mapTerritoryCopy'
import { buildTerritoryTooltipHtml } from './mapTooltip'

const JOIN_PROPERTY_BY_SCOPE: Record<Scope, 'uf_norm' | 'municipio_norm'> = {
  br: 'uf_norm',
  pr: 'municipio_norm',
  rmc: 'municipio_norm',
}

const MAP_CANVAS_CLASS = 'territory-map-canvas h-[360px] w-full md:h-[500px]'

type MapSnapshot = {
  scope: Scope
  municipalityRows: GoldRow[]
  ufRows: GoldRow[] | null
  competenciaLabel: string
  geoJson: GeoJsonFeatureCollection
}

function FitBounds({
  data,
  scope,
}: {
  data: GeoJsonFeatureCollection
  scope: Scope
}) {
  const map = useMap()
  useEffect(() => {
    const bounds =
      scope === 'br'
        ? L.latLngBounds(BRASIL_FRAMING_BOUNDS)
        : L.geoJSON(data as GeoJsonObject).getBounds()
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: FIT_BOUNDS_PADDING[scope], animate: false })
    }
  }, [data, map, scope])
  return null
}

type TerritoryMapProps = {
  scope: Scope
  municipalityRows: GoldRow[]
  ufRows: GoldRow[] | null
  competenciaLabel: string
  geoJson: GeoJsonFeatureCollection | null
  geoLoading: boolean
  geoError: string | null
  refreshing?: boolean
}

function metricsReady(
  scope: Scope,
  municipalityRows: GoldRow[],
  ufRows: GoldRow[] | null,
): boolean {
  if (scope === 'br') {
    return ufRows !== null && ufRows.length > 0
  }
  return municipalityRows.length > 0
}

function MapPanelShell({
  competenciaLabel,
  refreshing,
  children,
  overlay,
  showLegend,
}: {
  competenciaLabel: string
  refreshing?: boolean
  children: ReactNode
  overlay?: ReactNode
  showLegend?: boolean
}) {
  return (
    <Card enter={false} hover={false} className="overflow-hidden p-0">
      <div className={`space-y-1.5 ${theme.mapPanel.headerBorderClass} px-4 py-3 sm:px-5`}>
        <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
          <h3 className={theme.mapPanel.titleClass}>Mapa territorial · saldo</h3>
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
        {showLegend !== false ? (
          <div className="px-3 pb-3 pt-4 sm:px-5">
            <div className={theme.mapPanel.legendOverlayClass}>
              <MapLegend />
            </div>
          </div>
        ) : null}
      </div>
    </Card>
  )
}

function MapInitialLoading({ message }: { message: string }) {
  return (
    <MapPanelShell competenciaLabel="—" showLegend={false}>
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6">
        <div className={theme.mapPanel.loadingSpinnerClass} />
        <p className={theme.mapPanel.loadingMessageClass}>{message}</p>
      </div>
    </MapPanelShell>
  )
}

function TerritoryMapCanvas({
  snapshot,
}: {
  snapshot: MapSnapshot
}) {
  const { scope, municipalityRows, ufRows, geoJson } = snapshot
  const metricRows = scope === 'br' ? (ufRows ?? []) : municipalityRows
  const metricKey = scope === 'br' ? GOLD_COLUMNS.UF : GOLD_COLUMNS.MUNICIPIO

  const metricIndex = useMemo(
    () => buildMetricIndex(metricRows, metricKey),
    [metricRows, metricKey],
  )

  const join = useMemo(
    () =>
      joinGeoJsonWithMetrics(geoJson, {
        joinProperty: JOIN_PROPERTY_BY_SCOPE[scope],
        metricIndex,
      }),
    [geoJson, scope, metricIndex],
  )

  const styleFeature = useCallback(
    (feature?: Feature): PathOptions => {
      const properties = (feature?.properties ?? {}) as GeoFeatureProperties
      const metric = join.lookup(properties)
      const fill = saldoFillColor(metric?.[GOLD_COLUMNS.SALDO], join.maxAbsSaldo)
      return {
        fillColor: fill,
        fillOpacity: metric ? 0.84 : 0.38,
        color: MAP_CHOROPLETH.stroke,
        weight: scope === 'br' ? 1 : 1.25,
      }
    },
    [join, scope],
  )

  const onEachFeature = useCallback(
    (feature: Feature, layer: Layer) => {
      const properties = (feature.properties ?? {}) as GeoFeatureProperties
      const metric = join.lookup(properties)
      const baseStyle = styleFeature(feature)
      layer.bindTooltip(buildTerritoryTooltipHtml(properties, scope, metric), {
        sticky: true,
        opacity: 0.98,
        className: 'territory-map-tooltip',
      })
      layer.on('mouseover', () => {
        ;(layer as L.Path).setStyle({
          ...baseStyle,
          color: MAP_CHOROPLETH.accent.hoverStroke,
          weight: (baseStyle.weight ?? 1) + 0.75,
        })
      })
      layer.on('mouseout', () => {
        ;(layer as L.Path).setStyle(baseStyle)
      })
    },
    [join, scope, styleFeature],
  )

  return (
    <MapContainer
      key={scope}
      center={[-15.5, -52]}
      zoom={4}
      className="h-full w-full rounded-none"
      scrollWheelZoom={false}
      attributionControl={false}
      zoomControl={false}
      zoomSnap={0.25}
      zoomDelta={0.25}
    >
      <FitBounds data={geoJson} scope={scope} />
      <GeoJSON
        key={scope}
        data={geoJson as GeoJsonObject}
        style={styleFeature}
        onEachFeature={onEachFeature}
      />
    </MapContainer>
  )
}

export function TerritoryMap({
  scope,
  municipalityRows,
  ufRows,
  competenciaLabel,
  geoJson,
  geoLoading,
  geoError,
  refreshing = false,
}: TerritoryMapProps) {
  const lastSnapshotRef = useRef<MapSnapshot | null>(null)

  const mapReady =
    geoJson != null &&
    !geoError &&
    metricsReady(scope, municipalityRows, ufRows)

  if (mapReady) {
    lastSnapshotRef.current = {
      scope,
      municipalityRows,
      ufRows,
      competenciaLabel,
      geoJson,
    }
  }

  const snapshot = mapReady ? lastSnapshotRef.current! : lastSnapshotRef.current

  if (!snapshot) {
    if (geoError || (!geoLoading && !geoJson)) {
      return <MapPlaceholder message={MAP_FALLBACK.geoError} />
    }
    if (scope === 'br' && ufRows !== null && ufRows.length === 0) {
      return <MapPlaceholder message={MAP_FALLBACK.noMetrics} />
    }
    if (scope !== 'br' && !municipalityRows.length && !geoLoading) {
      return <MapPlaceholder message={MAP_FALLBACK.noMetrics} />
    }
    if (geoLoading) {
      return <MapInitialLoading message={MAP_FALLBACK.geoLoading} />
    }
    if (scope === 'br' && ufRows === null) {
      return <MapInitialLoading message={MAP_FALLBACK.metricsLoading} />
    }
    return <MapInitialLoading message={MAP_FALLBACK.geoLoading} />
  }

  const label = mapReady ? competenciaLabel : snapshot.competenciaLabel

  return (
    <MapPanelShell
      competenciaLabel={label}
      refreshing={refreshing}
      overlay={
        !mapReady ? (
          <div className="pointer-events-none absolute inset-0 z-[5] flex items-center justify-center bg-white/20">
            <div className={theme.mapPanel.loadingSpinnerClass} />
          </div>
        ) : null
      }
    >
      <TerritoryMapCanvas snapshot={snapshot} />
    </MapPanelShell>
  )
}
