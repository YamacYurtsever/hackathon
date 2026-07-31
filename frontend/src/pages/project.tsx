import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { AppLayout } from '@/components/app-layout'
import { AnswerCard } from '@/components/project/answer-card'
import { ChangesetPreview } from '@/components/project/changeset-preview'
import { Composer } from '@/components/project/composer'
import { Digest } from '@/components/project/digest'
import { Feed } from '@/components/project/feed'
import { PendingRequests } from '@/components/project/pending-requests'
import { SummaryPanel } from '@/components/project/summary-panel'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { citationNumbers } from '@/lib/citations'
import { useAuth } from '@/lib/auth-context'
import type {
  ChangeRequest,
  IREntry,
  InputResult,
  Member,
  Operation,
  Project,
  Segment,
} from '@/types/ir'

type Mode = 'summary' | 'ir'

const modeKey = (id: string) => `ct:mode:${id}`
const lastViewedKey = (id: string) => `ct:lastViewed:${id}`

export function ProjectPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { profile } = useAuth()

  const [project, setProject] = useState<Project | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [entries, setEntries] = useState<IREntry[]>([])
  const [requests, setRequests] = useState<ChangeRequest[]>([])
  const [digest, setDigest] = useState<IREntry[]>([])
  const [pending, setPending] = useState<InputResult | null>(null)

  const [segments, setSegments] = useState<Segment[]>([])
  const [summaryLoading, setSummaryLoading] = useState(false)
  // Restored from the last visit, so navigating around mid-demo doesn't keep
  // resetting you to the other mode.
  const [mode, setMode] = useState<Mode>(
    () =>
      (projectId && (localStorage.getItem(modeKey(projectId)) as Mode)) || 'summary',
  )
  const [showAll, setShowAll] = useState(false)
  const [highlightId, setHighlightId] = useState<string | undefined>()

  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  // Bumped when applied changes make the summary stale.
  const [summaryKey, setSummaryKey] = useState(0)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false

    const since = localStorage.getItem(lastViewedKey(projectId))

    Promise.all([
      api.getProject(projectId),
      api.listMembers(projectId),
      api.getChanges(projectId),
      api.listRequests(projectId),
      since ? api.getChanges(projectId, since) : Promise.resolve([]),
    ])
      .then(([loadedProject, loadedMembers, loadedEntries, loadedRequests, since_]) => {
        if (cancelled) return
        setProject(loadedProject)
        setMembers(loadedMembers)
        setEntries(loadedEntries)
        setRequests(loadedRequests)
        setDigest(since_)
        // First visit: start the clock rather than claiming everything is new.
        if (!since) localStorage.setItem(lastViewedKey(projectId), new Date().toISOString())
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : 'Could not load project')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [projectId, reloadKey])

  // Only fetch the summary when it's actually on screen — it's a live model
  // call, so loading it for someone reading the IR would be waste.
  useEffect(() => {
    if (!projectId || mode !== 'summary') return
    let cancelled = false

    const load = async () => {
      setSummaryLoading(true)
      try {
        const view = await api.getView(projectId)
        if (!cancelled) setSegments(view.segments)
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : 'Could not load summary')
      } finally {
        if (!cancelled) setSummaryLoading(false)
      }
    }
    load()

    return () => {
      cancelled = true
    }
  }, [projectId, mode, summaryKey])

  const viewerIsAdmin = Boolean(profile && project?.admins.includes(profile.id))
  const entriesById = new Map(entries.map((entry) => [entry.id, entry]))
  const citations = citationNumbers(segments)

  const refresh = () => {
    setReloadKey((key) => key + 1)
    setSummaryKey((key) => key + 1)
  }

  function switchMode(next: Mode) {
    setMode(next)
    if (projectId) localStorage.setItem(modeKey(projectId), next)
  }

  function showEvidenceFor(entryId: string) {
    setHighlightId(entryId)
    switchMode('ir')
  }

  function dismissDigest() {
    setDigest([])
    if (projectId)
      localStorage.setItem(lastViewedKey(projectId), new Date().toISOString())
  }

  async function run<T>(work: () => Promise<T>): Promise<T | undefined> {
    setError('')
    setBusy(true)
    try {
      return await work()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  async function handleSend(text: string, kind?: 'changeset' | 'answer') {
    if (!projectId) return
    const result = await run(() => api.sendInput(projectId, text, kind))
    if (result) setPending(result)
  }

  async function handleConfirm(operations: Operation[]) {
    if (!projectId || pending?.kind !== 'changeset') return
    const done = await run(() =>
      api.confirmChangeset(projectId, pending.text, operations),
    )
    if (done) {
      setPending(null)
      refresh()
    }
  }

  async function handleCopyInvite() {
    const link = `${window.location.origin}/invite/${projectId}`
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError(`Copy this invite link: ${link}`)
    }
  }

  if (loading) {
    return (
      <AppLayout>
        <p className="text-muted-foreground">Loading…</p>
      </AppLayout>
    )
  }

  if (project === null) {
    return (
      <AppLayout>
        <p className="text-destructive">{error || 'Project not found'}</p>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">{project.name}</h1>
            <p className="text-muted-foreground text-sm">
              {entries.length} {entries.length === 1 ? 'entry' : 'entries'} ·{' '}
              {members.length} {members.length === 1 ? 'member' : 'members'}
            </p>
          </div>
          <div className="flex gap-2">
            {viewerIsAdmin && (
              <Button variant="outline" onClick={handleCopyInvite}>
                {copied ? 'Link copied' : 'Copy invite link'}
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() =>
                projectId &&
                run(() => api.exitProject(projectId)).then(() => navigate('/'))
              }
            >
              Leave
            </Button>
          </div>
        </div>

        {error && <p className="text-destructive text-sm">{error}</p>}

        <Digest entries={digest} members={members} onDismiss={dismissDigest} />

        <PendingRequests
          requests={requests}
          members={members}
          entriesById={entriesById}
          currentUserId={profile?.id ?? ''}
          isAdmin={viewerIsAdmin}
          busy={busy}
          onApprove={(id) =>
            projectId && run(() => api.approveRequest(projectId, id)).then(refresh)
          }
          onReject={(id) =>
            projectId && run(() => api.rejectRequest(projectId, id)).then(refresh)
          }
          onEdit={(id, operations) =>
            projectId &&
            run(() => api.editRequest(projectId, id, operations)).then(refresh)
          }
        />

        {/* One toggle, two modes of the same panel — never both at once. */}
        <div className="flex justify-end gap-1">
          <Button
            size="sm"
            variant={mode === 'summary' ? 'secondary' : 'ghost'}
            onClick={() => switchMode('summary')}
          >
            Summary
          </Button>
          <Button
            size="sm"
            variant={mode === 'ir' ? 'secondary' : 'ghost'}
            onClick={() => switchMode('ir')}
          >
            IR
          </Button>
        </div>

        {mode === 'summary' ? (
          <SummaryPanel
            segments={segments}
            loading={summaryLoading}
            numbers={citations}
            onCitationClick={showEvidenceFor}
          />
        ) : (
          <Feed
            entries={entries}
            members={members}
            citations={citations}
            highlightId={highlightId}
            showAll={showAll}
            onShowAllChange={setShowAll}
          />
        )}

        {pending?.kind === 'changeset' && (
          <ChangesetPreview
            operations={pending.operations}
            unresolved={pending.unresolved}
            entriesById={entriesById}
            busy={busy}
            onConfirm={handleConfirm}
            onDiscard={() => setPending(null)}
          />
        )}

        {pending?.kind === 'answer' && (
          <AnswerCard
            question={pending.text}
            segments={pending.segments}
            busy={busy}
            onDismiss={() => setPending(null)}
            onTreatAsStatement={() => handleSend(pending.text, 'changeset')}
          />
        )}

        <Composer busy={busy} onSend={handleSend} />

        <Card>
          <CardHeader>
            <CardTitle>Members</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between gap-4 border-b py-2 last:border-b-0"
              >
                <div className="flex items-center gap-2 text-sm">
                  <span>{member.username}</span>
                  {member.id === profile?.id && (
                    <span className="text-muted-foreground text-xs">(you)</span>
                  )}
                  {member.is_admin && (
                    <span className="bg-secondary text-secondary-foreground rounded px-1.5 py-0.5 text-xs">
                      admin
                    </span>
                  )}
                </div>
                {viewerIsAdmin && !member.is_admin && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() =>
                      projectId &&
                      run(() => api.promoteMember(projectId, member.id)).then(refresh)
                    }
                  >
                    Make admin
                  </Button>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
