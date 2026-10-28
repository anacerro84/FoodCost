"""Punto de entrada de la API de FoodCost AI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .config import settings
from .database import Base, SessionLocal, engine
from .deps import NEGOCIO_ID
from .models import Negocio, Unidad
from .routers import catalogo, compras, recetas

UNIDADES = [  # nombre, símbolo, tipo, factor a la unidad base
    ("gramo", "g", "masa", 1), ("kilogramo", "kg", "masa", 1000), ("libra", "lb", "masa", 500),
    ("mililitro", "ml", "volumen", 1), ("litro", "l", "volumen", 1000),
    ("unidad", "und", "unidad", 1), ("docena", "doc", "unidad", 12),
]


def datos_iniciales():
    """Crea las tablas, las unidades y el negocio por defecto si no existen."""
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.get(Negocio, NEGOCIO_ID) is None:
            db.add(Negocio(id=NEGOCIO_ID, nombre="Mi negocio"))
        existentes = set(db.scalars(select(Unidad.simbolo)))
        for nombre, simbolo, tipo, factor in UNIDADES:
            if simbolo not in existentes:
                db.add(Unidad(nombre=nombre, simbolo=simbolo, tipo=tipo, factor_base=factor))
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    datos_iniciales()
    yield


app = FastAPI(title="FoodCost AI API", version="0.4.0", lifespan=lifespan,
              description="Avance 4: flujo de costeo de recetas de extremo a extremo.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","),
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(catalogo.router)
app.include_router(compras.router)
app.include_router(recetas.router)


@app.get("/api/health", tags=["sistema"])
def health():
    return {"estado": "ok"}
