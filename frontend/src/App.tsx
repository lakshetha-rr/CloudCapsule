
import { useCallback, useEffect, useState } from 'react'
import './App.css'

const API_URL = 'http://localhost:8000'

type ModuleStatus = 'registered' | 'deploying' | 'running' | 'stopped' | 'failed'
type Environment = 'development' | 'staging' | 'demo'
type LifecycleAction = 'deploy' | 'stop' | 'restart'

interface Module {
  id: number
  name: string
  description: string
  environment: Environment
  status: ModuleStatus
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
  detail?: string
}

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as ApiError
    throw new Error(error.detail || `Request failed (${response.status})`)
  }

  return response.json() as Promise<T>
}

function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
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
  const [form, setForm] = useState({
    name: '',
    description: '',
    environment: 'development' as Environment,
  })

  const loadDashboard = useCallback(async () => {
    setError('')

    try {
      const [moduleData, healthData] = await Promise.all([
        apiRequest<Module[]>('/modules'),
        apiRequest<HealthResponse>('/health/database'),
      ])

      setModules(moduleData)
      setHealth(healthData)
      setSelectedModule((current) => {
        if (current !== null && moduleData.some((item) => item.id === current)) {
          return current
        }
        return moduleData[0]?.id ?? null
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load dashboard')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadEvents = useCallback(async (moduleId: number) => {
    try {
      const data = await apiRequest<ModuleEvent[]>(`/modules/${moduleId}/events`)
      setEvents(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load audit history')
      setEvents([])
    }
  }, [])

  useEffect(() => {
    void loadDashboard()
  }, [loadDashboard])

  useEffect(() => {
    if (selectedModule !== null) {
      void loadEvents(selectedModule)
    } else {
      setEvents([])
    }
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

    const matchesEnvironment =
      environmentFilter === 'all' || item.environment === environmentFilter

    return matchesSearch && matchesEnvironment
  })

  async function createModule(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusyAction('create')
    setError('')
    setNotice('')

    try {
      const created = await apiRequest<Module>('/modules', {
        method: 'POST',
        body: JSON.stringify(form),
      })

      setNotice(`Module "${created.name}" created successfully.`)
      setForm({ name: '', description: '', environment: 'development' })
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
    const key = `${module.id}-${action}`
    setBusyAction(key)
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

  const activeModule = modules.find((item) => item.id === selectedModule)

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="CloudCapsule home">
          <span className="brand-mark">C</span>
          <span>CloudCapsule</span>
        </a>

        <div className="sidebar-label">WORKSPACE</div>
        <nav className="side-nav">
          <a className="nav-link active" href="#overview"><span>◫</span> Overview</a>
          <a className="nav-link" href="#modules"><span>▦</span> Modules</a>
          <a className="nav-link" href="#activity"><span>↗</span> Activity</a>
        </nav>

        <div className="sidebar-bottom">
          <div className="environment-card">
            <span className="live-dot" />
            <div>
              <strong>Local environment</strong>
              <small>AWS deployment disabled</small>
            </div>
          </div>
          <div className="sidebar-footer">CLOUDCAPSULE <span>v0.5.0</span></div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="breadcrumb">Workspace <span>/</span> Overview</div>
            <div className="topbar-subtitle">Cloud infrastructure, under control.</div>
          </div>
          <div className="topbar-actions">
            <span className={`connection-pill ${health?.status === 'healthy' ? 'connected' : ''}`}>
              <span className="live-dot" />
              {health?.status === 'healthy' ? 'API connected' : 'Checking API'}
            </span>
            <button className="button button-primary" onClick={() => setShowCreateForm(true)}>
              <span>＋</span> New module
            </button>
          </div>
        </header>

        <section id="overview" className="page-heading">
          <div>
            <div className="eyebrow">OVERVIEW</div>
            <h1>Your infrastructure</h1>
            <p>Monitor and manage your registered modules from one place.</p>
          </div>
          <button className="button button-secondary" onClick={() => void loadDashboard()}>
            ↻ Refresh
          </button>
        </section>

        {error && (
          <div className="alert alert-error" role="alert">
            <strong>Something needs attention</strong>
            <span>{error}</span>
            {error.toLowerCase().includes('fetch') && (
              <small>Confirm that Docker Compose is running and the API is available at localhost:8000.</small>
            )}
            <button onClick={() => setError('')} aria-label="Dismiss error">×</button>
          </div>
        )}

        {notice && (
          <div className="alert alert-success" role="status">
            <span>✓ {notice}</span>
            <button onClick={() => setNotice('')} aria-label="Dismiss message">×</button>
          </div>
        )}

        <section className="metrics-grid" aria-label="Module summary">
          <article className="metric-card">
            <div className="metric-top"><span>Total modules</span><span className="metric-icon blue">▦</span></div>
            <div className="metric-value">{loading ? '—' : counts.total}</div>
            <div className="metric-caption">Registered in CloudCapsule</div>
          </article>
          <article className="metric-card">
            <div className="metric-top"><span>Running</span><span className="metric-icon green">↗</span></div>
            <div className="metric-value">{loading ? '—' : counts.running}</div>
            <div className="metric-caption"><span className="status-dot green-dot" /> Active simulated modules</div>
          </article>
          <article className="metric-card">
            <div className="metric-top"><span>Stopped</span><span className="metric-icon amber">Ⅱ</span></div>
            <div className="metric-value">{loading ? '—' : counts.stopped}</div>
            <div className="metric-caption">Available to restart</div>
          </article>
          <article className="metric-card">
            <div className="metric-top"><span>Needs attention</span><span className="metric-icon red">!</span></div>
            <div className="metric-value">{loading ? '—' : counts.attention}</div>
            <div className="metric-caption">Modules in failed state</div>
          </article>
        </section>

        <section className="service-strip">
          <div className="service-leading">
            <div className="service-icon">⌘</div>
            <div>
              <strong>Local services</strong>
              <span>Development environment status</span>
            </div>
          </div>
          <div className="service-status">
            <span className={`status-dot ${health?.status === 'healthy' ? 'green-dot' : 'amber-dot'}`} />
            <div>
              <strong>PostgreSQL</strong>
              <span>{health?.database ?? 'Checking connection'}</span>
            </div>
          </div>
          <div className="service-status">
            <span className={`status-dot ${health?.status === 'healthy' ? 'green-dot' : 'amber-dot'}`} />
            <div>
              <strong>FastAPI</strong>
              <span>{health?.status ?? 'Checking connection'}</span>
            </div>
          </div>
          <span className="local-tag">LOCAL ONLY</span>
        </section>

        {showCreateForm && (
          <section className="panel create-panel">
            <div className="panel-header">
              <div>
                <h2>Create a module</h2>
                <p>Register a module in your local environment.</p>
              </div>
              <button className="icon-button" onClick={() => setShowCreateForm(false)} aria-label="Close form">×</button>
            </div>
            <form className="module-form" onSubmit={createModule}>
              <label>
                Module name
                <input
                  required
                  minLength={2}
                  maxLength={100}
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  placeholder="e.g. payments-service"
                />
              </label>
              <label>
                Environment
                <select
                  value={form.environment}
                  onChange={(event) => setForm({ ...form, environment: event.target.value as Environment })}
                >
                  <option value="development">Development</option>
                  <option value="staging">Staging</option>
                  <option value="demo">Demo</option>
                </select>
              </label>
              <label className="form-full">
                Description
                <textarea
                  maxLength={1000}
                  rows={3}
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                  placeholder="What does this module do?"
                />
              </label>
              <div className="form-actions">
                <button type="button" className="button button-secondary" onClick={() => setShowCreateForm(false)}>Cancel</button>
                <button type="submit" className="button button-primary" disabled={busyAction === 'create'}>
                  {busyAction === 'create' ? 'Creating…' : 'Create module'}
                </button>
              </div>
            </form>
          </section>
        )}

        <section id="modules" className="panel modules-panel">
          <div className="panel-header">
            <div>
              <h2>Modules</h2>
              <p>Your registered applications and their current state.</p>
            </div>
            <span className="record-count">{filteredModules.length} records</span>
          </div>

          <div className="table-toolbar">
            <label className="search-box">
              <span>⌕</span>
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search modules…" />
            </label>
            <select value={environmentFilter} onChange={(event) => setEnvironmentFilter(event.target.value)} aria-label="Filter environment">
              <option value="all">All environments</option>
              <option value="development">Development</option>
              <option value="staging">Staging</option>
              <option value="demo">Demo</option>
            </select>
          </div>

          {loading ? (
            <div className="empty-state"><span className="spinner" /> Loading modules…</div>
          ) : filteredModules.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">▦</div>
              <strong>{modules.length ? 'No matching modules' : 'No modules yet'}</strong>
              <p>{modules.length ? 'Try changing your search or filter.' : 'Create your first module to get started.'}</p>
              {!modules.length && <button className="button button-primary" onClick={() => setShowCreateForm(true)}>Create first module</button>}
            </div>
          ) : (
            <div className="table-scroll">
              <table className="module-table">
                <thead>
                  <tr><th>MODULE</th><th>ENVIRONMENT</th><th>STATUS</th><th>CREATED</th><th>ACTIONS</th></tr>
                </thead>
                <tbody>
                  {filteredModules.map((module) => (
                    <tr key={module.id} className={selectedModule === module.id ? 'selected-row' : ''}>
                      <td>
                        <button className="module-name" onClick={() => setSelectedModule(module.id)}>
                          <span className="module-avatar">{module.name.slice(0, 1).toUpperCase()}</span>
                          <span><strong>{module.name}</strong><small>{module.description || 'No description'}</small></span>
                        </button>
                      </td>
                      <td><span className="environment-tag">{module.environment}</span></td>
                      <td><StatusBadge status={module.status} /></td>
                      <td className="date-cell">{formatDate(module.created_at)}</td>
                      <td>
                        <div className="row-actions">
                          {module.status === 'registered' || module.status === 'stopped' || module.status === 'failed' ? (
                            <button className="action-button deploy" disabled={!!busyAction} onClick={() => void runAction(module, 'deploy')}>Deploy</button>
                          ) : module.status === 'running' ? (
                            <button className="action-button stop" disabled={!!busyAction} onClick={() => void runAction(module, 'stop')}>Stop</button>
                          ) : (
                            <span className="muted-text">Working…</span>
                          )}
                          {module.status === 'stopped' && (
                            <button className="action-button restart" disabled={!!busyAction} onClick={() => void runAction(module, 'restart')}>Restart</button>
                          )}
                          <button className="action-button details" onClick={() => setSelectedModule(module.id)}>Details</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section id="activity" className="panel activity-panel">
          <div className="panel-header">
            <div>
              <h2>Lifecycle activity</h2>
              <p>{activeModule ? `Recent events for ${activeModule.name}` : 'Select a module to inspect its event history.'}</p>
            </div>
            {activeModule && <StatusBadge status={activeModule.status} />}
          </div>

          {!activeModule ? (
            <div className="empty-state compact">No module selected.</div>
          ) : events.length === 0 ? (
            <div className="empty-state compact">No events recorded for this module yet.</div>
          ) : (
            <div className="event-list">
              {events.map((item) => (
                <article className="event-item" key={item.id}>
                  <div className={`event-marker ${item.result === 'success' ? 'event-success' : 'event-rejected'}`}>
                    {item.result === 'success' ? '✓' : '!'}
                  </div>
                  <div className="event-content">
                    <strong>{item.action} <span className={`event-result ${item.result === 'success' ? 'success-text' : 'error-text'}`}>{item.result}</span></strong>
                    <p>{item.details || `${item.previous_status} → ${item.new_status}`}</p>
                    <small>{formatDate(item.created_at)} · {item.previous_status} → {item.new_status}</small>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <footer className="page-footer">
          <span>CloudCapsule <strong>v0.5.0</strong></span>
          <span><span className="status-dot green-dot" /> Local simulation mode · No AWS resources modified</span>
        </footer>
      </main>
    </div>
  )
}

export default App
