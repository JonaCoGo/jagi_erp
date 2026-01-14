# movimiento_service.py

from app.database import get_connection, date_subtract_days, date_format_convert
from app.repositories import movimiento_repository as repo

def get_movimiento(dias=30):
    fecha_desde = date_subtract_days(dias)
    fecha_col = date_format_convert("f_sistema")

    with get_connection() as conn:
        return repo.fetch_movimiento(conn, fecha_col, fecha_desde)
    
    