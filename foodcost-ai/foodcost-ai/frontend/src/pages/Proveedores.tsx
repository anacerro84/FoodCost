import { FormEvent, useEffect, useState } from 'react'
import { api, Proveedor } from '../api'
import { Aviso } from '../components/ui'

export default function Proveedores() {
  const [lista, setLista] = useState<Proveedor[]>([])
  const [nombre, setNombre] = useState('')
  const [contacto, setContacto] = useState('')
  const [error, setError] = useState('')
  const cargar = () => api.proveedores().then(setLista).catch(e => setError(e.message))
  useEffect(() => { cargar() }, [])

  async function crear(e: FormEvent) {
    e.preventDefault(); setError('')
    try { await api.crearProveedor({ nombre, contacto: contacto || undefined }); setNombre(''); setContacto(''); cargar() }
    catch (err) { setError((err as Error).message) }
  }
  return (
    <>
      <h1>Proveedores</h1>
      <p className="sub">A quién le compras cada ingrediente.</p>
      <div className="grid g2">
        <form className="panel form" onSubmit={crear}>
          <h2>Nuevo proveedor</h2>
          <label>Nombre<input id="prov-nombre" required value={nombre} onChange={e => setNombre(e.target.value)} /></label>
          <label>Contacto (opcional)<input id="prov-contacto" value={contacto} onChange={e => setContacto(e.target.value)} /></label>
          <Aviso>{error}</Aviso>
          <button className="btn">Guardar proveedor</button>
        </form>
        <div className="panel tw">
          <table><thead><tr><th>Proveedor</th><th>Contacto</th></tr></thead>
            <tbody>{lista.map(p => <tr key={p.id}><td>{p.nombre}</td><td>{p.contacto ?? '—'}</td></tr>)}</tbody></table>
          {lista.length === 0 && <p className="muted">Sin proveedores registrados.</p>}
        </div>
      </div>
    </>
  )
}
