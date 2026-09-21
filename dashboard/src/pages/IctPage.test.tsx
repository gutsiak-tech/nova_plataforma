import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { useEffect } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { GOLD_COLUMNS } from '../api/goldColumns'
import { GOLD_TABLES } from '../api/goldTables'
import type { TableResponse } from '../api/types'
import { DisplaySelectionProvider } from '../context/DisplaySelectionContext'
import { MonthProvider } from '../context/MonthContext'
import { ScopeProvider, useScope } from '../context/ScopeContext'

vi.mock('../components/map/IctMap', () => ({
  IctMap: () => <div data-testid="ict-v1-map" />,
}))

vi.mock('../components/map/useTerritoryGeoJson', () => ({
  useTerritoryGeoJson: () => ({
    geoJson: { type: 'FeatureCollection', features: [] },
    geoLoading: false,
    geoError: null,
  }),
}))

vi.mock('../api/gold', async () => {
  const actual = await vi.importActual<typeof import('../api/gold')>('../api/gold')
  return {
    ...actual,
    fetchTable: vi.fn(),
    fetchCompetencias: vi.fn(async () => ({
      items: actual.buildFallbackCompetencias(),
      default: actual.buildFallbackDefault(),
    })),
  }
})

vi.mock('../api/ictReport', () => ({
  fetchIctReportContext: vi.fn(),
}))

import { fetchTable } from '../api/gold'
import { IctPage } from './IctPage'

function ForceParana() {
  const { setScope } = useScope()
  useEffect(() => {
    setScope('pr')
  }, [setScope])
  return null
}

function v1Table(): TableResponse {
  const rows = Array.from({ length: 103 }, (_, i) => ({
    [GOLD_COLUMNS.MUNICIPIO]: i === 0 ? 'Curitiba' : `Municipio ${i}`,
    [GOLD_COLUMNS.ICTT]: i === 0 ? 100 : 80 - i * 0.2,
    [GOLD_COLUMNS.RANKING_ICTT]: i + 1,
  }))
  return {
    month: { ano: 2026, mes: 4 },
    scope: 'pr',
    table: GOLD_TABLES.ICTT_MUNICIPIO,
    columns: [GOLD_COLUMNS.MUNICIPIO, GOLD_COLUMNS.ICTT, GOLD_COLUMNS.RANKING_ICTT],
    total: rows.length,
    offset: 0,
    count: rows.length,
    rows,
  }
}

afterEach(() => cleanup())

describe('IctPage V1 em /ict-v1', () => {
  beforeEach(() => {
    vi.mocked(fetchTable).mockResolvedValue(v1Table())
  })

  it('mantém o fingerprint de abril/2026: 103 municípios com ICT e Curitiba = 100', async () => {
    render(
      <MemoryRouter initialEntries={['/ict-v1']}>
        <ScopeProvider>
          <ForceParana />
          <MonthProvider>
            <DisplaySelectionProvider>
              <IctPage />
            </DisplaySelectionProvider>
          </MonthProvider>
        </ScopeProvider>
      </MemoryRouter>,
    )

    await waitFor(() =>
      expect(screen.getByLabelText('Municípios com ICT calculado: 103')).toBeTruthy(),
    )
    expect(screen.getByText('Índice de Competitividade do Trabalho')).toBeTruthy()
    expect(screen.getByLabelText('Maior ICT: 100,0')).toBeTruthy()
    expect(screen.getByText('Curitiba')).toBeTruthy()
    expect(fetchTable).toHaveBeenCalledWith(
      GOLD_TABLES.ICTT_MUNICIPIO,
      'pr',
      2026,
      4,
      expect.objectContaining({ sort_by: GOLD_COLUMNS.RANKING_ICTT }),
    )
  })
})
