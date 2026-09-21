import { NavLink, Outlet, useLocation, useSearchParams, type To } from 'react-router-dom'
import clsx from 'clsx'
import {
  Activity,
  Briefcase,
  Building2,
  Brain,
  Globe,
  Info,
  Layers,
  MapPinned,
  Users,
} from 'lucide-react'
import orgmigraBrand from '../../assets/brand/orgmigra-brand.webp'
import { ScopeProvider } from '../../context/ScopeContext'
import { MonthProvider, useMonth } from '../../context/MonthContext'
import { DisplaySelectionProvider } from '../../context/DisplaySelectionContext'
import { ScopeToggle } from './ScopeToggle'
import { MonthToggle } from './MonthToggle'
import { ContextHint } from './ContextHint'
import { CompetenciaBadge } from '../ui/CompetenciaBadge'
import { DataSourceFooter } from '../ui/DataSourceFooter'
import { TerritoryBackground } from '../map/TerritoryBackground'
import { isIcttV2Path } from '../../lib/icttV2Route'
import { theme } from '../../lib/theme'

const nav = [
  { to: '/', label: 'Visão executiva', icon: Activity },
  { to: '/territorio', label: 'Território', icon: MapPinned },
  { to: '/ict', label: 'ICT', icon: Brain },
  { to: '/setores', label: 'Setores', icon: Layers },
  { to: '/ocupacoes', label: 'Ocupações', icon: Briefcase },
  { to: '/perfil', label: 'Perfil demográfico', icon: Users },
  { to: '/pais', label: 'País', icon: Globe },
  { to: '/salario', label: 'Salários', icon: Building2 },
  { to: '/sobre', label: 'Sobre os dados', icon: Info },
]

function navTarget(pathname: string, searchParams: URLSearchParams): To {
  const search = searchParams.toString()
  if (!search) return pathname
  return { pathname, search }
}

function SidebarCompetenciaCard() {
  const { label, loading } = useMonth()

  return (
    <div className={theme.shell.sidebarCompetenciaCard}>
      <p className={theme.shell.sidebarCompetenciaLabel}>Competência atual</p>
      <p className={theme.shell.sidebarCompetenciaValue}>
        {loading ? '...' : label || '—'}
      </p>
    </div>
  )
}

function AppShellLayout() {
  const [searchParams] = useSearchParams()
  const { pathname } = useLocation()
  const icttV2 = isIcttV2Path(pathname)

  return (
    <div className={theme.shell.pageGradient}>
      <div className="mx-auto flex min-h-screen max-w-[1600px] gap-5 px-4 py-5 md:px-6 lg:ml-4 lg:mr-6 lg:px-0">
        <aside className={theme.shell.sidebarClass}>
          <div>
            <div className="mb-5 flex items-center justify-center rounded-xl bg-white px-3 py-3">
              <img
                src={orgmigraBrand}
                alt="Observatório de Migrantes"
                className="h-24 w-full object-contain object-center"
                width={268}
                height={96}
              />
            </div>

            <nav className="space-y-1" aria-label="Navegação principal">
              {nav.map((item) => (
                <NavLink
                  key={item.to}
                  to={navTarget(item.to, searchParams)}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    clsx(
                      theme.shell.navLinkBase,
                      isActive ? theme.shell.navLinkActive : theme.shell.navLinkInactive,
                    )
                  }
                >
                  <item.icon className="h-4 w-4 shrink-0" aria-hidden />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </nav>
          </div>

          <SidebarCompetenciaCard />
        </aside>

        <main className="relative isolate min-w-0 flex-1 pb-10">
          <TerritoryBackground />

          <div className="relative z-10 flex min-h-[calc(100vh-2.5rem)] flex-col">
            <header className={icttV2 ? 'mb-4 space-y-4' : theme.shell.globalHeaderClass}>
              <div className="flex items-start justify-between gap-3 lg:hidden">
                <div>
                  <p className={theme.shell.sidebarBrandLabel}>Observatório de Migrantes</p>
                  <h1 className={theme.shell.mobileBrandTitle}>Migrantes no emprego formal</h1>
                </div>
                <CompetenciaBadge compact className="shrink-0" />
              </div>

              <div
                className={
                  icttV2
                    ? 'flex flex-col gap-3 xl:flex-row xl:flex-wrap xl:items-center xl:gap-5'
                    : theme.shell.globalControlsRowClass
                }
              >
                <ScopeToggle />
                {icttV2 ? null : <MonthToggle />}
                <div className="hidden shrink-0 self-center lg:block xl:min-w-[22rem]">
                  <ContextHint />
                </div>
              </div>
            </header>

            <nav
              className="mb-5 -mx-1 overflow-x-auto pb-1 lg:hidden"
              aria-label="Navegação rápida"
            >
              <div className="flex min-w-max gap-1.5">
                {nav.map((item) => (
                  <NavLink
                    key={item.to}
                    to={navTarget(item.to, searchParams)}
                    end={item.to === '/'}
                    className={({ isActive }) =>
                      clsx(
                        'rounded-full px-3 py-1.5 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-orgmigra-blue-600/40',
                        isActive ? theme.shell.mobileNavActive : theme.shell.mobileNavInactive,
                      )
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </nav>

            <div className="flex flex-1 flex-col">
              <Outlet />
            </div>

            <div className="mt-auto shrink-0">
              <DataSourceFooter />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export function AppShell() {
  return (
    <ScopeProvider>
      <MonthProvider>
        <DisplaySelectionProvider>
          <AppShellLayout />
        </DisplaySelectionProvider>
      </MonthProvider>
    </ScopeProvider>
  )
}
