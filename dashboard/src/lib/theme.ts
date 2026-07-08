/**
 * Small, pragmatic design system presets.
 *
 * Goal: avoid scattering long Tailwind class strings while keeping layout/behavior unchanged.
 */

/** Superfície padrão de cards — tema claro institucional (M11C). */
const cardSurfaceClass =
  'border border-slate-200/90 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.06),0_8px_24px_rgba(15,23,42,0.06)]'

const cardSurfaceHoverClass =
  'hover:shadow-[0_2px_4px_rgba(15,23,42,0.08),0_16px_40px_rgba(15,23,42,0.1)]'

const kpiSurfaceClass = cardSurfaceClass
const compareChipSurfaceClass = cardSurfaceClass
const executiveKpiSurfaceClass = cardSurfaceClass

export const theme = {
  surface: {
    glassClass: cardSurfaceClass,
  },

  card: {
    baseClass: `rounded-2xl p-5 md:p-6 ${cardSurfaceClass}`,
    translucentClass: `rounded-2xl p-5 md:p-6 ${cardSurfaceClass}`,
    hoverClass: `transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-0.5 ${cardSurfaceHoverClass}`,
  },

  kpiTile: {
    baseClass: `rounded-xl border border-slate-200/90 bg-white p-4 shadow-sm`,
    emphasizedSurfaceClass: kpiSurfaceClass,
    emphasizedBaseClass: `rounded-2xl p-5 shadow-sm ${kpiSurfaceClass}`,
    executiveBaseClass: `flex min-h-[11rem] flex-col overflow-hidden rounded-2xl px-5 pb-0 pt-5 ${executiveKpiSurfaceClass}`,
    executiveBodyClass: 'relative z-10 flex flex-1 flex-col pb-3',
    executiveValueSlotClass: 'mt-2 flex min-h-[2.5rem] items-end md:min-h-[2.75rem]',
    executiveDeltaSlotClass: 'mt-1.5 min-h-[1.375rem] leading-5',
    executiveVsSlotClass: 'mt-1 min-h-[1.25rem] leading-5',
    executiveSparklineClass:
      'relative z-0 mt-auto h-10 w-full shrink-0 overflow-hidden opacity-[0.54]',
    labelClass: 'text-[11px] font-semibold uppercase tracking-wide text-slate-600',
    emphasizedLabelClass:
      'text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500',
    executiveLabelClass:
      'mt-3 text-[11px] font-semibold uppercase tracking-[0.16em]',
    valueClass: 'mt-2 text-2xl font-semibold tracking-tight tabular-nums md:text-3xl',
    executiveValueClass:
      'min-w-[11ch] text-3xl font-semibold tabular-nums leading-none tracking-tight text-slate-900 md:text-[2rem]',
    hintClass: 'mt-1.5 text-xs font-medium tabular-nums text-slate-500',
    emphasizedHintClass: 'mt-2 text-xs font-medium tabular-nums text-slate-500',
    executiveDeltaClass: 'text-sm font-medium tabular-nums',
    executiveVsClass: 'text-xs text-slate-500',
    tonePositive: 'text-orgmigra-green-700',
    toneNegative: 'text-rose-600',
    toneNeutral: 'text-slate-900',
    emphasizedTonePositive: 'text-orgmigra-green-700',
    emphasizedToneNegative: 'text-rose-600',
    emphasizedToneNeutral: 'text-slate-900',
  },

  compareChip: {
    baseClass: `rounded-2xl px-5 py-4 transition-[box-shadow,background-color,border-color] duration-200 ${compareChipSurfaceClass}`,
    activeClass: `${compareChipSurfaceClass} ring-2 ring-orgmigra-blue-500/35 border-orgmigra-blue-300`,
    inactiveClass: `${compareChipSurfaceClass} hover:border-slate-300`,
    executiveBaseClass:
      `rounded-2xl px-4 py-4 transition-[box-shadow,background-color,border-color] duration-200 ${compareChipSurfaceClass}`,
    executiveActiveClass: `${compareChipSurfaceClass} ring-2 ring-orgmigra-blue-500/35 border-orgmigra-blue-300`,
    executiveInactiveClass: `${compareChipSurfaceClass} hover:border-slate-300`,
    labelClass:
      'text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500',
    valueClass: 'mt-1.5 text-lg font-semibold tabular-nums text-slate-900',
    detailClass: 'mt-1.5 text-xs text-slate-500',
    executiveLabelClass:
      'text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500',
    executiveValueClass: 'mt-0.5 text-base font-semibold tabular-nums text-slate-900',
    executiveDetailClass: 'mt-1 text-xs text-slate-500',
  },

  dataSourceNote: {
    compactClass: 'border-t border-slate-200 pt-4 text-xs leading-relaxed text-slate-500',
    panelClass:
      'rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 text-xs leading-relaxed text-slate-600',
    titleClass: 'font-medium text-slate-700',
    highlightClass: 'text-slate-800',
  },

  dataSourceFooter: {
    className:
      'mt-8 flex flex-wrap items-center justify-center gap-1.5 pt-2 text-center text-xs text-slate-500',
  },

  chartCard: {
    surfaceClass: cardSurfaceClass,
    executiveSurfaceClass: cardSurfaceClass,
    grid2Class: 'grid gap-7 lg:grid-cols-2 lg:gap-8',
    grid3Class: 'grid gap-7 lg:grid-cols-3 lg:gap-8',
    footerClass: 'mt-4 border-t border-slate-200 pt-3',
    actionClass:
      'rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-orgmigra-blue-700 transition-colors hover:border-orgmigra-blue-300 hover:bg-orgmigra-blue-50 hover:text-orgmigra-blue-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-orgmigra-blue-600/30',
  },

  executive: {
    pageStack: 'space-y-8',
    heroSection: 'max-w-4xl pt-2 lg:pt-4',
    kpiGrid: 'grid gap-4 md:grid-cols-3 md:gap-5',
    compareSection: 'mb-8 space-y-4',
    compareGrid: 'grid gap-3 md:grid-cols-3 md:gap-4',
    chartGrid: 'grid gap-7 lg:grid-cols-2 lg:gap-8',
    chartHoverClass:
      'transition-[box-shadow,transform] duration-200 ease-out hover:-translate-y-0.5 hover:shadow-[0_2px_4px_rgba(15,23,42,0.08),0_16px_40px_rgba(15,23,42,0.1)]',
    heroTitle:
      'text-balance text-3xl font-bold tracking-tight text-[color:var(--orgmigra-blue)] md:text-4xl lg:text-[2.65rem] lg:leading-[1.1]',
    heroSubtitle: 'mt-2.5 text-sm leading-relaxed text-slate-600',
  },

  chartTable: {
    toggleClass:
      'inline-flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-orgmigra-blue-600/30',
    toggleActiveClass: 'border-orgmigra-blue-300 bg-orgmigra-blue-50 text-orgmigra-blue-700',
    panelClass: 'mt-4 border-t border-slate-200 pt-4',
  },

  dataGrid: {
    containerClass: 'overflow-auto rounded-xl border border-slate-200 bg-white',
    headerClass: 'sticky top-0 z-10 bg-slate-50/95 backdrop-blur-sm',
    headerRowClass: 'border-b border-slate-200',
    headerCellClass: 'whitespace-nowrap px-3 py-2 font-medium text-slate-700',
    headerButtonClass:
      'inline-flex items-center gap-1 rounded-lg px-1 py-0.5 text-slate-700 hover:bg-slate-100',
    bodyRowClass: 'border-b border-slate-100 transition-colors hover:bg-slate-50/80',
    bodyCellClass: 'px-3 py-2 text-slate-800',
    emptyCellClass: 'text-slate-400',
    footerClass: 'text-right text-xs text-slate-500',
  },

  emptyState: {
    containerClass:
      'flex min-h-[12rem] flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/50 px-6 py-10 text-center',
    titleClass: 'text-sm font-medium text-slate-700',
    descriptionClass: 'mt-2 max-w-sm text-sm text-slate-500',
  },

  loadingState: {
    labelClass: 'text-sm text-slate-500',
    skeletonClass:
      'h-28 animate-pulse rounded-2xl border border-slate-200 bg-slate-100/80',
  },

  mapPanel: {
    headerBorderClass: 'border-b border-slate-200',
    titleClass: 'text-sm font-semibold text-slate-900',
    subtitleClass: 'text-xs leading-relaxed text-slate-600',
    metaClass: 'text-[11px] text-slate-500',
    legendOverlayClass:
      'pointer-events-auto inline-flex max-w-full rounded-lg border border-slate-200 bg-white/95 px-3 py-2 shadow-sm backdrop-blur-sm',
    loadingSpinnerClass:
      'h-8 w-8 animate-pulse rounded-full bg-orgmigra-blue-100 ring-1 ring-orgmigra-blue-200/80',
    loadingMessageClass: 'max-w-md text-center text-sm text-slate-500',
  },

  mapPlaceholder: {
    gradientClass:
      'pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,rgba(25,78,147,0.06),transparent_40%,rgba(249,189,44,0.05))]',
    iconWrapClass: 'mt-0.5 rounded-xl bg-orgmigra-blue-50 p-2 ring-1 ring-orgmigra-blue-200/80',
    iconClass: 'h-5 w-5 text-orgmigra-blue-700',
    titleClass: 'text-sm font-semibold text-slate-900',
    bodyClass: 'mt-1 max-w-prose text-sm text-slate-600',
    badgeClass:
      'rounded-xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-3 text-xs text-slate-500',
  },

  competenciaBadge: {
    baseClass:
      'inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white text-sm shadow-sm',
    compactClass: 'px-2 py-1 text-xs',
    defaultClass: 'rounded-xl px-3 py-1.5',
    iconClass: 'shrink-0 text-orgmigra-blue-600/80',
    labelClass: 'text-slate-500',
    valueClass: 'font-medium text-slate-800',
    fallbackClass:
      'rounded-full bg-orgmigra-yellow-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-orgmigra-yellow-700 ring-1 ring-orgmigra-yellow-200/80',
  },

  shell: {
    pageGradient:
      'min-h-screen bg-[#f4f7fa] bg-[radial-gradient(ellipse_85%_55%_at_88%_8%,rgba(25,78,147,0.07),transparent_52%),radial-gradient(ellipse_50%_40%_at_8%_92%,rgba(140,93,172,0.05),transparent_55%),linear-gradient(180deg,#f8fafc_0%,#f1f5f9_100%)]',
    sidebarClass:
      'relative z-20 sticky top-5 hidden h-[calc(100vh-2.5rem)] w-56 shrink-0 flex-col justify-between rounded-2xl border border-orgmigra-blue-900/35 bg-orgmigra-blue-800 px-3 py-4 shadow-[0_1px_2px_rgba(15,23,42,0.12),0_8px_24px_rgba(15,23,42,0.18)] lg:flex',
    sidebarBrandRow: 'flex items-center gap-2.5 px-1',
    sidebarBrandIcon:
      'flex h-8 w-8 items-center justify-center rounded-lg bg-orgmigra-blue-50 text-orgmigra-blue-700 ring-1 ring-orgmigra-blue-200/80',
    sidebarBrandLabel: 'text-sm font-bold tracking-wide text-slate-900',
    sidebarBrandTitle: 'mt-0.5 text-xs text-slate-500',
    sidebarCompetenciaCard:
      'rounded-xl border border-white/25 bg-white/95 px-3 py-3 shadow-sm',
    sidebarCompetenciaLabel: 'text-[10px] font-medium uppercase tracking-wider text-slate-500',
    sidebarCompetenciaValue: 'mt-1 text-sm font-semibold text-orgmigra-blue-800',
    navLinkBase:
      'group relative flex items-center gap-3 rounded-lg py-2.5 pl-3 pr-3 text-sm font-medium transition-[color,background-color] duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40',
    navLinkActive:
      'bg-white/95 text-orgmigra-blue-800 shadow-sm before:absolute before:left-0 before:top-1/2 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-full before:bg-orgmigra-blue-600',
    navLinkInactive: 'text-blue-100 hover:bg-white/10 hover:text-white',
    mobileBrandTitle: 'text-base font-semibold text-slate-800',
    mobileNavActive:
      'border border-orgmigra-blue-200 bg-orgmigra-blue-50 text-orgmigra-blue-900 ring-0',
    mobileNavInactive:
      'border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900',
    globalHeaderClass: 'mb-6 space-y-5',
    globalControlsRowClass:
      'flex flex-col gap-4 xl:flex-row xl:flex-wrap xl:items-center xl:gap-6',
  },

  selector: {
    labelClass: 'text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500',
    containerClass:
      'inline-flex max-w-full flex-wrap rounded-full border border-slate-200 bg-white p-1 shadow-sm',
    buttonClass:
      'relative h-8 shrink-0 rounded-full border border-transparent px-3 text-sm font-medium tabular-nums transition-[color,background-color,border-color,box-shadow] duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-orgmigra-blue-600/40',
    scopeButtonClass: 'w-[5.5rem]',
    monthButtonClass: 'min-w-[4.75rem]',
    inactiveTextClass: 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
    activeButtonClass:
      'border-orgmigra-blue-200 bg-orgmigra-blue-600 text-white shadow-sm',
    loadingTextClass: 'px-3 py-1.5 text-sm text-slate-500',
  },

  typography: {
    heroLabel: 'text-xs font-semibold uppercase tracking-[0.2em] text-orgmigra-blue-700/90',
    heroTitle: 'mt-2 text-balance text-3xl font-semibold tracking-tight text-slate-900 md:text-4xl',
    heroTitleExecutive:
      'mt-2.5 text-balance text-3xl font-semibold leading-tight tracking-tight text-slate-900 md:text-4xl lg:text-5xl',
    pageSubtitle: 'mt-2 max-w-2xl text-sm text-slate-600',
    sectionTitle:
      'text-base font-semibold tracking-tight text-orgmigra-blue-800 md:text-lg',
    sectionSubtitle:
      'mt-0.5 max-w-prose text-xs leading-relaxed text-slate-500 sm:text-sm',
    smallMuted: 'text-xs text-slate-500',
  },

  doc: {
    bodyClass: 'text-sm leading-relaxed text-slate-600',
    emphasisClass: 'font-medium text-slate-800',
    layerClass: 'text-slate-700',
    codeClass: 'rounded bg-slate-100 px-1 font-mono text-xs text-slate-700',
    endpointClass: 'shrink-0 font-mono text-xs text-slate-700',
    badgeClass: 'rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700',
  },
} as const
