# consultas.py

import sqlite3
import os
import pandas as pd
import unicodedata
from datetime import datetime, timedelta
from app.services.analisis_marca_service import get_analisis_marca
from app.services.producto_service import get_consulta_producto
from app.database import (
    get_connection,
    date_subtract_days,
    date_format_convert,
    current_date,
    DB_TYPE,
    DATA_DIR
)

DB_NAME = "jagi_mahalo.db"

def _norm(s):
    """Normaliza strings: None->'', quita acentos, strip, lower, colapsa espacios."""
    if pd.isna(s):
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.strip().lower()
    s = " ".join(s.split())
    return s

#------------------------------------------------------ REABASTECIMIENTO AVANZADO ------------------------------------------------------#

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
    Usa solo la tabla `config_tiendas` para regiones, nombres y configuración fija.
    """

    if nuevos_codigos is None:
        nuevos_codigos = []

    with get_connection() as conn:
        # Configuración de stock mínimo
        df_cfg = pd.read_sql("SELECT tipo, cantidad FROM stock_minimo_config", conn)
        cfg_map = {str(r["tipo"]).lower(): int(r["cantidad"]) for _, r in df_cfg.iterrows() if pd.notna(r["cantidad"])}

        referencias_fijas = pd.read_sql("SELECT cod_barras FROM referencias_fijas", conn)["cod_barras"].dropna().astype(str).tolist()
        marcas_multimarca = pd.read_sql("SELECT marca FROM marcas_multimarca", conn)["marca"].dropna().astype(str).tolist()
        codigos_excluidos = pd.read_sql("SELECT cod_barras FROM codigos_excluidos", conn)["cod_barras"].dropna().astype(str).tolist()

        # ✅ Configuracion de tiendas
        config_tiendas = pd.read_sql("SELECT raw_name, clean_name, region, fija, tipo_tienda FROM config_tiendas", conn)

        # --- Query base para reabastecimiento (ventas en dias_reab) ---
        
        fecha_desde_reab = date_subtract_days(dias_reab)
        fecha_col_convertida = date_format_convert('h.f_sistema')
        
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
            WHERE {fecha_col_convertida} >= {fecha_desde_reab}
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

        fecha_desde_exp = date_subtract_days(dias_exp)
        
        # --- Query para expansión (ventas en dias_exp) ---
        query_exp = f"""
        SELECT 
            h.c_barra,
            COALESCE(ct.clean_name, h.d_almacen) AS tienda,
            SUM(h.cn_venta) AS ventas_expansion
        FROM ventas_historico_raw h
        LEFT JOIN config_tiendas ct ON h.d_almacen = ct.raw_name
        WHERE {fecha_col_convertida} >= {fecha_desde_exp}
        GROUP BY h.c_barra, tienda
        """
        df_exp = pd.read_sql(query_exp, conn)

        # Todas las tiendas activas
        tiendas_all = config_tiendas["clean_name"].dropna().unique().tolist()

    # --- Normalización ---
    config_tiendas["clean_norm"] = config_tiendas["clean_name"].fillna("").apply(_norm)
    region_map = dict(zip(config_tiendas["clean_norm"], config_tiendas["region"]))
    tiendas_fijas_set = set(config_tiendas.loc[config_tiendas["fija"] == 1, "clean_name"].apply(_norm))

    df["tienda_norm"] = df["tienda"].fillna("").apply(_norm)
    df["region"] = df["tienda_norm"].map(region_map).fillna("SIN REGION")

    # --- Excluir Bodega JAGI ---
    df = df[~df["tienda"].str.contains("bodega jagi", case=False, na=False)]
    tiendas_all = [t for t in tiendas_all if "bodega jagi" not in t.lower()]

    # --- Config sets ---
    ref_set = set([r.strip().upper() for r in referencias_fijas if r])
    marca_set = set([m.strip().upper() for m in marcas_multimarca if m])
    excluidos_set = set([c.strip().upper() for c in codigos_excluidos if c])

    # --- Stock mínimo dinámico ---
    def calcular_stock_min(row):
        tienda_norm_local = _norm(row["tienda"])
        c_barra = (str(row["c_barra"]) or "").upper()
        d_marca = (str(row["d_marca"]) or "").upper()

        if c_barra in ref_set:
            return cfg_map.get("fijo_especial", 8) if tienda_norm_local in tiendas_fijas_set else cfg_map.get("fijo_normal", 5)
        elif d_marca in marca_set:
            return cfg_map.get("multimarca", 2)
        elif "JGL" in c_barra or "JGL" in d_marca:
            return cfg_map.get("jgl", 3)
        elif "JGM" in c_barra or "JGM" in d_marca:
            return cfg_map.get("jgm", 3)
        else:
            return cfg_map.get("default", 4)

    df["stock_minimo_dinamico"] = df.apply(calcular_stock_min, axis=1)

    # --- Cantidad a despachar ---
    df["cantidad_a_despachar"] = df.apply(
        lambda r: max(r["stock_minimo_dinamico"] - (r["stock_actual"] or 0), 0)
        if ((str(r["c_barra"]).upper() in ref_set) or (r["ventas_periodo"] > 0)) else 0,
        axis=1
    )

    # --- Observación ---
    def obs(r):
        if r["cantidad_a_despachar"] == 0:
            return "OK"
        if r["cantidad_a_despachar"] > (r["stock_bodega"] or 0):
            return "COMPRA"
        return "REABASTECER"

    df["observacion"] = df.apply(obs, axis=1)

    # --- Filtrar sin movimiento ---
    if excluir_sin_movimiento:
        if incluir_fijos:
            df = df[(df["ventas_periodo"] > 0) | (df["c_barra"].str.upper().isin(ref_set))]
        else:
            df = df[df["ventas_periodo"] > 0]

    # --- EXPANSIÓN ---
    with get_connection() as conn:
        info_ref = pd.read_sql("""
            SELECT DISTINCT 
                c_barra, d_marca, d_color_proveedor AS color
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
            WHERE s.c_barra IS NOT NULL
        """, conn)

    df_existencias["tienda_norm"] = df_existencias["tienda"].fillna("").apply(_norm)
    df_existencias["c_barra_up"] = df_existencias["c_barra"].astype(str).str.upper()
    existentes_fisicos = set(zip(df_existencias["tienda_norm"], df_existencias["c_barra_up"]))

    df_exp_validas = df_exp[df_exp["ventas_expansion"] >= ventas_min_exp].copy()
    df_exp_validas = df_exp_validas[~df_exp_validas["c_barra"].isin(codigos_excluidos)]
    df_exp_validas["c_barra_up"] = df_exp_validas["c_barra"].astype(str).str.upper()

    exp_rows = []
    exp_codes = df_exp_validas["c_barra_up"].unique().tolist()

    for code in exp_codes:
        tiendas_con_venta = df_exp_validas.loc[df_exp_validas["c_barra_up"] == code, "tienda"].dropna().unique().tolist()
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

    df_expansion = pd.DataFrame(exp_rows)
    if not df_expansion.empty:
        df = pd.concat([df, df_expansion], ignore_index=True)

    # --- NUEVOS CÓDIGOS ---
    if nuevos_codigos:
        nuevos_rows = []
        for c in nuevos_codigos:
            d_marca = c.get("d_marca", "SIN MARCA")
            color = c.get("color", "SIN COLOR")
            for tienda in tiendas_all:
                tienda_norm = _norm(tienda)
                nuevos_rows.append({
                    "region": region_map.get(tienda_norm, "SIN REGION"),
                    "tienda": tienda,
                    "c_barra": c.get("c_barra"),
                    "d_marca": d_marca,
                    "color": color,
                    "ventas_periodo": 0,
                    "stock_actual": 0,
                    "stock_bodega": 0,
                    "stock_minimo_dinamico": cfg_map.get("general", 4),
                    "cantidad_a_despachar": cfg_map.get("general", 4),
                    "observacion": "NUEVO"
                })
        df_nuevos = pd.DataFrame(nuevos_rows)
        df = pd.concat([df, df_nuevos], ignore_index=True)

    # --- Limpiar OK ---
    df = df[df["observacion"] != "OK"]
    df = df.sort_values(by=["region", "tienda", "d_marca", "c_barra"])

    cols_order = [
        "region", "tienda", "c_barra", "d_marca", "color", "ventas_periodo",
        "stock_actual", "stock_bodega", "stock_minimo_dinamico",
        "cantidad_a_despachar", "observacion"
    ]
    result = df[cols_order].copy()

    if guardar_debug_csv:
        sin_region = df[df["region"] == "SIN REGION"][["tienda"]].drop_duplicates()
        if not sin_region.empty:
            sin_region.to_csv("tiendas_sin_region.csv", index=False, encoding="utf-8-sig")

    # --- FILTRO OPCIONAL: solo códigos con ventas ---
    if solo_con_ventas:
        # Mantiene las expansiones y nuevos códigos, pero filtra los demás sin ventas
        result = result[
            (result["ventas_periodo"] > 0)
            | (result["observacion"].isin(["EXPANSION", "NUEVO"]))
        ]
        
    return result

#------------------------------------------------------ REDISTRIBUCION REGIONAL ------------------------------------------------------#

def get_redistribucion_regional(dias=30, ventas_min=1, tienda_origen=None):
    """
    Sugiere redistribución regional (opcional: desde una tienda origen específica).
    - Usa config_tiendas en lugar de map_tiendas, map_regiones y tiendas_fijas.
    - Analiza ventas recientes (últimos `dias`) y existencias actuales.
    - Respeta stock mínimo por tipo/marca y referencias fijas.
    - Devuelve un DataFrame con resultados y genera redistribucion_regional.xlsx
    """

    with get_connection() as conn:
        # Configuraciones de stock mínimo
        df_cfg = pd.read_sql("SELECT tipo, cantidad FROM stock_minimo_config", conn)
        cfg_map = {str(r["tipo"]).lower(): int(r["cantidad"]) for _, r in df_cfg.iterrows() if pd.notna(r["cantidad"])}

        # Tablas auxiliares
        referencias_fijas = pd.read_sql("SELECT cod_barras FROM referencias_fijas", conn)["cod_barras"].dropna().astype(str).tolist()
        marcas_multimarca = pd.read_sql("SELECT marca FROM marcas_multimarca", conn)["marca"].dropna().astype(str).tolist()
        codigos_excluidos = pd.read_sql("SELECT cod_barras FROM codigos_excluidos", conn)["cod_barras"].dropna().astype(str).tolist()

        # 🔹 Nueva tabla unificada
        config_tiendas = pd.read_sql("SELECT raw_name, clean_name, region, fija, tipo_tienda FROM config_tiendas", conn)

        #✅ Usar funciones helper para fechas
        fecha_desde = date_subtract_days(dias)
        fecha_col = date_format_convert('h.f_sistema')

        # Ventas recientes
        ventas = pd.read_sql_query(f"""
            SELECT
                COALESCE(ct.clean_name, h.d_almacen) AS tienda_clean,
                h.d_almacen AS tienda_raw,
                h.c_barra,
                h.d_marca,
                SUM(h.cn_venta) AS ventas_periodo
            FROM ventas_historico_raw h
            LEFT JOIN config_tiendas ct ON h.d_almacen = ct.raw_name
            WHERE {fecha_col} >= {fecha_desde}
            GROUP BY tienda_clean, h.c_barra, h.d_marca
        """, conn)

        # Existencias actuales
        existencias = pd.read_sql_query("""
            SELECT
                COALESCE(ct.clean_name, s.d_almacen) AS tienda_clean,
                s.d_almacen AS tienda_raw,
                s.c_barra,
                s.d_marca,
                s.saldo_disponible AS stock_actual
            FROM ventas_saldos_raw s
            LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
        """, conn)

    # --- Normalización y región ---
    config_tiendas["raw_norm"] = config_tiendas["raw_name"].fillna("").apply(_norm)
    config_tiendas["clean_norm"] = config_tiendas["clean_name"].fillna("").apply(_norm)
    region_map = dict(zip(config_tiendas["clean_norm"], config_tiendas["region"]))
    fija_set = set(config_tiendas.loc[config_tiendas["fija"] == 1, "clean_name"].apply(_norm))

    # Normalizar ventas y existencias
    for df_x in (ventas, existencias):
        df_x["tienda_clean"] = df_x["tienda_clean"].fillna("").astype(str)
        df_x["tienda_norm"] = df_x["tienda_clean"].apply(_norm)
        df_x["region"] = df_x["tienda_norm"].map(region_map).fillna("SIN REGION")
        if "ventas_periodo" in df_x.columns:
            df_x["ventas_periodo"] = pd.to_numeric(df_x["ventas_periodo"], errors="coerce").fillna(0)

    # --- Stock mínimo dinámico ---
    ref_set = set([r.strip().upper() for r in referencias_fijas if r])
    marca_set = set([m.strip().upper() for m in marcas_multimarca if m])

    def calcular_stock_min(c_barra, d_marca, tienda_clean_norm):
        c = (str(c_barra) or "").upper()
        m = (str(d_marca) or "").upper()

        if c in ref_set:
            return cfg_map.get("fijo_especial", cfg_map.get("fijo_normal", 5))
        if m in marca_set:
            return cfg_map.get("multimarca", 2)
        if "JGL" in c or "JGL" in m:
            return cfg_map.get("jgl", 3)
        if "JGM" in c or "JGM" in m:
            return cfg_map.get("jgm", 3)
        return cfg_map.get("general", 4)

    existencias["stock_minimo"] = existencias.apply(
        lambda r: calcular_stock_min(r["c_barra"], r["d_marca"], r["tienda_norm"]), axis=1
    )

    # --- Unir existencias y ventas ---
    ventas_agg = ventas.groupby(["tienda_norm", "c_barra", "d_marca"], as_index=False)["ventas_periodo"].sum()
    df = pd.merge(
        existencias,
        ventas_agg,
        on=["tienda_norm", "c_barra", "d_marca"],
        how="left"
    ).fillna({"ventas_periodo": 0})

    df["stock_actual"] = pd.to_numeric(df["stock_actual"], errors="coerce").fillna(0).astype(int)
    df["ventas_periodo"] = df["ventas_periodo"].astype(int)
    df["region"] = df["tienda_norm"].map(region_map).fillna("SIN REGION")

    # --- Detectar orígenes (sobrestock) y destinos (faltantes) ---
    origen = df[(df["stock_actual"] > df["stock_minimo"]) & (df["ventas_periodo"] == 0)].copy()
    origen = origen[~origen["tienda_norm"].isin(fija_set)]  # excluir tiendas fijas

    destino = df[(df["stock_actual"] < df["stock_minimo"]) & (df["ventas_periodo"] >= ventas_min)].copy()

    # --- Si se indica tienda origen específica ---
    if tienda_origen:
        tienda_origen_norm = _norm(tienda_origen)
        if tienda_origen_norm not in origen["tienda_norm"].values:
            print(f"⚠️ No hay sobrestock en '{tienda_origen}'.")
            return pd.DataFrame()

        region_obj = origen.loc[origen["tienda_norm"] == tienda_origen_norm, "region"].iloc[0]
        origen = origen[origen["tienda_norm"] == tienda_origen_norm]
        destino = destino[destino["region"] == region_obj]

    n_origen, n_destino = len(origen), len(destino)
    print(f"🔎 Orígenes candidatos: {n_origen}, Destinos candidatos: {n_destino}")

    if origen.empty or destino.empty:
        print("✅ No hay oportunidades de redistribución.")
        return pd.DataFrame()

    # --- Emparejar orígenes y destinos dentro de la región ---
    merged = origen.merge(
        destino,
        on=["region", "c_barra", "d_marca"],
        how="inner",
        suffixes=("_origen", "_destino")
    )

    if merged.empty:
        print("✅ No hay coincidencias origen-destino por referencia.")
        return pd.DataFrame()

    merged["exceso_origen"] = (merged["stock_actual_origen"] - merged["stock_minimo_origen"]).clip(lower=0)
    merged["faltante_destino"] = (merged["stock_minimo_destino"] - merged["stock_actual_destino"]).clip(lower=0)

    merged["cantidad_sugerida"] = merged.apply(
        lambda r: int(max(1, min(int(r["exceso_origen"] // 2), int(r["faltante_destino"])))) if (r["exceso_origen"] > 0 and r["faltante_destino"] > 0) else 0,
        axis=1
    )

    final = merged[merged["cantidad_sugerida"] > 0].copy()

    if final.empty:
        print("✅ No hay movimientos sugeridos.")
        return pd.DataFrame()

    final = final[[
        "region", "c_barra", "d_marca",
        "tienda_clean_origen", "stock_actual_origen", "ventas_periodo_origen",
        "tienda_clean_destino", "stock_actual_destino", "ventas_periodo_destino",
        "stock_minimo_destino", "cantidad_sugerida"
    ]].rename(columns={
        "tienda_clean_origen": "tienda_origen",
        "tienda_clean_destino": "tienda_destino",
        "stock_actual_origen": "stock_origen",
        "stock_actual_destino": "stock_destino",
        "ventas_periodo_origen": "ventas_origen",
        "ventas_periodo_destino": "ventas_destino"
    })

    final = final.sort_values(by=["region", "d_marca", "c_barra", "tienda_origen"])
    final.to_excel("redistribucion_regional.xlsx", index=False)

    print(f"📦 Redistribución generada: {len(final)} movimientos sugeridos.")
    print("📂 Archivo: redistribucion_regional.xlsx")

    return final

#------------------------------------------------------ OTRAS FUNCIONES ------------------------------------------------------

def get_existencias_por_tienda():
    query = """
    SELECT 
        t.clean_name AS tienda,
        s.c_barra,
        s.d_marca,
        s.saldo_disponible AS stock_actual,
        t.region,
        t.tipo_tienda,
        t.fija
    FROM ventas_saldos_raw s
    LEFT JOIN config_tiendas t ON s.d_almacen = t.raw_name
    ORDER BY t.clean_name, s.d_marca;
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn)

