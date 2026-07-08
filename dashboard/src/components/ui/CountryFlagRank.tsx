import { memo, useMemo } from 'react'
import clsx from 'clsx'
import type { GoldRow } from '../../api/types'
import { GOLD_COLUMNS } from '../../api/goldColumns'
import { formatCompact, formatInt, formatSignedInt } from '../../lib/format'
import { CountryFlagPanel } from './CountryFlagAvatar'

export type CountryFlagRankProps = {
  rows: GoldRow[]
  className?: string
}

function titleCaseCountry(name: string): string {
  return name
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function saldoToneClass(saldo: number): string {
  if (saldo > 0) return 'text-orgmigra-green-700'
  if (saldo < 0) return 'text-rose-700'
  return 'text-slate-700'
}

export const CountryFlagRank = memo(function CountryFlagRank({ rows, className }: CountryFlagRankProps) {
  const totalPositiveSaldo = useMemo(
    () =>
      rows.reduce((sum, row) => {
        const value = Number(row[GOLD_COLUMNS.SALDO])
        return sum + (Number.isFinite(value) && value > 0 ? value : 0)
      }, 0),
    [rows],
  )

  if (!rows.length) {
    return (
      <p className="text-sm text-slate-500">
        Sem dados de país para o escopo e competência selecionados.
      </p>
    )
  }

  return (
    <div
      className={clsx(
        'grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 lg:gap-4',
        className,
      )}
    >
      {rows.map((row, index) => {
        const countryName = String(row[GOLD_COLUMNS.PAIS] ?? '—')
        const saldo = Number(row[GOLD_COLUMNS.SALDO])
        const admissoes = row[GOLD_COLUMNS.ADMISSOES]
        const desligamentos = row[GOLD_COLUMNS.DESLIGAMENTOS]
        const share =
          totalPositiveSaldo > 0 && Number.isFinite(saldo) && saldo > 0
            ? (saldo / totalPositiveSaldo) * 100
            : null

        return (
          <div
            key={`${countryName}-${index}`}
            className="country-mini-card group relative flex min-h-[9.5rem] overflow-hidden rounded-xl sm:min-h-[10rem]"
          >
            <CountryFlagPanel countryName={countryName} />

            <div className="country-mini-card__content p-3 sm:p-3.5">
              <p
                className="line-clamp-2 min-h-[2.25rem] pr-1 text-xs font-semibold leading-snug text-slate-800 sm:text-[13px]"
                title={countryName}
              >
                <span className="font-semibold text-slate-500">#{index + 1}</span>{' '}
                {titleCaseCountry(countryName)}
              </p>

              <p
                className={clsx(
                  'mt-1.5 text-lg font-semibold tabular-nums leading-none sm:text-xl',
                  saldoToneClass(saldo),
                )}
              >
                {formatSignedInt(saldo)}
              </p>

              <p className="mt-2 text-[10px] leading-relaxed text-slate-500 sm:text-[11px]">
                <span className="block">
                  Adm.{' '}
                  <span className="font-medium text-slate-600">{formatCompact(admissoes)}</span>
                </span>
                <span className="block">
                  Desl.{' '}
                  <span className="font-medium text-slate-600">
                    {formatCompact(desligamentos)}
                  </span>
                </span>
              </p>
            </div>

            <div
              role="tooltip"
              className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 w-max max-w-[15rem] -translate-x-1/2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-xs text-slate-700 opacity-0 shadow-md transition-opacity duration-150 group-hover:opacity-100"
            >
              <p className="font-semibold text-slate-900">{countryName}</p>
              <dl className="mt-1.5 space-y-0.5">
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Saldo</dt>
                  <dd className="font-medium tabular-nums text-slate-800">{formatSignedInt(saldo)}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Admissões</dt>
                  <dd className="tabular-nums">{formatInt(admissoes)}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Desligamentos</dt>
                  <dd className="tabular-nums">{formatInt(desligamentos)}</dd>
                </div>
                {share != null ? (
                  <div className="flex justify-between gap-4 border-t border-slate-100 pt-1">
                    <dt className="text-slate-500">Participação</dt>
                    <dd className="tabular-nums">{share.toFixed(1)}%</dd>
                  </div>
                ) : null}
              </dl>
            </div>
          </div>
        )
      })}
    </div>
  )
})
