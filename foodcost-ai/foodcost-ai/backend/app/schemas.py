"""Esquemas de entrada y salida de la API (validación con Pydantic)."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Unidades y categorías ----------
class UnidadOut(ORM):
    id: int
    nombre: str
    simbolo: str
    tipo: str
    factor_base: float


class CategoriaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)


class CategoriaOut(ORM):
    id: int
    nombre: str


# ---------- Proveedores ----------
class ProveedorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    contacto: str | None = None


class ProveedorOut(ORM):
    id: int
    nombre: str
    contacto: str | None


# ---------- Ingredientes ----------
class IngredienteIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    categoria_id: int | None = None
    unidad_base_id: int
    merma_pct: Decimal = Field(default=Decimal(0), ge=0, lt=100)
    stock_minimo: Decimal = Field(default=Decimal(0), ge=0)


class IngredienteOut(ORM):
    id: int
    nombre: str
    categoria: CategoriaOut | None
    unidad_base: UnidadOut
    merma_pct: float
    costo_unitario: float | None
    stock_minimo: float
    activo: bool


# ---------- Compras ----------
class CompraIn(BaseModel):
    ingrediente_id: int
    proveedor_id: int | None = None
    fecha: date
    cantidad: Decimal = Field(gt=0)
    unidad_id: int
    precio_total: Decimal = Field(ge=0)


class CompraOut(ORM):
    id: int
    ingrediente_id: int
    proveedor: ProveedorOut | None
    fecha: date
    cantidad: float
    unidad: UnidadOut
    precio_total: float
    costo_unitario_base: float


class CompraRegistrada(BaseModel):
    compra: CompraOut
    costo_anterior: float | None
    costo_nuevo: float
    variacion_pct: float | None
    recetas_afectadas: list[str]


# ---------- Recetas ----------
class RecetaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    es_subreceta: bool = False
    rendimiento_cantidad: Decimal | None = Field(default=None, gt=0)
    rendimiento_unidad_id: int | None = None
    porciones: int = Field(default=1, gt=0)
    precio_venta: Decimal | None = Field(default=None, gt=0)
    margen_objetivo_pct: Decimal | None = Field(default=None, ge=0, lt=100)

    @model_validator(mode="after")
    def subreceta_con_rendimiento(self):
        if self.es_subreceta and (self.rendimiento_cantidad is None or self.rendimiento_unidad_id is None):
            raise ValueError("Una subreceta necesita rendimiento (cantidad y unidad)")
        return self


class ComponenteIn(BaseModel):
    ingrediente_id: int | None = None
    subreceta_id: int | None = None
    cantidad: Decimal = Field(gt=0)
    unidad_id: int
    merma_pct: Decimal | None = Field(default=None, ge=0, lt=100)

    @model_validator(mode="after")
    def uno_solo(self):
        if (self.ingrediente_id is None) == (self.subreceta_id is None):
            raise ValueError("Indique un ingrediente o una subreceta (solo uno)")
        return self


class LineaOut(BaseModel):
    componente_id: int
    nombre: str
    tipo: str
    cantidad: float
    unidad: str
    merma_pct: float
    costo: float | None
    participacion_pct: float | None


class RecetaResumen(BaseModel):
    id: int
    nombre: str
    es_subreceta: bool
    porciones: int
    precio_venta: float | None
    costo_total: float
    costo_porcion: float
    margen: float | None
    food_cost_pct: float | None
    estado: str | None
    faltan_precios: list[str]


class RecetaDetalle(RecetaResumen):
    rendimiento_cantidad: float | None
    rendimiento_unidad: UnidadOut | None
    margen_objetivo_pct: float | None
    margen_pct: float | None
    precio_objetivo: float | None
    lineas: list[LineaOut]
