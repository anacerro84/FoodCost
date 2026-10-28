"""Registro de compras e historial de precios (RF-03, RF-08)."""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PrecioCompra, Proveedor, Receta, RecetaComponente, Unidad
from ..schemas import CompraIn, CompraOut, CompraRegistrada
from ..services.costeo import ErrorCosteo, costo_unitario_compra, validar_unidad
from .catalogo import obtener_ingrediente

router = APIRouter(prefix="/api", tags=["compras"])


def recetas_que_usan(db: Session, ingrediente_id: int) -> list[str]:
    """Recetas que usan el ingrediente directamente o a través de una subreceta."""
    nombres: set[str] = set()
    pendientes = set(db.scalars(select(RecetaComponente.receta_id)
                                .where(RecetaComponente.ingrediente_id == ingrediente_id)))
    vistas: set[int] = set()
    while pendientes:
        rid = pendientes.pop()
        if rid in vistas:
            continue
        vistas.add(rid)
        nombres.add(db.get(Receta, rid).nombre)
        pendientes |= set(db.scalars(select(RecetaComponente.receta_id)
                                     .where(RecetaComponente.subreceta_id == rid)))
    return sorted(nombres)


@router.get("/ingredientes/{ingrediente_id}/compras", response_model=list[CompraOut])
def historial(ingrediente_id: int, db: Session = Depends(get_db)):
    obtener_ingrediente(db, ingrediente_id)
    return db.scalars(select(PrecioCompra).where(PrecioCompra.ingrediente_id == ingrediente_id)
                      .order_by(PrecioCompra.fecha.desc(), PrecioCompra.id.desc())).all()


@router.post("/compras", response_model=CompraRegistrada, status_code=201)
def registrar_compra(data: CompraIn, db: Session = Depends(get_db)):
    ing = obtener_ingrediente(db, data.ingrediente_id)
    unidad = db.get(Unidad, data.unidad_id)
    if unidad is None:
        raise HTTPException(422, "Unidad no encontrada")
    if data.proveedor_id is not None and db.get(Proveedor, data.proveedor_id) is None:
        raise HTTPException(422, "Proveedor no encontrado")
    try:
        validar_unidad(unidad, ing.unidad_base, f"Compra de '{ing.nombre}'")
    except ErrorCosteo as e:
        raise HTTPException(422, str(e))

    costo_nuevo = costo_unitario_compra(data.precio_total, data.cantidad, unidad)
    compra = PrecioCompra(**data.model_dump(), costo_unitario_base=costo_nuevo)
    db.add(compra)
    db.flush()

    # El costo vigente es el de la compra más reciente (por fecha y luego por registro)
    ultima = db.scalars(select(PrecioCompra).where(PrecioCompra.ingrediente_id == ing.id)
                        .order_by(PrecioCompra.fecha.desc(), PrecioCompra.id.desc()).limit(1)).one()
    anterior = ing.costo_unitario
    ing.costo_unitario = ultima.costo_unitario_base
    db.commit()
    db.refresh(compra)

    variacion = None
    if anterior:
        variacion = float((Decimal(ing.costo_unitario) - Decimal(anterior)) / Decimal(anterior) * 100)
    return CompraRegistrada(
        compra=CompraOut.model_validate(compra),
        costo_anterior=float(anterior) if anterior is not None else None,
        costo_nuevo=float(ing.costo_unitario),
        variacion_pct=round(variacion, 2) if variacion is not None else None,
        recetas_afectadas=recetas_que_usan(db, ing.id))
