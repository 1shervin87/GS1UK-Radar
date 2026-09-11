export type SectorId = 'retail' | 'construction' | 'healthcare'
export type Impact = 'high' | 'medium' | 'low'

export interface SectorInfo {
  id: SectorId
  name: string
  colour: string
  description: string
}

export interface KeyDate {
  date: string
  label: string
}

export interface Link {
  url: string
  label: string
  kind: 'primary' | 'official' | 'guidance' | 'gs1' | 'news' | 'other'
}

export interface NextStep {
  audience: 'gs1_uk' | 'members' | 'both'
  action: string
  priority: 'now' | 'next_quarter' | 'monitor'
}

/** Numeric in API mode; "<digestId>__<n>" strings in static mode. Always compare with String(). */
export type Id = number | string

export interface ItemSummary {
  id: Id
  digest_id: Id
  title: string
  issuing_body: string
  publisher: string
  published_at: string | null
  change_type: string
  sectors: SectorId[]
  primary_sector: SectorId
  impact: Impact
  relevance_score: number
  summary: string
  gs1_standards_implicated: string[]
  key_dates: KeyDate[]
}

export interface Item extends ItemSummary {
  url: string
  jurisdiction: string
  what_changed: string
  why_it_matters_to_gs1: string
  affected_stakeholders: string[]
  next_steps: NextStep[]
  links: Link[]
  confidence: 'high' | 'medium' | 'low'
  source_connector: string
}

export interface SectorCount {
  sector: SectorId
  total: number
  high: number
}

export interface SectorOverview {
  sector: SectorId
  headline: string
  summary: string
  top_priorities: string[]
  watchlist: string[]
}

export interface DigestSummary {
  id: Id
  window_start: string
  window_end: string
  created_at: string
  completed_at: string | null
  status: 'running' | 'completed' | 'failed'
  trigger: string
  headline: string
  is_sample: boolean
  item_count: number
  sector_counts: SectorCount[]
}

export interface Digest extends DigestSummary {
  executive_summary: string
  cross_sector_themes: string[]
  sector_overviews: SectorOverview[]
  stats: Record<string, number | string>
  error: string | null
  items: ItemSummary[]
}

export interface Status {
  app: string
  environment: string
  llm_provider: string
  llm_configured: boolean
  web_search_provider: string
  schedule: string
  timezone: string
  next_run: string | null
  running: boolean
  latest_digest_id: Id | null
  sectors: SectorInfo[]
  data_mode?: 'api' | 'static'
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Accept: 'application/json' } })
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const DATA_MODE: 'api' | 'static' = import.meta.env.VITE_DATA_MODE === 'static' ? 'static' : 'api'

interface RadarApi {
  status: () => Promise<Status>
  digests: () => Promise<DigestSummary[]>
  latestDigest: () => Promise<Digest>
  digest: (id: Id) => Promise<Digest>
  item: (id: Id) => Promise<Item>
  search: (q: string, sector?: SectorId) => Promise<ItemSummary[]>
  runNow: (token: string, lookbackDays?: number) => Promise<{ started: boolean; message: string }>
}

const restApi: RadarApi = {
  status: () => get<Status>('/api/status'),
  digests: () => get<DigestSummary[]>('/api/digests'),
  latestDigest: () => get<Digest>('/api/digests/latest'),
  digest: (id) => get<Digest>(`/api/digests/${id}`),
  item: (id) => get<Item>(`/api/items/${id}`),
  search: (q, sector) => get<ItemSummary[]>(`/api/items?q=${encodeURIComponent(q)}${sector ? `&sector=${sector}` : ''}`),
  runNow: async (token, lookbackDays) => {
    const res = await fetch('/api/admin/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ lookback_days: lookbackDays ?? null }),
    })
    const body = await res.json().catch(() => ({}))
    if (!res.ok) throw new ApiError(res.status, body.detail ?? res.statusText)
    return body as { started: boolean; message: string }
  },
}

/* ---- Static mode: JSON files produced by the Cursor Automation ------------------
 *   <base>/data/index.json            { status, digests: DigestSummary[] }
 *   <base>/data/digests/<id>.json     Digest with full Item objects (id = "<digestId>__<n>")
 *   <base>/data/latest.json           copy of the latest digest
 * -------------------------------------------------------------------------------- */
