import {
  BookOpen,
  Braces,
  Check,
  ChevronRight,
  CircleAlert,
  Clock3,
  Copy,
  Database,
  FileText,
  Hash,
  LoaderCircle,
  Menu,
  MessageSquare,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  UserRound,
  Users,
  WandSparkles,
  X,
} from 'lucide-react'
import {
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import { Button } from '@/components/ui/button'

type Source = {
  kind?: 'document' | 'message'
  page: number | null
  quote: string
}

type EntryContent = {
  statement?: string
  category?: string
  entities?: string[]
  source?: Source
  confidence?: string
  [key: string]: unknown
}

type IREntry = {
  id: string
  content: EntryContent
  author: string
  created_at: string
}

type DocumentInfo = {
  id: string
  filename: string
  mime_type: string
  size_bytes: number
  page_count: number
  created_at: string
  models: {
    ocr: string
    ir: string
  }
}

type ProjectSummary = {
  id: string
  name: string
  entry_count: number
  member_count: number
  created_at: string
  document: DocumentInfo | null
}

type ProjectBundle = {
  project: {
    id: string
    name: string
    ir: string[]
    users: string[]
    admins: string[]
    created_at: string
  }
  document: DocumentInfo | null
  entries: IREntry[]
}

type Profile = {
  id: string
  content: {
    name?: string
    discipline?: string
    expertise?: string
    history?: string
    preferences?: string
    context?: string
    system?: boolean
    [key: string]: unknown
  }
}

type Grounding = {
  entry_id: string
  path: string
  value: unknown
}

type Claim = {
  id: string
  text: string
  entry_id: string
  grounding: Grounding[]
  is_implication: boolean
  author?: string
  created_at?: string
}

type Citation = {
  entry_id: string
  statement: string
  page: number | null
  quote: string
}

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  insufficient?: boolean
}

type ViewMode = 'lens' | 'ir' | 'raw'

const API_BASE = import.meta.env.VITE_API_URL ?? ''
const ACCEPTED_FILES = '.pdf,.docx,.pptx,.png,.jpg,.jpeg,.webp,.avif'

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  const payload = (await response.json().catch(() => ({}))) as {
    error?: string
  }
  if (!response.ok) {
    throw new Error(payload.error || 'Something went wrong. Please try again.')
  }
  return payload as T
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
  }).format(new Date(value))
}

function shortId(value: string) {
  return value.replace(/^ir_/, 'IR-').slice(0, 11).toUpperCase()
}

