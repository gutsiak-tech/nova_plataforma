import clsx from 'clsx'
import { theme } from '../../lib/theme'

export function LoadingState({
  label = 'Carregando dados...',
  rows = 3,
  className,
}: {
  label?: string
  rows?: number
  className?: string
}) {
  return (
    <div className={clsx('space-y-4', className)} role="status" aria-live="polite" aria-busy="true">
      <p className={theme.loadingState.labelClass}>{label}</p>
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className={theme.loadingState.skeletonClass} />
        ))}
      </div>
    </div>
  )
}
