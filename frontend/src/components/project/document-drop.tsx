import { useEffect, useRef, useState } from 'react'

/** Drag a file anywhere over the project view and this arms; release and it
 * runs the same read → propose → submit → merge path a typed sentence runs.
 *
 * There is no import screen, because a document isn't a different kind of
 * input — it's a longer message, and it enters where a message enters. */
export function DocumentDrop({
  disabled,
  onDrop,
  children,
}: {
  disabled: boolean
  onDrop: (files: File[]) => void
  children: React.ReactNode
}) {
  const [armed, setArmed] = useState(false)
  // dragenter/dragleave fire for every child element the pointer crosses, so
  // depth-counting is the only way to know when the drag has really left.
  const depth = useRef(0)
  // Escape disarms mid-drag; the browser will still deliver the drop, so this
  // records that it should be ignored when it arrives.
  const dismissed = useRef(false)

  useEffect(() => {
    if (!armed) return
    const disarm = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      dismissed.current = true
      depth.current = 0
      setArmed(false)
    }
    window.addEventListener('keydown', disarm)
    return () => window.removeEventListener('keydown', disarm)
  }, [armed])

  const carriesFiles = (event: React.DragEvent) =>
    Array.from(event.dataTransfer.types).includes('Files')

  return (
    <div
      className="relative h-full"
      onDragEnter={(event) => {
        if (disabled || !carriesFiles(event)) return
        event.preventDefault()
        depth.current += 1
        setArmed(true)
      }}
      onDragOver={(event) => {
        // Without this the browser navigates to the file instead of dropping it.
        if (!disabled && carriesFiles(event)) event.preventDefault()
      }}
      onDragLeave={() => {
        depth.current = Math.max(0, depth.current - 1)
        if (depth.current === 0) {
          setArmed(false)
          dismissed.current = false
        }
      }}
      onDrop={(event) => {
        if (disabled || !carriesFiles(event)) return
        event.preventDefault()
        depth.current = 0
        setArmed(false)
        if (dismissed.current) {
          dismissed.current = false
          return
        }
        onDrop(Array.from(event.dataTransfer.files))
      }}
    >
      {children}

      {armed && (
        // pointer-events-none matters: an overlay that catches the pointer
        // would swallow the drop it's inviting.
        <div className="bg-background/75 pointer-events-none absolute inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="border-brand/60 bg-brand/5 flex h-full w-full flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed">
            <p className="text-brand text-lg font-medium">
              Drop to read into this project
            </p>
            <p className="text-muted-foreground text-sm">
              PDF, markdown, or plain text — one document at a time
            </p>
            <p className="text-muted-foreground mt-2 text-xs">
              Esc to cancel. Nothing is recorded until you review it.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
