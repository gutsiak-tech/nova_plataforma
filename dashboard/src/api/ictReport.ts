import axios from 'axios'
import { http } from './http'
import type { Scope } from './types'
import type { IctReportContextResponse } from './ictReportTypes'

export async function fetchIctReportContext(
  scope: Scope,
  ano: number,
  mes: number,
): Promise<IctReportContextResponse> {
  try {
    const { data } = await http.get<IctReportContextResponse>('/api/ict/v1/report-context', {
      params: { scope, ano, mes },
    })
    return data
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      const detail = error.response?.data?.detail
      if (typeof detail === 'string') {
        throw new Error(detail)
      }
    }
    throw error instanceof Error
      ? error
      : new Error('Não foi possível carregar o relatório determinístico do ICT para esta competência.')
  }
}
