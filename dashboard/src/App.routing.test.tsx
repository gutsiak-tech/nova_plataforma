import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, useLocation } from 'react-router-dom'

vi.mock('./components/map/TerritoryBackground', () => ({
  TerritoryBackground: () => null,
}))

vi.mock('./pages/IcttV2Page', () => ({
  IcttV2Page: () => <div>ICTT v2.0</div>,
}))

vi.mock('./pages/IctPage', () => ({
  IctPage: () => <div>Índice de Competitividade do Trabalho</div>,
}))

vi.mock('./api/gold', async () => {
  const actual = await vi.importActual<typeof import('./api/gold')>('./api/gold')
  return {
    ...actual,
    fetchCompetencias: vi.fn(async () => ({
      items: actual.buildFallbackCompetencias(),
      default: actual.buildFallbackDefault(),
    })),
  }
})

import App from './App'

function LocationPath() {
  const location = useLocation()
  return <div data-testid="location-path">{location.pathname}</div>
}

function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <LocationPath />
      <App />
    </MemoryRouter>,
  )
}

afterEach(() => cleanup())

describe('migração das rotas ICT', () => {
  it('renderiza ICTT v2 em /ict', async () => {
    renderApp('/ict')
    await waitFor(() => expect(screen.getByText('ICTT v2.0')).toBeTruthy())
    expect(screen.getByTestId('location-path').textContent).toBe('/ict')
    expect(screen.queryByText('Índice de Competitividade do Trabalho')).toBeNull()
  })

  it('preserva a V1 em /ict-v1', async () => {
    renderApp('/ict-v1')
    await waitFor(() => expect(screen.getByText('Índice de Competitividade do Trabalho')).toBeTruthy())
    expect(screen.getByTestId('location-path').textContent).toBe('/ict-v1')
    expect(screen.queryByText('ICTT v2.0')).toBeNull()
  })

  it('redireciona /ict-v2 para /ict com replace', async () => {
    renderApp('/ict-v2')
    await waitFor(() => expect(screen.getByTestId('location-path').textContent).toBe('/ict'))
    expect(screen.getByText('ICTT v2.0')).toBeTruthy()
  })

  it('mantém o item de menu ICT apontando para /ict, sem V1/V2 na navegação', async () => {
    renderApp('/ict')
    await waitFor(() => expect(screen.getByText('ICTT v2.0')).toBeTruthy())
    const ictLinks = screen.getAllByRole('link', { name: 'ICT' })
    expect(ictLinks.length).toBeGreaterThan(0)
    for (const link of ictLinks) {
      expect(link.getAttribute('href')).toBe('/ict')
    }
    expect(screen.queryByRole('link', { name: 'ICT V1' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'ICT V2' })).toBeNull()
    expect(screen.queryByRole('link', { name: '/ict-v1' })).toBeNull()
  })
})
