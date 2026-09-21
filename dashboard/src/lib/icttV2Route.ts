/** Rota de preview ICTT v2. Isolada da V1 (`/ict`). */
export function isIcttV2Path(pathname: string): boolean {
  return pathname === '/ict-v2' || pathname.startsWith('/ict-v2/')
}
