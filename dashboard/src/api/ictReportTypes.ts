export type IctReportSummary = {
  municipios_total: number
  municipios_com_ict: number
  municipios_sem_base: number
  percentual_com_ict: number | null
  ict_medio: number | null
  ict_mediano: number | null
  ict_minimo: number | null
  ict_maximo: number | null
  municipio_lider: string | null
  ranking_lider: number | null
}

export type IctReportRankItem = {
  ranking: number
  municipio: string
  ict: number | null
  classe: string
  admissoes?: number | null
  desligamentos?: number | null
  saldo?: number | null
  dim_dinamismo?: number | null
  dim_remuneracao?: number | null
  dim_qualidade_emprego?: number | null
  dim_perfil_trabalhador?: number | null
  dim_complexidade?: number | null
}

export type IctReportMonthlyEvolutionItem = {
  competencia_str: string
  municipios_com_ict: number
  municipios_sem_base: number
  ict_medio: number | null
  ict_mediano?: number | null
  ict_maximo: number | null
  municipio_lider: string | null
  admissoes_total?: number
  desligamentos_total?: number
  saldo_total?: number
}

export type IctReportDimensionStats = {
  media: number | null
  mediana: number | null
  minimo?: number | null
  maximo?: number | null
  municipio_maior: string | null
  valor_maior: number | null
  municipio_menor: string | null
  valor_menor: number | null
}

export type IctReportDimensionSummary = Record<string, IctReportDimensionStats>

export type IctReportDiagnosticFlagItem = {
  municipio: string
  ict: number | null
  ranking_ictt: number
  descricao: string
  dim_qualidade_emprego?: number | null
  dim_remuneracao?: number | null
  dim_dinamismo?: number | null
  dim_complexidade?: number | null
}

export type IctReportDiagnosticFlags = {
  leaders_with_negative_quality: IctReportDiagnosticFlagItem[]
  leaders_with_negative_remuneration: IctReportDiagnosticFlagItem[]
  high_dynamism_low_quality: IctReportDiagnosticFlagItem[]
  high_complexity_low_remuneration: IctReportDiagnosticFlagItem[]
  municipios_sem_base: number
}

export type IctReportContext = {
  metadata: {
    indicator: string
    indicator_full_name: string
    scope: string
    ano: number
    mes: number
    competencia_str: string
    generated_from: string
    method_note: string
  }
  summary: IctReportSummary
  class_distribution: Record<string, number>
  top_10: IctReportRankItem[]
  bottom_10: IctReportRankItem[]
  monthly_evolution: IctReportMonthlyEvolutionItem[]
  dimension_summary: IctReportDimensionSummary
  diagnostic_flags: IctReportDiagnosticFlags
  interpretation_notes: string[]
}

export type IctReportContextResponse = {
  scope: string
  ano: number
  mes: number
  competencia_str: string
  source: 'deterministic_context'
  uses_ai: false
  cache_status: 'hit' | 'generated'
  context: IctReportContext
  markdown: string | null
}
