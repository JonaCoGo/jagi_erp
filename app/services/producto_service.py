# producto_service.py

import pandas as pd
from app.database import get_connection
from app.repositories import producto_repository as repo


def get_consulta_producto(codigo_barras):

    with get_connection() as conn:
        df_info = repo.fetch_info_producto(conn, codigo_barras)

        if df_info.empty:
            df_info = repo.fetch_info_producto_bodega(conn, codigo_barras)
            if df_info.empty:
                return {
                    "encontrado": False,
                    "mensaje": f"No se encontró el código {codigo_barras}"
                }

        info = df_info.iloc[0].to_dict()

        df_tiendas = repo.fetch_existencias_tiendas(conn, codigo_barras)
        df_bodega = repo.fetch_existencias_bodega(conn, codigo_barras)

        df_existencias = pd.concat([df_tiendas, df_bodega], ignore_index=True)

        stock_total = int(df_existencias["stock_actual"].sum())
        stock_bodega = int(df_bodega["stock_actual"].sum()) if not df_bodega.empty else 0
        stock_tiendas = stock_total - stock_bodega

        ventas_30 = int(repo.fetch_ventas_periodo(conn, codigo_barras, 30)["ventas"].iloc[0] or 0)
        ventas_60 = int(repo.fetch_ventas_periodo(conn, codigo_barras, 60)["ventas"].iloc[0] or 0)
        ventas_90 = int(repo.fetch_ventas_periodo(conn, codigo_barras, 90)["ventas"].iloc[0] or 0)

        velocidad_dia = round(ventas_30 / 30, 2) if ventas_30 > 0 else 0
        dias_agotar = int(stock_tiendas / velocidad_dia) if velocidad_dia > 0 else 999

        ultima_venta = repo.fetch_ultima_venta(conn, codigo_barras)["ultima_venta"].iloc[0]

        df_ventas_tienda = repo.fetch_ventas_por_tienda(conn, codigo_barras)
        df_dist = df_tiendas.merge(df_ventas_tienda, on="tienda", how="left").fillna(0)

        todas_tiendas = repo.fetch_todas_tiendas(conn)["tienda"].tolist()
        tiendas_con_producto = df_tiendas["tienda"].tolist()
        tiendas_sin_producto = [t for t in todas_tiendas if t not in tiendas_con_producto]

        df_historial = repo.fetch_historial(conn, codigo_barras)
        df_grafico = repo.fetch_grafico_ventas(conn, codigo_barras)

        if velocidad_dia == 0:
            texto, estado = "❌ Sin movimiento - Considerar redistribución", "sin_movimiento"
        elif dias_agotar < 15:
            texto, estado = f"🔴 URGENTE - Reabastecer ({dias_agotar} días)", "critico"
        elif dias_agotar < 30:
            texto, estado = f"🟡 Programar reabastecimiento ({dias_agotar} días)", "alerta"
        else:
            texto, estado = f"✅ Stock óptimo ({dias_agotar} días)", "optimo"

        return {
            "encontrado": True,
            "info_general": {
                "codigo": info["c_barra"],
                "marca": info["d_marca"],
                "color": info["color"],
                "stock_total": stock_total,
                "stock_bodega": stock_bodega,
                "stock_tiendas": stock_tiendas,
                "valor_inventario": None
            },
            "ventas": {
                "ultimos_30_dias": ventas_30,
                "ultimos_60_dias": ventas_60,
                "ultimos_90_dias": ventas_90,
                "velocidad_dia": velocidad_dia,
                "dias_para_agotar": dias_agotar,
                "ultima_fecha_venta": ultima_venta
            },
            "distribucion": df_dist.to_dict(orient="records"),
            "tiendas_sin_producto": tiendas_sin_producto,
            "historial": df_historial.to_dict(orient="records"),
            "grafico_ventas": {
                "fechas": df_grafico["fecha"].tolist(),
                "valores": df_grafico["ventas"].astype(int).tolist()
            },
            "recomendacion": {
                "texto": texto,
                "estado": estado
            }
        }