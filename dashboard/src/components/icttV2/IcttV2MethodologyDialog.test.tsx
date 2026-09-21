import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { IcttV2MethodologyDialog } from './IcttV2MethodologyDialog'

afterEach(() => cleanup())

const data = {
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
}

describe('IcttV2MethodologyDialog', () => {
  it('apresenta a metodologia em português, com referência amigável e identificador técnico', () => {
    render(
      <IcttV2MethodologyDialog open onClose={() => undefined} data={data} error={null} />,
    )

    expect(screen.getByText('Metodologia ICTT — versão 2.0')).toBeTruthy()
    expect(screen.queryByText(/ICTT methodology version/i)).toBeNull()
    expect(
      screen.getByText('Paraná · janeiro a abril de 2026 · municípios com pelo menos 10 admissões'),
    ).toBeTruthy()
    expect(
      screen.getByText('Identificador técnico: NORM_B.2026-01_2026-04.N233'),
    ).toBeTruthy()
    expect(screen.getByText('Absorção: 25%')).toBeTruthy()
    expect(screen.getByText('Remuneração: 25%')).toBeTruthy()
    expect(screen.getByText('Qualidade contratual: 25%')).toBeTruthy()
    expect(screen.getByText('Diversificação: 25%')).toBeTruthy()
    expect(screen.getByText(/Mínimo de 10 admissões para cálculo/)).toBeTruthy()
    expect(screen.getByText(/Maior robustez a partir de 20 admissões/)).toBeTruthy()
  })
})
