import { Info } from 'lucide-react'
import { DATA_PIPELINE_FOOTER_SUFFIX, DATA_SOURCE_LABEL } from '../../lib/dataSourceMeta'
import { theme } from '../../lib/theme'

export function DataSourceFooter() {
  return (
    <p className={theme.dataSourceFooter.className}>
      <Info className="h-3.5 w-3.5 shrink-0 text-slate-600" aria-hidden />
      <span>
        Fonte: <span className="text-slate-400">{DATA_SOURCE_LABEL}</span> ·{' '}
        {DATA_PIPELINE_FOOTER_SUFFIX}
      </span>
    </p>
  )
}
