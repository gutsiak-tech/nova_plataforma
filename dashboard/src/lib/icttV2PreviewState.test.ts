import { describe, expect, it } from 'vitest'
import {
  applyMunicipalitiesResult,
  applyRankingResult,
  EMPTY_ICTT_V2_PREVIEW_STATE,
  mapSurvivesRankingFailure,
} from './icttV2PreviewState'
import type { IcttV2MunicipalityListResponse, IcttV2RankingResponse } from '../api/icttV2Types'

const municipalities: IcttV2MunicipalityListResponse = {
  meta: {
    competencia: '2026-04',
    methodology_version: '2.0',
    normalization_version: 'NORM_B',
    n_municipalities: 399,
    n_calculable: 59,
    reliability: null,
  },
  data: [
    {
      competencia: '2026-04',
      codigo_municipio: '4108304',
      municipio: 'Foz do Iguaçu',
      calculavel: true,
      reliability_class: 'higher',
      admissoes: 463,
      desligamentos: 0,
      saldo: 0,
      absorcao: 78.16,
      remuneracao: 90.89,
      qualidade_contratual: 68.68,
      diversificacao: 93.73,
      ictt_v2: 82.86469407999354,
      rank_n10: 1,
      rank_n20: 1,
    },
  ],
}

const ranking: IcttV2RankingResponse = {
  meta: { ...municipalities.meta, universe: 'n20', n_ranked: 39 },
  data: municipalities.data,
}

describe('icttV2PreviewState', () => {
  it('mantém o mapa quando o ranking falha', () => {
    let state = applyMunicipalitiesResult(EMPTY_ICTT_V2_PREVIEW_STATE, {
      ok: true,
      payload: municipalities,
    })
    state = applyRankingResult(state, { ok: false, error: 'Erro de ranking' })
    expect(mapSurvivesRankingFailure(state)).toBe(true)
    expect(state.municipalities?.data).toHaveLength(1)
    expect(state.ranking).toBeNull()
    expect(state.rankingError).toBe('Erro de ranking')
  })

  it('preenche ranking n20 e n10 sem derrubar municípios', () => {
    let state = applyMunicipalitiesResult(EMPTY_ICTT_V2_PREVIEW_STATE, {
      ok: true,
      payload: municipalities,
    })
    state = applyRankingResult(state, { ok: true, payload: ranking })
    expect(state.ranking?.meta.n_ranked).toBe(39)
    expect(state.municipalities?.meta.n_municipalities).toBe(399)
  })
})
