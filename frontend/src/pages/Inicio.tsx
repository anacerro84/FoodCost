import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, RecetaResumen } from '../api'
import { Aviso, EstadoPill, Kpi } from '../components/ui'
import { cop, pct } from '../format'

export default function Inicio() {
  const [recetas, setRecetas] = useState<RecetaResumen[] | null>(null)
  const [error, setError] = useState('')
  const nav = useNavigate()
  useEffect(() => { api.recetas().then(setRecetas).catch(e => setError(e.message)) }, [])

  if (error) return <Aviso>No se pudo conectar con la API: {error}</Aviso>
  if (!recetas) return <p className="muted">Cargando…</p>
  const productos = recetas.filter(r => !r.es_subreceta)
  const conPrecio = productos.filter(r => r.food_cost_pct != null)
  const promedio = conPrecio.length ? conPrecio.reduce((s, r) => s + r.food_cost_pct!, 0) / conPrecio.length : null

  return (
    <>
      <h1>Rentabilidad de productos</h1>
      <p className="sub">Costos calculados con el último precio de compra de cada ingrediente.</p>
      <div className="grid g4">
        <Kpi label="Productos" value={productos.length} />
        <Kpi label="Food Cost promedio" value={pct(promedio)} />
        <Kpi label="En riesgo" value={productos.filter(r => r.estado === 'en_riesgo').length} tone="bad" />
        <Kpi label="Con precios faltantes" value={productos.filter(r => r.faltan_precios.length).length} tone="warn" />
      </div>
      <div className="panel" style={{ marginTop: 16 }}>
        {productos.length === 0 ? (
          <p>Aún no hay productos. Empieza registrando <Link to="/ingredientes">ingredientes</Link> y luego crea una <Link to="/recetas">receta</Link>.</p>
        ) : (
          <div className="tw"><table>
            <thead><tr><th>Producto</th><th>Costo porción</th><th>Precio venta</th><th>Margen</th><th>Food Cost</th><th>Estado</th></tr></thead>
            <tbody>{productos.map(r => (
              <tr key={r.id} className="click" onClick={() => nav(`/recetas/${r.id}`)}>
                <td><Link to={`/recetas/${r.id}`}>{r.nombre}</Link></td>
                <td className="num">{cop(r.costo_porcion)}</td><td className="num">{cop(r.precio_venta)}</td>
                <td className="num">{cop(r.margen)}</td><td className="num">{pct(r.food_cost_pct)}</td>
                <td><EstadoPill estado={r.estado} /></td>
              </tr>))}
            </tbody>
          </table></div>
        )}
      </div>
    </>
  )
}
