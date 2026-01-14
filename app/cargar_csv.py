# cargar_csv

import sqlite3
import pandas as pd
import os
from app.database import DATA_DIR, DB_PATH

def resetear_y_cargar():

    # 1. Definimos las rutas de los archivos dentro de la nueva carpeta /data/inputs
    inputs_dir = os.path.join(DATA_DIR, "inputs")

    archivos = {
        "ventas_saldos": os.path.join(inputs_dir, "1.Ventas-Saldos.csv"),
        "inventario_bodega": os.path.join(inputs_dir, "2.Inventario-Bodega.csv"),
        "ventas_historico": os.path.join(inputs_dir, "3.Ventas-Historico.csv")
    }

    # Conectamos a la BD en la nueva ruta (data/jagi_mahalo.db)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Paso 1: eliminar tablas _raw
    tablas_raw = ["ventas_saldos_raw", "inventario_bodega_raw", "ventas_historico_raw"]
    for tabla in tablas_raw:
        print(f"🗑️ Eliminando tabla {tabla} si existe...")
        cur.execute(f"DROP TABLE IF EXISTS {tabla}")
    conn.commit()

    # Paso 2: volver a crearlas con datos frescos
    for tabla, archivo_path in archivos.items():
        if not os.path.exists(archivo_path):
            print(f"❌ Error: No se encontró el archivo en {archivo_path}")
            continue

        print(f"📥 Cargando {os.path.basename(archivo_path)} en la tabla {tabla}_raw ...")
        
        df = pd.read_csv(archivo_path, encoding="latin1", sep=";")

        # 🔧 Eliminar columnas "Unnamed"
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

        # 🔧 Normalizar nombres de columnas
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(r"[^a-z0-9_]", "", regex=True)
        )

        # Guardar en SQLite
        df.to_sql(f"{tabla}_raw", conn, if_exists="replace", index=False)
        print(f"✅ {len(df)} filas insertadas en {tabla}_raw")

    conn.close()
    print(f"\n🎉 Tablas _raw recreadas y cargadas con éxito en {DB_PATH}")

if __name__ == "__main__":
    resetear_y_cargar()
