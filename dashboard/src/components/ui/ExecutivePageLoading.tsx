/** Loading inicial minimalista da Visão Executiva — sem skeletons de cards. */
export function ExecutivePageLoading() {
  return (
    <div
      className="flex min-h-[calc(100vh-14rem)] flex-col items-center justify-center"
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label="Carregando visão executiva"
    >
      <div className="flex flex-col items-center gap-3">
        <div
          className="h-5 w-5 rounded-full border-2 border-slate-200 border-t-orgmigra-blue-600/70 motion-safe:animate-spin"
          aria-hidden
        />
        <p className="text-sm text-slate-500">Carregando visão executiva...</p>
      </div>
    </div>
  )
}
