import sqlite3

DB_NAME = "jagi_mahalo.db"

def create_schema():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # --- TABLAS SIMPLES ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS codigos_excluidos (
        cod_barras TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS referencias_fijas (
        cod_barras TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS marcas_multimarca (
        marca TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS map_marcas (
        raw_name TEXT,
        clean_name TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_minimo_config (
        tipo TEXT,
        cantidad INTEGER
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS config_tiendas (
        raw_name TEXT,
        clean_name TEXT,
        region TEXT,
        fija INTEGER,
        tipo_tienda TEXT
    );
    """)

    # --- INVENTARIO ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventario_bodega_raw (
        c_almacen INTEGER,
        d_almacen TEXT,
        c_referencia INTEGER,
        d_referencia_prov TEXT,
        d_referencia TEXT,
        c_barra TEXT,
        c_talla TEXT,
        d_talla TEXT,
        c_color_proveedor TEXT,
        d_color_proveedor TEXT,
        c_proveedor INTEGER,
        d_proveedor TEXT,
        c_linea INTEGER,
        d_linea TEXT,
        c_categoria INTEGER,
        d_categoria TEXT,
        c_subcategoria INTEGER,
        d_subcategoria TEXT,
        c_segmento INTEGER,
        d_segmento TEXT,
        c_sector INTEGER,
        d_sector TEXT,
        c_marca INTEGER,
        d_marca TEXT,
        c_coleccion INTEGER,
        d_coleccion TEXT,
        costo_uni INTEGER,
        precio_venta_un INTEGER,
        stock_min INTEGER,
        stock_max INTEGER,
        saldo INTEGER,
        saldo_transito INTEGER,
        pr_venta INTEGER,
        saldo_separados INTEGER,
        saldo_disponibles INTEGER,
        pr_costo INTEGER
    );
    """)

    # --- VENTAS HISTORICO ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas_historico_raw (
        c_almacen REAL,
        d_almacen TEXT,
        c_producto REAL,
        d_referencia_prov TEXT,
        d_producto TEXT,
        c_barra TEXT,
        c_talla TEXT,
        d_talla TEXT,
        c_color_proveedor TEXT,
        d_color_proveedor TEXT,
        c_marca REAL,
        d_marca TEXT,
        c_coleccion REAL,
        d_coleccion TEXT,
        f_sistema TEXT,
        vr_bruto REAL,
        vr_neto REAL,
        vr_descuento REAL,
        vr_descuento_por REAL,
        vr_iva REAL,
        cn_venta REAL
    );
    """)

    # --- VENTAS SALDOS ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas_saldos_raw (
        c_almacen INTEGER,
        d_almacen TEXT,
        c_producto INTEGER,
        d_referencia_prov TEXT,
        d_producto TEXT,
        c_barra TEXT,
        c_talla TEXT,
        d_talla TEXT,
        c_color_proveedor TEXT,
        d_color_proveedor TEXT,
        c_marca INTEGER,
        d_marca TEXT,
        c_coleccion INTEGER,
        d_coleccion TEXT,
        to_cantidad REAL,
        tot_venta REAL,
        tot_costo REAL,
        to_saldo REAL,
        saldo_fecha REAL,
        saldo_transito REAL,
        saldo_separado REAL,
        saldo_disponible REAL
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Base de datos creada correctamente (estructura vacía)")

if __name__ == "__main__":
    create_schema()