// Cliente de la API REST de FoodCost AI
export interface Unidad { id: number; nombre: string; simbolo: string; tipo: 'masa' | 'volumen' | 'unidad'; factor_base: number }
export interface Categoria { id: number; nombre: string }
export interface Proveedor { id: number; nombre: string; contacto: string | null }
export interface Ingrediente {
  id: number; nombre: string; categoria: Categoria | null; unidad_base: Unidad
  merma_pct: number; costo_unitario: number | null; stock_minimo: number; activo: boolean
}
export interface Compra {
  id: number; ingrediente_id: number; proveedor: Proveedor | null; fecha: string
  cantidad: number; unidad: Unidad; precio_total: number; costo_unitario_base: number
}
export interface CompraRegistrada {
  compra: Compra; costo_anterior: number | null; costo_nuevo: number
  variacion_pct: number | null; recetas_afectadas: string[]
}
export type Estado = 'rentable' | 'revisar' | 'en_riesgo' | null
export interface RecetaResumen {
  id: number; nombre: string; es_subreceta: boolean; porciones: number; precio_venta: number | null
  costo_total: number; costo_porcion: number; margen: number | null; food_cost_pct: number | null
  estado: Estado; faltan_precios: string[]
}
export interface Linea {
  componente_id: number; nombre: string; tipo: 'ingrediente' | 'subreceta'; cantidad: number
  unidad: string; merma_pct: number; costo: number | null; participacion_pct: number | null
}
export interface RecetaDetalle extends RecetaResumen {
  rendimiento_cantidad: number | null; rendimiento_unidad: Unidad | null
  margen_objetivo_pct: number | null; margen_pct: number | null; precio_objetivo: number | null
  lineas: Linea[]
}

export class ApiError extends Error {}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, {
    ...init, headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (r.status === 204) return undefined as T
  const body = await r.json().catch(() => ({}))
  if (!r.ok) {
    const d = body.detail
    // FastAPI devuelve una lista cuando falla la validación de Pydantic
    const msg = Array.isArray(d) ? d.map((x: { msg: string }) => x.msg.replace('Value error, ', '')).join('. ') : d
    throw new ApiError(msg ?? `Error ${r.status}`)
  }
  return body as T
}
const post = <T,>(path: string, data: unknown) => req<T>(path, { method: 'POST', body: JSON.stringify(data) })

export const api = {
  unidades: () => req<Unidad[]>('/unidades'),
  categorias: () => req<Categoria[]>('/categorias'),
  crearCategoria: (nombre: string) => post<Categoria>('/categorias', { nombre }),
  proveedores: () => req<Proveedor[]>('/proveedores'),
  crearProveedor: (d: { nombre: string; contacto?: string }) => post<Proveedor>('/proveedores', d),
  ingredientes: () => req<Ingrediente[]>('/ingredientes'),
  crearIngrediente: (d: unknown) => post<Ingrediente>('/ingredientes', d),
  desactivarIngrediente: (id: number) => req<void>(`/ingredientes/${id}`, { method: 'DELETE' }),
  compras: (ingId: number) => req<Compra[]>(`/ingredientes/${ingId}/compras`),
  registrarCompra: (d: unknown) => post<CompraRegistrada>('/compras', d),
  recetas: () => req<RecetaResumen[]>('/recetas'),
  receta: (id: number) => req<RecetaDetalle>(`/recetas/${id}`),
  crearReceta: (d: unknown) => post<RecetaDetalle>('/recetas', d),
  editarReceta: (id: number, d: unknown) => req<RecetaDetalle>(`/recetas/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  agregarComponente: (id: number, d: unknown) => post<RecetaDetalle>(`/recetas/${id}/componentes`, d),
  quitarComponente: (id: number, compId: number) => req<RecetaDetalle>(`/recetas/${id}/componentes/${compId}`, { method: 'DELETE' }),
}
