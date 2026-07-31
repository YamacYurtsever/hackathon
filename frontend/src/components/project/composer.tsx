import { useState } from 'react'
import { ArrowUpIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

/** One box for both saying and asking — a message can be either or both. */
export function Composer({
  busy,
  onSend,
}: {
  busy: boolean
  onSend: (text: string) => void
}) {
  const [text, setText] = useState('')

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || busy) return
    onSend(trimmed)
    setText('')
  }

  return (
    <form onSubmit={handleSubmit} className="relative">
      <Textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Say something, or ask…"
        rows={1}
        disabled={busy}
        // Enter sends, since most messages are a line. Shift+Enter (and the
        // usual Cmd/Ctrl+Enter) still break the line for the longer ones.
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) handleSubmit(event)
        }}
        // Starts one line tall, so the placeholder sits centred against the
        // send button, and grows with what you type (the base textarea already
        // sets field-sizing-content; min-h-16 is what was forcing four rows).
        className="max-h-40 min-h-0 resize-none overflow-y-auto py-2.5 pr-12"
      />
      <Button
        type="submit"
        size="icon-sm"
        disabled={busy || !text.trim()}
        className="absolute top-1/2 right-2 -translate-y-1/2"
        aria-label="Send"
      >
        <ArrowUpIcon />
      </Button>
    </form>
  )
}
