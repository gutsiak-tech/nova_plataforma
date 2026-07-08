import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import type { Scope } from '../api/types'
import { useMonth } from './MonthContext'
import { useScope } from './ScopeContext'

export type DisplaySelection = {
  scope: Scope
  ano: number
  mes: number
}

type DisplaySelectionContextValue = {
  displayed: DisplaySelection
  displayedLabel: string
  isTransitioning: boolean
  beginVisualTransition: (key: string) => void
  commitVisualTransition: (key: string) => void
  abortVisualTransition: (key: string) => void
}

const DisplaySelectionContext = createContext<DisplaySelectionContextValue | null>(null)

export function DisplaySelectionProvider({ children }: { children: ReactNode }) {
  const { scope } = useScope()
  const { ano, mes, label } = useMonth()

  const requestedRef = useRef<DisplaySelection & { label: string }>({
    scope,
    ano,
    mes,
    label,
  })
  requestedRef.current = { scope, ano, mes, label }

  const activeKeyRef = useRef<string | null>(null)
  const hadDisplayedRef = useRef(false)

  const [displayed, setDisplayed] = useState<DisplaySelection>({ scope, ano, mes })
  const [displayedLabel, setDisplayedLabel] = useState(label)
  const [isTransitioning, setIsTransitioning] = useState(false)

  useEffect(() => {
    if (activeKeyRef.current !== null || isTransitioning) return
    setDisplayed({ scope, ano, mes })
    setDisplayedLabel(label)
  }, [scope, ano, mes, label, isTransitioning])

  const beginVisualTransition = useCallback((key: string) => {
    activeKeyRef.current = key
    if (hadDisplayedRef.current) {
      setIsTransitioning(true)
    }
  }, [])

  const commitVisualTransition = useCallback((key: string) => {
    if (activeKeyRef.current !== key) return
    activeKeyRef.current = null
    const requested = requestedRef.current
    setDisplayed({
      scope: requested.scope,
      ano: requested.ano,
      mes: requested.mes,
    })
    setDisplayedLabel(requested.label)
    setIsTransitioning(false)
    hadDisplayedRef.current = true
  }, [])

  const abortVisualTransition = useCallback((key: string) => {
    if (activeKeyRef.current !== key) return
    activeKeyRef.current = null
    setIsTransitioning(false)
  }, [])

  const value = useMemo(
    () => ({
      displayed,
      displayedLabel,
      isTransitioning,
      beginVisualTransition,
      commitVisualTransition,
      abortVisualTransition,
    }),
    [
      displayed,
      displayedLabel,
      isTransitioning,
      beginVisualTransition,
      commitVisualTransition,
      abortVisualTransition,
    ],
  )

  return (
    <DisplaySelectionContext.Provider value={value}>{children}</DisplaySelectionContext.Provider>
  )
}

export function useDisplaySelection(): DisplaySelectionContextValue {
  const ctx = useContext(DisplaySelectionContext)
  if (!ctx) {
    throw new Error('useDisplaySelection must be used within DisplaySelectionProvider')
  }
  return ctx
}
