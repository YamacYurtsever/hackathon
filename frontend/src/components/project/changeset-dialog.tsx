import { useState } from 'react'

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
import type { IREntry, Operation } from '@/types/ir'

/** Gate 1, as a popup: proposed changes are a decision to make, not something
 * to read past. Each is kept, edited, or dropped on its own — one message often
 * says several things and you shouldn't have to take them as a bundle. */
export function ChangesetDialog({
  operations,
  dropped,
  entriesById,
  busy,
  onAccept,
  onDiscard,
}: {
  operations: Operation[]
  dropped: number
  entriesById: Map<string, IREntry>
  busy: boolean
  onAccept: (operations: Operation[]) => void
  onDiscard: () => void
}) {
  const [edited, setEdited] = useState(operations)
  const [keptIndexes, setKeptIndexes] = useState(() => operations.map((_, i) => i))

  const kept = edited.filter((_, index) => keptIndexes.includes(index))

  function toggle(index: number) {
    setKeptIndexes((current) =>
      current.includes(index)
        ? current.filter((i) => i !== index)
        : [...current, index],
    )
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onDiscard()}>
      <DialogContent className="max-h-[85svh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Here's what we understood</DialogTitle>
          <DialogDescription>
            Nothing is recorded yet. Keep the ones you meant, fix any we got
            wrong, then send them for approval.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          {edited.map((operation, index) => {
            const keeping = keptIndexes.includes(index)
            return (
              <div key={index} className={keeping ? '' : 'opacity-50'}>
                <OperationCard
                  operation={operation}
                  target={
                    operation.target_id
                      ? entriesById.get(operation.target_id)
                      : undefined
                  }
                  onChange={
                    keeping
                      ? (next) =>
                          setEdited((current) =>
                            current.map((op, i) => (i === index ? next : op)),
                          )
                      : undefined
                  }
                  actions={
                    <Button size="xs" variant="ghost" onClick={() => toggle(index)}>
                      {keeping ? 'Drop' : 'Keep'}
                    </Button>
                  }
                />
              </div>
            )
          })}

          {dropped > 0 && (
            <p className="text-muted-foreground text-xs">
              {dropped} proposed {dropped === 1 ? 'change' : 'changes'} couldn't be
              read and {dropped === 1 ? 'was' : 'were'} discarded.
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onDiscard} disabled={busy}>
            Discard
          </Button>
          <Button onClick={() => onAccept(kept)} disabled={busy || !kept.length}>
            {busy ? 'Sending…' : `Send ${kept.length} for approval`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
