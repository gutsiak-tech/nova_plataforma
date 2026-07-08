import { memo, useId } from 'react'

type Trend = 'up' | 'down' | 'flat'

const PATHS: Record<Trend, string> = {
  up: 'M0,28 L24,22 L48,18 L72,14 L96,10 L120,8 L144,12 L168,6 L200,4',
  down: 'M0,6 L24,10 L48,14 L72,18 L96,22 L120,24 L144,20 L168,26 L200,28',
  flat: 'M0,16 L24,15 L48,17 L72,16 L96,15 L120,16 L144,17 L168,16 L200,15',
}

export const DecorativeSparkline = memo(function DecorativeSparkline({
  color,
  trend = 'up',
  className,
  soft = false,
}: {
  color: string
  trend?: Trend
  className?: string
  /** Estilo discreto para fundo claro (KPI executivo). */
  soft?: boolean
}) {
  const gradId = useId().replace(/:/g, '')
  const fillTopOpacity = soft ? 0.3 : 0.45
  const strokeOpacity = soft ? 0.68 : 0.85
  const strokeWidth = soft ? 1.35 : 2

  return (
    <svg
      viewBox="0 0 200 32"
      preserveAspectRatio="none"
      className={className ?? 'block h-10 w-full'}
      aria-hidden
    >
      <defs>
        <linearGradient id={`spark-${gradId}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={fillTopOpacity} />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path
        d={`${PATHS[trend]} L200,32 L0,32 Z`}
        fill={`url(#spark-${gradId})`}
      />
      <path
        d={PATHS[trend]}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={strokeOpacity}
      />
    </svg>
  )
})
