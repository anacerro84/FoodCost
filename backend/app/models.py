"""Modelo de datos consolidado (Avance 4).

Implementado en esta entrega: NEGOCIO, UNIDAD, CATEGORIA, INGREDIENTE, PROVEEDOR,
PRECIO_COMPRA, RECETA y RECETA_COMPONENTE (lo que necesita el flujo 1).
Las tablas de inventario, alertas, simulaciones y pronósticos se agregan en los
siguientes sprints.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric,
                        String, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

TIPOS_UNIDAD = ("masa", "volumen", "unidad")


class Negocio(Base):
    __tablename__ = "negocio"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(40), default="restaurante")
    moneda: Mapped[str] = mapped_column(String(3), default="COP")
    umbral_alerta_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=8)


class Unidad(Base):
    """Unidades de medida. factor_base convierte a la unidad base del tipo
    (g para masa, ml para volumen, und para unidad). Ej.: kg -> 1000."""
    __tablename__ = "unidad"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30))
    simbolo: Mapped[str] = mapped_column(String(10), unique=True)
    tipo: Mapped[str] = mapped_column(String(10))
    factor_base: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    __table_args__ = (CheckConstraint("tipo in ('masa','volumen','unidad')", name="ck_unidad_tipo"),
                      CheckConstraint("factor_base > 0", name="ck_unidad_factor"))


class Categoria(Base):
    __tablename__ = "categoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    negocio_id: Mapped[int] = mapped_column(ForeignKey("negocio.id"))
    nombre: Mapped[str] = mapped_column(String(60))
    __table_args__ = (UniqueConstraint("negocio_id", "nombre"),)


class Proveedor(Base):
    __tablename__ = "proveedor"
    id: Mapped[int] = mapped_column(primary_key=True)
    negocio_id: Mapped[int] = mapped_column(ForeignKey("negocio.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    contacto: Mapped[str | None] = mapped_column(String(120))


class Ingrediente(Base):
    __tablename__ = "ingrediente"
    id: Mapped[int] = mapped_column(primary_key=True)
    negocio_id: Mapped[int] = mapped_column(ForeignKey("negocio.id"))
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categoria.id"))
    unidad_base_id: Mapped[int] = mapped_column(ForeignKey("unidad.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    merma_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    # Costo por unidad base (por g, ml o und) según la compra más reciente
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    stock_minimo: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    unidad_base: Mapped[Unidad] = relationship()
    categoria: Mapped[Categoria | None] = relationship()
    __table_args__ = (UniqueConstraint("negocio_id", "nombre"),
                      CheckConstraint("merma_pct >= 0 and merma_pct < 100", name="ck_ing_merma"))


class PrecioCompra(Base):
    """Historial de compras: de aquí sale el costo actual del ingrediente."""
    __tablename__ = "precio_compra"
    id: Mapped[int] = mapped_column(primary_key=True)
    ingrediente_id: Mapped[int] = mapped_column(ForeignKey("ingrediente.id"), index=True)
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedor.id"))
    fecha: Mapped[date] = mapped_column(Date)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidad.id"))
    precio_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    costo_unitario_base: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    unidad: Mapped[Unidad] = relationship()
    proveedor: Mapped[Proveedor | None] = relationship()
    __table_args__ = (CheckConstraint("cantidad > 0", name="ck_compra_cantidad"),
                      CheckConstraint("precio_total >= 0", name="ck_compra_precio"))


class Receta(Base):
    __tablename__ = "receta"
    id: Mapped[int] = mapped_column(primary_key=True)
    negocio_id: Mapped[int] = mapped_column(ForeignKey("negocio.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    es_subreceta: Mapped[bool] = mapped_column(Boolean, default=False)
    # Para subrecetas: cuánto produce la preparación (ej. 205 g de salsa)
    rendimiento_cantidad: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    rendimiento_unidad_id: Mapped[int | None] = mapped_column(ForeignKey("unidad.id"))
    porciones: Mapped[int] = mapped_column(default=1)
    precio_venta: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    margen_objetivo_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    rendimiento_unidad: Mapped[Unidad | None] = relationship()
    componentes: Mapped[list["RecetaComponente"]] = relationship(
        back_populates="receta", cascade="all, delete-orphan",
        foreign_keys="RecetaComponente.receta_id")
    __table_args__ = (UniqueConstraint("negocio_id", "nombre"),
                      CheckConstraint("porciones > 0", name="ck_receta_porciones"))


class RecetaComponente(Base):
    """Un componente es un ingrediente O una subreceta (nunca ambos)."""
    __tablename__ = "receta_componente"
    id: Mapped[int] = mapped_column(primary_key=True)
    receta_id: Mapped[int] = mapped_column(ForeignKey("receta.id", ondelete="CASCADE"), index=True)
    ingrediente_id: Mapped[int | None] = mapped_column(ForeignKey("ingrediente.id"))
    subreceta_id: Mapped[int | None] = mapped_column(ForeignKey("receta.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidad.id"))
    # Si es nulo se usa la merma del ingrediente
    merma_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    receta: Mapped[Receta] = relationship(back_populates="componentes", foreign_keys=[receta_id])
    ingrediente: Mapped[Ingrediente | None] = relationship()
    subreceta: Mapped[Receta | None] = relationship(foreign_keys=[subreceta_id])
    unidad: Mapped[Unidad] = relationship()
    __table_args__ = (
        CheckConstraint("(ingrediente_id is null) <> (subreceta_id is null)", name="ck_comp_tipo"),
        CheckConstraint("cantidad > 0", name="ck_comp_cantidad"),
    )
