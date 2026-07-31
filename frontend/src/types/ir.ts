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

// Re-projections are runtime output, not stored data — no schema for them.
