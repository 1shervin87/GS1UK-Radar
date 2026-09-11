import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarRange, Search } from 'lucide-react'
import { SECTOR_META, SECTOR_ORDER, api, formatDate, formatWindow, type ItemSummary, type SectorId } from '../api'
import { useDigest } from '../DigestContext'
import { Card, EmptyState, ItemCard, SectionTitle, SectorDot } from '../components/ui'

export default function Archive() {
  const { digests, digest, selectDigest } = useDigest()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [sector, setSector] = useState<SectorId | ''>('')
  const [results, setResults] = useState<ItemSummary[] | null>(null)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    if (!q.trim()) {
      setResults(null)
      return
    }
    const t = setTimeout(() => {
      setSearching(true)
      api
        .search(q.trim(), sector || undefined)
        .then(setResults)
        .catch(() => setResults([]))
        .finally(() => setSearching(false))
    }, 300)
    return () => clearTimeout(t)
  }, [q, sector])

  return (
    <div className="space-y-8">
      <section>
        <SectionTitle>Search all analysed changes</SectionTitle>
        <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
          <label className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-gs1-gray-mid" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. UDI, deposit return, golden thread, QR code…"
              className="w-full rounded-lg border border-gs1-gray-light-mid py-2 pl-9 pr-3 text-sm focus:border-gs1-blue focus:outline-none"
            />
          </label>
          <select value={sector} onChange={(e) => setSector(e.target.value as SectorId | '')} className="rounded-lg border border-gs1-gray-light-mid bg-white px-3 py-2 text-sm font-semibold text-gs1-blue">
            <option value="">All sectors</option>
            {SECTOR_ORDER.map((s) => (
              <option key={s} value={s}>
                {SECTOR_META[s].name}
              </option>
            ))}
          </select>
        </Card>
        {results !== null && (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {searching && <p className="text-sm text-gs1-gray-mid">Searching…</p>}
            {!searching && results.length === 0 && <EmptyState title="No matches" />}
            {results.map((i) => (
              <ItemCard key={i.id} item={i} />
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionTitle>Weekly digests</SectionTitle>
        {digests.length === 0 ? (
          <EmptyState title="No digests yet" />
        ) : (
          <div className="overflow-hidden rounded-xl border border-black/5 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gs1-blue text-left text-xs font-bold uppercase tracking-wider text-white">
                <tr>
                  <th className="px-4 py-3">Week</th>
                  <th className="hidden px-4 py-3 md:table-cell">Headline</th>
                  <th className="px-4 py-3 text-center">Items</th>
                  {SECTOR_ORDER.map((s) => (
                    <th key={s} className="hidden px-3 py-3 text-center lg:table-cell">
                      <span className="inline-flex items-center gap-1.5">
                        <SectorDot sector={s} /> {SECTOR_META[s].name}
                      </span>
                    </th>
                  ))}
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gs1-gray-light">
                {digests.map((d) => (
                  <tr
                    key={d.id}
                    className={`cursor-pointer transition hover:bg-gs1-blue-light/60 ${String(digest?.id) === String(d.id) ? 'bg-gs1-blue-light/40' : ''}`}
                    onClick={() => {
                      if (d.status === 'completed') {
                        selectDigest(d.id)
                        navigate('/')
                      }
                    }}
                  >
                    <td className="px-4 py-3 font-semibold text-gs1-blue-dark">
                      <span className="inline-flex items-center gap-2">
                        <CalendarRange className="size-4 text-gs1-gray-mid" /> {formatWindow(d)}
                      </span>
                      {d.is_sample && <span className="ml-2 rounded bg-gs1-peach/40 px-1.5 py-0.5 text-[10px] font-bold uppercase text-gs1-blue-dark">sample</span>}
                    </td>
                    <td className="hidden max-w-lg truncate px-4 py-3 text-gs1-gray-dark md:table-cell">{d.headline || (d.status === 'failed' ? 'Run failed – see /api/runs' : '—')}</td>
                    <td className="px-4 py-3 text-center font-bold tabular-nums text-gs1-blue">{d.item_count}</td>
                    {SECTOR_ORDER.map((s) => {
                      const c = d.sector_counts.find((x) => x.sector === s)
                      return (
                        <td key={s} className="hidden px-3 py-3 text-center tabular-nums text-gs1-gray-dark lg:table-cell">
                          {c?.total ?? 0}
                          {c?.high ? <span className="ml-1 text-xs font-bold text-gs1-orange">({c.high}↑)</span> : null}
                        </td>
                      )
                    })}
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-md px-2 py-0.5 text-[11px] font-bold uppercase ${
                          d.status === 'completed' ? 'bg-gs1-mint/20 text-gs1-forest' : d.status === 'failed' ? 'bg-red-50 text-gs1-danger' : 'bg-gs1-peach/30 text-gs1-blue-dark'
                        }`}
                      >
                        {d.status}
                      </span>
                      <div className="mt-0.5 text-[11px] text-gs1-gray-mid">
                        {d.trigger} · {formatDate(d.completed_at ?? d.created_at, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
