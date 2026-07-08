import { Inbox } from 'lucide-react'
import { theme } from '../../lib/theme'

export function EmptyState({
  title = 'Sem dados para este recorte',
  description = 'Não há dados disponíveis para este recorte na competência selecionada.',
}: {
  title?: string
  description?: string
}) {
  return (
    <div className={theme.emptyState.containerClass} role="status">
      <Inbox className="mb-3 h-8 w-8 text-slate-400" aria-hidden />
      <p className={theme.emptyState.titleClass}>{title}</p>
      <p className={theme.emptyState.descriptionClass}>{description}</p>
    </div>
  )
}
