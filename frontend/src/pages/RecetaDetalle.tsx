import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, Ingrediente, RecetaDetalle as Detalle, RecetaResumen, Unidad } from '../api'
import { Aviso, EstadoPill, Kpi } from '../components/ui'
import { cop, num, pct } from '../format'

export default function RecetaDetalle() {
  const id = Number(useParams().id)
  const [r, setR] = useState<Detalle | null>(null)
  const [ings, setIngs] = useState<Ingrediente[]>([])
  const [subs, setSubs] = useState<RecetaResumen[]>([])
  const [unidades, setUnidades] = useState<Unidad[]>([])
  const [sel, setSel] = useState('')            // "i-3" (ingrediente) o "s-2" (subreceta)
  const [tipoSub, setTipoSub] = useState<string | null>(null)
  const [cantidad, setCantidad] = useState('')
  const [unidadId, setUnidadId] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.receta(id), api.ingredientes(), api.recetas(), api.unidades()])
      .then(([rec, i, rs, u]) => { setR(rec); setIngs(i); setSubs(rs.filter(x => x.es_subreceta && x.id !== id)); setUnidades(u) })
      .catch(e => setError(e.message))
  }, [id])

  // Tipo de unidad del componente elegido, para mostrar solo unidades compatibles
  const tipo = useMemo(() => {
    if (sel.startsWith('i-')) return ings.find(i => i.id === Number(sel.slice(2)))?.unidad_base.tipo ?? null
    if (sel.startsWith('s-')) return tipoSub
    return null
  }, [sel, ings, tipoSub])
  const compatibles = unidades.filter(u => u.tipo === tipo)

  useEffect(() => {
    if (sel.startsWith('s-')) api.receta(Number(sel.slice(2))).then(s => setTipoSub(s.rendimiento_unidad?.tipo ?? null))
  }, [sel])
  useEffect(() => { setUnidadId(String(compatibles[0]?.id ?? '')) }, [tipo])  // eslint-disable-line react-hooks/exhaustive-deps

  async function agregar(e: FormEvent) {
    e.preventDefault(); setError('')
    const [t, cid] = sel.split('-')
    try {
      setR(await api.agregarComponente(id, {
        ingrediente_id: t === 'i' ? Number(cid) : null, subreceta_id: t === 's' ? Number(cid) : null,
        cantidad: Number(cantidad), unidad_id: Number(unidadId),
      }))
      setSel(''); setCantidad('')
    } catch (err) { setError((err as Error).message) }
  }
  async function quitar(compId: number) {
    try { setR(await api.quitarComponente(id, compId)) } catch (err) { setError((err as Error).message) }
  }

  if (!r) return error ? <Aviso>{error}</Aviso> : <p className="muted">Cargando…</p>
  return (
    <>
      <Link to="/recetas" className="volver">← Recetas</Link>
      <h1>{r.nombre}</h1>
      <p className="sub">{r.es_subreceta
        ? `Subreceta · rinde ${num(r.rendimiento_cantidad ?? 0)} ${r.rendimiento_unidad?.simbolo ?? ''}`
        : `${r.porciones} ${r.porciones === 1 ? 'porción' : 'porciones'} · precio de venta ${cop(r.precio_venta)}`}</p>

      {r.faltan_precios.length > 0 && <Aviso tipo="info">Sin precio de compra: {r.faltan_precios.join(', ')}. El costo está incompleto hasta que registres una compra.</Aviso>}

      <div className="grid g4">
        {r.es_subreceta ? (<>
          <Kpi label="Costo total" value={cop(r.costo_total)} />
          <Kpi label={`Costo por 100 ${r.rendimiento_unidad?.simbolo}`} value={cop(r.rendimiento_cantidad ? r.costo_total / r.rendimiento_cantidad * 100 : null)} />
        </>) : (<>
          <Kpi label="Costo por porción" value={cop(r.costo_porcion)} />
          <Kpi label="Margen" value={<>{cop(r.margen)} <small>{pct(r.margen_pct)}</small></>} />
          <Kpi label="Food Cost" value={pct(r.food_cost_pct)} />
          <Kpi label="Estado" value={<EstadoPill estado={r.estado} />} />
        </>)}
      </div>

      <div className="grid g-side" style={{ marginTop: 16 }}>
        <form className="panel form" onSubmit={agregar}>
          <h2>Agregar componente</h2>
          <label>Ingrediente o subreceta
            <select id="comp-sel" required value={sel} onChange={e => setSel(e.target.value)}>
              <option value="">Elegir…</option>
              <optgroup label="Ingredientes">{ings.map(i => <option key={i.id} value={`i-${i.id}`}>{i.nombre}</option>)}</optgroup>
              {subs.length > 0 && <optgroup label="Subrecetas">{subs.map(s => <option key={s.id} value={`s-${s.id}`}>{s.nombre}</option>)}</optgroup>}
            </select>
          </label>
          <div className="row2">
            <label>Cantidad<input id="comp-cant" type="number" min="0" step="any" required value={cantidad} onChange={e => setCantidad(e.target.value)} /></label>
            <label>Unidad<select id="comp-unidad" value={unidadId} onChange={e => setUnidadId(e.target.value)}>
              {compatibles.map(u => <option key={u.id} value={u.id}>{u.simbolo}</option>)}</select></label>
          </div>
          <p className="hint">La merma del ingrediente se aplica automáticamente.</p>
          <Aviso>{error}</Aviso>
          <button className="btn">Agregar</button>
        </form>

        <div className="panel tw">
          <h2>Costo por componente</h2>
          <table>
            <thead><tr><th>Componente</th><th>Cantidad</th><th>Merma</th><th>Costo</th><th>Peso en el costo</th><th></th></tr></thead>
            <tbody>{r.lineas.map(l => (
              <tr key={l.componente_id}>
                <td>{l.nombre}{l.tipo === 'subreceta' && <span className="tag">subreceta</span>}</td>
                <td className="num">{num(l.cantidad)} {l.unidad}</td><td className="num">{pct(l.merma_pct)}</td>
                <td className="num">{l.costo == null ? <span className="pill wa">Sin precio</span> : cop(l.costo)}</td>
                <td><div className="bar" title={pct(l.participacion_pct)}><i style={{ width: `${l.participacion_pct ?? 0}%` }} /></div><span className="num small">{pct(l.participacion_pct)}</span></td>
                <td><button type="button" className="link" onClick={() => quitar(l.componente_id)} aria-label={`Quitar ${l.nombre}`}>Quitar</button></td>
              </tr>))}
            </tbody>
          </table>
          {r.lineas.length === 0 && <p className="muted">Agrega el primer ingrediente para calcular el costo.</p>}
          {!r.es_subreceta && r.precio_objetivo != null && r.lineas.length > 0 && (
            <p className="objetivo">Para un margen de {pct(r.margen_objetivo_pct)} el precio de venta debería ser <b>{cop(r.precio_objetivo)}</b>.</p>
          )}
        </div>
      </div>
    </>
  )
}
