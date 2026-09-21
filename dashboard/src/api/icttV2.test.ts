import { beforeEach, describe, expect, it, vi } from 'vitest'
import { http } from './http'

vi.mock('./http', () => ({
  http: { get: vi.fn() },
}))

import {
  fetchIcttV2Competencias,
  fetchIcttV2Methodology,
  fetchIcttV2Municipalities,
  fetchIcttV2MunicipalityDetail,
  fetchIcttV2Ranking,
} from './icttV2'

const get = vi.mocked(http.get)

describe('icttV2 API client', () => {
  beforeEach(() => {
    get.mockReset()
  })

  it('carrega competências versionadas', async () => {
    get.mockResolvedValueOnce({
      data: { methodology_version: '2.0', competencias: ['2026-01', '2026-02', '2026-03', '2026-04'] },
    })
    const payload = await fetchIcttV2Competencias()
    expect(get).toHaveBeenCalledWith('/api/ict/v2/competencias', expect.objectContaining({ params: undefined }))
    expect(payload.competencias).toEqual(['2026-01', '2026-02', '2026-03', '2026-04'])
  })

  it('carrega metodologia sem P05/P95', async () => {
    get.mockResolvedValueOnce({
      data: {
        methodology_version: '2.0',
        normalization_version: 'NORM_B.2026-01_2026-04.N233',
        reference_scope: 'PR',
        reference_period: { start: '2026-01', end: '2026-04' },
        eligibility: { min_admissions: 10, higher_reliability_from: 20 },
        dimensions: [
          { key: 'absorcao', weight: 0.25 },
          { key: 'remuneracao', weight: 0.25 },
          { key: 'qualidade_contratual', weight: 0.25 },
          { key: 'diversificacao', weight: 0.25 },
        ],
      },
    })
    const payload = await fetchIcttV2Methodology()
    expect(get).toHaveBeenCalledWith('/api/ict/v2/methodology', expect.any(Object))
    expect(payload.methodology_version).toBe('2.0')
    expect(JSON.stringify(payload)).not.toContain('0.917135')
  })

  it('consulta municipalities, ranking e detalhe', async () => {
    get.mockResolvedValue({ data: { meta: {}, data: [] } })
    await fetchIcttV2Municipalities('2026-04')
    await fetchIcttV2Ranking('2026-04', 'n20')
    await fetchIcttV2MunicipalityDetail('4108304', '2026-04')
    expect(get).toHaveBeenCalledWith(
      '/api/ict/v2/municipalities',
      expect.objectContaining({ params: { competencia: '2026-04' } }),
    )
    expect(get).toHaveBeenCalledWith(
      '/api/ict/v2/ranking',
      expect.objectContaining({ params: { competencia: '2026-04', universe: 'n20' } }),
    )
    expect(get).toHaveBeenCalledWith(
      '/api/ict/v2/municipalities/4108304',
      expect.objectContaining({ params: { competencia: '2026-04' } }),
    )
  })
})
