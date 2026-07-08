import { memo, type ReactNode } from 'react'
import clsx from 'clsx'
import { theme } from '../../lib/theme'

export const SectionTitle = memo(function SectionTitle({
  title,
  subtitle,
  action,
  className,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={clsx(
        'mb-3 flex flex-col gap-2 md:flex-row md:items-start md:justify-between md:gap-4',
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className={theme.typography.sectionTitle}>{title}</h2>
        {subtitle ? (
          <p className={theme.typography.sectionSubtitle}>{subtitle}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0 self-start md:mt-0.5">{action}</div> : null}
    </div>
  )
})
