const LABEL_MAX_LEN = 26
const BAR_ROW_HEIGHT = 32
const CHART_MIN_HEIGHT = 280
const CHART_MAX_HEIGHT = 560

export const HORIZONTAL_BAR_Y_AXIS_WIDTH = 172

export function truncateChartLabel(text: string, maxLen = LABEL_MAX_LEN): string {
  if (text.length <= maxLen) return text
  return `${text.slice(0, Math.max(1, maxLen - 1))}…`
}

export function horizontalBarChartHeight(itemCount: number): number {
  return Math.min(
    Math.max(CHART_MIN_HEIGHT, itemCount * BAR_ROW_HEIGHT + 48),
    CHART_MAX_HEIGHT,
  )
}
