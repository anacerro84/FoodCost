import { FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, Compra, CompraRegistrada, Ingrediente, Proveedor, Unidad } from '../api'
import { Aviso } from '../components/ui'
import { cop, costoPresentacion, num, pct } from '../format'

// Fecha local (toISOString usaría UTC y en la noche de Colombia daría el día siguiente)
const hoy = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10) }

export default function IngredienteDetalle() {
  const id = Number(useParams().id)
  const [ing, setIng] = useState<Ingrediente | null>(null)
  const [compras, setCompras] = useState<Compra[]>([])
  const [unidades, setUnidades] = useState<Unidad[]>([])
  const [provs, setProvs] = useState<Proveedor[]>([])
  const [form, setForm] = useState({ fecha: hoy(), cantidad: '', unidad_id: '', precio_total: '', proveedor_id: '' })
  const [res, setRes] = useState<CompraRegistrada | null>(null)
  const [error, setError] = useState('')

  async function cargar() {
    const [ings, cs, us, ps] = await Promise.all([api.ingredientes(), api.compras(id), api.unidades(), api.proveedores()])
    const actual = ings.find(i => i.id === id) ?? null
    setIng(actual); setCompras(cs); setProvs(ps)
    const compatibles = us.filter(u => u.tipo === actual?.unidad_base.tipo)
    setUnidades(compatibles)
    setForm(f => ({ ...f, unidad_id: f.unidad_id || String(compatibles.find(u => u.factor_base > 1)?.id ?? compatibles[0]?.id ?? '') }))
  }
  useEffect(() => { cargar().catch(e => setError(e.message)) }, [id])  // eslint-disable-line react-hooks/exhaustive-deps

  async function registrar(e: FormEvent) {
    e.preventDefault(); setError(''); setRes(null)
    try {
      const r = await api.registrarCompra({
        ingrediente_id: id, fecha: form.fecha, cantidad: Number(form.cantidad), unidad_id: Number(form.unidad_id),
        precio_total: Number(form.precio_total), proveedor_id: form.proveedor_id ? Number(form.proveedor_id) : null,
      })
      setRes(r); setForm(f => ({ ...f, cantidad: '', precio_total: '' })); await cargar()
    } catch (err) { setError((err as Error).message) }
  }
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  if (error && !ing) return <Aviso>{error}</Aviso>
  if (!ing) return <p className="muted">Cargando…</p>
  const tipo = ing.unidad_base.tipo
  return (
    <>
      <Link to="/ingredientes" className="volver">← Ingredientes</Link>
      <h1>{ing.nombre}</h1>
      <p className="sub">{ing.categoria?.nombre ?? 'Sin categoría'} · unidad base {ing.unidad_base.simbolo} · merma {pct(ing.merma_pct)} · costo actual <b>{costoPresentacion(ing.costo_unitario, tipo)}</b></p>
      <div className="grid g-side">
        <form className="panel form" onSubmit={registrar}>
          <h2>Registrar compra</h2>
          <label>Fecha<input id="compra-fecha" type="date" required value={form.fecha} onChange={set('fecha')} /></label>
          <div className="row2">
            <label>Cantidad<input id="compra-cantidad" type="number" min="0" step="any" required value={form.cantidad} onChange={set('cantidad')} /></label>
            <label>Unidad<select id="compra-unidad" value={form.unidad_id} onChange={set('unidad_id')}>
              {unidades.map(u => <option key={u.id} value={u.id}>{u.simbolo}</option>)}</select></label>
          </div>
          <label>Precio total pagado ($)<input id="compra-precio" type="number" min="0" step="any" required value={form.precio_total} onChange={set('precio_total')} /></label>
          <label>Proveedor<select id="compra-proveedor" value={form.proveedor_id} onChange={set('proveedor_id')}>
            <option value="">Sin proveedor</option>{provs.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></label>
          <Aviso>{error}</Aviso>
          {res && <Aviso tipo="ok">
            Compra registrada. Nuevo costo: {costoPresentacion(res.costo_nuevo, tipo)}
            {res.variacion_pct != null && <> ({res.variacion_pct > 0 ? '+' : ''}{pct(res.variacion_pct)} frente al anterior)</>}.
            {res.recetas_afectadas.length > 0 && <> Recetas recalculadas: {res.recetas_afectadas.join(', ')}.</>}
          </Aviso>}
          <button className="btn">Registrar compra</button>
        </form>
        <div className="panel tw">
          <h2>Historial de precios</h2>
          <table>
            <thead><tr><th>Fecha</th><th>Cantidad</th><th>Precio total</th><th>Costo</th><th>Proveedor</th></tr></thead>
            <tbody>{compras.map(c => (
              <tr key={c.id}><td className="num">{c.fecha}</td><td className="num">{num(c.cantidad)} {c.unidad.simbolo}</td>
                <td className="num">{cop(c.precio_total)}</td><td className="num">{costoPresentacion(c.costo_unitario_base, tipo)}</td>
                <td>{c.proveedor?.nombre ?? '—'}</td></tr>))}
            </tbody>
          </table>
          {compras.length === 0 && <p className="muted">Sin compras. Registra la primera para que el ingrediente tenga costo.</p>}
        </div>
      </div>
    </>
  )
}
