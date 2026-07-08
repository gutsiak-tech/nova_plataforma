import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import clsx from 'clsx'
import { X } from 'lucide-react'
import type {
  IctReportContext,
  IctReportContextResponse,
  IctReportDiagnosticFlagItem,
  IctReportDimensionSummary,
  IctReportMonthlyEvolutionItem,
  IctReportRankItem,
} from '../../api/ictReportTypes'
import { formatDecimal1, formatInt, labelScope } from '../../lib/format'
import { theme } from '../../lib/theme'
import { ErrorState } from '../ui/ErrorState'
import { LoadingState } from '../ui/LoadingState'

const DIMENSION_LABELS: Record<string, string> = {
  dim_dinamismo: 'Dinamismo',
  dim_remuneracao: 'Remuneração',
  dim_qualidade_emprego: 'Qualidade do Emprego',
  dim_perfil_trabalhador: 'Perfil do Trabalhador',
  dim_complexidade: 'Complexidade',
}

const FLAG_SECTIONS: Array<{
  key: keyof IctReportContext['diagnostic_flags']
  title: string
}> = [
  { key: 'leaders_with_negative_quality', title: 'Líderes com qualidade negativa' },
  { key: 'leaders_with_negative_remuneration', title: 'Líderes com remuneração negativa' },
  { key: 'high_dynamism_low_quality', title: 'Alto dinamismo e baixa qualidade' },
  { key: 'high_complexity_low_remuneration', title: 'Alta complexidade e baixa remuneração' },
]

function formatReportNumber(value: unknown, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—'
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(Number(value))
}

function SectionTitle({ children }: { children: string }) {
  return <h3 className={theme.typography.sectionTitle}>{children}</h3>
}

function SectionSubtitle({ children }: { children: string }) {
  return <p className={theme.typography.sectionSubtitle}>{children}</p>
}

