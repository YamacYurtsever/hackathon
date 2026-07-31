import {
  BookOpen,
  Braces,
  Check,
  ChevronRight,
  CircleAlert,
  Copy,
  Database,
  FileText,
  Hash,
  LoaderCircle,
  Menu,
  MessageSquare,
  Send,
  ShieldCheck,
  Sparkles,
  UploadCloud,
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
  page: number
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

type DocumentSummary = DocumentInfo & {
  name: string
  entry_count: number
}

type ProjectBundle = {
  project: {
    id: string
    name: string
    ir: string[]
    users: string[]
  }
  document: DocumentInfo
  entries: IREntry[]
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
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [bundle, setBundle] = useState<ProjectBundle | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loadingLibrary, setLoadingLibrary] = useState(true)
  const [loadingProject, setLoadingProject] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [asking, setAsking] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [mode, setMode] = useState<'natural' | 'raw'>('natural')
  const [question, setQuestion] = useState('')
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mistralConfigured, setMistralConfigured] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])

  useEffect(() => {
    const initialise = async () => {
      try {
        const [library, health] = await Promise.all([
          apiRequest<{ documents: DocumentSummary[] }>('/api/documents'),
          apiRequest<{ mistral_configured: boolean }>('/api/health'),
        ])
        setDocuments(library.documents)
        setMistralConfigured(health.mistral_configured)
        if (library.documents[0]) setSelectedId(library.documents[0].id)
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
      try {
        const result = await apiRequest<ProjectBundle>(`/api/projects/${selectedId}`)
        setBundle(result)
        setMessages([])
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Could not load that project.')
      } finally {
        setLoadingProject(false)
      }
    }
    void loadProject()
  }, [selectedId])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, asking])

  const categories = useMemo(() => {
    if (!bundle) return []
    return Array.from(
      new Set(bundle.entries.map((entry) => entry.content.category).filter(Boolean)),
    )
  }, [bundle])

  const uploadFile = async (file?: File) => {
    if (!file) return
    setUploading(true)
    setError(null)
    setSidebarOpen(false)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const result = await apiRequest<ProjectBundle>('/api/documents', {
        method: 'POST',
        body: formData,
      })
      const summary: DocumentSummary = {
        ...result.document,
        name: result.project.name,
        entry_count: result.entries.length,
      }
      setDocuments((current) => [
        summary,
        ...current.filter((document) => document.id !== summary.id),
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

  const askQuestion = async (event?: FormEvent, suggestedQuestion?: string) => {
    event?.preventDefault()
    const nextQuestion = (suggestedQuestion ?? question).trim()
    if (!nextQuestion || !bundle || asking) return

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: nextQuestion,
    }
    const nextMessages = [...messages, userMessage]
    setMessages(nextMessages)
    setQuestion('')
    setAsking(true)
    setError(null)

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
            caught instanceof Error
              ? caught.message
              : 'I could not answer that question.',
          insufficient: true,
        },
      ])
    } finally {
      setAsking(false)
    }
  }

  const selectDocument = (id: string) => {
    setSelectedId(id)
    setSidebarOpen(false)
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
          <span>{bundle?.project.name ?? 'Document intelligence'}</span>
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
              <p className="eyebrow">Your workspace</p>
              <h2>Projects</h2>
            </div>
            <span className="count-badge">{documents.length}</span>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_FILES}
            hidden
            onChange={onFileChange}
          />
          <button
            className="upload-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || !mistralConfigured}
          >
            {uploading ? <LoaderCircle className="spin" /> : <UploadCloud />}
            <span>
              <strong>{uploading ? 'Building IR…' : 'Add document'}</strong>
              <small>PDF, DOCX, PPTX or image</small>
            </span>
          </button>

          <div className="document-list">
            {loadingLibrary ? (
              <>
                <div className="document-skeleton" />
                <div className="document-skeleton" />
              </>
            ) : (
              documents.map((document) => (
                <button
                  key={document.id}
                  className={`document-item ${
                    selectedId === document.id ? 'document-item-active' : ''
                  }`}
                  onClick={() => selectDocument(document.id)}
                >
                  <span className="document-icon">
                    <FileText />
                  </span>
                  <span className="document-copy">
                    <strong>{document.name}</strong>
                    <small>
                      {document.entry_count} entries · {formatDate(document.created_at)}
                    </small>
                  </span>
                  <ChevronRight className="document-arrow" />
                </button>
              ))
            )}
          </div>

          <div className="sidebar-note">
            <ShieldCheck />
            <div>
              <strong>Grounded by design</strong>
              <p>Every answer links back to an IR entry and source page.</p>
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
                    <FileText />
                  </div>
                  <div>
                    <div className="project-kicker">
                      <span>Document IR</span>
                      <span className="verified-pill">
                        <ShieldCheck /> Source grounded
                      </span>
                    </div>
                    <h1>{bundle.project.name}</h1>
                    <div className="project-meta">
                      <span>{bundle.document.page_count} pages</span>
                      <i />
                      <span>{bundle.entries.length} atomic entries</span>
                      <i />
                      <span>{formatBytes(bundle.document.size_bytes)}</span>
                    </div>
                  </div>
                </div>

                <div className="project-actions">
                  <button className="id-chip" onClick={() => void copyProjectId()}>
                    <Hash />
                    <span>{bundle.project.id}</span>
                    {copied ? <Check /> : <Copy />}
                  </button>
                  <div className="view-toggle">
                    <button
                      className={mode === 'natural' ? 'active' : ''}
                      onClick={() => setMode('natural')}
                    >
                      <BookOpen /> Natural
                    </button>
                    <button
                      className={mode === 'raw' ? 'active' : ''}
                      onClick={() => setMode('raw')}
                    >
                      <Braces /> Raw IR
                    </button>
                  </div>
                </div>
              </div>

              <div className="ir-toolbar">
                <div>
                  <Database />
                  <span>Intermediate representation</span>
                  <span className="entry-count">{bundle.entries.length}</span>
                </div>
                <div className="category-row">
                  {categories.slice(0, 4).map((category) => (
                    <span key={category}>{category}</span>
                  ))}
                </div>
              </div>

              {mode === 'natural' ? (
                <div className="entry-list">
                  {bundle.entries.map((entry, index) => (
                    <article className="entry-card" key={entry.id}>
                      <div className="entry-index">{String(index + 1).padStart(2, '0')}</div>
                      <div className="entry-body">
                        <div className="entry-topline">
                          <span
                            className={`category category-${entry.content.category ?? 'context'}`}
                          >
                            {entry.content.category ?? 'fact'}
                          </span>
                          <code>{shortId(entry.id)}</code>
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
                              Source · Page {entry.content.source.page}
                            </div>
                            <blockquote>“{entry.content.source.quote}”</blockquote>
                          </div>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="raw-panel">
                  <div className="raw-header">
                    <span>project.ir.json</span>
                    <span>Schema validated</span>
                  </div>
                  <pre>{JSON.stringify(bundle.entries, null, 2)}</pre>
                </div>
              )}
            </>
          ) : (
            <EmptyState
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
                <p>Upload or select a document to ask grounded questions.</p>
              </div>
            ) : messages.length === 0 ? (
              <div className="chat-welcome">
                <div className="assistant-avatar">
                  <Sparkles />
                </div>
                <div className="assistant-intro">
                  <p>
                    I’m ready to answer questions about <strong>{bundle.project.name}</strong>.
                    Every factual answer will include its supporting IR entries.
                  </p>
                </div>
                <div className="suggestions">
                  <span>Try asking</span>
                  {[
                    'What are the key requirements?',
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
                            onClick={() => setMode('natural')}
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
                placeholder={bundle ? 'Ask about this project…' : 'Select a project to ask…'}
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
    </div>
  )
}

function EmptyState({
  onUpload,
  configured,
}: {
  onUpload: () => void
  configured: boolean
}) {
  return (
    <div className="empty-state">
      <div className="empty-visual">
        <div className="empty-sheet empty-sheet-back" />
        <div className="empty-sheet">
          <div className="sheet-icon">
            <FileText />
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
      <p className="eyebrow">Document → source of truth</p>
      <h1>Turn any document into grounded IR</h1>
      <p className="empty-description">
        Upload a PDF, presentation, document, or image. Mistral reads it, separates it
        into atomic facts, and gives you one stable ID to query.
      </p>
      <Button size="lg" onClick={onUpload} disabled={!configured}>
        <UploadCloud />
        Choose a document
      </Button>
      {!configured ? (
        <p className="configuration-note">
          Add <code>MISTRAL_API_KEY</code> to the backend before uploading.
        </p>
      ) : (
        <p className="file-note">PDF, DOCX, PPTX, PNG, JPG · up to 20 MB</p>
      )}
      <div className="empty-steps">
        <div>
          <span>01</span>
          <strong>Mistral OCR</strong>
          <p>Preserves page structure and source text.</p>
        </div>
        <div>
          <span>02</span>
          <strong>Atomic IR</strong>
          <p>Facts are validated against your schema.</p>
        </div>
        <div>
          <span>03</span>
          <strong>Grounded Q&A</strong>
          <p>Answers cite exact entries and pages.</p>
        </div>
      </div>
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
