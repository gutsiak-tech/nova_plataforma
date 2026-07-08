import { useState } from 'react'
import clsx from 'clsx'
import {
  circleFlagSvgUrl,
  countryNameToIso2,
  getCountryInitials,
  rectangularFlagUrl,
} from '../../lib/countryNameToIso2'

export type CountryFlagBadgeProps = {
  countryName: string
  size?: 'sm' | 'md'
  className?: string
}

export function CountryFlagBadge({
  countryName,
  size = 'md',
  className,
}: CountryFlagBadgeProps) {
  const iso2 = countryNameToIso2(countryName)
  const [flagFailed, setFlagFailed] = useState(false)
  const showFlag = iso2 && !flagFailed
  const initials = getCountryInitials(countryName)

  const sizeClass =
    size === 'sm' ? 'h-9 w-9 text-[10px]' : 'h-11 w-11 text-xs sm:h-12 sm:w-12'

  return (
    <div
      className={clsx(
        'shrink-0 overflow-hidden rounded-full border-2 border-white bg-slate-100 shadow-sm ring-1 ring-slate-200/80',
        sizeClass,
        className,
      )}
      aria-hidden
    >
      {showFlag ? (
        <img
          src={circleFlagSvgUrl(iso2)}
          alt=""
          className="h-full w-full object-cover"
          loading="lazy"
          decoding="async"
          onError={() => setFlagFailed(true)}
        />
      ) : (
        <span className="flex h-full w-full items-center justify-center bg-slate-100 font-semibold text-slate-600">
          {initials}
        </span>
      )}
    </div>
  )
}

export type CountryFlagPanelProps = {
  countryName: string
  className?: string
}

/** Bandeira retangular como fundo do mini-card. */
export function CountryFlagPanel({ countryName, className }: CountryFlagPanelProps) {
  const iso2 = countryNameToIso2(countryName)
  const [flagFailed, setFlagFailed] = useState(false)
  const showFlag = iso2 && !flagFailed
  const initials = getCountryInitials(countryName)

  return (
    <div className={clsx('country-mini-card__flag', className)} aria-hidden>
      {showFlag ? (
        <img
          src={rectangularFlagUrl(iso2)}
          alt=""
          className="country-mini-card__flag-image"
          loading="lazy"
          decoding="async"
          onError={() => setFlagFailed(true)}
        />
      ) : (
        <span className="country-mini-card__flag-fallback">{initials}</span>
      )}
    </div>
  )
}
