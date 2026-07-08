import { Link, useSearchParams } from 'react-router-dom'
import { memo, useEffect, useMemo, useRef, useState } from 'react'
import { GOLD_COLUMNS } from '../api/goldColumns'
import { GOLD_TABLES } from '../api/goldTables'
import { fetchOverview, fetchTable } from '../api/gold'
import type { GoldRow, OverviewResponse, Scope } from '../api/types'
import { BarRank } from '../components/charts/BarRank'
import { MovementSplit } from '../components/charts/MovementSplit'
import { ChartCard } from '../components/ui/ChartCard'
import { CountryFlagRank } from '../components/ui/CountryFlagRank'
import { CompareChip } from '../components/ui/CompareChip'
import { ErrorState } from '../components/ui/ErrorState'
import { KpiStat } from '../components/ui/KpiStat'
import { ExecutivePageLoading } from '../components/ui/ExecutivePageLoading'
import { SectionTitle } from '../components/ui/SectionTitle'
import { useScope } from '../context/ScopeContext'
import { useMonth } from '../context/MonthContext'
import { useDisplaySelection } from '../context/DisplaySelectionContext'
import { chartTheme } from '../lib/chartTheme'
import { buildDisplaySelectionKey } from '../lib/displaySelectionKey'
import { formatCompact, labelScope } from '../lib/format'
import { useScopeStableLoading } from '../lib/useScopeStableLoading'
import { theme } from '../lib/theme'

const palette = chartTheme.palette

type ExecutiveKpiDisplay = {
  resumo: GoldRow | null
  prevResumo: GoldRow | null
  previousLabel: string | null
}

const TOP_COUNTRIES_LIMIT = 5
const COMPARE_SCOPES = ['br', 'pr', 'rmc'] as const
const EMPTY_GOLD_ROWS: GoldRow[] = []

type OverviewSyncSnapshot = {
  key: string
  data: OverviewResponse
  kpiDisplay: ExecutiveKpiDisplay
}

type CountriesSyncSnapshot = {
  key: string
  rows: GoldRow[]
}

function publishSyncedExecutiveSnapshot(
  key: string,
  overview: OverviewSyncSnapshot | null,
  countries: CountriesSyncSnapshot | null,
  publish: (snapshot: {
    data: OverviewResponse
    kpiDisplay: ExecutiveKpiDisplay
    countryRows: GoldRow[]
  }) => void,
): void {
  if (overview?.key !== key || countries?.key !== key) return
  publish({
    data: overview.data,
    kpiDisplay: overview.kpiDisplay,
    countryRows: countries.rows,
  })
}

function territoryLink(search: string) {
  return search ? `/territorio?${search}` : '/territorio'
}

function paisLink(search: string) {
  return search ? `/pais?${search}` : '/pais'
}

type ExecutiveCompareChipProps = {
  scopeKey: Scope
  active: boolean
  resumo: GoldRow | null
}

const ExecutiveCompareChip = memo(function ExecutiveCompareChip({
  scopeKey,
  active,
  resumo,
}: ExecutiveCompareChipProps) {
  return (
    <CompareChip
      variant="executive"
      scopeKey={scopeKey}
      label={labelScope(scopeKey)}
      active={active}
      value={
        <>
          {formatCompact(resumo?.[GOLD_COLUMNS.SALDO])}
          <span className="ml-1 text-xs font-normal text-slate-500">saldo</span>
        </>
      }
      detail={
        <>
          adm {formatCompact(resumo?.[GOLD_COLUMNS.ADMISSOES])} · desl{' '}
          {formatCompact(resumo?.[GOLD_COLUMNS.DESLIGAMENTOS])}
        </>
      }
    />
  )
})

