# test_api_analisis_marca.py

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)
MARCA_TEST = "JAGI CAPS LICENCIAS"


def test_endpoint_analisis_marca_status_ok():
    response = client.get(f"/analisis-marca/{MARCA_TEST}")

    assert response.status_code == 200


def test_endpoint_analisis_marca_success_true():
    response = client.get(f"/analisis-marca/{MARCA_TEST}")
    data = response.json()

    assert "success" in data
    assert data["success"] is True


def test_endpoint_analisis_marca_contrato_general():
    response = client.get(f"/analisis-marca/{MARCA_TEST}")
    payload = response.json()["datos"]

    for clave in ["marca", "resumen", "top10", "tiendas", "recomendaciones"]:
        assert clave in payload


def test_endpoint_analisis_marca_resumen_valido():
    response = client.get(f"/analisis-marca/{MARCA_TEST}")
    resumen = response.json()["datos"]["resumen"]

    assert resumen["tiendas_totales"] > 0
    assert resumen["total_productos"] >= 0
    assert resumen["tiendas_con_top10"] >= 0
    assert resumen["oportunidades_redistribucion"] >= 0


def test_endpoint_analisis_marca_top10_frontend_safe():
    response = client.get(f"/analisis-marca/{MARCA_TEST}")
    top10 = response.json()["datos"]["top10"]

    assert isinstance(top10, list)

    for producto in top10:
        assert "c_barra" in producto
        assert isinstance(producto["ventas_30d"], int)
        assert producto["ventas_30d"] >= 0
        assert isinstance(producto["tiendas_con_producto"], list)
        assert isinstance(producto["tiendas_sin_producto"], list)


def test_endpoint_analisis_marca_tiendas_frontend_safe():
    response = client.get(f"/analisis-marca/{MARCA_TEST}")
    tiendas = response.json()["datos"]["tiendas"]

    assert isinstance(tiendas, list)
    assert len(tiendas) > 0

    for tienda in tiendas:
        assert "tienda" in tienda
        assert isinstance(tienda["productos_top10"], int)
        assert isinstance(tienda["productos_faltantes"], int)