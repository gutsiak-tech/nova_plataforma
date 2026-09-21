import { describe, expect, it } from 'vitest'
import { buildIcttV2TooltipHtml } from './icttV2Tooltip'
import { icttV2FillColor } from './icttV2Choropleth'
import { ICT_CHOROPLETH } from '../map/ictChoropleth'
import type { IcttV2MunicipalityPublic } from '../api/icttV2Types'

const ineligible: IcttV2MunicipalityPublic = {
  competencia: '2026-04',
  codigo_municipio: '4110706',
  municipio: 'Irati',
  calculavel: false,
  reliability_class: null,
  admissoes: 9,
  desligamentos: 0,
  saldo: 0,
  absorcao: null,
  remuneracao: null,
  qualidade_contratual: null,
  diversificacao: null,
  ictt_v2: null,
  rank_n10: null,
  rank_n20: null,
}

const foz: IcttV2MunicipalityPublic = {
  ...ineligible,
  codigo_municipio: '4108304',
  municipio: 'Foz do Iguaçu',
  calculavel: true,
  reliability_class: 'higher',
  admissoes: 463,
  absorcao: 78.15786276089538,
  remuneracao: 90.88963668433047,
  qualidade_contratual: 68.68250539956804,
  diversificacao: 93.72877147518022,
  ictt_v2: 82.86469407999354,
  rank_n10: 1,
  rank_n20: 1,
}

describe('ictt v2 visual helpers', () => {
  it('não pinta null como score zero', () => {
    expect(icttV2FillColor(null)).toBe(ICT_CHOROPLETH.noData)
    expect(icttV2FillColor(0)).not.toBe(ICT_CHOROPLETH.noData)
  })

  it('explica município N<10 no tooltip', () => {
    const html = buildIcttV2TooltipHtml({ municipio: 'Irati' }, ineligible)
    expect(html).toContain('ICTT não calculável')
    expect(html).toContain('Menos de 10 admissões na competência')
    expect(html).not.toContain('ICTT = 0')
    expect(html).not.toContain('>0<')
  })

  it('mostra dimensões e confiabilidade no tooltip de Foz', () => {
    const html = buildIcttV2TooltipHtml({ municipio: 'Foz do Iguaçu' }, foz)
    expect(html).toContain('Foz do Iguaçu')
    expect(html).toContain('ICTT')
    expect(html).toContain('Absorção')
    expect(html).toContain('Remuneração')
    expect(html).toContain('Qualidade contratual')
    expect(html).toContain('Diversificação')
    expect(html).toContain('Maior robustez')
  })
})
