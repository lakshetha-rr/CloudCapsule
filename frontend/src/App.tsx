import { useCallback, useEffect, useState } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000'

type ModuleStatus = 'registered' | 'deploying' | 'running' | 'stopped' | 'failed'
type Environment = 'development' | 'staging' | 'demo'
type LifecycleAction = 'deploy' | 'stop' | 'restart'
type NetworkAccess = 'internal' | 'public'

interface Module {
  id: number
  name: string
  description: string
  environment: Environment
  status: ModuleStatus
  design_version: string
  deployment_model: 'container'
  cpu_units: number
  memory_mb: number
  min_replicas: number
  max_replicas: number
  health_check_path: string
  network_access: NetworkAccess
  backup_enabled: boolean
  design_spec: Record<string, unknown>
  created_at: string
}

interface ModuleEvent {
  id: number
  module_id: number
  action: string
  previous_status: string
  new_status: string
  result: string
  details: string
  created_at: string
}

interface HealthResponse {
  status: string
  database: string
}

interface ApiError {
  detail?: string | { msg?: string }[]
}

interface ModuleForm {
  name: string
  description: string
  environment: Environment
  design_version: string
  deployment_model: 'container'
  cpu_units: number
  memory_mb: number
  min_replicas: number
  max_replicas: number
  health_check_path: string
  network_access: NetworkAccess
  backup_enabled: boolean
}

const initialForm: ModuleForm = {
  name: '',
  description: '',
  environment: 'development',
  design_version: '1.0.0',
  deployment_model: 'container',
  cpu_units: 256,
  memory_mb: 512,
  min_replicas: 1,
  max_replicas: 2,
  health_check_path: '/health',
  network_access: 'internal',
  backup_enabled: false,
}

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as ApiError
    const detail = Array.isArray(error.detail)
      ? error.detail.map((item) => item.msg ?? 'Invalid input').join('; ')
      : error.detail
    throw new Error(detail || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>
}

