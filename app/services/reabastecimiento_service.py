# reabastecimiento_service.py

import pandas as pd
from app.database import get_connection, date_subtract_days, date_format_convert
from app.utils.text import _norm


def get_reabastecimiento_avanzado(
    dias_reab=10,
    dias_exp=60,
    ventas_min_exp=3,
    excluir_sin_movimiento=True,
    incluir_fijos=True,
    guardar_debug_csv=True,
    nuevos_codigos=None,
    solo_con_ventas=False
):
    """
    Genera el reporte de reabastecimiento avanzado, expansión y nuevos códigos.
    Versión restaurada funcional (equivalente al backup original).
    """

    if nuevos_codigos is None:
        nuevos_codigos = []

    # =========================
    # CARGA BASE DE DATOS
    # =========================
    with get_connection() as conn:
        df_cfg = pd.read_sql("SELECT tipo, cantidad FROM stock_minimo_config", conn)
        cfg_map = {
            str(r["tipo"]).lower(): int(r["cantidad"])
            for _, r in df_cfg.iterrows()
            if pd.notna(r["cantidad"])
        }

        referencias_fijas = pd.read_sql(
            "SELECT cod_barras FROM referencias_fijas", conn
        )["cod_barras"].dropna().astype(str).tolist()

        marcas_multimarca = pd.read_sql(
            "SELECT marca FROM marcas_multimarca", conn
        )["marca"].dropna().astype(str).tolist()

        codigos_excluidos = pd.read_sql(
            "SELECT cod_barras FROM codigos_excluidos", conn
        )["cod_barras"].dropna().astype(str).tolist()

        config_tiendas = pd.read_sql(
            "SELECT raw_name, clean_name, region, fija, tipo_tienda FROM config_tiendas",
            conn
        )

        # -------------------------
        # REABASTECIMIENTO BASE
        # -------------------------
        fecha_desde_reab = date_subtract_days(dias_reab)
        fecha_col = date_format_convert("h.f_sistema")

        query = f"""
        WITH base AS (
            SELECT 
                s.c_barra,
                s.d_marca,
                COALESCE(ct.clean_name, s.d_almacen) AS tienda,
                s.d_color_proveedor AS color,
                s.saldo_disponible AS stock_actual,
                COALESCE(b.saldo_disponibles, 0) AS stock_bodega
            FROM ventas_saldos_raw s
            LEFT JOIN inventario_bodega_raw b ON s.c_barra = b.c_barra
            LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
            WHERE s.c_barra NOT IN (SELECT cod_barras FROM codigos_excluidos)
        ),
        ventas_reab AS (
            SELECT 
                h.c_barra,
                COALESCE(ct.clean_name, h.d_almacen) AS tienda,
                SUM(h.cn_venta) AS ventas_periodo
            FROM ventas_historico_raw h
            LEFT JOIN config_tiendas ct ON h.d_almacen = ct.raw_name
            WHERE {fecha_col} >= {fecha_desde_reab}
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
            ON base.c_barra = v.c_barra AND base.tienda = v.tienda;
        """
        df = pd.read_sql(query, conn)

        # -------------------------
        # EXPANSIÓN (VENTAS LARGAS)
        # -------------------------
        fecha_desde_exp = date_subtract_days(dias_exp)
        query_exp = f"""
        SELECT 
            h.c_barra,
            COALESCE(ct.clean_name, h.d_almacen) AS tienda,
            SUM(h.cn_venta) AS ventas_expansion
        FROM ventas_historico_raw h
        LEFT JOIN config_tiendas ct ON h.d_almacen = ct.raw_name
        WHERE {fecha_col} >= {fecha_desde_exp}
        GROUP BY h.c_barra, tienda
        """
        df_exp = pd.read_sql(query_exp, conn)

        tiendas_all = config_tiendas["clean_name"].dropna().unique().tolist()

    # =========================
    # NORMALIZACIÓN
    # =========================
    config_tiendas["clean_norm"] = config_tiendas["clean_name"].fillna("").apply(_norm)
    region_map = dict(zip(config_tiendas["clean_norm"], config_tiendas["region"]))
    tiendas_fijas_set = set(
        config_tiendas.loc[config_tiendas["fija"] == 1, "clean_name"].apply(_norm)
    )

    df["tienda_norm"] = df["tienda"].fillna("").apply(_norm)
    df["region"] = df["tienda_norm"].map(region_map).fillna("SIN REGION")

    df = df[~df["tienda"].str.contains("bodega jagi", case=False, na=False)]
    tiendas_all = [t for t in tiendas_all if "bodega jagi" not in t.lower()]

    ref_set = set(r.strip().upper() for r in referencias_fijas if r)
    marca_set = set(m.strip().upper() for m in marcas_multimarca if m)

    # =========================
    # STOCK MÍNIMO DINÁMICO
    # =========================
    def calcular_stock_min(row):
        tienda_norm = _norm(row["tienda"])
        code = str(row["c_barra"]).upper()
        marca = str(row["d_marca"]).upper()

        if code in ref_set:
            return cfg_map.get("fijo_especial", 8) if tienda_norm in tiendas_fijas_set else cfg_map.get("fijo_normal", 5)
        if marca in marca_set:
            return cfg_map.get("multimarca", 2)
        if "JGL" in code or "JGL" in marca:
            return cfg_map.get("jgl", 3)
        if "JGM" in code or "JGM" in marca:
            return cfg_map.get("jgm", 3)
        return cfg_map.get("default", 4)

    df["stock_minimo_dinamico"] = df.apply(calcular_stock_min, axis=1)

    df["cantidad_a_despachar"] = df.apply(
        lambda r: max(r["stock_minimo_dinamico"] - (r["stock_actual"] or 0), 0)
        if (r["ventas_periodo"] > 0 or str(r["c_barra"]).upper() in ref_set)
        else 0,
        axis=1
    )

    df["observacion"] = df.apply(
        lambda r: "OK"
        if r["cantidad_a_despachar"] == 0
        else "COMPRA"
        if r["cantidad_a_despachar"] > (r["stock_bodega"] or 0)
        else "REABASTECER",
        axis=1
    )

    if excluir_sin_movimiento:
        if incluir_fijos:
            df = df[(df["ventas_periodo"] > 0) | (df["c_barra"].str.upper().isin(ref_set))]
        else:
            df = df[df["ventas_periodo"] > 0]

    # =========================
    # EXPANSIÓN (LÓGICA COMPLETA)
    # =========================
    with get_connection() as conn:
        info_ref = pd.read_sql("""
            SELECT DISTINCT c_barra, d_marca, d_color_proveedor AS color
            FROM ventas_saldos_raw
            WHERE c_barra IS NOT NULL
        """, conn)

        df_existencias = pd.read_sql("""
            SELECT DISTINCT 
                COALESCE(ct.clean_name, s.d_almacen) AS tienda,
                s.c_barra,
                s.saldo_disponible
            FROM ventas_saldos_raw s
            LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
        """, conn)

    df_existencias["tienda_norm"] = df_existencias["tienda"].apply(_norm)
    df_existencias["c_barra_up"] = df_existencias["c_barra"].astype(str).str.upper()
    existentes_fisicos = set(zip(df_existencias["tienda_norm"], df_existencias["c_barra_up"]))

    df_exp_validas = df_exp[df_exp["ventas_expansion"] >= ventas_min_exp].copy()
    df_exp_validas = df_exp_validas[~df_exp_validas["c_barra"].isin(codigos_excluidos)]
    df_exp_validas["c_barra_up"] = df_exp_validas["c_barra"].astype(str).str.upper()

    exp_rows = []

    for code in df_exp_validas["c_barra_up"].unique():
        tiendas_con_venta = df_exp_validas.loc[
            df_exp_validas["c_barra_up"] == code, "tienda"
        ].dropna().unique().tolist()
        tiendas_con_venta_norm = [_norm(t) for t in tiendas_con_venta]

        info = info_ref[info_ref["c_barra"].astype(str).str.upper() == code]
        d_marca_val = info["d_marca"].iloc[0] if not info.empty else "SIN MARCA"
        color_val = info["color"].iloc[0] if not info.empty else "SIN COLOR"

        for tienda in tiendas_all:
            tienda_norm = _norm(tienda)
            if tienda_norm in tiendas_con_venta_norm:
                continue
            if (tienda_norm, code) in existentes_fisicos:
                continue

            if code in ref_set:
                tipo = "fijo_especial" if tienda_norm in tiendas_fijas_set else "fijo_normal"
            elif d_marca_val.upper() in marca_set:
                tipo = "multimarca"
            elif "JGL" in code or "JGL" in d_marca_val.upper():
                tipo = "jgl"
            elif "JGM" in code or "JGM" in d_marca_val.upper():
                tipo = "jgm"
            else:
                tipo = "default"

            stock_min = cfg_map.get(tipo, 4)

            exp_rows.append({
                "region": region_map.get(tienda_norm, "SIN REGION"),
                "tienda": tienda,
                "c_barra": code,
                "d_marca": d_marca_val,
                "color": color_val,
                "ventas_periodo": 0,
                "stock_actual": 0,
                "stock_bodega": 0,
                "stock_minimo_dinamico": stock_min,
                "cantidad_a_despachar": stock_min,
                "observacion": "EXPANSION"
            })

    if exp_rows:
        df = pd.concat([df, pd.DataFrame(exp_rows)], ignore_index=True)

    # =========================
    # NUEVOS CÓDIGOS
    # =========================
    if nuevos_codigos:
        nuevos_rows = []
        for c in nuevos_codigos:
            for tienda in tiendas_all:
                tienda_norm = _norm(tienda)
                nuevos_rows.append({
                    "region": region_map.get(tienda_norm, "SIN REGION"),
                    "tienda": tienda,
                    "c_barra": c.get("c_barra"),
                    "d_marca": c.get("d_marca", "SIN MARCA"),
                    "color": c.get("color", "SIN COLOR"),
                    "ventas_periodo": 0,
                    "stock_actual": 0,
                    "stock_bodega": 0,
                    "stock_minimo_dinamico": cfg_map.get("general", 4),
                    "cantidad_a_despachar": cfg_map.get("general", 4),
                    "observacion": "NUEVO"
                })
        df = pd.concat([df, pd.DataFrame(nuevos_rows)], ignore_index=True)

    # =========================
    # SALIDA FINAL
    # =========================
    df = df[df["observacion"] != "OK"]
    df = df.sort_values(by=["region", "tienda", "d_marca", "c_barra"])

    columnas = [
        "region", "tienda", "c_barra", "d_marca", "color",
        "ventas_periodo", "stock_actual", "stock_bodega",
        "stock_minimo_dinamico", "cantidad_a_despachar", "observacion"
    ]

    result = df[columnas].copy()

    if guardar_debug_csv:
        sin_region = result[result["region"] == "SIN REGION"][["tienda"]].drop_duplicates()
        if not sin_region.empty:
            sin_region.to_csv("tiendas_sin_region.csv", index=False, encoding="utf-8-sig")

    if solo_con_ventas:
        result = result[
            (result["ventas_periodo"] > 0)
            | (result["observacion"].isin(["EXPANSION", "NUEVO"]))
        ]

    return result