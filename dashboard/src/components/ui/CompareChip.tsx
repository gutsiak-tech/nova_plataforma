import { memo, type ReactNode } from 'react'
import clsx from 'clsx'
import { MapPinned } from 'lucide-react'
import type { Scope } from '../../api/types'
import { executiveAccentStyles, scopeToExecutiveAccent } from '../../lib/executiveAccentStyles'
import { theme } from '../../lib/theme'

export const CompareChip = memo(function CompareChip({
  label,
  value,
  detail,
  active = false,
  className,
  variant = 'default',
  scopeKey,
}: {
  label: string
  value: ReactNode
  detail?: ReactNode
  active?: boolean
  tone?: 'neutral' | 'positive' | 'negative'
  className?: string
  variant?: 'default' | 'executive'
  scopeKey?: Scope
}) {
  const isExecutive = variant === 'executive'
  const accentKey = scopeKey ? scopeToExecutiveAccent[scopeKey] : null
  const accent = accentKey ? executiveAccentStyles[accentKey] : null

  return (
    <div
      className={clsx(
        isExecutive ? theme.compareChip.executiveBaseClass : theme.compareChip.baseClass,
        active
          ? isExecutive
            ? accent?.activeRing ?? theme.compareChip.executiveActiveClass
            : theme.compareChip.activeClass
          : isExecutive
            ? theme.compareChip.executiveInactiveClass
            : theme.compareChip.inactiveClass,
        className,
      )}
      aria-current={active ? 'true' : undefined}
    >
      {isExecutive ? (
        <div className="flex items-start gap-3">
          <div
            className={clsx(
              'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset',
              accent?.iconBg,
            )}
          >
            <MapPinned className={clsx('h-4 w-4', accent?.iconColor)} aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <p className={clsx(theme.compareChip.executiveLabelClass, accent?.labelColor)}>
              {label}
            </p>
            <p className={theme.compareChip.executiveValueClass}>{value}</p>
            {detail ? (
              <p className={theme.compareChip.executiveDetailClass}>{detail}</p>
            ) : null}
          </div>
        </div>
      ) : (
        <>
          <p className={theme.compareChip.labelClass}>{label}</p>
          <p className={theme.compareChip.valueClass}>{value}</p>
          {detail ? <p className={theme.compareChip.detailClass}>{detail}</p> : null}
        </>
      )}
    </div>
  )
})
