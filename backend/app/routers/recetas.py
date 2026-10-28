"""Recetas, subrecetas, componentes y costeo (RF-04 a RF-07, RF-12, RF-14)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import NEGOCIO_ID
from ..models import Receta, RecetaComponente, Unidad
from ..schemas import ComponenteIn, LineaOut, RecetaDetalle, RecetaIn, RecetaResumen, UnidadOut
from ..services.costeo import ErrorCosteo, costear, redondear, rentabilidad, validar_unidad
from .catalogo import obtener_ingrediente

router = APIRouter(prefix="/api/recetas", tags=["recetas"])


def obtener_receta(db: Session, receta_id: int) -> Receta:
    r = db.get(Receta, receta_id)
    if r is None or r.negocio_id != NEGOCIO_ID:
        raise HTTPException(404, "Receta no encontrada")
    return r


def resumen(r: Receta) -> dict:
    try:
        res = costear(r)
    except ErrorCosteo as e:
        raise HTTPException(422, str(e))
    rent = rentabilidad(res.costo_porcion, r.precio_venta, r.margen_objetivo_pct)
    return dict(
        id=r.id, nombre=r.nombre, es_subreceta=r.es_subreceta, porciones=r.porciones,
        precio_venta=redondear(r.precio_venta), costo_total=redondear(res.costo_total),
        costo_porcion=redondear(res.costo_porcion), margen=redondear(rent["margen"]),
        food_cost_pct=redondear(rent["food_cost_pct"]), estado=rent["estado"],
        faltan_precios=res.faltan_precios, _res=res, _rent=rent)


@router.get("", response_model=list[RecetaResumen])
def listar(db: Session = Depends(get_db)):
    recetas = db.scalars(select(Receta).where(Receta.negocio_id == NEGOCIO_ID)
                         .order_by(Receta.es_subreceta, Receta.nombre)).all()
    return [resumen(r) for r in recetas]


@router.get("/{receta_id}", response_model=RecetaDetalle)
def detalle(receta_id: int, db: Session = Depends(get_db)):
    r = obtener_receta(db, receta_id)
    d = resumen(r)
    res, rent = d.pop("_res"), d.pop("_rent")
    d.update(
        rendimiento_cantidad=redondear(r.rendimiento_cantidad, 3),
        rendimiento_unidad=UnidadOut.model_validate(r.rendimiento_unidad) if r.rendimiento_unidad else None,
        margen_objetivo_pct=redondear(r.margen_objetivo_pct), margen_pct=redondear(rent["margen_pct"]),
        precio_objetivo=redondear(rent["precio_objetivo"]),
        lineas=[LineaOut(componente_id=l.componente_id, nombre=l.nombre, tipo=l.tipo,
                         cantidad=redondear(l.cantidad, 3), unidad=l.unidad,
                         merma_pct=redondear(l.merma_pct), costo=redondear(l.costo),
                         participacion_pct=redondear(l.participacion_pct)) for l in res.lineas])
    return d


def validar_receta(db: Session, data: RecetaIn):
    if data.rendimiento_unidad_id is not None and db.get(Unidad, data.rendimiento_unidad_id) is None:
        raise HTTPException(422, "Unidad de rendimiento no encontrada")


@router.post("", response_model=RecetaDetalle, status_code=201)
def crear(data: RecetaIn, db: Session = Depends(get_db)):
    validar_receta(db, data)
    r = Receta(negocio_id=NEGOCIO_ID, **data.model_dump())
    db.add(r)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe una receta con ese nombre")
    return detalle(r.id, db)


@router.put("/{receta_id}", response_model=RecetaDetalle)
def editar(receta_id: int, data: RecetaIn, db: Session = Depends(get_db)):
    r = obtener_receta(db, receta_id)
    validar_receta(db, data)
    for k, v in data.model_dump().items():
        setattr(r, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe una receta con ese nombre")
    return detalle(r.id, db)


@router.post("/{receta_id}/componentes", response_model=RecetaDetalle, status_code=201)
def agregar_componente(receta_id: int, data: ComponenteIn, db: Session = Depends(get_db)):
    r = obtener_receta(db, receta_id)
    unidad = db.get(Unidad, data.unidad_id)
    if unidad is None:
        raise HTTPException(422, "Unidad no encontrada")
    try:
        if data.ingrediente_id is not None:
            ing = obtener_ingrediente(db, data.ingrediente_id)
            validar_unidad(unidad, ing.unidad_base, f"Ingrediente '{ing.nombre}'")
        else:
            sub = obtener_receta(db, data.subreceta_id)
            if not sub.es_subreceta:
                raise HTTPException(422, f"'{sub.nombre}' no está marcada como subreceta")
            validar_unidad(unidad, sub.rendimiento_unidad, f"Subreceta '{sub.nombre}'")
        comp = RecetaComponente(receta_id=r.id, **data.model_dump())
        db.add(comp)
        db.flush()
        db.refresh(r)
        costear(r)  # detecta ciclos (A usa B y B usa A) antes de guardar
    except ErrorCosteo as e:
        db.rollback()
        raise HTTPException(422, str(e))
    db.commit()
    return detalle(r.id, db)


@router.delete("/{receta_id}/componentes/{componente_id}", response_model=RecetaDetalle)
def quitar_componente(receta_id: int, componente_id: int, db: Session = Depends(get_db)):
    r = obtener_receta(db, receta_id)
    comp = db.get(RecetaComponente, componente_id)
    if comp is None or comp.receta_id != r.id:
        raise HTTPException(404, "Componente no encontrado")
    db.delete(comp)
    db.commit()
    db.refresh(r)
    return detalle(r.id, db)