function App() {
  const [modules, setModules] = useState<Module[]>([])
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [events, setEvents] = useState<ModuleEvent[]>([])
  const [selectedModule, setSelectedModule] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busyAction, setBusyAction] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [search, setSearch] = useState('')
  const [environmentFilter, setEnvironmentFilter] = useState('all')
  const [form, setForm] = useState<ModuleForm>({ ...initialForm })

  const loadDashboard = useCallback(async () => {
    setError('')
    try {
      const [moduleData, healthData] = await Promise.all([
        apiRequest<Module[]>('/modules'),
        apiRequest<HealthResponse>('/health/database'),
      ])
      setModules(moduleData)
      setHealth(healthData)
      setSelectedModule((current) =>
        current !== null && moduleData.some((item) => item.id === current)
          ? current
          : moduleData[0]?.id ?? null,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load dashboard')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadEvents = useCallback(async (moduleId: number) => {
    try {
      setEvents(await apiRequest<ModuleEvent[]>(`/modules/${moduleId}/events`))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load audit history')
      setEvents([])
    }
  }, [])

  useEffect(() => { void loadDashboard() }, [loadDashboard])
  useEffect(() => {
    if (selectedModule !== null) void loadEvents(selectedModule)
    else setEvents([])
  }, [selectedModule, loadEvents])

  const counts = {
    total: modules.length,
    running: modules.filter((item) => item.status === 'running').length,
    stopped: modules.filter((item) => item.status === 'stopped').length,
    attention: modules.filter((item) => item.status === 'failed').length,
  }

  const filteredModules = modules.filter((item) => {
    const matchesSearch =
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.description.toLowerCase().includes(search.toLowerCase())
    return matchesSearch && (environmentFilter === 'all' || item.environment === environmentFilter)
  })
  const activeModule = modules.find((item) => item.id === selectedModule)

  async function createModule(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusyAction('create')
    setError('')
    setNotice('')
    try {
      const created = await apiRequest<Module>('/modules', {
        method: 'POST',
        body: JSON.stringify({ ...form, design_spec: {} }),
      })
      setNotice(`Module "${created.name}" created successfully.`)
      setForm({ ...initialForm })
      setShowCreateForm(false)
      await loadDashboard()
      setSelectedModule(created.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create module')
    } finally {
      setBusyAction('')
    }
  }

  async function runAction(module: Module, action: LifecycleAction) {
    setBusyAction(`${module.id}-${action}`)
    setError('')
    setNotice('')
    try {
      await apiRequest(`/modules/${module.id}/actions`, {
        method: 'POST',
        body: JSON.stringify({ action }),
      })
      setNotice(`${action[0].toUpperCase()}${action.slice(1)} request completed for ${module.name}.`)
      await loadDashboard()
      await loadEvents(module.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lifecycle action failed')
      await loadDashboard()
      await loadEvents(module.id)
    } finally {
      setBusyAction('')
    }
  }

  const setField = <K extends keyof ModuleForm>(key: K, value: ModuleForm[K]) =>
    setForm((current) => ({ ...current, [key]: value }))

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="CloudCapsule home">
          <span className="brand-mark">C</span><span>CloudCapsule</span>
        </a>
        <div className="sidebar-label">WORKSPACE</div>
        <nav className="side-nav">
          <a className="nav-link active" href="#overview"><span>◫</span> Overview</a>
          <a className="nav-link" href="#modules"><span>▦</span> Modules</a>
          <a className="nav-link" href="#activity"><span>↗</span> Activity</a>
        </nav>
        <div className="sidebar-bottom">
          <div className="environment-card"><span className="live-dot" /><div><strong>Local environment</strong><small>AWS deployment disabled</small></div></div>
          <div className="sidebar-footer">CLOUDCAPSULE <span>v0.6.0</span></div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div><div className="breadcrumb">Workspace <span>/</span> Overview</div><div className="topbar-subtitle">Cloud infrastructure, under control.</div></div>
          <div className="topbar-actions">
            <span className={`connection-pill ${health?.status === 'healthy' ? 'connected' : ''}`}><span className="live-dot" />{health?.status === 'healthy' ? 'API connected' : 'Checking API'}</span>
            <button className="button button-primary" onClick={() => setShowCreateForm(true)}><span>＋</span> New module</button>
          </div>
        </header>

        <section id="overview" className="page-heading">
          <div><div className="eyebrow">OVERVIEW</div><h1>Your infrastructure</h1><p>Design, register and manage modules from one place.</p></div>
          <button className="button button-secondary" onClick={() => void loadDashboard()}>↻ Refresh</button>
        </section>

        {error && <div className="alert alert-error" role="alert"><strong>Something needs attention</strong><span>{error}</span>{error.toLowerCase().includes('fetch') && <small>Confirm Docker Compose is running and the API is available at localhost:8000.</small>}<button onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
        {notice && <div className="alert alert-success" role="status"><span>✓ {notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss message">×</button></div>}

        <section className="metrics-grid" aria-label="Module summary">
          <article className="metric-card"><div className="metric-top"><span>Total modules</span><span className="metric-icon blue">▦</span></div><div className="metric-value">{loading ? '—' : counts.total}</div><div className="metric-caption">Registered in CloudCapsule</div></article>
          <article className="metric-card"><div className="metric-top"><span>Running</span><span className="metric-icon green">↗</span></div><div className="metric-value">{loading ? '—' : counts.running}</div><div className="metric-caption"><span className="status-dot green-dot" /> Active simulated modules</div></article>
          <article className="metric-card"><div className="metric-top"><span>Stopped</span><span className="metric-icon amber">Ⅱ</span></div><div className="metric-value">{loading ? '—' : counts.stopped}</div><div className="metric-caption">Available to restart</div></article>
          <article className="metric-card"><div className="metric-top"><span>Needs attention</span><span className="metric-icon red">!</span></div><div className="metric-value">{loading ? '—' : counts.attention}</div><div className="metric-caption">Modules in failed state</div></article>
        </section>

        <section className="service-strip">
          <div className="service-leading"><div className="service-icon">⌘</div><div><strong>Local services</strong><span>Development environment status</span></div></div>
          <div className="service-status"><span className={`status-dot ${health?.status === 'healthy' ? 'green-dot' : 'amber-dot'}`} /><div><strong>PostgreSQL</strong><span>{health?.database ?? 'Checking connection'}</span></div></div>
          <div className="service-status"><span className={`status-dot ${health?.status === 'healthy' ? 'green-dot' : 'amber-dot'}`} /><div><strong>FastAPI</strong><span>{health?.status ?? 'Checking connection'}</span></div></div>
          <span className="local-tag">LOCAL ONLY</span>
        </section>

        {showCreateForm && (
          <section className="panel create-panel">
            <div className="panel-header"><div><h2>Create a module</h2><p>Register a module and define its deployment design.</p></div><button className="icon-button" onClick={() => setShowCreateForm(false)} aria-label="Close form">×</button></div>
            <form className="module-form" onSubmit={createModule}>
              <label>Module name<input required minLength={2} maxLength={100} value={form.name} onChange={(e) => setField('name', e.target.value)} placeholder="e.g. payments-service" /></label>
              <label>Environment<select value={form.environment} onChange={(e) => setField('environment', e.target.value as Environment)}><option value="development">Development</option><option value="staging">Staging</option><option value="demo">Demo</option></select></label>
              <label className="form-full">Description<textarea maxLength={1000} rows={2} value={form.description} onChange={(e) => setField('description', e.target.value)} placeholder="What does this module do?" /></label>

              <div className="form-full"><h3>Deployment design</h3><p>These are saved design settings only; they do not provision AWS resources.</p></div>
              <label>Design version<input required maxLength={30} value={form.design_version} onChange={(e) => setField('design_version', e.target.value)} /></label>
              <label>Deployment model<select value={form.deployment_model} onChange={() => setField('deployment_model', 'container')}><option value="container">Container</option></select></label>
              <label>CPU units<select value={form.cpu_units} onChange={(e) => setField('cpu_units', Number(e.target.value))}><option value={256}>256</option><option value={512}>512</option><option value={1024}>1024</option><option value={2048}>2048</option><option value={4096}>4096</option></select></label>
              <label>Memory (MB)<select value={form.memory_mb} onChange={(e) => setField('memory_mb', Number(e.target.value))}><option value={512}>512</option><option value={1024}>1024</option><option value={2048}>2048</option><option value={4096}>4096</option><option value={8192}>8192</option><option value={16384}>16384</option><option value={32768}>32768</option></select></label>
              <label>Minimum replicas<input type="number" min={0} max={100} required value={form.min_replicas} onChange={(e) => setField('min_replicas', Number(e.target.value))} /></label>
              <label>Maximum replicas<input type="number" min={1} max={100} required value={form.max_replicas} onChange={(e) => setField('max_replicas', Number(e.target.value))} /></label>
              <label>Health-check path<input required maxLength={200} pattern="/.*" title="Must start with /" value={form.health_check_path} onChange={(e) => setField('health_check_path', e.target.value)} /></label>
              <label>Network access<select value={form.network_access} onChange={(e) => setField('network_access', e.target.value as NetworkAccess)}><option value="internal">Internal only</option><option value="public">Public</option></select></label>
              <label className="form-full checkbox-label"><input type="checkbox" checked={form.backup_enabled} onChange={(e) => setField('backup_enabled', e.target.checked)} /> Enable backup in the design specification</label>
              {form.min_replicas > form.max_replicas && <p className="form-full" role="alert">Minimum replicas cannot exceed maximum replicas.</p>}
              <div className="form-actions"><button type="button" className="button button-secondary" onClick={() => setShowCreateForm(false)}>Cancel</button><button type="submit" className="button button-primary" disabled={busyAction === 'create' || form.min_replicas > form.max_replicas}>{busyAction === 'create' ? 'Creating…' : 'Create module'}</button></div>
            </form>
          </section>
        )}

        <section id="modules" className="panel modules-panel">
          <div className="panel-header"><div><h2>Modules</h2><p>Your registered applications and their current state.</p></div><span className="record-count">{filteredModules.length} records</span></div>
          <div className="table-toolbar">
            <label className="search-box"><span>⌕</span><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search modules…" /></label>
            <select value={environmentFilter} onChange={(e) => setEnvironmentFilter(e.target.value)} aria-label="Filter environment"><option value="all">All environments</option><option value="development">Development</option><option value="staging">Staging</option><option value="demo">Demo</option></select>
          </div>
          {loading ? <div className="empty-state"><span className="spinner" /> Loading modules…</div> : filteredModules.length === 0 ? (
            <div className="empty-state"><div className="empty-icon">▦</div><strong>{modules.length ? 'No matching modules' : 'No modules yet'}</strong><p>{modules.length ? 'Try changing your search or filter.' : 'Create your first module to get started.'}</p>{!modules.length && <button className="button button-primary" onClick={() => setShowCreateForm(true)}>Create first module</button>}</div>
          ) : (
            <div className="table-scroll"><table className="module-table"><thead><tr><th>MODULE</th><th>ENVIRONMENT</th><th>STATUS</th><th>CREATED</th><th>ACTIONS</th></tr></thead><tbody>
              {filteredModules.map((module) => <tr key={module.id} className={selectedModule === module.id ? 'selected-row' : ''}>
                <td><button className="module-name" onClick={() => setSelectedModule(module.id)}><span className="module-avatar">{module.name.slice(0, 1).toUpperCase()}</span><span><strong>{module.name}</strong><small>{module.description || 'No description'}</small></span></button></td>
                <td><span className="environment-tag">{module.environment}</span></td><td><StatusBadge status={module.status} /></td><td className="date-cell">{formatDate(module.created_at)}</td>
                <td><div className="row-actions">
                  {module.status === 'registered' || module.status === 'stopped' || module.status === 'failed' ? <button className="action-button deploy" disabled={!!busyAction} onClick={() => void runAction(module, 'deploy')}>Deploy</button> : module.status === 'running' ? <button className="action-button stop" disabled={!!busyAction} onClick={() => void runAction(module, 'stop')}>Stop</button> : <span className="muted-text">Working…</span>}
                  {module.status === 'stopped' && <button className="action-button restart" disabled={!!busyAction} onClick={() => void runAction(module, 'restart')}>Restart</button>}
                  <button className="action-button details" onClick={() => setSelectedModule(module.id)}>Details</button>
                </div></td>
              </tr>)}
            </tbody></table></div>
          )}
        </section>

        {activeModule && <section className="panel details-panel">
          <div className="panel-header"><div><h2>Module design</h2><p>Configuration saved for {activeModule.name}.</p></div><StatusBadge status={activeModule.status} /></div>
          <div className="metrics-grid design-grid">
            <article className="metric-card"><div className="metric-top"><span>Version / model</span></div><div className="metric-value detail-value">{activeModule.design_version} / {activeModule.deployment_model}</div></article>
            <article className="metric-card"><div className="metric-top"><span>Compute</span></div><div className="metric-value detail-value">{activeModule.cpu_units} CPU units</div><div className="metric-caption">{activeModule.memory_mb} MB memory</div></article>
            <article className="metric-card"><div className="metric-top"><span>Scaling range</span></div><div className="metric-value detail-value">{activeModule.min_replicas}–{activeModule.max_replicas}</div><div className="metric-caption">Minimum to maximum replicas</div></article>
            <article className="metric-card"><div className="metric-top"><span>Network / backup</span></div><div className="metric-value detail-value">{activeModule.network_access}</div><div className="metric-caption">Backup {activeModule.backup_enabled ? 'enabled in design' : 'not enabled'}</div></article>
          </div>
          <p className="detail-footnote">Health check: <code>{activeModule.health_check_path}</code> · Design metadata only; lifecycle actions remain local simulations.</p>
        </section>}

        <section id="activity" className="panel activity-panel">
          <div className="panel-header"><div><h2>Lifecycle activity</h2><p>{activeModule ? `Recent events for ${activeModule.name}` : 'Select a module to inspect its event history.'}</p></div>{activeModule && <StatusBadge status={activeModule.status} />}</div>
          {!activeModule ? <div className="empty-state compact">No module selected.</div> : events.length === 0 ? <div className="empty-state compact">No events recorded for this module yet.</div> : (
            <div className="event-list">{events.map((item) => <article className="event-item" key={item.id}>
              <div className={`event-marker ${item.result === 'success' ? 'event-success' : 'event-rejected'}`}>{item.result === 'success' ? '✓' : '!'}</div>
              <div className="event-content"><strong>{item.action} <span className={`event-result ${item.result === 'success' ? 'success-text' : 'error-text'}`}>{item.result}</span></strong><p>{item.details || `${item.previous_status} → ${item.new_status}`}</p><small>{formatDate(item.created_at)} · {item.previous_status} → {item.new_status}</small></div>
            </article>)}</div>
          )}
        </section>
        <footer className="page-footer"><span>CloudCapsule <strong>v0.6.0</strong></span><span><span className="status-dot green-dot" /> Local simulation mode · No AWS resources modified</span></footer>
      </main>
    </div>
  )
}

export default App
