/** What we'll read, checked here before anything is uploaded.
 *
 * The server refuses the same things — this is the copy that saves someone
 * watching a 4 MB spreadsheet upload only to be told it was never readable.
 * Mirrors backend/src/ai/documents/extract.py; keep the two in step.
 */

export const SUPPORTED_SUFFIXES = ['.pdf', '.md', '.markdown', '.txt', '.text']

/** For the file picker's dialog, so unsupported files are greyed out there. */
export const ACCEPT = SUPPORTED_SUFFIXES.join(',')

const MAX_BYTES = 5 * 1024 * 1024

/** Why we won't read this file, or null if we will. */
export function refusalFor(file: File): string | null {
  const suffix = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()

  if (!file.name.includes('.') || !SUPPORTED_SUFFIXES.includes(suffix))
    return `${file.name} can't be read. Send a PDF, markdown, or plain text file.`

  if (file.size > MAX_BYTES)
    return `${file.name} is ${Math.round(file.size / (1024 * 1024))} MB. The limit is ${
      MAX_BYTES / (1024 * 1024)
    } MB.`

  return null
}
