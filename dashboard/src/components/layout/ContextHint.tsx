import clsx from 'clsx'
import { useLocation } from 'react-router-dom'
import type { Scope } from '../../api/types'
import { useScope } from '../../context/ScopeContext'
import { isIcttV2Path } from '../../lib/icttV2Route'

const SCOPE_HINTS: Record<Scope, string> = {
  br: 'Brasil — visão nacional consolidada.',
  pr: 'Paraná — recorte estadual.',
  rmc: 'Região Metropolitana de Curitiba.',
}

export function ContextHint({ className }: { className?: string }) {
  const { scope } = useScope()
  const { pathname } = useLocation()
  const hint = SCOPE_HINTS[isIcttV2Path(pathname) ? 'pr' : scope]

  return (
    <div
      className={clsx('flex shrink-0 items-center xl:w-[22rem]', className)}
      title={hint}
    >
      <p className="line-clamp-2 text-sm leading-5 text-slate-600">{hint}</p>
    </div>
  )
}
