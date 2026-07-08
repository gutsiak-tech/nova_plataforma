import { tokens } from './tokens'

const brand = tokens.colors.orgmigra

export const chartTheme = {
  grid: {
    stroke: tokens.colors.chart.grid,
    strokeDasharray: '3 3',
  },
  axis: {
    tick: { fill: tokens.colors.chart.tick, fontSize: 11 },
    tickSmall: { fill: tokens.colors.chart.tick, fontSize: 10 },
    label: { fill: tokens.colors.chart.label, fontSize: 11 },
  },
  tooltip: {
    cursorFill: tokens.colors.chart.cursor,
    contentStyle: {
      background: tokens.colors.chart.tooltipBg,
      border: `1px solid ${tokens.colors.chart.tooltipBorder}`,
      borderRadius: 12,
      color: tokens.colors.chart.tooltipText,
      fontSize: 12,
      lineHeight: '1.4',
      boxShadow: '0 4px 16px rgba(15, 23, 42, 0.1)',
    } as const,
  },
  legend: {
    wrapperStyle: { color: tokens.colors.chart.tick, fontSize: 11 },
  },
  palette: {
    movement: {
      admissions: brand.yellow,
      dismissals: brand.purple,
      balancePositive: brand.green,
      balanceNegative: tokens.colors.accent.rose,
      /** @deprecated use admissions — mantido para MovementSplit */
      admissoes: brand.yellow,
      /** @deprecated use dismissals — mantido para MovementSplit */
      desligamentos: brand.purple,
    },
    territory: {
      primary: brand.blue,
      municipio: brand.blueLight,
    },
    sector: {
      primary: brand.purple,
    },
    occupation: {
      primary: brand.yellow,
    },
    profile: {
      sex: brand.blue,
      age: brand.green,
      education: brand.purple,
    },
    salary: {
      primary: brand.blue,
      secondary: brand.purple,
      median: brand.green,
      average: brand.yellow,
      positive: brand.green,
      negative: tokens.colors.accent.rose,
    },
    neutral: {
      grid: tokens.colors.chart.grid,
      axis: tokens.colors.chart.tick,
      tooltip: tokens.colors.chart.tooltipText,
    },
    ranking: {
      default: brand.blue,
      purple: brand.purple,
      yellow: brand.yellow,
      sky: brand.green,
    },
  },
} as const
