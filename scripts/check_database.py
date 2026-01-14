# test_database.py

"""
Script para probar la capa de abstracción de base de datos.
"""

import pandas as pd
from app.database import (
    test_connection,
    get_connection,
    get_db_info,
    date_subtract_days,
    date_format_convert,
    current_date,
    DB_TYPE
)

def test_basic_connection():
    """Prueba 1: Conexión básica"""
    print("\n" + "="*50)
    print("TEST 1: Conexión básica")
    print("="*50)
    
    if test_connection():
        print("✅ Conexión exitosa")
        info = get_db_info()
        print(f"📊 Tipo de BD: {info['type']}")
        print(f"🔗 URL: {info['url']}")
    else:
        print("❌ Error de conexión")
        return False
    
    return True


def test_query_simple():
    """Prueba 2: Query simple"""
    print("\n" + "="*50)
    print("TEST 2: Query simple")
    print("="*50)
    
    try:
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT COUNT(*) as total 
                FROM ventas_saldos_raw
            """, conn)
            
            total = df['total'].iloc[0]
            print(f"✅ Query exitosa")
            print(f"📦 Total registros en ventas_saldos_raw: {total}")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_query_con_fechas():
    """Prueba 3: Query con fechas compatibles"""
    print("\n" + "="*50)
    print("TEST 3: Query con fechas (últimos 30 días)")
    print("="*50)
    
    try:
        fecha_desde = date_subtract_days(30)
        fecha_col = date_format_convert('h.f_sistema')
        
        print(f"🔧 SQL fecha generado: {fecha_desde}")
        print(f"🔧 SQL conversión: {fecha_col}")
        
        with get_connection() as conn:
            query = f"""
                SELECT COUNT(*) as total
                FROM ventas_historico_raw h
                WHERE {fecha_col} >= {fecha_desde}
            """
            df = pd.read_sql(query, conn)
            
            total = df['total'].iloc[0]
            print(f"✅ Query con fechas exitosa")
            print(f"📊 Ventas últimos 30 días: {total}")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_config_tiendas():
    """Prueba 4: Tabla de configuración"""
    print("\n" + "="*50)
    print("TEST 4: Tabla config_tiendas")
    print("="*50)
    
    try:
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT COUNT(*) as total, 
                       COUNT(DISTINCT region) as regiones
                FROM config_tiendas
            """, conn)
            
            total = df['total'].iloc[0]
            regiones = df['regiones'].iloc[0]
            
            print(f"✅ Query exitosa")
            print(f"🏪 Total tiendas: {total}")
            print(f"🗺️  Regiones: {regiones}")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_helpers():
    """Prueba 5: Funciones helper"""
    print("\n" + "="*50)
    print("TEST 5: Funciones helper")
    print("="*50)
    
    print(f"🔧 current_date(): {current_date()}")
    print(f"🔧 date_subtract_days(30): {date_subtract_days(30)}")
    print(f"🔧 date_format_convert('f_sistema'): {date_format_convert('f_sistema')}")
    print(f"✅ Helpers funcionando")
    
    return True


def main():
    """Ejecutar todos los tests"""
    print("\n🧪 INICIANDO PRUEBAS DE BASE DE DATOS")
    print(f"🔧 Tipo de BD actual: {DB_TYPE}")
    
    tests = [
        test_basic_connection,
        test_query_simple,
        test_query_con_fechas,
        test_config_tiendas,
        test_helpers
    ]
    
    resultados = []
    for test in tests:
        try:
            resultado = test()
            resultados.append(resultado)
        except Exception as e:
            print(f"❌ Test falló con excepción: {e}")
            resultados.append(False)
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*50)
    exitosos = sum(resultados)
    total = len(resultados)
    print(f"✅ Tests exitosos: {exitosos}/{total}")
    
    if exitosos == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("✅ La abstracción de BD está funcionando correctamente")
        print("✅ Puedes seguir desarrollando sin problemas")
        print("✅ Cuando quieras migrar a PostgreSQL, solo cambia .env")
    else:
        print("\n⚠️  ALGUNOS TESTS FALLARON")
        print("🔧 Revisa los errores arriba")
    
    return exitosos == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)