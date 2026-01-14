import sqlite3
from datetime import datetime, timedelta
import random

DB_NAME = "jagi_mahalo.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# =============================
# CONFIGURACIÓN BASE (FAKE)
# =============================

TIENDAS = [
    ('TIENDA MEDELLIN', 'MEDELLIN', 'ANTIOQUIA', 1, 'FISICA'),
    ('TIENDA BOGOTA', 'BOGOTA', 'CUNDINAMARCA', 0, 'FISICA'),
    ('TIENDA CALI', 'CALI', 'VALLE', 0, 'FISICA'),
    ('TIENDA BARRANQUILLA', 'BARRANQUILLA', 'ATLANTICO', 0, 'FISICA'),
    ('TIENDA ONLINE', 'ONLINE', 'NACIONAL', 1, 'ONLINE')
]

MARCAS = ['MARCA_DEMO_A', 'MARCA_DEMO_B', 'MARCA_DEMO_C', 'MARCA_DEMO_D']

# =============================
# TIENDAS
# =============================

cursor.executemany("""
INSERT INTO config_tiendas (raw_name, clean_name, region, fija, tipo_tienda)
VALUES (?, ?, ?, ?, ?)
""", TIENDAS)

# =============================
# MARCAS
# =============================

cursor.executemany("""
INSERT INTO map_marcas (raw_name, clean_name)
VALUES (?, ?)
""", [(m, m.replace('_DEMO_', ' ')) for m in MARCAS])

cursor.executemany("""
INSERT INTO marcas_multimarca (marca)
VALUES (?)
""", [(m,) for m in MARCAS])

# =============================
# CONFIGURACIÓN STOCK
# =============================

cursor.execute("""
INSERT INTO stock_minimo_config (tipo, cantidad)
VALUES ('GENERAL', 5)
""")

# =============================
# INVENTARIO (20 PRODUCTOS)
# =============================

productos = []
barras = []

for i in range(1, 21):
    c_barra = f"7700000000{i:02d}"
    barras.append(c_barra)
    marca = random.choice(MARCAS)
    precio = random.randint(65000, 350000)
    costo = int(precio * 0.5)
    saldo = random.randint(5, 80)

    productos.append((
        1, 'BODEGA CENTRAL', 1000 + i, f'REF-PROV-{i:03d}', f'PRODUCTO_DEMO_{i}',
        c_barra, 'M', 'MEDIUM', 'COL', 'COLOR DEMO',
        1, 'PROVEEDOR DEMO', 1, 'LINEA DEMO', 1, 'CATEGORIA DEMO',
        1, 'SUBCATEGORIA DEMO', 1, 'SEGMENTO DEMO', 1, 'SECTOR DEMO',
        MARCAS.index(marca) + 1, marca, 2025, 'COLECCION 2025',
        costo, precio, 5, 100, saldo, 0, precio, 0, saldo, costo
    ))

cursor.executemany("""
INSERT INTO inventario_bodega_raw (
    c_almacen, d_almacen, c_referencia, d_referencia_prov, d_referencia,
    c_barra, c_talla, d_talla, c_color_proveedor, d_color_proveedor,
    c_proveedor, d_proveedor, c_linea, d_linea, c_categoria, d_categoria,
    c_subcategoria, d_subcategoria, c_segmento, d_segmento, c_sector, d_sector,
    c_marca, d_marca, c_coleccion, d_coleccion, costo_uni, precio_venta_un,
    stock_min, stock_max, saldo, saldo_transito, pr_venta, saldo_separados,
    saldo_disponibles, pr_costo
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", productos)

# =============================
# CODIGOS EXCLUIDOS
# =============================

cursor.executemany("""
INSERT INTO codigos_excluidos (cod_barras)
VALUES (?)
""", [(barras[0],), (barras[5],)])

# =============================
# REFERENCIAS FIJAS
# =============================

cursor.executemany("""
INSERT INTO referencias_fijas (cod_barras)
VALUES (?)
""", [(barras[1],), (barras[10],)])

# =============================
# VENTAS HISTÓRICAS (50)
# =============================

ventas_historico = []
fecha_base = datetime(2025, 1, 1)

for _ in range(50):
    prod = random.choice(productos)
    fecha = fecha_base + timedelta(days=random.randint(0, 200))
    bruto = prod[27]
    descuento = bruto * 0.1
    neto = bruto - descuento
    iva = neto * 0.19

    ventas_historico.append((
        prod[0], 'BODEGA CENTRAL', prod[2], prod[3], prod[4],
        prod[5], prod[6], prod[7], prod[8], prod[9],
        prod[22], prod[23], prod[24], prod[25], fecha.strftime('%Y-%m-%d'),
        bruto, neto, descuento, 10, iva, 1
    ))

cursor.executemany("""
INSERT INTO ventas_historico_raw (
    c_almacen, d_almacen, c_producto, d_referencia_prov, d_producto,
    c_barra, c_talla, d_talla, c_color_proveedor, d_color_proveedor,
    c_marca, d_marca, c_coleccion, d_coleccion, f_sistema,
    vr_bruto, vr_neto, vr_descuento, vr_descuento_por, vr_iva, cn_venta
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", ventas_historico)

# =============================
# VENTAS SALDOS
# =============================

for prod in productos:
    cursor.execute("""
    INSERT INTO ventas_saldos_raw (
        c_almacen, d_almacen, c_producto, d_referencia_prov, d_producto,
        c_barra, c_talla, d_talla, c_color_proveedor, d_color_proveedor,
        c_marca, d_marca, c_coleccion, d_coleccion,
        to_cantidad, tot_venta, tot_costo, to_saldo,
        saldo_fecha, saldo_transito, saldo_separado, saldo_disponible
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        prod[0], 'BODEGA CENTRAL', prod[2], prod[3], prod[4],
        prod[5], prod[6], prod[7], prod[8], prod[9],
        prod[22], prod[23], prod[24], prod[25],
        10, prod[27] * 10, prod[26] * 10, prod[30],
        prod[30], 0, 0, prod[30]
    ))

conn.commit()
conn.close()

print("✅ Seed completo y corregido: esquema 100% compatible")
