import sqlite3

DB_PATH = "jagi_mahalo.db"

def mostrar_esquema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n📌 TABLAS EN LA BASE DE DATOS:\n")

    # Obtener listas de tablas
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tablas = [t[0] for t in cur.fetchall()]

    for tabla in tablas:
        print(f"\n🔹 Tabla: {tabla}")
        print("   Columnas:")

        # Obtener columnas de cada tabla
        cur.execute(f"PRAGMA table_info({tabla});")
        columnas = cur.fetchall()

        for col in columnas:
            cid, nombre, tipo, notnull, default, pk = col
            print(f"     - {nombre} ({tipo})")

    conn.close()
    print("\n✅ Esquema completado.\n")

if __name__ == "__main__":
    mostrar_esquema()