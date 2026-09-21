import clsx from 'clsx'
import { formatCompetenciaShort } from '../../lib/icttV2View'
import { theme } from '../../lib/theme'

export function IcttV2CompetenciaSelect({
  competencias,
  value,
  onChange,
  loading,
}: {
  competencias: string[]
  value: string | null
  onChange: (competencia: string) => void
  loading?: boolean
}) {
  if (loading && competencias.length === 0) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <span className={theme.selector.labelClass}>Competência ICTT v2</span>
        <div className={clsx(theme.selector.containerClass, 'min-w-[7rem] animate-pulse opacity-60')}>
          <span className={theme.selector.loadingTextClass}>...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className={theme.selector.labelClass} id="ictt-v2-competencia-label">
        Competência ICTT v2
      </span>
      <div
        className={clsx(theme.selector.containerClass, 'max-w-full flex-wrap')}
        role="group"
        aria-labelledby="ictt-v2-competencia-label"
      >
        {competencias.map((item) => {
          const active = value === item
          const label = formatCompetenciaShort(item)
          return (
            <button
              key={item}
              type="button"
              onClick={() => onChange(item)}
              aria-pressed={active}
              aria-label={`Competência ${label}`}
              className={clsx(
                theme.selector.buttonClass,
                theme.selector.monthButtonClass,
                active ? theme.selector.activeButtonClass : theme.selector.inactiveTextClass,
              )}
            >
              {label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
