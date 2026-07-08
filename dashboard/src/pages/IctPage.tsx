import { useCallback, useEffect, useMemo, useState } from 'react'
import { FileText } from 'lucide-react'
import { GOLD_COLUMNS } from '../api/goldColumns'
import { GOLD_TABLES } from '../api/goldTables'
import { fetchTable } from '../api/gold'
import { fetchIctReportContext } from '../api/ictReport'
import type { IctReportContextResponse } from '../api/ictReportTypes'
import type { Scope, TableResponse } from '../api/types'
import { BarRank } from '../components/charts/BarRank'
import { IctReportPanel } from '../components/ict/IctReportPanel'
import { IctMap } from '../components/map/IctMap'
import { useTerritoryGeoJson } from '../components/map/useTerritoryGeoJson'
import { ChartCard } from '../components/ui/ChartCard'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'
import { KpiStat } from '../components/ui/KpiStat'
import { LoadingState } from '../components/ui/LoadingState'
import { PageHeader } from '../components/ui/PageHeader'
import { useScope } from '../context/ScopeContext'
import { useMonth } from '../context/MonthContext'
import { useDisplaySelection } from '../context/DisplaySelectionContext'
import { API_TABLE_MAX_LIMIT } from '../lib/apiLimits'
import { chartTheme } from '../lib/chartTheme'
import { buildDisplaySelectionKey } from '../lib/displaySelectionKey'
import { labelScope } from '../lib/format'
import { buildTopIcttRanking, computeIcttKpis } from '../lib/ictMetrics'
import { useScopeStableLoading } from '../lib/useScopeStableLoading'
import { theme } from '../lib/theme'

const palette = chartTheme.palette

const ICT_UNAVAILABLE_TITLE =
  'O ICT está disponível inicialmente apenas para municípios do Paraná.'

const ICT_UNAVAILABLE_SUBTEXT: Record<Exclude<Scope, 'pr'>, string> = {
  br: 'Selecione o escopo Paraná para visualizar o Índice de Competitividade do Trabalho calculado a partir da movimentação formal de trabalhadores migrantes.',
  rmc: 'A análise municipal completa do ICT foi calculada para o escopo Paraná. A visualização específica da RMC poderá ser incorporada em etapa posterior.',
}

function IctScopeUnavailable({ scope }: { scope: Exclude<Scope, 'pr'> }) {
  return (
    <EmptyState title={ICT_UNAVAILABLE_TITLE} description={ICT_UNAVAILABLE_SUBTEXT[scope]} />
  )
}

