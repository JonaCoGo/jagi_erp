# main.py

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from urllib.parse import unquote
import os
import shutil
import pandas as pd
import logging
from app.database import get_connection, test_connection, get_db_info, DATA_DIR, date_subtract_days, date_format_convert
from app.consultas import(
    get_reabastecimiento_avanzado,
    get_redistribucion_regional,
    get_existencias_por_tienda,
    get_movimiento,
    get_resumen_movimiento,
    get_faltantes,
    get_consulta_producto,
    get_analisis_marca
)
from app.cargar_csv import resetear_y_cargar
from app.reports.excel_exporter import exportar_excel_formateado

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="JAGI ERP API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta a la BD usando la variable que creamos en database.py
DB_PATH = os.path.join(DATA_DIR, "jagi_mahalo.db")

# ---------------------- MODELOS Pydantic ----------------------
class ProductoNuevo(BaseModel):
    c_barra: str
    d_marca: str
    color: Optional[str] = "SIN COLOR"

class ReabastecimientoParams(BaseModel):
    dias_reab: int = 10
    dias_exp: int = 60
    ventas_min_exp: int = 3
    solo_con_ventas: bool = False
    nuevos_codigos: Optional[List[ProductoNuevo]] = None

class ReabastecimientoExportParams(BaseModel):
    dias_reab: int = 10
    dias_exp: int = 60
    ventas_min_exp: int = 3
    solo_con_ventas: bool = False
    nuevos_codigos: Optional[List[ProductoNuevo]] = None
    columnas_seleccionadas: Optional[List[str]] = None
    tiendas_filtro: Optional[List[str]] = None
    observaciones_filtro: Optional[List[str]] = None

class RedistribucionParams(BaseModel):
    dias: int = 30
    ventas_min: int = 1
    tienda_origen: Optional[str] = None

class ExistenciasParams(BaseModel):
    tienda: Optional[str] = None
    marca: Optional[str] = None
    stock_min: Optional[int] = 0
    stock_max: Optional[int] = 999999
    region: Optional[str] = None

class FaltantesParams(BaseModel):
    dias_sin_venta: Optional[int] = 90
    region: Optional[str] = None
    tienda: Optional[str] = None
    marca: Optional[str] = None

class ExportarPreviewParams(BaseModel):
    datos: List[dict]
    nombre_reporte: str = "Reporte"

class TiendaCreate(BaseModel):
    raw_name: str
    clean_name: str
    region: Optional[str] = None
    fija: bool = False

class TiendaUpdate(BaseModel):
    clean_name: Optional[str] = None
    region: Optional[str] = None
    fija: Optional[bool] = None

# ---------------------- ENDPOINTS ----------------------

# ===== INICIO =====
@app.get("/")
def read_root():
    return {"message": "JAGI ERP API v1.0 (Architecture Upgrade)"}

# ========== Salud de BD ==========
@app.get("/health/database")
async def health_database():
    """Verifica el estado de la conexión a la base de datos"""
    is_connected = test_connection()
    db_info = get_db_info()
    
    return {"status": "healthy" if is_connected else "unhealthy", "info": db_info}

# ===== OBTENER OPCIONES PARA FILTROS =====
@app.get("/reportes/opciones-tiendas")
async def obtener_opciones_tiendas():
    try:
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT DISTINCT COALESCE(ct.clean_name, s.d_almacen) AS tienda
                FROM ventas_saldos_raw s
                LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
                ORDER BY tienda
            """, conn)
            return JSONResponse({"success": True, "datos": df['tienda'].tolist()})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/opciones-marcas")
async def obtener_opciones_marcas():
    try:
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT DISTINCT d_marca
                FROM ventas_saldos_raw
                WHERE d_marca IS NOT NULL AND d_marca != ''
                ORDER BY d_marca
            """, conn)
            return JSONResponse({"success": True, "datos": df['d_marca'].tolist()})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/opciones-regiones")
