import { useState } from 'react'

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
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <Textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Say something, or ask…"
        rows={3}
        disabled={busy}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
            handleSubmit(event)
          }
        }}
      />
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={busy || !text.trim()}>
          {busy ? 'Thinking…' : 'Send'}
        </Button>
        <span className="text-muted-foreground text-xs">
          A statement becomes a proposed fact; a question just gets answered.
        </span>
      </div>
    </form>
  )
}
