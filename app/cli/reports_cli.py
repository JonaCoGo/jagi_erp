# reports_cli.py

from app.consultas import (
    get_reabastecimiento_avanzado,
    get_existencias_por_tienda,
    get_movimiento,
    get_resumen_movimiento,
    get_faltantes,
    get_redistribucion_regional,
)

from app.reports.excel_exporter import exportar_excel_formateado

def menu():
# ======================================================
# 🚀 MENÚ PRINCIPAL
# ======================================================
    print("\n📊 ¿Qué informe quieres generar?")
    print("1. Reabastecimiento por tienda")
    print("2. Existencias por tienda")
    print("3. Movimiento por tienda")
    print("4. Resumen por tienda")
    print("5. Faltantes por tienda")
    print("6. Redistribución entre tiendas")

    return input("Seleccione [1-6]: ").strip()

def limpiar_dataframe(df):
    columnas_a_eliminar = ["region"]
    return df.drop(columns=[c for c in columnas_a_eliminar if c in df.columns])

def run():
    opcion = menu()

    if opcion == "1":
        dias_reab = int(input("Ingrese los días para considerar reabastecimiento: "))
        dias_exp = int(input("Ingrese los días para considerar expansión: "))
        ventas_min_exp = int(input("Ingrese las ventas mínimas para considerar expansión: "))

        incluir_nuevos = input("\n¿Desea ingresar nuevos códigos de barras? (s/n): ").lower() == "s"
        nuevos_codigos = None
        if incluir_nuevos:
            codigos = input("Ingrese los códigos separados por coma: ")
            nuevos_codigos = [c.strip() for c in codigos.split(",") if c.strip()]

        solo_ventas = input("¿Mostrar solo códigos con ventas? (s/n): ").lower() == "s"

        df = get_reabastecimiento_avanzado(
            dias_reab=dias_reab,
            dias_exp=dias_exp,
            ventas_min_exp=ventas_min_exp,
            excluir_sin_movimiento=True,
            incluir_fijos=True,
            guardar_debug_csv=True,
            nuevos_codigos=nuevos_codigos,
            solo_con_ventas=solo_ventas,
        )

        df = limpiar_dataframe(df)

        print(f"\n🔍 Total filas en reporte: {len(df)}")
        exportar_excel_formateado(df, "reabastecimiento_jagi.xlsx", "Reabastecimiento")

    elif opcion == "2":
        df = get_existencias_por_tienda()
        df = limpiar_dataframe(df)
        exportar_excel_formateado(df, "existencias_jagi.xlsx", "Existencias")

    elif opcion == "3":
        df = get_movimiento()
        df = limpiar_dataframe(df)
        exportar_excel_formateado(df, "movimiento_jagi.xlsx", "Movimiento")

    elif opcion == "4":
        df = get_resumen_movimiento()
        df = limpiar_dataframe(df)
        exportar_excel_formateado(df, "resumen_jagi.xlsx", "Resumen Movimiento")

    elif opcion == "5":
        df = get_faltantes()
        df = limpiar_dataframe(df)
        exportar_excel_formateado(df, "faltantes_jagi.xlsx", "Faltantes")

    elif opcion == "6":
        dias = int(input("Ingrese los días para analizar redistribución: "))
        ventas_min = int(input("Ventas mínimas para considerar demanda: "))
        tienda_filtro = input("¿Desea analizar una tienda específica? (dejar vacío para todas): ").strip() or None
        df_redis = get_redistribucion_regional(dias, ventas_min, tienda_filtro)
        print(f"🔎 Orígenes candidatos: {df_redis['tienda_origen'].nunique()}, "
              f"Destinos candidatos: {df_redis['tienda_destino'].nunique()}")
        print(f"📦 Redistribución generada: {len(df_redis)} movimientos sugeridos.")
        exportar_excel_formateado(df_redis, "redistribucion_regional.xlsx", f"Redistribución {dias} días")

    else:
        print("❌ Opción no válida. Intente de nuevo.")

if __name__ == "__main__":
    run()
    