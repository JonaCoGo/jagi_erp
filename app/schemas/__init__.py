# app/schemas/__init__.py
"""
Schemas Pydantic para validación de datos del ERP.

Estos schemas definen la estructura y validación de datos
para todos los endpoints de la API.

Convenciones:
- *Request: Datos de entrada
- *Response: Datos de salida
- *Filter: Parámetros de filtrado
- *Item: Item individual en lista

"""

# Schemas comunes
from app.schemas.common import (
    ResponseBase,
    ErrorResponse,
    PaginationParams,
    DateRangeParams,
    TiendaFilter,
    ProductoFilter,
    TiendaBase,
    ProductoBase,
    StockInfo,
    ExportFormat,
    parse_date_dd_mm_yyyy,
    format_date_to_dd_mm_yyyy,
)

# Schemas de reabastecimiento
from app.schemas.reabastecimiento import (
    ReabastecimientoCalculoRequest,
    ReabastecimientoFiltrosRequest,
    ReabastecimientoItem,
    ReabastecimientoResponse,
    ReabastecimientoExportRequest,
)

__all__ = [
    # Common
    "ResponseBase",
    "ErrorResponse",
    "PaginationParams",
    "DateRangeParams",
    "TiendaFilter",
    "ProductoFilter",
    "TiendaBase",
    "ProductoBase",
    "StockInfo",
    "ExportFormat",
    "parse_date_dd_mm_yyyy",
    "format_date_to_dd_mm_yyyy",
    
    # Reabastecimiento
    "ReabastecimientoCalculoRequest",
    "ReabastecimientoFiltrosRequest",
    "ReabastecimientoItem",
    "ReabastecimientoResponse",
    "ReabastecimientoExportRequest",
]