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
  it('reconhece /ict como experiência v2 e isola a V1 em /ict-v1', () => {
    expect(isIcttV2Path('/ict')).toBe(true)
    expect(isIcttV2Path('/ict-v2')).toBe(true)
    expect(isIcttV2Path('/ict-v1')).toBe(false)
    expect(isIcttV2Path('/')).toBe(false)
  })

  it('mostra Paraná como escopo ativo em /ict, sem sugerir recorte nacional', () => {
    renderOn('/ict')
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

  it('preserva Brasil como padrão na V1 em /ict-v1', () => {
    renderOn('/ict-v1')
    expect(screen.getByLabelText('Escopo Brasil').getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByLabelText('Escopo Paraná').getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByText('Brasil — visão nacional consolidada.')).toBeTruthy()
  })
})
