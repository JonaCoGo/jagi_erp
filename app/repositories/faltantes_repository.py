# faltantes_repository.py

import pandas as pd

def fetch_codigos_excluidos(conn):
    query = "SELECT cod_barras FROM codigos_excluidos"
    return pd.read_sql(query, conn)


def fetch_ventas_periodo(conn, fecha_col, fecha_desde):
    query = f"""
        SELECT 
            h.c_barra,
            h.d_marca,
            h.d_almacen,
            SUM(h.cn_venta) AS ventas_periodo
        FROM ventas_historico_raw h
        WHERE {fecha_col} >= {fecha_desde}
        GROUP BY h.c_barra, h.d_marca, h.d_almacen
        HAVING SUM(h.cn_venta) > 0
    """
    return pd.read_sql(query, conn)


def fetch_existencias(conn):
    query = """
        SELECT c_barra, d_almacen, saldo_disponible
        FROM ventas_saldos_raw
    """
    return pd.read_sql(query, conn)


def fetch_tiendas(conn):
    query = "SELECT raw_name, clean_name FROM config_tiendas"
    return pd.read_sql(query, conn)