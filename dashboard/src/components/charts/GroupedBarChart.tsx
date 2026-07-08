import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { chartTheme } from '../../lib/chartTheme'

const profileSeriesColors = [
  chartTheme.palette.profile.age,
  chartTheme.palette.profile.sex,
  chartTheme.palette.profile.education,
  chartTheme.palette.sector.primary,
  chartTheme.palette.occupation.primary,
  chartTheme.palette.movement.dismissals,
  chartTheme.palette.territory.primary,
  chartTheme.palette.ranking.purple,
] as const

const legendStyle = chartTheme.legend.wrapperStyle

type GroupedBarChartProps = {
  data: Record<string, string | number>[]
  series: string[]
  /** Recharts layout: vertical = barras horizontais */
  layout?: 'horizontal' | 'vertical'
  height?: number
  maxBarSize?: number
  yAxisWidth?: number
}

export function GroupedBarChart({
  data,
  series,
  layout = 'horizontal',
  height = 360,
  maxBarSize = 18,
  yAxisWidth = 180,
}: GroupedBarChartProps) {
  const isVertical = layout === 'vertical'

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout={isVertical ? 'vertical' : 'horizontal'}
          margin={{ left: 8, right: 16 }}
        >
          <CartesianGrid
            strokeDasharray={chartTheme.grid.strokeDasharray}
            stroke={chartTheme.grid.stroke}
          />
          {isVertical ? (
            <>
              <XAxis
                type="number"
                tick={chartTheme.axis.tick}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={yAxisWidth}
                tick={chartTheme.axis.label}
                axisLine={false}
                tickLine={false}
              />
            </>
          ) : (
            <>
              <XAxis
                dataKey="label"
                tick={chartTheme.axis.tickSmall}
                interval={0}
                height={70}
                angle={-18}
                textAnchor="end"
              />
              <YAxis tick={chartTheme.axis.tick} axisLine={false} tickLine={false} />
            </>
          )}
          <Tooltip
            cursor={{ fill: chartTheme.tooltip.cursorFill }}
            contentStyle={chartTheme.tooltip.contentStyle}
          />
          <Legend wrapperStyle={legendStyle} />
          {series.map((key, i) => (
            <Bar
              key={key}
              dataKey={key}
              name={key}
              fill={profileSeriesColors[i % profileSeriesColors.length]}
              maxBarSize={maxBarSize}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
