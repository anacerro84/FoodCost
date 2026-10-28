# FoodCost AI

Plataforma web para que restaurantes, cafeterías y panaderías pequeñas conozcan el costo real de cada producto, su margen y su Food Cost, y detecten a tiempo cuándo un producto deja de ser rentable.

Proyecto de Ingeniería I · Universidad Tecnológica de Bolívar · 2026-02
Equipo: Sara Paola Vargas Vásquez · Ana Cerro Pérez

## Estado actual: Avance 4 (v0.4)

Funciona de extremo a extremo el **flujo 1: costear una receta**.

1. Registrar ingredientes con unidad base (g, ml o und), categoría y porcentaje de merma.
2. Registrar compras en cualquier unidad compatible (kg, lb, l, docena…). El sistema convierte a la unidad base y guarda el historial de precios.
3. Crear recetas y subrecetas (con porciones, rendimiento, precio de venta y margen objetivo).
4. Agregar ingredientes o subrecetas a una receta.
5. Ver el costo por porción, el margen, el Food Cost %, el estado (rentable / revisar / en riesgo), el peso de cada componente en el costo y el precio sugerido para el margen objetivo.
6. Si se registra un precio nuevo, todas las recetas que usan ese ingrediente (también a través de subrecetas) quedan recalculadas y se informa la variación.

| Requerimiento | Estado |
|---|---|
| RF-01 Ingredientes · RF-02 Unidades y conversiones · RF-03 Proveedores e historial de precios | Implementado |
| RF-04 Recetas y subrecetas · RF-05 Merma · RF-06 Costo automático · RF-07 Margen y Food Cost | Implementado |
| RF-08 Recalculo al cambiar precios | Implementado (el costo se calcula siempre con el precio vigente) |
| RF-12 Ingredientes de mayor impacto · RF-14 Precio para margen objetivo | Implementado (versión básica) |
| RF-17 Autenticación | Sprint 3 (por ahora se usa un único negocio) |
| RF-09 Inventario · RF-10 Dashboard · RF-11 Alertas · RF-13 Simulador | Sprints 3-4 |
| RF-15 Pronóstico · RF-16 Explicaciones IA · RF-18 Importar CSV | Sprints 5-6 |

## Arquitectura

![Arquitectura](docs/arquitectura.png)

- **Frontend**: React 18 + TypeScript (Vite) y React Router. Se comunica con la API por HTTP/JSON (`src/api.ts`).
- **Backend**: API REST con FastAPI. Está organizado en routers (`catalogo`, `compras`, `recetas`), un servicio de dominio (`services/costeo.py`) con todas las fórmulas y modelos SQLAlchemy 2.0.
- **Base de datos**: PostgreSQL 16. Las tablas se crean al iniciar la API.

El motor de costeo está separado de los routers para que el dashboard, el simulador y las alertas reutilicen exactamente el mismo cálculo.

### Fórmulas

```
costo ingrediente en la receta = cantidad (en unidad base) × costo unitario ÷ (1 − merma)
costo subreceta en la receta   = cantidad × costo total de la subreceta ÷ rendimiento
costo por porción              = costo total ÷ porciones
margen                         = precio de venta − costo por porción
Food Cost %                    = costo por porción ÷ precio de venta × 100
precio para margen objetivo    = costo por porción ÷ (1 − margen objetivo), redondeado a la centena
```

Estados: Food Cost ≤ 30 % rentable, ≤ 35 % revisar, > 35 % en riesgo.

### Modelo de datos

![Modelo de datos](docs/modelo-datos.png)

## Cómo ejecutarlo

### Opción A: Docker (recomendada)

```bash
docker compose up --build
docker compose exec api python -m app.seed   # opcional: datos de ejemplo
```

- Aplicación: http://localhost:5173
- Documentación de la API (Swagger): http://localhost:8000/docs

### Opción B: local

Requisitos: Python 3.12+, Node 20+ y PostgreSQL 16 con una base llamada `foodcost`.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate     # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # ajustar usuario/clave de PostgreSQL
python -m app.seed                                     # opcional: datos de ejemplo
uvicorn app.main:app --reload                          # http://localhost:8000/docs

# Frontend (otra terminal)
cd frontend
npm install
npm run dev                                            # http://localhost:5173
```

## Pruebas

```bash
# Backend: 9 pruebas de la API y del motor de costeo (SQLite temporal por defecto)
cd backend && pytest -q
# Contra PostgreSQL:
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/foodcost_test pytest -q

# Extremo a extremo (UI → API → PostgreSQL), con la API y el frontend en ejecución
# y la base recién cargada con `python -m app.seed`:
cd frontend && npx playwright install chromium && npm run e2e
```

Los valores esperados de las pruebas se calcularon a mano con las fórmulas de arriba. La prueba de extremo a extremo guarda capturas en `docs/evidencias/`.

El pipeline de GitHub Actions (`.github/workflows/ci.yml`) corre las pruebas del backend sobre PostgreSQL y el lint y el build del frontend en cada push.

## Endpoints principales

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/unidades` | Unidades y factores de conversión |
| GET/POST | `/api/categorias`, `/api/proveedores` | Catálogos |
| GET/POST | `/api/ingredientes` | Listar / crear ingrediente |
| PUT/DELETE | `/api/ingredientes/{id}` | Editar / desactivar |
| GET | `/api/ingredientes/{id}/compras` | Historial de precios |
| POST | `/api/compras` | Registrar compra (actualiza el costo y devuelve las recetas afectadas) |
| GET/POST | `/api/recetas` | Listar con costeo / crear |
| GET/PUT | `/api/recetas/{id}` | Detalle con desglose / editar |
| POST/DELETE | `/api/recetas/{id}/componentes` | Agregar / quitar componente |

## Estructura

```
foodcost-ai/
├── backend/
│   ├── app/
│   │   ├── main.py            # arranque, CORS, datos iniciales
│   │   ├── models.py          # modelo de datos (SQLAlchemy)
│   │   ├── schemas.py         # validación de entrada/salida (Pydantic)
│   │   ├── services/costeo.py # motor de costeo
│   │   ├── routers/           # catalogo, compras, recetas
│   │   └── seed.py            # datos de ejemplo
│   └── tests/
├── frontend/
│   ├── src/pages/             # Rentabilidad, Ingredientes, Recetas, Proveedores
│   └── e2e/flujo1.spec.ts     # prueba de extremo a extremo
├── docs/                      # diagramas y evidencias
└── docker-compose.yml
```
