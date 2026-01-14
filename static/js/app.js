// app.js

// ========================================
// LÓGICA PRINCIPAL DEL SISTEMA JAGI ERP
// ========================================

// ==========================================
// 1. VARIABLES GLOBALES Y ESTADO
// ==========================================
let datosPreview = null;
let paginaActual = 1;
let tipoModalActual = null; // 'filtros' o 'preview'

// ==========================================
// 2. INICIALIZACIÓN
// ==========================================
window.addEventListener('load', () => {
    inicializarFecha();
    cargarEstadisticas();
    inicializarGraficos();
    configurarEventListeners();
});

function inicializarFecha() {
    const fechaElement = document.getElementById('currentDate');
    if (fechaElement) {
        fechaElement.textContent = new Date().toLocaleDateString('es-ES', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
    
    const updateElement = document.getElementById('lastUpdate');
    if (updateElement) {
        updateElement.textContent = new Date().toLocaleString('es-ES');
    }
}

function configurarEventListeners() {
    // Búsqueda en tabla
    const searchInput = document.getElementById('searchTable');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            paginaActual = 1;
            renderizarTabla();
        });
    }
}

// ==========================================
// 3. NAVEGACIÓN ENTRE MÓDULOS
// ==========================================
function showModule(moduleName) {
    // Ocultar todos los módulos
    document.querySelectorAll('.module-content').forEach(m => {
        m.classList.add('hidden');
    });
    
    // Mostrar módulo seleccionado
    const moduloActivo = document.getElementById(`module-${moduleName}`);
    if (moduloActivo) {
        moduloActivo.classList.remove('hidden');
    }

    // Si estás entrando al módulo de análisis de marca, reiniciar
    if (moduleName === 'analisis-marca') {
        reiniciarAnalisisMarca();
    }
    
    // Actualizar estilos de navegación
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('border-blue-600', 'text-blue-600');
        btn.classList.add('text-gray-600');
    });
    
    const activeBtn = document.querySelector(`[data-module="${moduleName}"]`);
    if (activeBtn) {
        activeBtn.classList.add('border-blue-600', 'text-blue-600');
        activeBtn.classList.remove('text-gray-600');
    }
    
    // Cargar datos según módulo
    if (moduleName === 'dashboard') {
        cargarEstadisticas();
    } else if (moduleName === 'configuracion') {
        cargarConfiguraciones();
    }
}

// ==========================================
// 4. SISTEMA DE NOTIFICACIONES
// ==========================================
function showNotification(message, type = 'success') {
    const container = document.getElementById('notifications');
    if (!container) return;
    
    const notif = document.createElement('div');
    notif.className = `notification p-4 rounded-lg shadow-lg text-white flex items-center gap-2 ${
        type === 'success' ? 'bg-green-500' : 'bg-red-500'
    }`;
    notif.innerHTML = `
        <span>${type === 'success' ? '✓' : '✗'}</span>
        <span>${message}</span>
    `;
    
    container.appendChild(notif);
    
    setTimeout(() => {
        notif.remove();
    }, CONFIG.NOTIFICATION_DURATION);
}

