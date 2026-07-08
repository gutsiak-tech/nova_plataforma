import { useEffect, useRef, useState } from 'react'
import { GOLD_COLUMNS } from '../api/goldColumns'
import { GOLD_TABLES } from '../api/goldTables'
import { fetchTable } from '../api/gold'
import type { GoldRow, TableResponse } from '../api/types'
import { BarRank } from '../components/charts/BarRank'
import { MovementSplit } from '../components/charts/MovementSplit'
import { TerritoryMap } from '../components/map/TerritoryMap'
import { useTerritoryGeoJson } from '../components/map/useTerritoryGeoJson'
import { DataGrid } from '../components/table/DataGrid'
import { ChartCard } from '../components/ui/ChartCard'
import { ChartTablePanel, TableToggleButton } from '../components/ui/ChartTableToggle'
import { ErrorState } from '../components/ui/ErrorState'
import { LoadingState } from '../components/ui/LoadingState'
import { PageHeader } from '../components/ui/PageHeader'
import { useScope } from '../context/ScopeContext'
import { useMonth } from '../context/MonthContext'
import { useDisplaySelection } from '../context/DisplaySelectionContext'
import { chartTheme } from '../lib/chartTheme'
import { TERRITORY_TABLE_LIMIT } from '../lib/apiLimits'
import { buildDisplaySelectionKey } from '../lib/displaySelectionKey'
import { formatInt, labelScope } from '../lib/format'
import { useScopeStableLoading } from '../lib/useScopeStableLoading'
import { theme } from '../lib/theme'

const palette = chartTheme.palette
const TERRITORY_SORT_BY = GOLD_COLUMNS.SALDO
const TERRITORY_SORT_DIR = 'desc' as const

export function TerritoryPage() {
  const { scope } = useScope()
  const { ano, mes } = useMonth()
  const { displayed, displayedLabel, commitVisualTransition, isTransitioning } = useDisplaySelection()
  const [tbl, setTbl] = useState<TableResponse | null>(null)
  const [ufRows, setUfRows] = useState<GoldRow[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)
  const [tableOpen, setTableOpen] = useState(false)
  const municipalityBufferRef = useRef<TableResponse | null>(null)
  const ufBufferRef = useRef<GoldRow[] | null | undefined>(undefined)
  const selectionKey = buildDisplaySelectionKey(scope, ano, mes)
  const { beginFetch, abortFetch, shellClass, showInitialLoader } = useScopeStableLoading(
    tbl,
    selectionKey,
  )
  const { geoJson, geoLoading, geoError } = useTerritoryGeoJson(displayed.scope)

  const tryCommitTerritory = (key: string, requestedScope: typeof scope) => {
    const municipality = municipalityBufferRef.current
    if (!municipality) return
    if (requestedScope === 'br' && ufBufferRef.current === undefined) return

    setTbl(municipality)
    if (requestedScope === 'br') {
      setUfRows(ufBufferRef.current ?? [])
    }
    commitVisualTransition(key)
    municipalityBufferRef.current = null
    ufBufferRef.current = undefined
  }

  useEffect(() => {
    let cancelled = false
    const isCancelled = () => cancelled
    const key = buildDisplaySelectionKey(scope, ano, mes)
    municipalityBufferRef.current = null
    ufBufferRef.current = scope === 'br' ? undefined : null
    beginFetch(isCancelled, () => {
      setErr(null)
    })
    fetchTable(GOLD_TABLES.MUNICIPIO, scope, ano, mes, {
      limit: TERRITORY_TABLE_LIMIT,
      sort_by: TERRITORY_SORT_BY,
      sort_dir: TERRITORY_SORT_DIR,
    })
      .then((d) => {
        if (cancelled) return
        municipalityBufferRef.current = d
        tryCommitTerritory(key, scope)
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
  }, [scope, ano, mes, retryKey, beginFetch, abortFetch, selectionKey])

  useEffect(() => {
    if (scope !== 'br') return

    let cancelled = false
    const key = buildDisplaySelectionKey(scope, ano, mes)
    ufBufferRef.current = undefined
    fetchTable(GOLD_TABLES.UF, 'br', ano, mes, { limit: 50 })
      .then((d) => {
        if (cancelled) return
        ufBufferRef.current = d.rows
        tryCommitTerritory(key, scope)
      })
      .catch(() => {
        if (cancelled) return
        ufBufferRef.current = []
        tryCommitTerritory(key, scope)
      })
    return () => {
      cancelled = true
    }
  }, [scope, ano, mes, retryKey, selectionKey])

  if (err) {
    return <ErrorState message={err} onRetry={() => setRetryKey((k) => k + 1)} />
  }

  if (showInitialLoader || !tbl) {
    return <LoadingState label="Carregando dados territoriais..." />
  }

  const top = tbl.rows.slice(0, 14)
  const displayedUntil = tbl.offset + tbl.count
  const isPartial = displayedUntil < tbl.total
  const mapScope = displayed.scope

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="Território"
        title={`Municípios · ${labelScope(displayed.scope)}`}
        subtitle={`${tbl.count.toLocaleString('pt-BR')} registros exibidos · ${tbl.total.toLocaleString('pt-BR')} no recorte · competência ${displayedLabel}`}
        titleClassName={theme.typography.heroTitle.replace(
          'text-slate-900',
          'text-orgmigra-blue-800',
        )}
      />

      <TerritoryMap
        scope={mapScope}
        municipalityRows={tbl.rows}
        ufRows={mapScope === 'br' ? ufRows : null}
        competenciaLabel={displayedLabel}
        geoJson={geoJson}
        geoLoading={geoLoading}
        geoError={geoError}
        refreshing={isTransitioning}
      />

      {isPartial ? (
        <p className="rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-600">
          Exibindo os{' '}
          <span className="font-medium text-slate-300">{formatInt(tbl.count)}</span> municípios com
          maior saldo em <span className="font-medium text-slate-300">{labelScope(displayed.scope)}</span> na
          competência <span className="font-medium text-slate-300">{displayedLabel}</span>. O recorte possui{' '}
          <span className="font-medium text-slate-300">{formatInt(tbl.total)}</span> municípios no
          total — a API retorna até{' '}
          <span className="font-medium text-slate-300">{formatInt(TERRITORY_TABLE_LIMIT)}</span>{' '}
          registros por consulta. A paginação completa da base territorial será disponibilizada em
          etapa futura.
        </p>
      ) : null}

      <div className={['space-y-10', shellClass].filter(Boolean).join(' ')}>
      <div className={theme.chartCard.grid2Class}>
        <ChartCard
          title="Principais municípios por saldo"
          subtitle={`Top ${top.length} entre os registros carregados (ordenados por saldo).`}
          action={
            <TableToggleButton open={tableOpen} onToggle={() => setTableOpen((v) => !v)} />
          }
        >
          <BarRank
            rows={top}
            labelKey={GOLD_COLUMNS.MUNICIPIO}
            valueKey={GOLD_COLUMNS.SALDO}
            color={palette.territory.primary}
            yAxisInterval={0}
            highlightTop1
          />
          <ChartTablePanel open={tableOpen}>
            <DataGrid columns={tbl.columns} rows={tbl.rows} />
          </ChartTablePanel>
        </ChartCard>
        <ChartCard
          title="Movimentação (top 10)"
          subtitle="Comparação entre admissões e desligamentos dos 10 municípios líderes em saldo."
        >
          <MovementSplit rows={top.slice(0, 10)} labelKey={GOLD_COLUMNS.MUNICIPIO} />
        </ChartCard>
      </div>
      </div>
    </div>
  )
}
