JAGI ERP

Sistema ERP desarrollado en Python con interfaz web, enfocado en análisis de inventario, ventas y apoyo a la toma de decisiones operativas.

Este proyecto nace como una iniciativa personal con fines educativos y de práctica profesional. 
Ha sido utilizado como apoyo en un entorno académico (SENA) y en un contexto laboral, sin incluir información sensible ni datos reales de la empresa.

🧠 Arquitectura general

Backend: Python + FastAPI

Base de datos: SQLite (local)

Frontend: HTML, CSS y JavaScript

Testing: Pytest

Editor recomendado: VS Code

La base de datos no se versiona. Se genera localmente mediante scripts incluidos en este repositorio.

🚀 Funcionalidades principales

Análisis de inventario y ventas

Reportes Excel automatizados

Análisis por marca (Top 10, faltantes, cobertura por tienda)

Dashboard web para visualización

API REST para consumo del frontend

Pruebas automatizadas para evitar regresiones

🗂️ Estructura del proyecto
app/
│── main.py              # API FastAPI
│── consultas.py         # Lógica de consultas
│── database.py          # Conexión y helpers de BD
│
├── cli/                 # CLI opcional
├── reports/             # Exportación a Excel
├── services/            # Capa de servicios (en evolución)
├── repositories/        # Acceso a datos (en evolución)
│
data/
│── inputs/              # Archivos de carga (no sensibles)
│── reports/             # Reportes generados
│
scripts/
│── create_schema.py     # Crear esquema de BD
│── seed_data.py         # Datos ficticios
│── inspect_BD.py        # Inspección de BD
│
test/
│── test_analisis_marca.py
│── test_api_analisis_marca.py
│── test_database.py

🧪 Pruebas

Ejecutar todas las pruebas:

pytest

Las pruebas validan:

Contratos de datos esperados por el frontend

Estructura de respuestas de las consultas

Conexión a la base de datos

Endpoints de la API

▶️ Ejecución local
1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

2. Instalar dependencias
pip install -r requirements.txt

3. Crear base de datos local
python scripts/create_schema.py
python scripts/seed_data.py

4. Levantar la API
uvicorn app.main:app --reload

5. Abrir en el navegador
http://127.0.0.1:8000