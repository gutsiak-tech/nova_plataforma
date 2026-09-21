import type {
  IcttV2ListMeta,
  IcttV2MunicipalityPublic,
  IcttV2RankingUniverse,
  IcttV2ReliabilityClass,
} from '../api/icttV2Types'

/** Default de UI do preview: universo de maior robustez. Não é ranking oficial. Reversível. */
export const DEFAULT_RANKING_UNIVERSE: IcttV2RankingUniverse = 'n20'

export const RANKING_UNIVERSE_OPTIONS: ReadonlyArray<{
  value: IcttV2RankingUniverse
  label: string
  hint: string
}> = [
  {
    value: 'n20',
    label: 'N ≥ 20',
    hint: 'Universo do ranking com 20 ou mais admissões (maior robustez amostral).',
  },
  {
    value: 'n10',
    label: 'N ≥ 10',
    hint: 'Universo do ranking com 10 ou mais admissões.',
  },
]

export const DIMENSION_COPY = {
  absorcao: {
    label: 'Absorção',
    text:
      'Capacidade relativa de absorção de trabalhadores migrantes, combinando volume de admissões e saldo suavizado.',
  },
  remuneracao: {
    label: 'Remuneração',
    text:
      'Posição da mediana salarial elegível do município em relação à mediana estadual da competência.',
  },
  qualidade_contratual: {
    label: 'Qualidade contratual',
    text: 'Menor incidência relativa de vínculos parciais e intermitentes.',
  },
  diversificacao: {
    label: 'Diversificação',
    text:
      'Diversidade da estrutura ocupacional e setorial observada nas movimentações formais.',
  },
} as const

const SHORT_MONTH = [
  'jan',
  'fev',
  'mar',
  'abr',
  'mai',
  'jun',
  'jul',
  'ago',
  'set',
  'out',
  'nov',
  'dez',
] as const

export function pickLatestCompetencia(competencias: string[]): string | null {
  const valid = competencias.filter((item) => /^\d{4}-(0[1-9]|1[0-2])$/.test(item))
  if (valid.length === 0) return null
  return [...valid].sort()[valid.length - 1] ?? null
}

export function formatCompetenciaShort(competencia: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(competencia)
  if (!match) return competencia
  const year = match[1]
  const month = Number(match[2])
  const label = SHORT_MONTH[month - 1]
  if (!label) return competencia
  return `${label}/${year.slice(-2)}`
}

export function numericOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

export function formatIcttScore(value: number | null | undefined, digits = 1): string | null {
  const num = numericOrNull(value)
  if (num === null) return null
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(num)
}

export function formatIcttHeadline(value: number | null | undefined): string {
  const formatted = formatIcttScore(value, 4)
  return formatted ?? 'ICTT não calculável'
}

export function formatOptionalNumber(value: number | null | undefined, digits = 1): string | null {
  const num = numericOrNull(value)
  if (num === null) return null
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(num)
}

export function formatOptionalInt(value: number | null | undefined): string | null {
  const num = numericOrNull(value)
  if (num === null) return null
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(num)
}

export function formatOptionalPercent(value: number | null | undefined): string | null {
  const num = numericOrNull(value)
  if (num === null) return null
  return `${new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(num)}%`
}

export function formatOptionalCurrency(value: number | null | undefined): string | null {
  const num = numericOrNull(value)
  if (num === null) return null
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  }).format(num)
}

export function reliabilityLabel(
  value: IcttV2ReliabilityClass | null | undefined,
): string | null {
  if (value === 'reduced') return 'Confiabilidade reduzida'
  if (value === 'higher') return 'Maior robustez'
  return null
}

export function reliabilityHint(value: IcttV2ReliabilityClass | null | undefined): string | null {
  if (value === 'reduced') {
    return '10–19 admissões: indicador calculável com maior incerteza amostral.'
  }
  if (value === 'higher') {
    return '20 ou mais admissões: maior robustez amostral.'
  }
  return null
}

export type IcttV2Summary = {
  nMunicipalities: number
  nCalculable: number
  nReduced: number
  nHigher: number
  methodologyVersion: string | null
  competencia: string | null
}

export function summarizeMunicipalities(
  rows: IcttV2MunicipalityPublic[],
  meta?: IcttV2ListMeta | null,
): IcttV2Summary {
  return {
    nMunicipalities: meta?.n_municipalities ?? rows.length,
    nCalculable: meta?.n_calculable ?? rows.filter((row) => row.calculavel).length,
    nReduced: rows.filter((row) => row.reliability_class === 'reduced').length,
    nHigher: rows.filter((row) => row.reliability_class === 'higher').length,
    methodologyVersion: meta?.methodology_version ?? null,
    competencia: meta?.competencia ?? rows[0]?.competencia ?? null,
  }
}

export function rankingUniverseQuery(universe: IcttV2RankingUniverse): IcttV2RankingUniverse {
  return universe === 'n10' ? 'n10' : 'n20'
}

export function rankingPosition(
  row: IcttV2MunicipalityPublic,
  universe: IcttV2RankingUniverse,
): number | null {
  return universe === 'n20' ? numericOrNull(row.rank_n20) : numericOrNull(row.rank_n10)
}
