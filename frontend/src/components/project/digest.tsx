import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import type { IREntry, Member } from '@/types/ir'

function statementOf(entry: IREntry): string {
  const statement = entry.content.statement
  return typeof statement === 'string' ? statement : JSON.stringify(entry.content)
}

/** What landed while you were away, behind a header button like the pending
 * queue — a banner pushed the panel down every time you opened the project,
 * for something you often only want to glance at. Absent when nothing changed. */
export function Digest({
  entries,
  members,
  onDismiss,
}: {
  entries: IREntry[]
  members: Member[]
  onDismiss: () => void
}) {
  const [open, setOpen] = useState(false)

  if (entries.length === 0) return null

  const byId = new Map(members.map((member) => [member.id, member]))

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button
            variant="outline"
            className="border-brand/30 bg-brand-subtle text-brand hover:bg-brand/15"
          >
            <span className="bg-brand size-1.5 animate-pulse rounded-full" />
            {entries.length} new
          </Button>
        }
      />
      <DialogContent className="max-h-[85svh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {entries.length} {entries.length === 1 ? 'change' : 'changes'} since you
            last looked
          </DialogTitle>
        </DialogHeader>

        <ul className="flex flex-col gap-2">
          {entries.map((entry) => (
            <li key={entry.id} className="text-muted-foreground text-sm">
              <span className="text-foreground font-medium">
                {byId.get(entry.author)?.username ?? 'someone'}
              </span>{' '}
              — {statementOf(entry)}
            </li>
          ))}
        </ul>

        <DialogFooter>
          <Button
            variant="brand"
            onClick={() => {
              setOpen(false)
              onDismiss()
            }}
          >
            Got it
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
