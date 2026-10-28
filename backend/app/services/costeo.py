"""Motor de costeo de FoodCost AI.

Fórmulas (las mismas del documento del proyecto):
  costo de un ingrediente en la receta = cantidad_base * costo_unitario / (1 - merma)
  costo de una subreceta en la receta  = cantidad_base * (costo_total_subreceta / rendimiento_base)
  costo por porción = costo_total / porciones
  margen            = precio_venta - costo_por_porcion
  Food Cost %       = costo_por_porcion / precio_venta * 100
  precio objetivo   = costo_por_porcion / (1 - margen_objetivo)
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from ..models import Receta, RecetaComponente, Unidad

CIEN = Decimal(100)
FC_RENTABLE = Decimal(30)   # Food Cost <= 30 %  -> rentable
FC_REVISAR = Decimal(35)    # 30 % < FC <= 35 %  -> revisar; > 35 % en riesgo


class ErrorCosteo(ValueError):
    """Error de datos que impide costear (unidad incompatible, ciclo, etc.)."""


@dataclass
class LineaCosto:
    componente_id: int
    nombre: str
    tipo: str               # "ingrediente" | "subreceta"
    cantidad: Decimal
    unidad: str
    merma_pct: Decimal
    costo: Decimal | None   # None si el ingrediente aún no tiene precio
    participacion_pct: Decimal | None = None


@dataclass
class ResultadoCosteo:
    costo_total: Decimal
    costo_porcion: Decimal
    lineas: list[LineaCosto] = field(default_factory=list)
    faltan_precios: list[str] = field(default_factory=list)


def a_base(cantidad: Decimal, unidad: Unidad) -> Decimal:
    """Convierte una cantidad a la unidad base de su tipo (g, ml o und)."""
    return Decimal(cantidad) * Decimal(unidad.factor_base)


def validar_unidad(unidad: Unidad, esperada: Unidad, contexto: str) -> None:
    if unidad.tipo != esperada.tipo:
        raise ErrorCosteo(
            f"{contexto}: la unidad '{unidad.simbolo}' ({unidad.tipo}) no es compatible "
            f"con '{esperada.simbolo}' ({esperada.tipo})")


def costo_unitario_compra(precio_total: Decimal, cantidad: Decimal, unidad: Unidad) -> Decimal:
    """Precio de una compra llevado a costo por unidad base. Ej.: 5 kg a $157.500 -> $31,5/g."""
    return Decimal(precio_total) / a_base(cantidad, unidad)


def costo_linea(comp: RecetaComponente, _visitadas: frozenset[int]) -> tuple[Decimal | None, Decimal, list[str]]:
    """Devuelve (costo, merma aplicada, ingredientes sin precio) de un componente."""
    cantidad_base = a_base(comp.cantidad, comp.unidad)
    if comp.ingrediente is not None:
        ing = comp.ingrediente
        validar_unidad(comp.unidad, ing.unidad_base, f"Ingrediente '{ing.nombre}'")
        merma = Decimal(comp.merma_pct if comp.merma_pct is not None else ing.merma_pct)
        if ing.costo_unitario is None:
            return None, merma, [ing.nombre]
        costo = cantidad_base * Decimal(ing.costo_unitario) / (1 - merma / CIEN)
        return costo, merma, []

    sub = comp.subreceta
    if sub.id in _visitadas:
        raise ErrorCosteo(f"La subreceta '{sub.nombre}' genera un ciclo")
    if not sub.rendimiento_cantidad or sub.rendimiento_unidad is None:
        raise ErrorCosteo(f"La subreceta '{sub.nombre}' no tiene rendimiento definido")
    validar_unidad(comp.unidad, sub.rendimiento_unidad, f"Subreceta '{sub.nombre}'")
    res = costear(sub, _visitadas)
    rendimiento_base = a_base(sub.rendimiento_cantidad, sub.rendimiento_unidad)
    costo = cantidad_base * res.costo_total / rendimiento_base
    return costo, Decimal(0), res.faltan_precios


def costear(receta: Receta, _visitadas: frozenset[int] = frozenset()) -> ResultadoCosteo:
    """Costea una receta recorriendo sus componentes (y subrecetas de forma recursiva)."""
    visitadas = _visitadas | {receta.id}
    lineas: list[LineaCosto] = []
    faltan: list[str] = []
    total = Decimal(0)
    for comp in receta.componentes:
        costo, merma, sin_precio = costo_linea(comp, visitadas)
        faltan += sin_precio
        if costo is not None:
            total += costo
        es_ing = comp.ingrediente is not None
        lineas.append(LineaCosto(
            componente_id=comp.id,
            nombre=comp.ingrediente.nombre if es_ing else comp.subreceta.nombre,
            tipo="ingrediente" if es_ing else "subreceta",
            cantidad=Decimal(comp.cantidad), unidad=comp.unidad.simbolo,
            merma_pct=merma, costo=costo))
    for l in lineas:
        if l.costo is not None and total > 0:
            l.participacion_pct = l.costo / total * CIEN
    lineas.sort(key=lambda l: l.costo or Decimal(0), reverse=True)
    porciones = Decimal(receta.porciones or 1)
    return ResultadoCosteo(costo_total=total, costo_porcion=total / porciones,
                           lineas=lineas, faltan_precios=sorted(set(faltan)))


def estado_food_cost(fc_pct: Decimal) -> str:
    if fc_pct <= FC_RENTABLE:
        return "rentable"
    if fc_pct <= FC_REVISAR:
        return "revisar"
    return "en_riesgo"


def rentabilidad(costo_porcion: Decimal, precio_venta: Decimal | None,
                 margen_objetivo_pct: Decimal | None) -> dict:
    """Margen, Food Cost % y precio sugerido para el margen objetivo."""
    out: dict = {"margen": None, "margen_pct": None, "food_cost_pct": None,
                 "estado": None, "precio_objetivo": None}
    if precio_venta:
        pv = Decimal(precio_venta)
        out["margen"] = pv - costo_porcion
        out["margen_pct"] = (pv - costo_porcion) / pv * CIEN
        out["food_cost_pct"] = costo_porcion / pv * CIEN
        out["estado"] = estado_food_cost(out["food_cost_pct"])
    if margen_objetivo_pct is not None and Decimal(margen_objetivo_pct) < CIEN:
        bruto = costo_porcion / (1 - Decimal(margen_objetivo_pct) / CIEN)
        # Se redondea hacia arriba a la centena, como se cobra en la carta
        out["precio_objetivo"] = (bruto / CIEN).to_integral_value(rounding="ROUND_CEILING") * CIEN
    return out


def redondear(valor: Decimal | None, decimales: int = 2) -> float | None:
    if valor is None:
        return None
    return float(Decimal(valor).quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP))
