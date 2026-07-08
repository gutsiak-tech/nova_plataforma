import { useEffect, useState } from 'react'
import { GOLD_COLUMNS } from '../api/goldColumns'
import { GOLD_TABLES } from '../api/goldTables'
import { fetchTable } from '../api/gold'
import type { TableResponse } from '../api/types'
import { BarRank } from '../components/charts/BarRank'
import { ChartCard } from '../components/ui/ChartCard'
import { ErrorState } from '../components/ui/ErrorState'
import { LoadingState } from '../components/ui/LoadingState'
import { PageHeader } from '../components/ui/PageHeader'
import { useScope } from '../context/ScopeContext'
import { useMonth } from '../context/MonthContext'
import { useDisplaySelection } from '../context/DisplaySelectionContext'
import { chartTheme } from '../lib/chartTheme'
import { buildDisplaySelectionKey } from '../lib/displaySelectionKey'
import { labelScope } from '../lib/format'
import { useScopeStableLoading } from '../lib/useScopeStableLoading'
import { theme } from '../lib/theme'

const palette = chartTheme.palette
const TOP_COUNTRIES = 15
const SORT_BY = GOLD_COLUMNS.SALDO
const SORT_DIR = 'desc' as const

export function CountryPage() {
  const { scope } = useScope()
  const { ano, mes } = useMonth()
  const [tblPais, setTblPais] = useState<TableResponse | null>(null)
  const [tblContinente, setTblContinente] = useState<TableResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)
  const { displayed, displayedLabel, commitVisualTransition } = useDisplaySelection()
  const selectionKey = buildDisplaySelectionKey(scope, ano, mes)
  const { beginFetch, abortFetch, shellClass, showInitialLoader } = useScopeStableLoading(
    tblPais,
    selectionKey,
  )

  useEffect(() => {
    let cancelled = false
    const isCancelled = () => cancelled
    beginFetch(isCancelled, () => {
      setErr(null)
    })
    Promise.all([
      fetchTable(GOLD_TABLES.TABELA_PAIS, scope, ano, mes, {
        limit: TOP_COUNTRIES,
        sort_by: SORT_BY,
        sort_dir: SORT_DIR,
      }),
      fetchTable(GOLD_TABLES.TABELA_CONTINENTE, scope, ano, mes, {
        limit: 20,
        sort_by: SORT_BY,
        sort_dir: SORT_DIR,
      }),
    ])
      .then(([pais, continente]) => {
        if (cancelled) return
        setTblPais(pais)
        setTblContinente(continente)
        commitVisualTransition(selectionKey)
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : 'Erro')
          abortFetch()
        }
      })
    return () => {
      cancelled = true
      abortFetch()
    }
  }, [scope, ano, mes, retryKey, beginFetch, abortFetch, selectionKey, commitVisualTransition])

  const topCountries = tblPais?.rows ?? []

  if (err) {
    return <ErrorState message={err} onRetry={() => setRetryKey((k) => k + 1)} />
  }
  if (showInitialLoader || !tblPais || !tblContinente) {
    return <LoadingState label="Carregando dados de país e continente..." />
  }

  return (
    <div className={['space-y-10', shellClass].filter(Boolean).join(' ')}>
      <PageHeader
        eyebrow="País"
        title="País e continente"
        subtitle={`Distribuição dos vínculos formais segundo o país e o continente de origem. Competência ${displayedLabel} · ${labelScope(displayed.scope)}.`}
        titleClassName={theme.typography.heroTitle.replace(
          'text-slate-900',
          'text-orgmigra-blue-800',
        )}
      />

      <div className={theme.chartCard.grid2Class}>
        <ChartCard
          title="Continente"
          subtitle="Saldo líquido por continente no recorte selecionado."
          hover={false}
        >
          <BarRank
            rows={tblContinente.rows}
            labelKey={GOLD_COLUMNS.CONTINENTE}
            valueKey={GOLD_COLUMNS.SALDO}
            color={palette.ranking.sky}
            highlightTop1
          />
        </ChartCard>
        <ChartCard
          title="Principais países"
          subtitle="Ranking por saldo na competência selecionada."
          hover={false}
        >
          <BarRank
            rows={topCountries}
            labelKey={GOLD_COLUMNS.PAIS}
            valueKey={GOLD_COLUMNS.SALDO}
            color={palette.ranking.yellow}
            highlightTop1
          />
        </ChartCard>
      </div>
    </div>
  )
}
