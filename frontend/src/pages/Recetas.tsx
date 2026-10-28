import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, RecetaResumen, Unidad } from '../api'
import { Aviso, EstadoPill } from '../components/ui'
import { cop, pct } from '../format'

export default function Recetas() {
  const [recetas, setRecetas] = useState<RecetaResumen[]>([])
  const [unidades, setUnidades] = useState<Unidad[]>([])
  const [form, setForm] = useState({ nombre: '', es_subreceta: false, porciones: '1', precio_venta: '', margen_objetivo_pct: '70', rendimiento_cantidad: '', rendimiento_unidad_id: '' })
  const [error, setError] = useState('')
  const nav = useNavigate()

  useEffect(() => {
    api.recetas().then(setRecetas).catch(e => setError(e.message))
    api.unidades().then(u => { setUnidades(u); setForm(f => ({ ...f, rendimiento_unidad_id: String(u.find(x => x.simbolo === 'g')?.id ?? u[0]?.id) })) })
  }, [])

  async function crear(e: FormEvent) {
    e.preventDefault(); setError('')
    const sub = form.es_subreceta
    try {
      const r = await api.crearReceta({
        nombre: form.nombre, es_subreceta: sub, porciones: Number(form.porciones),
        precio_venta: !sub && form.precio_venta ? Number(form.precio_venta) : null,
        margen_objetivo_pct: !sub && form.margen_objetivo_pct ? Number(form.margen_objetivo_pct) : null,
        rendimiento_cantidad: sub ? Number(form.rendimiento_cantidad) : null,
        rendimiento_unidad_id: sub ? Number(form.rendimiento_unidad_id) : null,
      })
      nav(`/recetas/${r.id}`)  // siguiente paso del flujo: agregar componentes
    } catch (err) { setError((err as Error).message) }
  }
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  return (
    <>
      <h1>Recetas</h1>
      <p className="sub">Productos que vendes y subrecetas (salsas, masas, bases) que usas dentro de otros platos.</p>
      <div className="grid g-side">
        <form className="panel form" onSubmit={crear}>
          <h2>Nueva receta</h2>
          <label>Nombre<input id="rec-nombre" required value={form.nombre} onChange={set('nombre')} placeholder="Ej. Hamburguesa clásica" /></label>
          <label className="check"><input id="rec-sub" type="checkbox" checked={form.es_subreceta} onChange={e => setForm({ ...form, es_subreceta: e.target.checked })} /> Es una subreceta (se usa dentro de otras recetas)</label>
          {form.es_subreceta ? (
            <div className="row2">
              <label>Rendimiento<input id="rec-rend" type="number" min="0" step="any" required value={form.rendimiento_cantidad} onChange={set('rendimiento_cantidad')} /></label>
              <label>Unidad<select id="rec-rend-u" value={form.rendimiento_unidad_id} onChange={set('rendimiento_unidad_id')}>
                {unidades.map(u => <option key={u.id} value={u.id}>{u.simbolo}</option>)}</select></label>
            </div>
          ) : (<>
            <div className="row2">
              <label>Porciones<input id="rec-porc" type="number" min="1" required value={form.porciones} onChange={set('porciones')} /></label>
              <label>Precio de venta ($)<input id="rec-pv" type="number" min="0" step="any" value={form.precio_venta} onChange={set('precio_venta')} /></label>
            </div>
            <label>Margen objetivo (%)<input id="rec-margen" type="number" min="0" max="99" value={form.margen_objetivo_pct} onChange={set('margen_objetivo_pct')} /></label>
          </>)}
          <Aviso>{error}</Aviso>
          <button className="btn">Crear y agregar ingredientes</button>
        </form>
        <div className="panel tw">
          <table>
            <thead><tr><th>Receta</th><th>Tipo</th><th>Costo porción</th><th>Food Cost</th><th>Estado</th></tr></thead>
            <tbody>{recetas.map(r => (
              <tr key={r.id} className="click" onClick={() => nav(`/recetas/${r.id}`)}>
                <td><Link to={`/recetas/${r.id}`}>{r.nombre}</Link></td><td>{r.es_subreceta ? 'Subreceta' : 'Producto'}</td>
                <td className="num">{r.es_subreceta ? cop(r.costo_total) + ' total' : cop(r.costo_porcion)}</td>
                <td className="num">{pct(r.food_cost_pct)}</td>
                <td>{r.es_subreceta ? '—' : <EstadoPill estado={r.estado} />}</td>
              </tr>))}
            </tbody>
          </table>
          {recetas.length === 0 && <p className="muted">Todavía no hay recetas.</p>}
        </div>
      </div>
    </>
  )
}
