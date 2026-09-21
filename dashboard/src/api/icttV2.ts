import axios from 'axios'
import { http } from './http'
import type {
  IcttV2CompetenciasResponse,
  IcttV2MethodologyResponse,
  IcttV2MunicipalityDetailResponse,
  IcttV2MunicipalityListResponse,
  IcttV2RankingResponse,
  IcttV2RankingUniverse,
} from './icttV2Types'

export function readIcttV2ApiError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as
      | { error?: { message?: string; code?: string } }
      | undefined
    const message = payload?.error?.message
    if (typeof message === 'string' && message.trim()) return message.trim()
    if (error.response?.status === 404) {
      return 'Competência sem Gold ICTT v2 disponível.'
    }
    if (error.code === 'ERR_NETWORK' || error.response == null) {
      return 'API indisponível. Não foi possível carregar o ICTT v2.0.'
    }
  }
  return error instanceof Error && error.message ? error.message : fallback
}

async function getJson<T>(url: string, params?: Record<string, string>, signal?: AbortSignal): Promise<T> {
  try {
    const { data } = await http.get<T>(url, { params, signal })
    return data
  } catch (error: unknown) {
    throw new Error(readIcttV2ApiError(error, 'Falha ao consultar a API ICTT v2.0.'))
  }
}

export function fetchIcttV2Competencias(signal?: AbortSignal): Promise<IcttV2CompetenciasResponse> {
  return getJson<IcttV2CompetenciasResponse>('/api/ict/v2/competencias', undefined, signal)
}

export function fetchIcttV2Methodology(signal?: AbortSignal): Promise<IcttV2MethodologyResponse> {
  return getJson<IcttV2MethodologyResponse>('/api/ict/v2/methodology', undefined, signal)
}

export function fetchIcttV2Municipalities(
  competencia: string,
  signal?: AbortSignal,
): Promise<IcttV2MunicipalityListResponse> {
  return getJson<IcttV2MunicipalityListResponse>(
    '/api/ict/v2/municipalities',
    { competencia },
    signal,
  )
}

export function fetchIcttV2MunicipalityDetail(
  codigoMunicipio: string,
  competencia: string,
  signal?: AbortSignal,
): Promise<IcttV2MunicipalityDetailResponse> {
  return getJson<IcttV2MunicipalityDetailResponse>(
    `/api/ict/v2/municipalities/${encodeURIComponent(codigoMunicipio)}`,
    { competencia },
    signal,
  )
}

export function fetchIcttV2Ranking(
  competencia: string,
  universe: IcttV2RankingUniverse,
  signal?: AbortSignal,
): Promise<IcttV2RankingResponse> {
  return getJson<IcttV2RankingResponse>(
    '/api/ict/v2/ranking',
    { competencia, universe },
    signal,
  )
}
