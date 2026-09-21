import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import type { IcttV2MethodologyResponse } from '../../api/icttV2Types'
import { DIMENSION_COPY } from '../../lib/icttV2View'
import { theme } from '../../lib/theme'

function dimensionLabel(key: string): string {
  if (key === 'absorcao') return DIMENSION_COPY.absorcao.label
  if (key === 'remuneracao') return DIMENSION_COPY.remuneracao.label
  if (key === 'qualidade_contratual') return DIMENSION_COPY.qualidade_contratual.label
  if (key === 'diversificacao') return DIMENSION_COPY.diversificacao.label
  return key
}

export function IcttV2MethodologyDialog({
  open,
  onClose,
  data,
  error,
  loading,
}: {
  open: boolean
  onClose: () => void
  data: IcttV2MethodologyResponse | null
  error: string | null
  loading?: boolean
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40"
        aria-label="Fechar metodologia"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="ictt-v2-methodology-title"
        className="relative z-10 max-h-[min(32rem,calc(100vh-2rem))] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className={theme.typography.heroLabel}>ICTT methodology version 2.0</p>
            <h2 id="ictt-v2-methodology-title" className={theme.typography.sectionTitle}>
              Metodologia
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-slate-500 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-orgmigra-blue-600/30"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {loading ? (
          <p className={`mt-4 ${theme.loadingState.labelClass}`}>Carregando metodologia...</p>
        ) : error ? (
          <p className="mt-4 text-sm text-rose-700">{error}</p>
        ) : data ? (
          <dl className="mt-4 space-y-3 text-sm text-slate-700">
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Versão</dt>
              <dd>{data.methodology_version}</dd>
            </div>
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Referência de normalização
              </dt>
              <dd>NORM_B · {data.normalization_version}</dd>
            </div>
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Quatro dimensões
              </dt>
              <dd>
                <ul className="mt-1 space-y-1">
                  {data.dimensions.map((item) => (
                    <li key={item.key}>
                      {dimensionLabel(item.key)}: {(item.weight * 100).toFixed(0)}%
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Elegibilidade
              </dt>
              <dd>
                Mínimo de {data.eligibility.min_admissions} admissões para cálculo. Maior robustez a
                partir de {data.eligibility.higher_reliability_from} admissões.
              </dd>
            </div>
            <div>
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Recorte de referência
              </dt>
              <dd>
                {data.reference_scope} · {data.reference_period.start} a {data.reference_period.end}
              </dd>
            </div>
          </dl>
        ) : null}
      </div>
    </div>,
    document.body,
  )
}