async def obtener_opciones_regiones():
    try:
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT DISTINCT region
                FROM config_tiendas
                WHERE region IS NOT NULL AND region != ''
                ORDER BY region
            """, conn)
            return JSONResponse({"success": True, "datos": df['region'].tolist()})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== CARGAR CSV =====
@app.post("/cargar-csv")
async def cargar_csv_files(files: List[UploadFile] = File(...)):
    try:
        # 1. Definimos la ruta de destino (data/inputs) usando DATA_DIR de database.py
        inputs_dir = os.path.join(DATA_DIR, "inputs")
        os.makedirs(inputs_dir, exist_ok=True)

        # Nombres exactos que espera tu lógica de negocio
        expected_files = ["1.Ventas-Saldos.csv", "2.Inventario-Bodega.csv", "3.Ventas-Historico.csv"]

        # 2. Guardamos los archivos ÚNICAMENTE en la carpeta de datos
        for i, file in enumerate(files):
            if i < len(expected_files):
                file_path = os.path.join(inputs_dir, expected_files[i])
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                logging.info(f"✅ Archivo guardado en: {file_path}")

        # 3. Llamamos a tu función de carga que ya sabe leer de esa carpeta
        resetear_y_cargar()

        return {"message": "Datos cargados exitosamente", "archivos": len(files)}
    
    except Exception as e:
        logging.error(f"Error en carga de CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ACTUALIZAR INVENTARIO =====
@app.post("/actualizar-inventario")
async def actualizar_inventario_fisico(file: UploadFile = File(...)):
    try:
        file_path = "inventario_actualizado.xlsx"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if not os.path.exists(DB_PATH):
            raise HTTPException(status_code=404, detail="Base de datos no encontrada")

        backup_path = DB_PATH.replace(".db", "_backup.db")
        shutil.copy(DB_PATH, backup_path)

        df = pd.read_excel(file_path)
        df.columns = [c.strip().lower() for c in df.columns]

        if "producto_id" not in df.columns or "cantidad_fisica" not in df.columns:
            raise HTTPException(status_code=400, detail="Faltan columnas requeridas: producto_id, cantidad_fisica")

        with get_connection() as conn:
            cursor = conn.connection.cursor()

        actualizados = 0
        no_encontrados = []

        for _, row in df.iterrows():
            c_barra = str(row["producto_id"]).strip()
            cantidad = float(row["cantidad_fisica"]) if pd.notna(row["cantidad_fisica"]) else 0
            
            # Obtener el costo unitario actual antes de actualizar
            cursor.execute("SELECT costo_uni FROM inventario_bodega_raw WHERE c_barra = ?", (c_barra,))
            row_costo = cursor.fetchone()
            
            if row_costo and row_costo[0] is not None:
                costo_unitario = float(row_costo[0])
                nuevo_pr_costo = cantidad * costo_unitario
                
                # Actualizar cantidad y recalcular pr_costo
                cursor.execute("""
                    UPDATE inventario_bodega_raw
                    SET saldo_disponibles = ?, saldo = ?, pr_costo = ?
                    WHERE c_barra = ?;
                """, (cantidad, cantidad, nuevo_pr_costo, c_barra))
                
                actualizados += 1
            else:
                no_encontrados.append(c_barra)

        conn.commit()

        if no_encontrados:
            pd.DataFrame({"producto_id": no_encontrados}).to_excel("codigos_no_encontrados.xlsx", index=False)

        return {
            "message": "Inventario actualizado exitosamente",
            "archivos": file.filename,
            "actualizados": actualizados,
            "no_encontrados": len(no_encontrados)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== REPORTES =====
@app.post("/reabastecimiento")
async def generar_reabastecimiento(params: ReabastecimientoExportParams):
    """
    Genera reporte de reabastecimiento con filtros opcionales.
    Compatible con versión anterior (backward compatible).
    """
    try:
        # Convertir nuevos_codigos de Pydantic a dict si existen
        nuevos_codigos_dict = None
        if params.nuevos_codigos:
            nuevos_codigos_dict = [
                {
                    "c_barra": p.c_barra,
                    "d_marca": p.d_marca,
                    "color": p.color
                }
                for p in params.nuevos_codigos
            ]
        
        # Generar reporte completo
        df = get_reabastecimiento_avanzado(
            dias_reab=params.dias_reab,
            dias_exp=params.dias_exp,
            ventas_min_exp=params.ventas_min_exp,
            solo_con_ventas=params.solo_con_ventas,
            nuevos_codigos=nuevos_codigos_dict
        )
        
        if "region" in df.columns:
            df = df.drop(columns=["region"])
        
        # ← APLICAR FILTROS (solo si existen)
        if params.tiendas_filtro and len(params.tiendas_filtro) > 0:
            df = df[df['tienda'].isin(params.tiendas_filtro)]
            logging.info(f"Filtro de tiendas aplicado: {len(params.tiendas_filtro)} tiendas")
        
        if params.observaciones_filtro and len(params.observaciones_filtro) > 0:
            df = df[df['observacion'].isin(params.observaciones_filtro)]
            logging.info(f"Filtro de observaciones aplicado: {params.observaciones_filtro}")
        
        # ← FILTRAR COLUMNAS (solo si existen)
        if params.columnas_seleccionadas and len(params.columnas_seleccionadas) > 0:
            columnas_validas = [col for col in params.columnas_seleccionadas if col in df.columns]
            if columnas_validas:
                df = df[columnas_validas]
                logging.info(f"Filtro de columnas aplicado: {len(columnas_validas)} columnas")
        
        # Validación: asegurarse de que hay datos para exportar
        if df.empty:
            raise HTTPException(
                status_code=400, 
                detail="No hay datos para exportar con los filtros aplicados"
            )
        
        archivo = "reabastecimiento_jagi.xlsx"
        exportar_excel_formateado(df, archivo, "Reabastecimiento")
        
        logging.info(f"Reporte generado: {len(df)} registros")
        
        return FileResponse(
            archivo, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            filename=archivo
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en reabastecimiento: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/reabastecimiento/columnas-disponibles")
async def obtener_columnas_reabastecimiento(params: ReabastecimientoParams):
    """
    Retorna las columnas disponibles en el reporte de reabastecimiento
    sin generar el archivo completo (más rápido)
    """
    try:
        nuevos_codigos_dict = None
        if params.nuevos_codigos:
            nuevos_codigos_dict = [
                {
                    "c_barra": p.c_barra,
                    "d_marca": p.d_marca,
                    "color": p.color
                }
                for p in params.nuevos_codigos
            ]
        
        # Generar solo una muestra pequeña para obtener columnas
        df = get_reabastecimiento_avanzado(
            dias_reab=params.dias_reab,
            dias_exp=params.dias_exp,
            ventas_min_exp=params.ventas_min_exp,
            solo_con_ventas=params.solo_con_ventas,
            nuevos_codigos=nuevos_codigos_dict
        )
        
        if "region" in df.columns:
            df = df.drop(columns=["region"])
        
        # Retornar solo las columnas
        columnas = df.columns.tolist()
        
        return JSONResponse({
            "success": True,
            "columnas": columnas,
            "total_registros": len(df)
        })
    except Exception as e:
        logging.error(f"Error al obtener columnas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/reabastecimiento/opciones-filtros")
async def obtener_opciones_filtros(params: ReabastecimientoParams):
    """
    Obtiene las opciones disponibles para filtros:
    - Lista de tiendas
    - Lista de observaciones posibles
    - Total de registros sin filtrar
    """
    try:
        nuevos_codigos_dict = None
        if params.nuevos_codigos:
            nuevos_codigos_dict = [
                {
                    "c_barra": p.c_barra,
                    "d_marca": p.d_marca,
                    "color": p.color
                }
                for p in params.nuevos_codigos
            ]
        
        # Generar reporte completo para obtener opciones
        df = get_reabastecimiento_avanzado(
            dias_reab=params.dias_reab,
            dias_exp=params.dias_exp,
            ventas_min_exp=params.ventas_min_exp,
            solo_con_ventas=params.solo_con_ventas,
            nuevos_codigos=nuevos_codigos_dict
        )
        
        if "region" in df.columns:
            df = df.drop(columns=["region"])
        
        # Extraer opciones únicas
        tiendas = sorted(df['tienda'].dropna().unique().tolist()) if 'tienda' in df.columns else []
        observaciones = sorted(df['observacion'].dropna().unique().tolist()) if 'observacion' in df.columns else []
        columnas = df.columns.tolist()
        
        return JSONResponse({
            "success": True,
            "tiendas": tiendas,
            "observaciones": observaciones,
            "columnas": columnas,
            "total_registros": len(df)
        })
    except Exception as e:
        logging.error(f"Error al obtener opciones de filtros: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/reabastecimiento/preview-filtrado")
async def preview_reabastecimiento_filtrado(params: ReabastecimientoExportParams):
    """
    Genera preview filtrado según tiendas y observaciones seleccionadas.
    Retorna solo primeras 100 filas para mejor rendimiento.
    """
    try:
        nuevos_codigos_dict = None
        if params.nuevos_codigos:
            nuevos_codigos_dict = [
                {
                    "c_barra": p.c_barra,
                    "d_marca": p.d_marca,
                    "color": p.color
                }
                for p in params.nuevos_codigos
            ]
        
        # Generar reporte completo
        df = get_reabastecimiento_avanzado(
            dias_reab=params.dias_reab,
            dias_exp=params.dias_exp,
            ventas_min_exp=params.ventas_min_exp,
            solo_con_ventas=params.solo_con_ventas,
            nuevos_codigos=nuevos_codigos_dict
        )
        
        if "region" in df.columns:
            df = df.drop(columns=["region"])
        
        # ← APLICAR FILTROS
        df_filtrado = df.copy()
        
        # Filtro de tiendas
        if params.tiendas_filtro and len(params.tiendas_filtro) > 0:
            df_filtrado = df_filtrado[df_filtrado['tienda'].isin(params.tiendas_filtro)]
        
        # Filtro de observaciones
        if params.observaciones_filtro and len(params.observaciones_filtro) > 0:
            df_filtrado = df_filtrado[df_filtrado['observacion'].isin(params.observaciones_filtro)]
        
        total_registros = len(df_filtrado)
        
        # Limitar a 100 registros para preview (rendimiento)
        df_preview = df_filtrado.head(100)
        
        # Estadísticas adicionales
        tiendas_incluidas = df_filtrado['tienda'].nunique() if 'tienda' in df_filtrado.columns else 0
        productos_unicos = df_filtrado['c_barra'].nunique() if 'c_barra' in df_filtrado.columns else 0
        
        return JSONResponse({
            "success": True,
            "total_registros": total_registros,
            "preview_registros": len(df_preview),
            "tiendas_incluidas": tiendas_incluidas,
            "productos_unicos": productos_unicos,
            "datos": df_preview.to_dict(orient='records')
        })
    except Exception as e:
        logging.error(f"Error en preview filtrado: {e}")
        raise HTTPException(status_code=500, detail=str(e))    

@app.post("/redistribucion")
async def generar_redistribucion(params: RedistribucionParams):
    try:
        df = get_redistribucion_regional(
            dias=params.dias,
            ventas_min=params.ventas_min,
            tienda_origen=params.tienda_origen if params.tienda_origen else None
        )
        if df.empty:
            raise HTTPException(status_code=404, detail="No hay redistribuciones sugeridas")
        archivo = "redistribucion_regional.xlsx"
        exportar_excel_formateado(df, archivo, f"Redistribución {params.dias} días")
        return FileResponse(archivo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=archivo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== PREVIEWS =====
@app.post("/reabastecimiento-preview")
async def preview_reabastecimiento(params: ReabastecimientoParams):
    try:
        # Convertir nuevos_codigos de Pydantic a dict si existen
        nuevos_codigos_dict = None
        if params.nuevos_codigos:
            nuevos_codigos_dict = [
                {
                    "c_barra": p.c_barra,
                    "d_marca": p.d_marca,
                    "color": p.color
                }
                for p in params.nuevos_codigos
            ]
        
        df = get_reabastecimiento_avanzado(
            dias_reab=params.dias_reab,
            dias_exp=params.dias_exp,
            ventas_min_exp=params.ventas_min_exp,
            solo_con_ventas=params.solo_con_ventas,
            nuevos_codigos=nuevos_codigos_dict  # ⭐ PASAR NUEVOS CÓDIGOS
        )
        
        if "region" in df.columns:
            df = df.drop(columns=["region"])
        
        datos = df.to_dict(orient='records')
        return JSONResponse({"success": True, "total": len(datos), "datos": datos[:10000]})
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/exportar-preview-personalizado")
async def exportar_preview_personalizado(params: ExportarPreviewParams):
    """
    Exporta datos del preview con columnas personalizadas ya filtradas
    """
    try:
        if not params.datos or len(params.datos) == 0:
            raise HTTPException(status_code=400, detail="No hay datos para exportar")
        
        # Convertir datos a DataFrame
        df = pd.DataFrame(params.datos)
        
        # Generar nombre de archivo seguro
        nombre_archivo = params.nombre_reporte.replace(' ', '_').lower()
        archivo = f"{nombre_archivo}_personalizado.xlsx"
        
        # Exportar con formato
        exportar_excel_formateado(df, archivo, params.nombre_reporte)
        
        return FileResponse(
            archivo, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            filename=archivo
        )
    except Exception as e:
        logging.error(f"Error al exportar preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/redistribucion-preview")
async def preview_redistribucion(params: RedistribucionParams):
    try:
        df = get_redistribucion_regional(
            dias=params.dias,
            ventas_min=params.ventas_min,
            tienda_origen=params.tienda_origen if params.tienda_origen else None
        )
        if df.empty:
            return JSONResponse({"success": False, "message": "No hay redistribuciones sugeridas"})
        datos = df.to_dict(orient='records')
        return JSONResponse({"success": True, "total": len(datos), "datos": datos})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== CONFIGURACIONES =====

@app.get("/config/referencias-fijas")
async def obtener_referencias_fijas():
    try:
        with get_connection() as conn: 
            df = pd.read_sql("SELECT cod_barras FROM referencias_fijas", conn)
        return JSONResponse({"success": True, "datos": df['cod_barras'].tolist()})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/config/referencias-fijas/agregar")
async def agregar_referencia_fija(codigo: dict):
    try:
        with get_connection() as conn:
            cursor = conn.connection.cursor()
            cursor.execute("INSERT INTO referencias_fijas (cod_barras) VALUES (?)", (codigo.get('codigo'),))
            conn.commit()
        return JSONResponse({"success": True, "message": "Referencia agregada"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.delete("/config/referencias-fijas/{codigo:path}")
async def eliminar_referencia_fija(codigo: str):
    try:
        codigo = unquote(codigo)
        logging.info(f"🗑️ Eliminando referencia fija: {codigo}")
        with get_connection() as conn:
            cursor = conn.connection.cursor()
            cursor.execute("DELETE FROM referencias_fijas WHERE cod_barras = ?", (codigo,))
            filas = cursor.rowcount
            conn.commit()
            if filas == 0:
                return JSONResponse({"success": False, "error": "Código no encontrado"}, status_code=404)
        return JSONResponse({"success": True, "message": f"Referencia {codigo} eliminada"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/config/codigos-excluidos")
async def obtener_codigos_excluidos():
    try:
        with get_connection() as conn:
            df = pd.read_sql("SELECT cod_barras FROM codigos_excluidos", conn)
        return JSONResponse({"success": True, "datos": df['cod_barras'].dropna().astype(str).tolist()})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/config/codigos-excluidos/agregar")
async def agregar_codigo_excluido(codigo: dict):
    try:
        with get_connection() as conn:
            cursor = conn.connection.cursor()
            cursor.execute("INSERT INTO codigos_excluidos (cod_barras) VALUES (?)", (codigo.get('codigo'),))
            conn.commit()
        return JSONResponse({"success": True, "message": "Código excluido agregado"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.delete("/config/codigos-excluidos/{codigo:path}")
async def eliminar_codigo_excluido(codigo: str):
    try:
        codigo = unquote(codigo)
        logging.info(f"🗑️ Eliminando código excluido: {codigo}")
        with get_connection() as conn:
            cursor = conn.connection.cursor()
            cursor.execute("DELETE FROM codigos_excluidos WHERE cod_barras = ?", (codigo,))
            filas = cursor.rowcount
            conn.commit()
            if filas == 0:
                return JSONResponse({"success": False, "error": "Código no encontrado"}, status_code=404)
        return JSONResponse({"success": True, "message": "Código eliminado"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/config/stock-minimo")
async def obtener_stock_minimo():
    try:
        with get_connection() as conn:
            df = pd.read_sql("SELECT tipo, cantidad FROM stock_minimo_config", conn)

            datos = {row['tipo']: int(row['cantidad']) for _, row in df.iterrows()}
            if 'general' in datos and 'default' not in datos:
                datos['default'] = datos['general']

            campos_default = {'fijo_especial': 8, 'fijo_normal': 5, 'multimarca': 2, 'jgl': 3, 'jgm': 3, 'default': 4}
            for k, v in campos_default.items():
                if k not in datos:
                    datos[k] = v

        return JSONResponse({"success": True, "datos": datos})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/config/stock-minimo/actualizar")
async def actualizar_stock_minimo(config: dict):
    try:
        logging.info(f"📝 Recibiendo configuración stock: {config}")
        with get_connection() as conn:
            cursor = conn.connection.cursor()
            for tipo, cantidad in config.items():
                cursor.execute("INSERT OR REPLACE INTO stock_minimo_config (tipo, cantidad) VALUES (?, ?)", (tipo, cantidad))
            conn.commit()
        return JSONResponse({"success": True, "message": "Configuración actualizada correctamente"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/config/tiendas-stats")
async def obtener_stats_tiendas():
    try:
        with get_connection() as conn:
            cursor = conn.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM config_tiendas")
            total = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM config_tiendas WHERE fija = 1")
            fijas = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(DISTINCT region) FROM config_tiendas WHERE region IS NOT NULL")
            regiones = cursor.fetchone()[0] or 0
        return JSONResponse({"success": True, "total": total, "fijas": fijas, "regiones": regiones})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})
    
@app.get("/stats")
async def obtener_estadisticas_dashboard():
    """Devuelve métricas generales para el dashboard principal"""
    try:
        with get_connection() as conn:
            cursor = conn.connection.cursor()

            # Total de productos únicos
            cursor.execute("SELECT COUNT(DISTINCT c_barra) FROM ventas_saldos_raw WHERE c_barra IS NOT NULL")
            total_productos = cursor.fetchone()[0] or 0

            # Total de tiendas activas (excluyendo bodegas)
            cursor.execute("""
                SELECT COUNT(DISTINCT d_almacen)
                FROM ventas_saldos_raw
                WHERE d_almacen NOT LIKE '%BODEGA%'
            """)
            tiendas = cursor.fetchone()[0] or 0

            # Productos con bajo stock
            cursor.execute("""
                SELECT COUNT(*)
                FROM ventas_saldos_raw
                WHERE saldo_disponible < 5 AND saldo_disponible >= 0
            """)
            pendientes_reabastecer = cursor.fetchone()[0] or 0

            # Productos con sobrestock y sin ventas recientes
            cursor.execute("""
                SELECT COUNT(DISTINCT s.c_barra)
                FROM ventas_saldos_raw s
                WHERE s.saldo_disponible > 10
                AND s.c_barra NOT IN (
                    SELECT DISTINCT c_barra
                    FROM ventas_historico_raw
                    WHERE DATE(substr(f_sistema,7,4)||'-'||substr(f_sistema,4,2)||'-'||substr(f_sistema,1,2))
                    >= DATE('now', '-30 days')
                )
            """)
            redistribuciones = cursor.fetchone()[0] or 0

        return {
            "success": True,
            "totalProductos": total_productos,
            "tiendas": tiendas,
            "pendientesReabastecer": pendientes_reabastecer,
            "redistribucionesSugeridas": redistribuciones
        }

    except Exception as e:
        print(f"❌ Error en /stats: {e}")
        return {
            "success": False,
            "totalProductos": 0,
            "tiendas": 0,
            "pendientesReabastecer": 0,
            "redistribucionesSugeridas": 0,
            "error": str(e)
        }    

@app.get("/config/tiendas")
async def obtener_todas_tiendas():
    """Obtiene listado completo de tiendas"""
    try:
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT raw_name, clean_name, region, fija
                FROM config_tiendas
                ORDER BY clean_name
            """, conn)
            
            tiendas = df.to_dict(orient='records')
        return JSONResponse({"success": True, "datos": tiendas})
    except Exception as e:
        logging.error(f"Error al obtener tiendas: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/config/tiendas/agregar")
