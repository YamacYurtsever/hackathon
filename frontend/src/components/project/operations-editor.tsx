import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { IREntry, Operation } from '@/types/ir'

function statementOf(content: Record<string, unknown>): string {
  const statement = content.statement
  return typeof statement === 'string' ? statement : JSON.stringify(content)
}

/** Plain-language rendering: what each operation does, in a sentence. */
function NaturalLanguage({
  operations,
  entriesById,
}: {
  operations: Operation[]
  entriesById: Map<string, IREntry>
}) {
  return (
    <div className="flex flex-col gap-3">
      {operations.map((operation, index) => {
        const target = operation.target_id
          ? entriesById.get(operation.target_id)
          : undefined

        return (
          <div key={index} className="flex flex-col gap-1 text-sm">
            <span className="text-muted-foreground text-xs font-medium uppercase">
              {operation.op === 'update' ? 'revises an existing fact' : 'new fact'}
            </span>
            {/* An update is only meaningful against what it replaces. */}
            {operation.op === 'update' && target && (
              <span className="text-muted-foreground line-through">
                {statementOf(target.content)}
              </span>
            )}
            <span>{statementOf(operation.content)}</span>
          </div>
        )
      })}
    </div>
  )
}

export function OperationsEditor({
  operations,
  entriesById,
  onChange,
}: {
  operations: Operation[]
  entriesById: Map<string, IREntry>
  onChange: (operations: Operation[]) => void
}) {
  const [mode, setMode] = useState<'nl' | 'ir'>('nl')
  const [draft, setDraft] = useState('')
  const [parseError, setParseError] = useState('')

  function enterIrMode() {
    setDraft(JSON.stringify(operations, null, 2))
    setParseError('')
    setMode('ir')
  }

  function handleDraftChange(next: string) {
    setDraft(next)
    try {
      const parsed = JSON.parse(next)
      if (!Array.isArray(parsed)) throw new Error('Expected a list of operations')
      setParseError('')
      onChange(parsed)
    } catch (err) {
      // Keep the text as typed — clobbering it mid-edit would be maddening.
      setParseError(err instanceof Error ? err.message : 'Invalid JSON')
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-end gap-1">
        <Button
          size="sm"
          variant={mode === 'nl' ? 'secondary' : 'ghost'}
          onClick={() => setMode('nl')}
        >
          NL
        </Button>
        <Button
          size="sm"
          variant={mode === 'ir' ? 'secondary' : 'ghost'}
          onClick={enterIrMode}
        >
          IR
        </Button>
      </div>

      {mode === 'nl' ? (
        <NaturalLanguage operations={operations} entriesById={entriesById} />
      ) : (
        <div className="flex flex-col gap-2">
          <Textarea
            value={draft}
            onChange={(event) => handleDraftChange(event.target.value)}
            rows={14}
            className="font-mono text-xs"
          />
          {parseError && <p className="text-destructive text-xs">{parseError}</p>}
        </div>
      )}
    </div>
  )
}
