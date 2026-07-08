import { DEFAULT_API_ANO, DEFAULT_API_MES } from './constants'
import { http } from './http'
import type { CompetenciasResponse, OverviewResponse, Scope, TableResponse } from './types'

export async function fetchCompetencias(): Promise<CompetenciasResponse> {
  const { data } = await http.get<CompetenciasResponse>('/api/gold/v1/competencias')
  return data
}

export async function fetchOverview(
  scope: Scope,
  ano: number,
  mes: number,
): Promise<OverviewResponse> {
  const { data } = await http.get<OverviewResponse>('/api/gold/v1/overview', {
    params: { scope, ano, mes },
  })
  return data
}

export async function fetchTable(
  baseName: string,
  scope: Scope,
  ano: number,
  mes: number,
  opts?: { limit?: number; offset?: number; sort_by?: string; sort_dir?: 'asc' | 'desc' },
): Promise<TableResponse> {
  const { data } = await http.get<TableResponse>(`/api/gold/v1/table/${baseName}`, {
    params: {
      scope,
      ano,
      mes,
      limit: opts?.limit ?? 2000,
      offset: opts?.offset ?? 0,
      sort_by: opts?.sort_by,
      sort_dir: opts?.sort_dir ?? 'desc',
    },
  })
  return data
}

const FALLBACK_MONTH_LABELS: Record<number, string> = {
  1: 'Janeiro de 2026',
  2: 'Fevereiro de 2026',
  3: 'Março de 2026',
  4: 'Abril de 2026',
}

/** Fallback local quando /competencias não responde. */
export function buildFallbackCompetencias(): CompetenciasResponse['items'] {
  return [1, 2, 3, 4].map((mes) => ({
    ano: DEFAULT_API_ANO,
    mes,
    competencia: `${DEFAULT_API_ANO}-${String(mes).padStart(2, '0')}`,
    label: FALLBACK_MONTH_LABELS[mes] ?? `${mes}/${DEFAULT_API_ANO}`,
  }))
}

export function buildFallbackDefault(): CompetenciasResponse['default'] {
  return {
    ano: DEFAULT_API_ANO,
    mes: DEFAULT_API_MES,
    competencia: `${DEFAULT_API_ANO}-${String(DEFAULT_API_MES).padStart(2, '0')}`,
    label: FALLBACK_MONTH_LABELS[DEFAULT_API_MES] ?? `Competência ${DEFAULT_API_MES}/${DEFAULT_API_ANO}`,
  }
}
