import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Archive, ChevronDown, Clock, FlaskConical, LayoutDashboard, Loader2, Play, RefreshCw } from 'lucide-react'
import { DATA_MODE, SECTOR_META, SECTOR_ORDER, api, formatDate, formatWindow } from '../api'
import { useDigest } from '../DigestContext'
import { SectorDot } from './ui'

function Logo() {
  return (
    <div className="flex items-center gap-3 select-none">
      <div className="flex items-center gap-1.5">
        <span className="text-[26px] font-extrabold leading-none tracking-tight text-gs1-blue">GS1</span>
        <span className="text-[26px] font-extrabold leading-none tracking-tight text-gs1-orange">UK</span>
      </div>
      <span className="hidden h-6 w-px bg-gs1-gray-light-mid sm:block" />
      <div className="hidden leading-tight sm:block">
        <div className="text-sm font-bold text-gs1-blue-dark">Regulatory Radar</div>
        <div className="text-[11px] font-medium text-gs1-gray-mid">Weekly regulatory intelligence · Retail · Construction · Healthcare</div>
      </div>
    </div>
  )
}

function WeekPicker() {
  const { digests, digest, selectDigest } = useDigest()
  if (!digest) return null
  return (
    <label className="relative inline-flex items-center">
      <span className="sr-only">Select week</span>
      <select
        className="appearance-none rounded-lg border border-gs1-gray-light-mid bg-white py-2 pl-3 pr-9 text-sm font-semibold text-gs1-blue shadow-sm focus:border-gs1-blue focus:outline-none"
        value={String(digest.id)}
        onChange={(e) => selectDigest(e.target.value)}
      >
        {digests
          .filter((d) => d.status === 'completed')
          .map((d) => (
            <option key={String(d.id)} value={String(d.id)}>
              Week to {formatDate(d.window_end)}
              {d.is_sample ? ' (sample)' : ''}
            </option>
          ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 size-4 text-gs1-gray-mid" />
    </label>
  )
}

function RunNowButton() {
  const { status, refresh } = useDigest()
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  if (!status || DATA_MODE === 'static') return null
  const run = async () => {
    const token = window.prompt('Admin token to trigger a run now:')
    if (!token) return
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.runNow(token)
      setMsg(r.message)
      await refresh()
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="flex items-center gap-2">
      {msg && <span className="hidden text-xs text-gs1-gray-mid lg:inline">{msg}</span>}
      <button
        onClick={run}
        disabled={busy || status.running}
        className="inline-flex items-center gap-1.5 rounded-lg bg-gs1-orange px-3 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-gs1-orange-dark disabled:opacity-60"
        title="Run the search + AI analysis now (requires ADMIN_TOKEN)"
      >
        {status.running ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
        {status.running ? 'Running…' : 'Run now'}
      </button>
    </div>
  )
}

const navClass = ({ isActive }: { isActive: boolean }) =>
  `inline-flex items-center gap-2 border-b-[3px] px-1 pb-3 pt-3.5 text-sm font-bold no-underline transition hover:no-underline ${
    isActive ? 'border-gs1-orange text-gs1-blue-dark' : 'border-transparent text-gs1-gray-mid hover:text-gs1-blue'
  }`

export default function Layout() {
  const { status, digest, refresh } = useDigest()
  const navigate = useNavigate()
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-30 border-b border-black/5 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <button onClick={() => navigate('/')} className="text-left">
            <Logo />
          </button>
          <div className="flex items-center gap-2 sm:gap-3">
            <WeekPicker />
            <button
              onClick={() => void refresh()}
              className="rounded-lg border border-gs1-gray-light-mid bg-white p-2 text-gs1-gray-mid shadow-sm hover:text-gs1-blue"
              title="Refresh"
            >
              <RefreshCw className="size-4" />
            </button>
            <RunNowButton />
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-6 overflow-x-auto px-4 sm:px-6" aria-label="Sections">
          <NavLink to="/" end className={navClass}>
            <LayoutDashboard className="size-4" /> Overview
          </NavLink>
          {SECTOR_ORDER.map((s) => (
            <NavLink key={s} to={`/${s}`} className={navClass}>
              <SectorDot sector={s} /> {SECTOR_META[s].name}
            </NavLink>
          ))}
          <NavLink to="/archive" className={navClass}>
            <Archive className="size-4" /> Archive
          </NavLink>
        </nav>
      </header>

      {digest?.is_sample && (
        <div className="border-b border-gs1-peach/60 bg-gs1-peach/20">
          <div className="mx-auto flex max-w-7xl items-center gap-2 px-4 py-2 text-xs font-semibold text-gs1-blue-dark sm:px-6">
            <FlaskConical className="size-4 text-gs1-tangerine" />
            Sample digest – illustrates the format using real, publicly reported developments. The first scheduled run replaces it.
            {status && DATA_MODE === 'api' && !status.llm_configured && <span className="ml-1 font-normal text-gs1-gray-dark">Add an LLM API key to enable live runs.</span>}
            {DATA_MODE === 'static' && <span className="ml-1 font-normal text-gs1-gray-dark">Updated by the weekly Cursor Automation.</span>}
          </div>
        </div>
      )}

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 md:py-8">
        <Outlet />
      </main>

      <footer className="mt-8 border-t border-black/5 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-6 text-xs text-gs1-gray-mid sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="inline-flex items-center gap-1.5">
              <Clock className="size-3.5" />
              Runs every {status?.schedule ?? 'Monday 08:00 (Europe/London)'}
              {status?.next_run && <> · next: {formatDate(status.next_run, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</>}
            </span>
            {digest && <span>Current window: {formatWindow(digest)}</span>}
          </div>
          <span>
            AI analysis is decision support, not legal advice. GS1 UK is a standards body, not a regulator.
          </span>
        </div>
      </footer>
    </div>
  )
}
