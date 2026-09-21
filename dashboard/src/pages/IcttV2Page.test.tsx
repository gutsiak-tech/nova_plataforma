import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { IcttV2MunicipalityPublic } from '../api/icttV2Types'

vi.mock('../components/icttV2/IcttV2Map', () => ({
  IcttV2Map: ({ rows }: { rows: IcttV2MunicipalityPublic[] }) => (
    <div data-testid="ictt-v2-map">{rows.length} municípios no mapa</div>
  ),
}))

vi.mock('../components/map/useTerritoryGeoJson', () => ({
  useTerritoryGeoJson: () => ({ geoJson: { type: 'FeatureCollection', features: [] }, geoLoading: false, geoError: null }),
}))

const foz: IcttV2MunicipalityPublic = {
  competencia: '2026-04',
  codigo_municipio: '4108304',
  municipio: 'Foz do Iguaçu',
  calculavel: true,
  reliability_class: 'higher',
  admissoes: 463,
  desligamentos: 100,
  saldo: 363,
  absorcao: 78.15786276089538,
  remuneracao: 90.88963668433047,
  qualidade_contratual: 68.68250539956804,
  diversificacao: 93.72877147518022,
  ictt_v2: 82.86469407999354,
  rank_n10: 1,
  rank_n20: 1,
}

const guarapuava: IcttV2MunicipalityPublic = {
  ...foz,
  codigo_municipio: '4109401',
  municipio: 'Guarapuava',
  reliability_class: 'reduced',
  admissoes: 16,
  ictt_v2: 59.70914772764678,
  rank_n10: 37,
  rank_n20: null,
}

function municipalityList() {
  const others = Array.from({ length: 397 }, (_, i) => ({
    ...foz,
    codigo_municipio: String(4100000 + i).padStart(7, '0'),
    municipio: i === 0 ? 'Cidade Gaúcha' : `Municipio ${i}`,
    calculavel: i < 57,
    reliability_class: (i < 37 ? 'higher' : i < 57 ? 'reduced' : null) as IcttV2MunicipalityPublic['reliability_class'],
    ictt_v2: i < 57 ? 40 : null,
    rank_n10: i < 57 ? i + 2 : null,
    rank_n20: i < 37 ? i + 2 : null,
    admissoes: i < 37 ? 25 : i < 57 ? 12 : 3,
  }))
  const rows = [foz, guarapuava, ...others]
  return {
    meta: {
      competencia: '2026-04',
      methodology_version: '2.0',
      normalization_version: 'NORM_B.2026-01_2026-04.N233',
      n_municipalities: 399,
      n_calculable: 59,
      reliability: null,
    },
    data: rows,
  }
}

const rankingN20 = {
  meta: { ...municipalityList().meta, universe: 'n20' as const, n_ranked: 39 },
  data: [foz, ...municipalityList().data.filter((row) => row.rank_n20 != null && row.codigo_municipio !== foz.codigo_municipio)].slice(0, 39),
}

const rankingN10 = {
  meta: { ...municipalityList().meta, universe: 'n10' as const, n_ranked: 59 },
  data: [foz, guarapuava, ...municipalityList().data.filter((row) => row.rank_n10 != null && row.codigo_municipio !== foz.codigo_municipio && row.codigo_municipio !== guarapuava.codigo_municipio)].slice(0, 59),
}

vi.mock('../api/icttV2', () => ({
  fetchIcttV2Competencias: vi.fn(),
  fetchIcttV2Methodology: vi.fn(),
  fetchIcttV2Municipalities: vi.fn(),
  fetchIcttV2MunicipalityDetail: vi.fn(),
  fetchIcttV2Ranking: vi.fn(),
}))

