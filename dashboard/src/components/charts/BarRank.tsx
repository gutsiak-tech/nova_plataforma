import { memo, useMemo } from 'react'
import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { GoldRow } from '../../api/types'
import { formatCompact, formatInt } from '../../lib/format'
import { chartTheme } from '../../lib/chartTheme'
import { EmptyState } from '../ui/EmptyState'
import {
  HORIZONTAL_BAR_Y_AXIS_WIDTH,
  horizontalBarChartHeight,
  truncateChartLabel,
} from './horizontalBarChartUtils'

type Props = {
  rows: GoldRow[]
  labelKey: string
  valueKey: string
  title?: string
  color?: string
  yAxisInterval?: number
  highlightTop1?: boolean
}

export const BarRank = memo(function BarRank({
  rows,
  labelKey,
  valueKey,
  title,
  color = chartTheme.palette.ranking.default,
  yAxisInterval,
  highlightTop1 = false,
}: Props) {
  const data = useMemo(
    () =>
      rows
        .map((r) => {
          const full = String(r[labelKey] ?? '—')
          return {
            label: truncateChartLabel(full),
            full,
            value: Number(r[valueKey] ?? 0),
          }
        })
        .filter((d) => Number.isFinite(d.value)),
    [rows, labelKey, valueKey],
  )

  if (!data.length) {
    return (
      <EmptyState description="Não há dados disponíveis para este recorte na competência selecionada." />
    )
  }

  const chartHeight = horizontalBarChartHeight(data.length)

  return (
    <div className="w-full" style={{ height: chartHeight }}>
      {title ? (
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">
          {title}
        </p>
      ) : null}
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ left: 4, right: 16, top: 8, bottom: 8 }}
          barCategoryGap="18%"
        >
          <CartesianGrid strokeDasharray={chartTheme.grid.strokeDasharray} stroke={chartTheme.grid.stroke} />
          <XAxis
            type="number"
            tick={chartTheme.axis.tick}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={HORIZONTAL_BAR_Y_AXIS_WIDTH}
            tick={chartTheme.axis.label}
            axisLine={false}
            tickLine={false}
            interval={yAxisInterval ?? 0}
          />
          <Tooltip
            cursor={{ fill: chartTheme.tooltip.cursorFill }}
            contentStyle={chartTheme.tooltip.contentStyle}
            formatter={(v) => [formatInt(v as number), valueKey]}
            labelFormatter={(_label, payload) => {
              const row = (payload as unknown as Array<{ payload?: { full?: string } }>)?.[0]?.payload
              return row?.full ?? String(_label)
            }}
          />
          <Bar
            dataKey="value"
            fill={color}
            radius={[0, 8, 8, 0]}
            maxBarSize={18}
            className="transition-[filter,opacity] duration-200 hover:brightness-110"
          >
            {highlightTop1
              ? data.map((_, i) => (
                  <Cell key={`cell-${i}`} fill={color} fillOpacity={i === 0 ? 1 : 0.75} />
                ))
              : null}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
})

export const BarRankHorizontalLabels = memo(function BarRankHorizontalLabels({
  rows,
  labelKey,
  valueKey,
  title,
  color = chartTheme.palette.ranking.purple,
}: Props) {
  const data = useMemo(
    () =>
      rows
        .map((r) => ({
          label: String(r[labelKey] ?? '—').slice(0, 42),
          full: String(r[labelKey] ?? '—'),
          value: Number(r[valueKey] ?? 0),
        }))
        .filter((d) => Number.isFinite(d.value)),
    [rows, labelKey, valueKey],
  )

  if (!data.length) {
    return (
      <EmptyState description="Não há dados disponíveis para este recorte na competência selecionada." />
    )
  }

  return (
    <div className="h-[320px] w-full">
      {title ? (
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">
          {title}
        </p>
      ) : null}
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: 4, right: 12 }}>
          <CartesianGrid strokeDasharray={chartTheme.grid.strokeDasharray} stroke={chartTheme.grid.stroke} />
          <XAxis
            dataKey="label"
            tick={chartTheme.axis.tickSmall}
            interval={0}
            height={70}
            angle={-22}
            textAnchor="end"
          />
          <YAxis
            tick={chartTheme.axis.tick}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => formatCompact(v)}
          />
          <Tooltip
            cursor={{ fill: chartTheme.tooltip.cursorFill }}
            contentStyle={chartTheme.tooltip.contentStyle}
            formatter={(v) => [formatInt(v as number), valueKey]}
            labelFormatter={(_, p) => {
              const pl = (p as { payload?: { full?: string } })?.payload
              return pl?.full ?? ''
            }}
          />
          <Bar
            dataKey="value"
            fill={color}
            radius={[8, 8, 0, 0]}
            maxBarSize={36}
            className="transition-[filter,opacity] duration-200 hover:brightness-110"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
})
