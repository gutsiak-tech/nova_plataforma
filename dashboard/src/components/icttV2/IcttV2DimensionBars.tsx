import { DIMENSION_COPY, formatOptionalNumber } from '../../lib/icttV2View'

const ORDER = ['absorcao', 'remuneracao', 'qualidade_contratual', 'diversificacao'] as const

const BAR_COLOR: Record<(typeof ORDER)[number], string> = {
  absorcao: '#194E93',
  remuneracao: '#65B244',
  qualidade_contratual: '#8C5DAC',
  diversificacao: '#3D73AD',
}

type DimensionKey = (typeof ORDER)[number]

export function IcttV2DimensionBars({
  values,
}: {
  values: Partial<Record<DimensionKey, number | null>>
}) {
  return (
    <ul className="space-y-3" aria-label="Dimensões do ICTT v2.0">
      {ORDER.map((key) => {
        const copy = DIMENSION_COPY[key]
        const raw = values[key]
        const score = raw == null || !Number.isFinite(raw) ? null : Math.min(100, Math.max(0, raw))
        const label = formatOptionalNumber(score, 1)
        return (
          <li key={key}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-sm font-medium text-slate-800">{copy.label}</span>
              <span className="text-sm font-semibold tabular-nums text-slate-900">
                {label ?? 'não disponível'}
              </span>
            </div>
            <div
              className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100 ring-1 ring-slate-200/80"
              role="img"
              aria-label={
                score == null
                  ? `${copy.label} indisponível`
                  : `${copy.label} ${label} em uma escala visual de 0 a 100`
              }
            >
              <div
                className="h-full rounded-full transition-[width] duration-300"
                style={{
                  width: score == null ? '0%' : `${score}%`,
                  backgroundColor: BAR_COLOR[key],
                  opacity: score == null ? 0.25 : 1,
                }}
              />
            </div>
            <p className="mt-1 text-[11px] leading-snug text-slate-500">{copy.text}</p>
          </li>
        )
      })}
    </ul>
  )
}
