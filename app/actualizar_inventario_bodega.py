# actualizar_inventario_bodega

import sqlite3
import pandas as pd
import os
import shutil

# --- CONFIGURACIÓN ---
DB_PATH = "jagi_mahalo.db"
EXCEL_PATH = "inventario_actualizado.xlsx"
TABLE_NAME = "inventario_bodega_raw"

# --- VALIDACIÓN DE ARCHIVO ---
if not os.path.exists(EXCEL_PATH):
    print(f"❌ No se encontró el archivo '{EXCEL_PATH}'.")
    exit()

# --- COPIA DE SEGURIDAD ---
backup_path = DB_PATH.replace(".db", "_backup.db")
shutil.copy(DB_PATH, backup_path)
print(f"🛟 Copia de seguridad creada: {backup_path}")

# --- LEER EXCEL ---
df = pd.read_excel(EXCEL_PATH)
df.columns = [c.strip().lower() for c in df.columns]

if "producto_id" not in df.columns or "cantidad_fisica" not in df.columns:
    print("⚠️ El archivo debe tener las columnas 'producto_id' y 'cantidad_fisica'.")
    exit()

# --- CONECTAR A LA BASE DE DATOS ---
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --- ACTUALIZAR REGISTROS ---
actualizados = 0
no_encontrados = []

for _, row in df.iterrows():
    c_barra = str(row["producto_id"]).strip()
    cantidad = float(row["cantidad_fisica"]) if pd.notna(row["cantidad_fisica"]) else 0

    # Obtener el costo unitario actual antes de actualizar
    cursor.execute(f"SELECT costo_uni FROM {TABLE_NAME} WHERE c_barra = ?", (c_barra,))
    row_costo = cursor.fetchone()
    
    if row_costo and row_costo[0] is not None:
        costo_unitario = float(row_costo[0])
        nuevo_pr_costo = cantidad * costo_unitario
        
        # Actualizar cantidad y recalcular pr_costo
        cursor.execute(f"""
            UPDATE {TABLE_NAME}
            SET saldo_disponibles = ?, saldo = ?, pr_costo = ?
            WHERE c_barra = ?;
        """, (cantidad, cantidad, nuevo_pr_costo, c_barra))
        
        actualizados += 1
    else:
        no_encontrados.append({"producto_id": c_barra, "cantidad_fisica": cantidad})

conn.commit()
conn.close()

# --- GUARDAR NO ENCONTRADOS ---
if no_encontrados:
    df_no_encontrados = pd.DataFrame(no_encontrados)
    df_no_encontrados.to_excel("codigos_no_encontrados.xlsx", index=False)
    print(f"⚠️ Se guardaron {len(no_encontrados)} códigos no encontrados en 'codigos_no_encontrados.xlsx'.")

# --- RESUMEN FINAL ---
print("\n📦 ACTUALIZACIÓN FINALIZADA")
print(f"✅ Registros actualizados correctamente: {actualizados}")
if no_encontrados:
    print(f"⚠️ Códigos no encontrados en la tabla: {len(no_encontrados)}")
print(f"\n💾 Base de datos actualizada: {DB_PATH}")