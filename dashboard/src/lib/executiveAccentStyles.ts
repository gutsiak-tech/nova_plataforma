import type { Scope } from '../api/types'

/** Tokens visuais compartilhados — KPI executivo e comparativo de escopos. */
export const executiveAccentStyles = {
  blue: {
    iconBg: 'bg-orgmigra-blue-100 ring-orgmigra-blue-300/90',
    iconColor: 'text-orgmigra-blue-800',
    labelColor: 'text-orgmigra-blue-800',
    spark: '#184890',
    activeRing: 'ring-2 ring-orgmigra-blue-500/35 border-orgmigra-blue-300',
  },
  purple: {
    iconBg: 'bg-orgmigra-purple-100 ring-orgmigra-purple-200',
    iconColor: 'text-orgmigra-purple-800',
    labelColor: 'text-orgmigra-purple-800',
    spark: '#8858A8',
    activeRing: 'ring-2 ring-orgmigra-purple-500/35 border-orgmigra-purple-200',
  },
  green: {
    iconBg: 'bg-orgmigra-green-100 ring-orgmigra-green-200',
    iconColor: 'text-orgmigra-green-800',
    labelColor: 'text-orgmigra-green-800',
    spark: '#60B040',
    activeRing: 'ring-2 ring-orgmigra-green-500/35 border-orgmigra-green-200',
  },
} as const

export type ExecutiveAccentKey = keyof typeof executiveAccentStyles

export const scopeToExecutiveAccent: Record<Scope, ExecutiveAccentKey> = {
  br: 'blue',
  pr: 'purple',
  rmc: 'green',
}
