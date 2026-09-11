import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Building2,
  CalendarDays,
  CheckCircle2,
  ExternalLink,
  FileText,
  Landmark,
  Lightbulb,
  ShieldCheck,
  Target,
  Users,
} from 'lucide-react'
import { CHANGE_TYPE_LABEL, SECTOR_META, api, ApiError, formatDate, type Item, type NextStep } from '../api'
import { Card, ErrorState, ImpactBadge, SectorPill, Skeleton, TypeBadge } from '../components/ui'

const PRIORITY_STYLE: Record<NextStep['priority'], { label: string; cls: string }> = {
  now: { label: 'Act now', cls: 'bg-gs1-orange text-white' },
  next_quarter: { label: 'Next quarter', cls: 'bg-gs1-blue text-white' },
  monitor: { label: 'Monitor', cls: 'bg-gs1-gray-light text-gs1-gray-dark border border-gs1-gray-light-mid' },
}
const AUDIENCE_LABEL: Record<NextStep['audience'], string> = { gs1_uk: 'GS1 UK', members: 'Members', both: 'GS1 UK & members' }
const LINK_KIND_LABEL: Record<string, string> = { primary: 'Primary source', official: 'Official', guidance: 'Guidance', gs1: 'GS1', news: 'News', other: 'Related' }

function Block({ icon, title, children, accent = false }: { icon: React.ReactNode; title: string; children: React.ReactNode; accent?: boolean }) {
  return (
    <Card className={`p-6 ${accent ? 'border-gs1-orange/40 bg-gs1-orange-light/40' : ''}`}>
      <h2 className="mb-3 inline-flex items-center gap-2 text-base font-extrabold text-gs1-blue">
        <span className={accent ? 'text-gs1-orange' : 'text-gs1-link'}>{icon}</span>
        {title}
      </h2>
      {children}
    </Card>
  )
}

function Paragraphs({ text }: { text: string }) {
  return (
    <div className="prose-radar text-sm leading-relaxed text-gs1-gray-dark md:text-[15px]">
      {text.split(/\n{2,}|\n(?=[A-Z•-])/).map((p, i) => (
        <p key={i}>{p.trim()}</p>
      ))}
    </div>
  )
}

