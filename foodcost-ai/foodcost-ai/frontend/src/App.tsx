import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import Inicio from './pages/Inicio'
import Ingredientes from './pages/Ingredientes'
import IngredienteDetalle from './pages/IngredienteDetalle'
import Proveedores from './pages/Proveedores'
import Recetas from './pages/Recetas'
import RecetaDetalle from './pages/RecetaDetalle'

export default function App() {
  return (
    <div className="app">
      <nav aria-label="Menú principal">
        <div className="brand">FoodCost <span>AI</span></div>
        <NavLink to="/" end>Rentabilidad</NavLink>
        <NavLink to="/ingredientes">Ingredientes</NavLink>
        <NavLink to="/recetas">Recetas</NavLink>
        <NavLink to="/proveedores">Proveedores</NavLink>
        <div className="nav-foot">v0.4 · Avance 4</div>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/ingredientes" element={<Ingredientes />} />
          <Route path="/ingredientes/:id" element={<IngredienteDetalle />} />
          <Route path="/recetas" element={<Recetas />} />
          <Route path="/recetas/:id" element={<RecetaDetalle />} />
          <Route path="/proveedores" element={<Proveedores />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  )
}
