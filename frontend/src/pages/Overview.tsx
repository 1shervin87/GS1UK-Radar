import { Link } from 'react-router-dom'
import { ArrowRight, Flame, Layers, Radar, Sparkles } from 'lucide-react'
import { SECTOR_META, SECTOR_ORDER, formatWindow, type SectorId } from '../api'
import { useDigest } from '../DigestContext'
import { Card, EmptyState, ErrorState, ItemCard, SectionTitle, Skeleton } from '../components/ui'

function Hero() {
  const { digest, status } = useDigest()
  if (!digest) return null
  const high = digest.items.filter((i) => i.impact === 'high').length
  return (
    <section className="digest-hero relative overflow-hidden rounded-2xl bg-gs1-blue text-white shadow-md">
      <div className="hero-accent" aria-hidden />
      <div className="digest-grid relative grid gap-8 p-6 md:grid-cols-[1.6fr_1fr] md:p-10">
        <div>
          <p className="mb-3 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider">
            <Radar className="size-3.5" /> Weekly digest · {formatWindow(digest)}
          </p>
          <h1 className="text-2xl font-extrabold leading-tight md:text-4xl">{digest.headline}</h1>
          <p className="prose-radar mt-4 max-w-3xl text-sm leading-relaxed text-white/85 md:text-base">{digest.executive_summary}</p>
        </div>
        <div className="digest-stats grid grid-cols-2 gap-3 self-start md:grid-cols-1">
          <div className="rounded-xl bg-white/10 p-4">
            <div className="text-3xl font-extrabold tabular-nums">{digest.item_count}</div>
            <div className="text-xs font-semibold uppercase tracking-wider text-white/70">relevant changes</div>
          </div>
          <div className="rounded-xl bg-white/10 p-4">
            <div className="flex items-center gap-2 text-3xl font-extrabold tabular-nums">
              <Flame className="size-6 text-gs1-orange" /> {high}
            </div>
            <div className="text-xs font-semibold uppercase tracking-wider text-white/70">high impact</div>
          </div>
          <div className="col-span-2 rounded-xl bg-white/10 p-4 md:col-span-1">
            <div className="text-xs font-semibold uppercase tracking-wider text-white/70">Sources scanned</div>
            <div className="mt-1 text-sm">
              {Number(digest.stats?.unique ?? 0).toLocaleString()} unique pages from {Number(digest.stats?.queries ?? 0)} queries across GOV.UK,
              legislation.gov.uk and the web ({status?.web_search_provider ?? 'web'})
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function SectorCards() {
  const { digest } = useDigest()
  if (!digest) return null
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {SECTOR_ORDER.map((sid: SectorId) => {
        const meta = SECTOR_META[sid]
        const count = digest.sector_counts.find((c) => c.sector === sid)
        const ov = digest.sector_overviews.find((o) => o.sector === sid)
        return (
          <Link
            key={sid}
            to={`/${sid}`}
            className={`sector-card sector-${sid} group flex flex-col rounded-xl border border-black/5 bg-white p-5 shadow-sm no-underline transition hover:-translate-y-0.5 hover:shadow-md hover:no-underline`}
            style={{ borderTop: '5px solid var(--sector)' }}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-extrabold" style={{ color: meta.colour }}>
                {meta.name}
              </h3>
              <span className="rounded-full bg-gs1-gray-light px-2.5 py-1 text-xs font-bold text-gs1-blue tabular-nums">
                {count?.total ?? 0} items · {count?.high ?? 0} high
              </span>
            </div>
            <p className="mt-2 text-sm font-semibold text-gs1-blue-dark">{ov?.headline ?? 'No overview yet'}</p>
            <p className="mt-2 line-clamp-4 flex-1 text-sm leading-relaxed text-gs1-gray-dark">{ov?.summary ?? meta.blurb}</p>
            {ov?.top_priorities?.length ? (
              <ul className="mt-3 space-y-1 text-xs text-gs1-gray-dark">
                {ov.top_priorities.slice(0, 3).map((p) => (
                  <li key={p} className="flex gap-2">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full" style={{ background: meta.colour }} />
                    <span className="line-clamp-2">{p}</span>
                  </li>
                ))}
              </ul>
            ) : null}
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-gs1-blue group-hover:text-gs1-orange">
              Open {meta.name.toLowerCase()} view <ArrowRight className="size-4" />
            </span>
          </Link>
        )
      })}
    </div>
  )
}

export default function Overview() {
  const { digest, loading, error, status } = useDigest()

  if (error) return <ErrorState message={error} />
  if (loading && !digest)
    return (
      <div className="space-y-6">
        <Skeleton className="h-64" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-56" />
          <Skeleton className="h-56" />
          <Skeleton className="h-56" />
        </div>
      </div>
    )
  if (!digest)
    return (
      <EmptyState
        title="No digest yet"
        body={
          status?.llm_configured
            ? `The first digest will be generated ${status.next_run ? 'on ' + new Date(status.next_run).toLocaleString('en-GB') : 'on the next scheduled run'}. Use "Run now" to generate one immediately.`
            : 'Configure ANTHROPIC_API_KEY or OPENAI_API_KEY on the server, then trigger a run or wait for the Monday 08:00 schedule.'
        }
      />
    )

  const top = [...digest.items].sort((a, b) => b.relevance_score - a.relevance_score).slice(0, 6)

  return (
    <div className="space-y-10">
      <Hero />

      <section>
        <SectionTitle>Sector overview</SectionTitle>
        <SectorCards />
      </section>

      {digest.cross_sector_themes.length > 0 && (
        <section>
          <SectionTitle>Cross-sector themes</SectionTitle>
          <Card className="grid gap-3 p-5 sm:grid-cols-2">
            {digest.cross_sector_themes.map((t) => (
              <div key={t} className="flex gap-3 rounded-lg bg-gs1-gray-light p-4 text-sm leading-relaxed text-gs1-gray-dark">
                <Layers className="mt-0.5 size-4 shrink-0 text-gs1-orange" />
                {t}
              </div>
            ))}
          </Card>
        </section>
      )}

      <section>
        <SectionTitle
          aside={
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-gs1-gray-mid">
              <Sparkles className="size-3.5 text-gs1-orange" /> Ranked by AI relevance to GS1 UK
            </span>
          }
        >
          Most significant changes this week
        </SectionTitle>
        {top.length === 0 ? (
          <EmptyState title="No relevant changes found this week" body="The pipeline ran but nothing passed the GS1 UK relevance test." />
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {top.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
