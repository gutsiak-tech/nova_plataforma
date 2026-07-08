import type { Scope } from '../api/types'

export function buildDisplaySelectionKey(scope: Scope, ano: number, mes: number): string {
  return `${scope}:${ano}:${mes}`
}
