import { useEffect, useState } from 'react'
import { GOLD_COLUMNS } from '../api/goldColumns'
import { GOLD_TABLES } from '../api/goldTables'
import { fetchOverview, fetchTable } from '../api/gold'
import type { OverviewResponse, TableResponse } from '../api/types'
import { BarRank } from '../components/charts/BarRank'
import { CategoricalHeatmap } from '../components/charts/CategoricalHeatmap'
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
import { buildDisplaySelectionKey } from '../lib/displaySelectionKey'
import { formatCurrencyBRL, labelScope } from '../lib/format'
import { theme } from '../lib/theme'
import { useScopeStableLoading } from '../lib/useScopeStableLoading'

const palette = chartTheme.palette

export function SalaryPage() {
  const { scope } = useScope()
  const { ano, mes } = useMonth()
  const [ov, setOv] = useState<OverviewResponse | null>(null)
  const [tables, setTables] = useState<Record<string, TableResponse | null>>({})
  const [err, setErr] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)
  const { displayed, displayedLabel, commitVisualTransition } = useDisplaySelection()
  const selectionKey = buildDisplaySelectionKey(scope, ano, mes)
  const { beginFetch, abortFetch, shellClass, showInitialLoader } = useScopeStableLoading(
    ov,
    selectionKey,
  )
  const [tableOpen, setTableOpen] = useState({
    sexo: false,
    faixa: false,
    instrucao: false,
    sx_fx: false,
    sx_ins: false,
    fx_ins: false,
  })

  useEffect(() => {
    let c = false
    const isCancelled = () => c
    beginFetch(isCancelled, () => {
      setErr(null)
    })
    Promise.all([
      fetchOverview(scope, ano, mes),
      fetchTable(GOLD_TABLES.PERFIL_SEXO_SALARIO, scope, ano, mes, {
        limit: 50,
        sort_by: GOLD_COLUMNS.SALDO,
      }),
      fetchTable(GOLD_TABLES.PERFIL_FAIXA_ETARIA_SALARIO, scope, ano, mes, {
        limit: 80,
        sort_by: GOLD_COLUMNS.SALDO,
      }),
      fetchTable(GOLD_TABLES.PERFIL_GRAUDEINSTRUCAO_SALARIO, scope, ano, mes, {
        limit: 80,
        sort_by: GOLD_COLUMNS.SALDO,
      }),
      fetchTable(GOLD_TABLES.PERFIL_SEXO_FAIXA_ETARIA_SALARIO, scope, ano, mes, {
        limit: 200,
        sort_by: GOLD_COLUMNS.SALDO,
      }),
      fetchTable(GOLD_TABLES.PERFIL_SEXO_INSTRUCAO_SALARIO, scope, ano, mes, {
        limit: 200,
        sort_by: GOLD_COLUMNS.SALDO,
      }),
      fetchTable(GOLD_TABLES.PERFIL_FAIXA_ETARIA_INSTRUCAO_SALARIO, scope, ano, mes, {
        limit: 200,
        sort_by: GOLD_COLUMNS.SALDO,
      }),
    ])
      .then(([o, a, b, d, e, f, g]) => {
        if (c) return
        setOv(o)
        setTables({
          sexo: a,
          faixa: b,
          instrucao: d,
          sx_fx: e,
          sx_ins: f,
          fx_ins: g,
        })
        commitVisualTransition(selectionKey)
      })
      .catch((e: unknown) => {
        if (!c) {
          setErr(e instanceof Error ? e.message : 'Erro')
          abortFetch()
        }
      })
    return () => {
      c = true
      abortFetch()
    }
  }, [scope, ano, mes, retryKey, beginFetch, abortFetch, selectionKey, commitVisualTransition])

  if (err) {
    return <ErrorState message={err} onRetry={() => setRetryKey((k) => k + 1)} />
  }
  if (showInitialLoader || !ov) {
    return <LoadingState label="Carregando indicadores de salário..." />
  }

  const salSexo = ov.salary_profiles[GOLD_COLUMNS.SEXO]?.[0]

  return (
    <div className={['space-y-10', shellClass].filter(Boolean).join(' ')}>
      <PageHeader
        eyebrow="Salários"
        title={`Remuneração · ${labelScope(displayed.scope)}`}
        subtitle={`Competência ${displayedLabel}`}
        titleClassName={theme.typography.heroTitle.replace(
          'text-slate-900',
          'text-orgmigra-blue-800',
        )}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className={theme.kpiTile.baseClass}>
          <p
            className={theme.kpiTile.labelClass.replace(
              'text-slate-600',
              'text-orgmigra-blue-800',
            )}
          >
            Mediana (1º grupo)
          </p>
          <p
            className={[theme.kpiTile.valueClass, theme.kpiTile.toneNeutral].join(' ')}
            aria-label={`Mediana salarial: ${formatCurrencyBRL(salSexo?.[GOLD_COLUMNS.SALARIO_MEDIANO])}`}
          >
            {formatCurrencyBRL(salSexo?.[GOLD_COLUMNS.SALARIO_MEDIANO])}
          </p>
          <p className={theme.kpiTile.hintClass}>Mediana salarial no recorte selecionado.</p>
        </div>
        <div className="lg:col-span-2">
          <ChartCard
            title="Saldo vs salário médio (sexo)"
            subtitle="Comparação por sexo usando salário médio (referência do mês selecionado)."
            hover={false}
            action={
              tables.sexo ? (
                <TableToggleButton
                  open={tableOpen.sexo}
                  onToggle={() => setTableOpen((s) => ({ ...s, sexo: !s.sexo }))}
                />
              ) : null
            }
          >
            <BarRank
              rows={ov.salary_profiles[GOLD_COLUMNS.SEXO]}
              labelKey={GOLD_COLUMNS.SEXO}
              valueKey={GOLD_COLUMNS.SALARIO_MEDIO}
              color={palette.salary.primary}
              highlightTop1
            />
            {tables.sexo ? (
              <ChartTablePanel open={tableOpen.sexo}>
                <DataGrid columns={tables.sexo.columns} rows={tables.sexo.rows} />
              </ChartTablePanel>
            ) : null}
          </ChartCard>
        </div>
      </div>

      <div className={theme.chartCard.grid2Class}>
        <ChartCard
          title="Faixa etária — salário médio"
          subtitle="Ranking por faixa etária usando salário médio (mês selecionado)."
          hover={false}
          action={
            tables.faixa ? (
              <TableToggleButton
                open={tableOpen.faixa}
                onToggle={() => setTableOpen((s) => ({ ...s, faixa: !s.faixa }))}
              />
            ) : null
          }
        >
          <BarRank
            rows={ov.salary_profiles[GOLD_COLUMNS.FAIXA_ETARIA]}
            labelKey={GOLD_COLUMNS.FAIXA_ETARIA}
            valueKey={GOLD_COLUMNS.SALARIO_MEDIO}
            color={palette.salary.secondary}
            highlightTop1
          />
          {tables.faixa ? (
            <ChartTablePanel open={tableOpen.faixa}>
              <DataGrid
                columns={tables.faixa.columns}
                rows={tables.faixa.rows}
                maxHeightClass="max-h-[480px]"
              />
            </ChartTablePanel>
          ) : null}
        </ChartCard>
        <ChartCard
          title="Instrução — salário médio"
          subtitle="Ranking por escolaridade usando salário médio (mês selecionado)."
          hover={false}
          action={
            tables.instrucao ? (
              <TableToggleButton
                open={tableOpen.instrucao}
                onToggle={() => setTableOpen((s) => ({ ...s, instrucao: !s.instrucao }))}
              />
            ) : null
          }
        >
          <BarRank
            rows={ov.salary_profiles[GOLD_COLUMNS.GRAUDEINSTRUCAO]}
            labelKey={GOLD_COLUMNS.GRAUDEINSTRUCAO}
            valueKey={GOLD_COLUMNS.SALARIO_MEDIO}
            color={palette.salary.average}
            highlightTop1
          />
          {tables.instrucao ? (
            <ChartTablePanel open={tableOpen.instrucao}>
              <DataGrid
                columns={tables.instrucao.columns}
                rows={tables.instrucao.rows}
                maxHeightClass="max-h-[480px]"
              />
            </ChartTablePanel>
          ) : null}
        </ChartCard>
      </div>

      <div className={theme.chartCard.grid2Class}>
        {tables.sx_fx ? (
          <ChartCard
            title="Sexo × faixa etária"
            subtitle="Intensidade por salário médio em cada combinação."
            hover={false}
            action={
              <TableToggleButton
                open={tableOpen.sx_fx}
                onToggle={() => setTableOpen((s) => ({ ...s, sx_fx: !s.sx_fx }))}
              />
            }
          >
            <CategoricalHeatmap
              rows={tables.sx_fx.rows}
              rowKey={GOLD_COLUMNS.SEXO}
              colKey={GOLD_COLUMNS.FAIXA_ETARIA}
              rowAxisLabel="Sexo"
              colAxisLabel="Faixa etária"
            />
            <ChartTablePanel open={tableOpen.sx_fx}>
              <DataGrid
                columns={tables.sx_fx.columns}
                rows={tables.sx_fx.rows}
                maxHeightClass="max-h-[480px]"
              />
            </ChartTablePanel>
          </ChartCard>
        ) : null}

        {tables.sx_ins ? (
          <ChartCard
            title="Sexo × instrução"
            subtitle="Intensidade por salário médio em cada combinação."
            hover={false}
            action={
              <TableToggleButton
                open={tableOpen.sx_ins}
                onToggle={() => setTableOpen((s) => ({ ...s, sx_ins: !s.sx_ins }))}
              />
            }
          >
            <CategoricalHeatmap
              rows={tables.sx_ins.rows}
              rowKey={GOLD_COLUMNS.SEXO}
              colKey={GOLD_COLUMNS.GRAUDEINSTRUCAO}
              rowAxisLabel="Sexo"
              colAxisLabel="Instrução"
              wide
            />
            <ChartTablePanel open={tableOpen.sx_ins}>
              <DataGrid
                columns={tables.sx_ins.columns}
                rows={tables.sx_ins.rows}
                maxHeightClass="max-h-[480px]"
              />
            </ChartTablePanel>
          </ChartCard>
        ) : null}
      </div>

      {tables.fx_ins ? (
        <ChartCard
          title="Faixa etária × instrução"
          subtitle="Matriz ampla — intensidade por salário médio em cada combinação."
          hover={false}
          action={
            <TableToggleButton
              open={tableOpen.fx_ins}
              onToggle={() => setTableOpen((s) => ({ ...s, fx_ins: !s.fx_ins }))}
            />
          }
        >
          <CategoricalHeatmap
            rows={tables.fx_ins.rows}
            rowKey={GOLD_COLUMNS.FAIXA_ETARIA}
            colKey={GOLD_COLUMNS.GRAUDEINSTRUCAO}
            rowAxisLabel="Faixa etária"
            colAxisLabel="Instrução"
            wide
          />
          <ChartTablePanel open={tableOpen.fx_ins}>
            <DataGrid
              columns={tables.fx_ins.columns}
              rows={tables.fx_ins.rows}
              maxHeightClass="max-h-[480px]"
            />
          </ChartTablePanel>
        </ChartCard>
      ) : null}
    </div>
  )
}
