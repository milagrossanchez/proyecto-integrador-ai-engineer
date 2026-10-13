export type Risk = 'Bajo' | 'Medio' | 'Alto'

export type ClientRow = {
  IdCliente: number
  NombreCompleto: string
  Segmento: string
  NivelRiesgo: Risk
  CoinInTotal: number
  ProbRespuesta: number | null
  Recompensa: string | null
  Costo: number
  ValorEsperado: number | null
  ValorEsperadoBruto: number | null
  UpliftProbabilidad: number | null
  Asignada: boolean
  MotivoDecision: string
  EsPerfilAtipico: boolean
}

export type ClientDetail = ClientRow & {
  RiesgoScore: number
  DecilPropension: number
  CoinInPromedioSesion: number
  ValorTeoricoCasa: number
  NroSesiones: number
  DiasActivos: number
  DiasDesdeUltimaSesion: number
  AntiguedadDias: number
  PctSesionesChasing: number | null
  PctSesionesLargas: number | null
  PctJuegoMadrugada: number | null
  DuracionPromedioMin: number
  DuracionMaximaMin: number
  ApuestaMediaPromedio: number
  VolatilidadResultado: number | null
  RatioTendenciaCoinIn: number | null
  ValorIncremental: number | null
}

export type Portfolio = {
  budget: number
  summary: { clients: number; high_risk: number; eligible: number; assigned: number; spent: number; remaining_budget: number; expected_value: number }
  baseline: { eligible: number; spent: number; expected_value: number }
  risk_distribution: { name: string; value: number }[]
  reward_distribution: { name: string; value: number }[]
  clients: ClientRow[]
  pagination: { page: number; page_size: number; total: number }
}

export type ChatMessage = { role: 'user' | 'assistant'; content: string }
export type TelegramStatus = { enabled: boolean; connected: boolean; username: string | null }
export type TelegramSendResult = { enviado: boolean; motivo?: string; id_evento?: string }

// Mismos 3 clientes de demo que en la app Streamlit, con un chat_id real de
// Telegram precargado para poder demostrar el envío sin escribir nada a mano.
export const DEMO_TELEGRAM_CLIENTES: Record<number, string> = {
  900000: '8574346078',
  900001: '8574346078',
  900002: '8574346078',
}

type PortfolioParams = { budget: number; search: string; risk: string; assignment: string; page: number; pageSize: number; signal: AbortSignal }
const apiRoot = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`

export class ApiError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiRoot}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  } catch {
    throw new ApiError('No se pudo contactar a FastAPI. Confirma que esté activa en localhost:8000.')
  }
  if (!response.ok) {
    let message = `Error de API (${response.status}).`
    try {
      const body = await response.json() as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // Conservar el error HTTP si el servidor no responde JSON.
    }
    throw new ApiError(message, response.status)
  }
  return response.json() as Promise<T>
}

export function getPortfolio(params: PortfolioParams): Promise<Portfolio> {
  const query = new URLSearchParams({ budget: String(params.budget), page: String(params.page), page_size: String(params.pageSize) })
  if (params.search.trim()) query.set('search', params.search.trim())
  if (params.risk) query.set('risk', params.risk)
  if (params.assignment) query.set('assignment', params.assignment)
  return request(`/portfolio?${query}`, { signal: params.signal })
}

export function getClient(id: number, budget: number, signal?: AbortSignal): Promise<ClientDetail> {
  return request(`/clients/${id}?budget=${budget}`, { signal })
}

export function getExplanation(id: number, budget: number): Promise<{ explicacion: string; oferta: string; mensaje: string }> {
  return request(`/clients/${id}/explanation?budget=${budget}`, { method: 'POST' })
}

export function getChatReply(question: string): Promise<{ respuesta: string; fuentes: string[] }> {
  return request('/chat', { method: 'POST', body: JSON.stringify({ question }) })
}

export function getTelegramStatus(signal?: AbortSignal): Promise<TelegramStatus> {
  return request('/telegram/status', { signal })
}

export function sendTelegramOffer(id: number, budget: number, chatId: string): Promise<TelegramSendResult> {
  return request(`/clients/${id}/telegram?budget=${budget}`, {
    method: 'POST',
    body: JSON.stringify({ chat_id: chatId }),
  })
}