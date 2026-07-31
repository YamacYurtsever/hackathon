import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { AppLayout } from '@/components/app-layout'
import { AnswerCard } from '@/components/project/answer-card'
import { ChangesetDialog } from '@/components/project/changeset-dialog'
import { Composer } from '@/components/project/composer'
import { Digest } from '@/components/project/digest'
import { Feed } from '@/components/project/feed'
import { MembersPopover } from '@/components/project/members-popover'
import { PendingRequests } from '@/components/project/pending-requests'
import { SummaryPanel } from '@/components/project/summary-panel'
import { Button } from '@/components/ui/button'
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
  // Split on purpose: an answer is something to read, a proposal is a decision
  // to make, so they get different weight in the UI.
  const [answer, setAnswer] = useState<{ question: string; text: string } | null>(null)
  const [proposal, setProposal] = useState<InputResult | null>(null)

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

  async function handleSend(text: string) {
    if (!projectId) return
    const result = await run(() => api.sendInput(projectId, text))
    if (!result) return

    // A message can do both, so neither clears the other.
    setAnswer(result.answer ? { question: text, text: result.answer } : null)
    setProposal(result.operations.length || result.dropped ? result : null)
  }

  async function handleAccept(operations: Operation[]) {
    if (!projectId || !proposal) return
    const done = await run(() =>
      api.acceptChanges(projectId, proposal.text, operations),
    )
    if (done) {
      setProposal(null)
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
    <AppLayout fill>
      {/* Header and composer stay put; everything between them scrolls. */}
      <div className="flex h-full flex-col gap-4">
        <div className="flex shrink-0 items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">{project.name}</h1>
            <p className="text-muted-foreground text-sm">
              {entries.length} {entries.length === 1 ? 'entry' : 'entries'}
            </p>
          </div>
          <div className="flex gap-2">
            <PendingRequests
              requests={requests}
              members={members}
              entriesById={entriesById}
              currentUserId={profile?.id ?? ''}
              isAdmin={viewerIsAdmin}
              busy={busy}
              onApprove={(id) =>
                projectId &&
                run(() => api.approveRequest(projectId, id)).then(refresh)
              }
              onReject={(id) =>
                projectId &&
                run(() => api.rejectRequest(projectId, id)).then(refresh)
              }
              onEdit={(id, operation) =>
                projectId &&
                run(() => api.editRequest(projectId, id, operation)).then(refresh)
              }
            />
            <MembersPopover
              members={members}
              currentUserId={profile?.id ?? ''}
              viewerIsAdmin={viewerIsAdmin}
              busy={busy}
              onPromote={(userId) =>
                projectId &&
                run(() => api.promoteMember(projectId, userId)).then(refresh)
              }
            />
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

        {error && <p className="text-destructive shrink-0 text-sm">{error}</p>}

        {/* Capped so a long digest can't squeeze the panel out. */}
        {digest.length > 0 && (
          <div className="max-h-[35%] shrink-0 overflow-y-auto">
            <Digest entries={digest} members={members} onDismiss={dismissDigest} />
          </div>
        )}

        {/* One toggle, two modes of the same panel — never both at once. */}
        <div className="flex shrink-0 justify-end gap-1">
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

        {/* A reply to what you just asked, directly above the composer. */}
        {answer && (
          <div className="max-h-[40%] shrink-0 overflow-y-auto">
            <AnswerCard
              question={answer.question}
              answer={answer.text}
              onDismiss={() => setAnswer(null)}
            />
          </div>
        )}

        <div className="shrink-0">
          <Composer busy={busy} onSend={handleSend} />
        </div>

        {proposal && (
          <ChangesetDialog
            key={proposal.text}
            operations={proposal.operations}
            dropped={proposal.dropped}
            entriesById={entriesById}
            busy={busy}
            onAccept={handleAccept}
            onDiscard={() => setProposal(null)}
          />
        )}
      </div>
    </AppLayout>
  )
}
