import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { statementOf } from '@/lib/ir'
import type { IREntry, Operation } from '@/types/ir'

/** One proposed change, reviewed on its own. NL reads it as a sentence; IR is
 * the editable raw content — the escape hatch when the model got it wrong. */
export function OperationCard({
  operation,
  target,
  onChange,
  actions,
}: {
  operation: Operation
  /** The entry an update revises, so the diff has something to strike through. */
  target?: IREntry
  onChange?: (operation: Operation) => void
  actions?: React.ReactNode
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [parseError, setParseError] = useState('')

  function startEditing() {
    setDraft(JSON.stringify(operation, null, 2))
    setParseError('')
    setEditing(true)
  }

  function handleDraftChange(next: string) {
    setDraft(next)
    try {
      const parsed = JSON.parse(next)
      setParseError('')
      onChange?.(parsed)
    } catch (err) {
      // Keep the text as typed — clobbering it mid-edit would be maddening.
      setParseError(err instanceof Error ? err.message : 'Invalid JSON')
    }
  }

  return (
    <div className="bg-card flex flex-col gap-2 rounded-lg border p-3">
      {/* Adding and revising are different decisions, so they don't look alike:
          a revision replaces something already agreed. */}
      <span
        className={`w-fit rounded px-1.5 py-0.5 text-[0.65rem] font-medium tracking-wide uppercase ring-1 ${
          operation.op === 'update'
            ? 'bg-attention-subtle text-attention ring-attention/20'
            : 'bg-brand/10 text-brand ring-brand/20'
        }`}
      >
        {operation.op === 'update' ? 'revises a fact' : 'new fact'}
      </span>

      {editing ? (
        <div className="flex flex-col gap-2">
          <Textarea
            value={draft}
            onChange={(event) => handleDraftChange(event.target.value)}
            rows={10}
            className="font-mono text-xs"
          />
          {parseError && <p className="text-destructive text-xs">{parseError}</p>}
        </div>
      ) : (
        <div className="flex flex-col gap-1 text-sm">
          {operation.op === 'update' && target && (
            <span className="text-muted-foreground line-through">
              {statementOf(target.content)}
            </span>
          )}
          <span>{statementOf(operation.content)}</span>
        </div>
      )}

      <div className="flex items-center gap-2">
        {onChange && (
          <Button
            size="xs"
            variant="ghost"
            onClick={() => (editing ? setEditing(false) : startEditing())}
          >
            {editing ? 'Done' : 'Edit'}
          </Button>
        )}
        {actions}
      </div>
    </div>
  )
}
