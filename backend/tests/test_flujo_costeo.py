"""Pruebas del flujo 1 de extremo a extremo a través de la API.

Los valores esperados se calcularon a mano con las fórmulas del documento
(costeo manual de referencia, RNF-05).
"""
import pytest


def crear_ing(c, u, nombre, ub="g", merma=0):
    r = c.post("/api/ingredientes", json={"nombre": nombre, "unidad_base_id": u[ub], "merma_pct": merma})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def comprar(c, u, ing, cant, un, precio, fecha="2026-10-20"):
    r = c.post("/api/compras", json={"ingrediente_id": ing, "fecha": fecha, "cantidad": cant,
                                     "unidad_id": u[un], "precio_total": precio})
    assert r.status_code == 201, r.text
    return r.json()


def test_conversion_de_unidades_en_compra(client, u):
    carne = crear_ing(client, u, "Carne")
    r = comprar(client, u, carne, 5, "kg", 157500)
    assert r["costo_nuevo"] == pytest.approx(31.5)          # $157.500 / 5000 g


def test_compra_con_unidad_incompatible_falla(client, u):
    leche = crear_ing(client, u, "Leche", ub="ml")
    r = client.post("/api/compras", json={"ingrediente_id": leche, "fecha": "2026-10-20",
                                          "cantidad": 1, "unidad_id": u["kg"], "precio_total": 4000})
    assert r.status_code == 422


def test_costo_con_merma_margen_y_food_cost(client, u):
    tomate = crear_ing(client, u, "Tomate", merma=12)
    comprar(client, u, tomate, 1, "kg", 6400)               # $6,4 por g
    rec = client.post("/api/recetas", json={"nombre": "Ensalada", "precio_venta": 1000,
                                             "margen_objetivo_pct": 70}).json()["id"]
    d = client.post(f"/api/recetas/{rec}/componentes",
                    json={"ingrediente_id": tomate, "cantidad": 40, "unidad_id": u["g"]}).json()
    esperado = 40 * 6.4 / (1 - 0.12)                        # 290,91
    assert d["costo_porcion"] == pytest.approx(esperado, abs=0.01)
    assert d["margen"] == pytest.approx(1000 - esperado, abs=0.01)
    assert d["food_cost_pct"] == pytest.approx(esperado / 1000 * 100, abs=0.01)
    assert d["estado"] == "rentable"
    assert d["precio_objetivo"] == 1000                     # 290,91 / 0,30 = 969,7 -> 1.000


def test_subreceta_y_porciones(client, u):
    mayo = crear_ing(client, u, "Mayonesa")
    ajo = crear_ing(client, u, "Ajo", merma=15)
    comprar(client, u, mayo, 1, "kg", 15000)
    comprar(client, u, ajo, 500, "g", 10000)
    salsa = client.post("/api/recetas", json={"nombre": "Salsa", "es_subreceta": True,
                                               "rendimiento_cantidad": 205, "rendimiento_unidad_id": u["g"]}).json()["id"]
    client.post(f"/api/recetas/{salsa}/componentes", json={"ingrediente_id": mayo, "cantidad": 200, "unidad_id": u["g"]})
    s = client.post(f"/api/recetas/{salsa}/componentes", json={"ingrediente_id": ajo, "cantidad": 10, "unidad_id": u["g"]}).json()
    costo_salsa = 200 * 15 + 10 * 20 / 0.85                 # 3.235,29
    assert s["costo_total"] == pytest.approx(costo_salsa, abs=0.01)

    plato = client.post("/api/recetas", json={"nombre": "Papas con salsa", "porciones": 2,
                                               "precio_venta": 5000}).json()["id"]
    d = client.post(f"/api/recetas/{plato}/componentes",
                    json={"subreceta_id": salsa, "cantidad": 60, "unidad_id": u["g"]}).json()
    assert d["costo_total"] == pytest.approx(60 * costo_salsa / 205, abs=0.01)
    assert d["costo_porcion"] == pytest.approx(60 * costo_salsa / 205 / 2, abs=0.01)


def test_nuevo_precio_recalcula_la_receta(client, u):
    carne = crear_ing(client, u, "Carne", merma=5)
    comprar(client, u, carne, 5, "kg", 140000, fecha="2026-09-20")   # $28/g
    rec = client.post("/api/recetas", json={"nombre": "Hamburguesa", "precio_venta": 22000}).json()["id"]
    antes = client.post(f"/api/recetas/{rec}/componentes",
                        json={"ingrediente_id": carne, "cantidad": 150, "unidad_id": u["g"]}).json()
    r = comprar(client, u, carne, 5, "kg", 157500, fecha="2026-10-20")  # $31,5/g
    assert r["variacion_pct"] == pytest.approx(12.5)
    assert r["recetas_afectadas"] == ["Hamburguesa"]
    despues = client.get(f"/api/recetas/{rec}").json()
    assert antes["costo_porcion"] == pytest.approx(150 * 28 / 0.95, abs=0.01)
    assert despues["costo_porcion"] == pytest.approx(150 * 31.5 / 0.95, abs=0.01)


def test_compra_antigua_no_reemplaza_el_costo_vigente(client, u):
    harina = crear_ing(client, u, "Harina")
    comprar(client, u, harina, 1, "kg", 4000, fecha="2026-10-20")
    r = comprar(client, u, harina, 1, "kg", 3000, fecha="2026-08-01")
    assert r["costo_nuevo"] == pytest.approx(4.0)


def test_ingrediente_sin_precio_se_reporta(client, u):
    sal = crear_ing(client, u, "Sal")
    rec = client.post("/api/recetas", json={"nombre": "Caldo"}).json()["id"]
    d = client.post(f"/api/recetas/{rec}/componentes",
                    json={"ingrediente_id": sal, "cantidad": 5, "unidad_id": u["g"]}).json()
    assert d["faltan_precios"] == ["Sal"]
    assert d["costo_total"] == 0


def test_ciclo_entre_subrecetas_se_rechaza(client, u):
    a = client.post("/api/recetas", json={"nombre": "A", "es_subreceta": True, "rendimiento_cantidad": 100,
                                           "rendimiento_unidad_id": u["g"]}).json()["id"]
    b = client.post("/api/recetas", json={"nombre": "B", "es_subreceta": True, "rendimiento_cantidad": 100,
                                           "rendimiento_unidad_id": u["g"]}).json()["id"]
    assert client.post(f"/api/recetas/{a}/componentes", json={"subreceta_id": b, "cantidad": 10, "unidad_id": u["g"]}).status_code == 201
    r = client.post(f"/api/recetas/{b}/componentes", json={"subreceta_id": a, "cantidad": 10, "unidad_id": u["g"]})
    assert r.status_code == 422
    assert "ciclo" in r.json()["detail"]


def test_validaciones_basicas(client, u):
    assert client.post("/api/ingredientes", json={"nombre": "X", "unidad_base_id": u["g"], "merma_pct": 100}).status_code == 422
    assert client.post("/api/ingredientes", json={"nombre": "X", "unidad_base_id": u["kg"]}).status_code == 422
    crear_ing(client, u, "Y")
    assert client.post("/api/ingredientes", json={"nombre": "Y", "unidad_base_id": u["g"]}).status_code == 409
    assert client.post("/api/recetas", json={"nombre": "S", "es_subreceta": True}).status_code == 422
