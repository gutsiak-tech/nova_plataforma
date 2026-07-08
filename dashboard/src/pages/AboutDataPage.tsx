import { useEffect, useState } from 'react'
import { fetchCompetencias } from '../api/gold'
import type { Competencia } from '../api/types'
import { Card } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { SectionTitle } from '../components/ui/SectionTitle'
import { LoadingState } from '../components/ui/LoadingState'
import { ErrorState } from '../components/ui/ErrorState'
import { theme } from '../lib/theme'
import { scheduleAsyncState } from '../lib/scheduleAsyncState'

export function AboutDataPage() {
  const [competencias, setCompetencias] = useState<Competencia[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    const isCancelled = () => cancelled
    scheduleAsyncState(isCancelled, () => {
      setLoading(true)
      setErr(null)
    })
    fetchCompetencias()
      .then((res) => {
        if (!cancelled) setCompetencias(res.items)
      })
      .catch((e: unknown) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : 'Falha ao carregar competências')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [retryKey])

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="Documentação"
        title="Sobre os dados"
        subtitle="Fonte, processamento, escopos territoriais e limites de leitura do Observatório de Migrantes."
      />

      <Card hover={false}>
        <p className={theme.doc.bodyClass}>
          O <strong className={theme.doc.emphasisClass}>Observatório de Migrantes</strong> reúne
          indicadores sobre vínculos formais de trabalho a partir de uma{' '}
          <strong className={theme.doc.emphasisClass}>base filtrada</strong> de registros
          administrativos do Novo CAGED, disponibilizados pelo Ministério do Trabalho e processados
          localmente para fins analíticos. Os resultados exibidos referem-se exclusivamente a essa
          base analisada — não representam a totalidade do mercado de trabalho formal nem do universo
          de pessoas migrantes.
        </p>
      </Card>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card hover={false}>
          <SectionTitle title="Fonte dos dados" />
          <p className={theme.doc.bodyClass}>
            A fonte primária é uma base filtrada derivada dos registros do{' '}
            <strong className={theme.doc.emphasisClass}>Novo CAGED</strong> (Cadastro Geral de
            Empregados e Desempregados), mantido pelo{' '}
            <strong className={theme.doc.emphasisClass}>Ministério do Trabalho</strong>. A
            periodicidade é <strong className={theme.doc.emphasisClass}>mensual</strong>: cada
            competência corresponde a um ano e mês de movimentação de emprego formal na base
            selecionada.
          </p>
        </Card>

        <Card hover={false}>
          <SectionTitle title="Escopos territoriais" />
          <p className={`mb-3 ${theme.doc.bodyClass}`}>
            Os indicadores são organizados em três recortes territoriais da base analisada:
          </p>
          <ul className={`list-inside list-disc space-y-2 ${theme.doc.bodyClass}`}>
            <li>
              <strong className={theme.doc.emphasisClass}>Brasil</strong> — visão nacional
            </li>
            <li>
              <strong className={theme.doc.emphasisClass}>Paraná</strong> — recorte estadual
            </li>
            <li>
              <strong className={theme.doc.emphasisClass}>Região Metropolitana de Curitiba</strong>{' '}
              — recorte metropolitano
            </li>
          </ul>
          <p className={`mt-3 ${theme.doc.bodyClass}`}>
            O escopo ativo pode ser alterado no seletor do painel; rankings e mapas respeitam o
            recorte escolhido.
          </p>
        </Card>

        <Card hover={false}>
          <SectionTitle title="Indicadores" />
          <p className={theme.doc.bodyClass}>
            O painel apresenta indicadores de admissões, desligamentos, saldo, setores, ocupações,
            perfil demográfico, país, continente, raça/cor e remuneração, sempre no recorte da base
            analisada e da competência selecionada.
          </p>
          <ul className={`mt-3 list-inside list-disc space-y-2 ${theme.doc.bodyClass}`}>
            <li>
              <strong className={theme.doc.emphasisClass}>Admissões</strong>,{' '}
              <strong className={theme.doc.emphasisClass}>desligamentos</strong> e{' '}
              <strong className={theme.doc.emphasisClass}>saldo</strong> por competência
            </li>
            <li>Distribuição territorial, por setor e por ocupação (CBO)</li>
            <li>Perfil demográfico (sexo, faixa etária, instrução)</li>
            <li>
              <strong className={theme.doc.emphasisClass}>País</strong>,{' '}
              <strong className={theme.doc.emphasisClass}>continente</strong> e{' '}
              <strong className={theme.doc.emphasisClass}>raça/cor</strong> — dimensões disponíveis
              na base administrativa analisada
            </li>
            <li>Indicadores de remuneração nos recortes disponíveis</li>
          </ul>
        </Card>

        <Card hover={false}>
          <SectionTitle title="Processamento" />
          <p className={theme.doc.bodyClass}>
            Os dados passam por etapas locais de ingestão, tratamento, validação e agregação antes
            de serem exibidos no painel. O dashboard consome indicadores agregados via API, com
            leitura prioritária de arquivos colunares e fallback tabular quando necessário.
          </p>
          <p className={`mt-3 ${theme.typography.smallMuted}`}>
            Nota para operadores do ambiente: metadados técnicos adicionais podem ser consultados
            nos endpoints listados abaixo, incluindo catálogo de tabelas e competências
            disponíveis.
          </p>
        </Card>
      </section>

      <section className="space-y-6">
        <Card hover={false}>
          <SectionTitle
            title="Competência mensal"
            subtitle="Os indicadores variam conforme o mês selecionado no painel."
          />
          <p className={theme.doc.bodyClass}>
            Toda leitura deve considerar a competência ativa no seletor de mês. Ao trocar de
            período, admissões, desligamentos, saldo e demais recortes passam a refletir o novo
            mês escolhido.
          </p>
          <div className="mt-4">
            <p className={`mb-2 ${theme.typography.smallMuted}`}>Competências disponíveis no ambiente:</p>
            {loading ? (
              <LoadingState rows={1} label="Carregando competências..." className="mt-2" />
            ) : err ? (
              <div className="mt-2">
                <ErrorState message={err} onRetry={() => setRetryKey((k) => k + 1)} />
              </div>
            ) : competencias.length ? (
              <ul className="flex flex-wrap gap-2" aria-label="Competências disponíveis">
                {competencias.map((c) => (
                  <li key={c.competencia} className={theme.doc.badgeClass}>
                    {c.label}
                  </li>
                ))}
              </ul>
            ) : (
              <p className={theme.typography.smallMuted}>Nenhuma competência listada pela API.</p>
            )}
          </div>
        </Card>

        <Card hover={false}>
          <SectionTitle title="Limites de interpretação" />
          <ul className={`mt-3 list-inside list-disc space-y-2 ${theme.doc.bodyClass}`}>
            <li>Os dados tratam de vínculos formais registrados administrativamente.</li>
            <li>Não representam a totalidade da população migrante nem do mercado de trabalho.</li>
            <li>Não incluem trabalho informal ou vínculos fora da cobertura da base original.</li>
            <li>
              Os resultados dependem da classificação, filtros e cobertura dos registros de origem.
            </li>
            <li>
              Recortes territoriais e tabelas dependem do processamento da competência selecionada.
            </li>
            <li>
              A disponibilidade de novos meses depende da atualização periódica do processamento
              local.
            </li>
          </ul>
        </Card>

        <Card hover={false}>
          <SectionTitle
            title="Referências da API"
            subtitle="Endpoints úteis para verificação operacional do ambiente local."
          />
          <dl className="mt-2 space-y-3 text-sm">
            {[
              ['GET /ready', 'Verifica se indicadores, catálogo e metadados estão prontos'],
              ['GET /api/gold/v1/competencias', 'Lista competências disponíveis'],
              ['GET /api/gold/v1/catalog', 'Catálogo de tabelas e metadados dos indicadores'],
              ['GET /health', 'Verifica se a API está ativa'],
            ].map(([endpoint, desc]) => (
              <div key={endpoint} className="flex flex-col gap-1 sm:flex-row sm:gap-4">
                <dt className={theme.doc.endpointClass}>{endpoint}</dt>
                <dd className="text-slate-400">{desc}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </section>
    </div>
  )
}
