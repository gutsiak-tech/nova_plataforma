import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { IcttV2MunicipalityDetail } from '../../api/icttV2Types'
import { IcttV2DetailPanel } from './IcttV2DetailPanel'

afterEach(() => cleanup())

const base: IcttV2MunicipalityDetail = {
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
  a_volume_score: null,
  a_saldo: null,
  n_salarios_r4: null,
  salario_mediano_r4_municipio: null,
  salario_mediano_r4_pr: null,
  salario_relativo_r4: null,
  perc_parcial_admissao: null,
  perc_intermitente_admissao: null,
  q_parcial: null,
  q_intermitente: null,
  shannon_cbo: null,
  shannon_subclasse: null,
  shannon_secao: null,
  d_cbo: null,
  d_subclasse: null,
  d_secao: null,
}

describe('IcttV2DetailPanel', () => {
  it('mostra fingerprints de Foz e dimensões', () => {
    render(<IcttV2DetailPanel detail={base} error={null} />)
    expect(screen.getByText('Foz do Iguaçu')).toBeTruthy()
    expect(screen.getByText('82,8647')).toBeTruthy()
    expect(screen.getByText('Maior robustez.')).toBeTruthy()
    expect(screen.getByText('Absorção')).toBeTruthy()
    expect(screen.getByText('Remuneração')).toBeTruthy()
    expect(screen.getByText('Qualidade contratual')).toBeTruthy()
    expect(screen.getByText('Diversificação')).toBeTruthy()
  })

  it('explica município N<10 como não calculável', () => {
    render(
      <IcttV2DetailPanel
        detail={{
          ...base,
          codigo_municipio: '4110706',
          municipio: 'Irati',
          calculavel: false,
          reliability_class: null,
          ictt_v2: null,
          rank_n10: null,
          rank_n20: null,
          absorcao: null,
          remuneracao: null,
          qualidade_contratual: null,
          diversificacao: null,
          admissoes: 9,
        }}
        error={null}
      />,
    )
    expect(screen.getAllByText(/ICTT não calculável/).length).toBeGreaterThan(0)
    expect(
      screen.getByText(/menos de 10 admissões elegíveis para o critério de cálculo do ICTT/i),
    ).toBeTruthy()
    expect(screen.queryByText('0,0000')).toBeNull()
  })
})
