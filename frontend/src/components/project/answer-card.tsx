import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

/** An answer is transient: it isn't a fact, so it never enters the feed or the
 * IR. It sits above the composer, as a reply to what you just asked. */
export function AnswerCard({
  question,
  answer,
  onDismiss,
}: {
  question: string
  answer: string
  onDismiss: () => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Answer</CardTitle>
        <CardDescription>“{question}”</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm leading-relaxed">{answer}</p>
        <Button size="sm" variant="ghost" className="self-start" onClick={onDismiss}>
          Dismiss
        </Button>
      </CardContent>
    </Card>
  )
}
