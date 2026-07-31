import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import type { IREntry, Member } from '@/types/ir'

function statementOf(entry: IREntry): string {
  const statement = entry.content.statement
  return typeof statement === 'string' ? statement : JSON.stringify(entry.content)
}

/** What landed while you were away. Absent entirely when nothing changed. */
export function Digest({
  entries,
  members,
  onDismiss,
}: {
  entries: IREntry[]
  members: Member[]
  onDismiss: () => void
}) {
  if (entries.length === 0) return null

  const byId = new Map(members.map((member) => [member.id, member]))

  return (
    <Card className="border-primary/40">
      <CardContent className="flex flex-col gap-3 py-4">
        <div className="flex items-center justify-between gap-4">
          <span className="text-sm font-medium">
            {entries.length} {entries.length === 1 ? 'change' : 'changes'} since you
            last looked
          </span>
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            Got it
          </Button>
        </div>

        <ul className="flex flex-col gap-1">
          {entries.map((entry) => (
            <li key={entry.id} className="text-muted-foreground text-sm">
              <span className="font-medium">
                {byId.get(entry.author)?.username ?? 'someone'}
              </span>{' '}
              — {statementOf(entry)}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
