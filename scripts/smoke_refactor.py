# test_refactorizacion.py

from app.database import test_connection, get_db_info, get_connection
import pandas as pd

print("🧪 Probando refactorización...")

# Test 1: Conexión
if test_connection():
    print("✅ Test 1: Conexión exitosa")
else:
    print("❌ Test 1: Error de conexión")

# Test 2: Query simple
try:
    with get_connection() as conn:
        df = pd.read_sql("SELECT COUNT(*) as total FROM ventas_saldos_raw", conn)
    print(f"✅ Test 2: Query exitosa - {df['total'].iloc[0]} registros")
except Exception as e:
    print(f"❌ Test 2: Error - {e}")

# Test 3: Info de BD
info = get_db_info()
print(f"✅ Test 3: Tipo BD: {info['type']}")

print("\n🎉 Si ves 3 ✅, está todo bien")