def get_movimiento(dias=30):

    # ✅ Usar funciones helper
    fecha_desde = date_subtract_days(dias)
    fecha_col = date_format_convert('f_sistema')

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
    with get_connection() as conn:
        return pd.read_sql(query, conn)

def get_resumen_movimiento(dias=30):
    df = get_movimiento(dias)
    resumen = (
        df.groupby(["tienda", "estado"])
        .agg(productos=("c_barra", "count"), stock_total=("stock_actual", "sum"))
        .reset_index()
    )
    return resumen

def get_faltantes(dias=90):
    with get_connection() as conn:
        fecha_limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        codigos_excluidos = pd.read_sql("SELECT cod_barras FROM codigos_excluidos", conn)["cod_barras"].astype(str).tolist()

        # Ventas recientes
        fecha_desde_exp = date_subtract_days(dias)
        fecha_col_convertida = date_format_convert('h.f_sistema')

        query_ventas = f"""
            SELECT 
                h.c_barra,
                h.d_marca,
                h.d_almacen,
                SUM(h.cn_venta) AS ventas_periodo
            FROM ventas_historico_raw h
            WHERE {fecha_col_convertida} >= {fecha_desde_exp}
            GROUP BY h.c_barra, h.d_marca, h.d_almacen
            HAVING SUM(h.cn_venta) > 0
        """
        ventas = pd.read_sql(query_ventas, conn)

        # Existencias
        existencias = pd.read_sql("""
            SELECT c_barra, d_almacen, saldo_disponible
            FROM ventas_saldos_raw
        """, conn)

        # Enlazar con config_tiendas (solo una vez)
        tiendas = pd.read_sql("SELECT raw_name, clean_name FROM config_tiendas", conn)

        ventas = ventas.merge(tiendas, left_on="d_almacen", right_on="raw_name", how="left")
        existencias = existencias.merge(tiendas, left_on="d_almacen", right_on="raw_name", how="left")

        ventas["tienda"] = ventas["clean_name"].fillna(ventas["d_almacen"])
        existencias["tienda"] = existencias["clean_name"].fillna(existencias["d_almacen"])

        # Limpiar bodegas y excluidos
        ventas = ventas[~ventas["tienda"].str.contains("BODEGA", case=False, na=False)]
        existencias = existencias[~existencias["tienda"].str.contains("BODEGA", case=False, na=False)]
        ventas = ventas[~ventas["c_barra"].isin(codigos_excluidos)]
        existencias = existencias[~existencias["c_barra"].isin(codigos_excluidos)]

        tiendas_activas = existencias["tienda"].drop_duplicates().tolist()
        productos = ventas[["c_barra", "d_marca"]].drop_duplicates()

        # Generar faltantes
        faltantes = []
        for _, prod in productos.iterrows():
            c_barra, d_marca = prod["c_barra"], prod["d_marca"]
            tiendas_con_stock = existencias.loc[existencias["c_barra"] == c_barra, "tienda"].unique().tolist()
            for t in tiendas_activas:
                if t not in tiendas_con_stock:
                    faltantes.append({
                        "c_barra": c_barra,
                        "d_marca": d_marca,
                        "tienda_faltante": t
                    })

        return pd.DataFrame(faltantes).sort_values(by=["d_marca", "tienda_faltante"])