export function IctPage() {
  const { scope } = useScope()
  const { ano, mes } = useMonth()
  const { displayed, displayedLabel, commitVisualTransition, isTransitioning } = useDisplaySelection()
  const isPrScope = scope === 'pr'

  const [tbl, setTbl] = useState<TableResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)

  const [reportOpen, setReportOpen] = useState(false)
  const [reportData, setReportData] = useState<IctReportContextResponse | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const [reportLoadedKey, setReportLoadedKey] = useState<string | null>(null)

  const reportKey = buildDisplaySelectionKey('pr', ano, mes)
  const reportStale = Boolean(reportData && reportLoadedKey !== reportKey)

  const loadReport = useCallback(async () => {
    setReportLoading(true)
    setReportError(null)
    try {
      const data = await fetchIctReportContext('pr', ano, mes)
      setReportData(data)
      setReportLoadedKey(reportKey)
    } catch (e: unknown) {
      setReportError(
        e instanceof Error
          ? e.message
          : 'Não foi possível carregar o relatório determinístico do ICT para esta competência.',
      )
    } finally {
      setReportLoading(false)
    }
  }, [ano, mes, reportKey])

  const handleOpenReport = () => {
    setReportOpen(true)
    if (reportLoadedKey === reportKey && reportData) return
    void loadReport()
  }

  const selectionKey = buildDisplaySelectionKey(scope, ano, mes)
  const { beginFetch, abortFetch, shellClass, showInitialLoader } = useScopeStableLoading(
    isPrScope ? tbl : null,
    selectionKey,
  )

  const { geoJson, geoLoading, geoError } = useTerritoryGeoJson('pr')

  useEffect(() => {
    if (!isPrScope) {
      setTbl(null)
      setErr(null)
      return
    }

    let cancelled = false
    const isCancelled = () => cancelled
    beginFetch(isCancelled, () => {
      setErr(null)
    })

    fetchTable(GOLD_TABLES.ICTT_MUNICIPIO, 'pr', ano, mes, {
      limit: API_TABLE_MAX_LIMIT,
      sort_by: GOLD_COLUMNS.RANKING_ICTT,
      sort_dir: 'asc',
    })
      .then((data) => {
        if (cancelled) return
        setTbl(data)
        commitVisualTransition(selectionKey)
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : 'Erro ao carregar ICT')
          abortFetch()
        }
      })

    return () => {
      cancelled = true
      abortFetch()
    }
  }, [
    isPrScope,
    ano,
    mes,
    retryKey,
    beginFetch,
    abortFetch,
    selectionKey,
    commitVisualTransition,
  ])

  const kpis = useMemo(
    () => (tbl?.rows?.length ? computeIcttKpis(tbl.rows) : null),
    [tbl],
  )

  const topRanking = useMemo(
    () => (tbl?.rows?.length ? buildTopIcttRanking(tbl.rows, 20) : []),
    [tbl],
  )

  if (!isPrScope) {
    return (
      <div className="space-y-10">
        <PageHeader
          eyebrow="ICT"
          title="Índice de Competitividade do Trabalho"
          subtitle="Indicador territorial calculado a partir da movimentação formal de trabalhadores migrantes."
          titleClassName={theme.typography.heroTitle.replace(
            'text-slate-900',
            'text-orgmigra-blue-800',
          )}
        />
        <IctScopeUnavailable scope={scope} />
      </div>
    )
  }

  if (err) {
    return <ErrorState message={err} onRetry={() => setRetryKey((k) => k + 1)} />
  }

  if (showInitialLoader || !tbl) {
    return <LoadingState label="Carregando dados do ICT..." />
  }

  if (tbl.rows.length === 0) {
    return (
      <div className="space-y-10">
        <PageHeader
          eyebrow="ICT"
          title="Índice de Competitividade do Trabalho"
          subtitle="Indicador territorial calculado a partir da movimentação formal de trabalhadores migrantes."
        />
        <EmptyState
          title="Sem dados ICT para esta competência"
          description={`Não há registros ICT para ${labelScope('pr')} na competência ${displayedLabel}.`}
        />
      </div>
    )
  }

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="ICT"
        title="Índice de Competitividade do Trabalho"
        subtitle={`Indicador territorial calculado a partir da movimentação formal de trabalhadores migrantes · ${labelScope(displayed.scope)} · competência ${displayedLabel}`}
        titleClassName={theme.typography.heroTitle.replace(
          'text-slate-900',
          'text-orgmigra-blue-800',
        )}
        action={
          <button
            type="button"
            onClick={handleOpenReport}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-orgmigra-blue-200 hover:bg-orgmigra-blue-50 hover:text-orgmigra-blue-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-orgmigra-blue-600/30"
          >
            <FileText className="h-4 w-4" aria-hidden />
            Relatório
          </button>
        }
      />

      <IctReportPanel
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        competenciaLabel={displayedLabel}
        loading={reportLoading}
        error={reportError}
        data={reportData}
        stale={reportStale}
        onRetry={() => void loadReport()}
        onReload={() => void loadReport()}
      />

      <div className={['grid gap-4 sm:grid-cols-2 xl:grid-cols-4', shellClass].filter(Boolean).join(' ')}>
        <KpiStat
          variant="executive"
          executiveAccent="blue"
          label="Municípios com ICT calculado"
          value={kpis?.calculatedCount ?? 0}
        />
        <KpiStat
          variant="executive"
          executiveAccent="green"
          label="ICT médio"
          value={kpis?.meanIctt ?? null}
          valueFormat="decimal1"
        />
        <KpiStat
          variant="executive"
          executiveAccent="purple"
          label="Maior ICT"
          value={kpis?.topIctt ?? null}
          valueFormat="decimal1"
          hint={kpis?.topMunicipio ?? undefined}
        />
        <KpiStat
          variant="executive"
          executiveAccent="blue"
          label="Sem movimentação migratória suficiente"
          value={kpis?.insufficientCount ?? 0}
        />
      </div>

      <IctMap
        rows={tbl.rows}
        competenciaLabel={displayedLabel}
        geoJson={geoJson}
        geoLoading={geoLoading}
        geoError={geoError}
        refreshing={isTransitioning}
      />

      <div className={['space-y-10', shellClass].filter(Boolean).join(' ')}>
        <ChartCard
          title="Top 20 municípios por ICT"
          subtitle="Ordenado por ranking ICT (menor posição = maior índice). Municípios sem ICT calculado são excluídos."
        >
          <BarRank
            rows={topRanking}
            labelKey={GOLD_COLUMNS.MUNICIPIO}
            valueKey={GOLD_COLUMNS.ICTT}
            color={palette.territory.primary}
            yAxisInterval={0}
            highlightTop1
          />
        </ChartCard>
      </div>
    </div>
  )
}
