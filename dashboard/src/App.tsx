import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { LoadingState } from './components/ui/LoadingState'
import { ExecutivePageLoading } from './components/ui/ExecutivePageLoading'

const ExecutivePage = lazy(() =>
  import('./pages/ExecutivePage').then((m) => ({ default: m.ExecutivePage })),
)
const TerritoryPage = lazy(() =>
  import('./pages/TerritoryPage').then((m) => ({ default: m.TerritoryPage })),
)
const SectorPage = lazy(() => import('./pages/SectorPage').then((m) => ({ default: m.SectorPage })))
const OccupationPage = lazy(() =>
  import('./pages/OccupationPage').then((m) => ({ default: m.OccupationPage })),
)
const ProfilesPage = lazy(() =>
  import('./pages/ProfilesPage').then((m) => ({ default: m.ProfilesPage })),
)
const CountryPage = lazy(() =>
  import('./pages/CountryPage').then((m) => ({ default: m.CountryPage })),
)
const SalaryPage = lazy(() => import('./pages/SalaryPage').then((m) => ({ default: m.SalaryPage })))
const IctPage = lazy(() => import('./pages/IctPage').then((m) => ({ default: m.IctPage })))
const AboutDataPage = lazy(() =>
  import('./pages/AboutDataPage').then((m) => ({ default: m.AboutDataPage })),
)

function IndexPageFallback() {
  return <ExecutivePageLoading />
}

function PageFallback() {
  return (
    <div className="min-h-[28rem]" aria-busy="true" aria-live="polite">
      <LoadingState rows={2} label="Carregando página..." />
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route
          index
          element={
            <Suspense fallback={<IndexPageFallback />}>
              <ExecutivePage />
            </Suspense>
          }
        />
        <Route
          path="territorio"
          element={
            <Suspense fallback={<PageFallback />}>
              <TerritoryPage />
            </Suspense>
          }
        />
        <Route
          path="setores"
          element={
            <Suspense fallback={<PageFallback />}>
              <SectorPage />
            </Suspense>
          }
        />
        <Route
          path="ocupacoes"
          element={
            <Suspense fallback={<PageFallback />}>
              <OccupationPage />
            </Suspense>
          }
        />
        <Route
          path="perfil"
          element={
            <Suspense fallback={<PageFallback />}>
              <ProfilesPage />
            </Suspense>
          }
        />
        <Route
          path="pais"
          element={
            <Suspense fallback={<PageFallback />}>
              <CountryPage />
            </Suspense>
          }
        />
        <Route
          path="salario"
          element={
            <Suspense fallback={<PageFallback />}>
              <SalaryPage />
            </Suspense>
          }
        />
        <Route
          path="ict"
          element={
            <Suspense fallback={<PageFallback />}>
              <IctPage />
            </Suspense>
          }
        />
        <Route
          path="sobre"
          element={
            <Suspense fallback={<PageFallback />}>
              <AboutDataPage />
            </Suspense>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
