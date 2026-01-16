# 🏢 JAGI ERP - Sistema de Gestión de Inventarios

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Sistema ERP desarrollado para optimizar la gestión de inventarios, análisis de ventas y toma de decisiones operativas en retail.

---

## 📋 Características

- ✅ **Carga automática de datos** desde archivos CSV
- 📊 **Dashboard interactivo** con estadísticas en tiempo real
- 📦 **Análisis de inventario** por tienda y región
- 🔄 **Sugerencias de reabastecimiento** basadas en ventas históricas
- 🏷️ **Análisis por marca** (Top 10, cobertura, faltantes)
- 📈 **Reportes Excel** automatizados y personalizables
- 🔍 **Consulta de productos** con historial de movimientos

---

## 🚀 Instalación

### Prerequisitos

- Python 3.11 o superior
- pip (gestor de paquetes de Python)

### Pasos

1. **Clonar el repositorio**
```bash
git clone https://github.com/JonaCoGo/jagi_erp.git
cd jagi_erp
```

2. **Crear entorno virtual**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Crear base de datos**
```bash
python scripts/create_schema.py
python scripts/seed_data.py
```

5. **Ejecutar servidor**
```bash
uvicorn app.main:app --reload
```

6. **Abrir en navegador**
```
http://127.0.0.1:8000
```

---

## 🏗️ Arquitectura
```
JAGI_ERP/
├── app/
│   ├── main.py              # API FastAPI
│   ├── services/            # Lógica de negocio
│   ├── repositories/        # Acceso a datos
│   └── reports/             # Generación de reportes
├── static/                  # Frontend (HTML/CSS/JS)
├── scripts/                 # Utilidades BD
└── test/                    # Pruebas automatizadas
```

---

## 🧪 Testing
```bash
pytest
```

Cobertura actual: ~40% (en mejora continua)

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|-----------|-----------|
| Backend | FastAPI + Python 3.11 |
| Base de datos | SQLite (desarrollo) |
| Frontend | HTML5 + TailwindCSS + Vanilla JS |
| Testing | Pytest |
| Reportes | Pandas + OpenPyXL |

---

## 📖 Documentación API

Una vez ejecutado el servidor, visita:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

---

## 🤝 Contribuciones

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para las convenciones de commits y flujo de trabajo.

---

## 📝 Licencia

Este proyecto es de uso educativo y profesional.

---

## 👨‍💻 Autor

**Jonathan Cortés**  
Técnico en Programación de Aplicaciones - SENA  
[GitHub](https://github.com/JonaCoGo) | [LinkedIn](#)

---

## 📌 Estado del Proyecto

🚧 **En desarrollo activo** - Se aceptan sugerencias y mejoras