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
  GitBranch,
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
import { AuthProvider } from '@/components/auth-provider'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/auth-context'
import { LoginPage } from '@/pages/login'
import { ProfilePage } from '@/pages/profile'
import { SignupPage } from '@/pages/signup'

type Source = {
  kind?: 'document' | 'message' | 'issue'
  page?: number | null
  quote: string
  document_id?: string
  filename?: string
  issue_id?: string
  proposal_id?: string
  version?: number
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
  project_id?: string
  filename: string
  mime_type: string
  size_bytes: number
  page_count: number
  created_at: string
  author?: string
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
  document_count: number
  created_at: string
  document: DocumentInfo | null
}

type ProjectBundle = {
  project: {
    id: string
    name: string
    ir: string[]
    documents: string[]
    users: string[]
    admins: string[]
    created_at: string
  }
  document: DocumentInfo | null
  documents: DocumentInfo[]
  entries: IREntry[]
  members: Profile[]
  conflict_review?: ConflictReview
}

type ConflictReview = {
  status: 'complete' | 'skipped'
  created_issue_ids: string[]
  reason?: string
}

type Profile = {
  id: string
  username?: string
  content: {
    name?: string
    discipline?: string
    expertise?: string
    history?: string
    preferences?: string
    context?: string
    description?: string
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
  filename?: string
  document_id?: string
  quote: string
}

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  insufficient?: boolean
}

type ProposalVersion = {
  version: number
  solution: string
  author: string
  created_at: string
}

type ProposalReview = {
  reviewer: string
  decision: 'approved' | 'rejected'
  comment: string
  version: number
  created_at: string
}

type IssueProposal = {
  id: string
  status: 'draft' | 'in_review' | 'approved' | 'rejected'
  contributors: string[]
  created_at: string
  versions: ProposalVersion[]
  reviews: ProposalReview[]
}

type ProjectIssue = {
  id: string
  project_id: string
  title: string
  summary: string
  required_expertise: string
  reviewer_ids: string[]
  participant_ids?: string[]
  origin?: 'manual' | 'automatic'
  conflict_type?:
    | 'contradiction'
    | 'requirement_violation'
    | 'decision_mismatch'
    | 'constraint_violation'
  source_entry_ids?: string[]
  status: 'open' | 'resolved'
  created_by: string
  created_at: string
  approved_proposal_id?: string
  resolution_entry_id?: string
  proposals: IssueProposal[]
}

type FeedGroup = {
  id: string
  kind: 'document' | 'message' | 'issue'
  title: string
  summary: string
  author: string
  created_at: string
  entries: IREntry[]
}

type ViewMode = 'lens' | 'ir' | 'issues' | 'raw'

const API_BASE = import.meta.env.VITE_API_URL ?? ''
const ACCEPTED_FILES = '.pdf,.docx,.pptx,.png,.jpg,.jpeg,.webp,.avif'

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...init,
  })
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

function buildFeedGroups(entries: IREntry[]): FeedGroup[] {
  const groups = new Map<string, FeedGroup>()
  for (const entry of entries) {
    const source = entry.content.source
    const kind = source?.kind ?? 'message'
    const id =
      kind === 'document'
        ? `document:${source?.document_id ?? source?.filename ?? entry.id}`
        : kind === 'issue'
          ? `issue:${source?.issue_id ?? entry.id}`
          : `message:${entry.author}:${entry.created_at}`
    const statement =
      entry.content.statement ?? 'A grounded project update was added.'
    const existing = groups.get(id)
    if (existing) {
      existing.entries.push(entry)
      continue
    }
    const issueName = entry.content.entities?.[0]
    groups.set(id, {
      id,
      kind,
      title:
        kind === 'document'
          ? `${source?.filename ?? 'Document'} added`
          : kind === 'issue'
            ? `Approved solution${issueName ? ` · ${issueName}` : ''}`
            : 'Project update',
      summary:
        statement.length > 180 ? `${statement.slice(0, 177)}…` : statement,
      author: entry.author,
      created_at: entry.created_at,
      entries: [entry],
    })
  }
  return Array.from(groups.values()).reverse()
}