export default function ItemPage() {
  const { id } = useParams<{ id: string }>()
  const [item, setItem] = useState<Item | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setItem(null)
    setError(null)
    api
      .item(id ?? '')
      .then(setItem)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'Failed to load item'))
  }, [id])

  if (error) return <ErrorState message={error} />
  if (!item)
    return (
      <div className="space-y-4">
        <Skeleton className="h-40" />
        <Skeleton className="h-64" />
      </div>
    )

  const meta = SECTOR_META[item.primary_sector]
  const gs1Steps = item.next_steps.filter((s) => s.audience !== 'members')
  const memberSteps = item.next_steps.filter((s) => s.audience !== 'gs1_uk')

  return (
    <div className={`sector-${item.primary_sector} space-y-6`}>
      <Link to={`/${item.primary_sector}`} className="inline-flex items-center gap-1 text-sm font-semibold text-gs1-gray-mid no-underline hover:text-gs1-blue">
        <ArrowLeft className="size-4" /> Back to {meta.name}
      </Link>

      <header className="rounded-2xl bg-white p-6 shadow-sm md:p-8" style={{ borderLeft: '6px solid var(--sector)' }}>
        <div className="flex flex-wrap items-center gap-2">
          <ImpactBadge impact={item.impact} />
          <TypeBadge type={item.change_type} />
          {item.sectors.map((s) => (
            <SectorPill key={s} sector={s} small />
          ))}
          <span className="ml-auto text-xs font-semibold text-gs1-gray-mid">
            Relevance <span className="text-base font-extrabold text-gs1-orange tabular-nums">{item.relevance_score}</span>/100 · confidence {item.confidence}
          </span>
        </div>
        <h1 className="mt-3 text-2xl font-extrabold leading-tight text-gs1-blue-dark md:text-3xl">{item.title}</h1>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
          <div className="flex items-start gap-2">
            <Landmark className="mt-0.5 size-4 shrink-0 text-gs1-gray-mid" />
            <div>
              <dt className="text-[11px] font-bold uppercase tracking-wider text-gs1-gray-mid">Issuing body</dt>
              <dd className="font-semibold text-gs1-gray-dark">{item.issuing_body || item.publisher}</dd>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <CalendarDays className="mt-0.5 size-4 shrink-0 text-gs1-gray-mid" />
            <div>
              <dt className="text-[11px] font-bold uppercase tracking-wider text-gs1-gray-mid">Published</dt>
              <dd className="font-semibold text-gs1-gray-dark">{formatDate(item.published_at)}</dd>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Building2 className="mt-0.5 size-4 shrink-0 text-gs1-gray-mid" />
            <div>
              <dt className="text-[11px] font-bold uppercase tracking-wider text-gs1-gray-mid">Jurisdiction · type</dt>
              <dd className="font-semibold text-gs1-gray-dark">
                {item.jurisdiction} · {CHANGE_TYPE_LABEL[item.change_type] ?? item.change_type}
              </dd>
            </div>
          </div>
        </dl>
        <p className="mt-5 text-[15px] font-medium leading-relaxed text-gs1-blue-dark">{item.summary}</p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-6">
          <Block icon={<FileText className="size-5" />} title="What changed">
            <Paragraphs text={item.what_changed} />
          </Block>

          <Block icon={<Lightbulb className="size-5" />} title="Why this matters to GS1 UK" accent>
            <Paragraphs text={item.why_it_matters_to_gs1} />
            {item.gs1_standards_implicated.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1.5">
                {item.gs1_standards_implicated.map((s) => (
                  <span key={s} className="rounded-md bg-white px-2 py-1 text-xs font-bold text-gs1-blue shadow-sm ring-1 ring-gs1-blue/10">
                    {s}
                  </span>
                ))}
              </div>
            )}
          </Block>

          <Block icon={<Target className="size-5" />} title="Recommended next steps">
            <div className="grid gap-5 md:grid-cols-2">
              {[
                { label: 'For GS1 UK', steps: gs1Steps },
                { label: 'For affected members', steps: memberSteps },
              ].map(({ label, steps }) => (
                <div key={label}>
                  <p className="mb-2 text-xs font-bold uppercase tracking-wider text-gs1-gray-mid">{label}</p>
                  {steps.length === 0 ? (
                    <p className="text-sm text-gs1-gray-mid">No specific action identified.</p>
                  ) : (
                    <ul className="space-y-3">
                      {steps.map((s, i) => (
                        <li key={i} className="flex gap-3 rounded-lg bg-gs1-gray-light p-3 text-sm text-gs1-gray-dark">
                          <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-gs1-grass" />
                          <div>
                            <div className="mb-1 flex flex-wrap gap-1.5">
                              <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${PRIORITY_STYLE[s.priority].cls}`}>
                                {PRIORITY_STYLE[s.priority].label}
                              </span>
                              {s.audience === 'both' && <span className="rounded bg-white px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-gs1-blue">{AUDIENCE_LABEL.both}</span>}
                            </div>
                            {s.action}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </Block>
        </div>

        <aside className="space-y-6">
          {item.key_dates.length > 0 && (
            <Block icon={<CalendarDays className="size-5" />} title="Key dates">
              <ol className="relative ml-2 space-y-4 border-l-2 border-gs1-gray-light-mid/60 pl-5">
                {item.key_dates.map((d, i) => (
                  <li key={i} className="relative text-sm">
                    <span className="absolute -left-[27px] top-1 size-3 rounded-full ring-4 ring-white" style={{ background: meta.colour }} />
                    <div className="font-extrabold text-gs1-blue-dark">{d.date}</div>
                    <div className="text-gs1-gray-dark">{d.label}</div>
                  </li>
                ))}
              </ol>
            </Block>
          )}

          {item.affected_stakeholders.length > 0 && (
            <Block icon={<Users className="size-5" />} title="Who is affected">
              <ul className="flex flex-wrap gap-1.5">
                {item.affected_stakeholders.map((s) => (
                  <li key={s} className="rounded-full bg-gs1-gray-light px-2.5 py-1 text-xs font-semibold text-gs1-gray-dark">
                    {s}
                  </li>
                ))}
              </ul>
            </Block>
          )}

          <Block icon={<ExternalLink className="size-5" />} title="Sources and related links">
            <ul className="space-y-2.5">
              {item.links.map((l) => (
                <li key={l.url} className="text-sm">
                  <a href={l.url} target="_blank" rel="noreferrer noopener" className="group inline-flex items-start gap-2 font-semibold">
                    <ExternalLink className="mt-0.5 size-3.5 shrink-0 opacity-60 group-hover:opacity-100" />
                    <span>
                      {l.label}
                      <span className="ml-1.5 rounded bg-gs1-gray-light px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-gs1-gray-mid no-underline">
                        {LINK_KIND_LABEL[l.kind] ?? l.kind}
                      </span>
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          </Block>

          <Card className="p-4 text-xs leading-relaxed text-gs1-gray-mid">
            <p className="inline-flex items-center gap-1.5 font-bold text-gs1-gray-dark">
              <ShieldCheck className="size-4 text-gs1-mint" /> About this analysis
            </p>
            <p className="mt-1">
              Generated by the Regulatory Radar AI agent from the linked sources, grounded in a GS1 UK reference brief. Found via the {item.source_connector || 'search'} connector. Verify against primary sources before acting; GS1 UK is a standards body, not a regulator, and GS1 standards do not by themselves constitute compliance.
            </p>
          </Card>
        </aside>
      </div>
    </div>
  )
}
