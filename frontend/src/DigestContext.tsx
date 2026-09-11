import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, ApiError, type Digest, type DigestSummary, type Id, type Status } from './api'

interface DigestState {
  status: Status | null
  digests: DigestSummary[]
  digest: Digest | null
  loading: boolean
  error: string | null
  selectDigest: (id: Id) => void
  refresh: () => Promise<void>
}

const Ctx = createContext<DigestState | null>(null)

export function DigestProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status | null>(null)
  const [digests, setDigests] = useState<DigestSummary[]>([])
  const [digest, setDigest] = useState<Digest | null>(null)
  const [selectedId, setSelectedId] = useState<Id | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [st, list] = await Promise.all([api.status(), api.digests()])
      setStatus(st)
      setDigests(list)
      const wanted = selectedId ?? st.latest_digest_id
      if (wanted) {
        setDigest(await api.digest(wanted))
      } else {
        setDigest(null)
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Unable to reach the Regulatory Radar API')
    } finally {
      setLoading(false)
    }
  }, [selectedId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  // Poll while a run is in progress so the UI updates when the digest lands.
  useEffect(() => {
    if (!status?.running) return
    const t = setInterval(() => void refresh(), 15000)
    return () => clearInterval(t)
  }, [status?.running, refresh])

  const value = useMemo<DigestState>(
    () => ({ status, digests, digest, loading, error, selectDigest: setSelectedId, refresh }),
    [status, digests, digest, loading, error, refresh],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useDigest(): DigestState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useDigest must be used inside DigestProvider')
  return v
}