function WorkspacePage() {
  const { profile: actingProfile, setProfile: setActingProfile } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [bundle, setBundle] = useState<ProjectBundle | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedProfileId, setSelectedProfileId] = useState(
    actingProfile?.id ?? '',
  )
  const [claims, setClaims] = useState<Claim[]>([])
  const [issues, setIssues] = useState<ProjectIssue[]>([])
  const [changes, setChanges] = useState<IREntry[]>([])
  const [expandedEntryId, setExpandedEntryId] = useState<string | null>(null)
  const [expandedFeedId, setExpandedFeedId] = useState<string | null>(null)
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
  const [automationNotice, setAutomationNotice] = useState<string | null>(null)
  const [mistralConfigured, setMistralConfigured] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [showProjectModal, setShowProjectModal] = useState(false)
  const [showJoinModal, setShowJoinModal] = useState(false)
  const [showMembersModal, setShowMembersModal] = useState(false)
  const [showIssueModal, setShowIssueModal] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [joinProjectId, setJoinProjectId] = useState('')
  const [memberToAdd, setMemberToAdd] = useState('')
  const [issueTitle, setIssueTitle] = useState('')
  const [issueSummary, setIssueSummary] = useState('')
  const [issueExpertise, setIssueExpertise] = useState('')
  const [issueReviewerId, setIssueReviewerId] = useState('')
  const [solutionTarget, setSolutionTarget] = useState<{
    issueId: string
    proposalId?: string
    baseVersion?: number
  } | null>(null)
  const [solutionText, setSolutionText] = useState('')
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
        setSelectedProfileId(actingProfile?.id ?? '')
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Could not load projects.')
      } finally {
        setLoadingLibrary(false)
      }
    }
    void initialise()
  }, [actingProfile?.id])

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
      setAutomationNotice(null)
      try {
        const [result, issueResult] = await Promise.all([
          apiRequest<ProjectBundle>(`/api/projects/${selectedId}`),
          apiRequest<{ issues: ProjectIssue[] }>(
            `/api/projects/${selectedId}/issues`,
          ),
        ])
        setBundle(result)
        setIssues(issueResult.issues)
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
        setIssues([])
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
    () =>
      new Map(
        [...profiles, ...(bundle?.members ?? [])].map((profile) => [
          profile.id,
          profile,
        ]),
      ),
    [bundle?.members, profiles],
  )
  const projectProfiles = useMemo(
    () =>
      (bundle?.project.users ?? [])
        .map((id) => profileById.get(id))
        .filter((profile): profile is Profile => Boolean(profile)),
    [bundle, profileById],
  )
  const availableProfiles = useMemo(
    () =>
      profiles.filter(
        (profile) =>
          !profile.content.system &&
          !(bundle?.project.users ?? []).includes(profile.id),
      ),
    [bundle?.project.users, profiles],
  )
  const selectedProfile = profileById.get(selectedProfileId)
  const feedGroups = useMemo(
    () => buildFeedGroups(bundle?.entries ?? []),
    [bundle?.entries],
  )
  const reviewerCandidates = projectProfiles.filter(
    (profile) => profile.id !== actingProfile?.id,
  )
  const documentPages = (bundle?.documents ?? []).reduce(
    (total, document) => total + document.page_count,
    0,
  )
  const documentBytes = (bundle?.documents ?? []).reduce(
    (total, document) => total + document.size_bytes,
    0,
  )

  const profileNameFor = (id?: string) =>
    (id &&
      (profileById.get(id)?.content.name ||
        profileById.get(id)?.username)) ||
    id ||
    'Unknown'

  const refreshProject = async (projectId: string) => {
    const result = await apiRequest<ProjectBundle>(`/api/projects/${projectId}`)
    setBundle(result)
    setProjects((current) => {
      const summary: ProjectSummary = {
        id: result.project.id,
        name: result.project.name,
        entry_count: result.entries.length,
        member_count: result.project.users.length,
        document_count: result.documents.length,
        created_at: result.project.created_at,
        document: result.document,
      }
      return current.some((project) => project.id === projectId)
        ? current.map((project) =>
            project.id === projectId ? summary : project,
          )
        : [summary, ...current]
    })
    return result
  }

  const applyConflictReview = async (
    projectId: string,
    review?: ConflictReview,
  ) => {
    if (!review) return
    if (review.status === 'skipped') {
      setAutomationNotice(
        'Change saved. Automatic conflict review is temporarily unavailable.',
      )
      return
    }
    const count = review.created_issue_ids.length
    setAutomationNotice(
      count
        ? `The model found ${count} direct ${count === 1 ? 'conflict' : 'conflicts'} and opened assigned ${count === 1 ? 'issue' : 'issues'}.`
        : 'Change saved. The model found no direct conflicts with the project IR.',
    )
    if (count) {
      const issueResult = await apiRequest<{ issues: ProjectIssue[] }>(
        `/api/projects/${projectId}/issues`,
      )
      setIssues(issueResult.issues)
      setMode('issues')
    }
  }

  const updateIssue = (issue: ProjectIssue) => {
    setIssues((current) =>
      current.some((item) => item.id === issue.id)
        ? current.map((item) => (item.id === issue.id ? issue : item))
        : [issue, ...current],
    )
  }

  const createIssue = async (event: FormEvent) => {
    event.preventDefault()
    if (
      !bundle ||
      !issueTitle.trim() ||
      !issueSummary.trim() ||
      !issueExpertise.trim() ||
      !issueReviewerId
    ) {
      return
    }
    setSavingModal(true)
    setError(null)
    try {
      const issue = await apiRequest<ProjectIssue>(
        `/api/projects/${bundle.project.id}/issues`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: issueTitle.trim(),
            summary: issueSummary.trim(),
            required_expertise: issueExpertise.trim(),
            reviewer_ids: [issueReviewerId],
          }),
        },
      )
      updateIssue(issue)
      setIssueTitle('')
      setIssueSummary('')
      setIssueExpertise('')
      setIssueReviewerId('')
      setShowIssueModal(false)
      setMode('issues')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not create issue.')
    } finally {
      setSavingModal(false)
    }
  }

  const saveSolution = async (event: FormEvent) => {
    event.preventDefault()
    if (!bundle || !solutionTarget || !solutionText.trim()) return
    setSavingModal(true)
    setError(null)
    try {
      const base = `/api/projects/${bundle.project.id}/issues/${solutionTarget.issueId}`
      const path = solutionTarget.proposalId
        ? `${base}/proposals/${solutionTarget.proposalId}/revisions`
        : `${base}/proposals`
      const issue = await apiRequest<ProjectIssue>(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          solution: solutionText.trim(),
          ...(solutionTarget.baseVersion
            ? { base_version: solutionTarget.baseVersion }
            : {}),
        }),
      })
      updateIssue(issue)
      setSolutionText('')
      setSolutionTarget(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save solution.')
    } finally {
      setSavingModal(false)
    }
  }

  const submitProposal = async (issueId: string, proposalId: string) => {
    if (!bundle) return
    setError(null)
    try {
      const issue = await apiRequest<ProjectIssue>(
        `/api/projects/${bundle.project.id}/issues/${issueId}/proposals/${proposalId}/submit`,
        { method: 'POST' },
      )
      updateIssue(issue)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not submit proposal.')
    }
  }

  const reviewProposal = async (
    issueId: string,
    proposalId: string,
    decision: 'approved' | 'rejected',
  ) => {
    if (!bundle) return
    const comment = window.prompt(
      decision === 'approved'
        ? 'Approval note (optional)'
        : 'What should the contributors change?',
      '',
    )
    if (comment === null) return
    setError(null)
    try {
      const issue = await apiRequest<
        ProjectIssue & { conflict_review?: ConflictReview }
      >(
        `/api/projects/${bundle.project.id}/issues/${issueId}/proposals/${proposalId}/review`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision, comment }),
        },
      )
      updateIssue(issue)
      if (decision === 'approved') {
        await refreshProject(bundle.project.id)
        await applyConflictReview(bundle.project.id, issue.conflict_review)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not review proposal.')
    }
  }

  const uploadFiles = async (files: File[]) => {
    if (!files.length) return
    setUploading(true)
    setError(null)
    setSidebarOpen(false)
    let projectId = bundle?.project.id
    const conflictReviews: ConflictReview[] = []
    try {
      let result: ProjectBundle | null = null
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        const path = projectId
          ? `/api/projects/${projectId}/documents`
          : '/api/documents'
        result = await apiRequest<ProjectBundle>(path, {
          method: 'POST',
          body: formData,
        })
        if (result.conflict_review) {
          conflictReviews.push(result.conflict_review)
        }
        projectId = result.project.id
      }
      if (!result) return
      const summary: ProjectSummary = {
        id: result.project.id,
        name: result.project.name,
        entry_count: result.entries.length,
        member_count: result.project.users.length,
        document_count: result.documents.length,
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
      setMode('ir')
      const createdIssueIds = conflictReviews.flatMap(
        (review) => review.created_issue_ids,
      )
      const mergedReview: ConflictReview = {
        status:
          !createdIssueIds.length &&
          conflictReviews.some((review) => review.status === 'skipped')
          ? 'skipped'
          : 'complete',
        created_issue_ids: createdIssueIds,
      }
      await applyConflictReview(result.project.id, mergedReview)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The upload failed.')
      if (projectId) {
        try {
          await refreshProject(projectId)
          setSelectedId(projectId)
        } catch {
          // Preserve the original upload error; a later reload will reconcile.
        }
      }
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const postUpdate = async (event: FormEvent) => {
    event.preventDefault()
    if (!bundle || !actingProfile || !updateText.trim() || posting) return
    setPosting(true)
    setError(null)
    try {
      const response = await apiRequest<{
        entries: IREntry[]
        conflict_review: ConflictReview
      }>(
        `/api/projects/${bundle.project.id}/messages`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: updateText.trim(),
          }),
        },
      )
      setUpdateText('')
      await refreshProject(bundle.project.id)
      setMode('ir')
      await applyConflictReview(bundle.project.id, response.conflict_review)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not add that update.')
    } finally {
      setPosting(false)
    }
  }

  const createProject = async (event: FormEvent) => {
    event.preventDefault()
    if (!projectName.trim()) return
    setSavingModal(true)
    try {
      const project = await apiRequest<ProjectBundle['project']>('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projectName.trim(),
        }),
      })
      const summary: ProjectSummary = {
        id: project.id,
        name: project.name,
        entry_count: 0,
        member_count: 1,
        document_count: 0,
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

  const joinProject = async (event: FormEvent) => {
    event.preventDefault()
    const projectId = joinProjectId.trim()
    if (!projectId) return
    setSavingModal(true)
    setError(null)
    try {
      const result = await apiRequest<ProjectBundle>(
        `/api/projects/${encodeURIComponent(projectId)}/join`,
        {
        method: 'POST',
        },
      )
      const summary: ProjectSummary = {
        id: result.project.id,
        name: result.project.name,
        entry_count: result.entries.length,
        member_count: result.project.users.length,
        document_count: result.documents.length,
        created_at: result.project.created_at,
        document: result.document,
      }
      setProjects((current) => [
        summary,
        ...current.filter((project) => project.id !== summary.id),
      ])
      setJoinProjectId('')
      setShowJoinModal(false)
      setSelectedId(result.project.id)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not join project.')
    } finally {
      setSavingModal(false)
    }
  }

  const promoteMember = async (userId: string) => {
    if (!bundle) return
    setError(null)
    try {
      await apiRequest(`/api/projects/${bundle.project.id}/promote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      })
      await refreshProject(bundle.project.id)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not promote member.')
    }
  }

  const addMember = async () => {
    if (!bundle || !memberToAdd) return
    setError(null)
    try {
      const result = await apiRequest<ProjectBundle>(
        `/api/projects/${bundle.project.id}/members`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: memberToAdd }),
        },
      )
      setBundle(result)
      setMemberToAdd('')
      setProjects((current) =>
        current.map((project) =>
          project.id === result.project.id
            ? { ...project, member_count: result.project.users.length }
            : project,
        ),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not add member.')
    }
  }

  const removeMember = async (userId: string) => {
    if (!bundle) return
    setError(null)
    try {
      const result = await apiRequest<ProjectBundle>(
        `/api/projects/${bundle.project.id}/members/${userId}`,
        { method: 'DELETE' },
      )
      setBundle(result)
      if (!result.project.users.includes(selectedProfileId)) {
        setSelectedProfileId(actingProfile?.id ?? result.project.users[0] ?? '')
      }
      setProjects((current) =>
        current.map((project) =>
          project.id === result.project.id
            ? { ...project, member_count: result.project.users.length }
            : project,
        ),
      )
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not remove member.')
    }
  }

  const exitProject = async () => {
    if (!bundle) return
    setError(null)
    try {
      await apiRequest(`/api/projects/${bundle.project.id}/exit`, {
        method: 'POST',
      })
      setProjects((current) =>
        current.filter((project) => project.id !== bundle.project.id),
      )
      setBundle(null)
      setSelectedId(null)
      setShowMembersModal(false)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not exit project.')
    }
  }

  const handleLogout = async () => {
    await apiRequest('/api/logout', { method: 'POST' })
    setActingProfile(null)
    window.location.assign('/login')
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
    void uploadFiles(Array.from(event.target.files ?? []))
  }

  const onDrop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault()
    setDragging(false)
    void uploadFiles(Array.from(event.dataTransfer.files))
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
            multiple
            hidden
            onChange={onFileChange}
          />
          <div className="sidebar-actions">
            <button
              className="new-project-button"
              onClick={() => setShowProjectModal(true)}
            >
              <Plus />
              New project
            </button>
            <button
              className="icon-upload-button"
              aria-label="Join a project"
              title="Join a project"
              onClick={() => setShowJoinModal(true)}
            >
              <Users />
            </button>
            <button
              className="icon-upload-button"
              aria-label="Add documents"
              title={
                bundle
                  ? `Add documents to ${bundle.project.name}`
                  : 'Create a project from documents'
              }
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
                      {project.entry_count} entries · {project.document_count}{' '}
                      {project.document_count === 1 ? 'file' : 'files'} ·{' '}
                      {project.member_count} members
                    </small>
                  </span>
                  <ChevronRight className="document-arrow" />
                </button>
              ))
            )}
          </div>

          <button
            className="profile-card"
            onClick={() => window.location.assign('/profile')}
          >
            <span>
              <UserRound />
            </span>
            <div>
              <small>Signed in as</small>
              <strong>{profileNameFor(actingProfile?.id)}</strong>
            </div>
            <ChevronRight />
          </button>
          <button className="sidebar-logout" onClick={() => void handleLogout()}>
            Log out
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
              <strong>Drop files to update the IR</strong>
              <span>
                Mistral will add every grounded fact to{' '}
                {bundle?.project.name ?? 'one new project'}
              </span>
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
                    {bundle.documents.length ? <FileText /> : <Users />}
                  </div>
                  <div>
                    <div className="project-kicker">
                      <span>
                        {bundle.documents.length
                          ? 'Document-backed project'
                          : 'Shared project'}
                      </span>
                      <span className="verified-pill">
                        <ShieldCheck /> Grounded IR
                      </span>
                    </div>
                    <h1>{bundle.project.name}</h1>
                    <div className="project-meta">
                      <span>{bundle.entries.length} atomic entries</span>
                      <i />
                      <span>{bundle.project.users.length} members</span>
                      {!!bundle.documents.length && (
                        <>
                          <i />
                          <span>
                            {bundle.documents.length}{' '}
                            {bundle.documents.length === 1 ? 'file' : 'files'} ·{' '}
                            {documentPages} pages · {formatBytes(documentBytes)}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="project-actions">
                  <button
                    className="id-chip"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading || !mistralConfigured}
                  >
                    <UploadCloud />
                    <span>Add files</span>
                  </button>
                  <button
                    className="id-chip"
                    onClick={() => setShowMembersModal(true)}
                  >
                    <Users />
                    <span>
                      {bundle.project.users.length}{' '}
                      {bundle.project.users.length === 1 ? 'member' : 'members'}
                    </span>
                  </button>
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
                      className={mode === 'issues' ? 'active' : ''}
                      onClick={() => setMode('issues')}
                    >
                      <GitBranch /> Issues
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

              {!!bundle.documents.length && (
                <div className="project-documents">
                  <div>
                    <FileText />
                    <strong>Project files</strong>
                  </div>
                  <div>
                    {bundle.documents.map((document) => (
                      <span key={document.id} title={document.filename}>
                        {document.filename}
                      </span>
                    ))}
                  </div>
                </div>
              )}

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

              {automationNotice && (
                <div className="automation-banner">
                  <Sparkles />
                  <div>
                    <strong>Automatic conflict review</strong>
                    <span>{automationNotice}</span>
                  </div>
                  <button onClick={() => setAutomationNotice(null)}>Dismiss</button>
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
                      {profileNameFor(actingProfile?.id).slice(0, 1)}
                    </div>
                    <div className="composer-main">
                      <div className="composer-label">
                        <strong>{profileNameFor(actingProfile?.id)}</strong>
                        <span>Share an update in your own language</span>
                      </div>
                      <textarea
                        rows={2}
                        value={updateText}
                        disabled={!actingProfile || posting || !mistralConfigured}
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
                      <span>Project feed · Short updates</span>
                      <span className="entry-count">{feedGroups.length}</span>
                    </div>
                    <span className="lens-context">
                      Ask the IR for details
                    </span>
                  </div>
                  {feedGroups.length ? (
                    <div className="compact-feed">
                      {feedGroups.map((group) => (
                        <CompactFeedCard
                          key={group.id}
                          group={group}
                          authorName={profileNameFor(group.author)}
                          expanded={
                            expandedFeedId === group.id ||
                            group.entries.some(
                              (entry) => entry.id === expandedEntryId,
                            )
                          }
                          onToggle={() => {
                            setExpandedEntryId(null)
                            setExpandedFeedId((current) =>
                              current === group.id ? null : group.id,
                            )
                          }}
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
              ) : mode === 'issues' ? (
                <IssuesView
                  issues={issues}
                  entries={bundle.entries}
                  actingUserId={actingProfile?.id ?? ''}
                  profileNameFor={profileNameFor}
                  onCreate={() => setShowIssueModal(true)}
                  onPropose={(issueId) => {
                    setSolutionText('')
                    setSolutionTarget({ issueId })
                  }}
                  onRevise={(issueId, proposal) => {
                    setSolutionText(
                      proposal.versions[proposal.versions.length - 1]
                        ?.solution ?? '',
                    )
                    setSolutionTarget({
                      issueId,
                      proposalId: proposal.id,
                      baseVersion:
                        proposal.versions[proposal.versions.length - 1]
                          ?.version,
                    })
                  }}
                  onSubmit={(issueId, proposalId) =>
                    void submitProposal(issueId, proposalId)
                  }
                  onReview={(issueId, proposalId, decision) =>
                    void reviewProposal(issueId, proposalId, decision)
                  }
                />
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
              onCreate={() => setShowProjectModal(true)}
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
                            {citation.filename ? ` · ${citation.filename}` : ''}
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
            <p>
              You become the project’s first member and administrator.
            </p>
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

      {showJoinModal && (
        <Modal title="Join a project" onClose={() => setShowJoinModal(false)}>
          <form className="modal-form" onSubmit={joinProject}>
            <label>
              Project ID
              <input
                autoFocus
                value={joinProjectId}
                placeholder="prj_…"
                onChange={(event) => setJoinProjectId(event.target.value)}
              />
            </label>
            <p>Ask a teammate for the project ID shown in their project header.</p>
            <div className="modal-actions">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowJoinModal(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!joinProjectId.trim() || savingModal}
              >
                {savingModal && <LoaderCircle className="spin" />}
                Join project
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {showIssueModal && (
        <Modal title="Open an issue" onClose={() => setShowIssueModal(false)}>
          <form className="modal-form" onSubmit={createIssue}>
            <label>
              Issue
              <input
                autoFocus
                value={issueTitle}
                placeholder="e.g. Sensor false positives"
                onChange={(event) => setIssueTitle(event.target.value)}
              />
            </label>
            <label>
              Short context
              <textarea
                rows={3}
                value={issueSummary}
                placeholder="What is wrong, and what outcome is needed?"
                onChange={(event) => setIssueSummary(event.target.value)}
              />
            </label>
            <label>
              Expertise required
              <input
                value={issueExpertise}
                placeholder="e.g. Signal processing and clinical validation"
                onChange={(event) => setIssueExpertise(event.target.value)}
              />
            </label>
            <label>
              Independent expert reviewer
              <select
                value={issueReviewerId}
                onChange={(event) => setIssueReviewerId(event.target.value)}
              >
                <option value="">Choose a member…</option>
                {reviewerCandidates.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.content.name ?? profile.username ?? profile.id}
                    {profile.content.expertise ?? profile.content.description
                      ? ` — ${
                          profile.content.expertise ?? profile.content.description
                        }`
                      : ''}
                  </option>
                ))}
              </select>
            </label>
            <p>
              Reviewers stay independent: they can approve or reject, but cannot
              contribute revisions to this issue.
            </p>
            <div className="modal-actions">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowIssueModal(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={
                  !issueTitle.trim() ||
                  !issueSummary.trim() ||
                  !issueExpertise.trim() ||
                  !issueReviewerId ||
                  savingModal
                }
              >
                {savingModal && <LoaderCircle className="spin" />}
                Open issue
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {solutionTarget && (
        <Modal
          title={
            solutionTarget.proposalId
              ? 'Contribute a revision'
              : 'Propose a solution'
          }
          onClose={() => setSolutionTarget(null)}
        >
          <form className="modal-form" onSubmit={saveSolution}>
            <label>
              Proposed solution
              <textarea
                autoFocus
                rows={8}
                value={solutionText}
                placeholder="Describe the change, trade-offs, and how the team can verify it…"
                onChange={(event) => setSolutionText(event.target.value)}
              />
            </label>
            <p>
              Saving creates an immutable revision. Other members can build on it
              before a contributor submits it for expert review.
            </p>
            <div className="modal-actions">
              <Button
                type="button"
                variant="outline"
                onClick={() => setSolutionTarget(null)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!solutionText.trim() || savingModal}
              >
                {savingModal && <LoaderCircle className="spin" />}
                Save revision
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {showMembersModal && bundle && (
        <Modal
          title={`${bundle.project.name} members`}
          onClose={() => setShowMembersModal(false)}
        >
          {actingProfile &&
            bundle.project.admins.includes(actingProfile.id) && (
              <div className="member-add">
                <select
                  value={memberToAdd}
                  onChange={(event) => setMemberToAdd(event.target.value)}
                  disabled={!availableProfiles.length}
                >
                  <option value="">
                    {availableProfiles.length
                      ? 'Choose a person…'
                      : 'Everyone is already a member'}
                  </option>
                  {availableProfiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.content.name ?? profile.username ?? profile.id}
                      {profile.username ? ` (@${profile.username})` : ''}
                    </option>
                  ))}
                </select>
                <Button
                  disabled={!memberToAdd}
                  onClick={() => void addMember()}
                >
                  <Plus /> Add person
                </Button>
              </div>
            )}
          <div className="member-list">
            {projectProfiles.map((member) => {
              const isAdmin = bundle.project.admins.includes(member.id)
              const canManage =
                actingProfile !== null &&
                bundle.project.admins.includes(actingProfile.id)
              const canPromote = canManage && !isAdmin
              const canRemove = canManage && member.id !== actingProfile?.id
              return (
                <div className="member-row" key={member.id}>
                  <span className="member-avatar">
                    {(
                      member.content.name ??
                      member.username ??
                      '?'
                    ).slice(0, 1)}
                  </span>
                  <div>
                    <strong>
                      {member.content.name ?? member.username ?? member.id}
                    </strong>
                    <small>
                      @{member.username ?? member.id}
                      {isAdmin ? ' · Admin' : ' · Member'}
                    </small>
                  </div>
                  <div className="member-actions">
                    {canPromote && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => void promoteMember(member.id)}
                      >
                        Promote
                      </Button>
                    )}
                    {canRemove && (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => void removeMember(member.id)}
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
          <div className="member-modal-footer">
            <p>
              If the last admin exits, another member is automatically promoted.
            </p>
            <Button variant="destructive" onClick={() => void exitProject()}>
              Exit project
            </Button>
          </div>
        </Modal>
      )}
    </div>
  )
}

function CompactFeedCard({
  group,
  authorName,
  expanded,
  onToggle,
}: {
  group: FeedGroup
  authorName: string
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <article className="compact-update">
      <div className={`compact-update-icon compact-update-${group.kind}`}>
        {group.kind === 'document' ? (
          <FileText />
        ) : group.kind === 'issue' ? (
          <Check />
        ) : (
          <MessageSquare />
        )}
      </div>
      <div className="compact-update-body">
        <div className="compact-update-head">
          <strong>{group.title}</strong>
          <span>
            {authorName} · {formatDate(group.created_at)}
          </span>
        </div>
        <p>{group.summary}</p>
        <button className="compact-detail-toggle" onClick={onToggle}>
          {group.entries.length}{' '}
          {group.entries.length === 1 ? 'grounded fact' : 'grounded facts'} ·{' '}
          {expanded ? 'Hide details' : 'Show details'}
        </button>
        {expanded && (
          <div className="compact-details">
            {group.entries.map((entry, index) => (
              <IREntryCard
                key={entry.id}
                entry={entry}
                index={index}
                authorName={authorName}
              />
            ))}
          </div>
        )}
      </div>
    </article>
  )
}

function IssuesView({
  issues,
  entries,
  actingUserId,
  profileNameFor,
  onCreate,
  onPropose,
  onRevise,
  onSubmit,
  onReview,
}: {
  issues: ProjectIssue[]
  entries: IREntry[]
  actingUserId: string
  profileNameFor: (id?: string) => string
  onCreate: () => void
  onPropose: (issueId: string) => void
  onRevise: (issueId: string, proposal: IssueProposal) => void
  onSubmit: (issueId: string, proposalId: string) => void
  onReview: (
    issueId: string,
    proposalId: string,
    decision: 'approved' | 'rejected',
  ) => void
}) {
  const entriesById = new Map(entries.map((entry) => [entry.id, entry]))
  return (
    <div className="issues-view">
      <div className="issues-toolbar">
        <div>
          <GitBranch />
          <div>
            <strong>Issues and solution branches</strong>
            <span>Collaborate in revisions, then request independent review.</span>
          </div>
        </div>
        <Button onClick={onCreate}>
          <Plus /> Open issue
        </Button>
      </div>

      {!issues.length ? (
        <div className="feed-empty">
          <GitBranch />
          <h3>No open issues</h3>
          <p>Open an issue when a decision needs collaborative, expert review.</p>
        </div>
      ) : (
        <div className="issue-list">
          {issues.map((issue) => {
            const isReviewer = issue.reviewer_ids.includes(actingUserId)
            const participants = issue.participant_ids ?? []
            const isParticipant =
              !participants.length || participants.includes(actingUserId)
            return (
              <article className="issue-card" key={issue.id}>
                <div className="issue-head">
                  <div>
                    <span className={`issue-status issue-status-${issue.status}`}>
                      {issue.status}
                    </span>
                    {issue.origin === 'automatic' && (
                      <span className="issue-auto-status">
                        <Sparkles /> Model detected
                      </span>
                    )}
                    <code>{issue.id.replace('iss_', 'ISS-').toUpperCase()}</code>
                  </div>
                  <span>{formatDate(issue.created_at)}</span>
                </div>
                <h2>{issue.title}</h2>
                <p className="issue-summary">{issue.summary}</p>
                <div className="issue-expertise">
                  <ShieldCheck />
                  <span>
                    Needs <strong>{issue.required_expertise}</strong> · reviewer{' '}
                    {issue.reviewer_ids.map(profileNameFor).join(', ')}
                  </span>
                </div>
                {!!participants.length && (
                  <div className="issue-assignment">
                    <Users />
                    <span>
                      Participants: {participants.map(profileNameFor).join(', ')}
                    </span>
                  </div>
                )}
                {issue.origin === 'automatic' && (
                  <div className="issue-evidence">
                    <CircleAlert />
                    <span>
                      {issue.conflict_type?.replaceAll('_', ' ')} · grounded in{' '}
                      {issue.source_entry_ids?.length ?? 0} IR entries
                    </span>
                  </div>
                )}
                {!!issue.source_entry_ids?.length && (
                  <details className="issue-source-evidence">
                    <summary>Review conflict evidence</summary>
                    {issue.source_entry_ids.map((entryId) => {
                      const entry = entriesById.get(entryId)
                      return (
                        <div key={entryId}>
                          <code>{entryId}</code>
                          <p>
                            {entry?.content.statement ?? 'IR entry is unavailable.'}
                          </p>
                        </div>
                      )
                    })}
                  </details>
                )}

                {issue.status === 'open' && !isReviewer && isParticipant && (
                  <Button
                    className="issue-propose-button"
                    variant="outline"
                    onClick={() => onPropose(issue.id)}
                  >
                    <GitBranch /> Start a solution branch
                  </Button>
                )}

                <div className="proposal-list">
                  {issue.proposals.map((proposal) => {
                    const current =
                      proposal.versions[proposal.versions.length - 1]
                    const isContributor = proposal.contributors.includes(actingUserId)
                    const canRevise =
                      issue.status === 'open' &&
                      !isReviewer &&
                      isParticipant &&
                      ['draft', 'rejected'].includes(proposal.status)
                    return (
                      <section className="proposal-card" key={proposal.id}>
                        <div className="proposal-head">
                          <div>
                            <GitBranch />
                            <strong>Solution branch</strong>
                            <code>{proposal.id.replace('prop_', 'PR-').toUpperCase()}</code>
                          </div>
                          <span className={`proposal-status proposal-${proposal.status}`}>
                            {proposal.status.replace('_', ' ')}
                          </span>
                        </div>
                        <p className="proposal-solution">{current?.solution}</p>
                        <div className="proposal-meta">
                          <span>
                            v{current?.version} · {proposal.versions.length}{' '}
                            {proposal.versions.length === 1 ? 'revision' : 'revisions'}
                          </span>
                          <span>
                            Contributors:{' '}
                            {proposal.contributors.map(profileNameFor).join(', ')}
                          </span>
                        </div>
                        {proposal.versions.length > 1 && (
                          <details className="proposal-history">
                            <summary>Revision history</summary>
                            {proposal.versions
                              .slice()
                              .reverse()
                              .map((version) => (
                                <div key={`${proposal.id}-v${version.version}`}>
                                  <strong>
                                    v{version.version} · {profileNameFor(version.author)}
                                  </strong>
                                  <span>{formatDate(version.created_at)}</span>
                                  <p>{version.solution}</p>
                                </div>
                              ))}
                          </details>
                        )}
                        {!!proposal.reviews.length && (
                          <div className="proposal-reviews">
                            {proposal.reviews.map((review, index) => (
                              <div key={`${proposal.id}-review-${index}`}>
                                <strong>
                                  {review.decision === 'approved' ? 'Approved' : 'Changes requested'}
                                  {' '}by {profileNameFor(review.reviewer)} on v{review.version}
                                </strong>
                                {review.comment && <p>{review.comment}</p>}
                              </div>
                            ))}
                          </div>
                        )}
                        {issue.status === 'open' && (
                          <div className="proposal-actions">
                            {canRevise && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => onRevise(issue.id, proposal)}
                              >
                                Contribute revision
                              </Button>
                            )}
                            {isContributor && proposal.status === 'draft' && (
                              <Button
                                size="sm"
                                onClick={() => onSubmit(issue.id, proposal.id)}
                              >
                                Submit for review
                              </Button>
                            )}
                            {isReviewer && proposal.status === 'in_review' && (
                              <>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() =>
                                    onReview(issue.id, proposal.id, 'rejected')
                                  }
                                >
                                  Request changes
                                </Button>
                                <Button
                                  size="sm"
                                  onClick={() =>
                                    onReview(issue.id, proposal.id, 'approved')
                                  }
                                >
                                  <Check /> Approve
                                </Button>
                              </>
                            )}
                          </div>
                        )}
                      </section>
                    )
                  })}
                </div>
              </article>
            )
          })}
        </div>
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
                : entry.content.source.kind === 'issue'
                  ? `Approved issue proposal · v${
                      entry.content.source.version ?? '—'
                    }`
                : `${
                    entry.content.source.filename ?? 'Document'
                  } · Page ${entry.content.source.page ?? '—'}`}
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

function AppRoutes() {
  const { profile, loading } = useAuth()
  const path = window.location.pathname

  if (loading) return <LoadingProject />
  if (!profile) {
    return path === '/signup' ? <SignupPage /> : <LoginPage />
  }
  if (path === '/profile') return <ProfilePage />
  return <WorkspacePage />
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App
