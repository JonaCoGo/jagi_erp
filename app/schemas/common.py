# app/schemas/common.py

"""
Schemas comunes reutilizables en toda la aplicación.

Estos schemas se usan como base o se comparten
entre diferentes módulos del ERP.

"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
import re


# ==========================================
# SCHEMAS BASE
# ==========================================

class ResponseBase(BaseModel):
    """Schema base para respuestas exitosas."""
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Schema base para respuestas de error."""
    error: bool = True
    code: str
    message: str
    details: dict = {}


class PaginationParams(BaseModel):
    """Parámetros de paginación estándar."""
    page: int = Field(default=1, ge=1, description="Número de página")
    page_size: int = Field(default=50, ge=1, le=1000, description="Items por página")
    
    @property
    def offset(self) -> int:
        """Calcula el offset para SQL."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Alias para page_size."""
        return self.page_size


# ==========================================
# VALIDADORES DE FECHA
# ==========================================

class DateRangeParams(BaseModel):
    """Parámetros para rango de fechas."""
    fecha_inicio: str = Field(..., description="Fecha inicial (DD/MM/YYYY)")
    fecha_fin: str = Field(..., description="Fecha final (DD/MM/YYYY)")
    
    @field_validator('fecha_inicio', 'fecha_fin')
    def validate_date_format(cls, v):
        """Valida formato de fecha DD/MM/YYYY."""
        pattern = r'^\d{2}/\d{2}/\d{4}$'
        if not re.match(pattern, v):
            raise ValueError('Fecha debe estar en formato DD/MM/YYYY')
        
        # Validar que sea fecha válida
        try:
            day, month, year = map(int, v.split('/'))
            datetime(year, month, day)
        except ValueError:
            raise ValueError(f'Fecha inválida: {v}')
        
        return v
    
    @field_validator('fecha_fin')
    def fecha_fin_must_be_after_inicio(cls, v, info):
        """Valida que fecha_fin sea posterior a fecha_inicio."""
        if 'fecha_inicio' in info.data:
            inicio = datetime.strptime(info.data['fecha_inicio'], '%d/%m/%Y')
            fin = datetime.strptime(v, '%d/%m/%Y')
            
            if fin < inicio:
                raise ValueError('Fecha final debe ser posterior a fecha inicial')
        
        return v


# ==========================================
# SCHEMAS DE FILTROS
# ==========================================

class TiendaFilter(BaseModel):
    """Filtro de tiendas."""
    tiendas: Optional[List[str]] = Field(
        default=None,
        description="Lista de códigos de tiendas a filtrar"
    )
    
    @field_validator('tiendas')
    def normalize_tiendas(cls, v):
        """Normaliza códigos de tiendas (uppercase, sin espacios)."""
        if v:
            return [t.strip().upper() for t in v if t.strip()]
        return v


class ProductoFilter(BaseModel):
    """Filtro de productos."""
    productos: Optional[List[str]] = Field(
        default=None,
        description="Lista de códigos de productos a filtrar"
    )
    
    @field_validator('productos')
    def normalize_productos(cls, v):
        """Normaliza códigos de productos."""
        if v:
            return [p.strip().upper() for p in v if p.strip()]
        return v


# ==========================================
# SCHEMAS DE DATOS COMUNES
# ==========================================

class TiendaBase(BaseModel):
    """Información básica de tienda."""
    codigo: str = Field(..., min_length=1, max_length=50)
    nombre: Optional[str] = None
    
    @field_validator('codigo')
    def normalize_codigo(cls, v):
        """Normaliza código de tienda."""
        return v.strip().upper()


class ProductoBase(BaseModel):
    """Información básica de producto."""
    codigo: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = None
    
    @field_validator('codigo')
    def normalize_codigo(cls, v):
        """Normaliza código de producto."""
        return v.strip().upper()


class StockInfo(BaseModel):
    """Información de stock de producto."""
    tienda: str
    producto: str
    cantidad: int = Field(..., ge=0)
    fecha_actualizacion: Optional[datetime] = None


# ==========================================
# SCHEMAS DE EXPORTACIÓN
# ==========================================

class ExportFormat(BaseModel):
    """Formato de exportación solicitado."""
    format: str = Field(
        default="excel",
        pattern="^(excel|csv|pdf)$",
        description="Formato de exportación"
    )
    include_charts: bool = Field(
        default=True,
        description="Incluir gráficos (solo para Excel/PDF)"
    )
    
    @field_validator('format')
    def normalize_format(cls, v):
        """Normaliza formato a lowercase."""
        return v.lower()


# ==========================================
# HELPERS
# ==========================================

def parse_date_dd_mm_yyyy(date_str: str) -> date:
    """
    Convierte string DD/MM/YYYY a objeto date.
    
    Args:
        date_str: Fecha en formato DD/MM/YYYY
        
    Returns:
        Objeto date
        
    Raises:
        ValueError: Si el formato es inválido
    """
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        raise ValueError(f'Formato de fecha inválido: {date_str}')


def format_date_to_dd_mm_yyyy(d: date) -> str:
    """
    Convierte objeto date a string DD/MM/YYYY.
    
    Args:
        d: Objeto date
        
    Returns:
        String en formato DD/MM/YYYY
    """
    return d.strftime('%d/%m/%Y')