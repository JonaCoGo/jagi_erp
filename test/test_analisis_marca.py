# test_analisis_marca_2

import pytest
from app.consultas import get_analisis_marca

MARCA_TEST = "JAGI CAPS LICENCIAS"

@pytest.fixture(scope="module")
def analisis_marca():
    """
    Ejecuta una sola vez el análisis completo.
    Evita múltiples lecturas de BD.
    """
    return get_analisis_marca(MARCA_TEST)

def test_estructura_raiz(analisis_marca):
    assert isinstance(analisis_marca, dict)

    for clave in ("marca", "resumen", "top10", "tiendas", "recomendaciones"):
        assert clave in analisis_marca

def test_marca_correcta(analisis_marca):
    assert analisis_marca["marca"] == MARCA_TEST

def test_resumen_consistente(analisis_marca):
    resumen = analisis_marca["resumen"]

    assert resumen["total_productos"] == len(analisis_marca["top10"])
    assert resumen["tiendas_totales"] > 0
    assert resumen["tiendas_con_top10"] <= resumen["tiendas_totales"]
    assert resumen["oportunidades_redistribucion"] >= 0

def test_top10_estructura_y_coherencia(analisis_marca):
    top10 = analisis_marca["top10"]

    assert len(top10) <= 10

    for producto in top10:
        assert producto["ventas_30d"] >= 0
        assert producto["stock_total"] >= 0

        # coherencia lógica
        assert producto["potencial_faltante"] == len(producto["tiendas_sin_producto"])

def test_tiendas_consistentes_con_top10(analisis_marca):
    tiendas = analisis_marca["tiendas"]
    top10 = analisis_marca["top10"]

    for tienda in tiendas:
        total = tienda["productos_top10"] + tienda["productos_faltantes"]
        assert total == len(top10)
        assert tienda["ventas_top10"] >= 0