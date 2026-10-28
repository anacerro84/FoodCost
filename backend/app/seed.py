"""Carga datos de ejemplo (negocio ficticio) para probar el flujo 1.

Uso:  python -m app.seed
"""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from .main import app

HOY = date.today()


def main():
    with TestClient(app) as c:
        if c.get("/api/ingredientes").json():
            print("Ya hay datos; no se carga nada.")
            return
        u = {x["simbolo"]: x["id"] for x in c.get("/api/unidades").json()}
        cat = {n: c.post("/api/categorias", json={"nombre": n}).json()["id"]
               for n in ["Cárnicos", "Lácteos", "Panadería", "Verduras", "Salsas"]}
        prov = {n: c.post("/api/proveedores", json={"nombre": n}).json()["id"]
                for n in ["Carnes del Caribe", "Bazurto mayorista", "Distribuidora Costa"]}
        ings = [  # nombre, categoría, unidad base, merma %, compras (cantidad, unidad, precio, proveedor)
            ("Carne molida de res", "Cárnicos", "g", 5, [(5, "kg", 140000, "Carnes del Caribe"), (5, "kg", 157500, "Carnes del Caribe")]),
            ("Pan brioche", "Panadería", "und", 0, [(2, "doc", 22800, "Distribuidora Costa")]),
            ("Queso cheddar tajado", "Lácteos", "g", 0, [(1, "kg", 40000, "Distribuidora Costa")]),
            ("Tomate chonto", "Verduras", "g", 12, [(3, "kg", 16800, "Bazurto mayorista"), (3, "kg", 19200, "Bazurto mayorista")]),
            ("Lechuga batavia", "Verduras", "g", 25, [(1, "kg", 7000, "Bazurto mayorista")]),
            ("Mayonesa", "Salsas", "g", 0, [(3, "kg", 45000, "Distribuidora Costa")]),
            ("Ajo", "Verduras", "g", 15, [(500, "g", 10000, "Bazurto mayorista")]),
        ]
        ids = {}
        for nombre, c_, ub, merma, compras in ings:
            ids[nombre] = c.post("/api/ingredientes", json={
                "nombre": nombre, "categoria_id": cat[c_], "unidad_base_id": u[ub], "merma_pct": merma}).json()["id"]
            for k, (cant, un, precio, p) in enumerate(compras):
                c.post("/api/compras", json={
                    "ingrediente_id": ids[nombre], "proveedor_id": prov[p],
                    "fecha": str(HOY - timedelta(days=30 * (len(compras) - 1 - k))),
                    "cantidad": cant, "unidad_id": u[un], "precio_total": precio})
        salsa = c.post("/api/recetas", json={"nombre": "Salsa de la casa", "es_subreceta": True,
                       "rendimiento_cantidad": 205, "rendimiento_unidad_id": u["g"]}).json()["id"]
        for n, q in [("Mayonesa", 200), ("Ajo", 10)]:
            c.post(f"/api/recetas/{salsa}/componentes", json={"ingrediente_id": ids[n], "cantidad": q, "unidad_id": u["g"]})
        burger = c.post("/api/recetas", json={"nombre": "Hamburguesa clásica", "porciones": 1,
                        "precio_venta": 22000, "margen_objetivo_pct": 68}).json()["id"]
        for n, q, un in [("Pan brioche", 1, "und"), ("Carne molida de res", 150, "g"),
                         ("Queso cheddar tajado", 30, "g"), ("Tomate chonto", 40, "g"), ("Lechuga batavia", 20, "g")]:
            c.post(f"/api/recetas/{burger}/componentes", json={"ingrediente_id": ids[n], "cantidad": q, "unidad_id": u[un]})
        r = c.post(f"/api/recetas/{burger}/componentes", json={"subreceta_id": salsa, "cantidad": 30, "unidad_id": u["g"]}).json()
        print(f"Datos cargados. Hamburguesa: costo {r['costo_porcion']}, Food Cost {r['food_cost_pct']}%")


if __name__ == "__main__":
    main()
