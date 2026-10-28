const nf = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 0 })
export const cop = (n: number | null | undefined) => (n == null ? '—' : `$${nf.format(n)}`)
export const pct = (n: number | null | undefined) => (n == null ? '—' : `${n.toFixed(1).replace('.', ',')}%`)
export const num = (n: number) => new Intl.NumberFormat('es-CO', { maximumFractionDigits: 3 }).format(n)

/** Costo por unidad base mostrado por kg, l o und, que es como se compra. */
export function costoPresentacion(costo: number | null, tipo: string) {
  if (costo == null) return 'Sin precio'
  if (tipo === 'masa') return `${cop(costo * 1000)}/kg`
  if (tipo === 'volumen') return `${cop(costo * 1000)}/l`
  return `${cop(costo)}/und`
}

export const ESTADOS = {
  rentable: { txt: 'Rentable', cls: 'ok' },
  revisar: { txt: 'Revisar', cls: 'wa' },
  en_riesgo: { txt: 'En riesgo', cls: 'ba' },
} as const
