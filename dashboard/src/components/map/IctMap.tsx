import { useCallback, useEffect, useMemo, useRef, type ReactNode } from 'react'
import { GeoJSON, MapContainer, useMap } from 'react-leaflet'
import type { Layer, PathOptions } from 'leaflet'
import L from 'leaflet'
import type { Feature, GeoJsonObject } from 'geojson'
import type { GoldRow } from '../../api/types'
import type { GeoFeatureProperties, GeoJsonFeatureCollection } from '../../lib/geoJoin'
import {
  buildIcttMetricIndex,
  lookupIcttMetric,
  type IcttMetricRow,
} from '../../lib/ictMetrics'
import { Card } from '../ui/Card'
import { MapPlaceholder } from './MapPlaceholder'
import { FIT_BOUNDS_PADDING, MAP_FALLBACK } from './mapTerritoryCopy'
import { ICT_CHOROPLETH, icttFillColor } from './ictChoropleth'
import { buildIcttTooltipHtml } from './ictTooltip'
import { IctMapLegend } from './IctMapLegend'
import { theme } from '../../lib/theme'

const MAP_CANVAS_CLASS = 'territory-map-canvas h-[360px] w-full md:h-[500px]'

type IctMapSnapshot = {
  rows: GoldRow[]
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

function IctMapPanelShell({
  competenciaLabel,
  refreshing,
  children,
  overlay,
  showLegend = true,
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
          <h3 className={theme.mapPanel.titleClass}>Mapa ICT · Paraná</h3>
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
        {showLegend ? (
          <div className="px-3 pb-3 pt-4 sm:px-5">
            <div className={theme.mapPanel.legendOverlayClass}>
              <IctMapLegend />
            </div>
          </div>
        ) : null}
      </div>
    </Card>
  )
}

function IctMapInitialLoading({ message }: { message: string }) {
  return (
    <IctMapPanelShell competenciaLabel="—" showLegend={false}>
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6">
        <div className={theme.mapPanel.loadingSpinnerClass} />
        <p className={theme.mapPanel.loadingMessageClass}>{message}</p>
      </div>
    </IctMapPanelShell>
  )
}

function IctMapCanvas({ snapshot }: { snapshot: IctMapSnapshot }) {
  const { rows, geoJson } = snapshot

  const metricIndex = useMemo(() => buildIcttMetricIndex(rows), [rows])

  const lookup = useCallback(
    (properties: GeoFeatureProperties): IcttMetricRow | undefined =>
      lookupIcttMetric(properties, metricIndex),
    [metricIndex],
  )

  const styleFeature = useCallback(
    (feature?: Feature): PathOptions => {
      const properties = (feature?.properties ?? {}) as GeoFeatureProperties
      const metric = lookup(properties)
      const fill = icttFillColor(metric?.ICTT)
      return {
        fillColor: fill,
        fillOpacity: metric ? 0.86 : 0.72,
        color: ICT_CHOROPLETH.neutralStroke,
        weight: 1.25,
      }
    },
    [lookup],
  )

  const onEachFeature = useCallback(
    (feature: Feature, layer: Layer) => {
      const properties = (feature.properties ?? {}) as GeoFeatureProperties
      const metric = lookup(properties)
      const baseStyle = styleFeature(feature)
      layer.bindTooltip(buildIcttTooltipHtml(properties, metric), {
        sticky: true,
        opacity: 0.98,
        className: 'territory-map-tooltip territory-map-tooltip--ict',
      })
      layer.on('mouseover', () => {
        ;(layer as L.Path).setStyle({
          ...baseStyle,
          color: ICT_CHOROPLETH.hoverStroke,
          weight: (baseStyle.weight ?? 1) + 0.75,
        })
      })
      layer.on('mouseout', () => {
        ;(layer as L.Path).setStyle(baseStyle)
      })
    },
    [lookup, styleFeature],
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
      <GeoJSON data={geoJson as GeoJsonObject} style={styleFeature} onEachFeature={onEachFeature} />
    </MapContainer>
  )
}

type IctMapProps = {
  rows: GoldRow[]
  competenciaLabel: string
  geoJson: GeoJsonFeatureCollection | null
  geoLoading: boolean
  geoError: string | null
  refreshing?: boolean
}

export function IctMap({
  rows,
  competenciaLabel,
  geoJson,
  geoLoading,
  geoError,
  refreshing = false,
}: IctMapProps) {
  const lastSnapshotRef = useRef<IctMapSnapshot | null>(null)

  const mapReady = geoJson != null && !geoError && rows.length > 0

  if (mapReady) {
    lastSnapshotRef.current = {
      rows,
      competenciaLabel,
      geoJson,
    }
  }

  const snapshot = mapReady ? lastSnapshotRef.current! : lastSnapshotRef.current

  if (!snapshot) {
    if (geoError || (!geoLoading && !geoJson)) {
      return <MapPlaceholder message={MAP_FALLBACK.geoError} />
    }
    if (!rows.length && !geoLoading) {
      return <MapPlaceholder message={MAP_FALLBACK.noMetrics} />
    }
    if (geoLoading) {
      return <IctMapInitialLoading message={MAP_FALLBACK.geoLoading} />
    }
    return <IctMapInitialLoading message={MAP_FALLBACK.geoLoading} />
  }

  const label = mapReady ? competenciaLabel : snapshot.competenciaLabel

  return (
    <IctMapPanelShell
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
      <IctMapCanvas snapshot={snapshot} />
    </IctMapPanelShell>
  )
}