export function ExecutivePage() {
  const { scope } = useScope()
  const { ano, mes, previousCompetencia } = useMonth()
  const { displayed, displayedLabel, commitVisualTransition } = useDisplaySelection()
  const [searchParams] = useSearchParams()
  const search = searchParams.toString()
  const [data, setData] = useState<OverviewResponse | null>(null)
  const [kpiDisplay, setKpiDisplay] = useState<ExecutiveKpiDisplay | null>(null)
  const [compare, setCompare] = useState<Partial<Record<Scope, GoldRow | null>>>({})
  const [displayedCountryRows, setDisplayedCountryRows] = useState<GoldRow[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)
  const overviewSyncRef = useRef<OverviewSyncSnapshot | null>(null)
  const countriesSyncRef = useRef<CountriesSyncSnapshot | null>(null)
  const selectionKey = buildDisplaySelectionKey(scope, ano, mes)
  const { beginFetch, abortFetch, shellClass, showInitialLoader } = useScopeStableLoading(
    data,
    selectionKey,
  )

  const publishSyncedSnapshot = (
    key: string,
    overview: OverviewSyncSnapshot | null,
    countries: CountriesSyncSnapshot | null,
  ) => {
    publishSyncedExecutiveSnapshot(key, overview, countries, (snapshot) => {
      setData(snapshot.data)
      setKpiDisplay(snapshot.kpiDisplay)
      setDisplayedCountryRows(snapshot.countryRows)
      commitVisualTransition(key)
    })
  }

  useEffect(() => {
    let cancel = false
    const isCancelled = () => cancel
    beginFetch(isCancelled, () => {
      setErr(null)
    })
    const prev = previousCompetencia
    const reqs: Promise<OverviewResponse>[] = [
      fetchOverview(scope, ano, mes),
      ...(prev ? [fetchOverview(scope, prev.ano, prev.mes)] : []),
    ]
    const selectionKey = buildDisplaySelectionKey(scope, ano, mes)
    Promise.all(reqs)
      .then(([current, prevData]) => {
        if (cancel) return
        const newPrevResumo = prev ? (prevData?.resumo ?? null) : null
        const overviewSnapshot: OverviewSyncSnapshot = {
          key: selectionKey,
          data: current,
          kpiDisplay: {
            resumo: current.resumo,
            prevResumo: newPrevResumo,
            previousLabel: prev?.label ?? null,
          },
        }
        overviewSyncRef.current = overviewSnapshot
        publishSyncedSnapshot(selectionKey, overviewSnapshot, countriesSyncRef.current)
      })
      .catch((e: unknown) => {
        if (!cancel) {
          setErr(e instanceof Error ? e.message : 'Falha ao carregar')
          abortFetch()
        }
      })
    return () => {
      cancel = true
      abortFetch()
    }
  }, [scope, ano, mes, previousCompetencia, retryKey, beginFetch, abortFetch])

  useEffect(() => {
    let cancel = false
    const scopes: Scope[] = ['br', 'pr', 'rmc']
    Promise.all(scopes.map((s) => fetchOverview(s, ano, mes)))
      .then((rows) => {
        if (cancel) return
        const next: Partial<Record<Scope, GoldRow | null>> = {}
        rows.forEach((r, i) => {
          next[scopes[i]] = r.resumo
        })
        setCompare(next)
      })
      .catch(() => {
        /* comparativo é opcional */
      })
    return () => {
      cancel = true
    }
  }, [ano, mes])

  useEffect(() => {
    let cancel = false
    const selectionKey = buildDisplaySelectionKey(scope, ano, mes)
    fetchTable(GOLD_TABLES.TABELA_PAIS, scope, ano, mes, {
      limit: TOP_COUNTRIES_LIMIT,
      sort_by: GOLD_COLUMNS.SALDO,
      sort_dir: 'desc',
    })
      .then((res) => {
        if (cancel) return
        const countriesSnapshot: CountriesSyncSnapshot = {
          key: selectionKey,
          rows: res.rows,
        }
        countriesSyncRef.current = countriesSnapshot
        publishSyncedSnapshot(selectionKey, overviewSyncRef.current, countriesSnapshot)
      })
      .catch(() => {
        if (cancel) return
        const countriesSnapshot: CountriesSyncSnapshot = {
          key: selectionKey,
          rows: [],
        }
        countriesSyncRef.current = countriesSnapshot
        publishSyncedSnapshot(selectionKey, overviewSyncRef.current, countriesSnapshot)
      })
    return () => {
      cancel = true
    }
  }, [scope, ano, mes, retryKey])

  const overviewMatchesSelection =
    data?.month.ano === displayed.ano &&
    data?.month.mes === displayed.mes &&
    data?.scope === displayed.scope

  const countriesSectionAction = useMemo(
    () =>
      overviewMatchesSelection && displayedCountryRows.length > 0 ? (
        <Link to={paisLink(search)} className={theme.chartCard.actionClass}>
          Ver página País
        </Link>
      ) : undefined,
    [overviewMatchesSelection, displayedCountryRows.length, search],
  )

  const ufChartAction = useMemo(
    () =>
      scope === 'br' ? (
        <Link to={territoryLink(search)} className={theme.chartCard.actionClass}>
          Ver todas
        </Link>
      ) : undefined,
    [scope, search],
  )

  const municipioChartAction = useMemo(
    () => (
      <Link to={territoryLink(search)} className={theme.chartCard.actionClass}>
        Ver todos
      </Link>
    ),
    [search],
  )

  const topSetorRows = useMemo(
    () => data?.rankings.setor.slice(0, 10) ?? EMPTY_GOLD_ROWS,
    [data?.rankings.setor],
  )

  if (err) {
    return <ErrorState message={err} onRetry={() => setRetryKey((k) => k + 1)} />
  }

  if (showInitialLoader || !data || !kpiDisplay) {
    return <ExecutivePageLoading />
  }

  const kpiPreviousLabel = kpiDisplay.previousLabel ?? undefined
  const kpiHasCompare = kpiDisplay.previousLabel !== null

  return (
    <div className={theme.executive.pageStack}>
      <div className={theme.executive.heroSection}>
        <h1 className={theme.executive.heroTitle}>
          Movimentação de migrantes no emprego formal
        </h1>
        <p className={theme.executive.heroSubtitle}>
          Migrantes · {labelScope(displayed.scope)} · competência {displayedLabel} · base filtrada
          de migrantes
        </p>
        <p className="mt-2 text-xs leading-relaxed text-slate-500">
          Indicadores referentes exclusivamente a migrantes — não representam o CAGED nacional
          completo.
        </p>
      </div>

      <div className={theme.executive.kpiGrid}>
        <KpiStat
          variant="executive"
          executiveAccent="blue"
          label="Admissões"
          value={kpiDisplay.resumo?.[GOLD_COLUMNS.ADMISSOES]}
          prevValue={kpiHasCompare ? kpiDisplay.prevResumo?.[GOLD_COLUMNS.ADMISSOES] : undefined}
          previousLabel={kpiPreviousLabel}
        />
        <KpiStat
          variant="executive"
          executiveAccent="purple"
          label="Desligamentos"
          value={kpiDisplay.resumo?.[GOLD_COLUMNS.DESLIGAMENTOS]}
          prevValue={kpiHasCompare ? kpiDisplay.prevResumo?.[GOLD_COLUMNS.DESLIGAMENTOS] : undefined}
          previousLabel={kpiPreviousLabel}
        />
        <KpiStat
          variant="executive"
          executiveAccent="green"
          label="Saldo"
          value={kpiDisplay.resumo?.[GOLD_COLUMNS.SALDO]}
          prevValue={kpiHasCompare ? kpiDisplay.prevResumo?.[GOLD_COLUMNS.SALDO] : undefined}
          previousLabel={kpiPreviousLabel}
          valueToneFromDelta
        />
      </div>

      <section className="space-y-3">
        <SectionTitle
          className="mb-0"
          title="Top 5 nacionalidades por saldo líquido"
          subtitle="Ranking das nacionalidades com maior saldo positivo no mês selecionado."
          action={countriesSectionAction}
        />

        <CountryFlagRank rows={displayedCountryRows} />
      </section>

      <div className={shellClass || undefined}>
      <div className={theme.executive.compareSection}>
        <SectionTitle
          title="Comparativo rápido de escopos"
          subtitle="Visão lado a lado do saldo líquido, admissões e desligamentos no mês selecionado."
        />
        <div className={theme.executive.compareGrid}>
          {COMPARE_SCOPES.map((s) => (
            <ExecutiveCompareChip
              key={s}
              scopeKey={s}
              active={scope === s}
              resumo={compare[s] ?? null}
            />
          ))}
        </div>
      </div>

      <div className={theme.executive.chartGrid}>
        <ChartCard
          surface="executive"
          className={theme.executive.chartHoverClass}
          title="UF — maiores saldos"
          subtitle={
            scope === 'br'
              ? 'Ranking por saldo líquido de emprego no mês selecionado.'
              : 'Indisponível fora do escopo Brasil'
          }
          action={ufChartAction}
        >
          {data.rankings.uf?.length ? (
            <BarRank
              rows={data.rankings.uf}
              labelKey={GOLD_COLUMNS.UF}
              valueKey={GOLD_COLUMNS.SALDO}
              color={palette.territory.primary}
              highlightTop1
            />
          ) : (
            <p className="text-sm text-slate-500">Selecione o escopo Brasil para ver o ranking por UF.</p>
          )}
        </ChartCard>

        <ChartCard
          surface="executive"
          className={theme.executive.chartHoverClass}
          title="Municípios — top saldos"
          subtitle="Ranking por saldo líquido de emprego no recorte selecionado."
          action={municipioChartAction}
        >
          <BarRank
            rows={data.rankings.municipio}
            labelKey={GOLD_COLUMNS.MUNICIPIO}
            valueKey={GOLD_COLUMNS.SALDO}
            color={palette.territory.municipio}
            yAxisInterval={0}
            highlightTop1
          />
        </ChartCard>

        <ChartCard
          surface="executive"
          className={theme.executive.chartHoverClass}
          title="Setores — composição da movimentação"
          subtitle="Comparação entre admissões e desligamentos por setor no mês selecionado."
        >
          <MovementSplit rows={topSetorRows} labelKey={GOLD_COLUMNS.SECAO} />
        </ChartCard>

        <ChartCard
          surface="executive"
          className={theme.executive.chartHoverClass}
          title="Ocupações — liderança em saldo"
          subtitle="Ocupações com maior saldo líquido de emprego no período selecionado."
        >
          <BarRank
            rows={data.rankings.ocupacao}
            labelKey={GOLD_COLUMNS.CBO_OCUPACAO}
            valueKey={GOLD_COLUMNS.SALDO}
            color={palette.occupation.primary}
            highlightTop1
          />
        </ChartCard>
      </div>
      </div>
    </div>
  )
}
