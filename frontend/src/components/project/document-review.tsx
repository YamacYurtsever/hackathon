import { useEffect, useState } from 'react'
import { LoaderCircleIcon } from 'lucide-react'

import { OperationCard } from '@/components/project/operation-card'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { UiTheme } from '@/lib/ui-theme'
import { themedDialogClass } from '@/lib/themed-dialog'
import type { DocumentResult, IREntry, Operation } from '@/types/ir'

/** A document is many model calls, and a silent minute reads as a hang.
 *
 * There's no honest percentage to show — the passage count isn't known until
 * the read comes back — so this shows the thing that is true: what it's
 * reading, and how long it's been at it. */
export function DocumentReading({
  name,
  theme = 'classic',
}: {
  name: string
  theme?: UiTheme
}) {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    const tick = setInterval(() => setSeconds((elapsed) => elapsed + 1), 1000)
    return () => clearInterval(tick)
  }, [])

  return (
    <Dialog open>
      <DialogContent className={themedDialogClass(theme, 'sm:max-w-md')}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <LoaderCircleIcon className="text-brand size-4 animate-spin" />
            Reading {name}
          </DialogTitle>
          <DialogDescription>
            It's cut into passages and read one at a time, so a long document
            takes a while — {seconds}s so far. Nothing is recorded until you've
            reviewed what we found.
          </DialogDescription>
        </DialogHeader>
      </DialogContent>
    </Dialog>
  )
}

/** One proposal from a document, in the same card a typed message's proposals
 * get: the fact, the old wording struck through if it revises one, and keep /
 * edit / drop on it individually.
 *
 * Under it, the sentence in the document that says so — so checking a fact
 * doesn't mean going back and re-reading the file. That's the passage, not a
 * position: where it sat in the document is the request's business at gate 2,
 * not something to sort a review by. */
function ProposalCard({
  operation,
  target,
  keeping,
  onToggle,
  onChange,
}: {
  operation: Operation
  target?: IREntry
  keeping: boolean
  onToggle: () => void
  onChange: (operation: Operation) => void
}) {
  const quote = operation.provenance?.quote

  return (
    <div className={keeping ? '' : 'opacity-50'}>
      <OperationCard
        operation={operation}
        target={target}
        onChange={keeping ? onChange : undefined}
        actions={
          <Button size="xs" variant="ghost" onClick={onToggle}>
            {keeping ? 'Drop' : 'Keep'}
          </Button>
        }
      />
      {quote && (
        <p className="border-brand/30 text-muted-foreground mt-1 ml-3 border-l-2 pl-2 text-xs italic">
          {quote}
        </p>
      )}
    </div>
  )
}

/** Gate 1 for a document. The same gate a typed message passes — this is our
 * reading of what the file says, and nothing is stored until it's submitted.
 *
 * One split, and only one: changes to facts already on record come first,
 * because those rewrite something the project already agreed to and you need
 * the old wording in front of you to judge them. Everything after is a new
 * fact. Both halves render identically. */
export function DocumentReview({
  result,
  entriesById,
  busy,
  viewerIsAdmin,
  theme = 'classic',
  onSubmit,
  onDiscard,
}: {
  result: DocumentResult
  entriesById: Map<string, IREntry>
  busy: boolean
  /** An admin's own changes are merged as soon as they confirm here, so this
   * dialog is their only gate rather than the first of two. */
  viewerIsAdmin: boolean
  theme?: UiTheme
  onSubmit: (operations: Operation[]) => void
  onDiscard: () => void
}) {
  const [edited, setEdited] = useState(result.operations)
  // Kept by default. A typed message is two proposals you read individually; a
  // document is forty you scan for the wrong ones, and defaulting them all to
  // dropped would just mean forty clicks before anything could happen.
  const [dropped, setDropped] = useState<Set<number>>(new Set())

  const kept = edited.filter((_, index) => !dropped.has(index))

  function toggle(index: number) {
    setDropped((current) => {
      const next = new Set(current)
      if (!next.delete(index)) next.add(index)
      return next
    })
  }

  function setAll(indexes: number[], keeping: boolean) {
    setDropped((current) => {
      const next = new Set(current)
      indexes.forEach((index) => (keeping ? next.delete(index) : next.add(index)))
      return next
    })
  }

  const indexes = edited.map((_, index) => index)
  const revisions = indexes.filter((index) => edited[index].op === 'update')
  const additions = indexes.filter((index) => edited[index].op !== 'update')

  const section = (heading: string, members: number[]) =>
    members.length > 0 && (
      <section className="mb-6">
        <div className="mb-2 flex items-baseline justify-between gap-2">
          <h3 className="text-sm font-medium">
            {heading} ({members.length})
          </h3>
          <div className="flex gap-1">
            <Button size="xs" variant="ghost" onClick={() => setAll(members, true)}>
              Keep all
            </Button>
            <Button size="xs" variant="ghost" onClick={() => setAll(members, false)}>
              Drop all
            </Button>
          </div>
        </div>
        <div className="flex flex-col gap-3">
          {members.map((index) => (
            <ProposalCard
              key={index}
              operation={edited[index]}
              target={
                edited[index].target_id
                  ? entriesById.get(edited[index].target_id!)
                  : undefined
              }
              keeping={!dropped.has(index)}
              onToggle={() => toggle(index)}
              onChange={(operation) =>
                setEdited((current) =>
                  current.map((op, i) => (i === index ? operation : op)),
                )
              }
            />
          ))}
        </div>
      </section>
    )

  return (
    <Dialog open onOpenChange={(open) => !open && onDiscard()}>
      <DialogContent
        className={themedDialogClass(
          theme,
          'flex max-h-[85svh] flex-col overflow-hidden sm:max-w-2xl',
        )}
      >
        <DialogHeader>
          <DialogTitle>
            {edited.length} {edited.length === 1 ? 'fact' : 'facts'} read from{' '}
            {result.document}
          </DialogTitle>
          <DialogDescription>
            This is what we understood, not what the document says — nothing is
            recorded yet. Drop anything we got wrong.{' '}
            {viewerIsAdmin
              ? "Confirming adds the rest to the project, since you're an admin."
              : 'The rest goes for review — an admin still has to merge them.'}
          </DialogDescription>
        </DialogHeader>

        <div className="-mx-1 flex-1 overflow-y-auto px-1">
          {section('Changes to facts already recorded', revisions)}
          {section('New facts', additions)}

          {edited.length === 0 && (
            <p className="text-muted-foreground py-6 text-center text-sm">
              We didn't find any facts in {result.document}.
            </p>
          )}

          {/* Never silently: a fact someone thinks they imported and didn't is
              the failure that matters here. */}
          {(result.dropped > 0 || result.failed_passages > 0) && (
            <p className="text-muted-foreground border-t pt-3 text-xs">
              {result.dropped > 0 &&
                `${result.dropped} proposed ${
                  result.dropped === 1 ? 'fact' : 'facts'
                } couldn't be read and ${
                  result.dropped === 1 ? 'was' : 'were'
                } discarded. `}
              {result.failed_passages > 0 &&
                `${result.failed_passages} of ${result.passages} passages couldn't be read at all, so this may not be everything in the document.`}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onDiscard} disabled={busy}>
            Discard
          </Button>
          <Button
            variant="brand"
            onClick={() => onSubmit(kept)}
            disabled={busy || !kept.length}
          >
            {busy
              ? 'Saving…'
              : viewerIsAdmin
                ? `Add ${kept.length} to the project`
                : `Submit ${kept.length} for review`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
