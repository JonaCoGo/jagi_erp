# reabastecimiento_repository.py

import pandas as pd


# ======================================================
# CONFIGURACIONES BÁSICAS
# ======================================================

def fetch_stock_minimo_config(conn):
    return pd.read_sql(
        "SELECT tipo, cantidad FROM stock_minimo_config",
        conn
    )


def fetch_referencias_fijas(conn):
    return pd.read_sql(
        "SELECT cod_barras FROM referencias_fijas",
        conn
    )


def fetch_marcas_multimarca(conn):
    return pd.read_sql(
        "SELECT marca FROM marcas_multimarca",
        conn
    )


def fetch_codigos_excluidos(conn):
    return pd.read_sql(
        "SELECT cod_barras FROM codigos_excluidos",
        conn
    )


def fetch_config_tiendas(conn):
    return pd.read_sql(
        """
        SELECT raw_name, clean_name, region, fija, tipo_tienda
        FROM config_tiendas
        """,
        conn
    )


# ======================================================
# REABASTECIMIENTO BASE
# ======================================================

def fetch_base_reabastecimiento(conn, fecha_col, fecha_desde):
    """
    Base de reabastecimiento:
    - Stock por tienda
    - Stock en bodega
    - Ventas en el período
    """
    query = f"""
    WITH base AS (
        SELECT 
            s.c_barra,
            s.d_marca,
            COALESCE(ct.clean_name, s.d_almacen) AS tienda,
            s.d_color_proveedor AS color,
            s.saldo_disponible AS stock_actual,
            COALESCE(
                b.saldo_disponibles,
                b.saldo_disponible,
                0
            ) AS stock_bodega
        FROM ventas_saldos_raw s
        LEFT JOIN inventario_bodega_raw b
            ON s.c_barra = b.c_barra
        LEFT JOIN config_tiendas ct
            ON s.d_almacen = ct.raw_name
        WHERE s.c_barra NOT IN (
            SELECT cod_barras
            FROM codigos_excluidos
            WHERE cod_barras IS NOT NULL
        )
    ),
    ventas_reab AS (
        SELECT 
            h.c_barra,
            COALESCE(ct.clean_name, h.d_almacen) AS tienda,
            SUM(h.cn_venta) AS ventas_periodo
        FROM ventas_historico_raw h
        LEFT JOIN config_tiendas ct
            ON h.d_almacen = ct.raw_name
        WHERE {fecha_col} >= {fecha_desde}
        GROUP BY h.c_barra, tienda
    )
    SELECT 
        base.c_barra,
        base.d_marca,
        base.tienda,
        base.color,
        base.stock_actual,
        base.stock_bodega,
        COALESCE(v.ventas_periodo, 0) AS ventas_periodo
    FROM base
    LEFT JOIN ventas_reab v
        ON base.c_barra = v.c_barra
       AND base.tienda = v.tienda;
    """
    return pd.read_sql(query, conn)


# ======================================================
# EXPANSIÓN
# ======================================================

def fetch_ventas_expansion(conn, fecha_col, fecha_desde):
    query = f"""
    SELECT 
        h.c_barra,
        COALESCE(ct.clean_name, h.d_almacen) AS tienda,
        SUM(h.cn_venta) AS ventas_expansion
    FROM ventas_historico_raw h
    LEFT JOIN config_tiendas ct
        ON h.d_almacen = ct.raw_name
    WHERE {fecha_col} >= {fecha_desde}
    GROUP BY h.c_barra, tienda
    """
    return pd.read_sql(query, conn)


# ======================================================
# DATOS AUXILIARES
# ======================================================

def fetch_info_referencias(conn):
    return pd.read_sql(
        """
        SELECT DISTINCT 
            c_barra,
            d_marca,
            d_color_proveedor AS color
        FROM ventas_saldos_raw
        WHERE c_barra IS NOT NULL
        """,
        conn
    )


def fetch_existencias(conn):
    return pd.read_sql(
        """
        SELECT DISTINCT 
            COALESCE(ct.clean_name, s.d_almacen) AS tienda,
            s.c_barra,
            s.saldo_disponible
        FROM ventas_saldos_raw s
        LEFT JOIN config_tiendas ct
            ON s.d_almacen = ct.raw_name
        WHERE s.c_barra IS NOT NULL
        """,
        conn
    )