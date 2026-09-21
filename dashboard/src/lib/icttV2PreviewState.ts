import type {
  IcttV2MunicipalityListResponse,
  IcttV2RankingResponse,
} from '../api/icttV2Types'

export type IcttV2PreviewDataState = {
  municipalities: IcttV2MunicipalityListResponse | null
  municipalitiesError: string | null
  ranking: IcttV2RankingResponse | null
  rankingError: string | null
}

export const EMPTY_ICTT_V2_PREVIEW_STATE: IcttV2PreviewDataState = {
  municipalities: null,
  municipalitiesError: null,
  ranking: null,
  rankingError: null,
}

/** Falha de ranking não limpa o mapa já carregado. */
export function applyRankingResult(
  state: IcttV2PreviewDataState,
  result: { ok: true; payload: IcttV2RankingResponse } | { ok: false; error: string },
): IcttV2PreviewDataState {
  if (result.ok) {
    return { ...state, ranking: result.payload, rankingError: null }
  }
  return {
    ...state,
    ranking: null,
    rankingError: result.error,
  }
}

export function applyMunicipalitiesResult(
  state: IcttV2PreviewDataState,
  result:
    | { ok: true; payload: IcttV2MunicipalityListResponse }
    | { ok: false; error: string },
): IcttV2PreviewDataState {
  if (result.ok) {
    return { ...state, municipalities: result.payload, municipalitiesError: null }
  }
  return {
    ...state,
    municipalities: null,
    municipalitiesError: result.error,
  }
}

export function mapSurvivesRankingFailure(state: IcttV2PreviewDataState): boolean {
  return state.municipalities != null && state.municipalities.data.length > 0
}
