"""Unidades, categorías, proveedores e ingredientes (RF-01, RF-02, RF-03)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import NEGOCIO_ID
from ..models import Categoria, Ingrediente, Proveedor, Unidad
from ..schemas import (CategoriaIn, CategoriaOut, IngredienteIn, IngredienteOut, ProveedorIn,
                       ProveedorOut, UnidadOut)

router = APIRouter(prefix="/api", tags=["catálogo"])


def guardar(db: Session, obj, mensaje_duplicado: str):
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, mensaje_duplicado)
    db.refresh(obj)
    return obj


@router.get("/unidades", response_model=list[UnidadOut])
def listar_unidades(db: Session = Depends(get_db)):
    return db.scalars(select(Unidad).order_by(Unidad.tipo, Unidad.factor_base)).all()


@router.get("/categorias", response_model=list[CategoriaOut])
def listar_categorias(db: Session = Depends(get_db)):
    return db.scalars(select(Categoria).where(Categoria.negocio_id == NEGOCIO_ID)
                      .order_by(Categoria.nombre)).all()


@router.post("/categorias", response_model=CategoriaOut, status_code=201)
def crear_categoria(data: CategoriaIn, db: Session = Depends(get_db)):
    return guardar(db, Categoria(negocio_id=NEGOCIO_ID, **data.model_dump()), "La categoría ya existe")


@router.get("/proveedores", response_model=list[ProveedorOut])
def listar_proveedores(db: Session = Depends(get_db)):
    return db.scalars(select(Proveedor).where(Proveedor.negocio_id == NEGOCIO_ID)
                      .order_by(Proveedor.nombre)).all()


@router.post("/proveedores", response_model=ProveedorOut, status_code=201)
def crear_proveedor(data: ProveedorIn, db: Session = Depends(get_db)):
    return guardar(db, Proveedor(negocio_id=NEGOCIO_ID, **data.model_dump()), "El proveedor ya existe")


def obtener_ingrediente(db: Session, ingrediente_id: int) -> Ingrediente:
    ing = db.get(Ingrediente, ingrediente_id)
    if ing is None or ing.negocio_id != NEGOCIO_ID:
        raise HTTPException(404, "Ingrediente no encontrado")
    return ing


def validar_ingrediente(db: Session, data: IngredienteIn):
    unidad = db.get(Unidad, data.unidad_base_id)
    if unidad is None:
        raise HTTPException(422, "Unidad no encontrada")
    if unidad.factor_base != 1:
        raise HTTPException(422, "La unidad base debe ser g, ml o und (las demás se convierten)")
    if data.categoria_id is not None and db.get(Categoria, data.categoria_id) is None:
        raise HTTPException(422, "Categoría no encontrada")


@router.get("/ingredientes", response_model=list[IngredienteOut])
def listar_ingredientes(incluir_inactivos: bool = False, db: Session = Depends(get_db)):
    q = select(Ingrediente).where(Ingrediente.negocio_id == NEGOCIO_ID)
    if not incluir_inactivos:
        q = q.where(Ingrediente.activo.is_(True))
    return db.scalars(q.order_by(Ingrediente.nombre)).all()


@router.post("/ingredientes", response_model=IngredienteOut, status_code=201)
def crear_ingrediente(data: IngredienteIn, db: Session = Depends(get_db)):
    validar_ingrediente(db, data)
    return guardar(db, Ingrediente(negocio_id=NEGOCIO_ID, **data.model_dump()),
                   "Ya existe un ingrediente con ese nombre")


@router.put("/ingredientes/{ingrediente_id}", response_model=IngredienteOut)
def editar_ingrediente(ingrediente_id: int, data: IngredienteIn, db: Session = Depends(get_db)):
    ing = obtener_ingrediente(db, ingrediente_id)
    validar_ingrediente(db, data)
    if ing.costo_unitario is not None and data.unidad_base_id != ing.unidad_base_id:
        raise HTTPException(409, "No se puede cambiar la unidad base de un ingrediente con compras")
    for k, v in data.model_dump().items():
        setattr(ing, k, v)
    return guardar(db, ing, "Ya existe un ingrediente con ese nombre")


@router.delete("/ingredientes/{ingrediente_id}", status_code=204)
def desactivar_ingrediente(ingrediente_id: int, db: Session = Depends(get_db)):
    """No se borra para conservar el historial; solo se desactiva."""
    ing = obtener_ingrediente(db, ingrediente_id)
    ing.activo = False
    db.commit()
