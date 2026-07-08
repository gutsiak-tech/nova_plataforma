import clsx from 'clsx'
import { CalendarDays } from 'lucide-react'
import { useMonth } from '../../context/MonthContext'
import { theme } from '../../lib/theme'

export function CompetenciaBadge({
  className,
  compact = false,
}: {
  className?: string
  compact?: boolean
}) {
  const { label, competencia, loading, fetchError } = useMonth()

  return (
    <div
      className={clsx(
        theme.competenciaBadge.baseClass,
        compact ? theme.competenciaBadge.compactClass : theme.competenciaBadge.defaultClass,
        className,
      )}
      title="Competência selecionada (preservada ao recarregar a página)"
    >
      <CalendarDays
        className={clsx(theme.competenciaBadge.iconClass, compact ? 'h-3.5 w-3.5' : 'h-4 w-4')}
        aria-hidden
      />
      {!compact ? <span className={theme.competenciaBadge.labelClass}>Competência:</span> : null}
      <span className={clsx(theme.competenciaBadge.valueClass, compact && 'tabular-nums')}>
        {loading ? '...' : label || competencia}
      </span>
      {fetchError ? (
        <span className={theme.competenciaBadge.fallbackClass} title="API de competências indisponível; usando lista local de fallback">
          fallback
        </span>
      ) : null}
    </div>
  )
}
