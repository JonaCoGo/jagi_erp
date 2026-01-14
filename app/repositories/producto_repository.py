# producto_repository.py

import pandas as pd

def fetch_info_producto(conn, codigo):
    query = """
    SELECT DISTINCT
        c_barra,
        d_marca,
        d_color_proveedor AS color
    FROM ventas_saldos_raw
    WHERE c_barra = ?
    LIMIT 1
    """
    return pd.read_sql(query, conn, params=(codigo,))


def fetch_info_producto_bodega(conn, codigo):
    query = """
    SELECT DISTINCT
        c_barra,
        'DESCONOCIDO' as d_marca,
        'DESCONOCIDO' as color
    FROM inventario_bodega_raw
    WHERE c_barra = ?
    LIMIT 1
    """
    return pd.read_sql(query, conn, params=(codigo,))


def fetch_existencias_tiendas(conn, codigo):
    query = """
    SELECT 
        COALESCE(ct.clean_name, s.d_almacen) AS tienda,
        ct.region,
        s.saldo_disponible AS stock_actual
    FROM ventas_saldos_raw s
    LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
    WHERE s.c_barra = ?
    """
    return pd.read_sql(query, conn, params=(codigo,))


def fetch_existencias_bodega(conn, codigo):
    query = """
    SELECT 
        'BODEGA JAGI' AS tienda,
        'BODEGA' AS region,
        saldo_disponibles AS stock_actual
    FROM inventario_bodega_raw
    WHERE c_barra = ?
    """
    return pd.read_sql(query, conn, params=(codigo,))


def fetch_ventas_periodo(conn, codigo, dias):
    query = f"""
    SELECT SUM(cn_venta) as ventas
    FROM ventas_historico_raw
    WHERE c_barra = ?
    AND DATE(substr(f_sistema,7,4)||'-'||substr(f_sistema,4,2)||'-'||substr(f_sistema,1,2))
        >= DATE('now', '-{dias} days')
    """
    return pd.read_sql(query, conn, params=(codigo,))


def fetch_ultima_venta(conn, codigo):
    query = """
    SELECT MAX(DATE(substr(f_sistema,7,4)||'-'||substr(f_sistema,4,2)||'-'||substr(f_sistema,1,2))) as ultima_venta
    FROM ventas_historico_raw
    WHERE c_barra = ?
    """
    return pd.read_sql(query, conn, params=(codigo,))


def fetch_ventas_por_tienda(conn, codigo):
    query = """
    SELECT 
        COALESCE(ct.clean_name, h.d_almacen) AS tienda,
        SUM(h.cn_venta) as ventas_30d
    FROM ventas_historico_raw h
    LEFT JOIN config_tiendas ct ON h.d_almacen = ct.raw_name
    WHERE h.c_barra = ?
    AND DATE(substr(f_sistema,7,4)||'-'||substr(f_sistema,4,2)||'-'||substr(f_sistema,1,2))
        >= DATE('now', '-30 days')
    AND h.d_almacen NOT LIKE '%BODEGA%'
    GROUP BY tienda
    """
    return pd.read_sql(query, conn, params=(codigo,))


def fetch_todas_tiendas(conn):
    query = """
    SELECT DISTINCT clean_name as tienda
    FROM config_tiendas
    WHERE clean_name NOT LIKE '%BODEGA%'
    """
    return pd.read_sql(query, conn)


def fetch_historial(conn, codigo):
    query = """
    SELECT 
        DATE(substr(f_sistema,7,4)||'-'||substr(f_sistema,4,2)||'-'||substr(f_sistema,1,2)) as fecha,
        COALESCE(ct.clean_name, d_almacen) AS tienda,
        cn_venta as cantidad
    FROM ventas_historico_raw h
    LEFT JOIN config_tiendas ct ON h.d_almacen = ct.raw_name
    WHERE c_barra = ?
    AND DATE(substr(f_sistema,7,4)||'-'||substr(f_sistema,4,2)||'-'||substr(f_sistema,1,2))
        >= DATE('now', '-30 days')
    ORDER BY fecha DESC
    LIMIT 50
    """
    return pd.read_sql(query, conn, params=(codigo,))


def fetch_grafico_ventas(conn, codigo):
    query = """
    SELECT 
        DATE(substr(f_sistema,7,4)||'-'||substr(f_sistema,4,2)||'-'||substr(f_sistema,1,2)) as fecha,
        SUM(cn_venta) as ventas
    FROM ventas_historico_raw
    WHERE c_barra = ?
    AND DATE(substr(f_sistema,7,4)||'-'||substr(f_sistema,4,2)||'-'||substr(f_sistema,1,2))
        >= DATE('now', '-30 days')
    GROUP BY fecha
    ORDER BY fecha
    """
    return pd.read_sql(query, conn, params=(codigo,))