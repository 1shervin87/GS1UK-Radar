import { useMemo, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { Eye, ListChecks, SlidersHorizontal } from 'lucide-react'
import { SECTOR_META, SECTOR_ORDER, formatWindow, type Impact, type SectorId } from '../api'
import { useDigest } from '../DigestContext'
import { Card, EmptyState, ErrorState, ItemCard, SectionTitle, Skeleton } from '../components/ui'

type SortKey = 'relevance' | 'impact' | 'date'
const IMPACT_RANK: Record<Impact, number> = { high: 3, medium: 2, low: 1 }

export default function SectorPage() {
  const { sector } = useParams<{ sector: string }>()
  const { digest, loading, error } = useDigest()
  const [impact, setImpact] = useState<Impact | 'all'>('all')
  const [sort, setSort] = useState<SortKey>('relevance')
  const [onlyPrimary, setOnlyPrimary] = useState(false)

  const sid = sector as SectorId
  const valid = SECTOR_ORDER.includes(sid)

  const items = useMemo(() => {
    if (!digest || !valid) return []
    let list = digest.items.filter((i) => (onlyPrimary ? i.primary_sector === sid : i.sectors.includes(sid) || i.primary_sector === sid))
    if (impact !== 'all') list = list.filter((i) => i.impact === impact)
    return [...list].sort((a, b) => {
      if (sort === 'impact') return IMPACT_RANK[b.impact] - IMPACT_RANK[a.impact] || b.relevance_score - a.relevance_score
      if (sort === 'date') return (b.published_at ?? '').localeCompare(a.published_at ?? '')
      return b.relevance_score - a.relevance_score
    })
  }, [digest, valid, sid, impact, sort, onlyPrimary])

  if (!valid) return <Navigate to="/" replace />
  if (error) return <ErrorState message={error} />
  if (loading && !digest) return <Skeleton className="h-96" />
  if (!digest) return <EmptyState title="No digest yet" />

  const meta = SECTOR_META[sid]
  const ov = digest.sector_overviews.find((o) => o.sector === sid)
  const counts = digest.sector_counts.find((c) => c.sector === sid)

  return (
    <div className={`sector-${sid} space-y-8`}>
      <section className="relative overflow-hidden rounded-2xl bg-white shadow-sm" style={{ borderTop: '6px solid var(--sector)' }}>
        <div className="grid gap-6 p-6 md:grid-cols-[1.5fr_1fr] md:p-8">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider" style={{ color: meta.colour }}>
              {meta.name} · {formatWindow(digest)}
            </p>
            <h1 className="mt-1 text-2xl font-extrabold text-gs1-blue-dark md:text-3xl">{ov?.headline ?? `${meta.name} regulatory changes`}</h1>
            <p className="prose-radar mt-3 text-sm leading-relaxed text-gs1-gray-dark md:text-base">{ov?.summary ?? meta.blurb}</p>
            <div className="mt-4 flex gap-6 text-sm">
              <div>
                <span className="text-2xl font-extrabold tabular-nums text-gs1-blue">{counts?.total ?? 0}</span>
                <span className="ml-1.5 text-gs1-gray-mid">relevant items</span>
              </div>
              <div>
                <span className="text-2xl font-extrabold tabular-nums text-gs1-orange">{counts?.high ?? 0}</span>
                <span className="ml-1.5 text-gs1-gray-mid">high impact</span>
              </div>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-1">
            {ov?.top_priorities?.length ? (
              <div className="rounded-xl bg-gs1-gray-light p-4">
                <p className="mb-2 inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-gs1-blue">
                  <ListChecks className="size-4" /> Top priorities
                </p>
                <ol className="space-y-1.5 text-sm text-gs1-gray-dark">
                  {ov.top_priorities.map((p, i) => (
                    <li key={p} className="flex gap-2">
                      <span className="font-extrabold tabular-nums" style={{ color: meta.colour }}>
                        {i + 1}.
                      </span>
                      <span>{p}</span>
                    </li>
                  ))}
                </ol>
              </div>
            ) : null}
            {ov?.watchlist?.length ? (
              <div className="rounded-xl bg-gs1-gray-light p-4">
                <p className="mb-2 inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-gs1-blue">
                  <Eye className="size-4" /> Watchlist
                </p>
                <ul className="space-y-1.5 text-sm text-gs1-gray-dark">
                  {ov.watchlist.map((w) => (
                    <li key={w} className="flex gap-2">
                      <span className="mt-2 size-1.5 shrink-0 rounded-full" style={{ background: meta.colour }} />
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section>
        <SectionTitle
          aside={
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <SlidersHorizontal className="size-4 text-gs1-gray-mid" />
              <select value={impact} onChange={(e) => setImpact(e.target.value as Impact | 'all')} className="rounded-md border border-gs1-gray-light-mid bg-white px-2 py-1 font-semibold text-gs1-blue">
                <option value="all">All impacts</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
              <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} className="rounded-md border border-gs1-gray-light-mid bg-white px-2 py-1 font-semibold text-gs1-blue">
                <option value="relevance">Sort: relevance</option>
                <option value="impact">Sort: impact</option>
                <option value="date">Sort: date</option>
              </select>
              <label className="inline-flex items-center gap-1.5 font-semibold text-gs1-gray-dark">
                <input type="checkbox" checked={onlyPrimary} onChange={(e) => setOnlyPrimary(e.target.checked)} className="accent-gs1-orange" />
                Primary only
              </label>
            </div>
          }
        >
          Changes affecting {meta.name.toLowerCase()}
        </SectionTitle>

        {items.length === 0 ? (
          <EmptyState title={`Nothing for ${meta.name.toLowerCase()} matches these filters`} body="Try clearing the impact filter or including cross-sector items." />
        ) : (
          <div className="grid gap-4">
            {items.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>

      <Card className="p-5 text-sm text-gs1-gray-dark">
        <p className="font-bold text-gs1-blue">How relevance is judged for {meta.name.toLowerCase()}</p>
        <p className="mt-1 leading-relaxed">{meta.blurb} Items are kept only when they require or reference unique identification, machine-readable data carriers, structured product data sharing, or change traceability, labelling and recall duties in ways that touch GS1 standards or GS1 UK programmes.</p>
      </Card>
    </div>
  )
}
