import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import type { Segment } from '@/types/ir'

/** An answer is transient: it isn't a fact, so it never enters the feed. */
export function AnswerCard({
  question,
  segments,
  busy,
  onDismiss,
  onTreatAsStatement,
}: {
  question: string
  segments: Segment[]
  busy: boolean
  onDismiss: () => void
  onTreatAsStatement: () => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Answer</CardTitle>
        <CardDescription>“{question}”</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {segments.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            Nothing in the project answers that yet.
          </p>
        ) : (
          <p className="text-sm leading-relaxed">
            {segments.map((segment, index) => (
              <span key={index}>
                {segment.text}{' '}
                <span
                  className="text-muted-foreground text-xs"
                  title={segment.source_entry_ids.join(', ')}
                >
                  [{index + 1}]
                </span>{' '}
              </span>
            ))}
          </p>
        )}

        <div className="flex gap-2">
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            Dismiss
          </Button>
          {/* The classifier can be wrong in either direction, so both are one click away. */}
          <Button
            size="sm"
            variant="outline"
            onClick={onTreatAsStatement}
            disabled={busy}
          >
            That was a statement
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
