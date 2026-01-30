# app/schemas/reabastecimiento.py

"""
Schemas para el módulo de Reabastecimiento.

Define la estructura y validación de datos para:
- Cálculo de reabastecimiento
- Filtros de reabastecimiento
- Respuestas de reabastecimiento

"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from app.schemas.common import (
    DateRangeParams,
    TiendaFilter,
    ProductoFilter,
    ResponseBase
)


# ==========================================
# REQUEST SCHEMAS
# ==========================================

class ReabastecimientoCalculoRequest(BaseModel):
    """
    Request para calcular reabastecimiento.
    
    Ejemplo:
        {
            "dias_venta": 7,
            "dias_stock": 14,
            "fecha_inicio": "01/01/2026",
            "fecha_fin": "30/01/2026",
            "tiendas": ["T001", "T002"],
            "productos": ["P001", "P002"]
        }
    """
    
    dias_venta: int = Field(
        ...,
        ge=1,
        le=90,
        description="Días para calcular promedio de ventas"
    )
    
    dias_stock: int = Field(
        ...,
        ge=1,
        le=180,
        description="Días de stock objetivo"
    )
    
    fecha_inicio: str = Field(
        ...,
        description="Fecha inicial del período (DD/MM/YYYY)"
    )
    
    fecha_fin: str = Field(
        ...,
        description="Fecha final del período (DD/MM/YYYY)"
    )
    
    tiendas: Optional[List[str]] = Field(
        default=None,
        description="Filtrar por tiendas específicas"
    )
    
    productos: Optional[List[str]] = Field(
        default=None,
        description="Filtrar por productos específicos"
    )
    
    incluir_sin_movimiento: bool = Field(
        default=False,
        description="Incluir productos sin movimiento"
    )
    
    @field_validator('fecha_inicio', 'fecha_fin')
    def validate_date_format(cls, v):
        """Valida formato DD/MM/YYYY."""
        import re
        from datetime import datetime
        
        pattern = r'^\d{2}/\d{2}/\d{4}$'
        if not re.match(pattern, v):
            raise ValueError('Fecha debe estar en formato DD/MM/YYYY')
        
        try:
            day, month, year = map(int, v.split('/'))
            datetime(year, month, day)
        except ValueError:
            raise ValueError(f'Fecha inválida: {v}')
        
        return v
    
    @field_validator('fecha_fin')
    def validate_date_range(cls, v, info):
        """Valida que fecha_fin > fecha_inicio."""
        if 'fecha_inicio' in info.data:
            from datetime import datetime
            inicio = datetime.strptime(info.data['fecha_inicio'], '%d/%m/%Y')
            fin = datetime.strptime(v, '%d/%m/%Y')
            
            if fin < inicio:
                raise ValueError('Fecha final debe ser posterior a fecha inicial')
        
        return v
    
    @field_validator('tiendas', 'productos')
    def normalize_codes(cls, v):
        """Normaliza códigos a uppercase sin espacios."""
        if v:
            return [item.strip().upper() for item in v if item.strip()]
        return v
    
    @field_validator('dias_stock')
    def validate_dias_stock_vs_venta(cls, v, info):
        """Valida que dias_stock >= dias_venta."""
        if 'dias_venta' in info.data:
            if v < info.data['dias_venta']:
                raise ValueError(
                    'Días de stock debe ser mayor o igual a días de venta'
                )
        return v


class ReabastecimientoFiltrosRequest(BaseModel):
    """
    Request para filtrar resultados de reabastecimiento.
    
    Se usa después de calcular para refinar resultados.
    """
    
    stock_minimo: Optional[int] = Field(
        default=None,
        ge=0,
        description="Filtrar por stock mínimo"
    )
    
    stock_maximo: Optional[int] = Field(
        default=None,
        ge=0,
        description="Filtrar por stock máximo"
    )
    
    necesidad_minima: Optional[int] = Field(
        default=None,
        ge=0,
        description="Filtrar por necesidad mínima"
    )
    
    solo_con_necesidad: bool = Field(
        default=True,
        description="Mostrar solo productos con necesidad > 0"
    )
    
    ordenar_por: str = Field(
        default="necesidad",
        pattern="^(necesidad|stock|venta_promedio|tienda|producto)$",
        description="Campo para ordenar resultados"
    )
    
    orden_descendente: bool = Field(
        default=True,
        description="Orden descendente (True) o ascendente (False)"
    )


# ==========================================
# RESPONSE SCHEMAS
# ==========================================

class ReabastecimientoItem(BaseModel):
    """Item individual de reabastecimiento."""
    
    tienda: str
    producto: str
    descripcion: Optional[str] = None
    stock_actual: int
    venta_promedio: float
    dias_stock_actual: float
    necesidad: int
    prioridad: str  # "ALTA", "MEDIA", "BAJA"
    
    class Config:
        json_schema_extra = {
            "example": {
                "tienda": "T001",
                "producto": "P001",
                "descripcion": "Producto Ejemplo",
                "stock_actual": 10,
                "venta_promedio": 5.0,
                "dias_stock_actual": 2.0,
                "necesidad": 60,
                "prioridad": "ALTA"
            }
        }


class ReabastecimientoResponse(ResponseBase):
    """Respuesta del cálculo de reabastecimiento."""
    
    total_items: int = Field(..., description="Total de items calculados")
    items_con_necesidad: int = Field(..., description="Items que necesitan reabastecimiento")
    total_unidades_necesarias: int = Field(..., description="Total de unidades a reabastecer")
    
    parametros: dict = Field(..., description="Parámetros usados en el cálculo")
    
    items: List[ReabastecimientoItem] = Field(
        default=[],
        description="Lista de items de reabastecimiento"
    )
    
    resumen_por_tienda: Optional[dict] = Field(
        default=None,
        description="Resumen agrupado por tienda"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Reabastecimiento calculado correctamente",
                "total_items": 150,
                "items_con_necesidad": 45,
                "total_unidades_necesarias": 1250,
                "parametros": {
                    "dias_venta": 7,
                    "dias_stock": 14,
                    "fecha_inicio": "01/01/2026",
                    "fecha_fin": "30/01/2026"
                },
                "items": []
            }
        }


# ==========================================
# EXPORT SCHEMAS
# ==========================================

class ReabastecimientoExportRequest(BaseModel):
    """Request para exportar reabastecimiento a Excel."""
    
    formato: str = Field(
        default="excel",
        pattern="^(excel|csv)$",
        description="Formato de exportación"
    )
    
    incluir_graficos: bool = Field(
        default=True,
        description="Incluir gráficos en Excel"
    )
    
    incluir_resumen: bool = Field(
        default=True,
        description="Incluir hoja de resumen"
    )
    
    agrupar_por_tienda: bool = Field(
        default=False,
        description="Crear hojas separadas por tienda"
    )