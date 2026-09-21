import { describe, expect, it } from 'vitest'
import {
  DEFAULT_RANKING_UNIVERSE,
  formatIcttHeadline,
  formatIcttScore,
  numericOrNull,
  pickLatestCompetencia,
  rankingUniverseQuery,
  reliabilityLabel,
  summarizeMunicipalities,
} from './icttV2View'
import type { IcttV2MunicipalityPublic } from '../api/icttV2Types'

function row(
  partial: Partial<IcttV2MunicipalityPublic> & Pick<IcttV2MunicipalityPublic, 'codigo_municipio' | 'municipio'>,
): IcttV2MunicipalityPublic {
  return {
    competencia: '2026-04',
    calculavel: false,
    reliability_class: null,
    admissoes: 0,
    desligamentos: 0,
    saldo: 0,
    absorcao: null,
    remuneracao: null,
    qualidade_contratual: null,
    diversificacao: null,
    ictt_v2: null,
    rank_n10: null,
    rank_n20: null,
    ...partial,
  }
}

describe('icttV2View', () => {
  it('seleciona a competência mais recente disponível', () => {
    expect(pickLatestCompetencia(['2026-01', '2026-03', '2026-02', '2026-04'])).toBe('2026-04')
    expect(pickLatestCompetencia([])).toBeNull()
  })

  it('não transforma null em zero', () => {
    expect(numericOrNull(null)).toBeNull()
    expect(numericOrNull(undefined)).toBeNull()
    expect(numericOrNull(Number.NaN)).toBeNull()
    expect(formatIcttScore(null)).toBeNull()
    expect(formatIcttHeadline(null)).toBe('ICTT não calculável')
    expect(formatIcttHeadline(0)).toBe('0,0000')
  })

  it('resume abril com 399 / 59 / reduced / higher', () => {
    const rows = [
      ...Array.from({ length: 39 }, (_, i) =>
        row({
          codigo_municipio: String(4100000 + i),
          municipio: `H${i}`,
          calculavel: true,
          reliability_class: 'higher',
          ictt_v2: 80,
          admissoes: 25,
        }),
      ),
      ...Array.from({ length: 20 }, (_, i) =>
        row({
          codigo_municipio: String(4110000 + i),
          municipio: `R${i}`,
          calculavel: true,
          reliability_class: 'reduced',
          ictt_v2: 50,
          admissoes: 12,
        }),
      ),
      ...Array.from({ length: 340 }, (_, i) =>
        row({
          codigo_municipio: String(4120000 + i),
          municipio: `N${i}`,
          calculavel: false,
          ictt_v2: null,
          admissoes: 3,
        }),
      ),
    ]
    const summary = summarizeMunicipalities(rows, {
      competencia: '2026-04',
      methodology_version: '2.0',
      normalization_version: 'NORM_B.2026-01_2026-04.N233',
      n_municipalities: 399,
      n_calculable: 59,
      reliability: null,
    })
    expect(rows).toHaveLength(399)
    expect(summary.nMunicipalities).toBe(399)
    expect(summary.nCalculable).toBe(59)
    expect(summary.nReduced).toBe(20)
    expect(summary.nHigher).toBe(39)
  })

  it('rotula confiabilidade sem linguagem absoluta', () => {
    expect(reliabilityLabel('reduced')).toBe('Confiabilidade reduzida')
    expect(reliabilityLabel('higher')).toBe('Maior robustez')
    expect(reliabilityLabel(null)).toBeNull()
  })

  it('mapeia universo de ranking sem official_rank', () => {
    expect(DEFAULT_RANKING_UNIVERSE).toBe('n20')
    expect(rankingUniverseQuery('n10')).toBe('n10')
    expect(rankingUniverseQuery('n20')).toBe('n20')
  })
})
