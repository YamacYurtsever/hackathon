import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { AppLayout } from '@/components/app-layout'
import { ChangesetDialog } from '@/components/project/changeset-dialog'
import { Composer } from '@/components/project/composer'
import { ConflictsDialog } from '@/components/project/conflicts-dialog'
import { Digest } from '@/components/project/digest'
import { DocumentDrop } from '@/components/project/document-drop'
import { DocumentReading, DocumentReview } from '@/components/project/document-review'
import { EmptyProject } from '@/components/project/empty-project'
import { Feed } from '@/components/project/feed'
import { MembersPopover } from '@/components/project/members-popover'
import { PendingRequests } from '@/components/project/pending-requests'
import { SummaryPanel } from '@/components/project/summary-panel'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { citationNumbers } from '@/lib/citations'
import { refusalFor } from '@/lib/documents'
import { useAuth } from '@/lib/auth-context'
import { readUiTheme, writeUiTheme, type UiTheme } from '@/lib/ui-theme'
import type {
  ChangeRequest,
  Conflict,
  DocumentResult,
  IREntry,
  InputResult,
  Member,
  Operation,
  Project,
  Segment,
} from '@/types/ir'

type Mode = 'nl' | 'ir'

const modeKey = (id: string) => `ct:mode:${id}`
const lastViewedKey = (id: string) => `ct:lastViewed:${id}`

/** Anything unrecognised falls back to NL — including the "summary" this mode
 * used to be called, which is still sitting in people's localStorage. */
function storedMode(projectId: string | undefined): Mode {
  const stored = projectId && localStorage.getItem(modeKey(projectId))
  return stored === 'ir' ? 'ir' : 'nl'
}

