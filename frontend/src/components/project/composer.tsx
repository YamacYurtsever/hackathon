import { useRef, useState } from 'react'
import { ArrowUpIcon, PaperclipIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ACCEPT } from '@/lib/documents'

/** One box for both saying and asking — a message can be either or both.
 *
 * The paperclip sends a document down the same path: a file is a longer
 * message, so it enters where a message enters rather than through an import
 * screen of its own. Dragging one onto the project view does the same thing. */
export function Composer({
  busy,
  onSend,
  onAttach,
}: {
  busy: boolean
  onSend: (text: string) => void
  onAttach: (file: File) => void
}) {
  const [text, setText] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || busy) return
    onSend(trimmed)
    setText('')
  }

  return (
    <form onSubmit={handleSubmit} className="relative">
      <input
        ref={fileInput}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0]
          // Cleared either way, so picking the same file twice in a row still
          // fires a change event the second time.
          event.target.value = ''
          if (file) onAttach(file)
        }}
      />

      <Textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Say something, ask…, or drop in a document"
        rows={1}
        disabled={busy}
        // Enter sends, since most messages are a line. Shift+Enter (and the
        // usual Cmd/Ctrl+Enter) still break the line for the longer ones.
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) handleSubmit(event)
        }}
        // Starts one line tall, so the placeholder sits centred between the two
        // buttons, and grows with what you type (the base textarea already sets
        // field-sizing-content; min-h-16 is what was forcing four rows).
        className="max-h-40 min-h-0 resize-none overflow-y-auto py-2.5 pr-12 pl-11"
      />

      <Button
        type="button"
        size="icon-sm"
        variant="ghost"
        disabled={busy}
        onClick={() => fileInput.current?.click()}
        className="absolute top-1/2 left-2 -translate-y-1/2"
        aria-label="Attach a document"
      >
        <PaperclipIcon />
      </Button>

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
