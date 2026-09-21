import clsx from 'clsx'
import { useLocation } from 'react-router-dom'
import { useScope } from '../../context/ScopeContext'
import type { Scope } from '../../api/types'
import { labelScope } from '../../lib/format'
import { isIcttV2Path } from '../../lib/icttV2Route'
import { theme } from '../../lib/theme'

const options: { id: Scope; hint: string }[] = [
  { id: 'br', hint: 'Brasil — visão nacional consolidada' },
  { id: 'pr', hint: 'Paraná — recorte estadual' },
  { id: 'rmc', hint: 'Região Metropolitana de Curitiba' },
]

export function ScopeToggle() {
  const { scope, setScope } = useScope()
  const { pathname } = useLocation()
  const icttV2 = isIcttV2Path(pathname)
  const displayScope: Scope = icttV2 ? 'pr' : scope

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2">
      <span className={theme.selector.labelClass}>Escopo</span>
      <div
        className={theme.selector.containerClass}
        role="group"
        aria-label="Selecionar escopo geográfico"
      >
        {options.map((o) => {
          const active = displayScope === o.id
          return (
            <button
              key={o.id}
              type="button"
              onClick={() => {
                if (icttV2 && o.id !== 'pr') return
                setScope(o.id)
              }}
              title={o.hint}
              aria-pressed={active}
              aria-label={`Escopo ${labelScope(o.id)}`}
              className={clsx(
                theme.selector.buttonClass,
                theme.selector.scopeButtonClass,
                active ? theme.selector.activeButtonClass : theme.selector.inactiveTextClass,
              )}
            >
              {labelScope(o.id)}
            </button>
          )
        })}
      </div>
    </div>
  )
}