export function ProjectPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { profile } = useAuth()
  const [theme, setTheme] = useState<UiTheme>(() => readUiTheme())

  const [project, setProject] = useState<Project | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [entries, setEntries] = useState<IREntry[]>([])
  const [requests, setRequests] = useState<ChangeRequest[]>([])
  const [conflicts, setConflicts] = useState<Conflict[]>([])
  const [digest, setDigest] = useState<IREntry[]>([])
  // Split on purpose: an answer is something to read, a proposal is a decision
  // to make, so they get different weight in the UI.
  const [answer, setAnswer] = useState<{
    question: string
    segments: Segment[]
    pending?: boolean
  } | null>(null)
  const [proposal, setProposal] = useState<InputResult | null>(null)
  // A dropped file, before and after it's been read. Kept apart from `proposal`
  // because the two are reviewed differently — a message is two proposals you
  // read individually, a spec is forty you scan.
  const [reading, setReading] = useState<string | null>(null)
  const [documentRead, setDocumentRead] = useState<DocumentResult | null>(null)

  const [segments, setSegments] = useState<Segment[]>([])
  const [welcome, setWelcome] = useState('')
  const [summaryLoading, setSummaryLoading] = useState(false)
  // Restored from the last visit, so navigating around mid-demo doesn't keep
  // resetting you to the other mode.
  const [mode, setMode] = useState<Mode>(() => storedMode(projectId))
  const [highlightId, setHighlightId] = useState<string | undefined>()

  // Entries this viewer merged themselves. "Since you last looked" means
  // changes you haven't seen — and you have very much seen the ones you just
  // approved. Tracked by id rather than bumping the last-viewed clock, so
  // merging one thing doesn't quietly bury everything else you hadn't read.
  const [mergedHere, setMergedHere] = useState<Set<string>>(new Set())

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
      api.listConflicts(projectId),
    ])
      .then(([loadedProject, loadedMembers, loadedEntries, loadedRequests, since_, found]) => {
        if (cancelled) return
        setProject(loadedProject)
        setMembers(loadedMembers)
        setEntries(loadedEntries)
        setRequests(loadedRequests)
        setDigest(since_)
        setConflicts(found)
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
  // call, so loading it for someone reading the IR would be waste. On an empty
  // project the same endpoint returns the welcome instead of segments.
  useEffect(() => {
    if (!projectId || mode !== 'nl') return
    let cancelled = false

    const load = async () => {
      setSummaryLoading(true)
      try {
        const view = await api.getView(projectId)
        if (!cancelled) {
          setSegments(view.segments)
          setWelcome(view.welcome ?? '')
        }
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
  // Whatever the panel is currently showing is what IR should be the evidence
  // for — an answer's sources while one stands, the summary's otherwise.
  const citations = citationNumbers(answer ? answer.segments : segments)

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

  function noteMerged(ids: string[]) {
    if (!ids.length) return
    setMergedHere((seen) => new Set([...seen, ...ids]))
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

    // We don't yet know whether this asked anything — that's the model's call —
    // so the panel shows the message thinking, and settles into an answer or
    // back into the summary once we do know.
    setAnswer({ question: text, segments: [], pending: true })
    switchMode('nl')

    const result = await run(() => api.sendInput(projectId, text))
    if (!result) {
      setAnswer(null)
      return
    }

    // A message can do both, so neither clears the other.
    setAnswer(
      result.answer
        ? { question: text, segments: result.answer_segments ?? [] }
        : null,
    )
    setProposal(result.operations.length || result.dropped ? result : null)
  }

  async function handleSubmit(operations: Operation[]) {
    if (!projectId || !proposal) return
    const done = await run(() =>
      api.submitChanges(projectId, proposal.text, operations),
    )
    if (done) {
      noteMerged(done.merged)
      setProposal(null)
      refresh()
    }
  }

  /** A file takes the same path a sentence takes: read, propose, submit, merge.
   * One document per run, so a bad extraction from one can't contaminate review
   * of the other. */
  async function handleFiles(files: File[]) {
    if (!projectId || !files.length) return
    const [file] = files

    // Refused here rather than after the upload, so nobody watches a file they
    // were never going to be able to send.
    const refusal = refusalFor(file)
    if (refusal) {
      setError(refusal)
      return
    }
    setError(
      files.length > 1
        ? `Reading ${file.name} only — one document at a time.`
        : '',
    )

    setReading(file.name)
    try {
      setDocumentRead(await api.uploadDocument(projectId, file))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not read that document')
    } finally {
      setReading(null)
    }
  }

  async function handleSubmitDocument(operations: Operation[]) {
    if (!projectId || !documentRead) return
    // Each operation carries its own provenance, so the server gives each
    // request a source line naming the document and where in it the fact was.
    const done = await run(() =>
      api.submitChanges(projectId, documentRead.document, operations),
    )
    if (done) {
      setDocumentRead(null)
      refresh()
    }
  }

  /** Merge the whole queue, which is what bootstrapping a project looks like.
   * One bad request doesn't stop the rest — the same reason a request carries a
   * single change is the reason a failure here shouldn't be all-or-nothing. */
  async function handleMergeAll() {
    if (!projectId) return
    setError('')
    setBusy(true)

    let failed = 0
    const landed: string[] = []
    for (const pending of requests) {
      try {
        landed.push((await api.mergeRequest(projectId, pending.id)).merged)
      } catch {
        failed += 1
      }
    }
    noteMerged(landed)

    setBusy(false)
    if (failed > 0)
      setError(
        `${failed} of ${requests.length} couldn't be merged — they're still in the queue.`,
      )
    refresh()
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

  function toggleTheme() {
    const next: UiTheme = theme === 'obsidian' ? 'classic' : 'obsidian'
    writeUiTheme(next)
    setTheme(next)
  }

  if (loading) {
    return (
      <AppLayout theme={theme} onToggleTheme={toggleTheme}>
        <p className="text-muted-foreground">Loading…</p>
      </AppLayout>
    )
  }

  if (project === null) {
    return (
      <AppLayout theme={theme} onToggleTheme={toggleTheme}>
        <p className="text-destructive">{error || 'Project not found'}</p>
      </AppLayout>
    )
  }

  return (
    <AppLayout fill theme={theme} onToggleTheme={toggleTheme}>
      {/* The whole view is the drop target — there's no import screen, because
          a document is a longer message and enters where a message enters. */}
      <DocumentDrop disabled={busy || reading !== null} onDrop={handleFiles}>
      {/* Header and composer stay put; everything between them scrolls. */}
      <div className="flex h-full flex-col gap-4">
        <div className="flex shrink-0 items-start justify-between gap-4">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight">{project.name}</h1>
            <p className="text-muted-foreground text-sm">
              {entries.length} {entries.length === 1 ? 'entry' : 'entries'}
            </p>
          </div>
          <div className="flex gap-2">
            <Digest
              entries={digest.filter((entry) => !mergedHere.has(entry.id))}
              members={members}
              onDismiss={dismissDigest}
            />
            <ConflictsDialog
              conflicts={conflicts}
              entriesById={entriesById}
              members={members}
              isAdmin={viewerIsAdmin}
              busy={busy}
              theme={theme}
              onEdit={(conflictId, entryId, statement) =>
                projectId &&
                run(() =>
                  api.editConflictingEntry(projectId, conflictId, entryId, {
                    ...(entriesById.get(entryId)?.content ?? {}),
                    statement,
                  }),
                ).then(refresh)
              }
              onDiscard={(conflictId, entryId) =>
                projectId &&
                run(() =>
                  api.discardConflictingEntry(projectId, conflictId, entryId),
                ).then(refresh)
              }
              onDismiss={(conflictId) =>
                projectId &&
                run(() => api.dismissConflict(projectId, conflictId)).then(refresh)
              }
            />
            <PendingRequests
              requests={requests}
              members={members}
              entriesById={entriesById}
              currentUserId={profile?.id ?? ''}
              isAdmin={viewerIsAdmin}
              busy={busy}
              onMerge={(id) =>
                projectId &&
                run(() => api.mergeRequest(projectId, id)).then((result) => {
                  if (result) noteMerged([result.merged])
                  refresh()
                })
              }
              onMergeAll={handleMergeAll}
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
              theme={theme}
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
                run(() => api.exitProject(projectId)).then(() => navigate('/home'))
              }
            >
              Leave
            </Button>
          </div>
        </div>

        {error && <p className="text-destructive shrink-0 text-sm">{error}</p>}

        {/* One toggle, two modes of the same panel — never both at once. The
            arrow between them is the point of the whole screen: prose on one
            side, the entries it was built from on the other. */}
        <div className="flex shrink-0 justify-center">
          <div className="bg-muted ring-border/60 relative flex items-center rounded-full p-1 ring-1">
            {/* One pill that slides, rather than two that light up — the
                movement is what makes the two sides read as one thing seen
                two ways. It changes colour as it travels, because the accent
                means "interpreted for you" and the record isn't. */}
            <span
              aria-hidden
              // Tailwind v4's translate-x-* sets the CSS `translate` property,
              // not `transform` — so transition-transform animates nothing.
              className={`absolute top-1 bottom-1 left-1 w-16 rounded-full shadow-sm transition-[translate,background-color] duration-200 ease-out motion-reduce:transition-none ${
                mode === 'ir'
                  ? 'bg-foreground translate-x-full'
                  : 'bg-brand shadow-brand/30 translate-x-0'
              }`}
            />
            <button
              type="button"
              onClick={() => switchMode('nl')}
              className={`relative w-16 rounded-full py-1 text-sm font-medium transition-colors ${
                mode === 'nl'
                  ? 'text-brand-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              NL
            </button>
            <button
              type="button"
              onClick={() => switchMode('ir')}
              className={`relative w-16 rounded-full py-1 text-sm font-medium transition-colors ${
                mode === 'ir'
                  ? 'text-background'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              IR
            </button>
          </div>
        </div>

        {mode === 'nl' ? (
          entries.length === 0 && !answer ? (
            <EmptyProject
              projectName={project.name}
              welcome={welcome}
              loading={summaryLoading}
            />
          ) : (
            <SummaryPanel
              segments={segments}
              loading={summaryLoading}
              numbers={citations}
              answer={answer}
              onCitationClick={showEvidenceFor}
            />
          )
        ) : (
          <Feed
            entries={entries}
            members={members}
            citations={citations}
            highlightId={highlightId}
          />
        )}

        <div className="shrink-0">
          <Composer
            busy={busy || reading !== null}
            onSend={handleSend}
            onAttach={(file) => handleFiles([file])}
          />
        </div>

        {proposal && (
          <ChangesetDialog
            key={proposal.text}
            operations={proposal.operations}
            dropped={proposal.dropped}
            entriesById={entriesById}
            busy={busy}
            viewerIsAdmin={viewerIsAdmin}
            onSubmit={handleSubmit}
            onDiscard={() => setProposal(null)}
          />
        )}

        {reading && <DocumentReading name={reading} theme={theme} />}

        {documentRead && (
          <DocumentReview
            key={documentRead.document}
            result={documentRead}
            entriesById={entriesById}
            busy={busy}
            viewerIsAdmin={viewerIsAdmin}
            theme={theme}
            onSubmit={handleSubmitDocument}
            onDiscard={() => setDocumentRead(null)}
          />
        )}
      </div>
      </DocumentDrop>
    </AppLayout>
  )
}
