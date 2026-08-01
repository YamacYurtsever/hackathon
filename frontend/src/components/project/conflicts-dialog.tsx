import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { themedDialogClass } from '@/lib/themed-dialog'
import type { UiTheme } from '@/lib/ui-theme'
import type { Conflict, IREntry, Member } from '@/types/ir'

function statementOf(entry: IREntry): string {
  const statement = entry.content.statement
  return typeof statement === 'string'
    ? statement
    : JSON.stringify(entry.content)
}

function timeOf(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** One side of a contradiction: who said it, when, and what it says — with the
 * two things an admin can do about this half of it. */
function Side({
  entry,
  author,
  canAct,
  busy,
  onEditingChange,
  onEdit,
  onDiscard,
}: {
  entry: IREntry
  author?: Member
  canAct: boolean
  busy: boolean
  onEditingChange: (editing: boolean) => void
  onEdit: (statement: string) => void
  onDiscard: () => void
}) {
  const [draft, setDraft] = useState<string | null>(null)
  const editing = draft !== null

  function edit(next: string | null) {
    setDraft(next)
    onEditingChange(next !== null)
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="text-muted-foreground flex items-baseline gap-2 text-xs">
        <span className="text-foreground/70 font-medium">
          {author?.username ?? 'unknown'}
        </span>
        <span className="tabular-nums">{timeOf(entry.created_at)}</span>
      </div>

      {editing ? (
        <Textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={2}
          className="focus-visible:border-brand focus-visible:ring-brand/25 resize-none"
        />
      ) : (
        <p className="text-sm">{statementOf(entry)}</p>
      )}

      {canAct && (
        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <Button
                size="xs"
                variant="brand"
                disabled={busy || !draft.trim()}
                onClick={() => onEdit(draft.trim())}
              >
                Save
              </Button>
              <Button size="xs" variant="ghost" onClick={() => edit(null)}>
                Cancel
              </Button>
            </>
          ) : (
            <>
              <Button
                size="xs"
                variant="outline"
                disabled={busy}
                onClick={() => edit(statementOf(entry))}
              >
                Edit
              </Button>
              <Button
                size="xs"
                variant="outline"
                disabled={busy}
                onClick={onDiscard}
              >
                Discard
              </Button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

/** The record contradicting itself, and what to do about it.
 *
 * Same shape as the pending queue, because it's the same kind of thing — a
 * header button that opens what's waiting on a person. Red rather than amber
 * because it's worse: pending means the record is incomplete, a conflict means
 * it currently can't all be true, and every summary drawn from it is built on
 * both halves. */
export function ConflictsDialog({
  conflicts,
  entriesById,
  members,
  isAdmin,
  busy,
  theme = 'classic',
  onEdit,
  onDiscard,
  onDismiss,
}: {
  conflicts: Conflict[]
  entriesById: Map<string, IREntry>
  members: Member[]
  isAdmin: boolean
  busy: boolean
  theme?: UiTheme
  onEdit: (conflictId: string, entryId: string, statement: string) => void
  onDiscard: (conflictId: string, entryId: string) => void
  onDismiss: (conflictId: string) => void
}) {
  // Which conflict, if any, has a side open for editing. While one does, the
  // Cancel next to it is the way out and a second one would just be noise.
  const [editingIn, setEditingIn] = useState<string | null>(null)

  if (conflicts.length === 0) return null

  const byId = new Map(members.map((member) => [member.id, member]))

  return (
    <Dialog>
      <DialogTrigger
        render={
          <Button variant="alarm">
            <span className="bg-destructive size-1.5 rounded-full" />
            {conflicts.length}{' '}
            {conflicts.length === 1 ? 'conflict' : 'conflicts'}
          </Button>
        }
      />
      <DialogContent
        className={themedDialogClass(
          theme,
          'max-h-[85svh] overflow-y-auto sm:max-w-2xl',
        )}
      >
        <DialogHeader>
          <DialogTitle>
            {conflicts.length}{' '}
            {conflicts.length === 1 ? 'conflict' : 'conflicts'}
          </DialogTitle>
          <DialogDescription>
            {isAdmin
              ? "These can't both be true, and the record says both. Fix one side, drop one, or say they don't actually conflict."
              : "These can't both be true, and the record says both. An admin has to settle it."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          {conflicts.map((conflict) => {
            const [first, second] = conflict.entry_ids.map((id) =>
              entriesById.get(id),
            )
            // An entry can go while the dialog is open — discarding one side is
            // exactly what this offers.
            if (!first || !second) return null

            return (
              <div
                key={conflict.id}
                className="border-destructive/30 bg-destructive/[0.03] flex flex-col gap-3 rounded-lg border p-3"
              >
                <p className="text-destructive text-xs font-medium">
                  {conflict.reason}
                </p>

                <Side
                  entry={first}
                  author={byId.get(first.author)}
                  canAct={isAdmin}
                  busy={busy}
                  onEditingChange={(editing) =>
                    setEditingIn(editing ? conflict.id : null)
                  }
                  onEdit={(statement) =>
                    onEdit(conflict.id, first.id, statement)
                  }
                  onDiscard={() => onDiscard(conflict.id, first.id)}
                />

                <div className="text-muted-foreground flex items-center gap-2 text-[0.65rem] tracking-wide uppercase">
                  <span className="bg-border h-px flex-1" />
                  conflicts with
                  <span className="bg-border h-px flex-1" />
                </div>

                <Side
                  entry={second}
                  author={byId.get(second.author)}
                  canAct={isAdmin}
                  busy={busy}
                  onEditingChange={(editing) =>
                    setEditingIn(editing ? conflict.id : null)
                  }
                  onEdit={(statement) =>
                    onEdit(conflict.id, second.id, statement)
                  }
                  onDiscard={() => onDiscard(conflict.id, second.id)}
                />

                {isAdmin && editingIn !== conflict.id && (
                  <Button
                    size="xs"
                    variant="ghost"
                    className="self-end"
                    disabled={busy}
                    onClick={() => onDismiss(conflict.id)}
                  >
                    Not a conflict
                  </Button>
                )}
              </div>
            )
          })}
        </div>
      </DialogContent>
    </Dialog>
  )
}
