import { lazy, Suspense, useDeferredValue, useEffect, useState, type FormEvent } from 'react'
import {
  AlertTriangle, BadgeCheck, Bot, ChevronDown,
  ChevronLeft, ChevronRight, CircleHelp, Coins, Gift, MessageSquareText,
  RefreshCw, Search, Send, ShieldCheck, Sparkles, UsersRound, X,
} from 'lucide-react'
import {
  ApiError, getChatReply, getClient, getExplanation, getPortfolio,
  type ChatMessage, type ClientDetail, type Portfolio,
} from './api'
import './Dashboard.css'

const PortfolioCharts = lazy(() => import('./PortfolioCharts'))

const money = (value: number) => new Intl.NumberFormat('es-PE', {
  style: 'currency', currency: 'PEN', maximumFractionDigits: 0,
}).format(value)

const percent = (value: number) => new Intl.NumberFormat('es-PE', {
  style: 'percent', maximumFractionDigits: 0,
}).format(value)

function RiskBadge({ risk }: { risk: string }) {
  return <span className={`risk-badge risk-${risk.toLowerCase()}`}>{risk}</span>
}

function App() {
  const [budgetDraft, setBudgetDraft] = useState('15000')
  const [budget, setBudget] = useState(15000)
  const [search, setSearch] = useState('')
  const [risk, setRisk] = useState('')
  const [assignment, setAssignment] = useState('')
  const [page, setPage] = useState(1)
  const [refreshToken, setRefreshToken] = useState(0)
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [clientResult, setClientResult] = useState<{ id: number; budget: number; data: ClientDetail } | null>(null)
  const [explanation, setExplanation] = useState<{ explicacion: string; oferta: string; mensaje: string } | null>(null)
  const [explanationLoading, setExplanationLoading] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const deferredSearch = useDeferredValue(search)
  const client = clientResult?.id === selectedId && clientResult.budget === budget ? clientResult.data : null
  const clientLoading = selectedId !== null && client === null

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        setPortfolio(await getPortfolio({ budget, search: deferredSearch, risk, assignment, page, pageSize: 10, signal: controller.signal }))
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof ApiError ? cause.message : 'No se pudo conectar con la API.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }, 160)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [budget, deferredSearch, risk, assignment, page, refreshToken])

  useEffect(() => {
    if (selectedId === null) return
    const clientId = selectedId
    const controller = new AbortController()
    getClient(clientId, budget, controller.signal)
      .then((data) => setClientResult({ id: clientId, budget, data }))
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(cause instanceof Error ? cause.message : 'No se pudo cargar la ficha.')
          setSelectedId(null)
        }
      })
    return () => controller.abort()
  }, [selectedId, budget])

  const applyBudget = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const value = Number(budgetDraft)
    if (Number.isFinite(value) && value > 0 && value <= 1_000_000) {
      setPage(1)
      setBudget(value)
      setExplanation(null)
    }
  }

  const changeFilter = (setter: (value: string) => void, value: string) => {
    setter(value)
    setPage(1)
  }

  const openClient = (id: number) => {
    setError('')
    setExplanation(null)
    setClientResult(null)
    setSelectedId(id)
  }

  const requestExplanation = async () => {
    if (selectedId === null) return
    setExplanationLoading(true)
    try { setExplanation(await getExplanation(selectedId, budget)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No se pudo generar la explicación.') }
    finally { setExplanationLoading(false) }
  }

  const submitChat = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const question = chatInput.trim()
    if (!question || chatLoading) return
    setMessages((current) => [...current, { role: 'user', content: question }])
    setChatInput('')
    setChatLoading(true)
    try {
      const reply = await getChatReply(question)
      const sources = reply.fuentes.length ? `\n\nFuentes: ${reply.fuentes.join(', ')}` : ''
      setMessages((current) => [...current, { role: 'assistant', content: `${reply.respuesta}${sources}` }])
    } catch (cause) {
      setMessages((current) => [...current, { role: 'assistant', content: cause instanceof Error ? cause.message : 'No se pudo consultar el asistente.' }])
    } finally { setChatLoading(false) }
  }

  const pages = Math.max(1, Math.ceil((portfolio?.pagination.total ?? 0) / 10))

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#inicio" aria-label="Palacio Real, inicio"><span className="brand-mark">PR</span><span className="brand-copy"><strong>PALACIO REAL</strong><small>INTELIGENCIA DE CLIENTES</small></span></a>
        <div className="workspace-label">ESPACIO DE TRABAJO</div>
        <nav className="side-nav" aria-label="Navegación principal"><a className="nav-item active" href="#cartera"><UsersRound size={17} /> Cartera <span className="nav-dot" /></a><button className="nav-item" type="button" onClick={() => setChatOpen(true)}><CircleHelp size={17} /> Políticas y ayuda</button></nav>
        <div className="sidebar-bottom"><div className="admin-mark">AM</div><div><strong>Analista de marketing</strong><span>Vista administrativa</span></div><ChevronDown size={15} aria-hidden="true" /></div>
      </aside>

      <main className="main-content" id="inicio">
        <header className="topbar"><div className="breadcrumb">Operaciones <span>/</span> Campañas</div><div className="topbar-right"><span className="environment-tag"><span /> Entorno de demostración</span><button className="icon-button refresh-button" title="Actualizar cartera" aria-label="Actualizar cartera" onClick={() => setRefreshToken((value) => value + 1)}><RefreshCw size={16} /></button></div></header>
        <div className="page-wrap" id="cartera">
          <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line" /> PANEL DE CAMPAÑA</div><h1>Cartera de clientes</h1><p>Riesgo, propensión y asignación de recompensas en una sola vista.</p></div><form className="budget-control" onSubmit={applyBudget}><label htmlFor="campaign-budget">Presupuesto de campaña</label><div className="budget-input-wrap"><span>S/</span><input id="campaign-budget" type="number" min="1" max="1000000" step="500" value={budgetDraft} onChange={(event) => setBudgetDraft(event.target.value)} /><button type="submit">Aplicar</button></div></form></section>

          {error && <div className="error-banner" role="alert"><AlertTriangle size={18} /><div><strong>No se pudo actualizar el panel</strong><span>{error} Confirma que FastAPI esté activa en el puerto 8000.</span></div><button className="icon-button" onClick={() => setRefreshToken((value) => value + 1)} aria-label="Reintentar"><RefreshCw size={16} /></button></div>}

          <section className="kpi-grid" aria-label="Indicadores de campaña">
            <article className="kpi-card"><div className="kpi-top"><span className="kpi-label">Clientes en cartera</span><span className="kpi-icon icon-sage"><UsersRound size={17} /></span></div><strong className="kpi-value">{loading && !portfolio ? '—' : portfolio?.summary.clients.toLocaleString('es-PE')}</strong><span className="kpi-foot">Base analítica disponible</span></article>
            <article className="kpi-card"><div className="kpi-top"><span className="kpi-label">Riesgo alto</span><span className="kpi-icon icon-coral"><ShieldCheck size={17} /></span></div><strong className="kpi-value">{portfolio?.summary.high_risk.toLocaleString('es-PE') ?? '—'}</strong><span className="kpi-foot"><span className="text-coral">Excluidos</span> de incentivos</span></article>
            <article className="kpi-card"><div className="kpi-top"><span className="kpi-label">Recompensas asignadas</span><span className="kpi-icon icon-gold"><Gift size={17} /></span></div><strong className="kpi-value">{portfolio?.summary.assigned.toLocaleString('es-PE') ?? '—'}<small> / {portfolio?.summary.eligible.toLocaleString('es-PE') ?? '—'}</small></strong><span className="kpi-foot">Elegibles con valor positivo</span></article>
            <article className="kpi-card kpi-budget"><div className="kpi-top"><span className="kpi-label">Inversión asignada</span><span className="kpi-icon icon-ink"><Coins size={17} /></span></div><strong className="kpi-value">{portfolio ? money(portfolio.summary.spent) : '—'}</strong><div className="budget-progress"><span style={{ width: `${portfolio ? Math.min(100, (portfolio.summary.spent / budget) * 100) : 0}%` }} /></div><span className="kpi-foot">Disponible {portfolio ? money(portfolio.summary.remaining_budget) : '—'}</span></article>
          </section>

          <section className="insights-grid" aria-label="Distribución de cartera y campaña">
            <Suspense fallback={<div className="chart-loading">Cargando distribuciones...</div>}><PortfolioCharts portfolio={portfolio} budget={budget} /></Suspense>
          </section>

          <section className="portfolio-section"><div className="portfolio-header"><div><span className="section-kicker">GESTIÓN DE CLIENTES</span><h2>Decisiones de campaña</h2></div><span className="live-count">{portfolio?.pagination.total.toLocaleString('es-PE') ?? '—'} registros</span></div><div className="filters-row"><label className="search-field"><Search size={16} /><input value={search} onChange={(event) => changeFilter(setSearch, event.target.value)} placeholder="Buscar por ID de cliente" aria-label="Buscar por ID de cliente" /><kbd>/</kbd></label><label className="select-field"><span>Riesgo</span><select value={risk} onChange={(event) => changeFilter(setRisk, event.target.value)}><option value="">Todos</option><option value="Bajo">Bajo</option><option value="Medio">Medio</option><option value="Alto">Alto</option></select></label><label className="select-field"><span>Asignación</span><select value={assignment} onChange={(event) => changeFilter(setAssignment, event.target.value)}><option value="">Todas</option><option value="assigned">Asignada</option><option value="not_assigned">Sin asignar</option></select></label></div>
            <div className="table-wrap"><table><thead><tr><th>CLIENTE</th><th>SEGMENTO</th><th>RIESGO</th><th>PROPENSIÓN</th><th>RECOMPENSA</th><th>VALOR ESPERADO</th><th>ESTADO</th><th aria-label="Ver ficha" /></tr></thead><tbody>
              {loading && !portfolio && <tr><td colSpan={8} className="table-message">Cargando cartera...</td></tr>}
              {!loading && portfolio?.clients.length === 0 && <tr><td colSpan={8} className="table-message">No hay clientes que coincidan con los filtros.</td></tr>}
              {portfolio?.clients.map((row) => <tr key={row.IdCliente} className="client-row" onClick={() => openClient(row.IdCliente)} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') openClient(row.IdCliente) }}><td><span className="client-initial">{row.NombreCompleto.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()}</span><strong>{row.NombreCompleto}</strong></td><td><span className="segment-label">{row.Segmento}</span></td><td><RiskBadge risk={row.NivelRiesgo} /></td><td><div className="probability-cell"><span>{percent(row.ProbRespuesta ?? 0)}</span><i><span style={{ width: `${Math.min(100, Math.max(0, (row.ProbRespuesta ?? 0) * 100))}%` }} /></i></div></td><td>{row.Recompensa ? <span className={`reward-label reward-${row.Recompensa}`}>{row.Recompensa}</span> : <span className="muted">—</span>}</td><td className="money-cell">{row.ValorEsperado === null ? '—' : money(row.ValorEsperado)}</td><td><span className={`assignment-state ${row.Asignada ? 'is-assigned' : 'is-pending'}`}><i />{row.Asignada ? 'Asignada' : 'No asignada'}</span></td><td><ChevronRight size={16} className="row-chevron" /></td></tr>)}
            </tbody></table></div><div className="table-footer"><span>Mostrando {portfolio?.clients.length ?? 0} de {portfolio?.pagination.total ?? 0}</span><div className="pagination-controls"><button className="icon-button" title="Página anterior" aria-label="Página anterior" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}><ChevronLeft size={16} /></button><span>Página <strong>{page}</strong> de {pages}</span><button className="icon-button" title="Página siguiente" aria-label="Página siguiente" disabled={page >= pages || loading} onClick={() => setPage((value) => value + 1)}><ChevronRight size={16} /></button></div></div>
          </section>
          <footer className="page-footer"><span><ShieldCheck size={14} /> Guardrails de juego responsable activos</span><span>Datos simulados · Fecha de corte 29 jul 2026</span></footer>
        </div>
      </main>

      {selectedId !== null && <div className="drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedId(null) }}><aside className="client-drawer" role="dialog" aria-modal="true" aria-label={`Ficha del cliente ${selectedId}`}><div className="drawer-header"><div><span className="section-kicker">FICHA DE CLIENTE</span><h2>{client?.NombreCompleto ?? `Cliente ${selectedId}`}</h2></div><button className="icon-button" onClick={() => setSelectedId(null)} title="Cerrar ficha" aria-label="Cerrar ficha"><X size={18} /></button></div>
        {clientLoading || !client ? <div className="drawer-loading">Cargando ficha y decisión...</div> : <><div className="drawer-risk"><RiskBadge risk={client.NivelRiesgo} /><span>{client.EsPerfilAtipico ? <><AlertTriangle size={14} /> Perfil atípico</> : <><BadgeCheck size={14} /> Perfil analizado</>}</span></div><div className="drawer-metrics"><div><span>Probabilidad de respuesta</span><strong>{percent(client.ProbRespuesta ?? 0)}</strong></div><div><span>CoinIn histórico</span><strong>{money(client.CoinInTotal)}</strong></div></div>
          <section className="drawer-section"><h3>Decisión de campaña</h3><div className="decision-block"><div><span>Estado</span><strong>{client.Asignada ? 'Recompensa asignada' : 'Sin asignación'}</strong></div><div><span>Recompensa</span><strong>{client.Recompensa ?? 'No aplica'}</strong></div><div><span>Valor esperado</span><strong>{client.ValorEsperado === null ? '—' : money(client.ValorEsperado)}</strong></div><p>{client.MotivoDecision}</p></div></section>
          <section className="drawer-section"><h3>Actividad y señales</h3><dl className="signal-list"><div><dt>Sesiones registradas</dt><dd>{client.NroSesiones}</dd></div><div><dt>Días desde última sesión</dt><dd>{client.DiasDesdeUltimaSesion}</dd></div><div><dt>Antigüedad observada</dt><dd>{client.AntiguedadDias} días</dd></div><div><dt>Sesiones con chasing</dt><dd>{percent(client.PctSesionesChasing ?? 0)}</dd></div><div><dt>Sesiones largas</dt><dd>{percent(client.PctSesionesLargas ?? 0)}</dd></div><div><dt>Actividad de madrugada</dt><dd>{percent(client.PctJuegoMadrugada ?? 0)}</dd></div></dl></section>
          <section className="drawer-section explanation-section"><div className="section-heading"><h3>Lectura del modelo</h3><Sparkles size={16} /></div>{explanation ? <div className="explanation-copy"><p>{explanation.explicacion}</p><strong>{explanation.oferta}</strong><p>{explanation.mensaje}</p></div> : <p className="muted">Genera una explicación a partir de las señales del cliente y la decisión actual.</p>}<button className="secondary-button" onClick={requestExplanation} disabled={explanationLoading}>{explanationLoading ? 'Preparando explicación...' : <><Sparkles size={15} /> Generar explicación</>}</button></section></>}</aside></div>}

      {chatOpen && <section className="chat-panel" aria-label="Asistente de políticas"><div className="chat-header"><div className="chat-avatar"><Bot size={17} /></div><div><strong>Asistente de políticas</strong><span>RAG · Base documental</span></div><button className="icon-button" onClick={() => setChatOpen(false)} title="Cerrar asistente" aria-label="Cerrar asistente"><X size={17} /></button></div><div className="chat-messages">{messages.length === 0 && <div className="chat-welcome"><span className="chat-spark"><Sparkles size={16} /></span><strong>¿Qué necesitas revisar?</strong><p>Consulta reglas de elegibilidad, recompensas y juego responsable.</p><button onClick={() => setChatInput('¿Qué ocurre con clientes de riesgo alto?')}>¿Qué ocurre con riesgo alto?</button><button onClick={() => setChatInput('¿Qué límites tiene el presupuesto?')}>Límites del presupuesto</button></div>}{messages.map((message, index) => <div key={`${message.role}-${index}`} className={`chat-message ${message.role}`}>{message.content}</div>)}{chatLoading && <div className="chat-message assistant typing">Consultando políticas...</div>}</div><form className="chat-form" onSubmit={submitChat}><input value={chatInput} onChange={(event) => setChatInput(event.target.value)} placeholder="Pregunta sobre las políticas..." aria-label="Pregunta para el asistente" maxLength={1000} /><button type="submit" disabled={!chatInput.trim() || chatLoading} title="Enviar pregunta" aria-label="Enviar pregunta"><Send size={16} /></button></form><div className="chat-disclaimer">Respuestas basadas en documentos internos.</div></section>}
      {!chatOpen && <button className="chat-fab" onClick={() => setChatOpen(true)} aria-label="Abrir asistente de políticas" title="Asistente de políticas"><MessageSquareText size={20} /><span>Políticas</span></button>}
    </div>
  )
}

export default App
