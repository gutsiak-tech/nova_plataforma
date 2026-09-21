import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { IcttV2MunicipalityPublic } from '../../api/icttV2Types'
import { IcttV2RankingPanel } from './IcttV2RankingPanel'

const foz: IcttV2MunicipalityPublic = {
  competencia: '2026-04',
  codigo_municipio: '4108304',
  municipio: 'Foz do Iguaçu',
  calculavel: true,
  reliability_class: 'higher',
  admissoes: 463,
  desligamentos: 100,
  saldo: 363,
  absorcao: 78.16,
  remuneracao: 90.89,
  qualidade_contratual: 68.68,
  diversificacao: 93.73,
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

afterEach(() => cleanup())

describe('IcttV2RankingPanel', () => {
  it('mostra Foz em rank 1 e Guarapuava no n10', () => {
    render(
      <IcttV2RankingPanel
        universe="n10"
        onUniverseChange={() => undefined}
        rows={[foz, guarapuava]}
        error={null}
        selectedCodigo={null}
        onSelect={() => undefined}
      />,
    )
    expect(screen.getByText('Foz do Iguaçu')).toBeTruthy()
    expect(screen.getByText('Guarapuava')).toBeTruthy()
    expect(screen.getByText('Confiabilidade reduzida')).toBeTruthy()
    expect(screen.getByText('Maior robustez')).toBeTruthy()
  })

  it('não lista Guarapuava no universo n20', () => {
    render(
      <IcttV2RankingPanel
        universe="n20"
        onUniverseChange={() => undefined}
        rows={[foz]}
        error={null}
        selectedCodigo={null}
        onSelect={() => undefined}
      />,
    )
    expect(screen.getByText('Foz do Iguaçu')).toBeTruthy()
    expect(screen.queryByText('Guarapuava')).toBeNull()
  })

  it('troca n20 -> n10 pelo seletor de universo', () => {
    const seen: string[] = []
    render(
      <IcttV2RankingPanel
        universe="n20"
        onUniverseChange={(value) => seen.push(value)}
        rows={[foz]}
        error={null}
        selectedCodigo={null}
        onSelect={() => undefined}
      />,
    )
    fireEvent.click(screen.getByRole('radio', { name: 'N ≥ 10' }))
    expect(seen).toEqual(['n10'])
  })
})
