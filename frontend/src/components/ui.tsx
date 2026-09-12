import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ArrowUpRight, CalendarDays, Inbox } from 'lucide-react'
import { CHANGE_TYPE_LABEL, SECTOR_META, formatDate, type Impact, type ItemSummary, type SectorId } from '../api'

export function SectorDot({ sector, className = '' }: { sector: SectorId; className?: string }) {
  return <span className={`inline-block size-2.5 rounded-full ${SECTOR_META[sector].twBg} ${className}`} aria-hidden />
}

export function SectorPill({ sector, small = false }: { sector: SectorId; small?: boolean }) {
  const m = SECTOR_META[sector]
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border bg-white font-semibold ${m.twBorder} ${m.twText} ${small ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'}`}
    >
      <SectorDot sector={sector} />
      {m.name}
    </span>
  )
}

const IMPACT_STYLE: Record<Impact, string> = {
  high: 'bg-gs1-orange-light text-gs1-orange-dark',
  medium: 'bg-gs1-peach text-gs1-blue-dark',
  low: 'bg-gs1-gray-light text-gs1-gray-dark border border-gs1-gray-light-mid',
}

export function ImpactBadge({ impact }: { impact: Impact }) {
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide ${IMPACT_STYLE[impact]}`}>
      {impact} impact
    </span>
  )
}

export function TypeBadge({ type }: { type: string }) {
  return (
    <span className="inline-flex items-center rounded-md bg-gs1-blue-light px-2 py-0.5 text-[11px] font-semibold text-gs1-blue">
      {CHANGE_TYPE_LABEL[type] ?? type}
    </span>
  )
}

export function Score({ value }: { value: number }) {
  const tone = value >= 85 ? 'text-gs1-orange' : value >= 70 ? 'text-gs1-blue' : 'text-gs1-gray-mid'
  return (
    <div className="flex flex-col items-end leading-none" title="AI relevance score to GS1 UK (0–100)">
      <span className={`text-2xl font-extrabold tabular-nums ${tone}`}>{value}</span>
      <span className="text-[10px] font-semibold uppercase tracking-wider text-gs1-gray-mid">relevance</span>
    </div>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`radar-card rounded-xl border border-black/5 bg-white shadow-sm ${className}`}>{children}</div>
}

export function SectionTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="section-heading mb-4 flex items-end justify-between gap-4">
      <h2 className="text-lg font-bold text-gs1-blue md:text-xl">{children}</h2>
      {aside}
    </div>
  )
}

export function ItemCard({ item, showSector = true }: { item: ItemSummary; showSector?: boolean }) {
  const nextDate = item.key_dates?.[0]
  return (
    <Link
      to={`/items/${item.id}`}
      className={`item-card sector-${item.primary_sector} fade-up group block rounded-xl border border-black/5 bg-white p-5 shadow-sm no-underline transition hover:-translate-y-0.5 hover:shadow-md hover:no-underline`}
      style={{ borderLeft: '5px solid var(--sector)' }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <ImpactBadge impact={item.impact} />
            <TypeBadge type={item.change_type} />
            {showSector && item.sectors.map((s) => <SectorPill key={s} sector={s} small />)}
          </div>
          <h3 className="text-base font-bold leading-snug text-gs1-blue-dark group-hover:text-gs1-blue md:text-lg">{item.title}</h3>
          <p className="mt-1 text-xs font-medium text-gs1-gray-mid">
            {item.issuing_body || item.publisher}
            {item.published_at ? ` · ${formatDate(item.published_at)}` : ''}
          </p>
          <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-gs1-gray-dark">{item.summary}</p>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
            {item.gs1_standards_implicated.length > 0 && (
              <span className="flex flex-wrap gap-1">
                {item.gs1_standards_implicated.slice(0, 4).map((s) => (
                  <span key={s} className="rounded bg-gs1-gray-light px-1.5 py-0.5 font-semibold text-gs1-blue">
                    {s}
                  </span>
                ))}
                {item.gs1_standards_implicated.length > 4 && (
                  <span className="px-1 text-gs1-gray-mid">+{item.gs1_standards_implicated.length - 4}</span>
                )}
              </span>
            )}
            {nextDate && (
              <span className="inline-flex items-center gap-1 text-gs1-gray-mid">
                <CalendarDays className="size-3.5" /> {nextDate.date}: {nextDate.label}
              </span>
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-3">
          <Score value={item.relevance_score} />
          <ArrowUpRight className="size-5 text-gs1-gray-light-mid transition group-hover:text-gs1-orange" />
        </div>
      </div>
    </Link>
  )
}

export function EmptyState({ title, body, icon }: { title: string; body?: string; icon?: ReactNode }) {
  return (
    <Card className="flex flex-col items-center px-6 py-14 text-center">
      <div className="mb-3 text-gs1-gray-light-mid">{icon ?? <Inbox className="size-10" />}</div>
      <p className="font-bold text-gs1-blue">{title}</p>
      {body && <p className="mt-1 max-w-md text-sm text-gs1-gray-mid">{body}</p>}
    </Card>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <Card className="flex items-start gap-3 border-gs1-danger/30 bg-red-50 p-5">
      <AlertTriangle className="mt-0.5 size-5 shrink-0 text-gs1-danger" />
      <div>
        <p className="font-bold text-gs1-danger">Something went wrong</p>
        <p className="text-sm text-gs1-gray-dark">{message}</p>
      </div>
    </Card>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-gs1-gray-light-mid/40 ${className}`} />
}