// ==========================================
// 5. ESTADÍSTICAS DEL DASHBOARD
// ==========================================
async function cargarEstadisticas() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/stats`);
        
        if (response.ok) {
            const stats = await response.json();
            
            actualizarElemento('stat-productos', stats.totalProductos.toLocaleString());
            actualizarElemento('stat-tiendas', stats.tiendas.toLocaleString());
            actualizarElemento('stat-reabastecer', stats.pendientesReabastecer.toLocaleString());
            actualizarElemento('stat-redistribuir', stats.redistribucionesSugeridas.toLocaleString());
            
            // Remover animación pulse
            document.querySelectorAll('.pulse').forEach(el => el.classList.remove('pulse'));
            
            // Actualizar estado de conexión
            actualizarEstadoConexion('status-bd', true);
            actualizarEstadoConexion('status-server', true);
        } else {
            throw new Error('Error al cargar estadísticas');
        }
    } catch (error) {
        console.error('Error:', error);
        actualizarEstadoConexion('status-server', false);
    }
}

function actualizarElemento(id, valor) {
    const elemento = document.getElementById(id);
    if (elemento) {
        elemento.textContent = valor;
    }
}

function actualizarEstadoConexion(id, conectado) {
    const elemento = document.getElementById(id);
    if (elemento) {
        elemento.textContent = conectado ? '✓' : '✗';
        elemento.className = conectado ? 'text-green-500' : 'text-red-500';
    }
}

// ==========================================
// 6. MODAL DE VISTA PREVIA
// ==========================================
function abrirModal(titulo, datos) {
    datosPreview = datos;
    paginaActual = 1;
    tipoModalActual = 'preview'; // Establecer tipo de modal
    
    const modal = document.getElementById('previewModal');
    const modalTitle = document.getElementById('modalTitle');
    const tablaSeccion = document.getElementById('tabla-seccion');
    const filtrosSeccion = document.getElementById('filtros-seccion');
    
    if (modalTitle) modalTitle.textContent = titulo;
    if (modal) modal.classList.remove('hidden');
    
    // Asegurar que se muestre la tabla normal y se oculte la sección de filtros
    if (tablaSeccion) tablaSeccion.classList.remove('hidden');
    if (filtrosSeccion) filtrosSeccion.classList.add('hidden');
    
    renderizarTabla();
}

function cerrarModal() {
    const modal = document.getElementById('previewModal');
    if (modal) modal.classList.add('hidden');
    
    datosPreview = null;
    tipoModalActual = null; // Resetear tipo de modal
    
    // Asegurar que se muestre la tabla normal y se oculte la sección de filtros
    const tablaSeccion = document.getElementById('tabla-seccion');
    const filtrosSeccion = document.getElementById('filtros-seccion');
    
    if (tablaSeccion) tablaSeccion.classList.remove('hidden');
    if (filtrosSeccion) filtrosSeccion.classList.add('hidden');
}

function renderizarTabla() {
    if (!datosPreview || datosPreview.length === 0) return;

    const thead = document.getElementById('previewTableHead');
    const tbody = document.getElementById('previewTableBody');
    const search = document.getElementById('searchTable').value.toLowerCase();
    
    // Filtrar datos
    let datosFiltrados = datosPreview.filter(row => 
        Object.values(row).some(val => 
            String(val).toLowerCase().includes(search)
        )
    );

    // Renderizar estadísticas
    renderizarEstadisticasPreview(datosFiltrados);

    // Paginación
    const inicio = (paginaActual - 1) * CONFIG.REGISTROS_POR_PAGINA;
    const fin = inicio + CONFIG.REGISTROS_POR_PAGINA;
    const datosPagina = datosFiltrados.slice(inicio, fin);

    // Renderizar headers
    if (datosPagina.length > 0) {
        const columnas = Object.keys(datosPagina[0]);
        thead.innerHTML = '<tr>' + columnas.map(col => 
            `<th class="p-2 border bg-gray-100 text-left text-xs font-semibold">${col}</th>`
        ).join('') + '</tr>';

        // Filtro de columnas
        const filterSelect = document.getElementById('filterColumn');
        if (filterSelect) {
            filterSelect.innerHTML = '<option value="">Todas las columnas</option>' + 
                columnas.map(col => `<option value="${col}">${col}</option>`).join('');
        }
    }

    // Renderizar filas
    tbody.innerHTML = datosPagina.map((row, idx) => {
        const clase = idx % 2 === 0 ? 'bg-white' : 'bg-gray-50';
        return '<tr class="' + clase + ' hover:bg-blue-50">' + 
            Object.values(row).map(val => 
                `<td class="p-2 border text-xs">${val !== null && val !== undefined ? val : '-'}</td>`
            ).join('') + 
        '</tr>';
    }).join('');

    // Info paginación
    actualizarInfoPaginacion(inicio, fin, datosFiltrados.length);
    
    // Botones paginación
    renderizarBotonesPaginacion(datosFiltrados.length);
}

function renderizarEstadisticasPreview(datos) {
    const stats = document.getElementById('previewStats');
    if (!stats) return;
    
    stats.innerHTML = `
        <div class="bg-blue-50 p-3 rounded text-center">
            <div class="text-2xl font-bold text-blue-600">${datos.length}</div>
            <div class="text-xs text-gray-600">Total Registros</div>
        </div>
        <div class="bg-green-50 p-3 rounded text-center">
            <div class="text-2xl font-bold text-green-600">${
                new Set(datos.map(r => r.tienda || r.tienda_destino)).size
            }</div>
            <div class="text-xs text-gray-600">Tiendas</div>
        </div>
        <div class="bg-orange-50 p-3 rounded text-center">
            <div class="text-2xl font-bold text-orange-600">${
                new Set(datos.map(r => r.c_barra)).size
            }</div>
            <div class="text-xs text-gray-600">Productos</div>
        </div>
        <div class="bg-purple-50 p-3 rounded text-center">
            <div class="text-2xl font-bold text-purple-600">${
                datos.reduce((sum, r) => sum + (r.cantidad_a_despachar || r.cantidad_sugerida || 0), 0)
            }</div>
            <div class="text-xs text-gray-600">Unidades Total</div>
        </div>
    `;
}

function actualizarInfoPaginacion(inicio, fin, total) {
    const recordCount = document.getElementById('recordCount');
    if (recordCount) {
        recordCount.textContent = `Mostrando ${inicio + 1}-${Math.min(fin, total)} de ${total} registros`;
    }
}

function renderizarBotonesPaginacion(totalRegistros) {
    const totalPaginas = Math.ceil(totalRegistros / CONFIG.REGISTROS_POR_PAGINA);
    const pagination = document.getElementById('pagination');
    if (!pagination) return;
    
    pagination.innerHTML = '';
    
    if (paginaActual > 1) {
        pagination.innerHTML += `
            <button onclick="paginaActual--; renderizarTabla()" 
                class="px-3 py-1 bg-blue-600 text-white rounded text-sm">
                ← Anterior
            </button>`;
    }
    
    pagination.innerHTML += `
        <span class="px-3 py-1 bg-gray-200 rounded text-sm">
            Página ${paginaActual} de ${totalPaginas}
        </span>`;
    
    if (paginaActual < totalPaginas) {
        pagination.innerHTML += `
            <button onclick="paginaActual++; renderizarTabla()" 
                class="px-3 py-1 bg-blue-600 text-white rounded text-sm">
                Siguiente →
            </button>`;
    }
}

// ==========================================
// 7. CARGA DE DATOS
// ==========================================
async function cargarCSV() {
    const files = document.getElementById('csvFiles').files;
    
    if (files.length !== 3) {
        showNotification('Debes seleccionar los 3 archivos CSV', 'error');
        return;
    }

    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    try {
        showNotification('Cargando archivos...', 'success');
        
        const response = await fetch(`${CONFIG.API_URL}/cargar-csv`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            showNotification(result.message);
            cargarEstadisticas();
            inicializarFecha();
        } else {
            showNotification('Error al cargar archivos', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

async function actualizarInventario() {
    const file = document.getElementById('inventarioFile').files[0];
    
    if (!file) {
        showNotification('Debes seleccionar un archivo Excel', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        showNotification('Actualizando inventario...', 'success');
        
        const response = await fetch(`${CONFIG.API_URL}/actualizar-inventario`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            showNotification(`${result.message} - ${result.actualizados} registros actualizados`);
            cargarEstadisticas();
        } else {
            showNotification('Error al actualizar inventario', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

// ==========================================
// 8. REABASTECIMIENTO
// ==========================================
async function generarReabastecimiento() {
    const params = obtenerParametrosReabastecimiento();

    try {
        showNotification('Generando análisis de reabastecimiento...', 'success');
        
        const response = await fetch(`${CONFIG.API_URL}/reabastecimiento-preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                abrirModal(`Reabastecimiento - ${result.total} registros`, result.datos);
            } else {
                showNotification('No hay datos para mostrar', 'error');
            }
        } else {
            showNotification('Error al generar preview', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

async function generarReabastecimientoDirecto() {
    // En lugar de exportar directamente, abrir selector de columnas
    abrirModalExportacionAvanzada();
}

function obtenerParametrosReabastecimiento() {
    return {
        dias_reab: parseInt(document.getElementById('diasReab').value),
        dias_exp: parseInt(document.getElementById('diasExp').value),
        ventas_min_exp: parseInt(document.getElementById('ventasMinExp').value),
        solo_con_ventas: document.getElementById('soloVentas').checked,
        nuevos_codigos: listaLanzamientos.length > 0 ? listaLanzamientos : null
    };
}

async function exportarDesdePreview() {
    if (!datosPreview || datosPreview.length === 0) {
        showNotification('No hay datos para exportar', 'error');
        return;
    }
    
    // Inicializar estado desde preview
    estadoFiltros.columnas = Object.keys(datosPreview[0]);
    estadoFiltros.columnasSeleccionadas = [...estadoFiltros.columnas];
    estadoFiltros.datosPreview = datosPreview;
    
    // Para preview, ir directo a selección de columnas
    // (ya tiene filtros aplicados)
    showNotification('Configura las columnas a exportar...', 'success');
    
    // Aquí podrías abrir solo el selector de columnas simple
    // o usar el modal completo pero saltando a pestaña de columnas
    abrirSelectorColumnasSimple();
}
// Función simplificada para exportar desde preview
function abrirSelectorColumnasSimple() {
    columnasDisponibles = estadoFiltros.columnas;
    columnasSeleccionadas = [...estadoFiltros.columnas];
    window.datosParaExportar = estadoFiltros.datosPreview;
    
    mostrarModalColumnas(); // Usar el modal simple original
}

// ==========================================
// 9. REDISTRIBUCIÓN
// ==========================================
async function generarRedistribucion() {
    const params = obtenerParametrosRedistribucion();

    try {
        showNotification('Generando análisis de redistribución...', 'success');
        
        const response = await fetch(`${CONFIG.API_URL}/redistribucion-preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                abrirModal(`Redistribución - ${result.total} registros`, result.datos);
            } else {
                showNotification(result.message || 'No hay redistribuciones sugeridas', 'error');
            }
        } else {
            showNotification('Error al generar preview', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

async function generarRedistribucionDirecto() {
    const params = obtenerParametrosRedistribucion();

    try {
        showNotification(CONFIG.MESSAGES.generandoReporte, 'success');
        
        const response = await fetch(`${CONFIG.API_URL}/redistribucion`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (response.ok) {
            descargarArchivo(response, 'redistribucion_regional.xlsx');
            showNotification('Reporte de redistribución generado');
        } else {
            showNotification('No hay redistribuciones sugeridas', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

function obtenerParametrosRedistribucion() {
    return {
        dias: parseInt(document.getElementById('diasRedist').value),
        ventas_min: parseInt(document.getElementById('ventasMinRedist').value),
        tienda_origen: document.getElementById('tiendaOrigen').value || null
    };
}

// ==========================================
// 10. REPORTES
// ==========================================
async function generarReporte(tipo) {
    try {
        // Abrir modal de filtros en lugar de generar directamente
        abrirModalFiltrosReporte(tipo);
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

// Función para abrir modal de filtros
function abrirModalFiltrosReporte(tipo) {
    const modal = document.getElementById('previewModal');
    const modalTitle = document.getElementById('modalTitle');
    const tablaSeccion = document.getElementById('tabla-seccion');
    const filtrosSeccion = document.getElementById('filtros-seccion');
    
    if (modalTitle) modalTitle.textContent = `Filtros - ${tipo === 'existencias' ? 'Existencias' : 'Faltantes'}`;
    if (modal) modal.classList.remove('hidden');
    
    // Establecer tipo de modal
    tipoModalActual = 'filtros';
    
    // Mostrar sección de filtros, ocultar tabla normal
    if (tablaSeccion) tablaSeccion.classList.add('hidden');
    if (filtrosSeccion) filtrosSeccion.classList.remove('hidden');
    
    // Cargar opciones en los desplegables
    cargarOpcionesFiltros();
    
    // Limpiar filtros
    document.getElementById('filtro-tienda').value = '';
    document.getElementById('filtro-marca').value = '';
    document.getElementById('filtro-region').value = '';
    
    // Configurar valores por defecto según el tipo de reporte
    if (tipo === 'existencias') {
        document.getElementById('filtro-dias').value = '90';
        document.getElementById('filtro-stock-min').value = '0';
        document.getElementById('filtro-stock-max').value = '999999';
    } else if (tipo === 'faltantes') {
        document.getElementById('filtro-dias').value = '90';
        document.getElementById('filtro-stock-min').value = '';
        document.getElementById('filtro-stock-max').value = '';
    }
    
    // Actualizar botones según el tipo de reporte
    actualizarBotonesFiltros(tipo);
}

// Función para actualizar botones según el tipo de reporte
function actualizarBotonesFiltros(tipo) {
    const botonPreview = document.querySelector('#filtros-seccion button[onclick*="generarReporteConFiltros"]');
    const botonExportar = document.querySelector('#filtros-seccion button[onclick*="generarReporteDirecto"]');
    
    if (botonPreview) {
        botonPreview.onclick = () => generarReporteConFiltros(tipo);
    }
    if (botonExportar) {
        botonExportar.onclick = () => generarReporteDirecto(tipo);
    }
}

// Función para cargar opciones en los desplegables
async function cargarOpcionesFiltros() {
    try {
        // Cargar tiendas
        const tiendasResponse = await fetch(`${CONFIG.API_URL}/reportes/opciones-tiendas`);
        if (tiendasResponse.ok) {
            const tiendasData = await tiendasResponse.json();
            llenarSelect('filtro-tienda', tiendasData.datos || []);
        }

        // Cargar marcas
        const marcasResponse = await fetch(`${CONFIG.API_URL}/reportes/opciones-marcas`);
        if (marcasResponse.ok) {
            const marcasData = await marcasResponse.json();
            llenarSelect('filtro-marca', marcasData.datos || []);
        }

        // Cargar regiones
        const regionesResponse = await fetch(`${CONFIG.API_URL}/reportes/opciones-regiones`);
        if (regionesResponse.ok) {
            const regionesData = await regionesResponse.json();
            llenarSelect('filtro-region', regionesData.datos || []);
        }

    } catch (error) {
        console.error('Error al cargar opciones de filtros:', error);
    }
}

// Función para llenar un select
function llenarSelect(id, datos) {
    const select = document.getElementById(id);
    if (!select) return;
    
    select.innerHTML = `<option value="">Todas las ${id.replace('filtro-', '')}</option>`;
    
    datos.forEach(dato => {
        if (dato) { // Solo agregar si no es null o vacío
            const option = document.createElement('option');
            option.value = dato;
            option.textContent = dato;
            select.appendChild(option);
        }
    });
}

// Función para generar reporte con filtros (preview)
async function generarReporteConFiltros(tipo) {
    const params = recolectarFiltros(tipo);
    
    try {
        showNotification(`Generando ${tipo}...`, 'success');
        
        const response = await fetch(`${CONFIG.API_URL}/reportes/${tipo}-preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                // Cambiar a modo preview normal
                tipoModalActual = 'preview';
                
                // Actualizar título del modal
                document.getElementById('modalTitle').textContent = `${tipo.charAt(0).toUpperCase() + tipo.slice(1)} - ${result.total} registros`;
                
                // Cargar los datos en el preview
                datosPreview = result.datos;
                paginaActual = 1;
                
                // Mostrar tabla normal, ocultar filtros
                const tablaSeccion = document.getElementById('tabla-seccion');
                const filtrosSeccion = document.getElementById('filtros-seccion');
                
                if (tablaSeccion) tablaSeccion.classList.remove('hidden');
                if (filtrosSeccion) filtrosSeccion.classList.add('hidden');
                
                renderizarTabla();
                
            } else {
                showNotification(result.message || `No hay ${tipo} con los filtros aplicados`, 'error');
            }
        } else {
            showNotification(`Error al generar ${tipo}`, 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

// Función para generar reporte directo (excel)
async function generarReporteDirecto(tipo) {
    const params = recolectarFiltros(tipo);
    
    try {
        showNotification(`Generando reporte ${tipo}...`, 'success');
        
        const response = await fetch(`${CONFIG.API_URL}/reportes/${tipo}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (response.ok) {
            descargarArchivo(response, `${tipo}_detalle.xlsx`);
            showNotification(`Reporte ${tipo} generado`);
            cerrarModal(); // Cerrar modal después de exportar
        } else {
            showNotification(`Error al generar reporte ${tipo}`, 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

// Función para recolectar filtros
function recolectarFiltros(tipo) {
    const params = {};
    
    const tienda = document.getElementById('filtro-tienda')?.value;
    const marca = document.getElementById('filtro-marca')?.value;
    const region = document.getElementById('filtro-region')?.value;
    
    if (tienda) params.tienda = tienda;
    if (marca) params.marca = marca;
    if (region) params.region = region;
    
    if (tipo === 'existencias') {
        const stockMin = document.getElementById('filtro-stock-min')?.value;
        const stockMax = document.getElementById('filtro-stock-max')?.value;
        if (stockMin) params.stock_min = parseInt(stockMin);
        if (stockMax) params.stock_max = parseInt(stockMax);
    } else if (tipo === 'faltantes') {
        const dias = document.getElementById('filtro-dias')?.value;
        params.dias_sin_venta = dias ? parseInt(dias) : 90;
    }
    
    return params;
}

// ==========================================
// 11. CONFIGURACIONES
// ==========================================
async function cargarConfiguraciones() {
    console.log('📄 Cargando configuraciones...');
    
    try {
        const [resRefs, resExcl, resStock, resTiendas] = await Promise.all([
            fetch(`${CONFIG.API_URL}/config/referencias-fijas`),
            fetch(`${CONFIG.API_URL}/config/codigos-excluidos`),
            fetch(`${CONFIG.API_URL}/config/stock-minimo`),
            fetch(`${CONFIG.API_URL}/config/tiendas-stats`)
        ]);

        const refs = await resRefs.json();
        const excl = await resExcl.json();
        const stock = await resStock.json();
        const tiendas = await resTiendas.json();

        // Renderizar listas
        if (refs.success) {
            renderLista('listaRefFijas', refs.datos || [], 'referencia');
        }
        
        if (excl.success) {
            renderLista('listaExcluidos', excl.datos || [], 'excluido');
        }

        // Cargar stock mínimo
        if (stock.success && stock.datos) {
            cargarStockMinimo(stock.datos);
        }

        // Cargar stats de tiendas
        if (tiendas.success) {
            actualizarElemento('stat-tiendas-config', tiendas.total);
            actualizarElemento('stat-tiendas-fijas', tiendas.fijas);
            actualizarElemento('stat-regiones', tiendas.regiones);
        }

        // ⭐ NUEVO: Cargar tabla de tiendas
        cargarTiendas();

        showNotification('Configuración cargada correctamente ✅');
    } catch (error) {
        console.error('❌ Error al cargar configuraciones:', error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

function cargarStockMinimo(cfg) {
    const campos = ['fijo_especial', 'fijo_normal', 'multimarca', 'jgl', 'jgm', 'default'];
    campos.forEach(campo => {
        const elemento = document.getElementById(`stock_${campo}`);
        if (elemento) {
            elemento.value = cfg[campo] || 0;
        }
    });
}

function renderLista(idTabla, datos, tipo) {
    const tbody = document.getElementById(idTabla);
    if (!tbody) return;
    
    if (!datos || datos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" class="p-3 text-center text-gray-500">Sin registros</td></tr>';
        return;
    }

    tbody.innerHTML = datos.map(cod => {
        const codEscaped = String(cod).replace(/'/g, "\\'").replace(/"/g, '&quot;');
        return `
            <tr>
                <td class="p-2 border-b">${cod}</td>
                <td class="p-2 border-b text-center">
                    <button onclick='eliminarCodigo("${tipo}", "${codEscaped}")'
                        class="bg-red-500 text-white px-2 py-1 rounded text-xs hover:bg-red-600">
                        🗑️
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

async function guardarStockMinimo() {
    const config = {
        fijo_especial: parseInt(document.getElementById('stock_fijo_especial').value) || 0,
        fijo_normal: parseInt(document.getElementById('stock_fijo_normal').value) || 0,
        multimarca: parseInt(document.getElementById('stock_multimarca').value) || 0,
        jgl: parseInt(document.getElementById('stock_jgl').value) || 0,
        jgm: parseInt(document.getElementById('stock_jgm').value) || 0,
        default: parseInt(document.getElementById('stock_default').value) || 0
    };

    try {
        const response = await fetch(`${CONFIG.API_URL}/config/stock-minimo/actualizar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();
        if (result.success) {
            showNotification('Stock mínimo actualizado correctamente ✅');
            cargarConfiguraciones();
        } else {
            showNotification('Error al guardar stock mínimo', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

async function agregarReferencia() {
    const codigo = document.getElementById('nuevaRefFija').value.trim();
    if (!codigo) return showNotification('Ingresa un código', 'error');

    try {
        const response = await fetch(`${CONFIG.API_URL}/config/referencias-fijas/agregar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ codigo })
        });
        
        const result = await response.json();
        if (result.success) {
            showNotification('Referencia agregada correctamente ✅');
            document.getElementById('nuevaRefFija').value = '';
            cargarConfiguraciones();
        } else {
            showNotification('Error al agregar referencia', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

async function agregarExcluido() {
    const codigo = document.getElementById('nuevoExcluido').value.trim();
    if (!codigo) return showNotification('Ingresa un código', 'error');

    try {
        const response = await fetch(`${CONFIG.API_URL}/config/codigos-excluidos/agregar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ codigo })
        });
        
        const result = await response.json();
        if (result.success) {
            showNotification('Código excluido agregado correctamente ✅');
            document.getElementById('nuevoExcluido').value = '';
            cargarConfiguraciones();
        } else {
            showNotification('Error al agregar código excluido', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

async function eliminarCodigo(tipo, codigo) {
    const codigoEncoded = encodeURIComponent(codigo);
    const endpoint = tipo === 'referencia'
        ? `/config/referencias-fijas/${codigoEncoded}`
        : `/config/codigos-excluidos/${codigoEncoded}`;

    if (!confirm(`¿Seguro que deseas eliminar ${codigo}?`)) return;

    try {
        const response = await fetch(`${CONFIG.API_URL}${endpoint}`, { 
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Elemento eliminado correctamente ✅');
            cargarConfiguraciones();
        } else {
            showNotification(`Error: ${result.error || 'Desconocido'}`, 'error');
        }
    } catch (error) {
        console.error('❌ Error:', error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

let tiendaEnEdicion = null;
let modalTiendaAbierto = false;

async function cargarTiendas() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/config/tiendas`);
        const result = await response.json();
        
        if (result.success) {
            renderTablaTiendas(result.datos);
        } else {
            showNotification('Error al cargar tiendas', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

function renderTablaTiendas(tiendas) {
    const tbody = document.getElementById('listaTiendas');
    if (!tbody) return;
    
    if (!tiendas || tiendas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="p-3 text-center text-gray-500">Sin tiendas registradas</td></tr>';
        return;
    }

    tbody.innerHTML = tiendas.map(tienda => `
        <tr class="hover:bg-gray-50">
            <td class="p-2 border-b">${tienda.clean_name || tienda.raw_name}</td>
            <td class="p-2 border-b text-xs text-gray-600">${tienda.raw_name}</td>
            <td class="p-2 border-b">${tienda.region || '-'}</td>
            <td class="p-2 border-b text-center">
                ${tienda.fija ? '<span class="text-green-600">✓</span>' : '<span class="text-gray-400">-</span>'}
            </td>
            <td class="p-2 border-b text-center">
                <button onclick='abrirModalEditarTienda(${JSON.stringify(tienda).replace(/'/g, "&#39;")})' 
                    class="bg-blue-500 text-white px-2 py-1 rounded text-xs hover:bg-blue-600 mr-1">
                    ✏️
                </button>
                <button onclick='eliminarTienda("${tienda.raw_name.replace(/'/g, "\\'")}")' 
                    class="bg-red-500 text-white px-2 py-1 rounded text-xs hover:bg-red-600">
                    🗑️
                </button>
            </td>
        </tr>
    `).join('');
}

function abrirModalNuevaTienda() {
    tiendaEnEdicion = null;
    const modal = document.getElementById('modalTienda');
    const titulo = document.getElementById('modalTiendaTitulo');
    
    if (titulo) titulo.textContent = 'Agregar Nueva Tienda';
    
    // Limpiar formulario
    document.getElementById('tienda-raw-name').value = '';
    document.getElementById('tienda-clean-name').value = '';
    document.getElementById('tienda-region').value = '';
    document.getElementById('tienda-fija').checked = false;
    
    // Habilitar campo raw_name
    document.getElementById('tienda-raw-name').disabled = false;
    
    if (modal) {
        modal.classList.remove('hidden');
        modalTiendaAbierto = true;
    }
}

function abrirModalEditarTienda(tienda) {
    tiendaEnEdicion = tienda;
    const modal = document.getElementById('modalTienda');
    const titulo = document.getElementById('modalTiendaTitulo');
    
    if (titulo) titulo.textContent = 'Editar Tienda';
    
    // Llenar formulario
    document.getElementById('tienda-raw-name').value = tienda.raw_name;
    document.getElementById('tienda-clean-name').value = tienda.clean_name || '';
    document.getElementById('tienda-region').value = tienda.region || '';
    document.getElementById('tienda-fija').checked = tienda.fija === 1;
    
    // Deshabilitar campo raw_name en edición
    document.getElementById('tienda-raw-name').disabled = true;
    
    if (modal) {
        modal.classList.remove('hidden');
        modalTiendaAbierto = true;
    }
}

function cerrarModalTienda() {
    const modal = document.getElementById('modalTienda');
    if (modal) {
        modal.classList.add('hidden');
        modalTiendaAbierto = false;
        tiendaEnEdicion = null;
    }
}

async function guardarTienda() {
    const rawName = document.getElementById('tienda-raw-name').value.trim();
    const cleanName = document.getElementById('tienda-clean-name').value.trim();
    const region = document.getElementById('tienda-region').value.trim();
    const fija = document.getElementById('tienda-fija').checked;
    
    if (!rawName || !cleanName) {
        showNotification('Debes completar los campos obligatorios', 'error');
        return;
    }
    
    try {
        let response;
        
        if (tiendaEnEdicion) {
            // Actualizar tienda existente
            response = await fetch(`${CONFIG.API_URL}/config/tiendas/${encodeURIComponent(rawName)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    clean_name: cleanName,
                    region: region || null,
                    fija: fija
                })
            });
        } else {
            // Crear nueva tienda
            response = await fetch(`${CONFIG.API_URL}/config/tiendas/agregar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    raw_name: rawName,
                    clean_name: cleanName,
                    region: region || null,
                    fija: fija
                })
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(tiendaEnEdicion ? 'Tienda actualizada correctamente ✅' : 'Tienda agregada correctamente ✅');
            cerrarModalTienda();
            cargarTiendas();
            cargarConfiguraciones(); // Actualizar stats
        } else {
            showNotification(result.error || 'Error al guardar tienda', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

async function eliminarTienda(rawName) {
    if (!confirm(`¿Seguro que deseas eliminar la tienda "${rawName}"?`)) return;
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/config/tiendas/${encodeURIComponent(rawName)}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Tienda eliminada correctamente ✅');
            cargarTiendas();
            cargarConfiguraciones(); // Actualizar stats
        } else {
            showNotification(result.error || 'Error al eliminar tienda', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

// Cerrar modal al hacer clic fuera de él
window.addEventListener('click', (e) => {
    const modal = document.getElementById('modalTienda');
    if (modalTiendaAbierto && e.target === modal) {
        cerrarModalTienda();
    }
});

// Cerrar modal con tecla Escape
window.addEventListener('keydown', (e) => {
    if (modalTiendaAbierto && e.key === 'Escape') {
        cerrarModalTienda();
    }
});

// ==========================================
// 12. UTILIDADES
// ==========================================
async function descargarArchivo(response, nombreArchivo) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombreArchivo;
    a.click();
    window.URL.revokeObjectURL(url);
}

function exportarDesdePreview() {
    showNotification('Exportando desde preview...', 'success');
    // Implementación futura
}

function inicializarGraficos() {
    console.log("📊 inicializarGraficos() - función vacía temporalmente");
}

// ==========================================
// 13. CONSULTA DE PRODUCTO
// ==========================================

let chartVentasProducto = null;

// Autocompletado mientras escribe
document.addEventListener('DOMContentLoaded', () => {
    const inputBuscar = document.getElementById('buscarProducto');
    if (inputBuscar) {
        let timeoutBusqueda = null;
        
        inputBuscar.addEventListener('input', (e) => {
            const termino = e.target.value.trim();
            
            if (termino.length < 3) {
                ocultarSugerencias();
                return;
            }
            
            clearTimeout(timeoutBusqueda);
            timeoutBusqueda = setTimeout(() => {
                buscarSugerencias(termino);
            }, 300);
        });
        
        // Buscar al presionar Enter
        inputBuscar.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                buscarProductoPorCodigo();
            }
        });
    }
});

async function buscarSugerencias(termino) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/buscar-producto/${encodeURIComponent(termino)}`);
        
        if (response.ok) {
            const result = await response.json();
            mostrarSugerencias(result.resultados);
        }
    } catch (error) {
        console.error('Error al buscar sugerencias:', error);
    }
}

function mostrarSugerencias(resultados) {
    const container = document.getElementById('sugerenciasProducto');
    if (!container) return;
    
    if (resultados.length === 0) {
        ocultarSugerencias();
        return;
    }
    
    container.innerHTML = resultados.map(r => `
        <div class="p-3 hover:bg-blue-50 cursor-pointer border-b" 
             onclick="seleccionarProducto('${r.c_barra}')">
            <div class="font-medium">${r.c_barra}</div>
            <div class="text-xs text-gray-600">${r.d_marca} - ${r.color || 'Sin color'}</div>
        </div>
    `).join('');
    
    container.classList.remove('hidden');
}

function ocultarSugerencias() {
    const container = document.getElementById('sugerenciasProducto');
    if (container) {
        container.classList.add('hidden');
    }
}

function seleccionarProducto(codigo) {
    document.getElementById('buscarProducto').value = codigo;
    ocultarSugerencias();
    buscarProductoPorCodigo();
}

async function buscarProductoPorCodigo() {
    const codigo = document.getElementById('buscarProducto').value.trim();
    
    if (!codigo) {
        showNotification('Ingresa un código de barras', 'error');
        return;
    }
    
    ocultarSugerencias();
    showNotification('Consultando producto...', 'success');
    
    try {
        const response = await fetch(`${CONFIG.API_URL}/consulta-producto?codigo_barras=${encodeURIComponent(codigo)}`);
        
        if (response.ok) {
            const result = await response.json();
            mostrarResultadoConsulta(result.datos);
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Producto no encontrado', 'error');
            mostrarSinResultados();
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
        mostrarSinResultados();
    }
}

function mostrarResultadoConsulta(datos) {
    // Ocultar mensaje de sin resultados y mostrar contenido
    document.getElementById('sinResultadoConsulta').classList.add('hidden');
    document.getElementById('resultadoConsulta').classList.remove('hidden');
    
    const info = datos.info_general;
    const ventas = datos.ventas;
    
    // Información General
    actualizarElemento('cons-codigo', info.codigo);
    actualizarElemento('cons-marca', info.marca);
    actualizarElemento('cons-color', info.color || 'N/A');
    actualizarElemento('cons-valor', info.valor_inventario 
        ? `${info.valor_inventario.toLocaleString()}` 
        : 'No disponible');
    actualizarElemento('cons-ultima-venta', ventas.ultima_fecha_venta || 'Sin ventas');
    
    // Estadísticas
    actualizarElemento('cons-stock-total', info.stock_total);
    actualizarElemento('cons-stock-tiendas', info.stock_tiendas);
    actualizarElemento('cons-stock-bodega', info.stock_bodega);
    actualizarElemento('cons-ventas-30', ventas.ultimos_30_dias);
    
    // Análisis de Ventas
    actualizarElemento('cons-v30', `${ventas.ultimos_30_dias} unidades`);
    actualizarElemento('cons-v60', `${ventas.ultimos_60_dias} unidades`);
    actualizarElemento('cons-v90', `${ventas.ultimos_90_dias} unidades`);
    actualizarElemento('cons-velocidad', `${ventas.velocidad_dia} unid/día`);
    actualizarElemento('cons-dias-agotar', 
        ventas.dias_para_agotar < 999 ? `${ventas.dias_para_agotar} días` : 'N/A');
    
    // Recomendación
    mostrarRecomendacion(datos.recomendacion);
    
    // Tabla de Distribución
    renderTablaDistribucion(datos.distribucion);
    
    // Tiendas sin producto
    renderTiendasSinProducto(datos.tiendas_sin_producto);
    
    // Historial
    renderHistorial(datos.historial);
    
    // Gráfico
    renderGraficoVentas(datos.grafico_ventas);
}

function mostrarRecomendacion(recomendacion) {
    const container = document.getElementById('cons-recomendacion');
    if (!container) return;
    
    const colores = {
        'critico': 'bg-red-100 text-red-700 border-red-500',
        'alerta': 'bg-yellow-100 text-yellow-700 border-yellow-500',
        'optimo': 'bg-green-100 text-green-700 border-green-500',
        'sin_movimiento': 'bg-gray-100 text-gray-700 border-gray-500'
    };
    
    container.className = `p-4 rounded-lg mb-6 text-center text-lg font-semibold border-l-4 ${colores[recomendacion.estado]}`;
    container.textContent = recomendacion.texto;
}

function renderTablaDistribucion(distribucion) {
    const tbody = document.getElementById('cons-tabla-distribucion');
    if (!tbody) return;
    
    tbody.innerHTML = distribucion.map(d => `
        <tr class="hover:bg-gray-50">
            <td class="p-3">${d.tienda}</td>
            <td class="p-3">${d.region || 'N/A'}</td>
            <td class="p-3 text-right font-semibold">${d.stock_actual}</td>
            <td class="p-3 text-right ${d.ventas_30d > 0 ? 'text-green-600 font-semibold' : 'text-gray-400'}">
                ${d.ventas_30d || '-'}
            </td>
        </tr>
    `).join('');
}

function renderTiendasSinProducto(tiendas) {
    const container = document.getElementById('cons-tiendas-sin');
    if (!container) return;
    
    if (tiendas.length === 0) {
        container.innerHTML = '<p class="text-sm text-gray-500 text-center p-4">El producto está en todas las tiendas</p>';
        return;
    }
    
    container.innerHTML = tiendas.map(t => `
        <div class="p-2 bg-orange-50 rounded text-sm border-l-2 border-orange-400">
            ${t}
        </div>
    `).join('');
}

function renderHistorial(historial) {
    const tbody = document.getElementById('cons-tabla-historial');
    if (!tbody) return;
    
    if (historial.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="p-3 text-center text-gray-500">Sin movimientos recientes</td></tr>';
        return;
    }
    
    tbody.innerHTML = historial.map(h => `
        <tr class="hover:bg-gray-50">
            <td class="p-2">${h.fecha}</td>
            <td class="p-2">${h.tienda}</td>
            <td class="p-2 text-right font-semibold text-green-600">${h.cantidad}</td>
        </tr>
    `).join('');
}

function renderGraficoVentas(datos) {
    const canvas = document.getElementById('graficoVentasProducto');
    if (!canvas) return;
    
    // Destruir gráfico anterior si existe
    if (chartVentasProducto) {
        chartVentasProducto.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    chartVentasProducto = new Chart(ctx, {
        type: 'line',
        data: {
            labels: datos.fechas,
            datasets: [{
                label: 'Ventas Diarias',
                data: datos.valores,
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

function mostrarSinResultados() {
    document.getElementById('resultadoConsulta').classList.add('hidden');
    document.getElementById('sinResultadoConsulta').classList.remove('hidden');
}

// ==========================================
// 14. CONSULTA POR MARCA
// ==========================================

// Función para buscar por marca
async function buscarPorMarcaMarca() {
    const marca = document.getElementById('buscarMarca').value.trim();
    if (!marca) {
        showNotification('Ingresa una marca', 'error');
        return;
    }

    showNotification(`Analizando marca ${marca}...`, 'success');

    try {
        const response = await fetch(`${CONFIG.API_URL}/analisis-marca/${encodeURIComponent(marca)}`);
        
        if (response.ok) {
            const result = await response.json();
            mostrarAnalisisMarca(result.datos);
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Marca no encontrada', 'error');
            
            // Mostrar mensaje de error y ocultar resultados
            document.getElementById('sinResultadoMarca').classList.remove('hidden');
            document.getElementById('resultadoMarca').classList.add('hidden');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
        
        // Mostrar mensaje de error y ocultar resultados
        document.getElementById('sinResultadoMarca').classList.remove('hidden');
        document.getElementById('resultadoMarca').classList.add('hidden');
    }
}

// Función para mostrar el análisis de marca
function mostrarAnalisisMarca(datos) {
    // Limpiar resultados anteriores
    document.getElementById('resultadoMarca').classList.remove('hidden');
    document.getElementById('sinResultadoMarca').classList.add('hidden');

    // Mostrar resumen
    actualizarElemento('marca-nombre', datos.marca);
    actualizarElemento('marca-total-productos', datos.resumen.total_productos);
    actualizarElemento('marca-con-venta', datos.resumen.productos_con_venta);
    actualizarElemento('marca-sin-venta', datos.resumen.productos_sin_venta);
    actualizarElemento('marca-tiendas-cobertura', `${datos.resumen.tiendas_con_marca}/${datos.resumen.tiendas_totales}`);
    actualizarElemento('marca-porcentaje-cobertura', `${datos.resumen.porcentaje_cobertura}%`);
    actualizarElemento('marca-porcentaje-rotacion', `${datos.resumen.porcentaje_rotacion}%`);
    actualizarElemento('marca-valor-inventario', `$${datos.resumen.valor_total_inventario.toLocaleString()}`);

    // Mostrar recomendaciones
    const contenedorRecomendaciones = document.getElementById('marca-recomendaciones');
    contenedorRecomendaciones.innerHTML = datos.recomendaciones.map(rec => 
        `<div class="p-3 mb-2 rounded ${rec.startsWith('⚠️') ? 'bg-yellow-100 text-yellow-800' : rec.startsWith('📊') ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}">
            ${rec}
        </div>`
    ).join('');

    // Mostrar productos
    const tbody = document.getElementById('marca-tabla-productos');
    tbody.innerHTML = datos.productos.slice(0, 50).map(prod => `
        <tr class="hover:bg-gray-50">
            <td class="p-2 border">${prod.c_barra || 'Sin código'}</td>
            <td class="p-2 border">${prod.color || 'Sin color'}</td>
            <td class="p-2 border text-right">${prod.ventas_30d || 0}</td>
            <td class="p-2 border text-right">${prod.tiendas_venta || 0}</td>
            <td class="p-2 border text-right">${prod.tiendas_con_stock || 0}</td>
            <td class="p-2 border text-right">$${(prod.valor_producto || 0).toLocaleString()}</td>
        </tr>
    `).join('');
}

// Función para mostrar el análisis de marca (con vistas (tab))
function mostrarAnalisisMarca(datos) {
    // Limpiar resultados anteriores
    document.getElementById('resultadoMarca').classList.remove('hidden');
    document.getElementById('sinResultadoMarca').classList.add('hidden');

    // Mostrar resumen
    actualizarElemento('marca-nombre', datos.marca);
    actualizarElemento('marca-total-productos', datos.resumen.total_productos);
    actualizarElemento('marca-con-venta', datos.resumen.top10_productos);
    actualizarElemento('marca-sin-venta', datos.resumen.tiendas_totales - datos.resumen.tiendas_con_top10);
    actualizarElemento('marca-porcentaje-rotacion', datos.resumen.oportunidades_redistribucion);
    actualizarElemento('marca-tiendas-cobertura', `${datos.resumen.tiendas_con_top10}/${datos.resumen.tiendas_totales}`);

    // Mostrar recomendaciones
    const contenedorRecomendaciones = document.getElementById('marca-recomendaciones');
    contenedorRecomendaciones.innerHTML = datos.recomendaciones.map(rec => 
        `<div class="p-3 mb-2 rounded ${rec.startsWith('📊') ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}">
            ${rec}
        </div>`
    ).join('');

    // Mostrar vista de Top 10
    const tbodyTop10 = document.getElementById('marca-tabla-top10');
    tbodyTop10.innerHTML = datos.top10.map(prod => `
        <tr class="hover:bg-gray-50">
            <td class="p-2 border font-medium">${prod.c_barra}</td>
            <td class="p-2 border">${prod.color}</td>
            <td class="p-2 border text-right font-bold text-green-700">${prod.ventas_30d}</td>
            <td class="p-2 border text-right">${prod.tiendas_con_producto.length}</td>
            <td class="p-2 border text-right font-bold text-red-700">${prod.tiendas_sin_producto.length}</td>
            <td class="p-2 border text-right">${prod.stock_total}</td>
        </tr>
        <tr>
            <td colspan="6" class="p-2 border text-xs bg-gray-50">
                <div class="grid grid-cols-2 gap-2">
                    <div><span class="font-semibold">En tiendas:</span> ${prod.tiendas_con_producto.join(', ') || 'Ninguna'}</div>
                    <div><span class="font-semibold text-red-600">Faltantes en:</span> ${prod.tiendas_sin_producto.join(', ') || 'Ninguna'}</div>
                </div>
            </td>
        </tr>
    `).join('');

    // Mostrar vista de Tiendas
    const tbodyTiendas = document.getElementById('marca-tabla-tiendas');
    tbodyTiendas.innerHTML = datos.tiendas.map(tienda => `
        <tr class="hover:bg-gray-50">
            <td class="p-2 border font-medium">${tienda.tienda}</td>
            <td class="p-2 border">${tienda.region}</td>
            <td class="p-2 border text-right">${tienda.productos_top10}</td>
            <td class="p-2 border text-right">${tienda.productos_faltantes}</td>
            <td class="p-2 border text-right">${tienda.ventas_top10}</td>
            <td class="p-2 border text-right">${tienda.stock_top10}</td>
        </tr>
    `).join('');

    // Mostrar la primera vista por defecto
    cambiarVistaMarca('top10');
}

// Función para cambiar entre vistas (Top 10 vs Tiendas)
function cambiarVistaMarca(vista) {
    // Ocultar todas las vistas
    document.getElementById('vista-top10').classList.add('hidden');
    document.getElementById('vista-tiendas').classList.add('hidden');
    
    // Ocultar todos los tabs
    document.getElementById('tab-top10').classList.remove('border-blue-600', 'text-blue-600');
    document.getElementById('tab-top10').classList.add('text-gray-600');
    document.getElementById('tab-tiendas').classList.remove('border-blue-600', 'text-blue-600');
    document.getElementById('tab-tiendas').classList.add('text-gray-600');
    
    // Mostrar la vista seleccionada
    if (vista === 'top10') {
        document.getElementById('vista-top10').classList.remove('hidden');
        document.getElementById('tab-top10').classList.add('border-blue-600', 'text-blue-600');
        document.getElementById('tab-top10').classList.remove('text-gray-600');
    } else if (vista === 'tiendas') {
        document.getElementById('vista-tiendas').classList.remove('hidden');
        document.getElementById('tab-tiendas').classList.add('border-blue-600', 'text-blue-600');
        document.getElementById('tab-tiendas').classList.remove('text-gray-600');
    }
}

// ==========================================
// 15. GESTIÓN DE LANZAMIENTOS DE NUEVOS PRODUCTOS
// ==========================================

// Lista temporal de lanzamientos (en memoria)
let listaLanzamientos = [];

/**
 * Valida si el código existe en la BD y autocompleta marca/color
 */
async function validarCodigoLanzamiento() {
    const codigo = document.getElementById('lanzamiento-codigo').value.trim();
    const statusDiv = document.getElementById('lanzamiento-status');
    const inputMarca = document.getElementById('lanzamiento-marca');
    const inputColor = document.getElementById('lanzamiento-color');
    
    if (!codigo) {
        statusDiv.classList.add('hidden');
        inputMarca.value = '';
        inputColor.value = '';
        inputMarca.readOnly = true;
        inputColor.readOnly = true;
        return;
    }
    
    try {
        // Buscar en la BD si el código existe
        const response = await fetch(`${CONFIG.API_URL}/validar-codigo-lanzamiento/${encodeURIComponent(codigo)}`);
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.existe) {
                // Código existe → Autocompletar
                inputMarca.value = result.marca || 'SIN MARCA';
                inputColor.value = result.color || 'SIN COLOR';
                inputMarca.readOnly = true;
                inputColor.readOnly = true;
                
                statusDiv.className = 'mb-3 p-2 rounded text-sm bg-green-100 text-green-800 border border-green-300';
                statusDiv.textContent = `✅ Producto encontrado en BD: ${result.marca}`;
                statusDiv.classList.remove('hidden');
            } else {
                // Código NO existe → Permitir ingreso manual
                inputMarca.value = '';
                inputColor.value = '';
                inputMarca.readOnly = false;
                inputColor.readOnly = false;
                inputMarca.placeholder = 'Ingresa la marca del nuevo producto';
                inputColor.placeholder = 'Ingresa el color del nuevo producto';
                
                statusDiv.className = 'mb-3 p-2 rounded text-sm bg-yellow-100 text-yellow-800 border border-yellow-300';
                statusDiv.textContent = '⚠️ Producto nuevo - Completa la información manualmente';
                statusDiv.classList.remove('hidden');
            }
        }
    } catch (error) {
        console.error('Error al validar código:', error);
        statusDiv.className = 'mb-3 p-2 rounded text-sm bg-red-100 text-red-800 border border-red-300';
        statusDiv.textContent = '❌ Error al validar el código';
        statusDiv.classList.remove('hidden');
    }
}

/**
 * Agrega un nuevo producto a la lista de lanzamientos
 */
function agregarLanzamiento() {
    const codigo = document.getElementById('lanzamiento-codigo').value.trim();
    const marca = document.getElementById('lanzamiento-marca').value.trim();
    const color = document.getElementById('lanzamiento-color').value.trim();
    
    // Validaciones
    if (!codigo) {
        showNotification('Debes ingresar un código de barras', 'error');
        return;
    }
    
    if (!marca) {
        showNotification('Debes ingresar o validar la marca', 'error');
        return;
    }
    
    // Verificar si ya está en la lista
    if (listaLanzamientos.some(item => item.c_barra === codigo)) {
        showNotification('Este código ya está en la lista de lanzamientos', 'error');
        return;
    }
    
    // Agregar a la lista
    listaLanzamientos.push({
        c_barra: codigo,
        d_marca: marca,
        color: color || 'SIN COLOR'
    });
    
    showNotification(`✅ Producto ${codigo} agregado a lanzamientos`);
    
    // Actualizar vista
    renderizarListaLanzamientos();
    limpiarFormularioLanzamiento();
}

/**
 * Renderiza la lista de lanzamientos en la tabla
 */
function renderizarListaLanzamientos() {
    const tbody = document.getElementById('lista-lanzamientos');
    const container = document.getElementById('lista-lanzamientos-container');
    
    if (!tbody || !container) return;
    
    if (listaLanzamientos.length === 0) {
        container.classList.add('hidden');
        return;
    }
    
    container.classList.remove('hidden');
    
    tbody.innerHTML = listaLanzamientos.map((item, index) => `
        <tr class="hover:bg-gray-50">
            <td class="p-2 border-b font-mono">${item.c_barra}</td>
            <td class="p-2 border-b">${item.d_marca}</td>
            <td class="p-2 border-b">${item.color}</td>
            <td class="p-2 border-b text-center">
                <button 
                    onclick="eliminarLanzamiento(${index})" 
                    class="bg-red-500 text-white px-2 py-1 rounded text-xs hover:bg-red-600"
                >
                    🗑️
                </button>
            </td>
        </tr>
    `).join('');
}

/**
 * Elimina un producto de la lista de lanzamientos
 */
function eliminarLanzamiento(index) {
    if (confirm('¿Eliminar este producto de los lanzamientos?')) {
        listaLanzamientos.splice(index, 1);
        renderizarListaLanzamientos();
        showNotification('Producto eliminado de lanzamientos');
    }
}

/**
 * Limpia el formulario de lanzamientos
 */
function limpiarFormularioLanzamiento() {
    document.getElementById('lanzamiento-codigo').value = '';
    document.getElementById('lanzamiento-marca').value = '';
    document.getElementById('lanzamiento-color').value = '';
    
    const statusDiv = document.getElementById('lanzamiento-status');
    if (statusDiv) {
        statusDiv.classList.add('hidden');
    }
    
    const inputMarca = document.getElementById('lanzamiento-marca');
    const inputColor = document.getElementById('lanzamiento-color');
    
    if (inputMarca) {
        inputMarca.readOnly = true;
        inputMarca.placeholder = 'Se autocompleta o ingresa manualmente';
    }
    
    if (inputColor) {
        inputColor.readOnly = true;
        inputColor.placeholder = 'Se autocompleta o ingresa manualmente';
    }
}

/**
 * Limpia toda la lista de lanzamientos
 */
function limpiarTodosLosLanzamientos() {
    if (listaLanzamientos.length === 0) return;
    
    if (confirm('¿Eliminar TODOS los lanzamientos?')) {
        listaLanzamientos = [];
        renderizarListaLanzamientos();
        showNotification('Lista de lanzamientos limpiada');
    }
}

// ==========================================
// 16. SELECTOR DE COLUMNAS PARA EXPORTACIÓN
// ==========================================

let columnasDisponibles = [];
let columnasSeleccionadas = [];

/**
 * Abre el modal de selección de columnas antes de exportar
 */
async function abrirSelectorColumnas() {
    const params = obtenerParametrosReabastecimiento();
    
    try {
        showNotification('Obteniendo columnas disponibles...', 'success');
        
        const response = await fetch(`${CONFIG.API_URL}/reabastecimiento/columnas-disponibles`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (response.ok) {
            const result = await response.json();
            columnasDisponibles = result.columnas;
            columnasSeleccionadas = [...result.columnas]; // Por defecto todas seleccionadas
            
            mostrarModalColumnas();
        } else {
            showNotification('Error al obtener columnas', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

/**
 * Muestra el modal con checkboxes para seleccionar columnas
 */
function mostrarModalColumnas() {
    const modal = document.getElementById('modalSelectorColumnas');
    const listaColumnas = document.getElementById('listaColumnasSelector');
    
    if (!modal || !listaColumnas) {
        console.error('Modal de columnas no encontrado');
        return;
    }
    
    // Limpiar lista anterior
    listaColumnas.innerHTML = '';
    
    // Crear checkboxes para cada columna
    columnasDisponibles.forEach((columna, index) => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-2 p-2 hover:bg-gray-50 rounded';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `col-${index}`;
        checkbox.value = columna;
        checkbox.checked = true; // Por defecto todas seleccionadas
        checkbox.className = 'w-4 h-4';
        checkbox.onchange = (e) => {
            if (e.target.checked) {
                if (!columnasSeleccionadas.includes(columna)) {
                    columnasSeleccionadas.push(columna);
                }
            } else {
                columnasSeleccionadas = columnasSeleccionadas.filter(c => c !== columna);
            }
            actualizarContadorColumnas();
        };
        
        const label = document.createElement('label');
        label.htmlFor = `col-${index}`;
        label.className = 'text-sm cursor-pointer flex-1';
        label.textContent = columna;
        
        div.appendChild(checkbox);
        div.appendChild(label);
        listaColumnas.appendChild(div);
    });
    
    actualizarContadorColumnas();
    modal.classList.remove('hidden');
}

/**
 * Actualiza el contador de columnas seleccionadas
 */
function actualizarContadorColumnas() {
    const contador = document.getElementById('contadorColumnas');
    if (contador) {
        contador.textContent = `${columnasSeleccionadas.length} de ${columnasDisponibles.length} columnas seleccionadas`;
    }
}

/**
 * Selecciona/deselecciona todas las columnas
 */
function toggleTodasColumnas(seleccionar) {
    const checkboxes = document.querySelectorAll('#listaColumnasSelector input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = seleccionar;
    });
    
    if (seleccionar) {
        columnasSeleccionadas = [...columnasDisponibles];
    } else {
        columnasSeleccionadas = [];
    }
    
    actualizarContadorColumnas();
}

/**
 * Cierra el modal de selector de columnas
 */
function cerrarModalColumnas() {
    const modal = document.getElementById('modalSelectorColumnas');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * Confirma la selección y exporta el reporte
 */
async function confirmarYExportar() {
    if (columnasSeleccionadas.length === 0) {
        showNotification('Debes seleccionar al menos una columna', 'error');
        return;
    }
    
    cerrarModalColumnas();
    
    // Verificar si estamos exportando desde preview o desde parámetros
    if (window.datosParaExportar) {
        // Exportar desde preview (datos ya generados)
        exportarPreviewConColumnas();
    } else {
        // Exportar generando nuevo reporte con parámetros
        exportarNuevoReporteConColumnas();
    }
}

/**
 * Exporta los datos del preview filtrando columnas
 */
async function exportarPreviewConColumnas() {
    try {
        showNotification('Generando Excel con columnas personalizadas...', 'success');
        
        // Filtrar datos según columnas seleccionadas
        const datosFiltrados = window.datosParaExportar.map(row => {
            const rowFiltrado = {};
            columnasSeleccionadas.forEach(col => {
                if (row.hasOwnProperty(col)) {
                    rowFiltrado[col] = row[col];
                }
            });
            return rowFiltrado;
        });
        
        // Enviar al backend para generar Excel
        const response = await fetch(`${CONFIG.API_URL}/exportar-preview-personalizado`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                datos: datosFiltrados,
                nombre_reporte: document.getElementById('modalTitle').textContent || 'Reporte'
            })
        });

        if (response.ok) {
            descargarArchivo(response, 'reporte_personalizado.xlsx');
            showNotification('Excel generado con columnas personalizadas ✅');
            window.datosParaExportar = null; // Limpiar datos temporales
        } else {
            showNotification('Error al generar Excel', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

/**
 * Exporta generando nuevo reporte con parámetros
 */
async function exportarNuevoReporteConColumnas() {
    const params = obtenerParametrosReabastecimiento();
    params.columnas_seleccionadas = columnasSeleccionadas;

    try {
        showNotification(CONFIG.MESSAGES.generandoReporte, 'success');
        
        const response = await fetch(`${CONFIG.API_URL}/reabastecimiento`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (response.ok) {
            descargarArchivo(response, 'reabastecimiento_jagi.xlsx');
            showNotification('Reporte generado con columnas personalizadas ✅');
        } else {
            showNotification('Error al generar reporte', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

// ==========================================
// 17. SISTEMA DE FILTROS AVANZADOS CON PESTAÑAS
// ==========================================

// Estado global del sistema de filtros
const estadoFiltros = {
    tiendas: [],
    tiendasSeleccionadas: [],
    observaciones: [],
    observacionesSeleccionadas: [],
    columnas: [],
    columnasSeleccionadas: [],
    totalRegistros: 0,
    pestanaActual: 'filtros', // 'filtros', 'columnas', 'resumen'
    datosPreview: null,
    parametros: null
};

let timeoutPreview = null;

// ==========================================
// FUNCIONES PRINCIPALES
// ==========================================

/**
 * Abre el modal de exportación avanzada
 */
async function abrirModalExportacionAvanzada() {
    const params = obtenerParametrosReabastecimiento();
    estadoFiltros.parametros = params;
    
    try {
        showNotification('Cargando opciones de filtros...', 'success');
        
        // Obtener opciones disponibles
        const response = await fetch(`${CONFIG.API_URL}/reabastecimiento/opciones-filtros`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (response.ok) {
            const result = await response.json();
            
            // Actualizar estado
            estadoFiltros.tiendas = result.tiendas;
            estadoFiltros.tiendasSeleccionadas = [...result.tiendas]; // Todas por defecto
            estadoFiltros.observaciones = result.observaciones;
            estadoFiltros.observacionesSeleccionadas = [...result.observaciones]; // Todas por defecto
            estadoFiltros.columnas = result.columnas;
            estadoFiltros.columnasSeleccionadas = [...result.columnas]; // Todas por defecto
            estadoFiltros.totalRegistros = result.total_registros;
            
            // Mostrar modal
            mostrarModalFiltrosAvanzados();
            
            // Cargar preview inicial
            actualizarPreviewFiltrado();
        } else {
            showNotification('Error al cargar opciones', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

/**
 * Muestra el modal y renderiza la pestaña inicial
 */
function mostrarModalFiltrosAvanzados() {
    const modal = document.getElementById('modalFiltrosAvanzados');
    if (!modal) {
        console.error('Modal de filtros avanzados no encontrado');
        return;
    }
    
    modal.classList.remove('hidden');
    estadoFiltros.pestanaActual = 'filtros';
    renderizarPestana('filtros');
}

/**
 * Cierra el modal y resetea estado
 */
function cerrarModalFiltrosAvanzados() {
    const modal = document.getElementById('modalFiltrosAvanzados');
    if (modal) {
        modal.classList.add('hidden');
    }
    
    // Resetear estado
    estadoFiltros.pestanaActual = 'filtros';
    estadoFiltros.datosPreview = null;
}

// ==========================================
// SISTEMA DE PESTAÑAS
// ==========================================

/**
 * Cambia a una pestaña específica
 */
function cambiarPestanaFiltros(pestana) {
    estadoFiltros.pestanaActual = pestana;
    renderizarPestana(pestana);
}

/**
 * Renderiza el contenido de una pestaña
 */
function renderizarPestana(pestana) {
    // Actualizar tabs visuales
    document.querySelectorAll('.tab-filtros').forEach(tab => {
        tab.classList.remove('active', 'border-blue-600', 'text-blue-600');
        tab.classList.add('text-gray-600');
    });
    
    const tabActivo = document.querySelector(`[data-tab="${pestana}"]`);
    if (tabActivo) {
        tabActivo.classList.add('active', 'border-blue-600', 'text-blue-600');
        tabActivo.classList.remove('text-gray-600');
    }
    
    // Mostrar/ocultar contenido
    document.querySelectorAll('.contenido-pestana').forEach(contenido => {
        contenido.classList.add('hidden');
    });
    
    const contenidoActivo = document.getElementById(`pestana-${pestana}`);
    if (contenidoActivo) {
        contenidoActivo.classList.remove('hidden');
    }
    
    // Renderizar contenido específico
    if (pestana === 'filtros') {
        renderizarFiltrosTiendas();
        renderizarFiltrosObservaciones();
    } else if (pestana === 'columnas') {
        renderizarSelectorColumnas();
    } else if (pestana === 'resumen') {
        renderizarResumen();
    }
    
    // Actualizar botones de navegación
    actualizarBotonesNavegacion();
}

// ==========================================
// PESTAÑA 1: FILTROS DE DATOS
// ==========================================

/**
 * Renderiza checkboxes de tiendas
 */
function renderizarFiltrosTiendas() {
    const container = document.getElementById('listaTiendasFiltro');
    if (!container) return;
    
    container.innerHTML = '';
    
    estadoFiltros.tiendas.forEach((tienda, index) => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-2 p-2 hover:bg-gray-50 rounded transition';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `tienda-${index}`;
        checkbox.value = tienda;
        checkbox.checked = estadoFiltros.tiendasSeleccionadas.includes(tienda);
        checkbox.className = 'w-4 h-4 cursor-pointer';
        checkbox.onchange = (e) => toggleTienda(tienda, e.target.checked);
        
        const label = document.createElement('label');
        label.htmlFor = `tienda-${index}`;
        label.className = 'text-sm cursor-pointer flex-1';
        label.textContent = tienda;
        
        div.appendChild(checkbox);
        div.appendChild(label);
        container.appendChild(div);
    });
    
    actualizarContadorTiendas();
}

/**
 * Renderiza checkboxes de observaciones
 */
function renderizarFiltrosObservaciones() {
    const container = document.getElementById('listaObservacionesFiltro');
    if (!container) return;
    
    container.innerHTML = '';
    
    const iconos = {
        'REABASTECER': '🔄',
        'COMPRA': '🛒',
        'EXPANSION': '📈',
        'NUEVO': '🆕',
        'OK': '✅'
    };
    
    estadoFiltros.observaciones.forEach((obs, index) => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-2 p-2 hover:bg-gray-50 rounded transition';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `obs-${index}`;
        checkbox.value = obs;
        checkbox.checked = estadoFiltros.observacionesSeleccionadas.includes(obs);
        checkbox.className = 'w-4 h-4 cursor-pointer';
        checkbox.onchange = (e) => toggleObservacion(obs, e.target.checked);
        
        const label = document.createElement('label');
        label.htmlFor = `obs-${index}`;
        label.className = 'text-sm cursor-pointer flex-1 flex items-center gap-1';
        label.innerHTML = `<span>${iconos[obs] || '📊'}</span> ${obs}`;
        
        div.appendChild(checkbox);
        div.appendChild(label);
        container.appendChild(div);
    });
    
    actualizarContadorObservaciones();
}

/**
 * Toggle selección de tienda
 */
function toggleTienda(tienda, seleccionada) {
    if (seleccionada) {
        if (!estadoFiltros.tiendasSeleccionadas.includes(tienda)) {
            estadoFiltros.tiendasSeleccionadas.push(tienda);
        }
    } else {
        estadoFiltros.tiendasSeleccionadas = estadoFiltros.tiendasSeleccionadas.filter(t => t !== tienda);
    }
    
    actualizarContadorTiendas();
    actualizarPreviewFiltradoDebounced();
}

/**
 * Toggle selección de observación
 */
function toggleObservacion(obs, seleccionada) {
    if (seleccionada) {
        if (!estadoFiltros.observacionesSeleccionadas.includes(obs)) {
            estadoFiltros.observacionesSeleccionadas.push(obs);
        }
    } else {
        estadoFiltros.observacionesSeleccionadas = estadoFiltros.observacionesSeleccionadas.filter(o => o !== obs);
    }
    
    actualizarContadorObservaciones();
    actualizarPreviewFiltradoDebounced();
}

/**
 * Selecciona/deselecciona todas las tiendas
 */
function toggleTodasTiendas(seleccionar) {
    const checkboxes = document.querySelectorAll('#listaTiendasFiltro input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = seleccionar;
    });
    
    if (seleccionar) {
        estadoFiltros.tiendasSeleccionadas = [...estadoFiltros.tiendas];
    } else {
        estadoFiltros.tiendasSeleccionadas = [];
    }
    
    actualizarContadorTiendas();
    actualizarPreviewFiltradoDebounced();
}

/**
 * Selecciona/deselecciona todas las observaciones
 */
function toggleTodasObservaciones(seleccionar) {
    const checkboxes = document.querySelectorAll('#listaObservacionesFiltro input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = seleccionar;
    });
    
    if (seleccionar) {
        estadoFiltros.observacionesSeleccionadas = [...estadoFiltros.observaciones];
    } else {
        estadoFiltros.observacionesSeleccionadas = [];
    }
    
    actualizarContadorObservaciones();
    actualizarPreviewFiltradoDebounced();
}

/**
 * Actualiza preview con debouncing (espera 300ms)
 */
function actualizarPreviewFiltradoDebounced() {
    clearTimeout(timeoutPreview);
    
    // Mostrar loading
    const previewContainer = document.getElementById('previewFiltrado');
    if (previewContainer) {
        previewContainer.innerHTML = '<div class="text-center p-4 text-gray-500">Actualizando...</div>';
    }
    
    timeoutPreview = setTimeout(() => {
        actualizarPreviewFiltrado();
    }, 300);
}

/**
 * Actualiza el preview filtrado
 */
async function actualizarPreviewFiltrado() {
    try {
        const params = {
            ...estadoFiltros.parametros,
            tiendas_filtro: estadoFiltros.tiendasSeleccionadas,
            observaciones_filtro: estadoFiltros.observacionesSeleccionadas
        };
        
        const response = await fetch(`${CONFIG.API_URL}/reabastecimiento/preview-filtrado`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (response.ok) {
            const result = await response.json();
            estadoFiltros.datosPreview = result.datos;
            estadoFiltros.totalRegistros = result.total_registros;
            
            renderizarPreviewTabla(result);
        }
    } catch (error) {
        console.error('Error al actualizar preview:', error);
    }
}

/**
 * Renderiza tabla de preview
 */
function renderizarPreviewTabla(resultado) {
    const container = document.getElementById('previewFiltrado');
    if (!container) return;
    
    // Estadísticas
    const stats = `
        <div class="grid grid-cols-3 gap-3 mb-4">
            <div class="bg-blue-50 p-3 rounded text-center">
                <div class="text-2xl font-bold text-blue-600">${resultado.total_registros}</div>
                <div class="text-xs text-gray-600">Registros</div>
            </div>
            <div class="bg-green-50 p-3 rounded text-center">
                <div class="text-2xl font-bold text-green-600">${resultado.tiendas_incluidas}</div>
                <div class="text-xs text-gray-600">Tiendas</div>
            </div>
            <div class="bg-purple-50 p-3 rounded text-center">
                <div class="text-2xl font-bold text-purple-600">${resultado.productos_unicos}</div>
                <div class="text-xs text-gray-600">Productos</div>
            </div>
        </div>
    `;
    
    if (resultado.datos.length === 0) {
        container.innerHTML = stats + '<div class="text-center p-6 text-gray-500">Sin datos con los filtros aplicados</div>';
        return;
    }
    
    // Tabla (primeras 5 filas)
    const columnas = Object.keys(resultado.datos[0]);
    const filas = resultado.datos.slice(0, 5);
    
    const tabla = `
        <div class="overflow-x-auto max-h-60 border rounded">
            <table class="w-full text-xs">
                <thead class="bg-gray-100 sticky top-0">
                    <tr>
                        ${columnas.map(col => `<th class="p-2 text-left">${col}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${filas.map((row, idx) => `
                        <tr class="${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}">
                            ${columnas.map(col => `<td class="p-2 border-t">${row[col] || '-'}</td>`).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        ${resultado.preview_registros < resultado.total_registros ? 
            `<div class="text-xs text-gray-500 mt-2 text-center">Mostrando primeras ${resultado.preview_registros} filas de ${resultado.total_registros}</div>` 
            : ''}
    `;
    
    container.innerHTML = stats + tabla;
}

// ==========================================
// PESTAÑA 2: SELECCIÓN DE COLUMNAS
// ==========================================

/**
 * Renderiza selector de columnas
 */
function renderizarSelectorColumnas() {
    const container = document.getElementById('listaSelectorColumnas');
    if (!container) return;
    
    container.innerHTML = '';
    
    estadoFiltros.columnas.forEach((columna, index) => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-2 p-2 hover:bg-gray-50 rounded transition';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `col-filtro-${index}`;
        checkbox.value = columna;
        checkbox.checked = estadoFiltros.columnasSeleccionadas.includes(columna);
        checkbox.className = 'w-4 h-4 cursor-pointer';
        checkbox.onchange = (e) => toggleColumnaFiltro(columna, e.target.checked);
        
        const label = document.createElement('label');
        label.htmlFor = `col-filtro-${index}`;
        label.className = 'text-sm cursor-pointer flex-1';
        label.textContent = columna;
        
        div.appendChild(checkbox);
        div.appendChild(label);
        container.appendChild(div);
    });
    
    actualizarContadorColumnas();
    actualizarPreviewColumnasSeleccionadas();
}

/**
 * Toggle selección de columna
 */
function toggleColumnaFiltro(columna, seleccionada) {
    if (seleccionada) {
        if (!estadoFiltros.columnasSeleccionadas.includes(columna)) {
            estadoFiltros.columnasSeleccionadas.push(columna);
        }
    } else {
        estadoFiltros.columnasSeleccionadas = estadoFiltros.columnasSeleccionadas.filter(c => c !== columna);
    }
    
    actualizarContadorColumnas();
    actualizarPreviewColumnasSeleccionadas();
}

/**
 * Selecciona/deselecciona todas las columnas
 */
function toggleTodasColumnasAvanzado(seleccionar) {
    const checkboxes = document.querySelectorAll('#listaSelectorColumnas input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = seleccionar;
    });
    
    if (seleccionar) {
        estadoFiltros.columnasSeleccionadas = [...estadoFiltros.columnas];
    } else {
        estadoFiltros.columnasSeleccionadas = [];
    }
    
    actualizarContadorColumnas();
    actualizarPreviewColumnasSeleccionadas();
}

// ==========================================
// PESTAÑA 3: RESUMEN
// ==========================================

/**
 * Renderiza resumen final antes de exportar
 */
function renderizarResumen() {
    const container = document.getElementById('contenidoResumen');
    if (!container) return;
    
    const html = `
        <div class="space-y-4">
            <!-- Tiendas -->
            <div class="bg-blue-50 p-4 rounded-lg border-l-4 border-blue-500">
                <h4 class="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                    <span>🏪</span> Tiendas seleccionadas
                </h4>
                <div class="text-sm text-blue-700">
                    ${estadoFiltros.tiendasSeleccionadas.length === estadoFiltros.tiendas.length 
                        ? '<span class="font-medium">Todas las tiendas</span> (' + estadoFiltros.tiendas.length + ')'
                        : '<span class="font-medium">' + estadoFiltros.tiendasSeleccionadas.length + ' de ' + estadoFiltros.tiendas.length + ' tiendas</span>: ' + estadoFiltros.tiendasSeleccionadas.join(', ')
                    }
                </div>
            </div>
            
            <!-- Observaciones -->
            <div class="bg-green-50 p-4 rounded-lg border-l-4 border-green-500">
                <h4 class="font-semibold text-green-900 mb-2 flex items-center gap-2">
                    <span>📊</span> Observaciones incluidas
                </h4>
                <div class="text-sm text-green-700">
                    ${estadoFiltros.observacionesSeleccionadas.length === estadoFiltros.observaciones.length 
                        ? '<span class="font-medium">Todas las observaciones</span> (' + estadoFiltros.observaciones.length + ')'
                        : '<span class="font-medium">' + estadoFiltros.observacionesSeleccionadas.length + ' de ' + estadoFiltros.observaciones.length + ' tipos</span>: ' + estadoFiltros.observacionesSeleccionadas.join(', ')
                    }
                </div>
            </div>
            
            <!-- Columnas -->
            <div class="bg-purple-50 p-4 rounded-lg border-l-4 border-purple-500">
                <h4 class="font-semibold text-purple-900 mb-2 flex items-center gap-2">
                    <span>📋</span> Columnas a exportar
                </h4>
                <div class="text-sm text-purple-700">
                    <span class="font-medium">${estadoFiltros.columnasSeleccionadas.length} de ${estadoFiltros.columnas.length} columnas</span>
                    <div class="mt-2 flex flex-wrap gap-1">
                        ${estadoFiltros.columnasSeleccionadas.map(col => 
                            `<span class="inline-block bg-purple-100 px-2 py-1 rounded text-xs">${col}</span>`
                        ).join('')}
                    </div>
                </div>
            </div>
            
            <!-- Total de registros -->
            <div class="bg-orange-50 p-4 rounded-lg border-l-4 border-orange-500">
                <h4 class="font-semibold text-orange-900 mb-2 flex items-center gap-2">
                    <span>📦</span> Total a exportar
                </h4>
                <div class="text-sm text-orange-700">
                    <span class="text-2xl font-bold">${estadoFiltros.totalRegistros.toLocaleString()}</span> registros
                </div>
            </div>
            
            <!-- Advertencia si hay muchos datos -->
            ${estadoFiltros.totalRegistros > 10000 ? `
                <div class="bg-yellow-50 p-4 rounded-lg border-l-4 border-yellow-500">
                    <p class="text-sm text-yellow-800">
                        ⚠️ <strong>Nota:</strong> El reporte contiene más de 10,000 registros. 
                        La exportación puede tardar unos segundos.
                    </p>
                </div>
            ` : ''}
        </div>
    `;
    
    container.innerHTML = html;
}

// ==========================================
// NAVEGACIÓN Y CONTROLES
// ==========================================

/**
 * Actualiza botones de navegación según pestaña actual
 */
function actualizarBotonesNavegacion() {
    const btnAtras = document.getElementById('btnAtras');
    const btnSiguiente = document.getElementById('btnSiguiente');
    const btnExportar = document.getElementById('btnExportar');
    
    if (!btnAtras || !btnSiguiente || !btnExportar) return;
    
    // Resetear visibilidad
    btnAtras.classList.add('hidden');
    btnSiguiente.classList.add('hidden');
    btnExportar.classList.add('hidden');
    
    if (estadoFiltros.pestanaActual === 'filtros') {
        btnSiguiente.classList.remove('hidden');
    } else if (estadoFiltros.pestanaActual === 'columnas') {
        btnAtras.classList.remove('hidden');
        btnSiguiente.classList.remove('hidden');
    } else if (estadoFiltros.pestanaActual === 'resumen') {
        btnAtras.classList.remove('hidden');
        btnExportar.classList.remove('hidden');
    }
}

/**
 * Navega a la pestaña anterior
 */
function irPestanaAnterior() {
    if (estadoFiltros.pestanaActual === 'columnas') {
        cambiarPestanaFiltros('filtros');
    } else if (estadoFiltros.pestanaActual === 'resumen') {
        cambiarPestanaFiltros('columnas');
    }
}

/**
 * Navega a la pestaña siguiente
 */
function irPestanaSiguiente() {
    // Validaciones antes de avanzar
    if (estadoFiltros.pestanaActual === 'filtros') {
        if (estadoFiltros.tiendasSeleccionadas.length === 0) {
            showNotification('Debes seleccionar al menos una tienda', 'error');
            return;
        }
        if (estadoFiltros.observacionesSeleccionadas.length === 0) {
            showNotification('Debes seleccionar al menos un tipo de observación', 'error');
            return;
        }
        cambiarPestanaFiltros('columnas');
    } else if (estadoFiltros.pestanaActual === 'columnas') {
        if (estadoFiltros.columnasSeleccionadas.length === 0) {
            showNotification('Debes seleccionar al menos una columna', 'error');
            return;
        }
        cambiarPestanaFiltros('resumen');
    }
}

/**
 * Exporta con todos los filtros aplicados
 */
async function exportarConFiltrosAvanzados() {
    // Validación final
    if (estadoFiltros.columnasSeleccionadas.length === 0) {
        showNotification('Debes seleccionar al menos una columna', 'error');
        return;
    }
    
    if (estadoFiltros.totalRegistros === 0) {
        showNotification('No hay datos para exportar con los filtros aplicados', 'error');
        return;
    }
    
    cerrarModalFiltrosAvanzados();
    
    try {
        showNotification(CONFIG.MESSAGES.generandoReporte, 'success');
        
        const params = {
            ...estadoFiltros.parametros,
            tiendas_filtro: estadoFiltros.tiendasSeleccionadas,
            observaciones_filtro: estadoFiltros.observacionesSeleccionadas,
            columnas_seleccionadas: estadoFiltros.columnasSeleccionadas
        };
        
        const response = await fetch(`${CONFIG.API_URL}/reabastecimiento`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        if (response.ok) {
            descargarArchivo(response, 'reabastecimiento_personalizado.xlsx');
            showNotification(`Reporte generado: ${estadoFiltros.totalRegistros} registros ✅`);
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Error al generar reporte', 'error');
        }
    } catch (error) {
        console.error(error);
        showNotification(CONFIG.MESSAGES.errorConexion, 'error');
    }
}

// ==========================================
// ACTUALIZADORES DE CONTADORES
// ==========================================

function actualizarContadorTiendas() {
    const contador = document.getElementById('contadorTiendas');
    if (contador) {
        contador.textContent = `${estadoFiltros.tiendasSeleccionadas.length} de ${estadoFiltros.tiendas.length} seleccionadas`;
    }
}

function actualizarContadorObservaciones() {
    const contador = document.getElementById('contadorObservaciones');
    if (contador) {
        contador.textContent = `${estadoFiltros.observacionesSeleccionadas.length} de ${estadoFiltros.observaciones.length} seleccionadas`;
    }
}

function actualizarContadorColumnas() {
    const contador = document.getElementById('contadorColumnas');
    if (contador) {
        contador.textContent = `${estadoFiltros.columnasSeleccionadas.length} de ${estadoFiltros.columnas.length} columnas`;
    }
}

// ==========================================
// 19. PREVIEW DE COLUMNAS SELECCIONADAS
// ==========================================

/**
 * Actualiza el preview visual de cómo se verán las columnas en el Excel
 */
function actualizarPreviewColumnasSeleccionadas() {
    const container = document.getElementById('previewColumnasSeleccionadas');
    if (!container) return;
    
    // Verificar que hay columnas seleccionadas
    if (estadoFiltros.columnasSeleccionadas.length === 0) {
        container.innerHTML = `
            <div class="text-center p-8 text-gray-500 bg-gray-50 rounded-lg border-2 border-dashed">
                <div class="text-4xl mb-2">📋</div>
                <p class="font-medium">Selecciona columnas para ver el preview</p>
                <p class="text-sm mt-1">El preview mostrará cómo se verá tu Excel</p>
            </div>
        `;
        return;
    }
    
    // Verificar que hay datos del preview filtrado
    if (!estadoFiltros.datosPreview || estadoFiltros.datosPreview.length === 0) {
        container.innerHTML = `
            <div class="text-center p-8 text-gray-500 bg-yellow-50 rounded-lg border-2 border-yellow-300">
                <div class="text-4xl mb-2">⚠️</div>
                <p class="font-medium">No hay datos disponibles</p>
                <p class="text-sm mt-1">Regresa a la pestaña de filtros y selecciona datos</p>
            </div>
        `;
        return;
    }
    
    // Tomar las primeras 5 filas del preview
    const filasPreview = estadoFiltros.datosPreview.slice(0, 5);
    
    // Filtrar solo las columnas seleccionadas
    const datosFiltrados = filasPreview.map(row => {
        const rowFiltrado = {};
        estadoFiltros.columnasSeleccionadas.forEach(col => {
            if (row.hasOwnProperty(col)) {
                rowFiltrado[col] = row[col];
            }
        });
        return rowFiltrado;
    });
    
    // Generar HTML de la tabla
    const html = `
        <div class="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-lg border-2 border-blue-200">
            <div class="flex items-center gap-2 mb-3">
                <span class="text-2xl">👁️</span>
                <div class="flex-1">
                    <h4 class="font-semibold text-gray-800">Vista Previa del Excel</h4>
                    <p class="text-xs text-gray-600">
                        Mostrando ${Math.min(5, datosFiltrados.length)} filas con 
                        <span class="font-medium text-blue-600">${estadoFiltros.columnasSeleccionadas.length} columnas</span> seleccionadas
                    </p>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow-sm overflow-x-auto border">
                <table class="w-full text-xs">
                    <thead class="bg-gradient-to-r from-blue-600 to-blue-700 text-white sticky top-0">
                        <tr>
                            ${estadoFiltros.columnasSeleccionadas.map(col => 
                                `<th class="p-3 text-left font-semibold whitespace-nowrap border-r border-blue-500 last:border-r-0">
                                    ${col}
                                </th>`
                            ).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${datosFiltrados.map((row, idx) => `
                            <tr class="${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-blue-50 transition">
                                ${estadoFiltros.columnasSeleccionadas.map(col => 
                                    `<td class="p-3 border-b border-r border-gray-200 last:border-r-0 whitespace-nowrap">
                                        ${row[col] !== null && row[col] !== undefined ? row[col] : '-'}
                                    </td>`
                                ).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            
            <div class="mt-3 flex items-center gap-2 text-xs text-gray-600 bg-white p-2 rounded border">
                <span>💡</span>
                <span>
                    <strong>Tip:</strong> Este es el orden y formato exacto que verás en el Excel descargado.
                    ${estadoFiltros.totalRegistros > 5 ? 
                        ` El archivo completo tendrá <strong>${estadoFiltros.totalRegistros.toLocaleString()}</strong> filas.` 
                        : ''}
                </span>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}