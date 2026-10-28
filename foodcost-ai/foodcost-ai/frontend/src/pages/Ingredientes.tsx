import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, Categoria, Ingrediente, Unidad } from '../api'
import { Aviso } from '../components/ui'
import { costoPresentacion, pct } from '../format'

export default function Ingredientes() {
  const [ings, setIngs] = useState<Ingrediente[]>([])
  const [unidades, setUnidades] = useState<Unidad[]>([])
  const [cats, setCats] = useState<Categoria[]>([])
  const [form, setForm] = useState({ nombre: '', categoria_id: '', nueva_categoria: '', unidad_base_id: '', merma_pct: '0' })
  const [error, setError] = useState('')
  const nav = useNavigate()

  const cargar = () => Promise.all([api.ingredientes(), api.categorias()]).then(([i, c]) => { setIngs(i); setCats(c) })
  useEffect(() => {
    api.unidades().then(u => {
      const base = u.filter(x => x.factor_base === 1)  // solo g, ml y und pueden ser unidad base
      setUnidades(base); setForm(f => ({ ...f, unidad_base_id: String(base[0]?.id ?? '') }))
    }).catch(e => setError(e.message))
    cargar().catch(e => setError(e.message))
  }, [])

  async function crear(e: FormEvent) {
    e.preventDefault(); setError('')
    try {
      let categoria_id = form.categoria_id ? Number(form.categoria_id) : null
      if (form.categoria_id === 'nueva') categoria_id = (await api.crearCategoria(form.nueva_categoria)).id
      const ing = await api.crearIngrediente({
        nombre: form.nombre, categoria_id, unidad_base_id: Number(form.unidad_base_id), merma_pct: Number(form.merma_pct),
      })
      nav(`/ingredientes/${ing.id}`)  // siguiente paso del flujo: registrar su primera compra
    } catch (err) { setError((err as Error).message) }
  }
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  return (
    <>
      <h1>Ingredientes</h1>
      <p className="sub">El costo se calcula a partir de la última compra registrada.</p>
      <div className="grid g-side">
        <form className="panel form" onSubmit={crear}>
          <h2>Nuevo ingrediente</h2>
          <label>Nombre<input id="ing-nombre" required value={form.nombre} onChange={set('nombre')} placeholder="Ej. Tomate chonto" /></label>
          <label>Categoría
            <select id="ing-categoria" value={form.categoria_id} onChange={set('categoria_id')}>
              <option value="">Sin categoría</option>
              {cats.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
              <option value="nueva">+ Nueva categoría…</option>
            </select>
          </label>
          {form.categoria_id === 'nueva' && <label>Nombre de la categoría<input id="ing-nueva-cat" required value={form.nueva_categoria} onChange={set('nueva_categoria')} /></label>}
          <label>Unidad base
            <select id="ing-unidad" value={form.unidad_base_id} onChange={set('unidad_base_id')}>
              {unidades.map(u => <option key={u.id} value={u.id}>{u.nombre} ({u.simbolo})</option>)}
            </select>
          </label>
          <label>Merma (%)<input id="ing-merma" type="number" min="0" max="99" step="0.1" value={form.merma_pct} onChange={set('merma_pct')} /></label>
          <p className="hint">La merma es lo que se pierde al limpiar o preparar: cáscaras, hojas dañadas, grasa.</p>
          <Aviso>{error}</Aviso>
          <button className="btn">Guardar y registrar compra</button>
        </form>
        <div className="panel tw">
          <table>
            <thead><tr><th>Ingrediente</th><th>Categoría</th><th>Unidad</th><th>Merma</th><th>Costo actual</th></tr></thead>
            <tbody>{ings.map(i => (
              <tr key={i.id} className="click" onClick={() => nav(`/ingredientes/${i.id}`)}>
                <td><Link to={`/ingredientes/${i.id}`}>{i.nombre}</Link></td><td>{i.categoria?.nombre ?? '—'}</td>
                <td>{i.unidad_base.simbolo}</td><td className="num">{pct(i.merma_pct)}</td>
                <td className="num">{i.costo_unitario == null ? <span className="pill wa">Sin precio</span> : costoPresentacion(i.costo_unitario, i.unidad_base.tipo)}</td>
              </tr>))}
            </tbody>
          </table>
          {ings.length === 0 && <p className="muted">Todavía no hay ingredientes.</p>}
        </div>
      </div>
    </>
  )
}