function SummaryGrid({ context }: { context: IctReportContext }) {
  const { summary } = context
  const items = [
    ['Municípios totais', formatInt(summary.municipios_total)],
    ['Municípios com ICT', formatInt(summary.municipios_com_ict)],
    ['Sem base suficiente', formatInt(summary.municipios_sem_base)],
    ['Percentual com ICT', summary.percentual_com_ict != null ? `${formatReportNumber(summary.percentual_com_ict, 1)}%` : '—'],
    ['ICT médio', formatDecimal1(summary.ict_medio)],
    ['ICT mediano', formatDecimal1(summary.ict_mediano)],
    ['ICT máximo', formatDecimal1(summary.ict_maximo)],
    ['Município líder', summary.municipio_lider ?? '—'],
  ] as const

  return (
    <dl className="grid gap-3 sm:grid-cols-2">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-xl border border-slate-200 bg-slate-50/60 px-3 py-2.5">
          <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</dt>
          <dd className="mt-1 text-sm font-semibold text-slate-900">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function SimpleTable({
  headers,
  rows,
}: {
  headers: string[]
  rows: Array<Array<string | number | null | undefined>>
}) {
  return (
    <div className={clsx(theme.dataGrid.containerClass, 'max-h-[360px]')}>
      <table className="min-w-full border-collapse text-left text-sm">
        <thead className={theme.dataGrid.headerClass}>
          <tr className={theme.dataGrid.headerRowClass}>
            {headers.map((header) => (
              <th key={header} className={theme.dataGrid.headerCellClass}>
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className={theme.dataGrid.bodyRowClass}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className={theme.dataGrid.bodyCellClass}>
                  {cell ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MonthlyEvolutionTable({ items }: { items: IctReportMonthlyEvolutionItem[] }) {
  if (!items.length) {
    return <p className="text-sm text-slate-500">Nenhuma competência disponível.</p>
  }
  return (
    <SimpleTable
      headers={[
        'Competência',
        'Com ICT',
        'Sem base',
        'ICT médio',
        'ICT máximo',
        'Líder',
      ]}
      rows={items.map((item) => [
        item.competencia_str,
        formatInt(item.municipios_com_ict),
        formatInt(item.municipios_sem_base),
        formatDecimal1(item.ict_medio),
        formatDecimal1(item.ict_maximo),
        item.municipio_lider,
      ])}
    />
  )
}

function RankTable({
  items,
  compact = false,
}: {
  items: IctReportRankItem[]
  compact?: boolean
}) {
  if (!items.length) {
    return <p className="text-sm text-slate-500">Nenhum município com ICT calculado.</p>
  }

  if (compact) {
    return (
      <SimpleTable
        headers={['Ranking', 'Município', 'ICT', 'Classe']}
        rows={items.map((item) => [
          formatInt(item.ranking),
          item.municipio,
          formatDecimal1(item.ict),
          item.classe,
        ])}
      />
    )
  }

  return (
    <SimpleTable
      headers={['Ranking', 'Município', 'ICT', 'Classe', 'Admissões', 'Desligamentos', 'Saldo']}
      rows={items.map((item) => [
        formatInt(item.ranking),
        item.municipio,
        formatDecimal1(item.ict),
        item.classe,
        formatInt(item.admissoes),
        formatInt(item.desligamentos),
        formatInt(item.saldo),
      ])}
    />
  )
}

function DimensionSummarySection({ summary }: { summary: IctReportDimensionSummary }) {
  return (
    <div className="space-y-4">
      {Object.entries(DIMENSION_LABELS).map(([key, label]) => {
        const stats = summary[key]
        if (!stats) return null
        return (
          <div key={key} className="rounded-xl border border-slate-200 p-3">
            <h4 className="text-sm font-semibold text-slate-900">{label}</h4>
            <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs text-slate-500">Média</dt>
                <dd className="font-medium text-slate-800">{formatReportNumber(stats.media)}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Mediana</dt>
                <dd className="font-medium text-slate-800">{formatReportNumber(stats.mediana)}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Maior valor</dt>
                <dd className="font-medium text-slate-800">
                  {stats.municipio_maior ?? '—'} ({formatReportNumber(stats.valor_maior)})
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Menor valor</dt>
                <dd className="font-medium text-slate-800">
                  {stats.municipio_menor ?? '—'} ({formatReportNumber(stats.valor_menor)})
                </dd>
              </div>
            </dl>
          </div>
        )
      })}
    </div>
  )
}

function FlagList({ items }: { items: IctReportDiagnosticFlagItem[] }) {
  if (!items.length) {
    return <p className="text-sm text-slate-500">Nenhum caso identificado nesta competência.</p>
  }
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={`${item.municipio}-${item.ranking_ictt}`} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
          <p className="font-medium text-slate-900">
            {item.municipio} · ICT {formatDecimal1(item.ict)} · ranking {formatInt(item.ranking_ictt)}
          </p>
          <p className="mt-1 text-slate-600">{item.descricao}</p>
        </li>
      ))}
    </ul>
  )
}

function ReportBody({ data }: { data: IctReportContextResponse }) {
  const { context } = data

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <SectionTitle>Síntese</SectionTitle>
        <SummaryGrid context={context} />
      </section>

      <section className="space-y-3">
        <SectionTitle>Evolução mensal</SectionTitle>
        <SectionSubtitle>Competências disponíveis na Gold ICT do Paraná.</SectionSubtitle>
        <MonthlyEvolutionTable items={context.monthly_evolution} />
      </section>

      <section className="space-y-3">
        <SectionTitle>Top 10</SectionTitle>
        <RankTable items={context.top_10} />
      </section>

      <section className="space-y-3">
        <SectionTitle>Bottom 10</SectionTitle>
        <RankTable items={context.bottom_10} compact />
      </section>

      <section className="space-y-3">
        <SectionTitle>Dimensões</SectionTitle>
        <DimensionSummarySection summary={context.dimension_summary} />
      </section>

      <section className="space-y-4">
        <SectionTitle>Flags diagnósticas</SectionTitle>
        {FLAG_SECTIONS.map(({ key, title }) => {
          const items = context.diagnostic_flags[key]
          if (!Array.isArray(items)) return null
          return (
            <div key={key} className="space-y-2">
              <h4 className="text-sm font-semibold text-slate-800">{title}</h4>
              <FlagList items={items} />
            </div>
          )
        })}
      </section>

      <section className="space-y-3">
        <SectionTitle>Notas interpretativas</SectionTitle>
        <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-slate-600">
          {context.interpretation_notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}

export function IctReportPanel({
  open,
  onClose,
  competenciaLabel,
  loading,
  error,
  data,
  stale,
  onRetry,
  onReload,
}: {
  open: boolean
  onClose: () => void
  competenciaLabel: string
  loading: boolean
  error: string | null
  data: IctReportContextResponse | null
  stale: boolean
  onRetry: () => void
  onReload: () => void
}) {
  useEffect(() => {
    if (!open) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <>
      <button
        type="button"
        className="fixed inset-0 z-[1200] bg-slate-900/40 backdrop-blur-[1px]"
        aria-label="Fechar relatório"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="ict-report-title"
        className="fixed inset-y-0 right-0 z-[1201] flex h-[100dvh] w-full max-w-2xl flex-col border-l border-slate-200 bg-white shadow-2xl"
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-orgmigra-blue-700">
              Relatório determinístico · sem IA
            </p>
            <h2 id="ict-report-title" className="mt-1 text-lg font-semibold text-slate-900">
              Relatório do ICT
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              {labelScope('pr')} · competência {competenciaLabel}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-orgmigra-blue-600/30"
            aria-label="Fechar painel"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5">
          {stale ? (
            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              A competência selecionada mudou.{' '}
              <button
                type="button"
                className="font-medium underline underline-offset-2"
                onClick={onReload}
              >
                Atualizar relatório
              </button>
            </div>
          ) : null}

          {loading ? <LoadingState label="Carregando relatório determinístico do ICT..." /> : null}

          {!loading && error ? (
            <ErrorState
              title="Não foi possível carregar o relatório determinístico do ICT para esta competência."
              message={error}
              onRetry={onRetry}
            />
          ) : null}

          {!loading && !error && data && !stale ? <ReportBody data={data} /> : null}
        </div>
      </aside>
    </>,
    document.body,
  )
}
