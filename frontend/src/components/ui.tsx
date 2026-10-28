import { ReactNode } from 'react'
import { ESTADOS } from '../format'
import type { Estado } from '../api'

export function EstadoPill({ estado }: { estado: Estado }) {
  if (!estado) return <span className="muted">Sin precio de venta</span>
  const e = ESTADOS[estado]
  return <span className={`pill ${e.cls}`}>{e.txt}</span>
}

export function Aviso({ tipo = 'error', children }: { tipo?: 'error' | 'ok' | 'info'; children: ReactNode }) {
  if (!children) return null
  return <div className={`aviso ${tipo}`} role={tipo === 'error' ? 'alert' : 'status'}>{children}</div>
}

export function Kpi({ label, value, tone }: { label: string; value: ReactNode; tone?: string }) {
  return (
    <div className="panel kpi">
      <div className="l">{label}</div>
      <div className="v" style={tone ? { color: `var(--${tone})` } : undefined}>{value}</div>
    </div>
  )
}
