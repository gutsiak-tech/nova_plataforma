import { Info } from 'lucide-react'
import { ICT_CHOROPLETH } from '../map/ictChoropleth'

export function IcttV2MapLegend() {
  return (
    <div
      className="flex max-w-full flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-4"
      role="group"
      aria-label="Legenda visual do mapa ICTT v2.0"
    >
      <div className="flex min-w-[12rem] flex-1 items-center gap-2">
        <span className="text-[11px] text-slate-600">0</span>
        <div
          className="h-2.5 flex-1 rounded-full ring-1 ring-slate-200"
          style={{
            background: `linear-gradient(90deg, ${ICT_CHOROPLETH.scale.join(', ')})`,
          }}
          aria-hidden
        />
        <span className="text-[11px] text-slate-600">100</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span
          className="h-2.5 w-2.5 shrink-0 rounded-sm ring-1 ring-slate-200"
          style={{ backgroundColor: ICT_CHOROPLETH.noData }}
          aria-hidden
        />
        <span className="text-[11px] text-slate-600">Não calculável</span>
      </div>
      <p className="inline-flex items-center gap-1 text-[11px] text-slate-500">
        <Info className="h-3 w-3 shrink-0" aria-hidden />
        Escala visual 0–100 (apenas UI). Não é classe metodológica.
      </p>
    </div>
  )
}
