import { useEffect, useState } from 'react'
import type { Scope } from '../../api/types'
import type { GeoJsonFeatureCollection } from '../../lib/geoJoin'
import { fetchBackgroundGeoCached, getCachedBackgroundGeo } from './geoBackgroundCache'

export function useTerritoryGeoJson(scope: Scope) {
  const [geoJson, setGeoJson] = useState<GeoJsonFeatureCollection | null>(
    () => getCachedBackgroundGeo(scope),
  )
  const [loadedScope, setLoadedScope] = useState<Scope | null>(() =>
    getCachedBackgroundGeo(scope) ? scope : null,
  )
  const [geoError, setGeoError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const cached = getCachedBackgroundGeo(scope)
    if (cached) {
      setGeoJson(cached)
      setLoadedScope(scope)
      setGeoError(null)
      return () => {
        cancelled = true
      }
    }

    void fetchBackgroundGeoCached(scope).then((data) => {
      if (cancelled) return
      if (data) {
        setGeoJson(data)
        setGeoError(null)
      } else {
        setGeoJson(null)
        setGeoError('Falha ao carregar GeoJSON')
      }
      setLoadedScope(scope)
    })

    return () => {
      cancelled = true
    }
  }, [scope])

  const geoLoading = getCachedBackgroundGeo(scope) == null && loadedScope !== scope

  return { geoJson, geoLoading, geoError }
}
