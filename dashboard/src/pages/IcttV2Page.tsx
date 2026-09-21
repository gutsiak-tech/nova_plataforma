import { useCallback, useEffect, useMemo, useState } from 'react'
import { BookOpen } from 'lucide-react'
import {
  fetchIcttV2Competencias,
  fetchIcttV2Methodology,
  fetchIcttV2Municipalities,
  fetchIcttV2MunicipalityDetail,
  fetchIcttV2Ranking,
} from '../api/icttV2'
import type {
  IcttV2MethodologyResponse,
  IcttV2MunicipalityDetail,
  IcttV2RankingUniverse,
} from '../api/icttV2Types'
import { IcttV2CompetenciaSelect } from '../components/icttV2/IcttV2CompetenciaSelect'
import { IcttV2DetailPanel } from '../components/icttV2/IcttV2DetailPanel'
import { IcttV2Map } from '../components/icttV2/IcttV2Map'
import { IcttV2MethodologyDialog } from '../components/icttV2/IcttV2MethodologyDialog'
import { IcttV2RankingPanel } from '../components/icttV2/IcttV2RankingPanel'
import { useTerritoryGeoJson } from '../components/map/useTerritoryGeoJson'
import { ErrorState } from '../components/ui/ErrorState'
import { KpiStat } from '../components/ui/KpiStat'
import { LoadingState } from '../components/ui/LoadingState'
import { PageHeader } from '../components/ui/PageHeader'
import {
  applyMunicipalitiesResult,
  applyRankingResult,
  EMPTY_ICTT_V2_PREVIEW_STATE,
  mapSurvivesRankingFailure,
} from '../lib/icttV2PreviewState'
import {
  DEFAULT_RANKING_UNIVERSE,
  formatCompetenciaShort,
  pickLatestCompetencia,
  summarizeMunicipalities,
} from '../lib/icttV2View'
import { scheduleAsyncState } from '../lib/scheduleAsyncState'
import { theme } from '../lib/theme'

