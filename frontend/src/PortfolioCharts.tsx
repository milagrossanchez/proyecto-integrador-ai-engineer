import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Portfolio } from './api'

const riskColors: Record<string, string> = { Bajo: '#43877b', Medio: '#d49b43', Alto: '#ca6653' }

const money = (value: number) => new Intl.NumberFormat('es-PE', {
  style: 'currency', currency: 'PEN', maximumFractionDigits: 0,
}).format(value)

export default function PortfolioCharts({ portfolio, budget }: { portfolio: Portfolio | null; budget: number }) {
  return <>
    <article className="insight-section">
      <div className="section-heading"><div><span className="section-kicker">PERFIL DE CARTERA</span><h2>Distribución por riesgo</h2></div><span className="section-caption">{portfolio?.summary.clients ?? '—'} clientes</span></div>
      <div className="chart-area" role="img" aria-label="Gráfico de clientes por nivel de riesgo"><ResponsiveContainer width="100%" height="100%"><BarChart data={portfolio?.risk_distribution ?? []} margin={{ top: 8, right: 16, left: -22, bottom: 0 }}><CartesianGrid vertical={false} stroke="#e8ece9" /><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#66746e', fontSize: 12 }} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: '#85918b', fontSize: 11 }} /><Tooltip cursor={{ fill: '#f1f4f1' }} formatter={(value) => [`${value} clientes`, 'Cartera']} /><Bar dataKey="value" name="Clientes" radius={[4, 4, 0, 0]} maxBarSize={54}>{(portfolio?.risk_distribution ?? []).map((item) => <Cell key={item.name} fill={riskColors[item.name] ?? '#43877b'} />)}</Bar></BarChart></ResponsiveContainer></div>
      <div className="chart-legend">{(portfolio?.risk_distribution ?? []).map((item) => <span key={item.name}><i style={{ background: riskColors[item.name] }} />{item.name}<b>{item.value}</b></span>)}</div>
    </article>
    <article className="insight-section reward-insight">
      <div className="section-heading"><div><span className="section-kicker">CAMPAÑA ACTUAL</span><h2>Recompensas asignadas</h2></div><span className="section-caption">{money(budget)}</span></div>
      <div className="chart-area" role="img" aria-label="Gráfico de recompensas asignadas por tipo"><ResponsiveContainer width="100%" height="100%"><BarChart data={portfolio?.reward_distribution ?? []} margin={{ top: 8, right: 12, left: -22, bottom: 0 }}><CartesianGrid vertical={false} stroke="#e8ece9" /><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#66746e', fontSize: 12 }} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: '#85918b', fontSize: 11 }} /><Tooltip cursor={{ fill: '#f1f4f1' }} formatter={(value) => [`${value} asignadas`, 'Recompensas']} /><Bar dataKey="value" name="Asignadas" fill="#b98543" radius={[4, 4, 0, 0]} maxBarSize={54} /></BarChart></ResponsiveContainer></div>
      <div className="comparison-note"><span><strong>Plan: {money(portfolio?.summary.expected_value ?? 0)}</strong> · Reglas: {money(portfolio?.baseline.expected_value ?? 0)} <span className="muted">(sin topes)</span></span></div>
    </article>
  </>
}