function App() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [bundle, setBundle] = useState<ProjectBundle | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedProfileId, setSelectedProfileId] = useState('')
  const [claims, setClaims] = useState<Claim[]>([])
  const [changes, setChanges] = useState<IREntry[]>([])
  const [expandedEntryId, setExpandedEntryId] = useState<string | null>(null)
  const [loadingLibrary, setLoadingLibrary] = useState(true)
  const [loadingProject, setLoadingProject] = useState(false)
  const [loadingView, setLoadingView] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [posting, setPosting] = useState(false)
  const [asking, setAsking] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [mode, setMode] = useState<ViewMode>('ir')
  const [question, setQuestion] = useState('')
  const [updateText, setUpdateText] = useState('')
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mistralConfigured, setMistralConfigured] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [showProjectModal, setShowProjectModal] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [profileName, setProfileName] = useState('')
  const [profileContext, setProfileContext] = useState('')
  const [savingModal, setSavingModal] = useState(false)

  useEffect(() => {
    const initialise = async () => {
      try {
        const [library, profileList, health] = await Promise.all([
          apiRequest<{ projects: ProjectSummary[] }>('/api/projects'),
          apiRequest<{ profiles: Profile[] }>('/api/profiles'),
          apiRequest<{ mistral_configured: boolean }>('/api/health'),
        ])
        setProjects(library.projects)
        setProfiles(profileList.profiles)
        setMistralConfigured(health.mistral_configured)
        const firstHumanProfile = profileList.profiles.find(
          (profile) => !profile.content.system,
        )
        if (firstHumanProfile) setSelectedProfileId(firstHumanProfile.id)
        const medGuard =
          library.projects.find((project) => project.id === 'prj_medguard') ??
          library.projects[0]
        if (medGuard) setSelectedId(medGuard.id)
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Could not load projects.')
      } finally {
        setLoadingLibrary(false)
      }
    }
    void initialise()
  }, [])

  useEffect(() => {
    if (!selectedId) {
      setBundle(null)
      return
    }
    const loadProject = async () => {
      setLoadingProject(true)
      setError(null)
      setClaims([])
      setChanges([])
      try {
        const result = await apiRequest<ProjectBundle>(`/api/projects/${selectedId}`)
        setBundle(result)
        setMessages([])
        const viewerId = result.project.users.includes(selectedProfileId)
          ? selectedProfileId
          : result.project.users[0] ?? ''
        setSelectedProfileId(viewerId)

        const storageKey = `relay:last-viewed:${selectedId}`
        const lastViewed = localStorage.getItem(storageKey)
        if (lastViewed) {
          const digest = await apiRequest<{ entries: IREntry[] }>(
            `/api/projects/${selectedId}/changes?since=${encodeURIComponent(lastViewed)}`,
          )
          setChanges(digest.entries)
        }
        localStorage.setItem(storageKey, new Date().toISOString())
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Could not load that project.')
      } finally {
        setLoadingProject(false)
      }
    }
    void loadProject()
    // selectedProfileId is intentionally resolved after loading project membership.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId])

  useEffect(() => {
    if (!bundle || mode !== 'lens' || !selectedProfileId) return
    const loadView = async () => {
      setLoadingView(true)
      setError(null)
      try {
        const view = await apiRequest<{ claims: Claim[] }>(
          `/api/projects/${bundle.project.id}/view?user_id=${encodeURIComponent(
            selectedProfileId,
          )}`,
        )
        setClaims(view.claims)
      } catch (caught) {
        setClaims([])
        setError(
          caught instanceof Error ? caught.message : 'Could not generate that view.',
        )
      } finally {
        setLoadingView(false)
      }
    }
    void loadView()
  }, [bundle, mode, selectedProfileId])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, asking])

  const profileById = useMemo(
    () => new Map(profiles.map((profile) => [profile.id, profile])),
    [profiles],
  )
  const projectProfiles = useMemo(
    () =>
      (bundle?.project.users ?? [])
        .map((id) => profileById.get(id))
        .filter((profile): profile is Profile => Boolean(profile)),
    [bundle, profileById],
  )
  const selectedProfile = profileById.get(selectedProfileId)
  const categories = useMemo(
    () =>
      Array.from(
        new Set(
          (bundle?.entries ?? [])
            .map((entry) => entry.content.category)
            .filter(Boolean),
        ),
      ),
    [bundle],
  )

  const profileNameFor = (id?: string) =>
    (id && profileById.get(id)?.content.name) || id || 'Unknown'

  const refreshProject = async (projectId: string) => {
    const result = await apiRequest<ProjectBundle>(`/api/projects/${projectId}`)
    setBundle(result)
    setProjects((current) =>
      current.map((project) =>
        project.id === projectId
          ? { ...project, entry_count: result.entries.length }
          : project,
      ),
    )
    return result
  }

  const uploadFile = async (file?: File) => {
    if (!file) return
    setUploading(true)
    setError(null)
    setSidebarOpen(false)
    const formData = new FormData()
    formData.append('file', file)
    if (selectedProfileId) formData.append('author_id', selectedProfileId)
    try {
      const result = await apiRequest<ProjectBundle>('/api/documents', {
        method: 'POST',
        body: formData,
      })
      const summary: ProjectSummary = {
        id: result.project.id,
        name: result.project.name,
        entry_count: result.entries.length,
        member_count: result.project.users.length,
        created_at: result.project.created_at,
        document: result.document,
      }
      setProjects((current) => [
        summary,
        ...current.filter((project) => project.id !== summary.id),
      ])
      setBundle(result)
      setSelectedId(result.project.id)
      setMessages([])
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The upload failed.')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const postUpdate = async (event: FormEvent) => {
    event.preventDefault()
    if (!bundle || !selectedProfileId || !updateText.trim() || posting) return
    setPosting(true)
    setError(null)
    try {
      await apiRequest<{ entries: IREntry[] }>(
        `/api/projects/${bundle.project.id}/messages`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: updateText.trim(),
            author_id: selectedProfileId,
          }),
        },
      )
      setUpdateText('')
      await refreshProject(bundle.project.id)
      setMode('ir')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not add that update.')
    } finally {
      setPosting(false)
    }
  }

  const createProject = async (event: FormEvent) => {
    event.preventDefault()
    if (!projectName.trim() || !selectedProfileId) return
    setSavingModal(true)
    try {
      const project = await apiRequest<ProjectBundle['project']>('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projectName.trim(),
          creator_id: selectedProfileId,
        }),
      })
      const summary: ProjectSummary = {
        id: project.id,
        name: project.name,
        entry_count: 0,
        member_count: 1,
        created_at: project.created_at,
        document: null,
      }
      setProjects((current) => [summary, ...current])
      setProjectName('')
      setShowProjectModal(false)
      setSelectedId(project.id)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not create project.')
    } finally {
      setSavingModal(false)
    }
  }

  const createProfile = async (event: FormEvent) => {
    event.preventDefault()
    if (!profileName.trim() || !profileContext.trim()) return
    setSavingModal(true)
    try {
      const profile = await apiRequest<Profile>('/api/profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: {
            name: profileName.trim(),
            context: profileContext.trim(),
          },
        }),
      })
      setProfiles((current) => [...current, profile])
      if (!bundle) setSelectedProfileId(profile.id)
      setProfileName('')
      setProfileContext('')
      setShowProfileModal(false)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not create profile.')
    } finally {
      setSavingModal(false)
    }
  }

  const askQuestion = async (event?: FormEvent, suggestion?: string) => {
    event?.preventDefault()
    const nextQuestion = (suggestion ?? question).trim()
    if (!nextQuestion || !bundle || asking) return
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: nextQuestion,
    }
    setMessages((current) => [...current, userMessage])
    setQuestion('')
    setAsking(true)
    try {
      const response = await apiRequest<{
        answer: string
        insufficient_evidence: boolean
        citations: Citation[]
      }>(`/api/projects/${bundle.project.id}/questions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: nextQuestion,
          history: messages.map(({ role, content }) => ({ role, content })),
        }),
      })
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.answer,
          citations: response.citations,
          insufficient: response.insufficient_evidence,
        },
      ])
    } catch (caught) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content:
            caught instanceof Error ? caught.message : 'I could not answer that.',
          insufficient: true,
        },
      ])
    } finally {
      setAsking(false)
    }
  }

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    void uploadFile(event.target.files?.[0])
  }

  const onDrop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault()
    setDragging(false)
    void uploadFile(event.dataTransfer.files[0])
  }

  const copyProjectId = async () => {
    if (!bundle) return
    await navigator.clipboard.writeText(bundle.project.id)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  const selectProject = (id: string) => {
    setSelectedId(id)
    setSidebarOpen(false)
    setMode('ir')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <button
            className="mobile-menu"
            aria-label="Open project library"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu />
          </button>
          <div className="brand-mark">
            <Sparkles />
          </div>
          <div>
            <span className="brand-name">Relay</span>
            <span className="brand-suffix">IR</span>
          </div>
        </div>
        <div className="topbar-center">
          <span className="breadcrumb-muted">Workspace</span>
          <ChevronRight />
          <span>{bundle?.project.name ?? 'Context translator'}</span>
        </div>
        <div
          className={`api-status ${mistralConfigured ? '' : 'api-status-warning'}`}
          title={
            mistralConfigured
              ? 'Mistral API key is configured'
              : 'Add MISTRAL_API_KEY to the backend'
          }
        >
          <span />
          {mistralConfigured ? 'Mistral configured' : 'API key needed'}
        </div>
      </header>

      <main className="workspace">
        <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
          <div className="sidebar-mobile-head">
            <span>Projects</span>
            <button aria-label="Close project library" onClick={() => setSidebarOpen(false)}>
              <X />
            </button>
          </div>
          <div className="sidebar-header">
            <div>
              <p className="eyebrow">Shared workspace</p>
              <h2>Projects</h2>
            </div>
            <span className="count-badge">{projects.length}</span>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_FILES}
            hidden
            onChange={onFileChange}
          />
          <div className="sidebar-actions">
            <button
              className="new-project-button"
              onClick={() =>
                profiles.length ? setShowProjectModal(true) : setShowProfileModal(true)
              }
            >
              <Plus />
              New project
            </button>
            <button
              className="icon-upload-button"
              aria-label="Import document"
              title="Import a document"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || !mistralConfigured}
            >
              {uploading ? <LoaderCircle className="spin" /> : <UploadCloud />}
            </button>
          </div>

          <div className="document-list">
            {loadingLibrary ? (
              <>
                <div className="document-skeleton" />
                <div className="document-skeleton" />
              </>
            ) : (
              projects.map((project) => (
                <button
                  key={project.id}
                  className={`document-item ${
                    selectedId === project.id ? 'document-item-active' : ''
                  }`}
                  onClick={() => selectProject(project.id)}
                >
                  <span className="document-icon">
                    {project.document ? <FileText /> : <Users />}
                  </span>
                  <span className="document-copy">
                    <strong>{project.name}</strong>
                    <small>
                      {project.entry_count} entries · {project.member_count} members
                    </small>
                  </span>
                  <ChevronRight className="document-arrow" />
                </button>
              ))
            )}
          </div>

          <button className="profile-card" onClick={() => setShowProfileModal(true)}>
            <span>
              <UserRound />
            </span>
            <div>
              <small>Working as</small>
              <strong>{selectedProfile?.content.name ?? 'Create a profile'}</strong>
            </div>
            <Plus />
          </button>

          <div className="sidebar-note">
            <ShieldCheck />
            <div>
              <strong>Grounded by design</strong>
              <p>Every personalized claim links to an exact IR field.</p>
            </div>
          </div>
        </aside>

        {sidebarOpen && (
          <button
            className="sidebar-backdrop"
            aria-label="Close project library"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <section
          className={`content-panel ${dragging ? 'drop-active' : ''}`}
          onDragEnter={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={(event) => {
            if (event.currentTarget === event.target) setDragging(false)
          }}
          onDrop={onDrop}
        >
          {dragging && (
            <div className="drop-overlay">
              <UploadCloud />
              <strong>Drop to generate the IR</strong>
              <span>Mistral will read, structure, and ground the document</span>
            </div>
          )}
          {error && (
            <div className="error-banner">
              <CircleAlert />
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError(null)}>
                <X />
              </button>
            </div>
          )}

          {uploading ? (
            <ProcessingState />
          ) : loadingProject ? (
            <LoadingProject />
          ) : bundle ? (
            <>
              <div className="project-head">
                <div className="project-title-row">
                  <div className="project-file-icon">
                    {bundle.document ? <FileText /> : <Users />}
                  </div>
                  <div>
                    <div className="project-kicker">
                      <span>{bundle.document ? 'Imported project' : 'Shared project'}</span>
                      <span className="verified-pill">
                        <ShieldCheck /> Grounded IR
                      </span>
                    </div>
                    <h1>{bundle.project.name}</h1>
                    <div className="project-meta">
                      <span>{bundle.entries.length} atomic entries</span>
                      <i />
                      <span>{bundle.project.users.length} members</span>
                      {bundle.document && (
                        <>
                          <i />
                          <span>
                            {bundle.document.page_count} pages ·{' '}
                            {formatBytes(bundle.document.size_bytes)}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="project-actions">
                  <button className="id-chip" onClick={() => void copyProjectId()}>
                    <Hash />
                    <span>{bundle.project.id}</span>
                    {copied ? <Check /> : <Copy />}
                  </button>
                  <select
                    className="profile-select"
                    value={selectedProfileId}
                    onChange={(event) => setSelectedProfileId(event.target.value)}
                  >
                    {projectProfiles.map((profile) => (
                      <option key={profile.id} value={profile.id}>
                        {profile.content.name ?? profile.id}
                      </option>
                    ))}
                  </select>
                  <div className="view-toggle">
                    <button
                      className={mode === 'lens' ? 'active' : ''}
                      onClick={() => setMode('lens')}
                      disabled={!selectedProfileId}
                    >
                      <WandSparkles /> My lens
                    </button>
                    <button
                      className={mode === 'ir' ? 'active' : ''}
                      onClick={() => setMode('ir')}
                    >
                      <BookOpen /> IR
                    </button>
                    <button
                      className={mode === 'raw' ? 'active' : ''}
                      onClick={() => setMode('raw')}
                    >
                      <Braces /> Raw
                    </button>
                  </div>
                </div>
              </div>

              {changes.length > 0 && (
                <div className="changes-banner">
                  <Clock3 />
                  <div>
                    <strong>Since you last viewed</strong>
                    <span>
                      {changes.length} new IR {changes.length === 1 ? 'entry' : 'entries'}{' '}
                      added: {changes
                        .slice(0, 2)
                        .map((entry) => entry.content.statement)
                        .filter(Boolean)
                        .join(' · ')}
                      {changes.length > 2 ? ' · …' : ''}
                    </span>
                  </div>
                  <button onClick={() => setChanges([])}>Dismiss</button>
                </div>
              )}

              {mode === 'lens' ? (
                <>
                  <div className="ir-toolbar">
                    <div>
                      <WandSparkles />
                      <span>
                        Re-projected for{' '}
                        {selectedProfile?.content.name ?? selectedProfileId}
                      </span>
                      <span className="entry-count">{claims.length}</span>
                    </div>
                    <span className="lens-context">
                      {selectedProfile?.content.discipline ??
                        selectedProfile?.content.context ??
                        'Personal context'}
                    </span>
                  </div>
                  {loadingView ? (
                    <div className="claim-loading">
                      <LoaderCircle className="spin" />
                      Re-projecting the IR through this profile…
                    </div>
                  ) : claims.length ? (
                    <div className="entry-list">
                      {claims.map((claim, index) => {
                        const sourceEntry = bundle.entries.find(
                          (entry) => entry.id === claim.entry_id,
                        )
                        return (
                          <article className="claim-card" key={claim.id}>
                            <div className="claim-number">
                              {String(index + 1).padStart(2, '0')}
                            </div>
                            <div className="claim-body">
                              <div className="entry-topline">
                                <span
                                  className={`category ${
                                    claim.is_implication
                                      ? 'category-implication'
                                      : 'category-context'
                                  }`}
                                >
                                  {claim.is_implication ? 'Implication' : 'Re-projection'}
                                </span>
                                <span className="claim-author">
                                  For {selectedProfile?.content.name ?? 'viewer'}
                                </span>
                              </div>
                              <p className="claim-text">{claim.text}</p>
                              <div className="grounding-row">
                                {claim.grounding.map((ground) => (
                                  <button
                                    key={`${claim.id}-${ground.path}`}
                                    onClick={() =>
                                      setExpandedEntryId((current) =>
                                        current === claim.entry_id
                                          ? null
                                          : claim.entry_id,
                                      )
                                    }
                                  >
                                    <ShieldCheck />
                                    {shortId(ground.entry_id)} · {ground.path}
                                  </button>
                                ))}
                              </div>
                              {expandedEntryId === claim.entry_id && sourceEntry && (
                                <div className="grounding-detail">
                                  <strong>Referenced IR entry</strong>
                                  <p>{sourceEntry.content.statement}</p>
                                  <code>{JSON.stringify(sourceEntry.content, null, 2)}</code>
                                </div>
                              )}
                            </div>
                          </article>
                        )
                      })}
                    </div>
                  ) : (
                    <div className="feed-empty">
                      <WandSparkles />
                      <h3>No grounded claims returned</h3>
                      <p>
                        Add an update to the project or choose another profile lens.
                      </p>
                    </div>
                  )}
                </>
              ) : mode === 'ir' ? (
                <>
                  <form className="update-composer" onSubmit={postUpdate}>
                    <div className="composer-avatar">
                      {(selectedProfile?.content.name ?? '?').slice(0, 1)}
                    </div>
                    <div className="composer-main">
                      <div className="composer-label">
                        <strong>{selectedProfile?.content.name ?? 'Project member'}</strong>
                        <span>Share an update in your own language</span>
                      </div>
                      <textarea
                        rows={2}
                        value={updateText}
                        disabled={!selectedProfileId || posting || !mistralConfigured}
                        placeholder="What changed, what was decided, or what should the team know?"
                        onChange={(event) => setUpdateText(event.target.value)}
                      />
                      <div className="composer-footer">
                        <span>
                          <Sparkles /> Mistral extracts neutral, atomic facts
                        </span>
                        <Button type="submit" disabled={!updateText.trim() || posting}>
                          {posting ? <LoaderCircle className="spin" /> : <Send />}
                          Add to IR
                        </Button>
                      </div>
                    </div>
                  </form>
                  <div className="ir-toolbar">
                    <div>
                      <Database />
                      <span>Project feed · Intermediate representation</span>
                      <span className="entry-count">{bundle.entries.length}</span>
                    </div>
                    <div className="category-row">
                      {categories.slice(0, 4).map((category) => (
                        <span key={category}>{category}</span>
                      ))}
                    </div>
                  </div>
                  {bundle.entries.length ? (
                    <div className="entry-list">
                      {bundle.entries.map((entry, index) => (
                        <IREntryCard
                          key={entry.id}
                          entry={entry}
                          index={index}
                          authorName={profileNameFor(entry.author)}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="feed-empty">
                      <MessageSquare />
                      <h3>No project updates yet</h3>
                      <p>Share the first update above to create the project’s IR.</p>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="ir-toolbar">
                    <div>
                      <Braces />
                      <span>Raw Intermediate Representation</span>
                    </div>
                  </div>
                  <div className="raw-panel">
                    <div className="raw-header">
                      <span>project.ir.json</span>
                      <span>Schema validated</span>
                    </div>
                    <pre>{JSON.stringify(bundle.entries, null, 2)}</pre>
                  </div>
                </>
              )}
            </>
          ) : (
            <EmptyState
              onCreate={() =>
                profiles.length ? setShowProjectModal(true) : setShowProfileModal(true)
              }
              onUpload={() => fileInputRef.current?.click()}
              configured={mistralConfigured}
            />
          )}
        </section>

        <aside className="chat-panel">
          <div className="chat-head">
            <div className="chat-title">
              <span>
                <MessageSquare />
              </span>
              <div>
                <h2>Ask the IR</h2>
                <p>{bundle ? 'Answers from this project only' : 'Select a project first'}</p>
              </div>
            </div>
            {bundle && (
              <span className="chat-project-id">
                <i /> {bundle.project.id.slice(-6).toUpperCase()}
              </span>
            )}
          </div>

          <div className="chat-messages">
            {!bundle ? (
              <div className="chat-placeholder">
                <div>
                  <MessageSquare />
                </div>
                <h3>Your IR, conversationally</h3>
                <p>Create or select a project to ask grounded questions.</p>
              </div>
            ) : messages.length === 0 ? (
              <div className="chat-welcome">
                <div className="assistant-avatar">
                  <Sparkles />
                </div>
                <div className="assistant-intro">
                  <p>
                    Ask about <strong>{bundle.project.name}</strong>. Every factual
                    answer includes its supporting IR entries.
                  </p>
                </div>
                <div className="suggestions">
                  <span>Try asking</span>
                  {[
                    'What changed most recently?',
                    'What decisions were made?',
                    'List the risks and constraints.',
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => void askQuestion(undefined, suggestion)}
                    >
                      {suggestion}
                      <ChevronRight />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className={`message message-${message.role}`}>
                  {message.role === 'assistant' && (
                    <div className="mini-avatar">
                      <Sparkles />
                    </div>
                  )}
                  <div>
                    <div className="message-bubble">{message.content}</div>
                    {!!message.citations?.length && (
                      <div className="citation-list">
                        <span>Sources</span>
                        {message.citations.map((citation) => (
                          <button
                            key={citation.entry_id}
                            title={citation.quote}
                            onClick={() => {
                              setMode('ir')
                              setExpandedEntryId(citation.entry_id)
                            }}
                          >
                            <ShieldCheck />
                            {shortId(citation.entry_id)}
                            {citation.page ? ` · p.${citation.page}` : ''}
                          </button>
                        ))}
                      </div>
                    )}
                    {message.insufficient && (
                      <span className="insufficient-label">
                        <CircleAlert /> Insufficient IR evidence
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
            {asking && (
              <div className="message message-assistant">
                <div className="mini-avatar">
                  <Sparkles />
                </div>
                <div className="thinking">
                  <span />
                  <span />
                  <span />
                  Checking IR entries
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form className="chat-form" onSubmit={(event) => void askQuestion(event)}>
            <div className="chat-input-wrap">
              <textarea
                rows={1}
                value={question}
                disabled={!bundle || asking}
                placeholder={bundle ? 'Ask about this project…' : 'Select a project…'}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void askQuestion()
                  }
                }}
              />
              <Button
                type="submit"
                size="icon"
                aria-label="Send question"
                disabled={!bundle || !question.trim() || asking}
              >
                {asking ? <LoaderCircle className="spin" /> : <Send />}
              </Button>
            </div>
            <p>
              <ShieldCheck /> Answers are restricted to cited IR evidence.
            </p>
          </form>
        </aside>
      </main>

      {showProjectModal && (
        <Modal title="Create a project" onClose={() => setShowProjectModal(false)}>
          <form className="modal-form" onSubmit={createProject}>
            <label>
              Project name
              <input
                autoFocus
                value={projectName}
                placeholder="e.g. MedGuard"
                onChange={(event) => setProjectName(event.target.value)}
              />
            </label>
            <label>
              Creator profile
              <select
                value={selectedProfileId}
                onChange={(event) => setSelectedProfileId(event.target.value)}
              >
                {profiles
                  .filter((profile) => !profile.content.system)
                  .map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.content.name ?? profile.id}
                    </option>
                  ))}
              </select>
            </label>
            <p>The creator becomes the project’s first member and administrator.</p>
            <div className="modal-actions">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowProjectModal(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={!projectName.trim() || savingModal}>
                {savingModal && <LoaderCircle className="spin" />}
                Create project
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {showProfileModal && (
        <Modal title="Create your context profile" onClose={() => setShowProfileModal(false)}>
          <form className="modal-form" onSubmit={createProfile}>
            <label>
              Your name
              <input
                autoFocus
                value={profileName}
                placeholder="e.g. Maya Chen"
                onChange={(event) => setProfileName(event.target.value)}
              />
            </label>
            <label>
              Your context
              <textarea
                rows={5}
                value={profileContext}
                placeholder="Describe your expertise, responsibilities, project history, and how you prefer information framed…"
                onChange={(event) => setProfileContext(event.target.value)}
              />
            </label>
            <p>No fixed roles—the model uses exactly the context you choose to share.</p>
            <div className="modal-actions">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowProfileModal(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!profileName.trim() || !profileContext.trim() || savingModal}
              >
                {savingModal && <LoaderCircle className="spin" />}
                Save profile
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

function IREntryCard({
  entry,
  index,
  authorName,
}: {
  entry: IREntry
  index: number
  authorName: string
}) {
  return (
    <article className="entry-card">
      <div className="entry-index">{String(index + 1).padStart(2, '0')}</div>
      <div className="entry-body">
        <div className="entry-topline">
          <span className={`category category-${entry.content.category ?? 'context'}`}>
            {entry.content.category ?? 'fact'}
          </span>
          <code>{shortId(entry.id)}</code>
          <span className="entry-attribution">
            {authorName} · {formatDate(entry.created_at)}
          </span>
          <span className="confidence">
            <i /> {entry.content.confidence ?? 'grounded'}
          </span>
        </div>
        <p className="statement">
          {entry.content.statement ?? JSON.stringify(entry.content)}
        </p>
        {!!entry.content.entities?.length && (
          <div className="entity-row">
            {entry.content.entities.map((entity) => (
              <span key={entity}>{entity}</span>
            ))}
          </div>
        )}
        {entry.content.source && (
          <div className="source-block">
            <div className="source-label">
              <ShieldCheck />
              Source ·{' '}
              {entry.content.source.kind === 'message'
                ? 'Project message'
                : `Page ${entry.content.source.page ?? '—'}`}
            </div>
            <blockquote>“{entry.content.source.quote}”</blockquote>
          </div>
        )}
      </div>
    </article>
  )
}

function EmptyState({
  onCreate,
  onUpload,
  configured,
}: {
  onCreate: () => void
  onUpload: () => void
  configured: boolean
}) {
  return (
    <div className="empty-state">
      <div className="empty-visual">
        <div className="empty-sheet empty-sheet-back" />
        <div className="empty-sheet">
          <div className="sheet-icon">
            <Users />
          </div>
          <span />
          <span />
          <span className="short" />
        </div>
        <div className="spark spark-one">
          <Sparkles />
        </div>
        <div className="spark spark-two">
          <Database />
        </div>
      </div>
      <p className="eyebrow">One source of truth · every professional context</p>
      <h1>Give every teammate the view they need</h1>
      <p className="empty-description">
        Capture project updates as neutral IR, then re-project the same facts through
        each person’s own expertise, history, and priorities.
      </p>
      <div className="empty-actions">
        <Button size="lg" onClick={onCreate}>
          <Plus /> Create a project
        </Button>
        <Button size="lg" variant="outline" onClick={onUpload} disabled={!configured}>
          <UploadCloud /> Import a document
        </Button>
      </div>
      {!configured && (
        <p className="configuration-note">
          Add <code>MISTRAL_API_KEY</code> before extracting or re-projecting IR.
        </p>
      )}
      <div className="empty-steps">
        <div>
          <span>01</span>
          <strong>Speak naturally</strong>
          <p>Each person writes in the language of their discipline.</p>
        </div>
        <div>
          <span>02</span>
          <strong>Neutral IR</strong>
          <p>Mistral turns updates into atomic, traceable facts.</p>
        </div>
        <div>
          <span>03</span>
          <strong>Personal re-projection</strong>
          <p>Implications are shaped by each viewer’s own context.</p>
        </div>
      </div>
    </div>
  )
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: React.ReactNode
}) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <span className="brand-mark">
              <Sparkles />
            </span>
            <h2>{title}</h2>
          </div>
          <button aria-label="Close" onClick={onClose}>
            <X />
          </button>
        </div>
        {children}
      </section>
    </div>
  )
}

function ProcessingState() {
  return (
    <div className="processing-state">
      <div className="processing-orbit">
        <div className="processing-core">
          <Sparkles />
        </div>
        <span />
        <span />
        <span />
      </div>
      <p className="eyebrow">Mistral is working</p>
      <h2>Building your source of truth</h2>
      <p>Reading every page, extracting atomic facts, and verifying source quotes…</p>
      <div className="processing-track">
        <span />
      </div>
      <small>Large documents can take a minute</small>
    </div>
  )
}

function LoadingProject() {
  return (
    <div className="loading-project">
      <div className="loading-title" />
      <div className="loading-meta" />
      <div className="loading-card" />
      <div className="loading-card" />
      <div className="loading-card" />
    </div>
  )
}

export default App
