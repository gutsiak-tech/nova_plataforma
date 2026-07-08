import { useId, useState, type FocusEvent } from 'react'
import { Info } from 'lucide-react'
import { ICT_CHOROPLETH } from './ictChoropleth'

const SCALE_LABELS = [
  { label: 'Muito baixo · ICT 0–20', color: ICT_CHOROPLETH.scale[0] },
  { label: 'Baixo · ICT 20–40', color: ICT_CHOROPLETH.scale[1] },
  { label: 'Médio · ICT 40–60', color: ICT_CHOROPLETH.scale[2] },
  { label: 'Alto · ICT 60–80', color: ICT_CHOROPLETH.scale[3] },
  { label: 'Muito alto · ICT 80–100', color: ICT_CHOROPLETH.scale[4] },
] as const

const LEGEND_NOTE =
  'Quanto maior o ICT, maior a competitividade territorial relativa do trabalho formal migrante na competência selecionada. Municípios em cinza não tiveram movimentação migratória suficiente para cálculo.'

function LegendInfoTip({ text }: { text: string }) {
  const tooltipId = useId()
  const [open, setOpen] = useState(false)

  const handleBlur = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setOpen(false)
    }
  }

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={handleBlur}
    >
      <button
        type="button"
        className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-slate-400 transition-colors hover:text-slate-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-orgmigra-blue-400"
        aria-label="Como interpretar o ICT"
        aria-expanded={open}
        aria-controls={tooltipId}
        onClick={() => setOpen((value) => !value)}
      >
        <Info className="h-3 w-3" aria-hidden />
      </button>
      {open ? (
        <div
          id={tooltipId}
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-1.5 w-max min-w-[280px] max-w-[min(360px,calc(100vw-48px))] -translate-x-1/2 rounded-[0.625rem] border border-slate-200 bg-white/98 px-3 py-2.5 text-[11px] leading-snug text-slate-600 shadow-md"
        >
          {text}
        </div>
      ) : null}
    </div>
  )
}

export function IctMapLegend() {
  return (
    <div
      className="flex max-w-full flex-wrap items-center gap-x-4 gap-y-2"
      role="group"
      aria-label="Legenda do mapa ICT"
    >
      {SCALE_LABELS.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5" role="listitem">
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-sm ring-1 ring-slate-200"
            style={{ backgroundColor: item.color }}
            aria-hidden
          />
          <span className="text-[11px] text-slate-600">{item.label}</span>
        </div>
      ))}
      <div className="flex items-center gap-1.5" role="listitem">
        <span
          className="h-2.5 w-2.5 shrink-0 rounded-sm ring-1 ring-slate-200"
          style={{ backgroundColor: ICT_CHOROPLETH.noData }}
          aria-hidden
        />
        <span className="text-[11px] text-slate-600">Sem base suficiente</span>
      </div>
      <LegendInfoTip text={LEGEND_NOTE} />
    </div>
  )
}
