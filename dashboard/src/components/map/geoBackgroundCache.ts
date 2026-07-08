import type { Scope } from '../../api/types'
import type { GeoJsonFeatureCollection } from '../../lib/geoJoin'
import { GEO_URL_BY_SCOPE } from './territoryBackgroundConfig'

const cache = new Map<Scope, GeoJsonFeatureCollection>()
const inflight = new Map<Scope, Promise<GeoJsonFeatureCollection | null>>()

export function getCachedBackgroundGeo(scope: Scope): GeoJsonFeatureCollection | null {
  return cache.get(scope) ?? null
}

export function fetchBackgroundGeoCached(scope: Scope): Promise<GeoJsonFeatureCollection | null> {
  const cached = cache.get(scope)
  if (cached) return Promise.resolve(cached)

  const pending = inflight.get(scope)
  if (pending) return pending

  const request = fetch(GEO_URL_BY_SCOPE[scope])
    .then(async (res) => {
      if (!res.ok) return null
      return (await res.json()) as GeoJsonFeatureCollection
    })
    .then((data) => {
      if (data) cache.set(scope, data)
      inflight.delete(scope)
      return data
    })
    .catch(() => {
      inflight.delete(scope)
      return null
    })

  inflight.set(scope, request)
  return request
}
