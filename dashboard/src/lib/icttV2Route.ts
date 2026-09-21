/**
 * Experiência pública ICTT v2 (`/ict`).
 * `/ict-v2` permanece reconhecida só para o redirect legado.
 * `/ict-v1` é a V1 e não entra neste recorte.
 */
export function isIcttV2Path(pathname: string): boolean {
  if (pathname === '/ict-v1' || pathname.startsWith('/ict-v1/')) return false
  return (
    pathname === '/ict' ||
    pathname.startsWith('/ict/') ||
    pathname === '/ict-v2' ||
    pathname.startsWith('/ict-v2/')
  )
}
