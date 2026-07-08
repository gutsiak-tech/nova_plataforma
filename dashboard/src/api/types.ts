export type Scope = 'br' | 'pr' | 'rmc'

export type GoldRow = Record<string, unknown>

export type Competencia = {
  ano: number
  mes: number
  competencia: string
  label: string
}

export type CompetenciasResponse = {
  default: Competencia | null
  items: Competencia[]
}

export type TableResponse = {
  month: { ano: number; mes: number }
  scope: Scope
  table: string
  columns: string[]
  total: number
  offset: number
  count: number
  rows: GoldRow[]
}

export type OverviewResponse = {
  month: { ano: number; mes: number }
  scope: Scope
  resumo: GoldRow | null
  rankings: {
    uf: GoldRow[] | null
    municipio: GoldRow[]
    setor: GoldRow[]
    ocupacao: GoldRow[]
  }
  profiles: Record<string, GoldRow[]>
  salary_profiles: Record<string, GoldRow[]>
}

/** Linha da tabela Gold `tabela_ictt_municipio` (escopo Paraná). */
export type IcttMunicipio = {
  ano: number
  mes: number
  competencia_str: string
  uf: string
  municipio: string
  municipio_norm: string
  status_calculo: 'calculado' | 'sem_dados_suficientes' | string
  ICTT: number | null
  ranking_ictt: number | null
  percentil_ictt: number | null
  classe_ictt: string
  tooltip_resumo: string
  dim_dinamismo: number | null
  dim_remuneracao: number | null
  dim_qualidade_emprego: number | null
  dim_perfil_trabalhador: number | null
  dim_complexidade: number | null
  admissoes: number
  desligamentos: number
  saldo: number
  shannon_cbo: number | null
}
