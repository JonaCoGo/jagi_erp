# altantes_service.py

import pandas as pd
from app.database import get_connection, date_subtract_days, date_format_convert
from app.repositories import faltantes_repository as repo


def get_faltantes(dias=90):
    fecha_desde = date_subtract_days(dias)
    fecha_col = date_format_convert("h.f_sistema")

    with get_connection() as conn:
        cod_excluidos = (
            repo.fetch_codigos_excluidos(conn)["cod_barras"]
            .astype(str)
            .tolist()
        )

        ventas = repo.fetch_ventas_periodo(conn, fecha_col, fecha_desde)
        existencias = repo.fetch_existencias(conn)
        tiendas = repo.fetch_tiendas(conn)

    # Normalizar tiendas
    ventas = ventas.merge(tiendas, left_on="d_almacen", right_on="raw_name", how="left")
    existencias = existencias.merge(tiendas, left_on="d_almacen", right_on="raw_name", how="left")

    ventas["tienda"] = ventas["clean_name"].fillna(ventas["d_almacen"])
    existencias["tienda"] = existencias["clean_name"].fillna(existencias["d_almacen"])

    # Limpiar bodegas y excluidos
    ventas = ventas[~ventas["tienda"].str.contains("BODEGA", case=False, na=False)]
    existencias = existencias[~existencias["tienda"].str.contains("BODEGA", case=False, na=False)]

    ventas = ventas[~ventas["c_barra"].isin(cod_excluidos)]
    existencias = existencias[~existencias["c_barra"].isin(cod_excluidos)]

    tiendas_activas = existencias["tienda"].drop_duplicates().tolist()
    productos = ventas[["c_barra", "d_marca"]].drop_duplicates()

    # Lógica de negocio: detectar faltantes
    faltantes = []

    for _, prod in productos.iterrows():
        c_barra = prod["c_barra"]
        d_marca = prod["d_marca"]

        tiendas_con_stock = (
            existencias.loc[existencias["c_barra"] == c_barra, "tienda"]
            .unique()
            .tolist()
        )

        for tienda in tiendas_activas:
            if tienda not in tiendas_con_stock:
                faltantes.append({
                    "c_barra": c_barra,
                    "d_marca": d_marca,
                    "tienda_faltante": tienda
                })

    return pd.DataFrame(faltantes).sort_values(
        by=["d_marca", "tienda_faltante"]
    )