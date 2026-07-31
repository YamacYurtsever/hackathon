/** Rendering an IR fact for a human. */

/** The one key every entry has, and the only one worth showing in a list.
 *
 * Content is free-form, so a fact that somehow arrived without a statement
 * falls back to its raw JSON rather than rendering as an empty row — a
 * proposal you can't see is a proposal you can't reject.
 */
export function statementOf(content: Record<string, unknown>): string {
  const statement = content.statement
  return typeof statement === 'string' ? statement : JSON.stringify(content)
}
