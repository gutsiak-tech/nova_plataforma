import clsx from 'clsx'
import { motion } from 'framer-motion'
import type { ReactNode } from 'react'
import { theme } from '../../lib/theme'

export function Card({
  children,
  className,
  hover = true,
  surface = 'default',
  enter = true,
}: {
  children: ReactNode
  className?: string
  hover?: boolean
  /** `translucent` — cards de gráfico (páginas internas). */
  /** `executive` — Visão Executiva (mesma superfície clara). */
  surface?: 'default' | 'translucent' | 'executive'
  /** Animação de entrada; desligar em painéis estáveis (ex.: mapa). */
  enter?: boolean
}) {
  const surfaceClass =
    surface === 'executive'
      ? [theme.card.translucentClass, theme.chartCard.executiveSurfaceClass]
      : surface === 'translucent'
        ? [theme.card.translucentClass, theme.chartCard.surfaceClass]
        : theme.card.baseClass

  const classNames = clsx(surfaceClass, hover && theme.card.hoverClass, className)

  if (!enter) {
    return <div className={classNames}>{children}</div>
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={classNames}
    >
      {children}
    </motion.div>
  )
}
