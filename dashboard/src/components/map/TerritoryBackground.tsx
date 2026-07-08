import { useEffect, useMemo, type CSSProperties } from 'react'
import type { Scope } from '../../api/types'
import { useDisplaySelection } from '../../context/DisplaySelectionContext'
import { geoJsonToDecorativePaths, SVG_VIEW_BOX } from '../../lib/geoSvg'
import { BACKGROUND_MAP_CONFIG } from './territoryBackgroundConfig'
import { fetchBackgroundGeoCached } from './geoBackgroundCache'
import {
  getDecorativeTerritoryStyleByKey,
  type DecorativeTerritoryStyle,
} from './territoryBackgroundPalette'
import { useTerritoryBackgroundGeo } from './useTerritoryBackgroundGeo'

const SCOPES: Scope[] = ['br', 'pr', 'rmc']

/** Multiplicador base da opacidade final (M11D.2 — reforço fino). */
const BACKGROUND_LAYER_OPACITY_SCALE = 0.98

function layerTargetOpacity(scope: Scope): number {
  return BACKGROUND_MAP_CONFIG[scope].opacity * BACKGROUND_LAYER_OPACITY_SCALE
}

function ScopeBackgroundMapLayer({ scope }: { scope: Scope }) {
  const geoJson = useTerritoryBackgroundGeo(scope)
  const config = BACKGROUND_MAP_CONFIG[scope]

  const styledPaths = useMemo(() => {
    if (!geoJson) return []
    const paths = geoJsonToDecorativePaths(geoJson, {
      boundsOverride: config.boundsOverride,
      scope,
    })
    const styleByKey = new Map<string, DecorativeTerritoryStyle>()
    return paths.map((item) => {
      let style = styleByKey.get(item.territoryKey)
      if (!style) {
        style = getDecorativeTerritoryStyleByKey(item.territoryKey, scope)
        styleByKey.set(item.territoryKey, style)
      }
      return { ...item, style }
    })
  }, [geoJson, config.boundsOverride, scope])

  if (!styledPaths.length) return null

  const translateX = config.position.translateX ?? '0'
  const translateY = config.position.translateY ?? '0'

  const layerStyle = {
    '--territory-bg-opacity': layerTargetOpacity(scope),
  } as CSSProperties

  return (
    <div className="territory-background-map-layer" style={layerStyle} aria-hidden>
      <div
        className="territory-background-map"
        style={{
          width: config.position.width,
          height: config.position.height,
          transform: `translate(${translateX}, ${translateY}) scale(${config.cssScale})`,
        }}
      >
        <svg
          viewBox={SVG_VIEW_BOX}
          className="h-full w-full"
          preserveAspectRatio="xMidYMid meet"
          role="presentation"
        >
          <defs>
            <clipPath id={`territory-bg-clip-${scope}`}>
              <rect x="0" y="0" width="1000" height="1000" />
            </clipPath>
          </defs>
          <g clipPath={`url(#territory-bg-clip-${scope})`}>
            {styledPaths.map((item, index) => (
              <path
                key={`${item.territoryKey}-${item.featureIndex}-${index}`}
                d={item.d}
                fill={item.style.fill}
                stroke={item.style.stroke}
                fillOpacity={item.style.fillOpacity}
                strokeOpacity={item.style.strokeOpacity}
                strokeWidth={config.strokeWidth}
              />
            ))}
          </g>
        </svg>
      </div>
    </div>
  )
}

export function TerritoryBackground() {
  const { displayed } = useDisplaySelection()

  useEffect(() => {
    SCOPES.forEach((item) => {
      void fetchBackgroundGeoCached(item)
    })
  }, [])

  return (
    <div className="territory-background-layer hidden sm:block" aria-hidden>
      <div className="territory-background-stage">
        <ScopeBackgroundMapLayer scope={displayed.scope} />
      </div>
      <div className="territory-background-fade" />
    </div>
  )
}