interface StaticDigest extends Omit<Digest, 'items'> {
  items: Item[]
}
interface StaticIndex {
  status: Status
  digests: DigestSummary[]
}

const dataUrl = (p: string) => `${import.meta.env.BASE_URL.replace(/\/$/, '')}/data/${p}`
const digestCache = new Map<string, Promise<StaticDigest>>()
const loadDigest = (id: Id) => {
  const key = String(id)
  if (!digestCache.has(key)) digestCache.set(key, get<StaticDigest>(dataUrl(`digests/${key}.json`)))
  return digestCache.get(key)!
}
const matches = (i: Item, q: string) => {
  const needle = q.toLowerCase()
  return [i.title, i.summary, i.why_it_matters_to_gs1, i.what_changed, ...i.gs1_standards_implicated].some((t) => t?.toLowerCase().includes(needle))
}

const staticApi: RadarApi = {
  status: async () => ({ ...(await get<StaticIndex>(dataUrl('index.json'))).status, data_mode: 'static' }),
  digests: async () => (await get<StaticIndex>(dataUrl('index.json'))).digests,
  latestDigest: () => get<StaticDigest>(dataUrl('latest.json')),
  digest: loadDigest,
  item: async (id) => {
    const [digestId] = String(id).split('__')
    const d = await loadDigest(digestId)
    const item = d.items.find((i) => String(i.id) === String(id))
    if (!item) throw new ApiError(404, 'Item not found')
    return item
  },
  search: async (q, sector) => {
    const index = await get<StaticIndex>(dataUrl('index.json'))
    const digests = await Promise.all(index.digests.filter((d) => d.status === 'completed').map((d) => loadDigest(d.id)))
    return digests
      .flatMap((d) => d.items)
      .filter((i) => matches(i, q) && (!sector || i.sectors.includes(sector) || i.primary_sector === sector))
      .slice(0, 50)
  },
  runNow: async () => {
    throw new ApiError(400, 'This site is updated by the scheduled Cursor Automation; there is no server to run on demand.')
  },
}

export const api: RadarApi = DATA_MODE === 'static' ? staticApi : restApi

export const SECTOR_META: Record<SectorId, { name: string; colour: string; twBg: string; twText: string; twBorder: string; blurb: string }> = {
  retail: {
    name: 'Retail',
    colour: '#F05587',
    twBg: 'bg-gs1-raspberry',
    twText: 'text-gs1-raspberry',
    twBorder: 'border-gs1-raspberry',
    blurb: 'Grocery, FMCG, general merchandise, marketplaces, DRS, packaging EPR, labelling and product safety.',
  },
  construction: {
    name: 'Construction',
    colour: '#B78B20',
    twBg: 'bg-gs1-honey',
    twText: 'text-gs1-honey',
    twBorder: 'border-gs1-honey',
    blurb: 'Construction products regulation, Building Safety Act golden thread, digital product records and passports.',
  },
  healthcare: {
    name: 'Healthcare',
    colour: '#00B6DE',
    twBg: 'bg-gs1-sky',
    twText: 'text-gs1-sky',
    twBorder: 'border-gs1-sky',
    blurb: 'MHRA device and medicines regulation, UDI, NHS Scan4Safety, MDOR and NHS procurement standards.',
  },
}

export const SECTOR_ORDER: SectorId[] = ['retail', 'construction', 'healthcare']

export function formatDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' }): string {
  if (!iso) return 'Date unknown'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-GB', opts)
}

export function formatWindow(d: DigestSummary): string {
  return `${formatDate(d.window_start, { day: 'numeric', month: 'short' })} – ${formatDate(d.window_end)}`
}

export const CHANGE_TYPE_LABEL: Record<string, string> = {
  legislation: 'Legislation',
  draft_legislation: 'Draft legislation',
  consultation: 'Consultation',
  guidance: 'Guidance',
  policy: 'Policy',
  enforcement: 'Enforcement',
  standard: 'Standard',
  industry_scheme: 'Industry scheme',
  eu_international: 'EU / international',
  nhs_programme: 'NHS programme',
  other: 'Update',
}
