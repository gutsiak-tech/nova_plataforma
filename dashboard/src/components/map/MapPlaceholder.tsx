import { MapPinned } from 'lucide-react'
import { Card } from '../ui/Card'
import { theme } from '../../lib/theme'

type MapPlaceholderProps = {
  message?: string
}

export function MapPlaceholder({ message }: MapPlaceholderProps) {
  const body =
    message ??
    'O painel já organiza o recorte municipal em tabelas e rankings. Quando o pipeline de tiles/PostGIS estiver estável, este painel receberá um mapa coroplético ligado aos mesmos identificadores territoriais.'

  return (
    <Card enter={false} className="relative overflow-hidden">
      <div className={theme.mapPlaceholder.gradientClass} />
      <div className="relative flex flex-col items-start gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-start gap-3">
          <div className={theme.mapPlaceholder.iconWrapClass}>
            <MapPinned className={theme.mapPlaceholder.iconClass} aria-hidden />
          </div>
          <div>
            <h3 className={theme.mapPlaceholder.titleClass}>Camada cartográfica</h3>
            <p className={theme.mapPlaceholder.bodyClass}>{body}</p>
          </div>
        </div>
        <div className={theme.mapPlaceholder.badgeClass}>
          {message ? 'Mapa indisponível' : 'Placeholder intencional · integração futura'}
        </div>
      </div>
    </Card>
  )
}
