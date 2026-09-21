import type { IcttV2MunicipalityDetail } from '../../api/icttV2Types'
import {
  formatIcttHeadline,
  formatOptionalCurrency,
  formatOptionalInt,
  formatOptionalNumber,
  formatOptionalPercent,
  reliabilityHint,
  reliabilityLabel,
} from '../../lib/icttV2View'
import { Card } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { theme } from '../../lib/theme'
import { IcttV2DimensionBars } from './IcttV2DimensionBars'

function DiagnosticRow({ label, value }: { label: string; value: string | null }) {
  if (value == null) return null
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-slate-100 py-1.5 last:border-b-0">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-xs font-medium tabular-nums text-slate-800">{value}</dd>
    </div>
  )
}

export function IcttV2DetailPanel({
  detail,
  error,
  loading,
  onRetry,
}: {
  detail: IcttV2MunicipalityDetail | null
  error: string | null
  loading?: boolean
  onRetry?: () => void
}) {
  if (error) {
    return (
      <Card hover={false} enter={false}>
        <h3 className={theme.typography.sectionTitle}>Município selecionado</h3>
        <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-800" role="alert">
          <p className="font-medium">Erro de detalhe</p>
          <p className="mt-1 text-xs">{error}</p>
          {onRetry ? (
            <button type="button" onClick={onRetry} className="mt-2 text-xs font-medium underline">
              Tentar novamente
            </button>
          ) : null}
        </div>
      </Card>
    )
  }

  if (loading && !detail) {
    return (
      <Card hover={false} enter={false}>
        <h3 className={theme.typography.sectionTitle}>Município selecionado</h3>
        <p className={`mt-3 ${theme.loadingState.labelClass}`}>Carregando detalhe municipal...</p>
      </Card>
    )
  }

  if (!detail) {
    return (
      <Card hover={false} enter={false}>
        <h3 className={theme.typography.sectionTitle}>Município selecionado</h3>
        <EmptyState
          title="Selecione um município"
          description="Clique no mapa ou no ranking para abrir o detalhe do ICTT v2.0."
        />
      </Card>
    )
  }

  const reliability = reliabilityLabel(detail.reliability_class)
  const hint = reliabilityHint(detail.reliability_class)
  const calculavel = detail.calculavel && detail.ictt_v2 != null

  return (
    <Card hover={false} enter={false}>
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className={theme.typography.heroLabel}>Detalhe municipal</p>
          <h3 className={theme.typography.sectionTitle}>{detail.municipio}</h3>
          <p className={theme.typography.sectionSubtitle}>
            Código IBGE {detail.codigo_municipio} · competência {detail.competencia}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">ICTT</p>
          <p className="text-3xl font-semibold tabular-nums text-orgmigra-blue-800">
            {formatIcttHeadline(detail.ictt_v2)}
          </p>
        </div>
      </div>

      {reliability ? (
        <p className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          <span className="font-medium">{reliability}.</span>
          {hint ? <span className="ml-1 text-slate-600">{hint}</span> : null}
        </p>
      ) : null}

      {!calculavel ? (
        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-sm font-medium text-slate-800">ICTT não calculável nesta competência.</p>
          <p className="mt-1 text-sm text-slate-600">
            O município registrou menos de 10 admissões elegíveis para o critério de cálculo do
            ICTT nesta competência.
          </p>
        </div>
      ) : (
        <div className="mt-5">
          <h4 className="mb-3 text-sm font-semibold text-slate-800">Dimensões</h4>
          <IcttV2DimensionBars
            values={{
              absorcao: detail.absorcao,
              remuneracao: detail.remuneracao,
              qualidade_contratual: detail.qualidade_contratual,
              diversificacao: detail.diversificacao,
            }}
          />
        </div>
      )}

      <details className="mt-5 rounded-xl border border-slate-200 bg-white px-4 py-3">
        <summary className="cursor-pointer text-sm font-medium text-slate-700">
          Indicadores diagnósticos
        </summary>
        <dl className="mt-3">
          <DiagnosticRow label="Admissões" value={formatOptionalInt(detail.admissoes)} />
          <DiagnosticRow label="Desligamentos" value={formatOptionalInt(detail.desligamentos)} />
          <DiagnosticRow label="Saldo" value={formatOptionalInt(detail.saldo)} />
          <DiagnosticRow
            label="Mediana salarial municipal"
            value={formatOptionalCurrency(detail.salario_mediano_r4_municipio)}
          />
          <DiagnosticRow
            label="Mediana salarial PR"
            value={formatOptionalCurrency(detail.salario_mediano_r4_pr)}
          />
          <DiagnosticRow
            label="Salário relativo"
            value={formatOptionalNumber(detail.salario_relativo_r4, 3)}
          />
          <DiagnosticRow label="% parcial" value={formatOptionalPercent(detail.perc_parcial_admissao)} />
          <DiagnosticRow
            label="% intermitente"
            value={formatOptionalPercent(detail.perc_intermitente_admissao)}
          />
          <DiagnosticRow label="Shannon CBO" value={formatOptionalNumber(detail.shannon_cbo, 3)} />
          <DiagnosticRow
            label="Shannon subclasse"
            value={formatOptionalNumber(detail.shannon_subclasse, 3)}
          />
          <DiagnosticRow label="Shannon seção" value={formatOptionalNumber(detail.shannon_secao, 3)} />
        </dl>
      </details>
    </Card>
  )
}
