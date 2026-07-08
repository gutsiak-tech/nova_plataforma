/**
 * Design system tokens for the dashboard.
 *
 * Raw values live in `src/index.css` as CSS variables.
 * This file provides typed accessors so components stop repeating literals.
 */

export const tokens = {
  cssVar(name: `--ds-${string}`) {
    return `var(${name})`
  },

  colors: {
    orgmigra: {
      blue: 'var(--orgmigra-blue)',
      blueDark: 'var(--orgmigra-blue-dark)',
      blueLight: 'var(--orgmigra-blue-light)',
      green: 'var(--orgmigra-green)',
      greenDark: 'var(--orgmigra-green-dark)',
      purple: 'var(--orgmigra-purple)',
      purpleDark: 'var(--orgmigra-purple-dark)',
      yellow: 'var(--orgmigra-yellow)',
      yellowDark: 'var(--orgmigra-yellow-dark)',
    },
    accent: {
      teal: 'var(--ds-accent-teal)',
      tealLight: 'var(--ds-accent-teal-light)',
      amber: 'var(--ds-accent-amber)',
      amberLight: 'var(--ds-accent-amber-light)',
      cyan: 'var(--ds-accent-cyan)',
      sky: 'var(--ds-accent-sky)',
      indigo: 'var(--ds-accent-indigo)',
      purple: 'var(--ds-accent-purple)',
      yellow: 'var(--ds-accent-yellow)',
      green: 'var(--ds-accent-green)',
      rose: 'var(--ds-accent-rose)',
    },
    text: {
      primary: 'var(--ds-text-primary)',
      secondary: 'var(--ds-text-secondary)',
      muted: 'var(--ds-text-muted)',
      accentLabel: 'var(--ds-text-accent-label)',
    },
    border: {
      standard: 'var(--ds-border)',
      subtle: 'var(--ds-border-subtle)',
    },
    surface: {
      page: 'var(--ds-surface-page)',
      shell: 'var(--ds-surface-shell)',
      card: 'var(--ds-surface-card)',
      kpi: 'var(--ds-surface-kpi)',
      muted: 'var(--ds-surface-muted)',
    },
    chart: {
      grid: 'var(--ds-chart-grid)',
      tick: 'var(--ds-chart-tick)',
      label: 'var(--ds-chart-label)',
      tooltipBg: 'var(--ds-chart-tooltip-bg)',
      tooltipBorder: 'var(--ds-chart-tooltip-border)',
      tooltipText: 'var(--ds-chart-tooltip-text)',
      cursor: 'var(--ds-chart-cursor)',
    },
  },
} as const

