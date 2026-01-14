# movimiento_repository.py

import pandas as pd

def fetch_movimiento(conn, fecha_col, fecha_desde):
    query = f"""
    WITH ventas_periodo AS (
        SELECT 
            c_barra,
            d_almacen,
            SUM(cn_venta) AS ventas_periodo
        FROM ventas_historico_raw
        WHERE {fecha_col} >= {fecha_desde}
        GROUP BY c_barra, d_almacen
    )
    SELECT 
        t.clean_name AS tienda,
        s.c_barra,
        s.d_marca,
        s.saldo_disponible AS stock_actual,
        COALESCE(v.ventas_periodo, 0) AS ventas_periodo,
        CASE 
            WHEN COALESCE(v.ventas_periodo, 0) > 0 THEN 'EN MOVIMIENTO'
            ELSE 'SIN MOVIMIENTO'
        END AS estado,
        t.region,
        t.tipo_tienda,
        t.fija
    FROM ventas_saldos_raw s
    LEFT JOIN ventas_periodo v
        ON s.c_barra = v.c_barra AND s.d_almacen = v.d_almacen
    LEFT JOIN config_tiendas t
        ON s.d_almacen = t.raw_name
    ORDER BY t.clean_name, s.d_marca;
    """
    return pd.read_sql(query, conn)