import {
  fetchIcttV2Competencias,
  fetchIcttV2Methodology,
  fetchIcttV2Municipalities,
  fetchIcttV2MunicipalityDetail,
  fetchIcttV2Ranking,
} from '../api/icttV2'
import { IcttV2Page } from './IcttV2Page'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('IcttV2Page', () => {
  beforeEach(() => {
    vi.mocked(fetchIcttV2Competencias).mockResolvedValue({
      methodology_version: '2.0',
      competencias: ['2026-01', '2026-02', '2026-03', '2026-04'],
    })
    vi.mocked(fetchIcttV2Methodology).mockResolvedValue({
      methodology_version: '2.0',
      normalization_version: 'NORM_B.2026-01_2026-04.N233',
      reference_scope: 'PR',
      reference_period: { start: '2026-01', end: '2026-04' },
      eligibility: { min_admissions: 10, higher_reliability_from: 20 },
      dimensions: [
        { key: 'absorcao', weight: 0.25 },
        { key: 'remuneracao', weight: 0.25 },
        { key: 'qualidade_contratual', weight: 0.25 },
        { key: 'diversificacao', weight: 0.25 },
      ],
    })
    vi.mocked(fetchIcttV2Municipalities).mockResolvedValue(municipalityList())
    vi.mocked(fetchIcttV2Ranking).mockImplementation(async (_competencia, universe) =>
      universe === 'n10' ? rankingN10 : rankingN20,
    )
    vi.mocked(fetchIcttV2MunicipalityDetail).mockResolvedValue({
      meta: municipalityList().meta,
      data: {
        ...foz,
        a_volume_score: 70,
        a_saldo: 80,
        n_salarios_r4: 10,
        salario_mediano_r4_municipio: 2000,
        salario_mediano_r4_pr: 1800,
        salario_relativo_r4: 1.1,
        perc_parcial_admissao: 1,
        perc_intermitente_admissao: 2,
        q_parcial: 90,
        q_intermitente: 80,
        shannon_cbo: 1,
        shannon_subclasse: 1,
        shannon_secao: 1,
        d_cbo: 1,
        d_subclasse: 1,
        d_secao: 1,
      },
    })
  })

  it('carrega competências e seleciona a mais recente', async () => {
    render(<IcttV2Page />)
    await waitFor(() => expect(screen.getByLabelText('Competência abr/26')).toBeTruthy())
    expect(screen.getByLabelText('Competência abr/26').getAttribute('aria-pressed')).toBe('true')
    expect(fetchIcttV2Municipalities).toHaveBeenCalledWith('2026-04', expect.anything())
  })

  it('mostra 399 municípios e 59 calculáveis, com mapa mesmo se ranking falhar', async () => {
    vi.mocked(fetchIcttV2Ranking).mockRejectedValueOnce(new Error('Erro de ranking'))
    render(<IcttV2Page />)
    await waitFor(() => expect(screen.getByTestId('ictt-v2-map').textContent).toContain('399'))
    expect(screen.getByText('Municípios da malha')).toBeTruthy()
    await waitFor(() => expect(screen.getByText('Não foi possível carregar o ranking.')).toBeTruthy())
    expect(screen.getByTestId('ictt-v2-map')).toBeTruthy()
  })

  it('troca universo n20 para n10 e aplica fingerprints', async () => {
    render(<IcttV2Page />)
    await waitFor(() => expect(screen.getByText('Foz do Iguaçu')).toBeTruthy())
    expect(screen.getByText('82,9')).toBeTruthy()
    expect(screen.queryByText('Guarapuava')).toBeNull()
    fireEvent.click(screen.getByRole('radio', { name: 'N ≥ 10' }))
    await waitFor(() => expect(screen.getByText('Guarapuava')).toBeTruthy())
    expect(fetchIcttV2Ranking).toHaveBeenCalledWith('2026-04', 'n10', expect.anything())
  })

  it('mantém Paraná no recorte e um único seletor de competência da V2', async () => {
    render(<IcttV2Page />)
    await waitFor(() => expect(screen.getByLabelText('Competência abr/26')).toBeTruthy())
    expect(screen.getByText(/Índice de Competitividade Territorial do Trabalho · Paraná/)).toBeTruthy()
    expect(screen.getAllByText('Competência ICTT v2')).toHaveLength(1)
    expect(screen.queryByLabelText('Selecionar competência')).toBeNull()
  })

  it('abre a metodologia em português com identificador técnico discreto', async () => {
    render(<IcttV2Page />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Metodologia' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Metodologia' }))
    expect(screen.getByText('Metodologia ICTT — versão 2.0')).toBeTruthy()
    expect(
      screen.getByText('Paraná · janeiro a abril de 2026 · municípios com pelo menos 10 admissões'),
    ).toBeTruthy()
    expect(screen.getByText('Identificador técnico: NORM_B.2026-01_2026-04.N233')).toBeTruthy()
  })

  it('abre Foz no detalhe com ICTT 82,9 e maior robustez', async () => {
    render(<IcttV2Page />)
    await waitFor(() => expect(screen.getByText('Foz do Iguaçu')).toBeTruthy())
    fireEvent.click(screen.getByText('Foz do Iguaçu'))
    await waitFor(() => expect(screen.getByText('Maior robustez.')).toBeTruthy())
    expect(screen.getAllByText('82,9').length).toBeGreaterThan(1)
    expect(screen.getByText(/Código IBGE 4108304/)).toBeTruthy()
  })
})