export function IcttV2Page() {
  const { geoJson, geoLoading, geoError } = useTerritoryGeoJson('pr')

  const [competencias, setCompetencias] = useState<string[]>([])
  const [competenciasError, setCompetenciasError] = useState<string | null>(null)
  const [competenciasLoading, setCompetenciasLoading] = useState(true)
  const [competencia, setCompetencia] = useState<string | null>(null)

  const [methodology, setMethodology] = useState<IcttV2MethodologyResponse | null>(null)
  const [methodologyError, setMethodologyError] = useState<string | null>(null)
  const [methodologyOpen, setMethodologyOpen] = useState(false)

  const [preview, setPreview] = useState(EMPTY_ICTT_V2_PREVIEW_STATE)
  const [municipalitiesLoading, setMunicipalitiesLoading] = useState(false)
  const [rankingLoading, setRankingLoading] = useState(false)
  const [universe, setUniverse] = useState<IcttV2RankingUniverse>(DEFAULT_RANKING_UNIVERSE)
  const [rankingRetry, setRankingRetry] = useState(0)
  const [municipalitiesRetry, setMunicipalitiesRetry] = useState(0)

  const [selectedCodigo, setSelectedCodigo] = useState<string | null>(null)
  const [detail, setDetail] = useState<IcttV2MunicipalityDetail | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailRetry, setDetailRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    fetchIcttV2Competencias(controller.signal)
      .then((payload) => {
        setCompetencias(payload.competencias)
        setCompetenciasError(null)
        setCompetencia((current) => current ?? pickLatestCompetencia(payload.competencias))
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setCompetenciasError(
          error instanceof Error ? error.message : 'Não foi possível carregar as competências ICTT v2.',
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) setCompetenciasLoading(false)
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchIcttV2Methodology(controller.signal)
      .then((payload) => {
        setMethodology(payload)
        setMethodologyError(null)
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setMethodologyError(
          error instanceof Error ? error.message : 'Não foi possível carregar a metodologia.',
        )
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!competencia) return
    const controller = new AbortController()
    let cancelled = false
    const isCancelled = () => cancelled || controller.signal.aborted
    scheduleAsyncState(isCancelled, () => setMunicipalitiesLoading(true))
    fetchIcttV2Municipalities(competencia, controller.signal)
      .then((payload) => {
        setPreview((current) => applyMunicipalitiesResult(current, { ok: true, payload }))
        setSelectedCodigo((current) => {
          if (current && payload.data.some((row) => row.codigo_municipio === current)) {
            return current
          }
          return null
        })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setPreview((current) =>
          applyMunicipalitiesResult(current, {
            ok: false,
            error:
              error instanceof Error
                ? error.message
                : 'Não foi possível carregar os municípios ICTT v2.',
          }),
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) setMunicipalitiesLoading(false)
      })
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [competencia, municipalitiesRetry])

  useEffect(() => {
    if (!competencia) return
    const controller = new AbortController()
    let cancelled = false
    const isCancelled = () => cancelled || controller.signal.aborted
    scheduleAsyncState(isCancelled, () => setRankingLoading(true))
    fetchIcttV2Ranking(competencia, universe, controller.signal)
      .then((payload) => {
        setPreview((current) => applyRankingResult(current, { ok: true, payload }))
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setPreview((current) =>
          applyRankingResult(current, {
            ok: false,
            error: error instanceof Error ? error.message : 'Erro de ranking.',
          }),
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) setRankingLoading(false)
      })
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [competencia, universe, rankingRetry])

  useEffect(() => {
    if (!competencia || !selectedCodigo) return
    const controller = new AbortController()
    let cancelled = false
    const isCancelled = () => cancelled || controller.signal.aborted
    scheduleAsyncState(isCancelled, () => setDetailLoading(true))
    fetchIcttV2MunicipalityDetail(selectedCodigo, competencia, controller.signal)
      .then((payload) => {
        setDetail(payload.data)
        setDetailError(null)
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setDetail(null)
        setDetailError(error instanceof Error ? error.message : 'Erro de detalhe.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setDetailLoading(false)
      })
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [competencia, selectedCodigo, detailRetry])

  const handleSelect = useCallback((codigoMunicipio: string) => {
    setSelectedCodigo(codigoMunicipio)
  }, [])

  const rows = useMemo(
    () => preview.municipalities?.data ?? [],
    [preview.municipalities],
  )
  const rankingRows = useMemo(() => preview.ranking?.data ?? [], [preview.ranking])
  const summary = useMemo(
    () => summarizeMunicipalities(rows, preview.municipalities?.meta),
    [preview.municipalities, rows],
  )
  const visibleDetail =
    selectedCodigo && detail?.codigo_municipio === selectedCodigo ? detail : null
  const visibleDetailError = selectedCodigo ? detailError : null
  const competenciaLabel = competencia ? formatCompetenciaShort(competencia) : '—'
  const refreshing = municipalitiesLoading && rows.length > 0
  const mapAlive = mapSurvivesRankingFailure(preview)

  if (competenciasError) {
    return (
      <ErrorState
        message={competenciasError}
        onRetry={() => window.location.reload()}
        title="API indisponível"
      />
    )
  }

  if (competenciasLoading && !competencia) {
    return <LoadingState label="Carregando competências do ICTT v2.0..." />
  }

  if (preview.municipalitiesError && !mapAlive) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Versão metodológica 2.0"
          title="ICTT v2.0"
          subtitle="Índice de Competitividade Territorial do Trabalho"
        />
        <IcttV2CompetenciaSelect
          competencias={competencias}
          value={competencia}
          onChange={setCompetencia}
          loading={competenciasLoading}
        />
        <ErrorState
          title="Competência sem Gold"
          message={preview.municipalitiesError}
          onRetry={() => setMunicipalitiesRetry((value) => value + 1)}
        />
      </div>
    )
  }

  const showInitialLoader = municipalitiesLoading && rows.length === 0 && !preview.municipalitiesError

  return (
    <div className="min-w-0 space-y-5">
      <PageHeader
        eyebrow="Versão metodológica 2.0"
        title="ICTT v2.0"
        subtitle={`Índice de Competitividade Territorial do Trabalho · Paraná · competência ${competenciaLabel}`}
        titleClassName={theme.typography.heroTitle.replace('text-slate-900', 'text-orgmigra-blue-800')}
        action={
          <button
            type="button"
            onClick={() => setMethodologyOpen(true)}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-orgmigra-blue-200 hover:bg-orgmigra-blue-50 hover:text-orgmigra-blue-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-orgmigra-blue-600/30"
          >
            <BookOpen className="h-4 w-4" aria-hidden />
            Metodologia
          </button>
        }
      />

      <IcttV2CompetenciaSelect
        competencias={competencias}
        value={competencia}
        onChange={setCompetencia}
        loading={competenciasLoading}
      />

      {showInitialLoader ? (
        <LoadingState label="Carregando municípios do ICTT v2.0..." />
      ) : (
        <>
          <div
            className={[
              'grid gap-3 sm:grid-cols-2 xl:grid-cols-4 [&>div]:!min-h-[10rem] [&>div]:!pt-4',
              refreshing ? 'opacity-[0.88] transition-opacity duration-200' : '',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            <KpiStat
              variant="executive"
              executiveAccent="blue"
              label="Municípios da malha"
              value={summary.nMunicipalities}
            />
            <KpiStat
              variant="executive"
              executiveAccent="green"
              label="Municípios com ICTT calculável"
              value={summary.nCalculable}
            />
            <KpiStat
              variant="executive"
              executiveAccent="purple"
              label="Confiabilidade reduzida"
              value={summary.nReduced}
            />
            <KpiStat
              variant="executive"
              executiveAccent="blue"
              label="Maior robustez"
              value={summary.nHigher}
            />
          </div>
          <p className="text-xs text-slate-500">
            Competência {summary.competencia ?? competencia} · metodologia{' '}
            {summary.methodologyVersion ?? methodology?.methodology_version ?? '2.0'}
          </p>

          <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(20rem,0.9fr)]">
            <IcttV2Map
              rows={rows}
              competenciaLabel={competenciaLabel}
              geoJson={geoJson}
              geoLoading={geoLoading}
              geoError={geoError}
              refreshing={refreshing}
              selectedCodigo={selectedCodigo}
              onSelect={handleSelect}
            />
            <IcttV2RankingPanel
              universe={universe}
              onUniverseChange={setUniverse}
              rows={rankingRows}
              error={preview.rankingError}
              onRetry={() => setRankingRetry((value) => value + 1)}
              selectedCodigo={selectedCodigo}
              onSelect={handleSelect}
              loading={rankingLoading}
            />
          </div>

          <IcttV2DetailPanel
            detail={visibleDetail}
            error={visibleDetailError}
            loading={detailLoading}
            onRetry={() => setDetailRetry((value) => value + 1)}
          />
        </>
      )}

      <IcttV2MethodologyDialog
        open={methodologyOpen}
        onClose={() => setMethodologyOpen(false)}
        data={methodology}
        error={methodologyError}
        loading={!methodology && !methodologyError}
      />
    </div>
  )
}
