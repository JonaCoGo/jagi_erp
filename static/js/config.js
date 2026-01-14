// config.js
// ========================================
// CONFIGURACIÓN GLOBAL DEL SISTEMA
// ========================================

const CONFIG = {
    // URL del backend API
    API_URL: 'http://127.0.0.1:8000',
    
    // Configuración de paginación
    REGISTROS_POR_PAGINA: 50,
    
    // Valores por defecto para formularios
    DEFAULTS: {
        diasReabastecimiento: 10,
        diasExpansion: 60,
        ventasMinExpansion: 3,
        diasRedistribucion: 30,
        ventasMinRedistribucion: 1
    },
    
    // Mensajes del sistema
    MESSAGES: {
        cargaExitosa: 'Datos cargados exitosamente ✅',
        errorConexion: 'Error de conexión con el servidor',
        errorCarga: 'Error al cargar datos',
        confirmEliminar: '¿Seguro que deseas eliminar este código?',
        sinRegistros: 'No hay registros disponibles',
        generandoReporte: 'Generando reporte...'
    },
    
    // Archivos CSV esperados
    ARCHIVOS_CSV: [
        "1.Ventas-Saldos.csv",
        "2.Inventario-Bodega.csv",
        "3.Ventas-Historico.csv"
    ],
    
    // Tiempo de duración de notificaciones (ms)
    NOTIFICATION_DURATION: 5000,
    
    // Módulos disponibles
    MODULOS: [
        'dashboard',
        'carga',
        'reabastecimiento',
        'redistribucion',
        'reportes',
        'configuracion',
        'analytics'
    ]
};

// Exportar configuración
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}