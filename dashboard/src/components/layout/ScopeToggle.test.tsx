import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { ScopeProvider } from '../../context/ScopeContext'
import { isIcttV2Path } from '../../lib/icttV2Route'
import { ContextHint } from './ContextHint'
import { ScopeToggle } from './ScopeToggle'

afterEach(() => cleanup())

function renderOn(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ScopeProvider>
        <ScopeToggle />
        <ContextHint />
      </ScopeProvider>
    </MemoryRouter>,
  )
}

describe('escopo na rota ICTT v2', () => {
  it('reconhece apenas a rota /ict-v2', () => {
    expect(isIcttV2Path('/ict-v2')).toBe(true)
    expect(isIcttV2Path('/ict')).toBe(false)
    expect(isIcttV2Path('/')).toBe(false)
  })

  it('mostra Paraná como escopo ativo em /ict-v2, sem sugerir recorte nacional', () => {
    renderOn('/ict-v2')
    expect(screen.getByLabelText('Escopo Paraná').getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByLabelText('Escopo Brasil').getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByLabelText('Escopo RMC').getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByText('Paraná — recorte estadual.')).toBeTruthy()
    expect(screen.queryByText('Brasil — visão nacional consolidada.')).toBeNull()

    fireEvent.click(screen.getByLabelText('Escopo Brasil'))
    expect(screen.getByLabelText('Escopo Paraná').getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByLabelText('Escopo Brasil').getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByText('Paraná — recorte estadual.')).toBeTruthy()
  })

  it('preserva Brasil como padrão fora de /ict-v2', () => {
    renderOn('/ict')
    expect(screen.getByLabelText('Escopo Brasil').getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByLabelText('Escopo Paraná').getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByText('Brasil — visão nacional consolidada.')).toBeTruthy()
  })
})
