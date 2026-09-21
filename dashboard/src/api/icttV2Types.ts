/** Contratos TypeScript da API ICTT methodology version 2.0.
 * Independentes do schema PCA/V1 (`ictReportTypes`).
 */

export type IcttV2ReliabilityClass = 'reduced' | 'higher'

export type IcttV2RankingUniverse = 'n10' | 'n20'

export type IcttV2Dimension = {
  key: string
  weight: number
}

export type IcttV2Eligibility = {
  min_admissions: number
  higher_reliability_from: number
}

export type IcttV2ReferencePeriod = {
  start: string
  end: string
}

export type IcttV2MethodologyResponse = {
  methodology_version: string
  normalization_version: string
  reference_scope: string
  reference_period: IcttV2ReferencePeriod
  eligibility: IcttV2Eligibility
  dimensions: IcttV2Dimension[]
}

export type IcttV2CompetenciasResponse = {
  methodology_version: string
  competencias: string[]
}

export type IcttV2MunicipalityPublic = {
  competencia: string
  codigo_municipio: string
  municipio: string
  calculavel: boolean
  reliability_class: IcttV2ReliabilityClass | null
  admissoes: number
  desligamentos: number
  saldo: number
  absorcao: number | null
  remuneracao: number | null
  qualidade_contratual: number | null
  diversificacao: number | null
  ictt_v2: number | null
  rank_n10: number | null
  rank_n20: number | null
}

export type IcttV2MunicipalityDetail = IcttV2MunicipalityPublic & {
  a_volume_score: number | null
  a_saldo: number | null
  n_salarios_r4: number | null
  salario_mediano_r4_municipio: number | null
  salario_mediano_r4_pr: number | null
  salario_relativo_r4: number | null
  perc_parcial_admissao: number | null
  perc_intermitente_admissao: number | null
  q_parcial: number | null
  q_intermitente: number | null
  shannon_cbo: number | null
  shannon_subclasse: number | null
  shannon_secao: number | null
  d_cbo: number | null
  d_subclasse: number | null
  d_secao: number | null
}

export type IcttV2ListMeta = {
  competencia: string
  methodology_version: string
  normalization_version: string
  n_municipalities: number
  n_calculable: number
  reliability: IcttV2ReliabilityClass | null
}

export type IcttV2RankingMeta = IcttV2ListMeta & {
  universe: IcttV2RankingUniverse
  n_ranked: number
}

export type IcttV2MunicipalityListResponse = {
  meta: IcttV2ListMeta
  data: IcttV2MunicipalityPublic[]
}

export type IcttV2MunicipalityDetailResponse = {
  meta: IcttV2ListMeta
  data: IcttV2MunicipalityDetail
}

export type IcttV2RankingResponse = {
  meta: IcttV2RankingMeta
  data: IcttV2MunicipalityPublic[]
}
