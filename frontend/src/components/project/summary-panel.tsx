import { Card, CardContent } from '@/components/ui/card'
import type { Segment } from '@/types/ir'

/** Segments concatenated into one flowing block, not one row per segment — the
 * seams shouldn't be visible to the reader. Shared by the summary and by an
 * answer, which are the same thing pointed at different questions. */
function Prose({
  segments,
  numbers,
  onCitationClick,
}: {
  segments: Segment[]
  numbers: Map<string, number>
  onCitationClick: (entryId: string) => void
}) {
  return (
    <p className="text-sm leading-7">
      {segments.map((segment, index) => (
        <span key={index}>
          {segment.text}
          {segment.source_entry_ids.map((entryId) => (
            <button
              key={entryId}
              type="button"
              onClick={() => onCitationClick(entryId)}
              title="Show the entry this came from"
              className="text-brand/70 hover:bg-brand/10 hover:text-brand ml-0.5 rounded px-0.5 align-super text-[0.65rem] font-medium transition-colors"
            >
              [{numbers.get(entryId)}]
            </button>
          ))}{' '}
        </span>
      ))}
    </p>
  )
}

export function SummaryPanel({
  segments,
  loading,
  numbers,
  answer,
  onCitationClick,
}: {
  segments: Segment[]
  loading: boolean
  numbers: Map<string, number>
  /** A reply to what you just asked. Transient — it isn't a fact, so it never
   * enters the feed or the IR — but it belongs in this panel rather than a
   * second box below it. It stands until the next message; the summary is what
   * the panel shows when you haven't asked anything, not a place to go back to. */
  answer?: { question: string; segments: Segment[]; pending?: boolean } | null
  onCitationClick: (entryId: string) => void
}) {
  if (answer) {
    return (
      <Card className="ring-border/70 min-h-0 flex-1 overflow-hidden py-0 shadow-[0_1px_2px_rgb(0_0_0/0.04),0_12px_32px_-16px_rgb(0_0_0/0.12)]">
        <CardContent className="flex h-full flex-col gap-4 overflow-y-auto p-6">
          <p className="border-brand/40 text-muted-foreground border-l-2 pl-3 text-sm italic">
            {answer.question}
          </p>
          {answer.pending ? (
            <span className="flex items-center gap-1.5 pl-3">
              <span className="bg-brand size-1.5 animate-bounce rounded-full [animation-delay:-0.3s]" />
              <span className="bg-brand size-1.5 animate-bounce rounded-full [animation-delay:-0.15s]" />
              <span className="bg-brand size-1.5 animate-bounce rounded-full" />
            </span>
          ) : (
            <Prose
              segments={answer.segments}
              numbers={numbers}
              onCitationClick={onCitationClick}
            />
          )}
        </CardContent>
      </Card>
    )
  }

  if (loading) {
    return (
      <Card className="ring-border/70 min-h-0 flex-1 py-0 shadow-[0_1px_2px_rgb(0_0_0/0.04),0_12px_32px_-16px_rgb(0_0_0/0.12)]">
        <CardContent className="text-muted-foreground p-6 text-center text-sm">
          Reading the project for you…
        </CardContent>
      </Card>
    )
  }

  if (segments.length === 0) {
    return (
      <Card className="ring-border/70 min-h-0 flex-1 py-0 shadow-[0_1px_2px_rgb(0_0_0/0.04),0_12px_32px_-16px_rgb(0_0_0/0.12)]">
        <CardContent className="text-muted-foreground p-6 text-center text-sm">
          Nothing here concerns you yet.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="ring-border/70 min-h-0 flex-1 overflow-hidden py-0 shadow-[0_1px_2px_rgb(0_0_0/0.04),0_12px_32px_-16px_rgb(0_0_0/0.12)]">
      {/* Long summaries scroll here rather than pushing the composer off-screen. */}
      <CardContent className="h-full overflow-y-auto p-6">
        <Prose
          segments={segments}
          numbers={numbers}
          onCitationClick={onCitationClick}
        />
      </CardContent>
    </Card>
  )
}
