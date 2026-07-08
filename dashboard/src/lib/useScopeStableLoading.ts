import { useCallback, useEffect, useRef, useState } from 'react'
import { useDisplaySelection } from '../context/DisplaySelectionContext'
import { scheduleAsyncState } from './scheduleAsyncState'

/** Evita tela de loading completa ao refetch por troca de escopo ou competência. */
export function useScopeStableLoading<T>(data: T | null, selectionKey: string) {
  const { beginVisualTransition, abortVisualTransition, isTransitioning } = useDisplaySelection()
  const [loading, setLoading] = useState(data === null)
  const hadDataRef = useRef(data !== null)
  const transitionStartedRef = useRef(false)

  useEffect(() => {
    if (data !== null) {
      hadDataRef.current = true
    }
  }, [data])

  const beginFetch = useCallback(
    (isCancelled: () => boolean, onReset?: () => void) => {
      scheduleAsyncState(isCancelled, () => {
        onReset?.()
        beginVisualTransition(selectionKey)
        transitionStartedRef.current = true
        if (!hadDataRef.current) {
          setLoading(true)
        }
      })
    },
    [beginVisualTransition, selectionKey],
  )

  const abortFetch = useCallback(() => {
    setLoading(false)
    if (transitionStartedRef.current) {
      transitionStartedRef.current = false
      abortVisualTransition(selectionKey)
    }
  }, [abortVisualTransition, selectionKey])

  const shellClass =
    isTransitioning && hadDataRef.current
      ? 'transition-opacity duration-200 ease-out opacity-[0.88]'
      : ''

  return {
    loading,
    isTransitioning,
    beginFetch,
    abortFetch,
    shellClass,
    showInitialLoader: loading && data === null,
  }
}