async def agregar_tienda(tienda: TiendaCreate):
    """Agrega una nueva tienda a la configuración"""
    try:
        with get_connection() as conn:
            cursor = conn.connection.cursor()
            
            # Verificar si ya existe
            cursor.execute("SELECT COUNT(*) FROM config_tiendas WHERE raw_name = ?", (tienda.raw_name,))
            if cursor.fetchone()[0] > 0:
                return JSONResponse({"success": False, "error": "La tienda ya existe"}, status_code=400)
            
            cursor.execute("""
                INSERT INTO config_tiendas (raw_name, clean_name, region, fija)
                VALUES (?, ?, ?, ?)
            """, (tienda.raw_name, tienda.clean_name, tienda.region, 1 if tienda.fija else 0))
            
            conn.commit()
            
        return JSONResponse({"success": True, "message": "Tienda agregada correctamente"})
    except Exception as e:
        logging.error(f"Error al agregar tienda: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.put("/config/tiendas/{raw_name:path}")
async def actualizar_tienda(raw_name: str, tienda: TiendaUpdate):
    """Actualiza los datos de una tienda"""
    try:
        raw_name = unquote(raw_name)
        with get_connection() as conn:
            cursor = conn.connection.cursor()
            
            updates = []
            params = []
            
            if tienda.clean_name is not None:
                updates.append("clean_name = ?")
                params.append(tienda.clean_name)
            
            if tienda.region is not None:
                updates.append("region = ?")
                params.append(tienda.region)
            
            if tienda.fija is not None:
                updates.append("fija = ?")
                params.append(1 if tienda.fija else 0)
            
            if not updates:
                return JSONResponse({"success": False, "error": "No hay datos para actualizar"})
            
            params.append(raw_name)
            query = f"UPDATE config_tiendas SET {', '.join(updates)} WHERE raw_name = ?"
            
            cursor.execute(query, params)
            filas = cursor.rowcount
            conn.commit()
            
            if filas == 0:
                return JSONResponse({"success": False, "error": "Tienda no encontrada"}, status_code=404)
        
        return JSONResponse({"success": True, "message": "Tienda actualizada correctamente"})
    except Exception as e:
        logging.error(f"Error al actualizar tienda: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.delete("/config/tiendas/{raw_name:path}")
async def eliminar_tienda(raw_name: str):
    """Elimina una tienda de la configuración"""
    try:
        raw_name = unquote(raw_name)
        logging.info(f"🗑️ Eliminando tienda: {raw_name}")
        
        with get_connection() as conn:
            cursor = conn.connection.cursor()
            
            cursor.execute("DELETE FROM config_tiendas WHERE raw_name = ?", (raw_name,))
            filas = cursor.rowcount
            conn.commit()
            
            if filas == 0:
                return JSONResponse({"success": False, "error": "Tienda no encontrada"}, status_code=404)
            
        return JSONResponse({"success": True, "message": f"Tienda {raw_name} eliminada"})
    except Exception as e:
        logging.error(f"Error al eliminar tienda: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/config/regiones-disponibles")
async def obtener_regiones_disponibles():
    """Obtiene lista de regiones únicas"""
    try:
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT DISTINCT region
                FROM config_tiendas
                WHERE region IS NOT NULL AND region != ''
                ORDER BY region
            """, conn)
        return JSONResponse({"success": True, "datos": df['region'].tolist()})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/validar-codigo-lanzamiento/{codigo:path}")
async def validar_codigo_lanzamiento(codigo: str):
    """
    Valida si un código de barras existe en la BD.
    Si existe, retorna marca y color.
    Si no existe, indica que es un nuevo producto.
    """
    try:
        with get_connection() as conn:
            # Buscar primero en ventas_saldos_raw
            query = """
            SELECT DISTINCT 
                c_barra,
                d_marca,
                d_color_proveedor AS color
            FROM ventas_saldos_raw
            WHERE c_barra = ?
            LIMIT 1
            """
            df = pd.read_sql(query, conn, params=(codigo,))
            
            if not df.empty:
                # Producto existe
                producto = df.iloc[0]
                return JSONResponse({
                    "success": True,
                    "existe": True,
                    "c_barra": producto['c_barra'],
                    "marca": producto['d_marca'],
                    "color": producto['color'] if pd.notna(producto['color']) else 'SIN COLOR'
                })
            
            # Si no está en ventas_saldos, buscar en inventario_bodega
            query_bodega = """
            SELECT DISTINCT 
                c_barra,
                d_marca,
                d_color_proveedor AS color
            FROM inventario_bodega_raw
            WHERE c_barra = ?
            LIMIT 1
            """
            df_bodega = pd.read_sql(query_bodega, conn, params=(codigo,))
            
            if not df_bodega.empty:
                # Producto existe en bodega
                producto = df_bodega.iloc[0]
                return JSONResponse({
                    "success": True,
                    "existe": True,
                    "c_barra": producto['c_barra'],
                    "marca": producto['d_marca'],
                    "color": producto['color'] if pd.notna(producto['color']) else 'SIN COLOR'
                })
            
        # Producto no existe - es nuevo
        return JSONResponse({
            "success": True,
            "existe": False,
            "mensaje": "Producto nuevo - ingresa marca y color manualmente"
        })
            
    except Exception as e:
        logging.error(f"Error al validar código: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500) 

# ===== CONSULTA DE PRODUCTO =====
@app.get("/consulta-producto")
async def consultar_producto(codigo_barras: str):
    """
    Endpoint para consultar información detallada de un producto.
    Retorna existencias, ventas, velocidad, historial, etc.
    """
    try:
        resultado = get_consulta_producto(codigo_barras)
        
        if not resultado.get("encontrado"):
            raise HTTPException(
                status_code=404, 
                detail=resultado.get("mensaje", "Producto no encontrado")
            )
        
        return JSONResponse({"success": True, "datos": resultado})
    
    except Exception as e:
        logging.error(f"Error en consulta de producto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== BÚSQUEDA POR TÉRMINO =====
@app.get("/buscar-producto/{termino}")
async def buscar_producto(termino: str):
    """
    Busca productos que coincidan con el término (código o marca).
    Útil para autocompletado.
    """
    try:
        with get_connection() as conn:
        
            query = """
            SELECT DISTINCT 
                c_barra,
                d_marca,
                d_color_proveedor as color
            FROM ventas_saldos_raw
            WHERE c_barra LIKE ? OR d_marca LIKE ?
            LIMIT 20
            """
            
            termino_busqueda = f"%{termino}%"
            df = pd.read_sql(query, conn, params=(termino_busqueda, termino_busqueda))
            
            resultados = df.to_dict(orient='records')
        
        return JSONResponse({
            "success": True,
            "resultados": resultados,
            "total": len(resultados)
        })
    
    except Exception as e:
        logging.error(f"Error en búsqueda de producto: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ===== REPORTES CON FILTROS =====

@app.post("/reportes/existencias-preview")
async def preview_existencias(params: ExistenciasParams):
    try:
        with get_connection() as conn:
                query = """
                SELECT 
                    COALESCE(ct.clean_name, s.d_almacen) AS tienda,
                    ct.region,
                    s.c_barra,
                    s.d_marca,
                    s.d_color_proveedor AS color,
                    s.saldo_disponible AS stock_actual
                FROM ventas_saldos_raw s
                LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
                WHERE s.saldo_disponible BETWEEN ? AND ?
                """
                
                params_list = [params.stock_min, params.stock_max]
                
                if params.tienda:
                    query += " AND COALESCE(ct.clean_name, s.d_almacen) LIKE ?"
                    params_list.append(f"%{params.tienda}%")
                
                if params.marca:
                    query += " AND s.d_marca LIKE ?"
                    params_list.append(f"%{params.marca}%")
                
                if params.region:
                    query += " AND ct.region LIKE ?"
                    params_list.append(f"%{params.region}%")
                
                query += " ORDER BY ct.region, tienda, s.d_marca, s.c_barra"
                
                df = pd.read_sql(query, conn, params=params_list)
                
                if df.empty:
                    return JSONResponse({"success": False, "message": "No hay datos con los filtros aplicados"})
                
                datos = df.to_dict(orient='records')
        return JSONResponse({"success": True, "total": len(datos), "datos": datos})
            
    except Exception as e:
        logging.error(f"Error en preview existencias: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reportes/existencias")
async def generar_existencias(params: ExistenciasParams):
    try:
        with get_connection() as conn:
                query = """
                SELECT 
                    COALESCE(ct.clean_name, s.d_almacen) AS tienda,
                    ct.region,
                    s.c_barra,
                    s.d_marca,
                    s.d_color_proveedor AS color,
                    s.saldo_disponible AS stock_actual,
                    s.precio_venta,
                    (s.saldo_disponible * COALESCE(s.precio_venta * 0.6, 1)) AS valor_inventario
                FROM ventas_saldos_raw s
                LEFT JOIN config_tiendas ct ON s.d_almacen = ct.raw_name
                WHERE s.saldo_disponible BETWEEN ? AND ?
                """
                
                params_list = [params.stock_min, params.stock_max]
                
                if params.tienda:
                    query += " AND COALESCE(ct.clean_name, s.d_almacen) LIKE ?"
                    params_list.append(f"%{params.tienda}%")
                
                if params.marca:
                    query += " AND s.d_marca LIKE ?"
                    params_list.append(f"%{params.marca}%")
                
                if params.region:
                    query += " AND ct.region LIKE ?"
                    params_list.append(f"%{params.region}%")
                
                query += " ORDER BY ct.region, tienda, s.d_marca, s.c_barra"
                
                df = pd.read_sql(query, conn, params=params_list)
                
                if df.empty:
                    raise HTTPException(status_code=404, detail="No hay datos con los filtros aplicados")
                
                archivo = "existencias_detalle.xlsx"
                exportar_excel_formateado(df, archivo, f"Existencias - {len(df)} productos")
        return FileResponse(archivo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=archivo)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reportes/faltantes-preview")
async def preview_faltantes(params: FaltantesParams):
    try:
        # ✅ Importar funciones helper

        with get_connection() as conn:
                # Consulta base con placeholders correctos

                fecha_desde = date_subtract_days(params.dias_sin_venta)
                fecha_col = date_format_convert('f_sistema')

                query = f"""
                WITH productos_con_venta AS (
                    SELECT DISTINCT c_barra
                    FROM ventas_historico_raw
                    WHERE {fecha_col} >= {fecha_desde}
                ),
                tiendas_activas AS (
                    SELECT raw_name, clean_name, region
                    FROM config_tiendas
                    WHERE clean_name NOT LIKE '%BODEGA%'
                )
                SELECT DISTINCT
                    t.clean_name AS tienda,
                    t.region,
                    s.c_barra,
                    s.d_marca,
                    s.d_color_proveedor AS color,
                    s.saldo_disponible AS stock_actual
                FROM ventas_saldos_raw s
                JOIN tiendas_activas t ON s.d_almacen = t.raw_name
                LEFT JOIN productos_con_venta p ON s.c_barra = p.c_barra
                WHERE s.saldo_disponible = 0
                AND p.c_barra IS NULL
                """
                
                # Reemplazar el placeholder de días directamente en la query
               
                params_list = []
                
                if params.region:
                    query += " AND t.region LIKE ?"
                    params_list.append(f"%{params.region}%")
                
                if params.tienda:
                    query += " AND t.clean_name LIKE ?"
                    params_list.append(f"%{params.tienda}%")
                
                if params.marca:
                    query += " AND s.d_marca LIKE ?"
                    params_list.append(f"%{params.marca}%")
                
                query += " ORDER BY t.region, tienda, s.d_marca, s.c_barra"
                
                df = pd.read_sql(query, conn, params=params_list)
                
                if df.empty:
                    return JSONResponse({"success": False, "message": "No hay faltantes con los filtros aplicados"})
                
                datos = df.to_dict(orient='records')
        return JSONResponse({"success": True, "total": len(datos), "datos": datos})
            
    except Exception as e:
        logging.error(f"Error en preview faltantes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reportes/faltantes")
async def generar_faltantes(params: FaltantesParams):
    try:

        with get_connection() as conn:
                
                fecha_desde = date_subtract_days(params.dias_sin_venta)
                fecha_col = date_format_convert('f_sistema')

                query = f"""
                WITH productos_con_venta AS (
                    SELECT DISTINCT c_barra
                    FROM ventas_historico_raw
                    WHERE {fecha_col} >= {fecha_desde}
                ),
                tiendas_activas AS (
                    SELECT raw_name, clean_name, region
                    FROM config_tiendas
                    WHERE clean_name NOT LIKE '%BODEGA%'
                )
                SELECT DISTINCT
                    t.clean_name AS tienda,
                    t.region,
                    s.c_barra,
                    s.d_marca,
                    s.d_color_proveedor AS color,
                    s.saldo_disponible AS stock_actual
                FROM ventas_saldos_raw s
                JOIN tiendas_activas t ON s.d_almacen = t.raw_name
                LEFT JOIN productos_con_venta p ON s.c_barra = p.c_barra
                WHERE s.saldo_disponible = 0
                AND p.c_barra IS NULL
                """
                
                params_list = []
                
                if params.region:
                    query += " AND t.region LIKE ?"
                    params_list.append(f"%{params.region}%")
                
                if params.tienda:
                    query += " AND t.clean_name LIKE ?"
                    params_list.append(f"%{params.tienda}%")
                
                if params.marca:
                    query += " AND s.d_marca LIKE ?"
                    params_list.append(f"%{params.marca}%")
                
                query += " ORDER BY t.region, tienda, s.d_marca, s.c_barra"
                
                df = pd.read_sql(query, conn, params=params_list)
                
                if df.empty:
                    raise HTTPException(status_code=404, detail="No hay faltantes con los filtros aplicados")
                
                archivo = "faltantes_detalle.xlsx"
                exportar_excel_formateado(df, archivo, f"Faltantes - {len(df)} productos")
        return FileResponse(archivo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=archivo)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analisis-marca/{marca}")
async def analisis_marca_completo(marca: str):
    """
    Endpoint para análisis completo de una marca.
    """
    try:
        resultado = get_analisis_marca(marca)
        return JSONResponse({"success": True, "datos": resultado})
    except Exception as e:
        logging.error(f"Error en análisis de marca: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 

# ---------------------- MAIN ----------------------
if __name__ == "__main__":
    import uvicorn
    logging.info("🚀 Iniciando servidor JAGI ERP API en http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
