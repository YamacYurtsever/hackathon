// Mirrors backend/schemas/*.schema.json — keep in sync manually until we
// generate one from the other.

export interface IREntry {
  id: string
  // Neutral, structured fact. Free-form on purpose — no separate
  // type/summary/details split.
  content: Record<string, unknown>
  // Role is a lens applied via ContextProfile at read/write time, not a
  // stored fact — look it up from author, don't add owner_role here.
  // Overwritten on update — no contributor history, no versioning.
  author: string
  created_at: string
  // Which domains/roles this entry affects is computed at re-projection
  // time from content, not stored here — avoids update anomalies.
}

// A project owns a list of IR entry ids and a list of user ids — entries
// and users don't point back to a project.
export interface Project {
  id: string
  name: string
  ir: string[]
  users: string[]
  // Subset of users with admin rights. Creator is added here automatically
  // on creation. Only admins approve IR amendments and promote other
  // members to admin. If the last admin exits and users remain, one is
  // auto-promoted — a non-empty project always has at least one admin.
  admins: string[]
}

// A user's account and global context, not scoped to a project. Content is
// free-form on purpose — role, expertise, history blurb, whatever
// re-projection needs. The backend also stores a password_hash, but that
// never gets sent to the client, so it's not part of this type.
export interface Profile {
  id: string
  username: string
  content: Record<string, unknown>
}

// A project member: their profile plus whether they're an admin of the
// project being viewed. Admin-ness lives on the project, not the profile.
export interface Member extends Profile {
  is_admin: boolean
}

// Where a fact read out of a document came from. Not part of the fact — it
// rides along on the proposal and becomes the request's source text, so a
// reviewer can check one proposal without re-reading the document.
export interface Provenance {
  document: string
  // Usually one. A fact stated in both an abstract and an appendix is one
  // proposal that was found in two places.
  locations: string[]
  // Absent when the model paraphrased instead of copying. The server verifies
  // the quote is really in the passage and drops it if it isn't.
  quote?: string
}

// A proposed change to the IR. Extraction produces these; they only become
// entries once an admin approves the request carrying them.
export interface Operation {
  op: 'create' | 'update'
  // Present on updates: the entry being revised.
  target_id?: string
  content: Record<string, unknown>
  // Present only on proposals read out of a document.
  provenance?: Provenance
}

// One proposed change waiting on an admin. A message proposing three things
// makes three requests, so each can be accepted or rejected on its own.
export interface ChangeRequest {
  id: string
  project_id: string
  author: string
  created_at: string
  source_text: string
  operation: Operation
}

// Prose is returned as segments so it reads continuously while every clause
// stays traceable. The server drops any segment whose citations don't resolve.
export interface Segment {
  text: string
  source_entry_ids: string[]
}

export interface Summary {
  segments: Segment[]
  cached: boolean
  /** Only when the project has no entries: an orienting line for this reader,
   * in place of a summary there is nothing to write. */
  welcome?: string
}

// What one message turned out to be. It can propose changes, answer a
// question, or both — nothing is stored either way.
export interface InputResult {
  text: string
  operations: Operation[]
  answer: string | null
  /** The answer re-projected for the asker, carrying the entries it drew on.
   * Present whenever `answer` is. */
  answer_segments?: Segment[]
  /** Operations the server threw away as unusable, so nothing vanishes silently. */
  dropped: number
}

// What one document turned out to say. Same shape as a message's proposals —
// a document is a longer message — plus what it took to read it.
export interface DocumentResult {
  document: string
  /** How many passages it was cut into, which is how many model calls it took. */
  passages: number
  operations: Operation[]
  dropped: number
  /** Passages that couldn't be read at all. Reported rather than swallowed, so
   * nobody assumes the document was read in full when part of it wasn't. */
  failed_passages: number
}
