import clsx from 'clsx'
import type { IcttV2MunicipalityPublic, IcttV2RankingUniverse } from '../../api/icttV2Types'
import {
  DEFAULT_RANKING_UNIVERSE,
  RANKING_UNIVERSE_OPTIONS,
  formatIcttScore,
  rankingPosition,
  reliabilityLabel,
} from '../../lib/icttV2View'
import { ChartCard } from '../ui/ChartCard'
import { EmptyState } from '../ui/EmptyState'
import { theme } from '../../lib/theme'

export function IcttV2RankingPanel({
  universe,
  onUniverseChange,
  rows,
  error,
  onRetry,
  selectedCodigo,
  onSelect,
  loading,
}: {
  universe: IcttV2RankingUniverse
  onUniverseChange: (universe: IcttV2RankingUniverse) => void
  rows: IcttV2MunicipalityPublic[]
  error: string | null
  onRetry?: () => void
  selectedCodigo: string | null
  onSelect: (codigoMunicipio: string) => void
  loading?: boolean
}) {
  return (
    <ChartCard
      hover={false}
      title="Ranking municipal"
      subtitle="Universo do ranking — escolha de visualização, não uma classificação oficial."
      action={
        <div
          className={clsx(theme.selector.containerClass, 'flex-nowrap')}
          role="radiogroup"
          aria-label="Universo do ranking"
        >
          {RANKING_UNIVERSE_OPTIONS.map((option) => {
            const active = universe === option.value
            return (
              <button
                key={option.value}
                type="button"
                role="radio"
                aria-checked={active}
                title={option.hint}
                onClick={() => onUniverseChange(option.value)}
                className={clsx(
                  theme.selector.buttonClass,
                  active ? theme.selector.activeButtonClass : theme.selector.inactiveTextClass,
                )}
              >
                {option.label}
              </button>
            )
          })}
        </div>
      }
    >
      {error ? (
        <div
          className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-800"
          role="alert"
        >
          <p className="font-medium">Não foi possível carregar o ranking.</p>
          <p className="mt-1 text-xs text-rose-700">{error}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 text-xs font-medium text-rose-800 underline underline-offset-2"
            >
              Tentar novamente
            </button>
          ) : null}
        </div>
      ) : loading && rows.length === 0 ? (
        <p className={theme.loadingState.labelClass}>Carregando ranking...</p>
      ) : rows.length === 0 ? (
        <EmptyState description="Nenhum município neste universo de ranking para a competência selecionada." />
      ) : (
        <ol
          className="max-h-[28rem] space-y-1 overflow-y-auto overflow-x-hidden pr-1"
          aria-label={`Ranking ICTT v2.0 no universo ${universe === 'n20' ? 'N maior ou igual a 20' : 'N maior ou igual a 10'}`}
        >
          {rows.map((row) => {
            const rank = rankingPosition(row, universe)
            const selected = row.codigo_municipio === selectedCodigo
            const reliability = reliabilityLabel(row.reliability_class)
            const score = formatIcttScore(row.ictt_v2, 1)
            return (
              <li key={row.codigo_municipio}>
                <button
                  type="button"
                  onClick={() => onSelect(row.codigo_municipio)}
                  aria-current={selected ? 'true' : undefined}
                  aria-label={`${row.municipio}, posição ${rank ?? 'sem rank'}, ICTT ${score ?? 'não calculável'}${reliability ? `, ${reliability}` : ''}`}
                  className={clsx(
                    'flex w-full min-w-0 items-center gap-3 rounded-xl border px-3 py-2 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-orgmigra-blue-600/30',
                    selected
                      ? 'border-orgmigra-blue-300 bg-orgmigra-blue-50'
                      : 'border-transparent hover:border-slate-200 hover:bg-slate-50',
                  )}
                >
                  <span className="w-8 shrink-0 text-right text-xs font-semibold tabular-nums text-slate-500">
                    {rank ?? '—'}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-900">
                      {row.municipio}
                    </span>
                    {reliability ? (
                      <span className="block text-[11px] text-slate-500">{reliability}</span>
                    ) : null}
                  </span>
                  <span className="shrink-0 text-sm font-semibold tabular-nums text-orgmigra-blue-800">
                    {score ?? 'ICTT não calculável'}
                  </span>
                </button>
              </li>
            )
          })}
        </ol>
      )}
      <p className="mt-3 text-[11px] text-slate-500">
        Padrão inicial: {RANKING_UNIVERSE_OPTIONS.find((item) => item.value === DEFAULT_RANKING_UNIVERSE)?.label}.
        A troca de universo é apenas visual.
      </p>
    </ChartCard>
  )
}
